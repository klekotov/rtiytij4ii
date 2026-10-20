import asyncio
import logging
import os
import random
import re
import uuid
import zipfile
import sqlite3 # Добавьте этот импорт, если его нет в начале файла
from datetime import datetime, timedelta, timezone
from io import BytesIO
import tempfile
import traceback
from config import ADMIN_IDS
from database import activate_key, add_days_to_all_active_subscribers, claim_bonus_days, create_activation_keys, cursor, conn, update_global_stats
import aiohttp
import math
from aiogram.types import InputMediaDocument
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message, FSInputFile
from database import cursor, conn, update_global_stats, update_global_cookies_checked, update_global_cookies_freshed
from aiogram.fsm.context import FSMContext
import glob
import os.path
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
import random
import json
from database import get_user_game_overrides
import textwrap # Добавлен импорт для dedent
from config import bot
from config import TELEGRAM_TOKEN, CRYPTO_PAY_TOKEN, PLANS, CRYPTO_PAY_API_URL, MANUAL_USDT_RATE, CHECK_PARAMS, GAMES, BADGES_PER_GAME, GAMEPASSES_PER_GAME, CHANNEL_ID, CHANNEL_URL, REF_PERCENT, BOT_USERNAME # Импорт из config.py
from database import get_user_settings, save_user_settings, is_subscribed, get_profile_info, get_global_stats, get_all_users, get_user_custom_configs, add_user_custom_config, add_subscription, is_trial_enabled, set_trial_enabled, has_claimed_trial, set_claimed_trial, set_referrer, get_ref_balance, add_ref_earning, get_ref_count, create_withdrawal_request, get_pending_withdrawals, complete_withdrawal, get_user_ad_broadcast_enabled, set_user_ad_broadcast_enabled, increment_user_checked, increment_user_freshed, get_user_activity # Импорт из database.py
from cookie_processor import CookieProcessor # Импорт из cookie_processor.py
from utils import load_proxies, save_stats_html, get_stats_url # Импорт из utils.py
from database import (

    cursor, conn, get_sponsor_channels, add_sponsor_channel, remove_sponsor_channel, clear_sponsor_channels, can_claim_bonus, update_global_stats, update_global_cookies_checked, update_global_cookies_freshed,
    get_user_settings, save_user_settings, is_subscribed, get_profile_info, get_global_stats,
    get_all_users, get_user_custom_configs, add_user_custom_config, add_subscription,
    is_trial_enabled, set_trial_enabled, has_claimed_trial, set_claimed_trial,
    set_referrer, get_ref_balance, add_ref_earning, get_ref_count,
    create_withdrawal_request, get_pending_withdrawals, complete_withdrawal, get_referrer_id, reset_user_game_override, set_user_game_override, get_hourly_check_count, log_user_check
)
import time # Добавлен импорт time для отслеживания времени обновлений
from datetime import timezone, timedelta
from database import get_user_settings, save_user_settings, is_subscribed, get_profile_info, get_global_stats, get_all_users, get_user_custom_configs, add_user_custom_config, add_subscription, is_trial_enabled, set_trial_enabled, has_claimed_trial, set_claimed_trial, set_referrer, get_ref_balance, add_ref_earning, get_ref_count, create_withdrawal_request, get_pending_withdrawals, complete_withdrawal, get_referrer_id # Добавлен get_referrer_id
import logging # Добавлен для логирования в sniper функциях
import threading
from collections import defaultdict
moscow_tz = timezone(timedelta(hours=3))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
cookie_processor = CookieProcessor()

MAX_UPLOAD_FILE_BYTES = 8 * 1024 * 1024


def _validate_txt_document(document) -> tuple[bool, str]:
    """Проверяет расширение/имя/размер входящего файла."""
    if not document:
        return False, "missing"

    file_name = (getattr(document, "file_name", "") or "").strip()
    if not file_name:
        return False, "invalid_format"
    if "/" in file_name or "\\" in file_name or ".." in file_name:
        return False, "invalid_name"
    if not file_name.lower().endswith(".txt"):
        return False, "invalid_format"

    file_size = getattr(document, "file_size", None)
    if isinstance(file_size, int) and file_size > MAX_UPLOAD_FILE_BYTES:
        return False, "too_large"

    return True, ""

from aiogram import BaseMiddleware
from typing import Callable, Awaitable, Any

# НОВАЯ ФУНКЦИЯ: Отправка ошибок админам
from languages import get_text
from database import get_user_language, set_user_language
from database import (
    create_giveaway, update_giveaway_message_id, get_giveaway, add_participant_to_giveaway, get_expired_giveaways, set_giveaway_winner
)
class FSMStates(StatesGroup):
    main_menu = State()
    settings = State()
    creating_giveaway_amount = State()
    creating_giveaway_end = State()
    waiting_for_validation_file = State()
    checks = State()
    editing_file = State()
    ingame = State()
    waiting_for_game_url = State()  # Ожидание ссылки на новую игру
    playtime = State() # ДОБАВЛЕНО: состояние для меню выбора игр playtime
    badges = State()
    gamepasses = State()
    badges_lists = State()
    gamepasses_lists = State()
    waiting_for_activation_key = State()  # Ожидание ввода ключа
    waiting_for_file = State()
    waiting_for_file_duplicate = State()
    waiting_for_file_fresh = State()
    waiting_for_custom_badges = State()
    waiting_for_custom_gamepasses = State()
    waiting_for_config_name = State()
    waiting_for_sponsor_channel = State()   # для добавления канала
    waiting_for_sponsor_channel_remove = State()  # для удаления по ID
    waiting_for_config_badges = State()
    waiting_for_config_gamepasses = State()
    waiting_for_withdrawal_amount = State() # Новое состояние для вывода
    waiting_for_payout_link = State() # Новое состояние для админа
    other_functions = State() # Новое состояние для "Остальные функции"
    sorter = State() # Новое состояние для "Сортер"
    waiting_for_cookie_files = State() # Новое состояние для ожидания файлов с куками
    waiting_for_sponsor_channel_edit = State()  # для редактирования ссылки канала
    waiting_for_post_message = State()  # Новое состояние для ожидания сообщения рассылки
    waiting_for_file_action = State()  # Новое состояние для выбора действия с файлом
async def create_invoice(user_id: int, plan: str):
    price = PLANS[plan]['price']
    days = PLANS[plan]['days']
    payload = json.dumps({'user_id': user_id, 'plan': plan})
    # Исправление склонения для дней
    if days == 1:
        days_str = "1 день"
    elif 2 <= days % 10 <= 4 and (days % 100 < 10 or days % 100 >= 20):
        days_str = f"{days} дня"
    else:
        days_str = f"{days} дней"
    if plan == 'forever':
        days_str = "Навсегда"
    params = {
        'currency_type': 'fiat',
        'fiat': 'RUB',
        'amount': f"{price}",
        'accepted_assets': 'USDT,TON',
        'payload': payload,
        'description': f'Подписка 227 Checker - {days_str}',
        'allow_comments': False,
        'allow_anonymous': True,
        'expires_in': 3600
    }
    headers = {'Crypto-Pay-API-Token': CRYPTO_PAY_TOKEN}
    logging.info(f"🔄 Создание инвойса для user_id {user_id}, план {plan}, цена {price} RUB")
    logging.info(f"📨 Параметры запроса: {params}")
    async with aiohttp.ClientSession() as session:
        async with session.post(CRYPTO_PAY_API_URL + 'createInvoice', headers=headers, json=params) as resp:
            response_text = await resp.text()
            logging.info(f"📨 Ответ от Crypto Pay: статус {resp.status}, тело: {response_text}")
            if resp.status == 200:
                data = await resp.json()
                if data['ok']:
                    invoice = data['result']
                    # Логируем все полученные URL
                    logging.info(f"✅ Инвойс создан успешно:")
                    logging.info(f" - Invoice ID: {invoice.get('invoice_id')}")
                    logging.info(f" - Bot Invoice URL: {invoice.get('bot_invoice_url', 'N/A')}")
                    logging.info(f" - Mini App Invoice URL: {invoice.get('mini_app_invoice_url', 'N/A')}")
                    logging.info(f" - Web App Invoice URL: {invoice.get('web_app_invoice_url', 'N/A')}")
                    logging.info(f" - Pay URL (deprecated): {invoice.get('pay_url', 'N/A')}")
                    return invoice
                else:
                    error_msg = data.get('error', {})
                    logging.error(f"❌ Ошибка в ответе Crypto Pay: {error_msg}")
            else:
                logging.error(f"❌ HTTP ошибка при создании инвойса: статус {resp.status}")
    return None
async def create_test_invoice(user_id: int):
    params = {
        'asset': 'TON',
        'amount': '0.1',
        'description': 'Test payment 0.1 TON',
        'payload': json.dumps({'user_id': user_id, 'test': True}),
        'allow_comments': False,
        'allow_anonymous': True,
        'expires_in': 3600
    }
    headers = {'Crypto-Pay-API-Token': CRYPTO_PAY_TOKEN}
    logging.info(f"🔄 Создание тестового инвойса для user_id {user_id}")
    logging.info(f"📨 Параметры запроса: {params}")
    async with aiohttp.ClientSession() as session:
        async with session.post(CRYPTO_PAY_API_URL + 'createInvoice', headers=headers, json=params) as resp:
            response_text = await resp.text()
            logging.info(f"📨 Ответ от Crypto Pay: статус {resp.status}, тело: {response_text}")
            if resp.status == 200:
                data = await resp.json()
                if data['ok']:
                    invoice = data['result']
                    logging.info(f"✅ Тестовый инвойс создан успешно:")
                    logging.info(f" - Invoice ID: {invoice.get('invoice_id')}")
                    logging.info(f" - Bot Invoice URL: {invoice.get('bot_invoice_url', 'N/A')}")
                    logging.info(f" - Mini App Invoice URL: {invoice.get('mini_app_invoice_url', 'N/A')}")
                    logging.info(f" - Web App Invoice URL: {invoice.get('web_app_invoice_url', 'N/A')}")
                    logging.info(f" - Pay URL (deprecated): {invoice.get('pay_url', 'N/A')}")
                    return invoice
                else:
                    error_msg = data.get('error', {})
                    logging.error(f"❌ Ошибка в ответе Crypto Pay: {error_msg}")
            else:
                logging.error(f"❌ HTTP ошибка при создании тестового инвойса: статус {resp.status}")
    return None
@dp.message(Command('testpayy'))
async def testpay_handler(message: Message):
    invoice = await create_test_invoice(message.from_user.id)
    if invoice:
        url = (invoice.get('bot_invoice_url') or
               invoice.get('web_app_invoice_url') or
               invoice.get('mini_app_invoice_url') or
               invoice.get('pay_url'))
        if url:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить в боте", url=url)],
                [InlineKeyboardButton(text="🔄 Подтвердить оплату", callback_data=f"check_test_{invoice['invoice_id']}")]
            ])
            await message.answer(
                f"✅ Тестовый счёт создан!\n"
                f"💰 Сумма: 0.1 TON\n"
                f"⏰ Время на оплату: 1 час\n\n"
                f"После оплаты нажмите 'Подтвердить оплату'",
                reply_markup=keyboard
            )
        else:
            await message.answer("❌ Не удалось получить ссылку для оплаты")
    else:
        await message.answer("❌ Ошибка создания тестового счёта. Попробуйте позже.")
@dp.callback_query(lambda c: c.data.startswith("check_test_"))
async def check_test_payment(callback: types.CallbackQuery):
    invoice_id = callback.data.split("check_test_")[1]
    headers = {'Crypto-Pay-API-Token': CRYPTO_PAY_TOKEN}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{CRYPTO_PAY_API_URL}getInvoices?invoice_ids={invoice_id}", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data['ok']:
                    invoice = data['result']['items'][0]
                    status = invoice['status']
  
                    if status == 'paid':
                        await callback.message.edit_text("✅ Тестовая оплата подтверждена!")
                    elif status == 'active':
                        await callback.answer("⏳ Платёж ещё не подтверждён. Попробуйте позже.")
                    else:
                        await callback.answer("❌ Платёж не найден или отменён.")
                else:
                    await callback.answer("❌ Ошибка проверки платежа.")
            else:
                await callback.answer("❌ Ошибка соединения.")
async def show_language_selection(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Русский",icon_custom_emoji_id="5449408995691341691", callback_data="set_lang_ru")],
        [InlineKeyboardButton(text="English", icon_custom_emoji_id="5202021044105257611",callback_data="set_lang_en")],
    ])
    
    await message.answer(
        f"""<tg-emoji emoji-id="6030768072296502910">💬</tg-emoji> <b>Выберите язык / Select language</b>""",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
@dp.message(Command('start'))
async def start_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # УБРАНА ПРОВЕРКА ПОДПИСКИ НА КАНАЛ
    
    # Загружаем настройки пользователя
    await load_and_merge_settings(user_id, state)
    
    # Получаем язык пользователя из БД
    user_lang = get_user_language(user_id)
    
    # Если пользователь новый (нет языка), предлагаем выбрать
    settings = await state.get_data()
    if 'language' not in settings or not settings.get('language'):
        # Показываем меню выбора языка
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Русский",icon_custom_emoji_id="5449408995691341691", callback_data="set_lang_ru")],
        [InlineKeyboardButton(text="English", icon_custom_emoji_id="5202021044105257611",callback_data="set_lang_en")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), icon_custom_emoji_id="5807619215321996754", callback_data="main_menu")]
    ])
        await message.answer(
            f"""<tg-emoji emoji-id="6030768072296502910">💬</tg-emoji> <b>Выберите язык / Select language</b>""",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    # Установка реферала для новых пользователей
    referrer_id = None
    if args and args[0].startswith('ref'):
        try:
            referrer_id = int(args[0][3:])
            if referrer_id != user_id:
                set_referrer(user_id, referrer_id)
        except:
            pass
    
    await state.set_state(FSMStates.main_menu)
    
    # Отправляем ТОЛЬКО премиум эмодзи отдельным сообщением
    await message.answer(
        '<tg-emoji emoji-id="5938325816147448855">✨</tg-emoji>',
        parse_mode="HTML"
    )
    
    # ID премиум эмодзи (например, какая-то звездочка или иконка)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_checker"),
            icon_custom_emoji_id="6019205852831947754",  # Changed to string
            callback_data="checker"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_fresher"),
            icon_custom_emoji_id="5807492110059838726",  # Changed to string
            callback_data="fresher"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_validator"),
            icon_custom_emoji_id="6021659039367173797",  # Changed to string
            callback_data="validator"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_stats"),
            icon_custom_emoji_id="6021384767050618542",  # Changed to string
            callback_data="global_stats"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_profile"),
            icon_custom_emoji_id="6024039683904772353",  # Changed to string
            callback_data="profile"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_other"),
            icon_custom_emoji_id="6021401276904905698",  # Changed to string
            callback_data="other_functions"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_language"),
            icon_custom_emoji_id="6030768072296502910",  # Changed to string
            callback_data="language_menu"
        )
    ]
])

    await message.answer(
        f'{get_text(user_lang, "welcome")}',
        reply_markup=keyboard,
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data == "check_subscription")
async def check_subscription_handler(callback: types.CallbackQuery, state: FSMContext):
    # УБРАНА ПРОВЕРКА ПОДПИСКИ
    # Просто показываем главное меню
    await callback.message.delete()
    await start_handler(callback.message, state)
@dp.callback_query(lambda c: c.data == "language_menu")
async def language_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = get_user_language(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Русский",icon_custom_emoji_id="5449408995691341691", callback_data="set_lang_ru")],
        [InlineKeyboardButton(text="English", icon_custom_emoji_id="5202021044105257611",callback_data="set_lang_en")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), icon_custom_emoji_id="5807619215321996754", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        get_text(user_lang, "select_language"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# Функция для получения языка пользователя из state
async def get_user_lang_from_state(state: FSMContext) -> str:
    """Возвращает язык пользователя из state или по умолчанию 'ru'"""
    data = await state.get_data()
    return data.get('language', 'ru')

@dp.callback_query(lambda c: c.data == "profile")
@dp.message(Command('profile'))
async def profile_handler(query_or_message, state: FSMContext):
    if isinstance(query_or_message, types.CallbackQuery):
        message = query_or_message.message
        user_id = query_or_message.from_user.id
        callback = query_or_message
    else:
        message = query_or_message
        user_id = message.from_user.id
        callback = None

    # Получаем язык пользователя
    user_lang = await get_user_lang_from_state(state)

    reg, _, _ = get_profile_info(user_id)
    ref_balance = get_ref_balance(user_id)
    ref_count = get_ref_count(user_id)
    checked_count, freshed_count = get_user_activity(user_id)
    
    # Формирование текста профиля с переводом
    reg_text = reg.strftime('%d.%m.%Y %H:%M') if reg else 'Неизвестно'
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
    sponsor_channels = get_sponsor_channels()

    # Free mode: показываем подписку как активную для всех.
    sub_text = get_text(user_lang, "profile_sub_active_forever")

    text = f"""{get_text(user_lang, 'profile_title')} {get_text(user_lang, 'profile_id', user_id=user_id)}
{get_text(user_lang, 'profile_reg', reg_date=reg_text)}
{sub_text}

{get_text(user_lang, 'profile_ref_balance', balance=ref_balance)}
{get_text(user_lang, 'profile_ref_count', count=ref_count)}
{get_text(user_lang, 'profile_checked', checked=checked_count)}
{get_text(user_lang, 'profile_freshed', freshed=freshed_count)}
{get_text(user_lang, 'profile_ref_link', link=ref_link)}"""

    # Инициализация клавиатуры
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    if len(sponsor_channels) == 5:
        # Показываем кнопку только если есть все 5 каналов и подписка активна
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=get_text(user_lang, "btn_bonus_days"), callback_data="claim_bonus")
        ])
    
    if ref_balance >= 200:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=get_text(user_lang, "btn_withdraw_ref"), callback_data="withdraw_ref")])

    keyboard.inline_keyboard.append([InlineKeyboardButton(text=get_text(user_lang, "btn_ad_broadcast"), callback_data="ad_broadcast_settings")])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text=get_text(user_lang, "btn_back_menu"), icon_custom_emoji_id="5807619215321996754", callback_data="main_menu")])

    if callback:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "ad_broadcast_settings")
async def ad_broadcast_settings_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    if not is_subscribed(user_id):
        set_user_ad_broadcast_enabled(user_id, True)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="profile")]
        ])
        await callback.message.edit_text(
            get_text(user_lang, "ad_broadcast_sub_required"),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    is_enabled = get_user_ad_broadcast_enabled(user_id)
    
    if is_enabled:
        text = get_text(user_lang, "ad_broadcast_enabled")
    else:
        text = get_text(user_lang, "ad_broadcast_disabled")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_lang, "btn_toggle_ad_broadcast"), callback_data="toggle_ad_broadcast")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="profile")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "toggle_ad_broadcast")
