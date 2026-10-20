import sqlite3
import json
from datetime import datetime, timezone, timedelta
import uuid
from config import DB_FILE, CHECK_PARAMS, GAMES, PLANS
import logging
import threading
from collections import defaultdict

moscow_tz = timezone(timedelta(hours=3))
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

# WAL mode и настройки для предотвращения lock'ов
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
conn.execute("PRAGMA busy_timeout=10000")  # 10 сек retry на locked

# Кэш времени последнего бонуса для каждого пользователя
_last_bonus_cache = {}
_cache_lock = threading.Lock()

def update_sponsor_channel_link(admin_id: int, channel_id: int, new_link: str):
    """Обновляет ссылку для спонсорского канала"""
    try:
        cursor.execute("""
            UPDATE sponsor_channels 
            SET channel_link = ?
            WHERE channel_id = ?
        """, (new_link, channel_id))
        conn.commit()
        return cursor.rowcount > 0, "✅ Ссылка обновлена"
    except Exception as e:
        logging.error(f"Ошибка обновления ссылки канала: {e}")
        return False, f"❌ Ошибка: {e}"
    
def add_days_to_all_active_subscribers(days: int) -> int:
    """
    Добавляет указанное количество дней ко всем активным подпискам.
    Пропускает пользователей с '0' или NULL в subscription_expiration.
    Возвращает количество обновленных пользователей.
    """
    now = datetime.now(moscow_tz).replace(tzinfo=None)
    updated_count = 0
    skipped_count = 0

    # Получаем всех пользователей у которых есть поле subscription_expiration
    cursor.execute("SELECT user_id, subscription_expiration FROM users WHERE subscription_expiration IS NOT NULL")
    rows = cursor.fetchall()

    for user_id, exp_str in rows:
        try:
            # Пропускаем если значение '0' или пустое
            if not exp_str or exp_str == '0' or exp_str.strip() == '':
                skipped_count += 1
                continue

            exp = datetime.fromisoformat(exp_str).replace(tzinfo=None)

            # Проверяем, активна ли подписка (не истекла)
            if exp > now:
                # Добавляем дни
                new_exp = exp + timedelta(days=days)
                cursor.execute(
                    "UPDATE users SET subscription_expiration = ? WHERE user_id = ?",
                    (new_exp.isoformat(), user_id)
                )
                updated_count += 1
            else:
                # Подписка истекла - пропускаем
                skipped_count += 1

        except (ValueError, TypeError) as e:
            # Если не удалось распарсить дату - пропускаем
            logging.warning(f"Некорректный формат даты для user_id {user_id}: {exp_str} - {e}")
            skipped_count += 1
            continue
        except Exception as e:
            logging.error(f"Ошибка обновления подписки для user_id {user_id}: {e}")
            skipped_count += 1
            continue

    conn.commit()
    logging.info(f"add_days_to_all_active_subscribers: обновлено {updated_count}, пропущено {skipped_count}")
    return updated_count


def safe_load_and_repair(user_id: int, column_name: str, json_str, default_dict: dict) -> dict:
    if not json_str:
        return default_dict
    try:
        if len(json_str) > 10 * 1024 * 1024:  # Лимит 10 МБ
            raise json.JSONDecodeError("Too large", json_str, 0)
        data = json.loads(json_str)
        if not isinstance(data, dict):
            raise json.JSONDecodeError("Not a dict", json_str, 0)
        return data
    except json.JSONDecodeError as e:
        logging.warning(f"Corrupted JSON in column '{column_name}' for user {user_id}: {json_str} → resetting to default")
        repaired_json = json.dumps(default_dict)
        cursor.execute(f"UPDATE users SET {column_name} = ? WHERE user_id = ?", (repaired_json, user_id))
        conn.commit()
        return default_dict


