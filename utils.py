import asyncio
import logging
import os
import re
import tempfile
import uuid
import traceback
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Dict, Any, List, Optional, Set
import textwrap  # Добавлен импорт для dedent
import json
from config import PLANS
from database import cursor, conn
from config import bot
import aiohttp
from aiohttp import web
from aiohttp import ClientSession

from config import TEMP_DIR, stats_public_url, CRYPTO_PAY_TOKEN  # Импорт из config.py

app = web.Application()

MAX_WEBHOOK_BODY_BYTES = 64 * 1024
MAX_STATS_FILE_BYTES = 10 * 1024 * 1024
_ALLOWED_STATS_EXTS = {'.html', '.jpg'}
_STATS_FILENAME_RE = re.compile(r'^[A-Za-z0-9._-]{1,128}$')


def _resolve_temp_file_path(filename: str, allowed_exts: Set[str], require_exists: bool = False) -> str | None:
    """Безопасно резолвит путь файла внутри TEMP_DIR."""
    if not isinstance(filename, str):
        return None

    safe_name = filename.strip()
    if not safe_name or safe_name != os.path.basename(safe_name):
        return None
    if not _STATS_FILENAME_RE.fullmatch(safe_name):
        return None

    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in allowed_exts:
        return None

    temp_root = os.path.realpath(TEMP_DIR)
    os.makedirs(temp_root, exist_ok=True)

    candidate = os.path.realpath(os.path.join(temp_root, safe_name))
    try:
        if os.path.commonpath([candidate, temp_root]) != temp_root:
            return None
    except ValueError:
        return None

    if require_exists and not os.path.isfile(candidate):
        return None
    return candidate