async def toggle_ad_broadcast_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    if not is_subscribed(user_id):
        set_user_ad_broadcast_enabled(user_id, True)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="profile")]
        ])
        await callback.message.edit_text(
            get_text(user_lang, "ad_broadcast_sub_required"),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    current_status = get_user_ad_broadcast_enabled(user_id)
    new_status = not current_status
    set_user_ad_broadcast_enabled(user_id, new_status)
    
    # Обновляем настройки в state
    data = await state.get_data()
    data['ad_broadcast_enabled'] = new_status
    await state.update_data(data)
    save_user_settings(user_id, data)
    
    # Показываем обновленное меню
    await ad_broadcast_settings_handler(callback, state)

@dp.message(Command('mailing'))
async def mailing_command_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    if not is_subscribed(user_id):
        set_user_ad_broadcast_enabled(user_id, True)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="profile")]
        ])
        await message.answer(
            get_text(user_lang, "ad_broadcast_sub_required"),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    current_status = get_user_ad_broadcast_enabled(user_id)
    new_status = not current_status
    set_user_ad_broadcast_enabled(user_id, new_status)
    
    data = await state.get_data()
    data['ad_broadcast_enabled'] = new_status
    await state.update_data(data)
    save_user_settings(user_id, data)
    
    if new_status:
        text = get_text(user_lang, "ad_broadcast_enabled")
    else:
        text = get_text(user_lang, "ad_broadcast_disabled")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_lang, "btn_toggle_ad_broadcast"), callback_data="toggle_ad_broadcast")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="profile")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "claim_bonus")
async def claim_bonus_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)

    # ПРИНУДИТЕЛЬНО БЕРЕМ СВЕЖИЕ ДАННЫЕ ИЗ БД
    sponsor_channels = get_sponsor_channels()
    
    if len(sponsor_channels) != 5:
        await callback.answer(get_text(user_lang, "bonus_no_sponsors"), show_alert=True)
        return

    # Создаем клавиатуру со ссылками на каналы
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    for channel in sponsor_channels:
        channel_id = channel['channel_id']
        invite_link = channel.get('channel_link', '')
        
        # Если ссылки совсем нет — простой fallback
        if not invite_link or str(invite_link).lstrip('-').isdigit():
            invite_link = f"https://t.me/c/{str(channel_id).replace('-100', '')}"
        
        # Форматируем отображаемое имя
        if 't.me/' in invite_link:
            display_name = invite_link.split('t.me/')[-1]
            if display_name.startswith('c/'):
                display_name = f"Канал {display_name}"
        else:
            display_name = invite_link
        
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{display_name}",
                url=invite_link
            )
        ])
    
    # Добавляем кнопку проверки подписки
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_check_subscription"),
            icon_custom_emoji_id="5807414083388971488",
            callback_data="verify_sponsor_subscription"
        )
    ])
    
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_back"),
            callback_data="profile"
        )
    ])
    
    await callback.message.edit_text(
        get_text(user_lang, "bonus_sponsor_required"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "verify_sponsor_subscription")
async def verify_sponsor_subscription(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)

    # ПРИНУДИТЕЛЬНО ПОЛУЧАЕМ СВЕЖИЕ ДАННЫЕ ИЗ БД
    sponsor_channels = get_sponsor_channels()
    
    # Отправляем сообщение о начале проверки
    checking_msg = await callback.message.answer(get_text(user_lang, "bonus_checking"))
    
    # Проверяем подписку на все каналы
    unsubscribed_channels = []
    unsubscribed_ids = []
    
    for channel in sponsor_channels:
        channel_id = channel['channel_id']
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                unsubscribed_ids.append(channel_id)
                # Берём ссылку из БД
                invite_link = channel.get('channel_link', '')
                if not invite_link or str(invite_link).lstrip('-').isdigit():
                    invite_link = f"https://t.me/c/{str(channel_id).replace('-100', '')}"
                unsubscribed_channels.append(invite_link)
        except Exception as e:
            logging.error(f"Ошибка проверки подписки на канал {channel_id}: {e}")
            unsubscribed_ids.append(channel_id)
            invite_link = channel.get('channel_link', '')
            if not invite_link or str(invite_link).lstrip('-').isdigit():
                invite_link = f"Канал {channel_id} (ошибка проверки)"
            unsubscribed_channels.append(invite_link)
    
    # Если есть неподписанные каналы
    if unsubscribed_channels:
        # Создаем клавиатуру со ссылками из БД
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        for channel in sponsor_channels:
            channel_id = channel['channel_id']
            invite_link = channel.get('channel_link', '')
            
            # Если ссылки совсем нет — простой fallback
            if not invite_link or str(invite_link).lstrip('-').isdigit():
                invite_link = f"https://t.me/c/{str(channel_id).replace('-100', '')}"
            
            # Форматируем отображаемое имя
            if 't.me/' in invite_link:
                display_name = invite_link.split('t.me/')[-1]
                if display_name.startswith('c/'):
                    display_name = f"Канал {display_name}"
            else:
                display_name = invite_link
            
            # Помечаем неподписанные каналы
            if channel_id in unsubscribed_ids:
                display_name = f"⚠️ {display_name} (не подписан)"
            
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=display_name,
                    url=invite_link
                )
            ])
        
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=get_text(user_lang, "btn_check_subscription"),
                icon_custom_emoji_id="5807414083388971488",
                callback_data="verify_sponsor_subscription"
            )
        ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=get_text(user_lang, "btn_back"),
                callback_data="profile"
            )
        ])
        
        # Формируем текст о неподписанных каналах
        unsubscribed_text = "\n".join([f"• {ch}" for ch in unsubscribed_channels])
        
        await checking_msg.delete()
        await callback.message.edit_text(
            get_text(user_lang, "bonus_not_subscribed_list", channels=unsubscribed_text),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    # Проверяем, можно ли получить бонус
    can, reason = can_claim_bonus(user_id)
    if not can:
        await checking_msg.delete()
        await callback.message.edit_text(reason, parse_mode="HTML")
        return

    # Добавляем бонус
    if claim_bonus_days(user_id):
        # Получаем новую дату окончания
        _, exp, _ = get_profile_info(user_id)
        exp_str = exp.strftime('%d.%m.%Y') if exp else "неизвестно"
        
        await checking_msg.delete()
        await callback.message.edit_text(
            get_text(user_lang, "bonus_success", expiry=exp_str),
            parse_mode="HTML"
        )
        # Обновляем профиль
        await profile_handler(callback, state)
    else:
        await checking_msg.delete()
        await callback.message.edit_text(
            get_text(user_lang, "bonus_already_claimed"),
            parse_mode="HTML"
        )
@dp.message(Command('work'))
async def work_handler(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Нет доступа")
        return

    await show_work_menu(message, state)
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
async def show_work_menu(message: Message, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    channels = get_sponsor_channels()
    count = len(channels)

    text = get_text(user_lang, "admin_work_title", count=count)
    if channels:
        text += get_text(user_lang, "admin_work_list")
        for i, ch in enumerate(channels, 1):
            link_display = ch['channel_link']
            if not link_display or str(link_display).lstrip('-').isdigit():
                link_display = "Нет ссылки"
            text += get_text(user_lang, "admin_work_item", index=i, link=link_display, channel_id=ch['channel_id'])
    else:
        text += get_text(user_lang, "admin_work_no_channels")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_lang, "btn_add_channel"), callback_data="work_add_channel")],
        [InlineKeyboardButton(text="✏️ Изменить ссылку", callback_data="work_edit_channel")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_remove_channel"), callback_data="work_remove_channel")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_clear_channels"), callback_data="work_clear_channels")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="tool_menu")]
    ])
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

# ДОБАВЬТЕ НОВЫЕ ОБРАБОТЧИКИ:
@dp.callback_query(lambda c: c.data == "work_edit_channel")
async def work_edit_channel(callback: types.CallbackQuery, state: FSMContext):
    """Показывает список каналов для выбора"""
    user_lang = await get_user_lang_from_state(state)
    channels = get_sponsor_channels()
    
    if not channels:
        await callback.answer(get_text(user_lang, "admin_work_no_channels"), show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for ch in channels:
        button_text = f"✏️ Канал {ch['channel_id']}"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=button_text, callback_data=f"work_edit_select_{ch['channel_id']}")
        ])
    
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="work_menu")
    ])
    
    await callback.message.edit_text(
        "✏️ <b>Выберите канал</b>\n\nОтправьте новую ссылку после выбора",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data.startswith("work_edit_select_"))
async def work_edit_select_channel(callback: types.CallbackQuery, state: FSMContext):
    """Выбор канала"""
    user_lang = await get_user_lang_from_state(state)
    channel_id = int(callback.data.split("_")[-1])
    
    await state.update_data(edit_channel_id=channel_id)
    await state.set_state(FSMStates.waiting_for_sponsor_channel_edit)
    
    await callback.message.edit_text(
        f"✏️ <b>Введите новую ссылку</b>\n\n"
        f"Канал ID: <code>{channel_id}</code>\n\n"
        f"Примеры:\n"
        f"• <code>https://t.me/username</code>\n"
        f"• <code>@username</code>\n"
        f"• или любая ссылка",
        parse_mode="HTML"
    )

@dp.message(FSMStates.waiting_for_sponsor_channel_edit)
async def process_sponsor_channel_edit(message: Message, state: FSMContext):
    """Просто сохраняет новую ссылку"""
    data = await state.get_data()
    channel_id = data.get('edit_channel_id')
    
    if not channel_id:
        await message.answer("❌ Ошибка")
        await state.clear()
        await show_work_menu(message, state)
        return
    
    new_link = message.text.strip()
    
    # Просто сохраняем ссылку как есть
    success, msg = update_sponsor_channel_link(message.from_user.id, channel_id, new_link)
    
    await message.answer(msg)
    
    if success:
        await state.clear()
        await show_work_menu(message, state)
    else:
        await state.set_state(FSMStates.main_menu)
@dp.callback_query(lambda c: c.data == "work_add_channel")
async def work_add_channel(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    await state.set_state(FSMStates.waiting_for_sponsor_channel)
    await callback.message.edit_text(get_text(user_lang, "enter_channel_link"), parse_mode="HTML")

@dp.message(FSMStates.waiting_for_sponsor_channel)
async def process_sponsor_channel(message: Message, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    text = message.text.strip()
    channel_id = None
    channel_link = text

    # Парсим ссылку
    if text.startswith('@'):
        # username
        try:
            chat = await bot.get_chat(text)
            channel_id = chat.id
        except Exception as e:
            await message.answer(get_text(user_lang, "invalid_channel_link"))
            return
    elif text.lstrip('-').isdigit():
        # numeric ID
        channel_id = int(text)
    else:
        # пробуем извлечь ID из ссылки
        match = re.search(r'(?:https?://)?(?:t\.me/|telegram\.me/)?([a-zA-Z0-9_]+)', text)
        if match:
            username = match.group(1)
            try:
                chat = await bot.get_chat(f"@{username}")
                channel_id = chat.id
            except:
                await message.answer(get_text(user_lang, "invalid_channel_link"))
                return
        else:
            await message.answer(get_text(user_lang, "invalid_channel_link"))
            return

    # Проверяем, что бот админ в канале
    try:
        bot_member = await bot.get_chat_member(channel_id, (await bot.me()).id)
        if bot_member.status not in ['administrator', 'creator']:
            await message.answer("❌ Бот не является администратором этого канала. Добавьте бота в администраторы.")
            return
    except Exception as e:
        await message.answer(f"❌ Не удалось проверить права бота: {e}")
        return

    # Сохраняем
    success, msg = add_sponsor_channel(message.from_user.id, channel_id, channel_link)
    await message.answer(msg)
    if success:
        await show_work_menu(message, state)
    else:
        await state.clear()

@dp.callback_query(lambda c: c.data == "work_remove_channel")
async def work_remove_channel(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    channels = get_sponsor_channels()
    if not channels:
        await callback.answer(get_text(user_lang, "admin_work_no_channels"), show_alert=True)
        return

    # Строим клавиатуру со списком каналов
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for ch in channels:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"❌ {ch['channel_link']}",
                callback_data=f"work_remove_confirm_{ch['channel_id']}"
            )
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="work_menu")
    ])
    await callback.message.edit_text(
        get_text(user_lang, "admin_work_list") + "\nВыберите канал для удаления:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data.startswith("work_remove_confirm_"))
async def work_remove_confirm(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    channel_id = int(callback.data.split("_")[-1])
    if remove_sponsor_channel(callback.from_user.id, channel_id):
        await callback.answer(get_text(user_lang, "channel_removed"), show_alert=True)
        await show_work_menu(callback.message, state)
    else:
        await callback.answer(get_text(user_lang, "channel_not_found"), show_alert=True)

@dp.callback_query(lambda c: c.data == "work_clear_channels")
async def work_clear_channels(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_lang, "btn_confirm_clear"), callback_data="work_clear_confirm")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="work_menu")]
    ])
    await callback.message.edit_text(
        get_text(user_lang, "confirm_clear_channels"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "work_clear_confirm")
async def work_clear_confirm(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    clear_sponsor_channels(callback.from_user.id)
    await callback.answer(get_text(user_lang, "channels_cleared"), show_alert=True)
    await show_work_menu(callback.message, state)

@dp.callback_query(lambda c: c.data == "work_menu")
async def work_menu_back(callback: types.CallbackQuery, state: FSMContext):
    await show_work_menu(callback.message, state)
@dp.message(FSMStates.waiting_for_activation_key)
async def process_activation_key(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    key_str = message.text.strip().upper()
    
    success, text = activate_key(user_id, key_str)
    
    # Переводим сообщение об успехе/ошибке
    if success:
        # Извлекаем days_text из текста ответа
        if "навсегда" in text:
            days_text = get_text(user_lang, "buy_menu_forever")
        else:
            days_text = text.split("на ")[1] if "на " in text else ""
        response_text = get_text(user_lang, "key_activated", days_text=days_text)
    else:
        response_text = get_text(user_lang, "key_not_found")
    
    await message.answer(response_text, parse_mode="HTML")
    
    await state.set_state(FSMStates.main_menu)
    if success:
        await profile_handler(message, state)
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(user_lang, "btn_try_another"), callback_data="activate_key")]
        ])
        await message.answer(get_text(user_lang, "try_another_key"), reply_markup=keyboard)
@dp.callback_query(lambda c: c.data == "activate_key")
async def activate_key_start(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    
    # УБРАНА ПРОВЕРКА ПОДПИСКИ
    # Пользователь может активировать ключ даже если у него уже есть подписка
    
    await state.set_state(FSMStates.waiting_for_activation_key)
    await callback.message.edit_text(
        get_text(user_lang, "activate_key_title"),
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data == "buy_menu")
async def buy_menu(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    
    usdt_rate = MANUAL_USDT_RATE
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    for plan, data in PLANS.items():
        days_str = get_text(user_lang, "buy_menu_forever") if plan == 'forever' else get_text(user_lang, "buy_menu_days", days=data['days'])
        price_rub = data['price']
        
        if usdt_rate:
            price_usdt = price_rub / usdt_rate
            button_text = f"{days_str} - {price_rub} RUB (~{price_usdt:.2f} USDT)"
        else:
            button_text = f"{days_str} - {price_rub} RUB"
        
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=button_text, callback_data=f"buy_{plan}")
        ])
    
    if is_trial_enabled() and not has_claimed_trial(callback.from_user.id):
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=get_text(user_lang, "btn_trial"), callback_data="claim_trial")])
    
    keyboard.inline_keyboard.append([InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="profile")])
    
    rate_info = f"\n<blockquote>{get_text(user_lang, 'exchange_rate', rate=usdt_rate)}</blockquote>" if usdt_rate else ""
    await callback.message.edit_text(
        get_text(user_lang, "buy_menu_title", rate_info=rate_info),
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def get_exchange_rate(fiat: str = 'RUB', crypto: str = 'USDT') -> float:
    """Получить текущий курс обмена"""
    headers = {'Crypto-Pay-API-Token': CRYPTO_PAY_TOKEN}
    async with aiohttp.ClientSession() as session:
        async with session.get(CRYPTO_PAY_API_URL + 'getExchangeRates', headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data['ok']:
                    for rate in data['result']:
                        if rate.get('is_valid') and rate.get('source') == crypto and rate.get('target') == fiat:
                            return float(rate['rate'])
    return None
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_subscription(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    plan = callback.data.split("_")[1]
    plan_data = PLANS[plan]
    
    days_str = get_text(user_lang, "buy_menu_forever") if plan == 'forever' else get_text(user_lang, "buy_menu_days", days=plan_data['days'])

    # Показываем "Создаём платёж..." в ТОМ ЖЕ сообщении (отдельное соо не плодим/не оставляем)
    try:
        await callback.message.edit_text(
            get_text(user_lang, "creating_payment", plan=days_str, price=plan_data['price']),
            parse_mode="HTML"
        )
    except Exception:
        pass

    invoice = await create_invoice(callback.from_user.id, plan)
    if invoice:
        url = (invoice.get('bot_invoice_url') or
               invoice.get('web_app_invoice_url') or
               invoice.get('mini_app_invoice_url') or
               invoice.get('pay_url'))

        if url:
            logging.info(f"🔗 Используем URL для оплаты: {url}")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_text(user_lang, "btn_pay").replace("💳 ", ""), url=url,
                                      style="success", icon_custom_emoji_id="5350716634413681396")],
                [InlineKeyboardButton(text=get_text(user_lang, "btn_check_payment"), callback_data=f"check_payment_{invoice['invoice_id']}")],
                [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="buy_menu", style="danger")],
            ])
            await callback.message.edit_text(
                get_text(user_lang, "invoice_created", price=plan_data['price']),
                reply_markup=keyboard, parse_mode="HTML"
            )
        else:
            logging.error("❌ Не найдено подходящего URL для оплаты")
            await callback.message.edit_text(get_text(user_lang, "payment_url_error"))
    else:
        await callback.message.edit_text(get_text(user_lang, "payment_error"))