def check_and_create_columns():
    expected_tables = {
        'giveaways': [
            'id INTEGER PRIMARY KEY AUTOINCREMENT',
            'amount INTEGER NOT NULL',
            'end_date TEXT NOT NULL',
            'message_id INTEGER NOT NULL',
            'participants TEXT DEFAULT "[]"',
            'winner_id INTEGER DEFAULT NULL'
        ],
        'activation_keys': [
            'id INTEGER PRIMARY KEY AUTOINCREMENT',
            'key TEXT UNIQUE',
            'plan TEXT NOT NULL',
            'created_by INTEGER NOT NULL',
            'created_at TEXT NOT NULL',
            'used_by INTEGER',
            'used_at TEXT'
        ],
        'sponsor_channels': [
            'id INTEGER PRIMARY KEY AUTOINCREMENT',
            'channel_id INTEGER UNIQUE NOT NULL',
            'channel_link TEXT NOT NULL'
        ],
        'users': [
            'user_id INTEGER PRIMARY KEY',
            'selected_checks TEXT',
            'selected_ingame TEXT',
            'selected_badges TEXT',
            'selected_gamepasses TEXT',
            'selected_playtime TEXT',
            'last_bonus_claim TEXT',
            'registration_date TEXT',
            'subscription_expiration TEXT',
            'trial_claimed INTEGER DEFAULT 0',
            'referrer_id INTEGER',
            'ref_balance INTEGER DEFAULT 0',
            'output_format TEXT DEFAULT "zip"',
            'fresher_invalidate_old INTEGER DEFAULT 1',
            'language TEXT DEFAULT "ru"',
            'ad_broadcast_enabled INTEGER DEFAULT 1',
            'user_cookies_checked INTEGER DEFAULT 0',
            'user_cookies_freshed INTEGER DEFAULT 0'
        ],
        'global_stats': [
            'id INTEGER PRIMARY KEY',
            'total_donate INTEGER DEFAULT 0',
            'total_balance INTEGER DEFAULT 0',
            'total_pending INTEGER DEFAULT 0',
            'total_rap INTEGER DEFAULT 0',
            'total_groups_balance INTEGER DEFAULT 0',
            'total_cookies_checked INTEGER DEFAULT 0',
            'total_cookies_freshed INTEGER DEFAULT 0',
            'trial_enabled INTEGER DEFAULT 0',
            'total_sniped_balance INTEGER DEFAULT 0',
            'total_sniped_pending INTEGER DEFAULT 0'
        ],
        'custom_configs': [
            'id INTEGER PRIMARY KEY AUTOINCREMENT',
            'user_id INTEGER',
            'type TEXT',
            'name TEXT',
            'ids TEXT'
        ],
        'withdrawal_requests': [
            'id INTEGER PRIMARY KEY AUTOINCREMENT',
            'user_id INTEGER',
            'amount INTEGER',
            'status TEXT DEFAULT "pending"',
            'payout_link TEXT'
        ],
        'sniper_sessions': [
            'id INTEGER PRIMARY KEY AUTOINCREMENT',
            'user_id INTEGER',
            'name TEXT',
            'data TEXT',
            'threshold_balance INTEGER DEFAULT 100',
            'threshold_pending INTEGER DEFAULT 50',
            'active INTEGER DEFAULT 0',
            'total_sniped_balance INTEGER DEFAULT 0',
            'total_sniped_pending INTEGER DEFAULT 0',
            'cookie_count INTEGER DEFAULT 0',
            'created_at TEXT',
            'processing INTEGER DEFAULT 0'
        ],
        'badge_cache': [
            'id INTEGER PRIMARY KEY AUTOINCREMENT',
            'badge_id INTEGER UNIQUE',
            'name TEXT NOT NULL'
        ],
        'gamepass_cache': [
            'id INTEGER PRIMARY KEY AUTOINCREMENT',
            'gamepass_id INTEGER UNIQUE',
            'name TEXT NOT NULL'
        ],
        'user_game_overrides': {
            'columns': [
                'id INTEGER PRIMARY KEY AUTOINCREMENT',
                'user_id INTEGER',
                'short TEXT',
                'type TEXT',
                'name TEXT',
                'place_id INTEGER',
                'universe_id INTEGER'
            ],
            'constraints': [
                'UNIQUE(user_id, short, type)'
            ]
        },
        'check_logs': [
            'id INTEGER PRIMARY KEY AUTOINCREMENT',
            'user_id INTEGER',
            'timestamp TEXT',
            'cookie_count INTEGER'
        ],
    }

    # Сначала создаем все таблицы и добавляем недостающие колонки
    for table_name, definition in expected_tables.items():
        if isinstance(definition, list):
            columns = definition
            constraints = []
        else:
            columns = definition.get('columns', [])
            constraints = definition.get('constraints', [])

        # Проверяем существование таблицы
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = [column[1] for column in cursor.fetchall()]

        # Если таблицы нет - создаем
        if not existing_columns:
            all_defs = columns + constraints
            create_query = f"CREATE TABLE {table_name} ({', '.join(all_defs)})"
            cursor.execute(create_query)
            logging.info(f"Создана таблица {table_name}")
            continue

        # Добавляем недостающие колонки
        for column_def in columns:
            column_name = column_def.split(' ', 1)[0]
            if column_name not in existing_columns:
                alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column_def}"
                try:
                    cursor.execute(alter_query)
                    logging.info(f"Добавлена колонка {column_name} в {table_name}")
                except sqlite3.OperationalError as e:
                    logging.error(f"Ошибка добавления колонки {column_name} в {table_name}: {e}")

        # Создаем индексы для таблицы user_game_overrides
        if table_name == 'user_game_overrides' and constraints:
            index_name = f"idx_{table_name}_unique_user_short_type"
            cursor.execute(f"PRAGMA index_list({table_name})")
            existing_indexes = [row[1] for row in cursor.fetchall()]
            if index_name not in existing_indexes:
                cursor.execute(f"CREATE UNIQUE INDEX {index_name} ON {table_name}(user_id, short, type)")
                logging.info(f"Создан уникальный индекс {index_name} для {table_name}")

    # Специальная проверка для колонки last_bonus_claim
    try:
        cursor.execute("SELECT last_bonus_claim FROM users LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN last_bonus_claim TEXT")
            conn.commit()
            logging.info("✅ Добавлена колонка last_bonus_claim в таблицу users")
        except sqlite3.OperationalError as e:
            logging.error(f"Ошибка добавления колонки last_bonus_claim: {e}")

    # Специальная проверка для колонки ad_broadcast_enabled
    try:
        cursor.execute("SELECT ad_broadcast_enabled FROM users LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN ad_broadcast_enabled INTEGER DEFAULT 1")
            conn.commit()
            logging.info("✅ Добавлена колонка ad_broadcast_enabled в таблицу users")
        except sqlite3.OperationalError as e:
            logging.error(f"Ошибка добавления колонки ad_broadcast_enabled: {e}")

    # Добавляем недостающие колонки в sponsor_channels (если их нет)
    try:
        cursor.execute("PRAGMA table_info(sponsor_channels)")
        sponsor_columns = [col[1] for col in cursor.fetchall()]
        
        if 'added_by' not in sponsor_columns:
            cursor.execute("ALTER TABLE sponsor_channels ADD COLUMN added_by INTEGER")
            logging.info("✅ Добавлена колонка added_by в sponsor_channels")
        
        if 'updated_by' not in sponsor_columns:
            cursor.execute("ALTER TABLE sponsor_channels ADD COLUMN updated_by INTEGER")
            logging.info("✅ Добавлена колонка updated_by в sponsor_channels")
        
        if 'updated_at' not in sponsor_columns:
            cursor.execute("ALTER TABLE sponsor_channels ADD COLUMN updated_at TEXT")
            logging.info("✅ Добавлена колонка updated_at в sponsor_channels")
        
        conn.commit()
    except Exception as e:
        logging.error(f"Ошибка добавления колонок в sponsor_channels: {e}")

    # Создаем индексы для check_logs
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_check_logs_user_time ON check_logs(user_id, timestamp)")

    conn.commit()


