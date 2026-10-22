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

async def handle_health(request):
    return web.Response(text="OK", content_type="text/plain")

async def handle_root(request):
    return web.Response(text="228 Checker stats server running. Use /{uuid}.html for reports.", content_type="text/plain")

async def handle_stats(request):
    filename = request.match_info.get('filename', '')
    # health/root уже обработаны отдельными роутами, но на всякий случай
    if filename in ("health", ""):
        return web.Response(text="OK", content_type="text/plain")
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

app.router.add_get('/health', handle_health)
app.router.add_get('/', handle_root)
app.router.add_get('/{filename}', handle_stats)
app.router.add_post('/crypto_webhook', handle_crypto_webhook)

def open_firewall_port(port: int):
    """
    Открывает входящий TCP-порт в брандмауэре (Windows + Linux best-effort).
    Требует прав администратора/root. Если прав нет — пишет инструкцию в лог.
    """
    import platform
    import subprocess
    import shutil
    system = platform.system()
    rule_name = f"RobloxChecker_Stats_{port}"

    # --- Windows ---
    if system == 'Windows':
        try:
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
                logging.info(f"🔓 Firewall (Windows): порт {port}/TCP открыт (правило '{rule_name}')")
            else:
                err = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ''
                logging.warning(
                    f"⚠️ Не удалось открыть порт {port} в фаерволе Windows (нужны права администратора). {err.strip()} "
                    f"Открой вручную в PowerShell от админа: netsh advfirewall firewall add rule name={rule_name} dir=in action=allow protocol=TCP localport={port}"
                )
            return
        except Exception as e:
            logging.warning(f"⚠️ Ошибка открытия порта в фаерволе Windows: {e}")
            return

    # --- Linux ---
    if system == 'Linux':
        # 1) ufw
        if shutil.which('ufw'):
            try:
                # ufw может спросить пароль — делаем best-effort без интерактива
                result = subprocess.run(['ufw', 'allow', f'{port}/tcp'],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                if result.returncode == 0:
                    logging.info(f"🔓 Firewall (ufw): разрешён порт {port}/tcp")
                    subprocess.run(['ufw', 'reload'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                    return
                else:
                    logging.info(f"ℹ️ ufw allow {port} не выполнен (нужен root): {result.stderr.strip()[:200]}")
            except Exception as e:
                logging.debug(f"ufw check failed: {e}")
        # 2) firewalld
        if shutil.which('firewall-cmd'):
            try:
                result = subprocess.run(['firewall-cmd', '--permanent', f'--add-port={port}/tcp'],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                if result.returncode == 0:
                    subprocess.run(['firewall-cmd', '--reload'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                    logging.info(f"🔓 Firewall (firewalld): открыт порт {port}/tcp")
                    return
            except Exception as e:
                logging.debug(f"firewalld check failed: {e}")
        # 3) iptables (требует root, пишем инструкцию)
        logging.info(f"ℹ️ Linux: проверь внешний фаервол вручную: sudo ufw allow {port}/tcp  ИЛИ  sudo iptables -I INPUT -p tcp --dport {port} -j ACCEPT")
        # Проверяем, слушает ли вообще порт
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(('127.0.0.1', port))
            s.close()
            logging.info(f"✅ Порт {port} уже слушается локально")
        except Exception:
            logging.warning(f"⚠️ Порт {port} не отвечает локально — сервер может не запуститься (занят или нет прав)")
        return

    logging.info(f"ℹ️ Авто-открытие фаервола для {system} не поддерживается — открой порт {port}/TCP вручную")

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
    import os as _os
    # Bothost.ru и др. хостинги прокидывают порт через env PORT/WEB_PORT — уважаем его
    # Если PORT задан (например 3000), слушаем на нём, иначе 8001 для локальной/десктоп отладки
    port = 8001
    for env_name in ("PORT", "WEB_PORT", "SERVER_PORT", "APP_PORT"):
        env_val = _os.getenv(env_name)
        if env_val and env_val.isdigit():
            port = int(env_val)
            logging.info(f"🔧 Порт из env {env_name}={port} (bothost.ru / хостинг)")
            break
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logging.info(f"🌐 Сервер отчётов слушает 0.0.0.0:{port}")
    except OSError as e:
        logging.error(f"❌ Не удалось запустить сервер отчётов на порту {port}: {e}")
        logging.error(f"   Проверь, не занят ли порт: Windows: netstat -ano | findstr :{port}  Linux: sudo ss -tulpn | grep {port}")
        # Пытаемся всё равно продолжить, но ссылки будут битые
        return config.stats_public_url

    # Открываем порт в брандмауэре (Windows / Linux) — на bothost.ru не нужно, но безвредно
    open_firewall_port(port)

    # Определяем хост для ссылок: ручной override (config.STATS_HOST) / env / внешний IP
    # Если STATS_HOST = None или пусто — авто-определяем, но на bothost.ru нужно задать домен
    host = getattr(config, 'STATS_HOST', None)
    # Также поддерживаем env для bothost.ru без правки config.py: STATS_HOST, BOTHOST_HOST, PUBLIC_HOST
    for env_name in ("STATS_HOST", "BOTHOST_HOST", "PUBLIC_HOST", "DOMAIN", "HOST"):
        env_host = _os.getenv(env_name)
        if env_host and env_host.strip():
            if not host:  # env имеет приоритет только если config не задан — не перетираем ручной домен
                host = env_host.strip()
                logging.info(f"🔧 Хост из env {env_name}={host}")
                break
    if isinstance(host, str):
        host = host.strip()
        if not host:
            host = None
    if not host:
        detected = await get_public_ip()
        if detected:
            host = detected
            logging.info(f"🔍 Авто-определён внешний IP: {host}")
        else:
            host = None

    if host:
        # Хост может быть уже полным URL (https://...), IP, или домен bothost.tech
        host_low = host.lower()
        if host.startswith("http://") or host.startswith("https://"):
            # Полный URL — уважам как есть (важно для bothost с https и кастомных доменов)
            base = host.rstrip("/")
            config.stats_public_url = base
            # Если URL без порта и хост — IP/домашняя, подскажем про порт
            if ":" not in base.split("/")[-1] and port != 80 and port != 443:
                logging.info(f"ℹ️ Используется полный URL {base} без явного порта — убедись, что реверс-прокси/хостинг прокидывает на {port}")
        elif "bothost" in host_low:
            # Bothost: даёт https://xxx.bothost.tech и сам терминирует SSL на своём балансире → внешний порт не нужен
            # Локально всё ещё слушаем на $PORT, но наружу отдаём https без порта
            clean = host.replace("https://", "").replace("http://", "").strip("/").split("/")[0]
            config.stats_public_url = f"https://{clean}"
            logging.info(f"📊 URL отчётов (bothost.ru): {config.stats_public_url}")
            logging.info(f"   ℹ️ На bothost.ru убедись: в панели включён Веб-интерфейс, выдан домен {clean}, порт панели = {port} (совпадает с логом выше)")
            # Локальная проверка (127.0.0.1:port) — публичный домен проверить не можем на старте
            try:
                import socket
                with socket.create_connection(("127.0.0.1", port), timeout=2):
                    logging.info(f"✅ Локальная проверка: 127.0.0.1:{port} доступен")
            except Exception as e:
                logging.warning(f"⚠️ Локальная проверка 127.0.0.1:{port} не прошла: {e}")
            return config.stats_public_url
        else:
            # Обычный IP или свой домен (mydomain.com)
            # Если домен без IP — считаем что DNS A-запись уже настроена и порт открыт
            config.stats_public_url = f"http://{host}:{port}"
            # Для домена с HTTPS (если пользователь прокинул через Nginx/Cloudflare) — подсказка
            if "." in host and not host.replace(".", "").replace("-", "").isdigit():
                logging.info(f"📊 URL отчётов (домен): {config.stats_public_url}")
                logging.info(f"   ℹ️ Для своего домена: 1) A-запись → {await get_public_ip() or 'IP_ХОСТА'}, 2) порт {port} открыт (ufw/iptables), 3) для https без :{port} настрой Nginx: proxy_pass http://127.0.0.1:{port}")
            else:
                logging.info(f"📊 URL отчётов: {config.stats_public_url}")
        # Если хост — приватный (192.168.x, 10.x, 172.16.x) — сразу предупреждаем
        is_private = host.startswith(('192.168.', '10.', '172.')) or host in ('127.0.0.1', 'localhost')
        if is_private:
            logging.warning(
                f"⚠️ STATS_HOST={host} — это приватный IP, из интернета по нему не зайти! "
                f"Укажи публичный IP в config.py: STATS_HOST = \"ТВОЙ_ПУБЛИЧНЫЙ_IP\" или оставь None для авто-определения. "
                f"Для домашнего ПК нужен проброс порта {port} на роутере."
            )
        else:
            if "bothost" not in host_low:  # для bothost уже вывели отдельные подсказки выше
                logging.info(f"   ℹ️ Если отчёт не открывается (ERR_CONNECTION_REFUSED) — проверь: 1) фаервол Windows/Linux разрешил {port}/TCP, "
                             f"2) на роутере проброшен порт {port} (внешний {port} → этот ПК:{port}), 3) провайдер не блокирует входящие. "
                             f"Для bothost.ru: включи Веб-интерфейс и укажи выданный домен в STATS_HOST, бот сам подхватит PORT. "
                             f"Временный обход: бот также отправит HTML-файл напрямую, если веб-ссылка недоступна.")
        # Локальная проверка доступности (127.0.0.1)
        try:
            import socket
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                logging.info(f"✅ Локальная проверка: 127.0.0.1:{port} доступен")
        except Exception as e:
            logging.warning(f"⚠️ Локальная проверка 127.0.0.1:{port} не прошла: {e}")
    else:
        logging.warning(
            "⚠️ Не удалось определить публичный IP. Веб-отчёты будут недоступны по внешней ссылке.\n"
            "   Задай IP/домен вручную в config.py: STATS_HOST = \"ТВОЙ_IP_ИЛИ_ДОМЕН\"  или проверь интернет."
        )
    return config.stats_public_url

async def check_stats_accessible(url: str, timeout: float = 3.0) -> bool:
    """Проверяет, открывается ли URL отчётов извне (best-effort)."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                return resp.status in (200, 304)
    except Exception:
        return False

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
import urllib.parse
from typing import List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Универсальный парсер прокси
# Поддерживает:
#   ip:port
#   ip:port:login:password
#   login:password:ip:port
#   ip:port@login:password              (инвертированный, как в старом файле)
#   login:password@ip:port               (стандарт)
#   http://login:password@ip:port
#   http://ip:port@login:password
#   socks5://login:password@ip:port
#   и те же варианты с уже готовым URL (http://user:pass@host:port)
# Пароль/логин с символами : @ / ? # кодируются через quote
# ─────────────────────────────────────────────────────────────────────────────

_VALID_SCHEMES = {"http", "https", "socks5", "socks5h", "socks4", "socks4a"}

def _is_valid_port(port_str: str) -> bool:
    if not port_str or not port_str.isdigit():
        return False
    try:
        p = int(port_str)
        return 1 <= p <= 65535
    except ValueError:
        return False


def _is_hostport(s: str) -> bool:
    """host:port где port — число 1-65535, host не пустой и без @/пробела"""
    if not s or ":" not in s:
        return False
    # IPv6 в скобках: [::1]:8080
    s = s.strip()
    if s.startswith("["):
        end = s.find("]")
        if end == -1:
            return False
        host = s[1:end]
        rest = s[end + 1:]
        if not rest.startswith(":"):
            return False
        port_str = rest[1:]
        return bool(host) and _is_valid_port(port_str)
    # обычный host:port — берём последний ':'
    if " " in s or "/" in s or "@" in s:
        return False
    host, port_str = s.rsplit(":", 1)
    if not host or not port_str:
        return False
    if ":" in host:
        return False
    return _is_valid_port(port_str)


def _is_creds(s: str) -> bool:
    """login:password — содержит ':', не является host:port, логин не пустой"""
    if not s or ":" not in s:
        return False
    if _is_hostport(s):
        return False
    user, _ = s.split(":", 1)
    if not user or " " in user or "@" in user:
        return False
    return True


def _hostport_split(s: str) -> Tuple[str, str]:
    s = s.strip()
    if s.startswith("["):
        end = s.find("]")
        host = s[1:end]
        port = s[end + 2:] if s[end + 1] == ":" else s.split(":")[-1]
        # более надёжно:
        port = s.rsplit(":", 1)[-1]
        return host, port
    host, port = s.rsplit(":", 1)
    return host.strip(), port.strip()


def _build_url(scheme: str, host: str, port: str, user: Optional[str] = None, pwd: Optional[str] = None) -> Optional[str]:
    host = host.strip()
    port = port.strip()
    if not host or not _is_valid_port(port):
        return None
    # IPv6 без скобок нужно обернуть
    host_fmt = host
    if ":" in host and not host.startswith("["):
        host_fmt = f"[{host}]"
    if user is not None:
        user_q = urllib.parse.quote(user, safe="")
        pwd_q = urllib.parse.quote(pwd or "", safe="")
        if pwd is not None and pwd != "":
            return f"{scheme}://{user_q}:{pwd_q}@{host_fmt}:{port}"
        elif pwd == "":
            return f"{scheme}://{user_q}@{host_fmt}:{port}"
        else:
            return f"{scheme}://{user_q}:{pwd_q}@{host_fmt}:{port}"
    else:
        return f"{scheme}://{host_fmt}:{port}"


def _parse_with_at(line: str, scheme: str) -> Optional[str]:
    """Строка содержит '@' — пробуем все разбиения по '@' (для пароля с '@')."""
    parts = line.split("@")
    # перебор по каждому возможному @ как разделителю
    for i in range(1, len(parts)):
        left = "@".join(parts[:i])
        right = "@".join(parts[i:])
        left = left.strip()
        right = right.strip()
        if not left or not right:
            continue
        # случай 1: left = host:port , right = user:pass
        if _is_hostport(left) and _is_creds(right):
            host, port = _hostport_split(left)
            user, pwd = right.split(":", 1)
            url = _build_url(scheme, host, port, user, pwd)
            if url:
                return url
        # случай 2: left = user:pass , right = host:port (стандарт)
        if _is_creds(left) and _is_hostport(right):
            user, pwd = left.split(":", 1)
            host, port = _hostport_split(right)
            url = _build_url(scheme, host, port, user, pwd)
            if url:
                return url
    return None


def _parse_without_at(line: str, scheme: str) -> Optional[str]:
    """Строка без '@' — host:port или с credentials через ':'"""
    line = line.strip()
    if not line:
        return None
    # простой host:port
    if _is_hostport(line) and line.count(":") == 1:
        # для IPv6 будет больше, но считаем hostport
        host, port = _hostport_split(line)
        return _build_url(scheme, host, port, None, None)
    # частый случай: одно ':' но это не hostport? тогда не прокси
    parts = line.split(":")
    if len(parts) == 2:
        # host:port — уже проверено выше, но если port не валиден — отклоним
        if _is_hostport(line):
            host, port = _hostport_split(line)
            return _build_url(scheme, host, port, None, None)
        return None
    if len(parts) >= 4:
        # вариант A: host:port:user:pass  (порт на 2-й позиции)
        host_a = parts[0].strip()
        port_a = parts[1].strip()
        if host_a and _is_valid_port(port_a):
            user_a = parts[2].strip()
            pwd_a = ":".join(parts[3:])  # пароль может содержать ':'
            if user_a:
                url = _build_url(scheme, host_a, port_a, user_a, pwd_a)
                if url:
                    return url
        # вариант B: user:pass:host:port  (порт в конце)
        host_b = parts[-2].strip()
        port_b = parts[-1].strip()
        if host_b and _is_valid_port(port_b):
            # user — первый элемент, pass — всё между 1 и -2
            if len(parts) == 4:
                user_b = parts[0].strip()
                pwd_b = parts[1].strip()
                if user_b:
                    url = _build_url(scheme, host_b, port_b, user_b, pwd_b)
                    if url:
                        return url
            elif len(parts) > 4:
                user_b = parts[0].strip()
                pwd_b = ":".join(parts[1:-2])
                if user_b:
                    url = _build_url(scheme, host_b, port_b, user_b, pwd_b)
                    if url:
                        return url
    # 3 части — неоднозначно, пробуем оба как выше с пустым паролем? пропускаем
    return None


def _parse_fallback_at_in_password(line: str, scheme: str) -> Optional[str]:
    """
    Фолбек для случаев когда пароль содержит '@' но формат без '@' (ip:port:user:pass).
    Пример: 192.168.1.1:8080:user:pa$$w@rd  → host:port в начале, pass с @.
            user:pa@ss:1.1.1.1:8080         → host:port в конце, pass с @.
    """
    # Попытка 1: host:port в начале → "host:port:user:pass_with_@"
    # Разбиваем максимум на 3 части: host, port, остаток (user:pass)
    try:
        parts = line.split(":", 2)
        if len(parts) == 3:
            host_cand = parts[0].strip()
            port_cand = parts[1].strip()
            rest = parts[2]
            cand_hp = f"{host_cand}:{port_cand}"
            if host_cand and _is_valid_port(port_cand) and _is_hostport(cand_hp) and ":" in rest:
                user, pwd = rest.split(":", 1)
                if user:
                    url = _build_url(scheme, host_cand, port_cand, user, pwd)
                    if url:
                        return url
    except Exception:
        pass
    # Попытка 2: host:port в конце → "user:pass_with_@:host:port"
    # Ищем трейлинговый host:port через regex
    try:
        m = re.search(r'([\w\.\-]+|\[[^\]]+\]):(\d+)\s*$', line)
        if m:
            hostport = m.group(0).strip()
            if _is_hostport(hostport):
                # префикс до hostport (без последнего ':host:port')
                prefix = line[: len(line) - len(hostport)].rstrip(":")
                if ":" in prefix:
                    user, pwd = prefix.split(":", 1)
                    if user:
                        host, port = _hostport_split(hostport)
                        url = _build_url(scheme, host, port, user, pwd)
                        if url:
                            return url
    except Exception:
        pass
    return None


def parse_proxy_line(raw_line: str) -> Optional[str]:
    """
    Парсит одну строку прокси в нормализованный URL.
    Возвращает None если строка пустая/комментарий/невалидна.
    """
    if not isinstance(raw_line, str):
        return None
    orig = raw_line.strip()
    if not orig or orig.startswith("#") or orig.startswith("//"):
        return None

    scheme = "http"
    line = orig
    if "://" in line:
        scheme_part, rest = line.split("://", 1)
        scheme_low = scheme_part.lower().strip()
        if scheme_low in _VALID_SCHEMES:
            scheme = scheme_low
            line = rest
        elif re.match(r"^[a-z0-9]+$", scheme_low):
            # неизвестная но похожая на схему — считаем http
            scheme = "http"
            line = rest
        # иначе оставляем как есть (напр. "user:pass://host" — маловероятно)
        line = line.strip().lstrip("/")

    line = line.strip().rstrip("/")
    # убираем пробелы внутри (прокси не содержат пробелов)
    line = re.sub(r"\s+", "", line)
    if not line:
        return None

    if "@" in line:
        res = _parse_with_at(line, scheme)
        if res:
            return res
        # фолбек: пароль содержит '@' но формат ip:port:user:pass
        fb = _parse_fallback_at_in_password(line, scheme)
        if fb:
            return fb
        return None
    else:
        return _parse_without_at(line, scheme)


def get_proxy_aiohttp_params(proxy_url: Optional[str]) -> dict:
    """
    Возвращает kwargs для aiohttp: {"proxy": clean_url, "proxy_auth": BasicAuth}.
    Критично для 407: aiohttp в некоторых версиях не берёт auth из URL,
    нужно передавать proxy_auth отдельно.
    Поддерживает http/https/socks5 (для socks5 нужен aiohttp_socks).
    """
    if not proxy_url:
        return {}
    try:
        import aiohttp
        parsed = urllib.parse.urlparse(proxy_url)
        scheme = (parsed.scheme or "http").lower()
        # webshare free — всегда http, но если socks5 указан — оставляем как есть
        # Для socks5 aiohttp нужен ProxyConnector, но пока отдаём как есть, cookie_processor попробует fallback
        if scheme in ("socks5", "socks5h", "socks4", "socks4a"):
            # Для SOCKS aiohttp_socks нужен отдельный коннектор, но proxy_auth всё равно нужен
            if parsed.username:
                user = urllib.parse.unquote(parsed.username)
                pwd = urllib.parse.unquote(parsed.password or "")
                auth = aiohttp.BasicAuth(user, pwd)
                return {"proxy": proxy_url, "proxy_auth": auth, "_is_socks": True}
            return {"proxy": proxy_url, "_is_socks": True}

        if parsed.username:
            user = urllib.parse.unquote(parsed.username)
            pwd = urllib.parse.unquote(parsed.password or "")
            auth = aiohttp.BasicAuth(user, pwd)
            host = parsed.hostname or ""
            is_ipv6 = ":" in host and not host.startswith("[")
            had_brackets = "[" in (proxy_url or "")
            if is_ipv6:
                host = f"[{host}]"
            port = parsed.port
            clean = f"{scheme}://{host}:{port}" if port else f"{scheme}://{host}"
            return {"proxy": clean, "proxy_auth": auth}
        else:
            return {"proxy": proxy_url}
    except Exception as e:
        logging.debug(f"get_proxy_aiohttp_params failed for {proxy_url[:40]}: {e}")
        return {"proxy": proxy_url}


def detect_proxy_type(proxy_url: str) -> str:
    """Определяет тип прокси для webshare: http или socks5."""
    if not proxy_url:
        return "direct"
    low = proxy_url.lower()
    if low.startswith("socks5") or low.startswith("socks4"):
        return "socks"
    # webshare free — http, но если 407 — возможно socks
    return "http"


async def test_proxy_connectivity(proxy_url: str, timeout: int = 8) -> dict:
    """
    Тестирует прокси через httpbin/ip и roblox, возвращает статус.
    Используется для диагностики 407 и определения типа прокси (webshare free).
    """
    import asyncio, aiohttp, ssl, time
    result = {"proxy": _mask_proxy(proxy_url), "ok": False, "type": detect_proxy_type(proxy_url), "error": None, "latency": None}
    # Подготавливаем SSL контекст без проверки (для тестов)
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    except Exception:
        ctx = None
    # Тестовые URL: сначала httpbin, потом roblox
    test_urls = ["https://api.ipify.org?format=json", "https://www.roblox.com/my/settings/json"]
    proxy_params = get_proxy_aiohttp_params(proxy_url)
    is_socks = proxy_params.pop("_is_socks", False)
    # Если SOCKS — пробуем через aiohttp_socks
    connector = None
    if is_socks:
        try:
            from aiohttp_socks import ProxyConnector
            connector = ProxyConnector.from_url(proxy_url, ssl=ctx)
            # Для SOCKS proxy передаётся через connector, а не proxy param
            proxy_params = {}
        except ImportError:
            result["error"] = "aiohttp_socks не установлен (pip install aiohttp_socks)"
            return result
        except Exception as e:
            result["error"] = f"socks connector failed: {e}"
            return result
    else:
        connector = aiohttp.TCPConnector(ssl=ctx) if ctx else None

    start = time.time()
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            for url in test_urls:
                try:
                    async with session.get(url, **proxy_params, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                        if resp.status in (200, 401, 403):  # 401 для роблокса без куки — нормально, прокси работает
                            result["ok"] = True
                            result["latency"] = round((time.time() - start)*1000)
                            result["error"] = f"HTTP {resp.status} ({url})"
                            return result
                        elif resp.status == 407:
                            result["error"] = "407 Proxy Auth Failed — неверный логин/пароль или IP не в вайтлисте webshare"
                            return result
                        else:
                            result["error"] = f"HTTP {resp.status}"
                except Exception as e:
                    err = str(e).lower()
                    if "407" in err or "proxy authentication" in err:
                        result["error"] = "407 Proxy Auth Failed"
                        return result
                    # пробуем следующий URL
                    continue
            result["error"] = "timeout or connection failed"
            return result
    except Exception as e:
        result["error"] = str(e)[:120]
        return result
    finally:
        result["latency"] = round((time.time() - start)*1000) if result["latency"] is None else result["latency"]
    return result


def _mask_proxy(proxy_url: str) -> str:
    """Маскирует пароль для логов: http://user:***@host:port"""
    try:
        if "@" not in proxy_url:
            return proxy_url
        # scheme://creds@host
        scheme, rest = proxy_url.split("://", 1)
        creds, hostport = rest.rsplit("@", 1)
        if ":" in creds:
            user, _ = creds.split(":", 1)
            return f"{scheme}://{user}:***@{hostport}"
        else:
            return f"{scheme}://***@{hostport}"
    except Exception:
        return proxy_url[:30] + "***"


def _extract_hostport_key(proxy_url: str) -> str:
    """Возвращает host:port ключ для дедупликации (без credentials)."""
    try:
        parsed = urllib.parse.urlparse(proxy_url)
        host = parsed.hostname or ""
        port = parsed.port
        return f"{host}:{port}" if port else host
    except Exception:
        return proxy_url

def load_proxies(file_path: str) -> List[str]:
    """
    Загружает прокси из файла и нормализует каждый в URL вида
    http://login:pass@host:port (логин/пароль URL-encoded).

    Поддерживаемые входные форматы:
      ip:port
      ip:port:login:password
      login:password:ip:port
      ip:port@login:password
      login:password@ip:port
      http://login:password@ip:port
      http://ip:port@login:password
      socks5://login:password@ip:port
    Также:
      - пароль/логин могут содержать : @ и другие спецсимволы (кодируются)
      - строки с пробелами, пустые, комментарии # пропускаются
      - дубликаты удаляются (сохраняется порядок)
      - webshare free: дедупликация по host:port с предупреждением (одинаковые IP с разными логинами = 90% 407)
    """
    proxies: List[str] = []
    seen = set()
    seen_hostport = set()
    dup_ip_warned = False
    try:
        if not os.path.exists(file_path):
            logging.error(f"Файл прокси не найден: {file_path}")
            return []

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, raw in enumerate(f, 1):
                # убираем BOM и пробелы
                line = raw.strip().lstrip("\ufeff")
                if not line or line.startswith("#") or line.startswith("//"):
                    continue

                proxy_url = parse_proxy_line(line)
                if not proxy_url:
                    logging.warning(f"Прокси строка {line_num}: неподдерживаемый формат — пропущено: {raw.strip()[:80]}")
                    continue

                if proxy_url in seen:
                    logging.debug(f"Прокси строка {line_num}: дубликат — пропущено: {_mask_proxy(proxy_url)}")
                    continue
                # Дедупликация по host:port (webshare free часто дублируют IP с разными кредами -> 407)
                hostport_key = _extract_hostport_key(proxy_url)
                if hostport_key in seen_hostport:
                    if not dup_ip_warned:
                        logging.warning(f"⚠️ Обнаружены дубликаты IP:port с разными логинами (например {hostport_key}) — webshare free даёт 10 уникальных IP, а у вас {len(seen)}+ строк. Дубликаты пропускаются, иначе 407.")
                        dup_ip_warned = True
                    logging.debug(f"Прокси строка {line_num}: дубликат IP:port {hostport_key} — пропущено: {_mask_proxy(proxy_url)}")
                    continue
                seen.add(proxy_url)
                seen_hostport.add(hostport_key)
                proxies.append(proxy_url)
                logging.debug(f"Загружен прокси: {_mask_proxy(proxy_url)}")

        # webshare free диагностика: если прокси много, но уникальных IP мало
        if len(proxies) < len(seen) // 2:
            logging.warning(f"⚠️ Загружено {len(proxies)} уникальных прокси из {len(seen)} строк — много дубликатов IP:port. Проверь proxies.txt: webshare free обычно 10 IP на аккаунт, не накручивай кредами.")

        logging.info(f"Успешно загружено {len(proxies)} прокси из {file_path} (уникальных IP:port: {len(seen_hostport)})")
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