@dp.callback_query(lambda c: c.data == "cancel_payment")
async def cancel_payment(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("check_payment_"))
async def check_payment(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    invoice_id = callback.data.split("check_payment_")[1]
    
    headers = {'Crypto-Pay-API-Token': CRYPTO_PAY_TOKEN}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{CRYPTO_PAY_API_URL}getInvoices?invoice_ids={invoice_id}", headers=headers) as resp:
            if resp.status != 200:
                await callback.answer(get_text(user_lang, "payment_error"), show_alert=True)
                return
            
            data = await resp.json()
            if not data['ok'] or not data['result']['items']:
                await callback.answer(get_text(user_lang, "invoice_not_found"), show_alert=True)
                return
            
            invoice = data['result']['items'][0]
            status = invoice['status']
            
            if status == 'paid':
                payload = json.loads(invoice['payload'])
                user_id = payload['user_id']
                
                if 'plan' in payload:
                    plan = payload['plan']
                    days = PLANS[plan]['days']
                    price = PLANS[plan]['price']
                    
                    now = datetime.now(moscow_tz).replace(tzinfo=None)
                    
                    if plan == 'forever':
                        expiration = now + timedelta(days=365*100)
                    else:
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
                        expiration = new_exp
                    
                    cursor.execute("UPDATE users SET subscription_expiration = ? WHERE user_id = ?", (expiration.isoformat(), user_id))
                    conn.commit()
                    
                    referrer_id = get_referrer_id(user_id)
                    if referrer_id:
                        earning = int(price * REF_PERCENT)
                        add_ref_earning(referrer_id, earning)
                        try:
                            await bot.send_message(referrer_id, get_text('ru', 'referral_purchase_notify', amount=earning))
                        except Exception as ref_e:
                            logging.error(f"Ошибка отправки рефералки referrer_id {referrer_id}: {ref_e}")
                    
                    days_text = get_text(user_lang, "buy_menu_forever") if plan == 'forever' else get_text(user_lang, "buy_menu_days", days=days)
                    await callback.message.edit_text(
                        get_text(user_lang, "payment_success", days_text=days_text)
                    )
                else:
                    await callback.message.edit_text(get_text(user_lang, "payment_unknown"))
            elif status == 'active':
                await callback.answer(get_text(user_lang, "payment_pending"), show_alert=True)
            else:
                await callback.answer(get_text(user_lang, "payment_expired"), show_alert=True)
@dp.callback_query(lambda c: c.data == "buy_with_ref")
async def buy_with_ref_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    ref_balance = get_ref_balance(user_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    for plan, data in PLANS.items():
        if ref_balance >= data['price']:
            days_str = get_text(user_lang, "buy_menu_forever") if plan == 'forever' else get_text(user_lang, "buy_menu_days", days=data['days'])
            button_text = f"{days_str} - {data['price']} RUB"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=button_text, callback_data=f"buy_ref_{plan}")
            ])
    
    keyboard.inline_keyboard.append([InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="profile")])
    
    await callback.message.edit_text(
        get_text(user_lang, "buy_with_ref_title", balance=ref_balance),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data.startswith("buy_ref_"))
async def buy_with_ref(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    plan = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    ref_balance = get_ref_balance(user_id)
    price = PLANS[plan]['price']
    
    if ref_balance < price:
        await callback.answer(get_text(user_lang, "insufficient_funds"))
        return
    
    days = PLANS[plan]['days']
    now = datetime.now(moscow_tz).replace(tzinfo=None)
    
    if plan == 'forever':
        expiration = now + timedelta(days=365*100)
        exp_str = expiration.isoformat()
    else:
        cursor.execute("SELECT subscription_expiration FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row[0]:
            try:
                current_exp = datetime.fromisoformat(row[0])
                current_exp = current_exp.replace(tzinfo=None)
                if current_exp > now:
                    new_exp = current_exp + timedelta(days=days)
                else:
                    new_exp = now + timedelta(days=days)
            except:
                new_exp = now + timedelta(days=days)
        else:
            new_exp = now + timedelta(days=days)
        exp_str = new_exp.isoformat()
    
    cursor.execute("UPDATE users SET subscription_expiration = ?, ref_balance = ref_balance - ? WHERE user_id = ?", (exp_str, price, user_id))
    conn.commit()
    
    days_text = get_text(user_lang, "buy_menu_forever") if plan == 'forever' else get_text(user_lang, "buy_menu_days", days=days)
    await callback.message.edit_text(
        get_text(user_lang, "purchased_with_ref", days_text=days_text)
    )
@dp.callback_query(lambda c: c.data == "withdraw_ref")
async def withdraw_ref(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    ref_balance = get_ref_balance(user_id)
    await state.set_state(FSMStates.waiting_for_withdrawal_amount)
    
    await callback.message.edit_text(
        get_text(user_lang, "withdraw_title", balance=ref_balance),
        parse_mode="HTML"
    )

@dp.message(FSMStates.waiting_for_withdrawal_amount)
async def process_withdrawal_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    ref_balance = get_ref_balance(user_id)
    
    try:
        amount = int(message.text)
        if amount < 200 or amount > ref_balance:
            await message.answer(get_text(user_lang, "withdraw_invalid_amount"))
            return
        
        request_id = create_withdrawal_request(user_id, amount)
        await message.answer(
            get_text(user_lang, "withdraw_request_created", amount=amount)
        )
        
        for admin_id in ADMIN_IDS:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_text(user_lang, "btn_complete_withdraw"), callback_data=f"complete_withdraw_{request_id}")]
            ])
            try:
                await bot.send_message(
                    admin_id, 
                    get_text(user_lang, "withdraw_admin_notify", user_id=user_id, amount=amount),
                    reply_markup=keyboard
                )
            except Exception as admin_e:
                logging.error(f"Ошибка отправки уведомления админу {admin_id}: {admin_e}")
        
        await state.set_state(FSMStates.main_menu)
    except:
        await message.answer(get_text(user_lang, "invalid_amount"))