check_and_create_columns()

cursor.execute('''INSERT OR IGNORE INTO global_stats (id) VALUES (1)''')
conn.commit()


# ==================== ФУНКЦИИ ДЛЯ ЯЗЫКА ====================
def get_user_language(user_id: int) -> str:
    """Возвращает язык пользователя (ru или en)"""
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0]:
        return row[0]
    return "ru"  # По умолчанию русский


def set_user_language(user_id: int, language: str):
    """Устанавливает язык пользователя"""
    if language not in ["ru", "en"]:
        language = "ru"
    cursor.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))
    conn.commit()


def get_user_settings(user_id: int) -> dict | None:
    cursor.execute("""
        SELECT
            selected_checks,
            selected_ingame,
            selected_badges,
            selected_gamepasses,
            selected_playtime,
            registration_date,
            subscription_expiration,
            trial_claimed,
            referrer_id,
            ref_balance,
            output_format,
            fresher_invalidate_old,
            language,
            ad_broadcast_enabled
        FROM users WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()

    if not row:
        return None

    default_checks = {p: True for p in CHECK_PARAMS}
    default_ingame = {s: True for s in GAMES}
    default_playtime = {s: True for s in GAMES}
    default_badges = {}
    default_gamepasses = {}

    return {
        'selected_checks': safe_load_and_repair(user_id, 'selected_checks', row[0], default_checks),
        'selected_ingame': safe_load_and_repair(user_id, 'selected_ingame', row[1], default_ingame),
        'selected_badges': safe_load_and_repair(user_id, 'selected_badges', row[2], default_badges),
        'selected_gamepasses': safe_load_and_repair(user_id, 'selected_gamepasses', row[3], default_gamepasses),
        'selected_playtime': safe_load_and_repair(user_id, 'selected_playtime', row[4], default_playtime),
        'registration_date': row[5],
        'subscription_expiration': row[6],
        'trial_claimed': bool(row[7]) if row[7] is not None else False,
        'referrer_id': row[8],
        'ref_balance': row[9] or 0,
        'output_format': row[10] or 'zip',
        'fresher_invalidate_old': bool(row[11]) if len(row) > 11 and row[11] is not None else True,
        'language': row[12] if len(row) > 12 and row[12] else "ru",
        'ad_broadcast_enabled': bool(row[13]) if len(row) > 13 and row[13] is not None else True
    }


def save_user_settings(user_id: int, settings: dict):
    reg_date = settings.get('registration_date', datetime.now(moscow_tz).isoformat())
    sub_exp = settings.get('subscription_expiration')

    def ensure_dict(val, default):
        if not isinstance(val, dict):
            return default
        return val

    invalidate_old = 1 if settings.get('fresher_invalidate_old', True) else 0
    language = settings.get('language', 'ru')
    ad_broadcast_enabled = 1 if settings.get('ad_broadcast_enabled', True) else 0

    # Проверяем, существует ли пользователь
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone()

    if exists:
        # UPDATE — обновляем ТОЛЬКО поля настроек, НЕ трогаем last_bonus_claim, trial_claimed, referrer_id, ref_balance
        cursor.execute('''UPDATE users SET
            selected_checks = ?,
            selected_ingame = ?,
            selected_badges = ?,
            selected_gamepasses = ?,
            selected_playtime = ?,
            registration_date = ?,
            subscription_expiration = ?,
            output_format = ?,
            fresher_invalidate_old = ?,
            language = ?,
            ad_broadcast_enabled = ?
            WHERE user_id = ?''', (
            json.dumps(ensure_dict(settings.get('selected_checks'), {p: True for p in CHECK_PARAMS})),
            json.dumps(ensure_dict(settings.get('selected_ingame'), {s: True for s in GAMES})),
            json.dumps(ensure_dict(settings.get('selected_badges'), {})),
            json.dumps(ensure_dict(settings.get('selected_gamepasses'), {})),
            json.dumps(ensure_dict(settings.get('selected_playtime'), {s: True for s in GAMES})),
            reg_date,
            sub_exp,
            settings.get('output_format', 'zip'),
            invalidate_old,
            language,
            ad_broadcast_enabled,
            user_id
        ))
    else:
        # INSERT — только для новых пользователей
        cursor.execute('''INSERT INTO users
            (user_id, selected_checks, selected_ingame, selected_badges, selected_gamepasses,
             selected_playtime, registration_date, subscription_expiration, output_format,
             fresher_invalidate_old, language, ad_broadcast_enabled, last_bonus_claim, trial_claimed, referrer_id, ref_balance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0, NULL, 0)''', (
            user_id,
            json.dumps(ensure_dict(settings.get('selected_checks'), {p: True for p in CHECK_PARAMS})),
            json.dumps(ensure_dict(settings.get('selected_ingame'), {s: True for s in GAMES})),
            json.dumps(ensure_dict(settings.get('selected_badges'), {})),
            json.dumps(ensure_dict(settings.get('selected_gamepasses'), {})),
            json.dumps(ensure_dict(settings.get('selected_playtime'), {s: True for s in GAMES})),
            reg_date,
            sub_exp,
            settings.get('output_format', 'zip'),
            invalidate_old,
            language,
            ad_broadcast_enabled
        ))
    conn.commit()


# ==================== ФУНКЦИИ ДЛЯ РАССЫЛКИ ====================

def get_user_ad_broadcast_enabled(user_id: int) -> bool:
    """Проверяет, включена ли рекламная рассылка для пользователя"""
    cursor.execute("SELECT ad_broadcast_enabled FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0] is not None:
        return bool(row[0])
    return True  # По умолчанию включена

def set_user_ad_broadcast_enabled(user_id: int, enabled: bool):
    """Устанавливает настройку рекламной рассылки для пользователя"""
    value = 1 if enabled else 0
    cursor.execute("UPDATE users SET ad_broadcast_enabled = ? WHERE user_id = ?", (value, user_id))
    conn.commit()

# ==================== ОСТАЛЬНЫЕ ФУНКЦИИ ====================

def generate_unique_key() -> str:
    """Генерирует уникальный 16-символьный ключ"""
    return uuid.uuid4().hex.upper()[:16]


def create_activation_keys(admin_id: int, plan: str, count: int) -> list[str]:
    """Создаёт count ключей для указанного плана. Возвращает список ключей."""
    if plan not in PLANS:
        raise ValueError("Некорректный план")

    keys = []
    for _ in range(count):
        while True:
            key = generate_unique_key()
            cursor.execute("SELECT 1 FROM activation_keys WHERE key = ?", (key,))
            if not cursor.fetchone():
                break

        cursor.execute("""
            INSERT INTO activation_keys
            (key, plan, created_by, created_at)
            VALUES (?, ?, ?, ?)
        """, (key, plan, admin_id, datetime.now(moscow_tz).isoformat()))
        keys.append(key)

    conn.commit()
    return keys


def claim_bonus_days(user_id: int) -> bool:
    with _cache_lock:
        cache_time = _last_bonus_cache.get(user_id)
        if cache_time:
            now = datetime.now(moscow_tz).replace(tzinfo=None)
            if (now - cache_time).days < 30:
                return False

    cursor.execute("BEGIN IMMEDIATE")
    try:
        cursor.execute("SELECT last_bonus_claim, subscription_expiration FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            cursor.execute("ROLLBACK")
            return False

        last_claim_str, sub_exp_str = row
        now = datetime.now(moscow_tz).replace(tzinfo=None)

        if last_claim_str:
            try:
                last_claim = datetime.fromisoformat(last_claim_str).replace(tzinfo=None)
                if (now - last_claim).days < 30:
                    cursor.execute("ROLLBACK")
                    return False
            except:
                pass

        # Вычисляем новую дату подписки
        if sub_exp_str and sub_exp_str != '0':
            try:
                sub_exp = datetime.fromisoformat(sub_exp_str).replace(tzinfo=None)
                new_exp = (sub_exp if sub_exp > now else now) + timedelta(days=2)
            except:
                new_exp = now + timedelta(days=2)
        else:
            new_exp = now + timedelta(days=2)

        cursor.execute(
            "UPDATE users SET subscription_expiration = ?, last_bonus_claim = ? WHERE user_id = ?",
            (new_exp.isoformat(), now.isoformat(), user_id)
        )

        if cursor.rowcount == 0:
            cursor.execute("ROLLBACK")
            return False

        cursor.execute("COMMIT")

        with _cache_lock:
            _last_bonus_cache[user_id] = now

        return True

    except Exception as e:
        cursor.execute("ROLLBACK")
        logging.error(f"[BONUS] Ошибка для {user_id}: {e}")
        return False


def get_unused_key(key_str: str) -> dict | None:
    """Возвращает информацию о неиспользованном ключе или None"""
    cursor.execute("""
        SELECT id, plan, created_by 
        FROM activation_keys 
        WHERE key = ? AND used_by IS NULL
    """, (key_str,))
    row = cursor.fetchone()
    if row:
        return {'id': row[0], 'plan': row[1], 'created_by': row[2]}
    return None


def activate_key(user_id: int, key_str: str) -> tuple[bool, str]:
    """Активирует ключ и продлевает подписку. Возвращает (успех, сообщение)"""
    key_info = get_unused_key(key_str)
    if not key_info:
        return False, "❌ Ключ не найден или уже использован."

    plan = key_info['plan']
    days = PLANS[plan]['days']

    now = datetime.now(moscow_tz).replace(tzinfo=None)

    cursor.execute("SELECT subscription_expiration FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row and row[0]:
        try:
            current_exp = datetime.fromisoformat(row[0]).replace(tzinfo=None)
            if plan == 'forever':
                new_exp = now + timedelta(days=365*100)  # «навсегда»
            else:
                new_exp = current_exp + timedelta(days=days) if current_exp > now else now + timedelta(days=days)
        except:
            new_exp = now + timedelta(days=days) if plan != 'forever' else now + timedelta(days=365*100)
    else:
        new_exp = now + timedelta(days=days) if plan != 'forever' else now + timedelta(days=365*100)

    exp_str = new_exp.isoformat()

    cursor.execute("UPDATE users SET subscription_expiration = ? WHERE user_id = ?", (exp_str, user_id))
    cursor.execute("""
        UPDATE activation_keys 
        SET used_by = ?, used_at = ? 
        WHERE id = ?
    """, (user_id, datetime.now(moscow_tz).isoformat(), key_info['id']))

    conn.commit()

    days_text = "навсегда 🎉" if plan == 'forever' else f"на {days} дней"
    return True, f"✅ Ключ успешно активирован!\nПодписка продлена {days_text}"


def update_global_sniped_stats(balance: int, pending: int):
    cursor.execute('''UPDATE global_stats SET
        total_sniped_balance = total_sniped_balance + ?,
        total_sniped_pending = total_sniped_pending + ?
        WHERE id = 1''', (balance, pending))
    conn.commit()


def get_badge_name_from_cache(badge_id: int) -> str | None:
    cursor.execute("SELECT name FROM badge_cache WHERE badge_id = ?", (badge_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def cache_badge_name(badge_id: int, name: str):
    cursor.execute("""
        INSERT OR REPLACE INTO badge_cache (badge_id, name) VALUES (?, ?)
    """, (badge_id, name))
    conn.commit()


def get_gamepass_name_from_cache(gamepass_id: int) -> str | None:
    cursor.execute("SELECT name FROM gamepass_cache WHERE gamepass_id = ?", (gamepass_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def cache_gamepass_name(gamepass_id: int, name: str):
    cursor.execute("""
        INSERT OR REPLACE INTO gamepass_cache (gamepass_id, name) VALUES (?, ?)
    """, (gamepass_id, name))
    conn.commit()


# ==================== ФУНКЦИИ ДЛЯ СНАЙПЕРА ====================
def create_sniper_session(user_id: int, name: str, data_list: list[dict], threshold_balance: int = 100, threshold_pending: int = 50, active: int = 0) -> int:
    cursor.execute("SELECT COUNT(*) FROM sniper_sessions WHERE user_id = ?", (user_id,))
    if cursor.fetchone()[0] >= 5:
        raise ValueError("Максимум 5 сессий снайпера на пользователя")

    cookie_count = len(data_list)

    if data_list and isinstance(data_list[0], str):
        data_list = [{"cookie": ck, "last_bal": 0, "last_pend": 0} for ck in data_list]
        cookie_count = len(data_list)

    data_json = json.dumps(data_list)
    cursor.execute("""
        INSERT INTO sniper_sessions 
        (user_id, name, data, threshold_balance, threshold_pending, active, cookie_count, created_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, name, data_json, threshold_balance, threshold_pending, active, cookie_count, datetime.now(moscow_tz).isoformat()))
    conn.commit()
    return cursor.lastrowid