async def handle_stats(request):
    filename = request.match_info.get('filename', '')
    filepath = _resolve_temp_file_path(filename, _ALLOWED_STATS_EXTS, require_exists=True)
    if not filepath:
        return web.Response(status=404, text="Not Found")

    try:
        if os.path.getsize(filepath) > MAX_STATS_FILE_BYTES:
            logging.warning(f"❌ Stats file too large: {filename}")
            return web.Response(status=413, text="File too large")
    except OSError:
        return web.Response(status=404, text="Not Found")

    ctype = 'image/jpeg' if filename.lower().endswith('.jpg') else 'text/html'
    return web.FileResponse(
        path=filepath,
        headers={
            "Content-Type": ctype,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )

async def handle_crypto_webhook(request):
    try:
        body = await request.read()
        if len(body) > MAX_WEBHOOK_BODY_BYTES:
            logging.warning("❌ Webhook body too large")
            return web.Response(status=413)

        signature = request.headers.get('Crypto-Pay-Api-Signature', '')
        if not signature:
            logging.warning("❌ Отсутствует подпись вебхука")
            return web.Response(status=403)

        if not CRYPTO_PAY_TOKEN:
            logging.error("❌ CRYPTO_PAY_TOKEN не задан")
            return web.Response(status=500)
     
        # Верификация подписи
        secret = hashlib.sha256(CRYPTO_PAY_TOKEN.encode()).digest()
        calculated_hmac = hmac.new(secret, body, hashlib.sha256).hexdigest()
     
        if not hmac.compare_digest(calculated_hmac, signature):
            logging.warning("❌ Неверная подпись вебхука")
            return web.Response(status=403)

        try:
            body_str = body.decode('utf-8')
            update = json.loads(body_str)
        except (UnicodeDecodeError, json.JSONDecodeError):
            logging.warning("❌ Невалидный JSON в вебхуке")
            return web.Response(status=400)

        update_type = update.get('update_type')
        logging.info(f"🔍 Тип обновления: {update_type}")
     
        if update_type == 'invoice_paid':
            invoice = update.get('payload') or {}
            invoice_id = invoice.get('invoice_id')
         
            logging.info(f"💰 Инвойс оплачен: ID {invoice_id}")

            try:
                payload = json.loads(invoice.get('payload', '{}'))
            except json.JSONDecodeError:
                logging.warning("❌ Невалидный payload в invoice")
                return web.Response(status=400)

            user_id = payload.get('user_id')
            plan = payload.get('plan')
            if not isinstance(user_id, int) or plan not in PLANS:
                logging.warning(f"❌ Некорректные данные платежа: user_id={user_id}, plan={plan}")
                return web.Response(status=400)

            days = PLANS[plan]['days']
         
            logging.info(f"✅ Оплата получена: user_id={user_id}, plan={plan}, days={days}")
         
            now = datetime.now(timezone.utc)
            expiration = now + timedelta(days=days) if days < 365*100 else None
            exp_str = expiration.isoformat() if expiration else None
         
            cursor.execute("UPDATE users SET subscription_expiration = ? WHERE user_id = ?", (exp_str, user_id))
            conn.commit()
         
            await bot.send_message(user_id,
                f"✅ Подписка активирована на {days} дней!\n"
                f"Теперь вы можете использовать все функции чекера."
            )
            logging.info(f"🎉 Подписка активирована для user_id {user_id}")
         
        return web.Response(status=200)
    except Exception as e:
        logging.error(f"❌ Ошибка вебхука: {e}")
        logging.error(traceback.format_exc())
        return web.Response(status=500)

app.router.add_get('/{filename}', handle_stats)
app.router.add_post('/crypto_webhook', handle_crypto_webhook)

def open_firewall_port(port: int):
    """
    Открывает входящий TCP-порт в брандмауэре Windows (best-effort).
    Требует прав администратора. Если прав нет — пишет инструкцию в лог.
    """
    import platform
    import subprocess
    if platform.system() != 'Windows':
        return
    rule_name = f"RobloxChecker_Stats_{port}"
    try:
        # Удаляем старое правило (если было) и создаём заново — идемпотентно
        subprocess.run(
            ['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={rule_name}'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        result = subprocess.run(
            ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
             f'name={rule_name}', 'dir=in', 'action=allow',
             'protocol=TCP', f'localport={port}'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            logging.info(f"🔓 Firewall: порт {port}/TCP открыт (правило '{rule_name}')")
        else:
            logging.warning(
                f"⚠️ Не удалось открыть порт {port} в фаерволе (нужны права администратора). "
                f"Открой вручную в PowerShell от админа:\n"
                f"netsh advfirewall firewall add rule name={rule_name} dir=in action=allow protocol=TCP localport={port}"
            )
    except Exception as e:
        logging.warning(f"⚠️ Ошибка открытия порта в фаерволе: {e}")

async def get_public_ip():
    """Определяет внешний (публичный) IP машины через внешние сервисы."""
    services = ['https://api.ipify.org', 'https://ifconfig.me/ip', 'https://icanhazip.com']
    for url in services:
        try:
            async with ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        ip = (await resp.text()).strip()
                        if ip and len(ip) <= 45:  # отсекаем мусор
                            return ip
        except Exception:
            continue
    return None

async def start_stats_server():
    import config
    port = 8001
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"🌐 Сервер отчётов слушает 0.0.0.0:{port}")

    # Открываем порт в брандмауэре Windows
    open_firewall_port(port)

    # Определяем хост для ссылок: ручной override (config.STATS_HOST) или внешний IP
    host = getattr(config, 'STATS_HOST', None)
    if not host:
        host = await get_public_ip()

    if host:
        config.stats_public_url = f"http://{host}:{port}"
        logging.info(f"📊 URL отчётов: {config.stats_public_url}")
        logging.info(f"   ⚠️ Для доступа из интернета пробрось порт {port} на роутере (внешний {port} → этот ПК:{port})")
    else:
        logging.warning(
            "⚠️ Не удалось определить публичный IP. Отчёты могут быть недоступны.\n"
            "   Задай IP вручную в config.py: STATS_HOST = \"ТВОЙ_ВНЕШНИЙ_IP\""
        )
    return config.stats_public_url

def save_stats_html(filename: str, html_content: str) -> bool:
    try:
        filepath = _resolve_temp_file_path(filename, {'.html'}, require_exists=False)
        if not filepath:
            logging.error(f"Unsafe stats filename rejected: {filename}")
            return False

        temp_root = os.path.realpath(TEMP_DIR)
        os.makedirs(temp_root, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False, dir=temp_root, suffix='.tmp') as tf:
            tf.write(html_content)
            temp_path = tf.name
        os.replace(temp_path, filepath)
        logging.info(f"HTML saved: {filepath}")
        return True
    except Exception as e:
        logging.error(f"Error saving HTML: {str(e)}")
        return False

def get_stats_url(filename: str) -> str:
    import config
    safe_name = os.path.basename(str(filename or ""))
    return f"{config.stats_public_url}/{safe_name}"


import os
import logging
import traceback
from typing import List

def load_proxies(file_path: str) -> List[str]:
    """
    Загружает прокси из файла.
    Поддерживаемые форматы строк:
    1. ip:http_port:login:password
       Пример: 192.168.1.1:8080:user123:pass456
    
    2. ip:port@login:password  
       Пример: 196.19.10.63:8000@jYVpxc:CeANUv
    
    3. ip:port@login:password с дополнительными параметрами
       Пример: 196.19.11.136:8000@hpCMTz:5yGTpp
    """
    proxies = []
    try:
        if not os.path.exists(file_path):
            logging.error(f"Файл прокси не найден: {file_path}")
            return []

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Определяем формат строки и парсим
                proxy_url = None
                
                # Формат 1: ip:port:login:password (через двоеточия)
                if line.count(':') == 3 and '@' not in line:
                    parts = line.split(':')
                    ip, port, username, password = parts
                    
                    # Проверка порта на валидность
                    try:
                        port_num = int(port)
                        if not (1 <= port_num <= 65535):
                            raise ValueError
                    except ValueError:
                        logging.warning(f"Прокси строка {line_num}: неверный порт '{port}' — пропущено: {line}")
                        continue
                    
                    proxy_url = f"http://{username}:{password}@{ip}:{port}"
                
                # Формат 2 и 3: ip:port@login:password (с возможными дополнительными символами после пароля)
                elif '@' in line:
                    # Разделяем на адрес и часть с авторизацией
                    address_part, auth_part = line.split('@', 1)
                    
                    # Проверяем, что в auth_part есть двоеточие
                    if ':' not in auth_part:
                        logging.warning(f"Прокси строка {line_num}: неверный формат авторизации — пропущено: {line}")
                        continue
                    
                    # Разделяем логин и пароль (берем только первые две части, остальное игнорируем)
                    auth_parts = auth_part.split(':', 1)
                    username, password = auth_parts[0], auth_parts[1]
                    
                    # Проверяем, что в address_part есть двоеточие (ip:port)
                    if ':' not in address_part:
                        logging.warning(f"Прокси строка {line_num}: неверный формат адреса — пропущено: {line}")
                        continue
                    
                    ip, port = address_part.split(':', 1)
                    
                    # Проверка порта на валидность
                    try:
                        port_num = int(port)
                        if not (1 <= port_num <= 65535):
                            raise ValueError
                    except ValueError:
                        logging.warning(f"Прокси строка {line_num}: неверный порт '{port}' — пропущено: {line}")
                        continue
                    
                    proxy_url = f"http://{username}:{password}@{ip}:{port}"
                
                else:
                    logging.warning(f"Прокси строка {line_num}: неподдерживаемый формат — пропущено: {line}")
                    continue

                if proxy_url:
                    proxies.append(proxy_url)
                    logging.debug(f"Загружен прокси: {proxy_url}")

        logging.info(f"Успешно загружено {len(proxies)} прокси из {file_path}")
        return proxies

    except Exception as e:
        logging.error(f"Ошибка при загрузке прокси из {file_path}: {e}")
        logging.error(traceback.format_exc())
        return []

def cleanup_old_html_files(max_age_hours=24):
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)
        current_time = datetime.now().timestamp()
        for filename in os.listdir(TEMP_DIR):
            filepath = _resolve_temp_file_path(filename, _ALLOWED_STATS_EXTS, require_exists=True)
            if not filepath:
                continue
            file_time = os.path.getmtime(filepath)
            if current_time - file_time > max_age_hours * 3600:
                os.remove(filepath)
                logging.info(f"Removed old file: {filename}")
    except Exception as e:
        logging.error(f"Error cleaning up files: {str(e)}")