@dp.callback_query(lambda c: c.data.startswith("complete_withdraw_"))
async def complete_withdraw(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(get_text(user_lang, "no_access"))
        return
    
    request_id = int(callback.data.split("_")[2])
    await state.update_data(request_id=request_id)
    await state.set_state(FSMStates.waiting_for_payout_link)
    await callback.message.edit_text(get_text(user_lang, "enter_payout_link"))
@dp.message(FSMStates.waiting_for_payout_link)
async def process_payout_link(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    user_lang = await get_user_lang_from_state(state)
    data = await state.get_data()
    request_id = data['request_id']
    payout_link = message.text
    
    user_id = complete_withdrawal(request_id, payout_link)
    if user_id:
        await message.answer(get_text(user_lang, "withdraw_completed"))
        try:
            await bot.send_message(
                user_id,
                get_text(user_lang, "withdraw_completed_user", link=payout_link)
            )
        except Exception as user_e:
            logging.error(f"Ошибка отправки подтверждения вывода user_id {user_id}: {user_e}")
    else:
        await message.answer(get_text(user_lang, "withdraw_not_found"))
    
    await state.set_state(FSMStates.main_menu)
@dp.callback_query(lambda c: c.data == "global_stats")
async def show_global_stats(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    
    stats = get_global_stats()
    
    text = f"""{get_text(user_lang, 'stats_title')}
{get_text(user_lang, 'stats_total_donate', total_donate=stats['total_donate'])}
{get_text(user_lang, 'stats_total_balance', total_balance=stats['total_balance'])}
{get_text(user_lang, 'stats_total_pending', total_pending=stats['total_pending'])}
{get_text(user_lang, 'stats_total_rap', total_rap=stats['total_rap'])}
{get_text(user_lang, 'stats_total_groups', total_groups_balance=stats['total_groups_balance'])}
{get_text(user_lang, 'stats_total_checked', total_cookies_checked=stats['total_cookies_checked'])}
{get_text(user_lang, 'stats_total_freshed', total_cookies_freshed=stats['total_cookies_freshed'])}"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back_menu"),icon_custom_emoji_id="5807619215321996754", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "checker")
async def checker_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    if not is_subscribed(user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(user_lang, "btn_profile"), callback_data="profile")]
        ])
        await callback.message.edit_text(
            get_text(user_lang, "checker_no_sub"),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    await load_and_merge_settings(user_id, state)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_settings"), 
            icon_custom_emoji_id="6021622729713652937",
            callback_data="settings"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_start_check"), 
            icon_custom_emoji_id="5807414083388971488",
            callback_data="start_check"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_back_menu"), 
            icon_custom_emoji_id="5807619215321996754",
            callback_data="main_menu"
        )
    ]
])
    
    await callback.message.edit_text(
        get_text(user_lang, "checker_menu"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data == "validator")
async def validator_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    if not is_subscribed(user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(user_lang, "btn_profile"), callback_data="profile")]
        ])
        await callback.message.edit_text(
            get_text(user_lang, "validator_no_sub"),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_lang, "btn_start_validation"), icon_custom_emoji_id="5807414083388971488", callback_data="start_validation")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back_menu"), icon_custom_emoji_id="5807619215321996754", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        get_text(user_lang, "validator_menu"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data == "fresher")
async def fresher_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    if not is_subscribed(user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(user_lang, "btn_profile"), callback_data="profile")]
        ])
        await callback.message.edit_text(
            get_text(user_lang, "fresher_no_sub"),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_lang, "btn_start_fresh"),icon_custom_emoji_id="5807414083388971488", callback_data="start_fresh")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back_menu"), icon_custom_emoji_id="5807619215321996754", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        get_text(user_lang, "fresher_menu"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "other_functions")
async def other_functions_menu(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_duplicator"), 
            icon_custom_emoji_id="6025960139876473191",  # Исправлено: строка вместо числа
            callback_data="duplicator"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_sorter"), 
            icon_custom_emoji_id="5258477770735885832",  # Исправлено: строка вместо числа
            callback_data="sorter"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_back_menu"), 
            icon_custom_emoji_id="5807619215321996754",  # Исправлено: строка вместо числа
            callback_data="main_menu"
        )
    ]
])
    
    await callback.message.edit_text(
        get_text(user_lang, "other_functions_title"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data == "main_menu")
async def main_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await load_and_merge_settings(user_id, state)
    user_lang = await get_user_lang_from_state(state)
    
    # Создаем клавиатуру с вашими ID эмодзи
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_checker"),
            icon_custom_emoji_id="6019205852831947754",  # Changed to string
            callback_data="checker"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_fresher"),
            icon_custom_emoji_id="5807492110059838726",  # Changed to string
            callback_data="fresher"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_validator"),
            icon_custom_emoji_id="6021659039367173797",  # Changed to string
            callback_data="validator"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_stats"),
            icon_custom_emoji_id="6021384767050618542",  # Changed to string
            callback_data="global_stats"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_profile"),
            icon_custom_emoji_id="6024039683904772353",  # Changed to string
            callback_data="profile"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_other"),
            icon_custom_emoji_id="6021401276904905698",  # Changed to string
            callback_data="other_functions"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(user_lang, "btn_language"),
            icon_custom_emoji_id="6030768072296502910",  # Changed to string
            callback_data="language_menu"
        )
    ]
])
    
    await state.set_state(FSMStates.main_menu)
    await callback.message.edit_text(
        get_text(user_lang, "welcome"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data == "settings")
async def settings_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    await load_and_merge_settings(user_id, state)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=get_text(user_lang, "btn_checks"), icon_custom_emoji_id="6021451978993834164", callback_data="checks")],
    [InlineKeyboardButton(text=get_text(user_lang, "btn_ingame"), icon_custom_emoji_id="5258508428212445001", callback_data="ingame")],
    [InlineKeyboardButton(text=get_text(user_lang, "btn_playtime"), icon_custom_emoji_id="5199457120428249992", callback_data="playtime")],
    [InlineKeyboardButton(text=get_text(user_lang, "btn_badges"), icon_custom_emoji_id="6021594546138257831", callback_data="badges")],
    [InlineKeyboardButton(text=get_text(user_lang, "btn_gamepasses"), icon_custom_emoji_id="6021428854889913572", callback_data="gamepasses")],
    [InlineKeyboardButton(text=get_text(user_lang, "btn_output_format"), icon_custom_emoji_id="6021856393114426113", callback_data="output_format")],
    [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), icon_custom_emoji_id="5807619215321996754", callback_data="checker")]
])
    
    await callback.message.edit_text(
        get_text(user_lang, "settings_title"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data == "output_format")
async def output_format_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    await load_and_merge_settings(user_id, state)
    data = await state.get_data()
    current_format = data.get('output_format', 'zip')
    
    format_names = {
        'zip': get_text(user_lang, "output_format_zip"),
        'txt': get_text(user_lang, "output_format_txt")
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    # Радио-выбор: активный формат — зелёный, остальные обычные
    fmt_row = []
    for fmt in ['zip', 'txt']:
        active = (current_format == fmt)
        btn = InlineKeyboardButton(text=format_names[fmt], callback_data=f"toggle_output_{fmt}")
        if active:
            btn = InlineKeyboardButton(text=format_names[fmt], callback_data=f"toggle_output_{fmt}", style="success")
        fmt_row.append(btn)
    keyboard.inline_keyboard.append(fmt_row)

    keyboard.inline_keyboard.append([InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="settings")])
    
    await callback.message.edit_text(
        get_text(user_lang, "output_format_title", current=format_names[current_format]),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data.startswith("toggle_output_"))
async def toggle_output_format(callback: types.CallbackQuery, state: FSMContext):
    fmt = callback.data.split("toggle_output_")[1]
    await state.update_data(output_format=fmt)
    save_user_settings(callback.from_user.id, await state.get_data())
    await output_format_menu(callback, state)

@dp.callback_query(lambda c: c.data == "checks")
async def checks_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    await load_and_merge_settings(user_id, state)
    data = await state.get_data()
    selected = data.get('selected_checks', {p: True for p in CHECK_PARAMS})
    
    for param in CHECK_PARAMS:
        if param not in selected:
            selected[param] = True
    
    if 'use_emoji' not in selected:
        selected['use_emoji'] = True
    
    await state.update_data(selected_checks=selected)
    save_user_settings(user_id, await state.get_data())
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    # Верхний ряд: выбрать всё (зелёный) / снять всё (красный)
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="Выбрать всё", callback_data="checks_all_on", style="success"),
        InlineKeyboardButton(text="Снять всё", callback_data="checks_all_off", style="danger"),
    ])
    # Параметры в 2 колонки: вкл — зелёная кнопка, выкл — красная (цвет = состояние)
    row = []
    for param, name in CHECK_PARAMS.items():
        on = bool(selected.get(param))
        btn = InlineKeyboardButton(
            text=name,
            callback_data=f"toggle_check_{param}",
            style="success" if on else "danger",
        )
        row.append(btn)
        if len(row) == 2:
            keyboard.inline_keyboard.append(row)
            row = []
    if row:
        keyboard.inline_keyboard.append(row)

    keyboard.inline_keyboard.append([InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="settings")])

    await callback.message.edit_text(
        get_text(user_lang, "checks_title"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data in ("checks_all_on", "checks_all_off"))
async def checks_toggle_all(callback: types.CallbackQuery, state: FSMContext):
    value = callback.data == "checks_all_on"
    data = await state.get_data()
    selected = data.get('selected_checks', {p: True for p in CHECK_PARAMS})
    if all(selected.get(p) == value for p in CHECK_PARAMS):
        await callback.answer("Уже так ✅" if value else "Уже снято")
        return
    for param in CHECK_PARAMS:
        selected[param] = value
    await state.update_data(selected_checks=selected)
    save_user_settings(callback.from_user.id, await state.get_data())
    await checks_menu(callback, state)

@dp.callback_query(lambda c: c.data.startswith("toggle_check_"))
async def toggle_check(callback: types.CallbackQuery, state: FSMContext):
    param = callback.data.split("toggle_check_")[1]
    data = await state.get_data()
    selected = data.get('selected_checks', {p: True for p in CHECK_PARAMS})
    selected[param] = not selected.get(param, True)
    await state.update_data(selected_checks=selected)
    save_user_settings(callback.from_user.id, await state.get_data())
    await checks_menu(callback, state)
@dp.callback_query(lambda c: c.data.startswith("toggle_ingame_"))
async def toggle_ingame(callback: types.CallbackQuery, state: FSMContext):
    short = callback.data.split("toggle_ingame_")[1]
    data = await state.get_data()
    selected = data.get('selected_ingame', {})
    current_value = selected.get(short, True)
    selected[short] = not current_value
    await state.update_data(selected_ingame=selected)
    save_user_settings(callback.from_user.id, await state.get_data())
    await ingame_menu(callback, state)
@dp.callback_query(lambda c: c.data == "ingame")
async def ingame_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    await load_and_merge_settings(user_id, state)
    data = await state.get_data()
    ingame_overrides = data.get('ingame_overrides', {})
    selected = data.get('selected_ingame', {})

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for short in GAMES:
        info = GAMES[short].copy()
        if short in ingame_overrides:
            info.update(ingame_overrides[short])
        name = info['name']

        is_selected = selected.get(short, True)
        game_row = [
            InlineKeyboardButton(text=name, callback_data=f"toggle_ingame_{short}",
                                 style="success" if is_selected else "danger"),
            InlineKeyboardButton(text="✏️", callback_data=f"change_ingame_{short}"),
        ]
        if short in ingame_overrides:
            game_row.append(InlineKeyboardButton(text="🔄", callback_data=f"reset_ingame_{short}"))
        keyboard.inline_keyboard.append(game_row)

    keyboard.inline_keyboard.append([InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="settings")])

    await callback.message.edit_text(
        get_text(user_lang, "ingame_title"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data == "playtime")
async def playtime_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    await load_and_merge_settings(user_id, state)
    data = await state.get_data()
    playtime_overrides = data.get('playtime_overrides', {})
    selected = data.get('selected_playtime', {})

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for short in GAMES:
        info = GAMES[short].copy()
        if short in playtime_overrides:
            info.update(playtime_overrides[short])
        name = info['name']

        is_selected = selected.get(short, True)
        game_row = [
            InlineKeyboardButton(text=name, callback_data=f"toggle_playtime_{short}",
                                 style="success" if is_selected else "danger"),
            InlineKeyboardButton(text="✏️", callback_data=f"change_playtime_{short}"),
        ]
        if short in playtime_overrides:
            game_row.append(InlineKeyboardButton(text="🔄", callback_data=f"reset_playtime_{short}"))
        keyboard.inline_keyboard.append(game_row)

    keyboard.inline_keyboard.append([InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="settings")])

    await callback.message.edit_text(
        get_text(user_lang, "playtime_title"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data.startswith("change_ingame_"))
async def change_ingame_handler(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    short = callback.data.split("change_ingame_")[1]
    
    if short not in GAMES:
        await callback.answer("❌ " + get_text(user_lang, "invalid_game_url"), show_alert=True)
        return
    
    await state.update_data(temp_short=short, change_type='ingame')
    await state.set_state(FSMStates.waiting_for_game_url)

    await callback.message.edit_text(
        get_text(user_lang, "send_game_url", game_name=GAMES[short]['name']),
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data.startswith("reset_ingame_"))
async def reset_ingame_handler(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    short = callback.data.split("reset_ingame_")[1]
    
    if short not in GAMES:
        await callback.answer("❌ " + get_text(user_lang, "invalid_game_url"), show_alert=True)
        return

    reset_user_game_override(callback.from_user.id, short, 'ingame')

    overrides_data = get_user_game_overrides(callback.from_user.id)
    await state.update_data(
        ingame_overrides=overrides_data.get('ingame', {}),
        playtime_overrides=overrides_data.get('playtime', {})
    )

    await callback.answer("✅ " + get_text(user_lang, "game_reset", game_short=short.upper()))
    await ingame_menu(callback, state)

@dp.callback_query(lambda c: c.data.startswith("reset_playtime_"))
async def reset_playtime_handler(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    short = callback.data.split("reset_playtime_")[1]
    
    if short not in GAMES:
        await callback.answer("❌ " + get_text(user_lang, "invalid_game_url"), show_alert=True)
        return

    reset_user_game_override(callback.from_user.id, short, 'playtime')

    overrides_data = get_user_game_overrides(callback.from_user.id)
    await state.update_data(
        ingame_overrides=overrides_data.get('ingame', {}),
        playtime_overrides=overrides_data.get('playtime', {})
    )

    await callback.answer("✅ " + get_text(user_lang, "game_reset", game_short=short.upper()))
    await playtime_menu(callback, state)
    
@dp.callback_query(lambda c: c.data.startswith("toggle_playtime_"))
async def toggle_playtime(callback: types.CallbackQuery, state: FSMContext):
    short = callback.data.split("toggle_playtime_")[1]
    data = await state.get_data()
    selected = data.get('selected_playtime', {})
    current_value = selected.get(short, True)
    selected[short] = not current_value
    await state.update_data(selected_playtime=selected)
    save_user_settings(callback.from_user.id, await state.get_data())
    await playtime_menu(callback, state)
@dp.callback_query(lambda c: c.data == "badges")
async def badges_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    await load_and_merge_settings(user_id, state)
    data = await state.get_data()
    selected = data.get('selected_badges', {})
    custom_configs = get_user_custom_configs(user_id, 'badges')
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    _row = []
    for game in BADGES_PER_GAME:
        _on = bool(selected.get(game, False))
        _row.append(InlineKeyboardButton(text=game, callback_data=f"toggle_badge_{game}",
                                         style="success" if _on else "danger"))
        if len(_row) == 2:
            keyboard.inline_keyboard.append(_row); _row = []
    for config_name in custom_configs:
        _on = bool(selected.get(config_name, False))
        _row.append(InlineKeyboardButton(text=config_name, callback_data=f"toggle_badge_{config_name}",
                                         style="success" if _on else "danger"))
        if len(_row) == 2:
            keyboard.inline_keyboard.append(_row); _row = []
    if _row:
        keyboard.inline_keyboard.append(_row)

    keyboard.inline_keyboard.extend([
        [InlineKeyboardButton(text=get_text(user_lang, "custom_badges_prompt").replace("📥 <b>", "").replace("</b>", ""), callback_data="custom_badges")],
        [InlineKeyboardButton(text=get_text(user_lang, "config_name_prompt_badges").replace("🆕 <b>", "").replace("</b>", ""), callback_data="create_config_badges")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="settings")]
    ])
    
    await callback.message.edit_text(
        get_text(user_lang, "badges_title"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.update_data(selected_badges=selected)
@dp.callback_query(lambda c: c.data.startswith("toggle_badge_"))
async def toggle_badge(callback: types.CallbackQuery, state: FSMContext):
    game = callback.data.split("toggle_badge_")[1]
    data = await state.get_data()
    selected = data.get('selected_badges', {})
    selected[game] = not selected.get(game, False)
    await state.update_data(selected_badges=selected)
    save_user_settings(callback.from_user.id, await state.get_data())
    await badges_menu(callback, state)
@dp.callback_query(lambda c: c.data == "custom_badges")
async def custom_badges(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    await state.set_state(FSMStates.waiting_for_custom_badges)
    await callback.message.edit_text(
        get_text(user_lang, "custom_badges_prompt"),
        parse_mode="HTML"
    )
@dp.message(FSMStates.waiting_for_custom_badges)
async def process_custom_badges(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    try:
        ids = [int(id.strip()) for id in re.split(r'[,\n]', message.text) if id.strip().isdigit()]
        if ids:
            config_name = f"Custom_{uuid.uuid4().hex[:8]}"
            add_user_custom_config(user_id, 'badges', config_name, ids)
            await message.answer(
                get_text(user_lang, "custom_saved", name=config_name),
                parse_mode="HTML"
            )
        else:
            await message.answer(get_text(user_lang, "no_valid_ids"), parse_mode="HTML")
            await state.set_state(FSMStates.settings)
            return
    except Exception as e:
        logging.error(f"Ошибка парсинга кастомных бейджей для user_id {user_id}: {e}")
        await message.answer(get_text(user_lang, "no_valid_ids"), parse_mode="HTML")
        await state.set_state(FSMStates.settings)
        return

    # Возвращаемся в меню бейджей
    custom_configs = get_user_custom_configs(user_id, 'badges')
    data = await state.get_data()
    selected = data.get('selected_badges', {})
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    _row = []
    for game in BADGES_PER_GAME:
        _on = bool(selected.get(game, False))
        _row.append(InlineKeyboardButton(text=game, callback_data=f"toggle_badge_{game}", style="success" if _on else "danger"))
        if len(_row) == 2:
            keyboard.inline_keyboard.append(_row); _row = []
    for cfg in custom_configs:
        _on = bool(selected.get(cfg, False))
        _row.append(InlineKeyboardButton(text=cfg, callback_data=f"toggle_badge_{cfg}", style="success" if _on else "danger"))
        if len(_row) == 2:
            keyboard.inline_keyboard.append(_row); _row = []
    if _row:
        keyboard.inline_keyboard.append(_row)

    keyboard.inline_keyboard.extend([
        [InlineKeyboardButton(text=get_text(user_lang, "custom_badges_prompt").replace("📥 <b>", "").replace("</b>", ""), callback_data="custom_badges")],
        [InlineKeyboardButton(text=get_text(user_lang, "config_name_prompt_badges").replace("🆕 <b>", "").replace("</b>", ""), callback_data="create_config_badges")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="settings")]
    ])
    
    await message.answer(
        get_text(user_lang, "badges_title"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(FSMStates.settings)
@dp.callback_query(lambda c: c.data == "create_config_badges")
async def create_config_badges(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    await state.update_data(config_type='badges')
    await state.set_state(FSMStates.waiting_for_config_name)
    await callback.message.edit_text(
        get_text(user_lang, "config_name_prompt_badges"),
        parse_mode="HTML"
    )
@dp.message(FSMStates.waiting_for_config_name)
async def process_config_name(message: Message, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    config_name = message.text.strip()
    data = await state.get_data()
    await state.update_data(config_name=config_name)
    
    if data['config_type'] == 'badges':
        await state.set_state(FSMStates.waiting_for_config_badges)
        await message.answer(
            get_text(user_lang, "custom_badges_prompt"),
            parse_mode="HTML"
        )
    elif data['config_type'] == 'gamepasses':
        await state.set_state(FSMStates.waiting_for_config_gamepasses)
        await message.answer(
            get_text(user_lang, "custom_gamepasses_prompt"),
            parse_mode="HTML"
        )
@dp.message(FSMStates.waiting_for_config_badges)
async def process_config_badges(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_lang = await get_user_lang_from_state(state)
    data = await state.get_data()
    config_name = data['config_name']
    
    try:
        ids = [int(id.strip()) for id in re.split(r'[,\n]', message.text) if id.strip().isdigit()]
        if ids:
            add_user_custom_config(user_id, 'badges', config_name, ids)
            selected = data.get('selected_badges', {})
            selected[config_name] = False
            await state.update_data(selected_badges=selected)
            save_user_settings(user_id, await state.get_data())
            
            await message.answer(
                get_text(user_lang, "config_created", name=config_name),
                parse_mode="HTML"
            )
        else:
            await message.answer(get_text(user_lang, "no_valid_ids"), parse_mode="HTML")
            await state.set_state(FSMStates.settings)
            return
    except Exception as e:
        logging.error(f"Ошибка создания конфига бейджей для user_id {user_id}: {e}")
        await message.answer(get_text(user_lang, "no_valid_ids"), parse_mode="HTML")
        await state.set_state(FSMStates.settings)
        return

    # Возвращаемся в меню бейджей - ОТПРАВЛЯЕМ НОВОЕ СООБЩЕНИЕ, а не редактируем старое
    await state.set_state(FSMStates.settings)
    
    # Получаем обновлённые данные
    data = await state.get_data()
    selected = data.get('selected_badges', {})
    custom_configs = get_user_custom_configs(user_id, 'badges')
    
    # Формируем клавиатуру (копия кода из badges_menu)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    _row = []
    for game in BADGES_PER_GAME:
        _on = bool(selected.get(game, False))
        _row.append(InlineKeyboardButton(text=game, callback_data=f"toggle_badge_{game}",
                                         style="success" if _on else "danger"))
        if len(_row) == 2:
            keyboard.inline_keyboard.append(_row); _row = []
    for config_name in custom_configs:
        _on = bool(selected.get(config_name, False))
        _row.append(InlineKeyboardButton(text=config_name, callback_data=f"toggle_badge_{config_name}",
                                         style="success" if _on else "danger"))
        if len(_row) == 2:
            keyboard.inline_keyboard.append(_row); _row = []
    if _row:
        keyboard.inline_keyboard.append(_row)

    keyboard.inline_keyboard.extend([
        [InlineKeyboardButton(text=get_text(user_lang, "custom_badges_prompt").replace("📥 <b>", "").replace("</b>", ""), callback_data="custom_badges")],
        [InlineKeyboardButton(text=get_text(user_lang, "config_name_prompt_badges").replace("🆕 <b>", "").replace("</b>", ""), callback_data="create_config_badges")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="settings")]
    ])
    
    await message.answer(
        get_text(user_lang, "badges_title"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data == "badges_lists")
async def badges_lists(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get('selected_badges', {game: False for game in list(BADGES_PER_GAME) + list(get_user_custom_configs(callback.from_user.id, 'badges'))})
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    _row = []
    for game in BADGES_PER_GAME:
        _on = bool(selected.get(game, False))
        _row.append(InlineKeyboardButton(text=game, callback_data=f"toggle_badge_{game}", style="success" if _on else "danger"))
        if len(_row) == 2:
            keyboard.inline_keyboard.append(_row); _row = []
    if _row:
        keyboard.inline_keyboard.append(_row)
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="badges")])
    await callback.message.edit_text("📋 <b>Готовые списки бейджей</b>\nВыберите списки для проверки:", reply_markup=keyboard, parse_mode="HTML")
@dp.callback_query(lambda c: c.data == "gamepasses")
async def gamepasses_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    await load_and_merge_settings(user_id, state)
    data = await state.get_data()
    selected = data.get('selected_gamepasses', {})
    custom_configs = get_user_custom_configs(user_id, 'gamepasses')
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    _row = []
    for game in GAMEPASSES_PER_GAME:
        _on = bool(selected.get(game, False))
        _row.append(InlineKeyboardButton(text=game, callback_data=f"toggle_gp_{game}",
                                         style="success" if _on else "danger"))
        if len(_row) == 2:
            keyboard.inline_keyboard.append(_row); _row = []
    for config_name in custom_configs:
        _on = bool(selected.get(config_name, False))
        _row.append(InlineKeyboardButton(text=config_name, callback_data=f"toggle_gp_{config_name}",
                                         style="success" if _on else "danger"))
        if len(_row) == 2:
            keyboard.inline_keyboard.append(_row); _row = []
    if _row:
        keyboard.inline_keyboard.append(_row)

    keyboard.inline_keyboard.extend([
        [InlineKeyboardButton(text=get_text(user_lang, "custom_gamepasses_prompt").replace("📥 <b>", "").replace("</b>", ""), callback_data="custom_gamepasses")],
        [InlineKeyboardButton(text=get_text(user_lang, "config_name_prompt_gamepasses").replace("🆕 <b>", "").replace("</b>", ""), callback_data="create_config_gamepasses")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="settings")]
    ])
    
    await callback.message.edit_text(
        get_text(user_lang, "gamepasses_title"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.update_data(selected_gamepasses=selected)
@dp.callback_query(lambda c: c.data.startswith("toggle_gp_"))
async def toggle_gp(callback: types.CallbackQuery, state: FSMContext):
    game = callback.data.split("toggle_gp_")[1]
    data = await state.get_data()
    selected = data.get('selected_gamepasses', {})
    selected[game] = not selected.get(game, False)
    await state.update_data(selected_gamepasses=selected)
    save_user_settings(callback.from_user.id, await state.get_data())
    await gamepasses_menu(callback, state)
@dp.callback_query(lambda c: c.data == "custom_gamepasses")
async def custom_gamepasses(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    await state.set_state(FSMStates.waiting_for_custom_gamepasses)
    await callback.message.edit_text(
        get_text(user_lang, "custom_gamepasses_prompt"),
        parse_mode="HTML"
    )
@dp.message(FSMStates.waiting_for_custom_gamepasses)
async def process_custom_gamepasses(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    try:
        ids = [int(id.strip()) for id in re.split(r'[,\n]', message.text) if id.strip().isdigit()]
        if ids:
            config_name = f"Custom_{uuid.uuid4().hex[:8]}"
            add_user_custom_config(user_id, 'gamepasses', config_name, ids)
            await message.answer(
                get_text(user_lang, "custom_gamepasses_saved", name=config_name),
                parse_mode="HTML"
            )
        else:
            await message.answer(get_text(user_lang, "no_valid_ids"), parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка парсинга кастомных геймпассов для user_id {user_id}: {e}")
        await message.answer(get_text(user_lang, "no_valid_ids"), parse_mode="HTML")
    
    await state.set_state(FSMStates.settings)
    await gamepasses_menu(types.CallbackQuery(message=message, data="gamepasses", from_user=message.from_user), state)
@dp.callback_query(lambda c: c.data == "create_config_gamepasses")
async def create_config_gamepasses(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    await state.update_data(config_type='gamepasses')
    await state.set_state(FSMStates.waiting_for_config_name)
    await callback.message.edit_text(
        get_text(user_lang, "config_name_prompt_gamepasses"),
        parse_mode="HTML"
    )
@dp.message(FSMStates.waiting_for_config_gamepasses)
async def process_config_gamepasses(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_lang = await get_user_lang_from_state(state)
    data = await state.get_data()
    config_name = data['config_name']
    
    try:
        ids = [int(id.strip()) for id in re.split(r'[,\n]', message.text) if id.strip().isdigit()]
        if ids:
            add_user_custom_config(user_id, 'gamepasses', config_name, ids)
            selected = data.get('selected_gamepasses', {})
            selected[config_name] = False
            await state.update_data(selected_gamepasses=selected)
            save_user_settings(user_id, await state.get_data())
            
            await message.answer(
                get_text(user_lang, "config_created", name=config_name),
                parse_mode="HTML"
            )
        else:
            await message.answer(get_text(user_lang, "no_valid_ids"), parse_mode="HTML")
            await state.set_state(FSMStates.settings)
            return
    except Exception as e:
        logging.error(f"Ошибка создания конфига геймпассов для user_id {user_id}: {e}")
        await message.answer(get_text(user_lang, "no_valid_ids"), parse_mode="HTML")
        await state.set_state(FSMStates.settings)
        return

    # Возвращаемся в меню геймпассов - ОТПРАВЛЯЕМ НОВОЕ СООБЩЕНИЕ, а не редактируем старое
    await state.set_state(FSMStates.settings)
    
    # Получаем обновлённые данные
    data = await state.get_data()
    selected = data.get('selected_gamepasses', {})
    custom_configs = get_user_custom_configs(user_id, 'gamepasses')
    
    # Формируем клавиатуру (копия кода из gamepasses_menu)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    _row = []
    for game in GAMEPASSES_PER_GAME:
        _on = bool(selected.get(game, False))
        _row.append(InlineKeyboardButton(text=game, callback_data=f"toggle_gp_{game}",
                                         style="success" if _on else "danger"))
        if len(_row) == 2:
            keyboard.inline_keyboard.append(_row); _row = []
    for config_name in custom_configs:
        _on = bool(selected.get(config_name, False))
        _row.append(InlineKeyboardButton(text=config_name, callback_data=f"toggle_gp_{config_name}",
                                         style="success" if _on else "danger"))
        if len(_row) == 2:
            keyboard.inline_keyboard.append(_row); _row = []
    if _row:
        keyboard.inline_keyboard.append(_row)

    keyboard.inline_keyboard.extend([
        [InlineKeyboardButton(text=get_text(user_lang, "custom_gamepasses_prompt").replace("📥 <b>", "").replace("</b>", ""), callback_data="custom_gamepasses")],
        [InlineKeyboardButton(text=get_text(user_lang, "config_name_prompt_gamepasses").replace("🆕 <b>", "").replace("</b>", ""), callback_data="create_config_gamepasses")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="settings")]
    ])
    
    await message.answer(
        get_text(user_lang, "gamepasses_title"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
@dp.message(Command('keys'))
async def keys_handler(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Нет доступа")
        return
    
    args = message.text.split()[1:]
    if len(args) != 2:
        await message.answer(
            "❌ Формат: /keys <plan> <count>\n"
            f"Доступные планы: {', '.join(PLANS.keys())}\n"
            "Пример: /keys month 10"
        )
        return
    
    plan, count_str = args
    try:
        count = int(count_str)
        if not (1 <= count <= 100):
            raise ValueError
    except ValueError:
        await message.answer("❌ Количество ключей должно быть от 1 до 100")
        return
    
    if plan not in PLANS:
        await message.answer(f"❌ Некорректный план. Доступные: {', '.join(PLANS.keys())}")
        return
    
    try:
        keys = create_activation_keys(message.from_user.id, plan, count)
        keys_text = "\n".join(keys)
        await message.answer(
            f"✅ Создано <b>{count}</b> ключей для плана <b>{plan}</b>:\n\n"
            f"<code>{keys_text}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка создания ключей: {e}")
        await message.answer("❌ Ошибка при создании ключей")

@dp.callback_query(lambda c: c.data == "gamepasses_lists")
async def gamepasses_lists(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get('selected_gamepasses', {game: False for game in list(GAMEPASSES_PER_GAME) + list(get_user_custom_configs(callback.from_user.id, 'gamepasses'))})
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    _row = []
    for game in GAMEPASSES_PER_GAME:
        _on = bool(selected.get(game, False))
        _row.append(InlineKeyboardButton(text=game, callback_data=f"toggle_gp_{game}", style="success" if _on else "danger"))
        if len(_row) == 2:
            keyboard.inline_keyboard.append(_row); _row = []
    if _row:
        keyboard.inline_keyboard.append(_row)
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="gamepasses")])
    await callback.message.edit_text("📋 <b>Готовые списки геймпассов</b>\nВыберите списки для проверки:", reply_markup=keyboard, parse_mode="HTML")
@dp.callback_query(lambda c: c.data == "start_check")
async def start_check(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    await state.set_state(FSMStates.waiting_for_file)
    await callback.message.edit_text(
        get_text(user_lang, "send_cookie_file"),
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data == "start_validation")
async def start_validation(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    await state.set_state(FSMStates.waiting_for_validation_file)
    await callback.message.edit_text(
        get_text(user_lang, "send_validation_file"),
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "start_fresh")
async def start_fresh(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    await state.set_state(FSMStates.waiting_for_file_fresh)
    await callback.message.edit_text(
        get_text(user_lang, "fresher_warning"),
        parse_mode="HTML"
    )
@dp.message(FSMStates.waiting_for_validation_file)
async def process_validation_file(message: Message, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    is_valid_doc, reason = _validate_txt_document(message.document)

    if is_valid_doc:
        temp_path = None
        try:
            file_id = message.document.file_id
            file_info = await bot.get_file(file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
                temp_file.write(downloaded_file.getvalue())
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_path = temp_file.name
            
            raw_cookies = await cookie_processor.extract_cookies_from_file(temp_path)
            cookies = list(raw_cookies)
            
            if not cookies:
                await message.answer(get_text(user_lang, "no_cookies"), parse_mode="HTML")
                await state.set_state(FSMStates.main_menu)
                return
            
            update_global_cookies_checked(len(cookies))
            increment_user_checked(message.from_user.id, len(cookies))
            proxies = load_proxies("proxies.txt")
            
            progress_msg = await message.answer(
                get_text(user_lang, "progress_validating", current=0, total=len(cookies)),
                parse_mode="HTML"
            )
            
            last_update = 0
            progress_lock = asyncio.Lock()
            
            async def update_progress(completed, total):
                nonlocal last_update
                async with progress_lock:
                    current_time = time.time()
                    if current_time - last_update >= 3 or completed == total:
                        text = get_text(user_lang, "progress_validating", current=completed, total=total)
                        await bot.edit_message_text(
                            text=text,
                            chat_id=message.chat.id,
                            message_id=progress_msg.message_id,
                            parse_mode="HTML"
                        )
                        last_update = current_time
                await asyncio.sleep(0)
            
            valid_results = await cookie_processor.validate_cookie_batch(cookies, proxies, update_progress)
            valid_cookies = [r['cookie'] for r in valid_results]

            total_cookies = len(cookies)
            valid_count = len(valid_cookies)
            invalid_count = total_cookies - valid_count

            if valid_cookies:
                unique_filename = f"valid_cookies_{uuid.uuid4().hex[:8]}.txt"
                with open(unique_filename, "w", encoding="utf-8") as f:
                    for cookie in valid_cookies:
                        f.write(cookie + "\n")
                
                result_text = get_text(user_lang, "validation_results", total=total_cookies, valid=valid_count, invalid=invalid_count)
                
                await bot.delete_message(message.chat.id, progress_msg.message_id)
                await message.answer_document(
                    FSInputFile(unique_filename),
                    caption=result_text,
                    parse_mode="HTML"
                )
                
                os.remove(unique_filename)
            else:
                await bot.edit_message_text(
                    text=get_text(user_lang, "no_valid_cookies_found"),
                    chat_id=message.chat.id,
                    message_id=progress_msg.message_id,
                    parse_mode="HTML"
                )
            
            await state.set_state(FSMStates.main_menu)
            
        except Exception as e:
            error_details = traceback.format_exc()
            logging.error(f"Ошибка обработки файла для валидации: {str(e)}\n{error_details}")
            await message.answer(f"❌ Ошибка: {str(e)}")
            await state.set_state(FSMStates.main_menu)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
    else:
        if reason == "too_large":
            await message.answer("❌ Файл слишком большой. Максимальный размер: 8 MB.")
        else:
            await message.answer(get_text(user_lang, "invalid_format"))
       
@dp.message(FSMStates.waiting_for_file_fresh)
async def process_file_fresh(message: Message, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)

    is_valid_doc, reason = _validate_txt_document(message.document)
    if not is_valid_doc:
        if reason == "too_large":
            await message.answer("❌ Файл слишком большой. Максимальный размер: 8 MB.")
        else:
            await message.answer(get_text(user_lang, "invalid_format"))
        return

    temp_path = None
    status_msg = None
    try:
        file_id = message.document.file_id
        file_info = await bot.get_file(file_id)
        downloaded_file = await bot.download_file(file_info.file_path)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
            temp_file.write(downloaded_file.getvalue())
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = temp_file.name

        raw_cookies = await cookie_processor.extract_cookies_from_file(temp_path)
        cookies = list(raw_cookies)

        if not cookies:
            await message.answer(get_text(user_lang, "no_cookies"), parse_mode="HTML")
            await state.set_state(FSMStates.main_menu)
            return

        update_global_cookies_freshed(len(cookies))
        increment_user_freshed(message.from_user.id, len(cookies))
        proxies = load_proxies("proxies.txt")

        status_msg = await message.answer(
            get_text(user_lang, "progress_validating", current=0, total=len(cookies)),
            parse_mode="HTML"
        )

        valid_results = await cookie_processor.validate_cookie_batch(cookies, proxies, progress_callback=None)
        valid_cookies = [r['cookie'] for r in valid_results]

        if not valid_cookies:
            await status_msg.edit_text(get_text(user_lang, "no_valid_cookies"), parse_mode="HTML")
            await state.set_state(FSMStates.main_menu)
            return

        await status_msg.edit_text(get_text(user_lang, "progress_freshing"), parse_mode="HTML")

        refreshed_cookies = await cookie_processor.fresh_cookie_batch(
            valid_cookies,
            progress_callback=None
        )

        success_count = len(refreshed_cookies) if refreshed_cookies else 0
        failed_count = len(valid_cookies) - success_count

        from datetime import datetime
        now = datetime.now()
        user = message.from_user
        username = f"@{user.username}" if user.username else user.full_name
        log_line = f"{username} id:{user.id} {len(cookies)} cookies {now.strftime('%H:%M')} {now.strftime('%d.%m.%Y')}"
        logging.info(f"🧊 FRESH: {log_line}")
        with open("fresh_logs.txt", "a", encoding="utf-8") as fl:
            fl.write(log_line + "\n")

        if success_count > 0:
            filename = f"fresh_cookies_{uuid.uuid4().hex[:8]}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                for cookie in refreshed_cookies:
                    f.write(cookie + "\n")

            caption = get_text(user_lang, "fresh_results_success", success=success_count, failed=failed_count)

            try:
                await status_msg.delete()
            except:
                pass

            file_sent = False
            try:
                await message.answer_document(
                    FSInputFile(filename),
                    caption=caption,
                    parse_mode="HTML"
                )
                file_sent = True
            except Exception as send_e:
                logging.error(f"Ошибка отправки файла фреша: {send_e}")

            if not file_sent:
                await message.answer(
                    get_text(user_lang, "fresh_file_error"),
                    parse_mode="HTML"
                )

            try:
                os.remove(filename)
            except:
                pass

        else:
            await status_msg.edit_text(
                get_text(user_lang, "fresh_results_no_success"),
                parse_mode="HTML"
            )

        await state.set_state(FSMStates.main_menu)

    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"Критическая ошибка в process_file_fresh: {e}\n{error_details}")
        try:
            await message.answer("❌ Произошла непредвиденная ошибка при фреше.")
        except:
            pass
        await state.set_state(FSMStates.main_menu)

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass
        if status_msg:
            try:
                print("олег лох это дуал")
            except:
                pass
@dp.message(Command('sabki'))
async def add_days_to_all_subscribers(message: Message):
    """Добавляет указанное количество дней всем пользователям с активной подпиской"""
    user_id = message.from_user.id
    
    # Проверка прав администратора
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Нет доступа")
        return
    
    # Парсим аргументы
    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "❌ Неправильный формат.\n"
            "Используйте: /sabki <количество_дней>\n"
            "Пример: /sabki 30"
        )
        return
    
    try:
        days = int(args[1])
        if days <= 0:
            await message.answer("❌ Количество дней должно быть положительным числом")
            return
        if days > 3650:  # Ограничение ~10 лет
            await message.answer("❌ Слишком большое значение (максимум 3650 дней)")
            return
    except ValueError:
        await message.answer("❌ Количество дней должно быть числом")
        return
    
    # Отправляем сообщение о начале процесса
    status_msg = await message.answer(f"⏳ Добавляю {days} дней всем активным подпискам...")
    
    try:
        # Вызываем функцию из database.py
        updated_count = add_days_to_all_active_subscribers(days)
        
        # Формируем сообщение с результатом
        if updated_count > 0:
            # Склонение слова "пользователь" для красоты
            if updated_count % 10 == 1 and updated_count % 100 != 11:
                users_word = "пользователю"
            elif 2 <= updated_count % 10 <= 4 and (updated_count % 100 < 10 or updated_count % 100 >= 20):
                users_word = "пользователям"
            else:
                users_word = "пользователям"
            
            result_text = (
                f"✅ <b>Готово!</b>\n\n"
                f"📊 Добавлено <b>{days}</b> дней\n"
                f"👥 {updated_count} {users_word} с активной подпиской\n\n"
                f"✨ Спасибо, друн!"
            )
        else:
            result_text = "❌ Нет пользователей с активной подпиской"
        
        await status_msg.edit_text(result_text, parse_mode="HTML")
        
        # Логируем действие
        logging.info(f"Админ {user_id} добавил {days} дней {updated_count} пользователям")
        
    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"Ошибка в команде /sabki: {e}\n{error_details}")
        await status_msg.edit_text(
            f"❌ <b>Ошибка при выполнении команды</b>\n\n"
            f"{str(e)}",
            parse_mode="HTML"
        )
@dp.callback_query(lambda c: c.data.startswith("set_lang_"))
async def set_language(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = callback.data.split("_")[2]  # ru или en
    
    # Сохраняем язык в БД
    set_user_language(user_id, lang)
    
    # Обновляем в state
    data = await state.get_data()
    data['language'] = lang
    await state.update_data(data)
    save_user_settings(user_id, data)
    
    await callback.answer()
    
    # Показываем подтверждение
    await callback.message.edit_text(
        get_text(lang, "language_changed")
    )
    
    # Возвращаемся в главное меню
    await state.set_state(FSMStates.main_menu)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(
            text=get_text(lang, "btn_checker"),
            icon_custom_emoji_id="6019205852831947754",  # Changed to string
            callback_data="checker"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(lang, "btn_fresher"),
            icon_custom_emoji_id="5807492110059838726",  # Changed to string
            callback_data="fresher"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(lang, "btn_validator"),
            icon_custom_emoji_id="6021659039367173797",  # Changed to string
            callback_data="validator"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(lang, "btn_stats"),
            icon_custom_emoji_id="6021384767050618542",  # Changed to string
            callback_data="global_stats"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(lang, "btn_profile"),
            icon_custom_emoji_id="6024039683904772353",  # Changed to string
            callback_data="profile"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(lang, "btn_other"),
            icon_custom_emoji_id="6021401276904905698",  # Changed to string
            callback_data="other_functions"
        )
    ],
    [
        InlineKeyboardButton(
            text=get_text(lang, "btn_language"),
            icon_custom_emoji_id="6030768072296502910",  # Changed to string
            callback_data="language_menu"
        )
    ]
])
    
    await callback.message.edit_text(
        get_text(lang, "welcome"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
@dp.message(FSMStates.waiting_for_game_url)
async def process_game_url(message: Message, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    url = message.text.strip()
    
    match = re.search(r'/games/(\d+)', url)
    if not match:
        await message.answer("❌ " + get_text(user_lang, "invalid_game_url"))
        return
    
    place_id = int(match.group(1))
    game_info = await cookie_processor.get_game_info(place_id)
    
    if not game_info or not game_info.get('universe_id'):
        await message.answer("❌ " + get_text(user_lang, "game_not_found"))
        return
    
    data = await state.get_data()
    short = data['temp_short']
    change_type = data.get('change_type', 'ingame')
    
    set_user_game_override(
        message.from_user.id,
        short,
        change_type,
        game_info['name'],
        place_id,
        game_info['universe_id']
    )
    
    overrides_data = get_user_game_overrides(message.from_user.id)
    await state.update_data(
        ingame_overrides=overrides_data.get('ingame', {}),
        playtime_overrides=overrides_data.get('playtime', {})
    )
    
    await message.answer(
        get_text(user_lang, "game_changed_success", game_short=short.upper(), game_name=game_info['name']),
        parse_mode="HTML"
    )

    data = await state.get_data()
    if change_type == 'ingame':
        selected = data.get('selected_ingame', {s: True for s in GAMES})
        overrides = data.get('ingame_overrides', {})
        menu_text = get_text(user_lang, "ingame_title")
        toggle_prefix = "toggle_ingame_"
        change_prefix = "change_ingame_"
        reset_prefix = "reset_ingame_"
    else:
        selected = data.get('selected_playtime', {s: True for s in GAMES})
        overrides = data.get('playtime_overrides', {})
        menu_text = get_text(user_lang, "playtime_title")
        toggle_prefix = "toggle_playtime_"
        change_prefix = "change_playtime_"
        reset_prefix = "reset_playtime_"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for short_code in GAMES:
        info = GAMES[short_code].copy()
        if short_code in overrides:
            info.update(overrides[short_code])
        name = info['name']
        is_selected = selected.get(short_code, True)
        game_row = [
            InlineKeyboardButton(text=name, callback_data=f"{toggle_prefix}{short_code}",
                                 style="success" if is_selected else "danger"),
            InlineKeyboardButton(text="✏️", callback_data=f"{change_prefix}{short_code}"),
        ]
        if short_code in overrides:
            game_row.append(InlineKeyboardButton(text="🔄", callback_data=f"{reset_prefix}{short_code}"))
        keyboard.inline_keyboard.append(game_row)

    keyboard.inline_keyboard.append([InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="settings")])
    
    await message.answer(menu_text, reply_markup=keyboard, parse_mode="HTML")
@dp.callback_query(lambda c: c.data.startswith("change_playtime_"))
async def change_playtime_handler(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    short = callback.data.split("change_playtime_")[1]
    
    if short not in GAMES:
        await callback.answer("❌ " + get_text(user_lang, "invalid_game_url"), show_alert=True)
        return
    
    # Важно: Указываем change_type='playtime'
    await state.update_data(temp_short=short, change_type='playtime')
    await state.set_state(FSMStates.waiting_for_game_url)

    await callback.message.edit_text(
        get_text(user_lang, "send_game_url", game_name=GAMES[short]['name']),
        parse_mode="HTML"
    )
@dp.message(Command('check'))
async def check_user_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS and user_id != 8793956932:
        await message.answer("❌ Нет доступа")
        return
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if not args:
        await message.answer("❌ Формат: /check <user_id или username>")
        return
    target = args[0]
    target_id = None
    user_info = None
    try:
        # Если это число — считаем user_id
        target_id = int(target)
    except ValueError:
        # Иначе — username (может быть с @ или без)
        try:
            # Приводим к формату @username для надёжности
            username_for_api = target if target.startswith('@') else f'@{target}'
            user_info = await bot.get_chat(username_for_api)
            target_id = user_info.id
        except Exception:
            await message.answer("❌ Пользователь не найден по username")
            return
    # Если user_info ещё не получен (был введён ID), получаем его по ID
    if user_info is None:
        try:
            user_info = await bot.get_chat(target_id)
        except Exception:
            user_info = None
    # Формируем строку с username/именем
    if user_info and user_info.username:
        username_str = f"@{user_info.username}"
    elif user_info:
        username_str = user_info.full_name
    else:
        username_str = "Не удалось получить"
    # Получаем всю остальную информацию (по target_id — это правильно)
    reg, exp, days_left = get_profile_info(target_id)
    ref_balance = get_ref_balance(target_id)
    ref_count = get_ref_count(target_id)
    checked_count, freshed_count = get_user_activity(target_id)
    referrer_id = get_referrer_id(target_id)
    settings = get_user_settings(target_id)
    has_trial = has_claimed_trial(target_id)
    is_sub = is_subscribed(target_id)
    custom_badges = get_user_custom_configs(target_id, 'badges')
    custom_gamepasses = get_user_custom_configs(target_id, 'gamepasses')
    pending_withdrawals = get_pending_withdrawals()
    user_pending = [w for w in pending_withdrawals if w['user_id'] == target_id]
    now = datetime.now(moscow_tz).replace(tzinfo=None)
    sub_text = "Активна" if is_sub else "Отсутствует"
    sub_expiry = exp.strftime('%d.%m.%Y %H:%M') if exp else "Нет"
    reg_text = reg.strftime('%d.%m.%Y %H:%M') if reg else 'Неизвестно'
    text = f"👤 <b>Информация о пользователе {target_id}</b>\n"
    text += f"Username: {username_str}\n"
    text += f"Регистрация: {reg_text}\n"
    text += f"Подписка: {sub_text} (истекает: {sub_expiry}, дней осталось: {days_left})\n"
    text += f"Реф. баланс: {ref_balance} RUB\n"
    text += f"Рефералов: {ref_count}\n"
    text += f"Проверено куков: {checked_count:,}\n"
    text += f"Фрешнуто куков: {freshed_count:,}\n"
    text += f"Реферер: {referrer_id if referrer_id else 'Нет'}\n"
    text += f"Получил trial: {'Да' if has_trial else 'Нет'}\n"
    text += f"\n⚙️ <b>Настройки:</b>\n{json.dumps(settings, indent=2, ensure_ascii=False)}\n"
    text += f"\n🎖️ <b>Кастомные бейджи:</b> {', '.join(custom_badges) if custom_badges else 'Нет'}\n"
    text += f"🎟️ <b>Кастомные геймпассы:</b> {', '.join(custom_gamepasses) if custom_gamepasses else 'Нет'}\n"
    text += f"\n💸 <b>Заявки на вывод:</b>\n"
    if user_pending:
        for w in user_pending:
            text += f"- ID: {w['id']}, Сумма: {w['amount']} RUB, Статус: pending\n"
    else:
        text += "Нет заявок\n"
    await message.answer(text, parse_mode="HTML")
@dp.message(Command('addsub'))
async def add_sub_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Нет доступа")
        return
    try:
        _, target_id, days = message.text.split()
        target_id = int(target_id)
        days = int(days)
        add_subscription(target_id, days)
        await message.answer(f"✅ Подписка добавлена для {target_id} на {days} дней")
        await bot.send_message(target_id, f"✅ Администратор добавил вам подписку на {days} дней!")
    except Exception as e:
        logging.error(f"Ошибка добавления подписки: {e}")
        await message.answer("❌ Формат: /addsub <user_id> <days>")
@dp.message(Command('post'))
async def admin_post(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Нет доступа")
        return
    
    # Проверяем, есть ли аргументы команды
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not args:
        # Показываем меню выбора режима рассылки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Рекламная рассылка", icon_custom_emoji_id="5350456973575865566", callback_data="post_ad")],
            [InlineKeyboardButton(text="📝 Обычная рассылка", callback_data="post_normal")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="post_cancel")]
        ])
        await message.answer("📤 <b>Выберите тип рассылки</b>\n\n• <b>Рекламная</b> - не отправляется пользователям, отключившим рекламу\n• <b>Обычная</b> - отправляется всем пользователям", reply_markup=keyboard, parse_mode="HTML")
        return
    
    # Если есть аргументы, используем старый формат для обратной совместимости
    text = message.html_text[6:] if message.html_text.startswith('/post ') else None
    if not text:
        await message.answer("❌ Укажите сообщение")
        return
    
    users = get_all_users()
    sent_count = 0
    for uid in users:
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
            sent_count += 1
        except Exception as post_e:
            logging.error(f"Ошибка отправки поста user_id {uid}: {post_e}")
    await message.answer(f"✅ Рассылка отправлена ({sent_count}/{len(users)} получателей)")

@dp.callback_query(lambda c: c.data == "post_cancel")
async def post_cancel_handler(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Рассылка отменена")

@dp.callback_query(lambda c: c.data in ["post_ad", "post_normal"])
async def post_mode_handler(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data.split("_")[1]  # "ad" или "normal"
    await state.update_data(post_mode=mode)
    await state.set_state(FSMStates.waiting_for_post_message)
    
    mode_text = '<tg-emoji emoji-id="5350456973575865566">📢</tg-emoji> <b>Рекламная рассылка</b>' if mode == "ad" else "📝 <b>Обычная рассылка</b>"
    instruction = "\n\nℹ️ Рекламные посты не отправляются пользователям, отключившим рекламные рассылки." if mode == "ad" else "\n\nℹ️ Обычные посты отправляются всем пользователям."
    
    await callback.message.edit_text(
        f"{mode_text}{instruction}\n\n"
        f"📤 <b>Отправьте сообщение для рассылки</b>\n\n"
        f"Поддерживается:\n"
        f"• Текст с HTML-разметкой\n"
        f"• Telegram эмодзи\n"
        f"• Фото и видео\n"
        f"• Для пометки как реклама добавьте <code>#реклама</code> в конце текста",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="post_cancel")]
        ]),
        parse_mode="HTML"
    )

@dp.message(FSMStates.waiting_for_post_message)
async def process_post_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Нет доступа")
        await state.clear()
        return
    
    data = await state.get_data()
    mode = data.get('post_mode', 'normal')
    
    # Определяем текст сообщения с сохранением форматирования и TG эмодзи
    if message.text is not None:
        text = message.html_text
    elif message.caption is not None:
        from aiogram.utils.text_decorations import html_decoration
        text = html_decoration.unparse(message.caption, message.caption_entities or [])
    else:
        text = ""
    
    # Проверяем, есть ли пометка #реклама
    is_ad = "#реклама" in text.lower() or mode == "ad"
    
    # Убираем #реклама из текста (добавим внизу для рекламных постов)
    if "#реклама" in text.lower():
        text = re.sub(r'\s*#реклама\s*', '', text, flags=re.IGNORECASE).strip()
        is_ad = True
    
    # Для рекламных постов добавляем #реклама внизу
    if is_ad:
        text = text + "\n\n#реклама"
    
    # Получаем список пользователей
    users = get_all_users()
    sent_count = 0
    skipped_count = 0
    
    # Отправляем сообщение пользователям
    for uid in users:
        try:
            # Если это рекламная рассылка, проверяем настройку пользователя
            if is_ad:
                if not is_subscribed(uid):
                    set_user_ad_broadcast_enabled(uid, True)
                if not get_user_ad_broadcast_enabled(uid):
                    skipped_count += 1
                    continue
            
            # Отправляем сообщение
            if message.photo:
                await bot.send_photo(uid, message.photo[-1].file_id, caption=text, parse_mode="HTML")
            elif message.video:
                await bot.send_video(uid, message.video.file_id, caption=text, parse_mode="HTML")
            elif message.document:
                await bot.send_document(uid, message.document.file_id, caption=text, parse_mode="HTML")
            else:
                await bot.send_message(uid, text, parse_mode="HTML")
            
            sent_count += 1
        except Exception as post_e:
            logging.error(f"Ошибка отправки поста user_id {uid}: {post_e}")
    
    # Формируем результат
    mode_text = "рекламная" if is_ad else "обычная"
    result_text = f"✅ <b>{mode_text.capitalize()} рассылка отправлена</b>\n\n"
    result_text += f"📊 Отправлено: <code>{sent_count}</code> получателей\n"
    if is_ad and skipped_count > 0:
        result_text += f"⏭️ Пропущено (отключили рекламу): <code>{skipped_count}</code> пользователей"
    
    await message.answer(result_text, parse_mode="HTML")
    await state.clear()



class FileMessageAdapter:
    """Адаптер для использования сохранённого файла с существующими обработчиками"""
    def __init__(self, callback_message, user, file_id, file_name='uploaded.txt'):
        self.chat = callback_message.chat
        self.from_user = user
        self.document = type('Document', (), {
            'file_id': file_id,
            'file_name': file_name
        })()
        self._msg = callback_message
        self.photo = None
        self.video = None

    async def answer(self, *args, **kwargs):
        return await self._msg.answer(*args, **kwargs)

    async def answer_document(self, *args, **kwargs):
        return await self._msg.answer_document(*args, **kwargs)

    async def answer_animation(self, *args, **kwargs):
        return await self._msg.answer_animation(*args, **kwargs)

# Обработчики для кнопок выбора действия с файлом
@dp.callback_query(lambda c: c.data.startswith("file_action_"))
async def file_action_handler(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[2]  # check, fresh, validate, duplicate, cancel
    user_lang = await get_user_lang_from_state(state)
    
    if action == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Операция отменена")
        return
    
    data = await state.get_data()
    file_id = data.get('file_id')
    cookie_text = data.get('cookie_text')
    
    if not file_id and not cookie_text:
        await callback.message.edit_text("❌ Файл не найден. Отправьте файл заново.")
        await state.clear()
        return
    
    # Если кук был отправлен текстом — создаём временный файл и загружаем в Telegram
    if not file_id and cookie_text:
        import tempfile
        os.makedirs('temp', exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, dir='temp') as f:
            f.write(cookie_text)
            temp_path = f.name
        from aiogram.types import FSInputFile
        doc = FSInputFile(temp_path, filename='cookie.txt')
        sent = await callback.message.answer_document(doc)
        os.remove(temp_path)
        file_id = sent.document.file_id
        try:
            await sent.delete()
        except:
            pass
    
    await callback.message.delete()
    
    adapter = FileMessageAdapter(callback.message, callback.from_user, file_id)
    
    if action == "check":
        await state.set_state(FSMStates.waiting_for_file)
        await process_file(adapter, state)
    elif action == "fresh":
        await state.set_state(FSMStates.waiting_for_file_fresh)
        await process_file_fresh(adapter, state)
    elif action == "validate":
        await state.set_state(FSMStates.waiting_for_validation_file)
        await process_validation_file(adapter, state)
    elif action == "duplicate":
        await state.set_state(FSMStates.waiting_for_file_duplicate)
        await process_file_duplicate(adapter, state)
@dp.message(Command('turn'))
async def turn_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Нет доступа")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Включить тестовую подписку", callback_data="turn_on")],
        [InlineKeyboardButton(text="Отключить тестовую подписку", callback_data="turn_off")]
    ])
    await message.answer("Управление тестовой подпиской:", reply_markup=keyboard)
@dp.callback_query(lambda c: c.data in ["turn_on", "turn_off"])
async def toggle_trial(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    enabled = callback.data == "turn_on"
    set_trial_enabled(enabled)
    status = "включена" if enabled else "отключена"
    await callback.message.edit_text(f"Тестовая подписка {status}.")
@dp.callback_query(lambda c: c.data == "claim_trial")
async def claim_trial(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    if not is_trial_enabled():
        await callback.answer(get_text(user_lang, "trial_unavailable"))
        return
    
    if has_claimed_trial(user_id):
        await callback.answer(get_text(user_lang, "trial_already_claimed"))
        return
    
    add_subscription(user_id, 1)
    set_claimed_trial(user_id, True)
    
    await callback.message.answer(get_text(user_lang, "trial_activated"))
    await profile_handler(callback, state)
# НОВАЯ КОМАНДА: /tool - подробная глобальная статистика
@dp.message(Command('tool'))
async def tool_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Нет доступа")
        return

    stats = get_global_stats()
    total_earned = stats.get('total_donate', 0)

    text = f"""
📊 <b>АДМИН ПАНЕЛЬ</b>

👥 Всего пользователей: <code>{len(get_all_users()):,}</code>
✅ Активных подписок: <code>{sum(1 for u in get_all_users() if is_subscribed(u)):,}</code>
💰 Общий реф. заработок: <code>{sum(get_ref_balance(u) for u in get_all_users()):,}</code> RUB"""


    await message.answer(text, parse_mode="HTML")





# ОБНОВЛЕННОЕ МЕНЮ tool (возврат из других меню)
@dp.callback_query(lambda c: c.data == "tool_menu")
async def back_to_tool(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа")
        return
    
    stats = get_global_stats()
    total_earned = stats.get('total_donate', 0)

    text = f"""
📊 <b>АДМИН ПАНЕЛЬ</b>

👥 Всего пользователей: <code>{len(get_all_users()):,}</code>
✅ Активных подписок: <code>{sum(1 for u in get_all_users() if is_subscribed(u)):,}</code>
💰 Общий реф. заработок: <code>{sum(get_ref_balance(u) for u in get_all_users()):,}</code> RUB"""

 

    await callback.message.edit_text(text, parse_mode="HTML")

# Меню Дубликатора
@dp.callback_query(lambda c: c.data == "duplicator")
async def duplicator_menu(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_lang, "btn_start_duplicate"), callback_data="start_duplicate")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="other_functions")]
    ])
    
    await callback.message.edit_text(
        get_text(user_lang, "duplicator_menu"),
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# Запуск дублирования
@dp.callback_query(lambda c: c.data == "start_duplicate")
async def start_duplicate(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    data = await state.get_data()
    file_id = data.get('file_id')
    cookie_text = data.get('cookie_text')
    if file_id or cookie_text:
        if not file_id and cookie_text:
            import tempfile
            os.makedirs('temp', exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, dir='temp') as f:
                f.write(cookie_text)
                temp_path = f.name
            from aiogram.types import FSInputFile
            doc = FSInputFile(temp_path, filename='cookie.txt')
            sent = await callback.message.answer_document(doc)
            os.remove(temp_path)
            file_id = sent.document.file_id
            try:
                await sent.delete()
            except:
                pass
        await callback.message.delete()
        adapter = FileMessageAdapter(callback.message, callback.from_user, file_id)
        await state.set_state(FSMStates.waiting_for_file_duplicate)
        await process_file_duplicate(adapter, state)
        return
    await state.set_state(FSMStates.waiting_for_file_duplicate)
    await callback.message.edit_text(
        get_text(user_lang, "duplicate_file_request"),
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data == "sorter")
async def sorter_menu(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    user_id = callback.from_user.id
    
    # ДОБАВЛЯЕМ ПРОВЕРКУ ПОДПИСКИ
    if not is_subscribed(user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(user_lang, "btn_profile"), callback_data="profile")]
        ])
        await callback.message.edit_text(
            get_text(user_lang, "sorter_no_sub"),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    await state.set_state(FSMStates.sorter)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="other_functions")]
    ])
    
    # Проверяем, есть ли текст в сообщении
    try:
        if callback.message.text:
            # Если есть текст - редактируем
            await callback.message.edit_text(
                get_text(user_lang, "sorter_menu"),
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            # Если нет текста (например, сообщение с документом) - удаляем старое и отправляем новое
            await callback.message.delete()
            await callback.message.answer(
                get_text(user_lang, "sorter_menu"),
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    except Exception as e:
        logging.error(f"Ошибка в sorter_menu: {e}")
        # Если не удалось отредактировать - отправляем новое сообщение
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(
            get_text(user_lang, "sorter_menu"),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    await state.set_state(FSMStates.waiting_for_cookie_files)
    await state.update_data(cookie_files=[])
@dp.message(FSMStates.waiting_for_cookie_files)
async def process_cookie_file(message: Message, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)

    is_valid_doc, reason = _validate_txt_document(message.document)
    if is_valid_doc:
        data = await state.get_data()
        cookie_files = data.get('cookie_files', [])
        file_id = message.document.file_id
        cookie_files.append(file_id)
        await state.update_data(cookie_files=cookie_files)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(user_lang, "btn_merge"), callback_data="merge_cookies")],
            [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="sorter")]
        ])
        
        await message.answer(
            get_text(user_lang, "sorter_file_added", count=len(cookie_files)),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        if reason == "too_large":
            await message.answer("❌ Файл слишком большой. Максимальный размер: 8 MB.")
        else:
            await message.answer("❌ Пожалуйста, отправьте файл .txt с куками.")
@dp.callback_query(lambda c: c.data == "merge_cookies")
async def merge_cookies(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    
    data = await state.get_data()
    cookie_files = data.get('cookie_files', [])
    
    if not cookie_files:
        await callback.answer(get_text(user_lang, "sorter_no_files"))
        return
    
    all_cookies = set()
    for file_id in cookie_files:
        temp_path = None
        try:
            file_info = await bot.get_file(file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
                temp_file.write(downloaded_file.getvalue())
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_path = temp_file.name
            
            raw_cookies = await cookie_processor.extract_cookies_from_file(temp_path)
            all_cookies.update(raw_cookies)
        except Exception as file_e:
            logging.error(f"Ошибка обработки файла в сортере: {file_e}")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    if all_cookies:
        # СОХРАНЯЕМ КУКИ В ПАМЯТЬ
        cookies_list = list(all_cookies)
        
        # Сохраняем список кук в state
        await state.update_data(merged_cookies=cookies_list)
        await state.update_data(is_shuffled=False)  # Флаг, что куки ещё не перемешаны
        
        # Создаём временный файл для отправки
        temp_filename = f"merged_cookies_{uuid.uuid4().hex[:8]}.txt"
        with open(temp_filename, "w", encoding="utf-8") as f:
            for ck in cookies_list:
                f.write(ck + "\n")
        
        # Кнопка перемешивания активна
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(user_lang, "btn_shuffle"), callback_data="shuffle_cookies")],
            [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="sorter")]
        ])
        
        await callback.message.answer_document(
            FSInputFile(temp_filename),
            caption=get_text(user_lang, "sorter_merged", count=len(cookies_list)),
            reply_markup=keyboard, 
            parse_mode="HTML"
        )
        
        # Удаляем временный файл после отправки
        os.remove(temp_filename)
        
    else:
        await callback.message.answer(get_text(user_lang, "sorter_no_cookies"), parse_mode="HTML")
    
    await state.update_data(cookie_files=[])
    await sorter_menu(callback, state)
    
# Обработка файла для дубликатора
@dp.message(FSMStates.waiting_for_file_duplicate)
async def process_file_duplicate(message: Message, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)

    is_valid_doc, reason = _validate_txt_document(message.document)
    if not is_valid_doc:
        if reason == "too_large":
            await message.answer("❌ Файл слишком большой. Максимальный размер: 8 MB.")
        else:
            await message.answer(get_text(user_lang, "invalid_format"))
        return

    temp_path = None
    status_msg = None
    try:
        file_id = message.document.file_id
        file_info = await bot.get_file(file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
            temp_file.write(downloaded_file.getvalue())
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = temp_file.name

        raw_cookies = await cookie_processor.extract_cookies_from_file(temp_path)
        cookies = list(raw_cookies)
        
        if not cookies:
            await message.answer(get_text(user_lang, "no_cookies"), parse_mode="HTML")
            await state.set_state(FSMStates.main_menu)
            return

        update_global_cookies_freshed(len(cookies))
        increment_user_freshed(message.from_user.id, len(cookies))
        proxies = load_proxies("proxies.txt")

        status_msg = await message.answer(
            get_text(user_lang, "progress_validating", current=0, total=len(cookies)),
            parse_mode="HTML"
        )
        
        valid_results = await cookie_processor.validate_cookie_batch(cookies, proxies, progress_callback=None)
        valid_cookies = [r['cookie'] for r in valid_results]

        if not valid_cookies:
            await status_msg.edit_text(get_text(user_lang, "no_valid_cookies"), parse_mode="HTML")
            await state.set_state(FSMStates.main_menu)
            return

        await status_msg.edit_text(get_text(user_lang, "progress_duplicating"), parse_mode="HTML")

        duplicated_cookies = await cookie_processor.duplicate_cookie_batch(
            valid_cookies,
            progress_callback=None
        )

        success_count = len(duplicated_cookies) if duplicated_cookies else 0
        failed_count = len(valid_cookies) - success_count

        if success_count > 0:
            filename = f"duplicated_cookies_{uuid.uuid4().hex[:8]}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                for cookie in duplicated_cookies:
                    f.write(cookie + "\n")

            caption = get_text(user_lang, "duplicate_results_success", success=success_count, failed=failed_count)

            try:
                await status_msg.delete()
            except:
                pass

            file_sent = False
            try:
                await message.answer_document(
                    FSInputFile(filename),
                    caption=caption,
                    parse_mode="HTML"
                )
                file_sent = True
            except Exception as e:
                logging.error(f"Ошибка отправки файла дубликатора: {e}")

            if not file_sent:
                await message.answer(
                    get_text(user_lang, "fresh_file_error"),
                    parse_mode="HTML"
                )

            os.remove(filename)
        else:
            await status_msg.edit_text(
                get_text(user_lang, "duplicate_results_no_success"),
                parse_mode="HTML"
            )

        await state.set_state(FSMStates.main_menu)

    except Exception as e:
        logging.error(f"Ошибка в process_file_duplicate: {traceback.format_exc()}")
        await message.answer("❌ Произошла ошибка при дублировании.")
        await state.set_state(FSMStates.main_menu)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        if status_msg:
            try:
                await status_msg.delete()
            except:
                pass
@dp.callback_query(lambda c: c.data == "shuffle_cookies")
async def shuffle_cookies(callback: types.CallbackQuery, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)
    
    data = await state.get_data()
    cookies_list = data.get('merged_cookies', [])
    is_shuffled = data.get('is_shuffled', False)
    
    if not cookies_list:
        await callback.answer("❌ Нет кук для перемешивания. Сначала объедините файлы.")
        return
    
    # Проверяем, были ли куки уже перемешаны
    if is_shuffled:
        await callback.answer("❌ Куки уже были перемешаны! Повторное перемешивание недоступно.", show_alert=True)
        return
    
    # Перемешиваем список
    random.shuffle(cookies_list)
    
    # Создаём файл с перемешанными куками
    shuffled_filename = f"shuffled_cookies_{uuid.uuid4().hex[:8]}.txt"
    with open(shuffled_filename, "w", encoding="utf-8") as f:
        for ck in cookies_list:
            if ck:
                f.write(ck + "\n")
    
    # Обновляем состояние - куки перемешаны
    await state.update_data(merged_cookies=cookies_list)
    await state.update_data(is_shuffled=True)
    
    # Отправляем перемешанный файл БЕЗ кнопки перемешивания
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_lang, "btn_back"), callback_data="sorter")]
    ])
    
    # Отправляем новое сообщение с файлом
    await callback.message.answer_document(
        FSInputFile(shuffled_filename),
        caption=get_text(user_lang, "shuffled", count=len(cookies_list)) + "\n\n Good Luck!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    # Удаляем временный файл
    os.remove(shuffled_filename)
    
    # Удаляем исходное сообщение (то, на котором была кнопка "Перемешать")
    try:
        await callback.message.delete()
    except Exception as e:
        logging.error(f"Ошибка удаления сообщения: {e}")
    
    # Не вызываем sorter_menu, так как мы уже отправили новое сообщение с кнопкой "Назад"
    # Кнопка "Назад" вернёт пользователя в меню сортера при нажатии
@dp.message(FSMStates.waiting_for_file)
async def process_file(message: Message, state: FSMContext):
    user_lang = await get_user_lang_from_state(state)

    is_valid_doc, reason = _validate_txt_document(message.document)
    if is_valid_doc:
        temp_path = None
        try:
            file_id = message.document.file_id
            file_info = await bot.get_file(file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
     
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
                temp_file.write(downloaded_file.getvalue())
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_path = temp_file.name
     
            raw_cookies = await cookie_processor.extract_cookies_from_file(temp_path)
            cookies = list(raw_cookies)
     
            if not cookies:
                await message.answer(get_text(user_lang, "no_cookies"), parse_mode="HTML")
                await state.set_state(FSMStates.main_menu)
                return
                
            user_id = message.from_user.id
            # ЛИМИТ: НЕ БОЛЕЕ 100 000 КУКОВ ЗА ПОСЛЕДНИЙ ЧАС
            hourly_used = get_hourly_check_count(user_id)
            this_file_count = len(cookies)
            
            if hourly_used + this_file_count > 100000:
                excess = (hourly_used + this_file_count) - 100000
                await message.answer(
                    get_text(user_lang, "limit_exceeded", used=hourly_used, file=this_file_count, excess=excess),
                    parse_mode="HTML"
                )
                await state.set_state(FSMStates.main_menu)
                return
                
            # Логируем и обновляем статистику только после прохождения лимита
            log_user_check(user_id, this_file_count)
            update_global_cookies_checked(this_file_count)
            increment_user_checked(user_id, this_file_count)
            proxies = load_proxies("proxies.txt")
     
            progress_msg = await message.answer(
                get_text(user_lang, "progress_validating", current=0, total=len(cookies)),
                parse_mode="HTML"
            )
     
            last_update = 0
            progress_lock = asyncio.Lock()
     
            async def update_progress(completed, total):
                nonlocal last_update
                async with progress_lock:
                    current_time = time.time()
                    if current_time - last_update >= 3 or completed == total:
                        text = get_text(user_lang, "progress_validating", current=completed, total=total)
                        await bot.edit_message_text(
                            text=text,
                            chat_id=message.chat.id,
                            message_id=progress_msg.message_id,
                            parse_mode="HTML"
                        )
                        last_update = current_time
                await asyncio.sleep(0)
     
            valid_cookies = await cookie_processor.validate_cookie_batch(
                cookies, proxies, update_progress
            )
     
            if not valid_cookies:
                await bot.edit_message_text(
                    text=get_text(user_lang, "no_valid_cookies"),
                    chat_id=message.chat.id,
                    message_id=progress_msg.message_id,
                    parse_mode="HTML"
                )
                await state.set_state(FSMStates.main_menu)
                return
     
            await bot.edit_message_text(
                text=get_text(user_lang, "progress_checking_stats", current=0, total=len(valid_cookies)),
                chat_id=message.chat.id,
                message_id=progress_msg.message_id,
                parse_mode="HTML"
            )
     
            data = await state.get_data()
            selected_checks = data.get('selected_checks', {p: True for p in CHECK_PARAMS})
     
            if 'ingame_donate' not in selected_checks:
                selected_checks['ingame_donate'] = True
     
            selected_ingame = data.get('selected_ingame', {s: True for s in GAMES})
            selected_playtime = data.get('selected_playtime', {s: True for s in GAMES})
            selected_badges = data.get('selected_badges', {})
            selected_gamepasses = data.get('selected_gamepasses', {})
         
            game_overrides_data = get_user_game_overrides(message.from_user.id)
            ingame_overrides = game_overrides_data.get('ingame', {})
            playtime_overrides = game_overrides_data.get('playtime', {})
         
            ingame_games_with_overrides = {}
            playtime_games_with_overrides = {}
         
            for short in GAMES:
                game_info = GAMES[short].copy()
                if short in ingame_overrides:
                    game_info.update(ingame_overrides[short])
                ingame_games_with_overrides[short] = game_info
             
                game_info_pt = GAMES[short].copy()
                if short in playtime_overrides:
                    game_info_pt.update(playtime_overrides[short])
                playtime_games_with_overrides[short] = game_info_pt
     
            last_update = 0
            progress_lock = asyncio.Lock()
            stats_start_ts = time.time()

            def _fmt_eta(seconds):
                seconds = int(max(0, seconds))
                if seconds < 60:
                    return f"~{seconds}с"
                m, s = divmod(seconds, 60)
                if m < 60:
                    return f"~{m}м {s:02d}с"
                h, m = divmod(m, 60)
                return f"~{h}ч {m:02d}м"

            async def update_stats_progress(completed, total):
                nonlocal last_update
                async with progress_lock:
                    current_time = time.time()
                    if current_time - last_update >= 3 or completed == total:
                        text = get_text(user_lang, "progress_checking_stats", current=completed, total=total)
                        # ETA по средней скорости
                        elapsed = current_time - stats_start_ts
                        if completed > 0 and completed < total and elapsed > 1:
                            rate = completed / elapsed
                            if rate > 0:
                                eta = (total - completed) / rate
                                text += f"\n⏳ Осталось: {_fmt_eta(eta)}"
                        await bot.edit_message_text(
                            text=text,
                            chat_id=message.chat.id,
                            message_id=progress_msg.message_id,
                            parse_mode="HTML"
                        )
                        last_update = current_time
                await asyncio.sleep(0)
         
            stats_result = await cookie_processor.process_stats_batch(
                valid_cookies,
                proxies,
                selected_checks,
                selected_ingame,
                selected_badges,
                selected_gamepasses,
                selected_playtime,
                update_stats_progress,
                ingame_games=ingame_games_with_overrides,
                playtime_games=playtime_games_with_overrides
            )
     
            valid_stats = stats_result['valid_stats']
            summary = stats_result['summary']
         
            game_summary = {}
            playtime_summary = {}
         
            for stat in valid_stats:
                for game_name, data in stat.get('game_donates', {}).items():
                    if isinstance(data, dict):
                        amount = data.get('sum', 0)
                    else:
                        amount = data
                    game_summary[game_name] = game_summary.get(game_name, 0) + amount
         
            for stat in valid_stats:
                for game_name, minutes in stat.get('playtime_minutes', {}).items():
                    playtime_summary[game_name] = playtime_summary.get(game_name, 0) + minutes
     
            update_global_stats(summary)
     
            html = cookie_processor.generate_stats_html(
                summary, valid_stats, game_summary, selected_checks, playtime_summary
            )
            filename = f"{uuid.uuid4()}.html"
            save_stats_html(filename, html)
            url = get_stats_url(filename)
     
            # ИСПРАВЛЕННЫЕ РАСЧЁТЫ СТАТИСТИКИ
            valid = summary['valid']
            invalid = summary['invalid']
            
            # Количество аккаунтов с балансом
            balance_accounts = sum(1 for d in valid_stats if d.get('balance', 0) > 0)
            
            # Количество аккаунтов с донатом за год (donate_year > 0)
            donate_year_accounts = sum(1 for d in valid_stats if d.get('donate_year', 0) > 0)
            
            # Количество аккаунтов с донатом за всё время (donate_lifetime > 0)
            lifetime_donate_accounts = sum(1 for d in valid_stats if d.get('donate_lifetime', 0) > 0)
            
            # Средние значения
            avg_balance = summary.get('sum_balance', 0) / balance_accounts if balance_accounts > 0 else 0.0
            avg_donate_year = summary.get('sum_donate_year', 0) / donate_year_accounts if donate_year_accounts > 0 else 0.0
            avg_donate_lifetime = summary.get('sum_donate_lifetime', 0) / lifetime_donate_accounts if lifetime_donate_accounts > 0 else 0.0
           
            stats_text = f"""{get_text(user_lang, 'checker_results_title')}
{get_text(user_lang, 'checker_results_valid', valid=valid)}
{get_text(user_lang, 'checker_results_invalid', invalid=invalid)}"""

            if selected_checks.get('balance', False) or selected_checks.get('donate_year', False) or selected_checks.get('donate_lifetime', False) or selected_checks.get('pending', False) or selected_checks.get('rap', False) or selected_checks.get('billing', False):
                stats_text += get_text(user_lang, "finance_title")
                finance_lines = []
                if selected_checks.get('balance', False):
                    finance_lines.append(get_text(user_lang, "finance_balance", sum=summary.get('sum_balance', 0), count=balance_accounts, avg=avg_balance))
                if selected_checks.get('donate_year', False):
                    finance_lines.append(get_text(user_lang, "finance_donate_year", sum=summary.get('sum_donate_year', 0), count=donate_year_accounts, avg=avg_donate_year))
                if selected_checks.get('donate_lifetime', False):
                    finance_lines.append(get_text(user_lang, "finance_donate_lifetime", sum=summary.get('sum_donate_lifetime', 0), count=lifetime_donate_accounts, avg=avg_donate_lifetime))
                if selected_checks.get('pending', False):
                    finance_lines.append(get_text(user_lang, "finance_pending", sum=summary.get('sum_pending', 0)))
                if selected_checks.get('rap', False):
                    finance_lines.append(get_text(user_lang, "finance_rap", sum=summary.get('sum_rap', 0)))
                if selected_checks.get('billing', False):
                    finance_lines.append(get_text(user_lang, "finance_billing", sum=summary.get('sum_billing_robux', 0)))
                if finance_lines:
                    stats_text += '\n<blockquote>' + '\n'.join(line.strip() for line in finance_lines) + '</blockquote>'
     
            if selected_checks.get('card', False) or selected_checks.get('premium', False) or selected_checks.get('email_verified', False) or selected_checks.get('rares', False) or selected_checks.get('badges', False) or selected_checks.get('gamepasses', False) or selected_checks.get('groups_balance', False) or selected_checks.get('places_visits', False) or selected_checks.get('passable', False) or selected_checks.get('rare_items_check', False):
                stats_text += get_text(user_lang, "accounts_title")
                accounts_lines = []
                if selected_checks.get('card', False):
                    accounts_lines.append(get_text(user_lang, "accounts_cards", count=summary.get('card_count', 0)))
                if selected_checks.get('premium', False):
                    accounts_lines.append(get_text(user_lang, "accounts_premium", count=summary.get('prem_count', 0)))
                if selected_checks.get('email_verified', False):
                    accounts_lines.append(get_text(user_lang, "accounts_no_email", count=summary.get('no_email_count', 0)))
                if selected_checks.get('rares', False):
                    accounts_lines.append(get_text(user_lang, "accounts_korblox", count=summary.get('korblox_count', 0)))
                    accounts_lines.append(get_text(user_lang, "accounts_headless", count=summary.get('headless_count', 0)))
                if selected_checks.get('badges', False):
                    accounts_lines.append(get_text(user_lang, "accounts_badges", sum=summary.get('sum_badges', 0)))
                if selected_checks.get('gamepasses', False):
                    accounts_lines.append(get_text(user_lang, "accounts_gamepasses", sum=summary.get('sum_gamepasses', 0)))
                if selected_checks.get('groups_balance', False):
                    accounts_lines.append(get_text(user_lang, "accounts_groups", sum=summary.get('sum_groups_balance', 0)))
                if selected_checks.get('places_visits', False):
                    accounts_lines.append(get_text(user_lang, "accounts_visits", sum=summary.get('sum_visits', 0)))
                if selected_checks.get('passable', False):
                    accounts_lines.append(get_text(user_lang, "accounts_passable", passable=summary.get('passable_count', 0), unpassable=summary.get('unpassable_count', 0)))
                if selected_checks.get('rare_items_check', False):
                    accounts_lines.append(get_text(user_lang, "accounts_rare_items", count=summary.get('rare_items_accounts', 0)))
                if accounts_lines:
                    stats_text += '\n<blockquote>' + '\n'.join(line.strip() for line in accounts_lines) + '</blockquote>'
     
            if selected_checks.get('ingame_donate', False) and game_summary:
                stats_text += get_text(user_lang, "ingame_results")
                sorted_games = sorted(game_summary.items(), key=lambda x: x[1], reverse=True)
                ingame_lines = [f"{name}: {total:,} R$" for name, total in sorted_games]
                stats_text += '<blockquote>' + '\n'.join(ingame_lines) + '</blockquote>'
     
            if selected_checks.get('playtime', False) and playtime_summary:
                stats_text += get_text(user_lang, "playtime_results")
                sorted_playtime = sorted(playtime_summary.items(), key=lambda x: x[1], reverse=True)
                playtime_lines = [f"{name}: {total:,}" for name, total in sorted_playtime]
                stats_text += '<blockquote>' + '\n'.join(playtime_lines) + '</blockquote>'

            # Оценка стоимости пачки — в самом низу
            batch_price = summary.get('sum_price', 0)
            if selected_checks.get('price', True) and batch_price and batch_price > 0:
                stats_text += "\n" + get_text(user_lang, "checker_results_price", price=batch_price)

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_text(user_lang, "btn_web_report"), url=url)],
            ])
     
            await bot.delete_message(message.chat.id, progress_msg.message_id)

            import os as _os
            _gif_path = _os.path.join(_os.path.dirname(__file__), 'report_gif.mp4')
            _gif_sent = False
            if _os.path.exists(_gif_path):
                try:
                    await message.answer_animation(
                        FSInputFile(_gif_path),
                        caption=stats_text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                    _gif_sent = True
                except Exception:
                    pass
            if not _gif_sent:
                await message.answer(
                    text=stats_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
     
            settings = await state.get_data()
            output_format = settings.get('output_format', 'zip')
            use_emoji = selected_checks.get('use_emoji', True)
     
            if output_format == 'zip':
                zip_bytes = cookie_processor.create_results_zip(
                    valid_stats,
                    selected_checks,
                    selected_ingame,
                    selected_badges,
                    selected_gamepasses,
                    selected_playtime,
                    ingame_games=ingame_games_with_overrides,
                    playtime_games=playtime_games_with_overrides
                )
           
                MAX_SINGLE_SIZE = 50 * 1024 * 1024
                SAFE_PART_SIZE = 49 * 1024 * 1024
           
                total_size = len(zip_bytes)
           
                if total_size <= MAX_SINGLE_SIZE:
                    await message.answer_document(
                        BufferedInputFile(zip_bytes, filename="results.zip")
                    )
                else:
                    await message.answer(
                        "⚠️ <b>ZIP-файл превышает лимит Telegram (50 МБ).</b>\n"
                        "Отправляю архив частями (по ~49 МБ)",
                        parse_mode="HTML"
                    )
               
                    part_num = 1
                    offset = 0
                    while offset < total_size:
                        chunk_end = min(offset + SAFE_PART_SIZE, total_size)
                        chunk = zip_bytes[offset:chunk_end]
                        part_filename = f"results_part{part_num}.zip"
                        await message.answer_document(
                            BufferedInputFile(chunk, filename=part_filename)
                        )
                        offset = chunk_end
                        part_num += 1
                   
            else:
                media = []
                random.shuffle(valid_stats)
                valid_content = '\n'.join(
                    cookie_processor.format_cookie_line(
                        d, selected_badges, selected_gamepasses, selected_checks,
                        selected_ingame, selected_playtime, use_emoji
                    ) for d in valid_stats
                )
                media.append(InputMediaDocument(
                    media=BufferedInputFile(valid_content.encode('utf-8'), "valids.txt")
                ))
             
                if selected_checks.get('rap', False):
                    rap_stats = sorted([d for d in valid_stats if d['rap'] > 0], key=lambda x: x['rap'], reverse=True)
                    if rap_stats:
                        content = '\n'.join(cookie_processor.format_cookie_line(
                            d, selected_badges, selected_gamepasses, selected_checks,
                            selected_ingame, selected_playtime, use_emoji
                        ) for d in rap_stats)
                        media.append(InputMediaDocument(media=BufferedInputFile(content.encode('utf-8'), "rap.txt")))
              
                if selected_checks.get('premium', False):
                    premium_stats = [d for d in valid_stats if d['prem']]
                    random.shuffle(premium_stats)
                    if premium_stats:
                        content = '\n'.join(cookie_processor.format_cookie_line(
                            d, selected_badges, selected_gamepasses, selected_checks,
                            selected_ingame, selected_playtime, use_emoji
                        ) for d in premium_stats)
                        media.append(InputMediaDocument(media=BufferedInputFile(content.encode('utf-8'), "premium.txt")))
         
                if selected_checks.get('donate_lifetime', False) or selected_checks.get('donate_year', False):
                    donate_stats = sorted([d for d in valid_stats if d['donate_lifetime'] > 0 or d['donate_year'] > 0],
                                          key=lambda x: x['donate_lifetime'] + x['donate_year'], reverse=True)
                    if donate_stats:
                        content = '\n'.join(cookie_processor.format_cookie_line(
                            d, selected_badges, selected_gamepasses, selected_checks,
                            selected_ingame, selected_playtime, use_emoji
                        ) for d in donate_stats)
                        media.append(InputMediaDocument(media=BufferedInputFile(content.encode('utf-8'), "donate.txt")))
         
                if selected_checks.get('balance', False):
                    balance_stats = sorted([d for d in valid_stats if d['balance'] > 0], key=lambda x: x['balance'], reverse=True)
                    if balance_stats:
                        content = '\n'.join(cookie_processor.format_cookie_line(
                            d, selected_badges, selected_gamepasses, selected_checks,
                            selected_ingame, selected_playtime, use_emoji
                        ) for d in balance_stats)
                        media.append(InputMediaDocument(media=BufferedInputFile(content.encode('utf-8'), "balance.txt")))
         
                if selected_checks.get('pending', False):
                    pending_stats = sorted([d for d in valid_stats if d['pending'] > 0], key=lambda x: x['pending'], reverse=True)
                    if pending_stats:
                        content = '\n'.join(cookie_processor.format_cookie_line(
                            d, selected_badges, selected_gamepasses, selected_checks,
                            selected_ingame, selected_playtime, use_emoji
                        ) for d in pending_stats)
                        media.append(InputMediaDocument(media=BufferedInputFile(content.encode('utf-8'), "pending.txt")))
         
                if selected_checks.get('card', False):
                    cards_stats = sorted([d for d in valid_stats if d['card'] > 0], key=lambda x: x['card'], reverse=True)
                    if cards_stats:
                        content = '\n'.join(cookie_processor.format_cookie_line(
                            d, selected_badges, selected_gamepasses, selected_checks,
                            selected_ingame, selected_playtime, use_emoji
                        ) for d in cards_stats)
                        media.append(InputMediaDocument(media=BufferedInputFile(content.encode('utf-8'), "cards.txt")))
         
                if selected_checks.get('groups_balance', False):
                    groups_stats = sorted([d for d in valid_stats if d['groups_balance'] > 0], key=lambda x: x['groups_balance'], reverse=True)
                    if groups_stats:
                        content = '\n'.join(cookie_processor.format_cookie_line(
                            d, selected_badges, selected_gamepasses, selected_checks,
                            selected_ingame, selected_playtime, use_emoji
                        ) for d in groups_stats)
                        media.append(InputMediaDocument(media=BufferedInputFile(content.encode('utf-8'), "groups.txt")))
         
                if selected_checks.get('badges', False) and any(selected_badges.values()):
                    badges_stats = [
                        d for d in valid_stats
                        if sum(v.get('count', 0) for v in d.get('badges_count_per_game', {}).values()) > 0
                    ]
                    if badges_stats:
                        content = '\n'.join(
                            cookie_processor.format_cookie_line(
                                d, selected_badges, selected_gamepasses, selected_checks,
                                selected_ingame, selected_playtime, use_emoji
                            ) for d in badges_stats
                        )
                        media.append(InputMediaDocument(
                            media=BufferedInputFile(content.encode('utf-8'), "badges.txt")
                        ))
         
                if media:
                    for i in range(0, len(media), 10):
                        await bot.send_media_group(message.chat.id, media=media[i:i+10])
          
                if any(selected_playtime.values()):
                    playtime_media = []
                    for short in [k for k in selected_playtime if selected_playtime[k]]:
                        game_info = playtime_games_with_overrides[short]
                        game_name = game_info['name']
                     
                        playtime_stats = [
                            d for d in valid_stats
                            if d['playtime_minutes'].get(game_name, 0) > 0
                        ]
                        if playtime_stats:
                            playtime_stats = sorted(
                                playtime_stats,
                                key=lambda x: x['playtime_minutes'].get(game_name, 0),
                                reverse=True
                            )
                            content = '\n'.join(
                                cookie_processor.format_cookie_line(
                                    d, selected_badges, selected_gamepasses, selected_checks,
                                    selected_ingame, selected_playtime, use_emoji
                                ) for d in playtime_stats
                            )
                            filename = f"{game_name} Playtime.txt"
                            playtime_media.append(InputMediaDocument(
                                media=BufferedInputFile(content.encode('utf-8'), filename)
                            ))
              
                    if playtime_media:
                        for i in range(0, len(playtime_media), 10):
                            await bot.send_media_group(message.chat.id, media=playtime_media[i:i+10])
     
            await state.set_state(FSMStates.main_menu)
     
        except Exception as e:
            error_details = traceback.format_exc()
            logging.error(f"Ошибка обработки файла: {str(e)}\n{error_details}")
            await message.answer("❌ Произошла ошибка при обработке файла. Попробуйте позже или обратитесь в поддержку.")
            await state.set_state(FSMStates.main_menu)
    else:
        if reason == "too_large":
            await message.answer("❌ Файл слишком большой. Максимальный размер: 8 MB.")
        else:
            await message.answer(get_text(user_lang, "invalid_format"))
@dp.message(Command('cancel'))
async def cancel_state(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено. Вернитесь в меню.")
async def load_and_merge_settings(user_id: int, state: FSMContext):
    """Загружает настройки из БД, применяет дефолты и сохраняет в state"""
    settings = get_user_settings(user_id)
    game_overrides_data = get_user_game_overrides(user_id)
    ingame_overrides = game_overrides_data.get('ingame', {})
    playtime_overrides = game_overrides_data.get('playtime', {})

    default_settings = {
        'selected_checks': {p: True for p in CHECK_PARAMS},
        'selected_ingame': {s: True for s in GAMES},
        'selected_playtime': {s: True for s in GAMES},
        'selected_badges': {},
        'selected_gamepasses': {},
        'registration_date': datetime.now(moscow_tz).isoformat(),
        'subscription_expiration': None,
        'output_format': 'zip',
        'language': 'ru'
    }

    if not settings:
        settings = default_settings.copy()
    else:
        for key, default_value in default_settings.items():
            if key not in settings:
                settings[key] = default_value

        for param in CHECK_PARAMS:
            if param not in settings['selected_checks']:
                settings['selected_checks'][param] = True

        for short in GAMES:
            if short not in settings['selected_ingame']:
                settings['selected_ingame'][short] = True
            if short not in settings['selected_playtime']:
                settings['selected_playtime'][short] = True

        if 'output_format' not in settings:
            settings['output_format'] = 'zip'
        
        if 'language' not in settings:
            settings['language'] = 'ru'

    save_user_settings(user_id, settings)
    await state.update_data(**settings)
    await state.update_data(
        ingame_overrides=ingame_overrides,
        playtime_overrides=playtime_overrides
    )
    return settings

## РОЗЫГРЫШЫ КУ ОЛЕГ
@dp.message(Command('create'))
async def cmd_create_giveaway(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Нет доступа")
        return
    await state.set_state(FSMStates.creating_giveaway_amount)
    await message.answer("💰 Введите сумму розыгрыша в RUB:")

@dp.message(FSMStates.creating_giveaway_amount)
async def process_giveaway_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError
        await state.update_data(giveaway_amount=amount)
        await state.set_state(FSMStates.creating_giveaway_end)
        await message.answer(
            "⏰ Укажите окончание розыгрыша:\n"
            "• Через сколько часов (например: 24)\n"
            "• Или точную дату и время (DD.MM.YYYY HH:MM)\n\n"
            "Пример: 48\nПример: 20.02.2026 20:00"
        )
    except ValueError:
        await message.answer("❌ Введите положительное число.")

@dp.message(FSMStates.creating_giveaway_end)
async def process_giveaway_end(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    amount = data['giveaway_amount']
    now = datetime.now(moscow_tz)

    end_dt = None

    # Сначала пробуем как часы
    if text.isdigit():
        hours = int(text)
        if 1 <= hours <= 720:  # от 1 часа до 30 дней
            end_dt = now + timedelta(hours=hours)
        else:
            await message.answer("❌ Укажите от 1 до 720 часов.")
            return
    else:
        # Пробуем как дату
        try:
            # Парсим дату (без часового пояса)
            end_dt_naive = datetime.strptime(text, "%d.%m.%Y %H:%M")
            # Добавляем московский часовой пояс
            end_dt = end_dt_naive.replace(tzinfo=moscow_tz)
            
            if end_dt <= now:
                await message.answer("❌ Дата не может быть в прошлом")
                return
        except ValueError as e:
            logging.error(f"Ошибка парсинга даты: {e}")
            await message.answer("❌ Неверный формат.\nПримеры:\n48\n20.02.2026 20:00")
            return

    # Сохраняем дату в ISO формате
    end_date_iso = end_dt.isoformat()
    
    # Создаём розыгрыш
    giveaway_id = create_giveaway(amount, end_date_iso)

    end_str = end_dt.strftime("%d.%m.%Y %H:%M")

    post_text = f"<tg-emoji emoji-id=\"5348319041935132191\">🎰</tg-emoji> <tg-emoji emoji-id=\"5348131308914624735\">💎</tg-emoji> <tg-emoji emoji-id=\"5348532407320463735\">⚡️</tg-emoji> <b>Розыгрыш {amount} RUB!</b>\n\n⏰ Окончание: {end_str} МСК\n\n👥 Участники: 0"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Участвовать (0)",icon_custom_emoji_id="6021561470595112226", callback_data=f"join_giveaway_{giveaway_id}")]
    ])

    sent = await bot.send_message(
        chat_id=CHANNEL_ID,
        text=post_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    update_giveaway_message_id(giveaway_id, sent.message_id)

    await message.answer(f"✅ Розыгрыш на {amount} RUB создан!\nОкончание: {end_str} МСК")
    await state.clear()
@dp.message(Command('giveaways'))
async def cmd_list_giveaways(message: Message):
    """Показывает список всех розыгрышей"""
    user_id = message.from_user.id
    
    # Проверяем права доступа (только для админов
    
    try:
        # Получаем все розыгрыши
        cursor.execute("""
            SELECT id, amount, end_date, message_id, participants, winner_id 
            FROM giveaways 
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        
        if not rows:
            await message.answer("📭 Розыгрышей не найдено")
            return
        
        now = datetime.now(moscow_tz)
        
        # Формируем сообщение со списком розыгрышей
        text = "🎁 <b>Список всех розыгрышей:</b>\n\n"
        
        for row in rows:
            giveaway_id, amount, end_date_str, message_id, participants_json, winner_id = row
            
            try:
                end_date = datetime.fromisoformat(end_date_str)
                participants = json.loads(participants_json) if participants_json else []
                participant_count = len(participants)
                
                # Определяем статус розыгрыша
                if winner_id:
                    status = "✅ ЗАВЕРШЁН (есть победитель)"
                elif end_date <= now:
                    status = "⏰ ЗАВЕРШЁН (ожидает выбора победителя)"
                else:
                    status = "🟢 АКТИВЕН"
                
                # Время до окончания для активных
                if not winner_id and end_date > now:
                    time_left = end_date - now
                    hours_left = time_left.total_seconds() / 3600
                    if hours_left < 24:
                        time_str = f"осталось {int(hours_left)} ч"
                    else:
                        days_left = int(hours_left / 24)
                        hours_remain = int(hours_left % 24)
                        time_str = f"осталось {days_left} д {hours_remain} ч"
                else:
                    time_str = ""
                
                # Добавляем информацию о розыгрыше
                text += f"<b>ID: {giveaway_id}</b>\n"
                text += f"💰 Сумма: {amount} RUB\n"
                text += f"📅 Окончание: {end_date.strftime('%d.%m.%Y %H:%M')}\n"
                text += f"👥 Участников: {participant_count}\n"
                text += f"📊 Статус: {status}\n"
                if time_str:
                    text += f"⏳ {time_str}\n"
                if winner_id:
                    text += f"🏆 Победитель: {winner_id}\n"
                text += f"🔗 Сообщение: https://t.me/c/{str(CHANNEL_ID).replace('-100', '')}/{message_id}\n"
                text += "─" * 20 + "\n\n"
                
            except Exception as e:
                logging.error(f"Ошибка обработки розыгрыша {giveaway_id}: {e}")
                continue
        
        # Если текст слишком длинный, разбиваем на несколько сообщений
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                await message.answer(part, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
            
    except Exception as e:
        logging.error(f"Ошибка получения списка розыгрышей: {e}")
        await message.answer("❌ Ошибка при получении списка розыгрышей")
# === ФОНОВАЯ ЗАДАЧА ДЛЯ ЗАВЕРШЕНИЯ РОЗЫГРЫШЕЙ ===
async def check_and_finish_giveaways():
    """Проверяет завершённые розыгрыши и объявляет победителей"""
    expired = get_expired_giveaways()
    if not expired:
        return

    for ga in expired:
        if not ga['participants']:
            # Нет участников — просто помечаем как завершённый без победителя
            completed_text = (
                f"🎉 <b>Розыгрыш {ga['amount']} RUB завершён!</b>\n\n"
                f"⏰ Окончание: {datetime.fromisoformat(ga['end_date']).strftime('%d.%m.%Y %H:%M')} МСК\n"
                f"👥 Участников: 0\n\n"
                f"😔 Победитель не определён (нет участников)"
            )
            try:
                await bot.edit_message_text(
                    chat_id=CHANNEL_ID,
                    message_id=ga['message_id'],
                    text=completed_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Ошибка редактирования сообщения розыгрыша {ga['id']} (нет участников): {e}")
            continue

        # Выбираем случайного победителя
        winner_id = random.choice(ga['participants'])

        # Сохраняем победителя в БД
        set_giveaway_winner(ga['id'], winner_id)

        # Получаем информацию о победителе
        try:
            winner_user = await bot.get_chat(winner_id)
            winner_mention = f"@{winner_user.username}" if winner_user.username else winner_user.full_name
            winner_link = f"tg://user?id={winner_id}"
        except Exception as e:
            logging.error(f"Не удалось получить данные победителя {winner_id}: {e}")
            winner_mention = f"Пользователь {winner_id}"
            winner_link = None

        # Текст для редактирования оригинального сообщения
        end_str = datetime.fromisoformat(ga['end_date']).strftime("%d.%m.%Y %H:%M")
        completed_text = (
            f"🎉 <b>Розыгрыш {ga['amount']} RUB завершён!</b>\n\n"
            f"⏰ Окончание: {end_str} МСК\n"
            f"👥 Участников: {len(ga['participants'])}\n\n"
            f"🏆 <b>Победитель:</b> {winner_mention}"
        )
        if winner_link:
            completed_text = completed_text.replace(winner_mention, f"[{winner_mention}]({winner_link})")

        try:
            await bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=ga['message_id'],
                text=completed_text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except Exception as e:
            logging.error(f"Ошибка редактирования сообщения розыгрыша {ga['id']}: {e}")

        # Отправляем отдельное сообщение с объявлением победителя
        announce_text = (
            f"🎉 <b>Поздравляем победителя розыгрыша на {ga['amount']} RUB!</b>\n\n"
            f"🏆 {winner_mention}\n\n"
            f"(скоро ему напишет админ)"
        )
        if winner_link:
            announce_text = announce_text.replace(winner_mention, f"[{winner_mention}]({winner_link})")

        try:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=announce_text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except Exception as e:
            logging.error(f"Ошибка отправки объявления о победителе для розыгрыша {ga['id']}: {e}")

async def background_giveaway_checker():
    """Фоновая задача: каждые 60 секунд проверяет завершённые розыгрыши"""
    logging.info("🚀 Фоновая задача проверки розыгрышей ЗАПУЩЕНА")
    
    cycle_count = 0
    while True:
        try:
            cycle_count += 1
            current_time = datetime.now(moscow_tz).strftime('%Y-%m-%d %H:%M:%S')
            logging.info(f"🔄 Цикл проверки #{cycle_count} в {current_time}")
            
            await check_and_finish_giveaways()
            
            logging.info(f"✅ Цикл #{cycle_count} завершён. Следующая проверка через 60 секунд")
            
        except Exception as e:
            logging.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в фоновой проверке розыгрышей (цикл #{cycle_count}): {e}")
            logging.error(traceback.format_exc())
        
        await asyncio.sleep(60)

@dp.callback_query(lambda c: c.data.startswith("join_giveaway_"))
async def join_giveaway(callback: types.CallbackQuery):
    try:
        giveaway_id = int(callback.data.split("_")[-1])
    except:
        await callback.answer("❌ Ошибка")
        return

    user_id = callback.from_user.id

    ga = get_giveaway(giveaway_id)
    if not ga:
        await callback.answer("❌ Розыгрыш не найден")
        return

    now = datetime.now(moscow_tz)
    end_dt = datetime.fromisoformat(ga['end_date'])

    # Если уже завершён (победитель выбран или время вышло)
    if ga.get('winner_id') or now >= end_dt:
        await callback.answer("❌ Розыгрыш уже завершён")
        return

    if not is_subscribed(user_id):
        await callback.answer("❌ Участвовать могут только пользователи с активной подпиской!", show_alert=True)
        return

    old_count = len(ga['participants'])
    new_count = add_participant_to_giveaway(giveaway_id, user_id)

    if new_count == old_count:
        await callback.answer("Вы уже участвуете!")
    else:
        await callback.answer(f"✅ Вы участвуете! Участников: {new_count}")

        # Обновляем кнопку и текст
        current_text = (
            f"🎉 <b>Розыгрыш {ga['amount']} RUB!</b>\n\n"
            f"⏰ Окончание: {end_dt.strftime('%d.%m.%Y %H:%M')} МСК\n\n"
            f"👥 Участники: {new_count}"
        )
        new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Участвовать ({new_count})", callback_data=f"join_giveaway_{giveaway_id}")]
        ])

        try:
            await bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=ga['message_id'],
                text=current_text,
                reply_markup=new_keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Ошибка обновления розыгрыша {giveaway_id}: {e}")
# Обработчик для куков, отправленных текстом (регистрируется после state-based хендлеров)
@dp.message(lambda message: message.text and "_|WARNING:-DO-NOT-SHARE-THIS" in message.text)
async def handle_cookie_text(message: Message, state: FSMContext):
    """Обрабатывает куки, отправленные текстом"""
    current_state = await state.get_state()
    logging.info(f"🍪 handle_cookie_text: user={message.from_user.id}, state={current_state}, text_len={len(message.text or '')}")
    
    if current_state in [
        FSMStates.waiting_for_file.state,
        FSMStates.waiting_for_file_duplicate.state,
        FSMStates.waiting_for_file_fresh.state,
        FSMStates.waiting_for_validation_file.state,
        FSMStates.waiting_for_file_action.state,
        FSMStates.waiting_for_cookie_files.state,
        FSMStates.waiting_for_post_message.state
    ]:
        logging.info(f"🍪 handle_cookie_text: SKIPPED due to state={current_state}")
        return
    
    user_id = message.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    if not is_subscribed(user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(user_lang, "btn_profile"), callback_data="profile")]
        ])
        await message.answer(
            get_text(user_lang, "checker_no_sub"),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    await state.update_data(
        cookie_text=message.text,
        file_id=None,
        file_message_id=message.message_id
    )
    await state.set_state(FSMStates.waiting_for_file_action)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_lang, "btn_checker"), icon_custom_emoji_id="6019205852831947754", callback_data="file_action_check")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_fresher"), icon_custom_emoji_id="5807492110059838726", callback_data="file_action_fresh")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_validator"), icon_custom_emoji_id="6021659039367173797", callback_data="file_action_validate")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_other"), icon_custom_emoji_id="6021401276904905698", callback_data="other_functions")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_cancel_file"), icon_custom_emoji_id="5348432102654232741", callback_data="file_action_cancel")]
    ])
    
    await message.answer(get_text(user_lang, "file_action_menu"), reply_markup=keyboard, parse_mode="HTML")