def get_user_sniper_sessions(user_id: int):
    cursor.execute("""
        SELECT id, name, active, total_sniped_balance, total_sniped_pending, threshold_balance, threshold_pending, cookie_count
        FROM sniper_sessions WHERE user_id = ? ORDER BY id DESC
    """, (user_id,))
    rows = cursor.fetchall()
    return [
        {
            'id': r[0],
            'name': r[1],
            'active': bool(r[2]),
            'total_bal': r[3],
            'total_pend': r[4],
            'th_bal': r[5],
            'th_pend': r[6],
            'cookie_count': r[7] or 0
        } for r in rows
    ]


def get_sniper_session(session_id: int) -> dict | None:
    cursor.execute("SELECT * FROM sniper_sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    if not row:
        return None
    try:
        data_str = row[3]
        if len(data_str) > 20 * 1024 * 1024:
            raise json.JSONDecodeError("Data too large", data_str, 0)
        data = json.loads(data_str)
        if not isinstance(data, list):
            raise json.JSONDecodeError("Not a list", data_str, 0)
    except json.JSONDecodeError:
        logging.warning(f"Corrupted or too large JSON data in sniper session {session_id}")
        data = []
        cursor.execute("UPDATE sniper_sessions SET data = ?, cookie_count = 0 WHERE id = ?", ('[]', session_id))
        conn.commit()
    return {
        'id': row[0],
        'user_id': row[1],
        'name': row[2],
        'data': data,
        'threshold_balance': row[4],
        'threshold_pending': row[5],
        'active': bool(row[6]),
        'total_sniped_balance': row[7],
        'total_sniped_pending': row[8],
        'cookie_count': row[9] or 0,
        'created_at': row[10],
        'processing': bool(row[11])
    }


def update_sniper_session(session_id: int, **kwargs):
    allowed = ['data', 'threshold_balance', 'threshold_pending', 'active', 'total_sniped_balance', 'total_sniped_pending', 'name', 'processing', 'cookie_count']
    set_parts = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            set_parts.append(f"{k} = ?")
            if k == 'data':
                try:
                    if isinstance(v, list):
                        if len(v) > 5000:
                            v = v[:5000]
                            logging.warning(f"Data усечено до 5000 элементов в update для сессии {session_id}")
                        cookie_count = len(v)
                        data_json = json.dumps(v)
                        if len(data_json) > 20 * 1024 * 1024:
                            raise ValueError("JSON too large after dump")
                        values.append(data_json)
                        values.append(cookie_count)
                        set_parts.append('cookie_count = ?')
                    else:
                        values.append('[]')
                        values.append(0)
                        set_parts.append('cookie_count = ?')
                except (json.JSONDecodeError, ValueError) as e:
                    logging.error(f"Error dumping data for session {session_id}: {e}")
                    values.append('[]')
                    values.append(0)
                    set_parts.append('cookie_count = ?')
            else:
                values.append(v)
    if not set_parts:
        return
    values.append(session_id)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            cursor.execute(f"UPDATE sniper_sessions SET {', '.join(set_parts)} WHERE id = ?", values)
            conn.commit()
            break
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                logging.warning(f"DB locked during update for session {session_id} (attempt {attempt+1}), retrying in 2 sec...")
                import time
                time.sleep(2)
                continue
            else:
                logging.error(f"Failed to update session {session_id} after {max_retries} retries: {e}")
                raise


def delete_sniper_session(session_id: int):
    cursor.execute("DELETE FROM sniper_sessions WHERE id = ?", (session_id,))
    conn.commit()


# ==================== ФУНКЦИИ ДЛЯ РОЗЫГРЫШЕЙ ====================
def create_giveaway(amount: int, end_date_iso: str) -> int:
    """Создаёт новый розыгрыш"""
    cursor.execute("""
        INSERT INTO giveaways (amount, end_date, message_id, participants)
        VALUES (?, ?, 0, '[]')
    """, (amount, end_date_iso))
    conn.commit()
    return cursor.lastrowid


def update_giveaway_message_id(giveaway_id: int, message_id: int):
    cursor.execute("UPDATE giveaways SET message_id = ? WHERE id = ?", (message_id, giveaway_id))
    conn.commit()


def get_expired_giveaways() -> list[dict]:
    """Возвращает все розыгрыши, где время истекло и победитель ещё не выбран"""
    now = datetime.now(moscow_tz)
    now_iso = now.isoformat()

    # Получаем все активные розыгрыши
    cursor.execute("""
        SELECT id, amount, end_date, message_id, participants 
        FROM giveaways 
        WHERE winner_id IS NULL
    """)
    rows = cursor.fetchall()

    result = []
    for row in rows:
        try:
            end_date_str = row[2]
            # Парсим дату окончания
            end_date = datetime.fromisoformat(end_date_str)

            # Проверяем, истекло ли время (сравниваем datetime объекты)
            if end_date <= now:
                try:
                    participants = json.loads(row[4])
                except:
                    participants = []

                result.append({
                    'id': row[0],
                    'amount': row[1],
                    'end_date': end_date_str,
                    'message_id': row[3],
                    'participants': participants
                })
        except Exception as e:
            logging.error(f"Ошибка парсинга даты розыгрыша {row[0]}: {e}")
            continue

    return result


def set_giveaway_winner(giveaway_id: int, winner_id: int):
    cursor.execute("UPDATE giveaways SET winner_id = ? WHERE id = ?", (winner_id, giveaway_id))
    conn.commit()


def get_giveaway(giveaway_id: int) -> dict | None:
    cursor.execute("""
        SELECT amount, end_date, message_id, participants, winner_id 
        FROM giveaways WHERE id = ?
    """, (giveaway_id,))
    row = cursor.fetchone()
    if not row:
        return None
    try:
        participants = json.loads(row[3])
    except:
        participants = []
    return {
        'id': giveaway_id,
        'amount': row[0],
        'end_date': row[1],
        'message_id': row[2],
        'participants': participants,
        'winner_id': row[4]
    }


def add_participant_to_giveaway(giveaway_id: int, user_id: int) -> int:
    ga = get_giveaway(giveaway_id)
    if not ga:
        return 0
    if user_id not in ga['participants']:
        ga['participants'].append(user_id)
        cursor.execute("UPDATE giveaways SET participants = ? WHERE id = ?", 
                      (json.dumps(ga['participants']), giveaway_id))
        conn.commit()
    return len(ga['participants'])


# ==================== ФУНКЦИИ ДЛЯ ЛИМИТА ЧЕКЕРА ====================
def log_user_check(user_id: int, count: int):
    """Логирует проверку куков и чистит записи старше 2 часов"""
    cursor.execute("DELETE FROM check_logs WHERE timestamp < datetime('now', '-2 hours')")
    cursor.execute(
        "INSERT INTO check_logs (user_id, timestamp, cookie_count) VALUES (?, datetime('now'), ?)",
        (user_id, count)
    )
    conn.commit()


def get_hourly_check_count(user_id: int) -> int:
    """Возвращает количество проверенных куков за последний час"""
    cursor.execute("""
        SELECT COALESCE(SUM(cookie_count), 0) FROM check_logs
        WHERE user_id = ? AND timestamp > datetime('now', '-1 hour')
    """, (user_id,))
    row = cursor.fetchone()
    return row[0]


# ==================== ФУНКЦИИ ДЛЯ ПРОВЕРКИ ПОДПИСКИ ====================
def is_subscribed(user_id: int) -> bool:
    # Free mode: доступ к функциям открыт всем пользователям без подписки/ключа.
    return True


def get_profile_info(user_id: int) -> tuple:
    cursor.execute("SELECT registration_date, subscription_expiration FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    now = datetime.now(moscow_tz).replace(tzinfo=None)
    if row:
        try:
            reg = datetime.fromisoformat(row[0]).replace(tzinfo=None)
        except:
            reg = now
        try:
            exp = datetime.fromisoformat(row[1]).replace(tzinfo=None)
        except:
            exp = None
        if exp:
            if exp > now + timedelta(days=365*10):
                days_left = "∞ (навсегда)"
            else:
                days_left = max(0, (exp - now).days)
        else:
            days_left = 0
        return reg, exp, days_left
    return None, None, 0


# ==================== ФУНКЦИИ ДЛЯ СТАТИСТИКИ ====================
def update_global_stats(summary: dict):
    cursor.execute('''UPDATE global_stats SET
        total_donate = total_donate + ?,
        total_balance = total_balance + ?,
        total_pending = total_pending + ?,
        total_rap = total_rap + ?,
        total_groups_balance = total_groups_balance + ?
        WHERE id = 1''', (
        summary.get('sum_donate_lifetime', 0),
        summary.get('sum_balance', 0),
        summary.get('sum_pending', 0),
        summary.get('sum_rap', 0),
        summary.get('sum_groups_balance', 0)
    ))
    conn.commit()


def update_global_cookies_checked(amount: int):
    cursor.execute('UPDATE global_stats SET total_cookies_checked = total_cookies_checked + ? WHERE id = 1', (amount,))
    conn.commit()


def update_global_cookies_freshed(amount: int):
    cursor.execute('UPDATE global_stats SET total_cookies_freshed = total_cookies_freshed + ? WHERE id = 1', (amount,))
    conn.commit()


def increment_user_checked(user_id: int, amount: int):
    cursor.execute('UPDATE users SET user_cookies_checked = COALESCE(user_cookies_checked, 0) + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()


def increment_user_freshed(user_id: int, amount: int):
    cursor.execute('UPDATE users SET user_cookies_freshed = COALESCE(user_cookies_freshed, 0) + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()


def get_user_activity(user_id: int) -> tuple:
    cursor.execute('SELECT COALESCE(user_cookies_checked, 0), COALESCE(user_cookies_freshed, 0) FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    return (row[0], row[1]) if row else (0, 0)


def get_global_stats() -> dict:
    cursor.execute("SELECT * FROM global_stats WHERE id = 1")
    row = cursor.fetchone()
    if row:
        return {
            'total_donate': row[1] or 0,
            'total_balance': row[2] or 0,
            'total_pending': row[3] or 0,
            'total_rap': row[4] or 0,
            'total_groups_balance': row[5] or 0,
            'total_cookies_checked': row[6] or 0,
            'total_cookies_freshed': row[7] or 0,
            'trial_enabled': row[8] or 0,
            'total_sniped_balance': row[9] or 0,
            'total_sniped_pending': row[10] or 0
        }
    return {
        'total_donate': 0,
        'total_balance': 0,
        'total_pending': 0,
        'total_rap': 0,
        'total_groups_balance': 0,
        'total_cookies_checked': 0,
        'total_cookies_freshed': 0,
        'trial_enabled': 0,
        'total_sniped_balance': 0,
        'total_sniped_pending': 0
    }


def get_all_users() -> list[int]:
    cursor.execute("SELECT user_id FROM users")
    return [row[0] for row in cursor.fetchall()]


# ==================== ФУНКЦИИ ДЛЯ КАСТОМНЫХ КОНФИГОВ ====================
def get_user_custom_configs(user_id: int, config_type: str) -> dict[str, list[int]]:
    cursor.execute("SELECT name, ids FROM custom_configs WHERE user_id = ? AND type = ?", (user_id, config_type))
    rows = cursor.fetchall()
    result = {}
    for row in rows:
        try:
            result[row[0]] = json.loads(row[1])
        except:
            result[row[0]] = []
    return result


def add_user_custom_config(user_id: int, config_type: str, name: str, ids: list[int]):
    cursor.execute("SELECT COUNT(*) FROM custom_configs WHERE user_id = ? AND type = ?", (user_id, config_type))
    count = cursor.fetchone()[0]
    if count >= 5:
        raise ValueError("Максимум 5 конфигов")
    cursor.execute("INSERT INTO custom_configs (user_id, type, name, ids) VALUES (?, ?, ?, ?)", (
        user_id, config_type, name, json.dumps(ids)
    ))
    conn.commit()


# ==================== ФУНКЦИИ ДЛЯ ПОДПИСКИ ====================
def add_subscription(user_id: int, days: int):
    now = datetime.now(moscow_tz).replace(tzinfo=None)
    cursor.execute("SELECT subscription_expiration FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0]:
        try:
            current_exp = datetime.fromisoformat(row[0]).replace(tzinfo=None)
            new_exp = current_exp + timedelta(days=days) if current_exp > now else now + timedelta(days=days)
        except:
            new_exp = now + timedelta(days=days)
    else:
        new_exp = now + timedelta(days=days)

    exp_str = new_exp.isoformat()
    cursor.execute("UPDATE users SET subscription_expiration = ? WHERE user_id = ?", (exp_str, user_id))
    conn.commit()


# ==================== ФУНКЦИИ ДЛЯ TRIAL ====================
def is_trial_enabled() -> bool:
    cursor.execute("SELECT trial_enabled FROM global_stats WHERE id = 1")
    row = cursor.fetchone()
    return bool(row[0]) if row else False


def set_trial_enabled(enabled: bool):
    value = 1 if enabled else 0
    cursor.execute("UPDATE global_stats SET trial_enabled = ? WHERE id = 1", (value,))
    conn.commit()


def has_claimed_trial(user_id: int) -> bool:
    cursor.execute("SELECT trial_claimed FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return bool(row[0]) if row else False


def set_claimed_trial(user_id: int, claimed: bool):
    value = 1 if claimed else 0
    cursor.execute("UPDATE users SET trial_claimed = ? WHERE user_id = ?", (value, user_id))
    conn.commit()


# ==================== ФУНКЦИИ ДЛЯ РЕФЕРАЛОВ ====================
def set_referrer(user_id: int, referrer_id: int):
    cursor.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (referrer_id, user_id))
    conn.commit()


def get_referrer_id(user_id: int) -> int:
    cursor.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row and row[0] else None


def add_ref_earning(referrer_id: int, amount: int):
    cursor.execute("UPDATE users SET ref_balance = ref_balance + ? WHERE user_id = ?", (amount, referrer_id))
    conn.commit()


def get_ref_balance(user_id: int) -> int:
    cursor.execute("SELECT ref_balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0


def get_ref_count(user_id: int) -> int:
    cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
    return cursor.fetchone()[0]


# ==================== ФУНКЦИИ ДЛЯ ВЫВОДА ====================
def create_withdrawal_request(user_id: int, amount: int) -> int:
    cursor.execute("INSERT INTO withdrawal_requests (user_id, amount) VALUES (?, ?)", (user_id, amount))
    conn.commit()
    return cursor.lastrowid


def get_pending_withdrawals() -> list:
    cursor.execute("SELECT id, user_id, amount FROM withdrawal_requests WHERE status = 'pending'")
    return [{"id": row[0], "user_id": row[1], "amount": row[2]} for row in cursor.fetchall()]


def complete_withdrawal(request_id: int, payout_link: str) -> int | None:
    cursor.execute("SELECT user_id, amount FROM withdrawal_requests WHERE id = ? AND status = 'pending'", (request_id,))
    row = cursor.fetchone()
    if row:
        user_id, amount = row
        cursor.execute("UPDATE withdrawal_requests SET status = 'completed', payout_link = ? WHERE id = ?", (payout_link, request_id))
        cursor.execute("UPDATE users SET ref_balance = ref_balance - ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        return user_id
    return None


# ==================== ФУНКЦИИ ДЛЯ ПЕРЕОПРЕДЕЛЕНИЯ ИГР ====================
def set_user_game_override(user_id: int, short: str, type_: str, name: str, place_id: int, universe_id: int):
    cursor.execute("""
        INSERT OR REPLACE INTO user_game_overrides 
        (user_id, short, type, name, place_id, universe_id) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, short, type_, name, place_id, universe_id))
    conn.commit()


def reset_user_game_override(user_id: int, short: str, type_: str = None):
    if type_:
        cursor.execute("""
            DELETE FROM user_game_overrides 
            WHERE user_id = ? AND short = ? AND type = ?
        """, (user_id, short, type_))
    else:
        cursor.execute("""
            DELETE FROM user_game_overrides 
            WHERE user_id = ? AND short = ?
        """, (user_id, short))
    conn.commit()


def get_user_game_overrides(user_id: int, type_: str = None) -> dict:
    if type_:
        cursor.execute("""
            SELECT short, name, place_id, universe_id 
            FROM user_game_overrides 
            WHERE user_id = ? AND type = ?
        """, (user_id, type_))
        rows = cursor.fetchall()
        return {
            row[0]: {'name': row[1], 'place_id': row[2], 'universe_id': row[3]}
            for row in rows
        }
    else:
        cursor.execute("""
            SELECT short, name, place_id, universe_id, type
            FROM user_game_overrides 
            WHERE user_id = ?
        """, (user_id,))
        rows = cursor.fetchall()
        result = {'ingame': {}, 'playtime': {}}
        for row in rows:
            short, name, place_id, universe_id, override_type = row
            if override_type == 'ingame':
                result['ingame'][short] = {
                    'name': name, 
                    'place_id': place_id, 
                    'universe_id': universe_id
                }
            elif override_type == 'playtime':
                result['playtime'][short] = {
                    'name': name, 
                    'place_id': place_id, 
                    'universe_id': universe_id
                }
        return result


# ==================== ФУНКЦИИ ДЛЯ СПОНСОРСКИХ КАНАЛОВ ====================
def get_sponsor_channels() -> list[dict]:
    """Возвращает список всех спонсорских каналов."""
    cursor.execute("SELECT id, channel_id, channel_link FROM sponsor_channels ORDER BY id")
    rows = cursor.fetchall()
    return [{'id': row[0], 'channel_id': row[1], 'channel_link': row[2]} for row in rows]


def add_sponsor_channel(admin_id: int, channel_id: int, channel_link: str) -> tuple[bool, str]:
    """Добавляет канал, если не превышен лимит 5."""
    existing = get_sponsor_channels()
    if len(existing) >= 5:
        return False, "❌ Достигнут лимит – 5 каналов."
    try:
        cursor.execute(
            "INSERT INTO sponsor_channels (channel_id, channel_link) VALUES (?, ?)",
            (channel_id, channel_link)
        )
        conn.commit()
        return True, f"✅ Канал {channel_link} добавлен."
    except sqlite3.IntegrityError:
        return False, "❌ Этот канал уже есть в списке."


def remove_sponsor_channel(admin_id: int, channel_id: int) -> bool:
    """Удаляет канал по ID."""
    cursor.execute("DELETE FROM sponsor_channels WHERE channel_id = ?", (channel_id,))
    affected = cursor.rowcount
    conn.commit()
    return affected > 0


def clear_sponsor_channels(admin_id: int) -> bool:
    """Удаляет все спонсорские каналы."""
    cursor.execute("DELETE FROM sponsor_channels")
    conn.commit()
    return True


def can_claim_bonus(user_id: int) -> tuple[bool, str]:
    """Проверяет, может ли пользователь получить бонусные дни."""
    cursor.execute("SELECT last_bonus_claim FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    last_claim_str = row[0] if row and row[0] else None

    now = datetime.now(moscow_tz).replace(tzinfo=None)

    if last_claim_str:
        try:
            last_date = datetime.fromisoformat(last_claim_str).replace(tzinfo=None)
            days_passed = (now - last_date).days
            if days_passed < 30:
                days_left = 30 - days_passed
                return False, f"⏳ Вы уже получали бонус недавно. Следующий бонус доступен через {days_left} дней."
        except Exception as e:
            logging.error(f"Ошибка парсинга last_bonus_claim для {user_id}: {e}")
            return False, "❌ Ошибка проверки бонуса. Попробуйте позже."

    return True, ""