# Глобальный обработчик для файлов, отправленных без выбора режима (регистрируется последним)
@dp.message(lambda message: message.document is not None)
async def handle_file_without_mode(message: Message, state: FSMContext):
    """Обрабатывает файлы, отправленные без выбора режима"""
    current_state = await state.get_state()
    
    if current_state in [
        FSMStates.waiting_for_file.state,
        FSMStates.waiting_for_file_duplicate.state,
        FSMStates.waiting_for_file_fresh.state,
        FSMStates.waiting_for_validation_file.state,
        FSMStates.waiting_for_file_action.state,
        FSMStates.waiting_for_cookie_files.state,
        FSMStates.waiting_for_post_message.state
    ]:
        return
    
    user_id = message.from_user.id
    user_lang = await get_user_lang_from_state(state)
    
    if not is_subscribed(user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(user_lang, "btn_profile"), callback_data="profile")]
        ])
        await message.answer(
            get_text(user_lang, "checker_no_sub"),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    is_valid_doc, reason = _validate_txt_document(message.document)
    if not is_valid_doc:
        if reason == "too_large":
            await message.answer("❌ Файл слишком большой. Максимальный размер: 8 MB.")
        else:
            await message.answer(get_text(user_lang, "invalid_format"))
        return
    
    await state.update_data(
        file_id=message.document.file_id,
        file_message_id=message.message_id
    )
    await state.set_state(FSMStates.waiting_for_file_action)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_lang, "btn_checker"), icon_custom_emoji_id="6019205852831947754", callback_data="file_action_check")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_fresher"), icon_custom_emoji_id="5807492110059838726", callback_data="file_action_fresh")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_validator"), icon_custom_emoji_id="6021659039367173797", callback_data="file_action_validate")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_other"), icon_custom_emoji_id="6021401276904905698", callback_data="other_functions")],
        [InlineKeyboardButton(text=get_text(user_lang, "btn_cancel_file"), icon_custom_emoji_id="5348432102654232741", callback_data="file_action_cancel")]
    ])
    
    await message.answer(get_text(user_lang, "file_action_menu"), reply_markup=keyboard, parse_mode="HTML")

# Запуск бота
async def main():
    await dp.start_polling(bot)
if __name__ == '__main__':
    asyncio.run(main())
