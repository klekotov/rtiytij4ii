# languages.py - Файл с переводами

import logging

class Languages:
    # Русский язык
    ru = {
        'custom_badges_prompt': '📥 <b>Вставьте список ID бейджей</b>\nЧерез запятую или новую строку:',
        'custom_gamepasses_prompt': '📥 <b>Вставьте список ID геймпассов</b>\nЧерез запятую или новую строку:',
        'config_name_prompt_badges': '🆕 <b>Введите название конфига для бейджей</b>:',
        'config_name_prompt_gamepasses': '🆕 <b>Введите название конфига для геймпассов</b>:',
        'config_created': '✅ Конфиг "{name}" создан',
        'custom_saved': '✅ Кастомные бейджи сохранены как "{name}", чтобы они использовались включите их',
        'custom_gamepasses_saved': '✅ Кастомные геймпассы сохранены как "{name}"',
        'game_changed_success': '✅ Игра <b>{game_short}</b> изменена на <b>{game_name}</b>',
        'invalid_game_url': '❌ Некорректная ссылка. Убедитесь, что это ссылка на игру Roblox.',
        'game_not_found': '❌ Игра не найдена или произошла ошибка API Roblox.',
        'send_game_url': '📤 Отправьте новую ссылку на игру Roblox для <b>{game_name}</b>\n\nПример: https://www.roblox.com/games/126884695634066/Grow-a-Garden',
        'btn_change': '✏️ Изменить {name}',
        'btn_reset': '🔄 Сбросить {name}',
        'no_valid_ids': '❌ Нет валидных ID',
          "btn_bonus_days": "🎁 Бонусные дни",
    "bonus_checking": "🔍 Проверяю подписку на спонсорские каналы...",
    "bonus_not_subscribed": "❌ Вы не подписаны на все спонсорские каналы.\nПожалуйста, подпишитесь и нажмите кнопку снова.",
    "bonus_already_claimed": "⏳ Вы уже получали бонус в этом месяце. Следующий бонус доступен через {days_left} дней.",
    "bonus_no_sponsors": "❌ Бонусная программа временно недоступна.",
    "bonus_success": "✅ Бонус активирован! Вам добавлено 2 дня подписки.\nНовая дата окончания: {expiry}",
    "admin_work_title": "🛠 Управление спонсорскими каналами\n\nВсего каналов: {count}/5",
    "admin_work_list": "📋 Список каналов:\n",
    "admin_work_item": "{index}. {link} (ID: {channel_id})\n",
    "admin_work_no_channels": "Список пуст.",
    "btn_add_channel": "➕ Добавить канал",
    "btn_check_subscription": "✅ Я подписался",
"bonus_sponsor_required": "🎁 <b>Для получения бонусных дней необходимо подписаться на все каналы ниже:</b>\n\nПосле подписки нажмите кнопку «Я подписался»",
"bonus_not_subscribed_list": "❌ <b>Вы не подписаны на следующие каналы:</b>\n\n{channels}\n\nПожалуйста, подпишитесь и нажмите кнопку снова.",

    "btn_remove_channel": "➖ Удалить канал",
    "btn_clear_channels": "🗑 Очистить все",
    "enter_channel_link": "🔗 Отправьте ссылку или ID канала (например: @channel или -1001234567890):",
    "invalid_channel_link": "❌ Некорректная ссылка или ID канала.",
    "channel_added": "✅ Канал добавлен.",
    "channel_not_found": "❌ Канал не найден в списке.",
    "channel_removed": "✅ Канал удалён.",
    "channels_cleared": "✅ Все спонсорские каналы удалены.",
    "confirm_clear_channels": "⚠️ Вы уверены, что хотите удалить ВСЕ спонсорские каналы?",
    "btn_confirm_clear": "✅ Да, удалить",
        
        # Приветствие и главное меню
        "welcome": """<tg-emoji emoji-id="5855154023568510775">☠️</tg-emoji> Приветствуем в 227 Checker! 
<blockquote>Проверяйте и фрешайте куки легко и удобно.</blockquote>

OOO "Разъеб хаха" """,
        "main_menu": """<tg-emoji emoji-id="5855015738506482494">🏠</tg-emoji> <b>Меню чекера</b>
Выберите опцию ниже:""",
        
        # Кнопки главного меню
        "btn_checker": "Cookie Checker",
        "btn_fresher": "Cookie Fresher",
        "btn_validator": "Cookie Validator",
        "btn_stats": "Статистика",
        "btn_profile": "Профиль",
        "btn_other": "Остальные функции",
        "btn_language": "Язык / Language",
        
        # Настройка пользовательских игр
        'btn_custom_game1': '🎮 Игра 1',
        'btn_custom_game2': '🎮 Игра 2',
        'custom_game_setup': '🔗 Настройка пользовательской игры {num}',
        'custom_game_url_prompt': 'Отправьте ссылку на игру в Roblox\nИли /skip чтобы пропустить',
        'custom_game_name_prompt': 'Введите название для отображения в результатах',
        'custom_game_added': '✅ Игра "{name}" успешно добавлена!',
        'custom_game_reset': '🔄 Игра сброшена до стандартной',
        
        # Магазин
        'shop_text': '<b>Купить за рубли/лолз</b> - <a href="https://t.me/S1PshopBot">@S1PshopBot</a>',
         'ru': '❌ <b>Сортер доступен только с активной подпиской!</b>\n\nПриобретите подписку в профиле.',
        # Языковое меню
        "select_language": '<tg-emoji emoji-id="6050689397630702147">🌐</tg-emoji> <b>Выберите язык / Select language</b>',
        "btn_russian": "🇷🇺 Русский",
        "btn_english": "🇬🇧 English",
        "language_changed": '<tg-emoji emoji-id="6050689397630702147">✅</tg-emoji> Язык изменен на русский',
        
        # Проверка подписки
        "need_subscription": '<tg-emoji emoji-id="5363790055301205826">❌</tg-emoji> Для использования бота необходимо подписаться на наш канал!\n\n<tg-emoji emoji-id="5366077477573643872">📢</tg-emoji> Перейдите по кнопке ниже и подпишитесь на канал, затем нажмите \'Проверить подписку\'',
        "btn_subscribe": "Подписаться на канал",
        "btn_check_sub": "Проверить подписку",
        "not_subscribed": '<tg-emoji emoji-id="5366341798450973386">❌</tg-emoji> Вы всё ещё не подписаны на канал!',
        "sub_check_error": '<tg-emoji emoji-id="5364089324327423737">❌</tg-emoji> Ошибка проверки подписки. Попробуйте позже.',
        
        # Профиль
        "profile_title": '<tg-emoji emoji-id="5855015738506482494">👤</tg-emoji> <b>Ваш профиль</b>',
        "profile_id": 'ID: <code>{user_id}</code>',
        "profile_reg": 'Регистрация: {reg_date}',
        "profile_sub_active_forever": 'Подписка: Активна (навсегда) <tg-emoji emoji-id="5366493793048611678">🎉</tg-emoji>',
        "profile_sub_active_days": 'Подписка: Активна ({days} {days_word} осталось)',
        "profile_sub_active_less_day": 'Подписка: Активна (менее дня осталось)',
        "profile_sub_inactive": 'Подписка: Отсутствует',
        "profile_ref_balance": 'Реферальный баланс: {balance} RUB',
        "profile_ref_count": 'Рефералов: {count}',
        "profile_checked": 'Проверено куков: <code>{checked:,}</code>',
        "profile_freshed": 'Фрешнуто куков: <code>{freshed:,}</code>',
        "profile_ref_link": 'Реферальная ссылка: {link}',
        
        # Активация ключа
        'already_subscribed': '❌ У вас уже есть активная подписка',
        
        # Покупка подписки
        'exchange_rate': 'Текущий курс: 1 USDT ≈ {rate:.2f} RUB',
        'payment_url_error': '❌ Ошибка: не удалось получить ссылку для оплаты',
        
        # Покупка с реферального баланса
        
        # Вывод средств
        'enter_payout_link': '📤 Введите ссылку на выплату:',
        'invalid_amount': '❌ Некорректная сумма.',
        
        # Пробная подписка
        
        # Реферальная система
        'referral_purchase_notify': '💰 Ваш реферал купил подписку!\n+{amount} RUB на реф. баланс',
        
        # Админские команды
        
        # Слова для дней
        "days_word_1": "день",
        "days_word_2": "дня",
        "days_word_5": "дней",
        
        # Кнопки профиля
        "btn_activate_key": "Активировать ключ",
        "btn_buy_sub": "Купить подписку",
        "btn_withdraw_ref": "Вывести реф. баланс",
        "btn_buy_with_ref": "Купить подписку на реф. баланс",
        "btn_back_menu": "В меню",
        "btn_ad_broadcast": "Рекламные рассылки",
        "ad_broadcast_enabled": '<b>Рекламные рассылки</b>\n\nСтатус: <b>Включены</b>\n\nВы будете получать рекламные рассылки от бота.',
        "ad_broadcast_disabled": '<b>Рекламные рассылки</b>\n\nСтатус: <b>Отключены</b>\n\nВы не будете получать рекламные рассылки от бота.',
        "ad_broadcast_sub_required": '<b>Рекламные рассылки</b>\n\nОтключение рекламных рассылок доступно только пользователям с активной подпиской.',
        "btn_toggle_ad_broadcast": "Изменить статус",
        
        # Меню выбора действия для файла
        "file_action_menu": '<tg-emoji emoji-id="5348319041935132191">📄</tg-emoji> <b>Файл получен!</b>\n\nВыберите действие с файлом:',
        "btn_check_file": "🔍 Проверить куки",
        "btn_fresh_file": "🔄 Фрешнуть куки",
        "btn_validate_file": "✅ Проверить валидность",
        "btn_duplicate_file": "📋 Дублировать куки",
        "btn_cancel_file": "Отмена",
        
        # Активация ключа
        "activate_key_title": '<tg-emoji emoji-id="5348532407320463735">🔑</tg-emoji> <b>Активация подписки по ключу</b>\n\nВведите ключ:',
        "key_not_found": '<tg-emoji emoji-id="5348127009652361348">❌</tg-emoji> Ключ не найден или уже использован.',
        "key_activated": '<tg-emoji emoji-id="5348142956865932724">✅</tg-emoji> Ключ успешно активирован!\nПодписка продлена {days_text}',
        "try_another_key": 'Попробуйте другой ключ или вернитесь в меню.',
        "btn_try_another": "Попробовать другой ключ",
        
        # Покупка подписки
        "buy_menu_title": '<tg-emoji emoji-id="5778407832776871799">💳</tg-emoji> <b>Выберите план подписки</b>\n{rate_info}\nОплата в USDT/TON по текущему курсу',
        "buy_menu_forever": "Навсегда",
        "buy_menu_days": "{days} дней",
        "btn_trial": "Получить тестовую подписку (1 день)",
        "trial_unavailable": '<tg-emoji emoji-id="5348125703982303915">❌</tg-emoji> Тестовая подписка сейчас недоступна.',
        "trial_already_claimed": '<tg-emoji emoji-id="5348241083983745758">❌</tg-emoji> Вы уже получали тестовую подписку.',
        "trial_activated": '<tg-emoji emoji-id="5348319041935132191">✅</tg-emoji> Тестовая подписка на 1 день активирована!',
        "creating_payment": '🔄 Создаём платёж...\n💳 План: {plan}\n💰 Сумма: {price} RUB\n🎯 Конвертируется в USDT/TON по текущему курсу',
        "invoice_created": '<tg-emoji emoji-id="5359719332542718652">💎</tg-emoji> <b>Для оплаты нажмите кнопку ниже</b>\n<blockquote>Сумма: {price} RUB\nВремя на оплату: 1 час</blockquote>\nПосле оплаты нажмите «Проверить оплату»',
        "btn_pay": "💳 Оплатить в боте",
        "btn_check_payment": "🔄 Проверить оплату",
        "payment_success": 'Оплата прошла успешно!\nПодписка активирована {days_text}',
        "payment_unknown": 'Оплата прошла, но тип платежа неизвестен. Обратитесь в поддержку.',
        "payment_pending": 'Платёж ещё не завершён. Подождите или нажмите кнопку ещё раз через 10 секунд.',
        "payment_expired": 'Счёт просрочен или отменён.',
        "payment_error": 'Ошибка связи с платёжной системой',
        "invoice_not_found": 'Счёт не найден',
        
        # Покупка на реф. баланс
        "buy_with_ref_title": '<tg-emoji emoji-id="5350716634413681396">💳</tg-emoji> <b>Купить подписку на реф. баланс</b>\n\n<tg-emoji emoji-id="5348037463879207320">💰</tg-emoji> Ваш баланс: {balance} RUB',
        "buy_with_ref_forever": 'Навсегда - {price} RUB (с реф. баланса)',
        "buy_with_ref_days": '{days} дней - {price} RUB (с реф. баланса)',
        "insufficient_funds": '<tg-emoji emoji-id="5350519400925515717">❌</tg-emoji> Недостаточно средств на реф. балансе.',
        "purchased_with_ref": '<tg-emoji emoji-id="5350688446543319173">✅</tg-emoji> Подписка куплена на реф. баланс! Активирована {days_text}.',
        
        # Вывод средств
        "withdraw_title": '<tg-emoji emoji-id="5348495118414399621">💸</tg-emoji> <b>Вывод реф. баланса</b>\nВаш баланс: {balance} RUB\n\nВведите сумму для вывода (от 200 до {balance}):',
        "withdraw_invalid_amount": '<tg-emoji emoji-id="5350456973575865566">❌</tg-emoji> Сумма должна быть от 200 до вашего баланса.',
        "withdraw_request_created": '<tg-emoji emoji-id="5350522390222752741">✅</tg-emoji> Заявка на вывод {amount} RUB создана! Ожидайте обработки администратором.',
        "withdraw_admin_notify": '<tg-emoji emoji-id="5350387030033451336">🆕</tg-emoji> Новая заявка на вывод от {user_id}:\nСумма: {amount} RUB',
        "btn_complete_withdraw": "Выполнить заявку",
        "withdraw_completed": '<tg-emoji emoji-id="5350526607880635633">✅</tg-emoji> Заявка выполнена.',
        "withdraw_completed_user": '<tg-emoji emoji-id="5350411434037627118">✅</tg-emoji> Ваша заявка на вывод одобрена!\nСсылка на выплату: {link}',
        "withdraw_not_found": '<tg-emoji emoji-id="5350499644075954298">❌</tg-emoji> Заявка не найдена или уже выполнена.',
        
        # Глобальная статистика
        "stats_title": '<b><tg-emoji emoji-id="5803421391596294672">💸</tg-emoji> ГЛОБАЛЬНАЯ СТАТИСТИКА ЗА ВСЕ ВРЕМЯ</b>',
        "stats_total_donate": "Всего доната: <code>{total_donate:,}</code> R$",
        "stats_total_balance": "Всего баланса: <code>{total_balance:,}</code> R$",
        "stats_total_pending": "Всего пендинга: <code>{total_pending:,}</code> R$",
        "stats_total_rap": 'Всего RAP: <code>{total_rap:,}</code> R$',
        "stats_total_groups": 'Всего баланса групп: <code>{total_groups_balance:,}</code> R$',
        "stats_total_checked": 'Всего проверили куков: <code>{total_cookies_checked:,}</code>',
        "stats_total_freshed": 'Всего фрешнули куков: <code>{total_cookies_freshed:,}</code>',
        
        # Меню чекера
        "checker_menu": '<tg-emoji emoji-id="5855015738506482494">🍪</tg-emoji> <b>Меню чекера</b>\nВыберите опцию ниже:',
        "checker_no_sub": '<tg-emoji emoji-id="5801094756272444286">☠️</tg-emoji> Доступ к чекеру требует активной подписки.\nПерейдите в профиль для покупки',
        "btn_settings": "Настройки",
        "btn_start_check": "Начать чек",
        
        # Меню валидатора
        "validator_menu": '<tg-emoji emoji-id="5855015738506482494">🍪</tg-emoji> <b>Меню валидатора</b>\nПростая проверка куков на валидность',
        "validator_no_sub": '<tg-emoji emoji-id="5801094756272444286">☠️</tg-emoji> Доступ к валидатору требует активной подписки.\nПерейдите в профиль для покупки.',
        "btn_start_validation": "Начать валидацию",
        
        # Меню фрешера
        "fresher_menu": '<tg-emoji emoji-id="5855015738506482494">🍪</tg-emoji> <b>Меню фрешера</b>\nВыберите опцию ниже:',
        "fresher_no_sub": '<tg-emoji emoji-id="5801094756272444286">☠️</tg-emoji> Доступ к фрешеру требует активной подписки.\nПерейдите в профиль для покупки.',
        "btn_start_fresh": "Начать фреш",
        "fresher_warning": '<tg-emoji emoji-id="6048805272787357971">📤</tg-emoji> <b>Отправьте файл с куками для фреша</b>\nПоддерживаемые форматы: .txt \n\nВНИМАНИЕ\nМы не несем ответственность за фрешер куков.\nПользоваться можете, но только на свой страх и риск',
        
        # Остальные функции
        "other_functions_title": '<tg-emoji emoji-id="5800942272048533376">🔀</tg-emoji> <b>Остальные функции</b>\n\nДубликатор куки\nСортер',
        "btn_duplicator": "Дубликатор",
        "btn_sorter": "Сортер",
        
        # Дубликатор
        "duplicator_menu": '<tg-emoji emoji-id="5855015738506482494">🍪</tg-emoji> <b>Меню дубликатора</b>\n\nДублирует активную сессию Roblox (создаёт новый валидный куки на основе нынешнего, без логаута из текущего устройства, эта сессия никому не видна)',
        "btn_start_duplicate": "Начать дублирование",
        "duplicate_file_request": '<tg-emoji emoji-id="5348373068328751172">📤</tg-emoji> <b>Отправьте файл с куками для дублирования</b>\n\nПоддерживаемые форматы: .txt',
        
        # Сортер
        "sorter_menu": '<tg-emoji emoji-id="5855015738506482494">🍪</tg-emoji> <b>Сортер куков</b>\n\nЭто функция для объединения нескольких файлов с куками в один, исключая дубликаты.\n\nОтправьте несколько файлов с куками (.txt), а затем нажмите \'Объединить\'.',
        "sorter_file_added": '<tg-emoji emoji-id="5348120597266190780">✅</tg-emoji> Файл добавлен. Всего файлов: {count}\n\nОтправьте ещё или нажмите \'Объединить\'.',
        "sorter_no_files": '<tg-emoji emoji-id="5348432867158412360">❌</tg-emoji> Нет файлов для объединения.',
        "sorter_merged": '<tg-emoji emoji-id="5364081859674262626">✅</tg-emoji> Объединено {count} уникальных куков.',
        "sorter_no_cookies": '<tg-emoji emoji-id="5350685607569934181">❌</tg-emoji> Нет куков в файлах.',
        "btn_merge": "Объединить",
        "btn_shuffle": "🔀 Перемешать куки",
        "shuffled": '<tg-emoji emoji-id="5348532407320463735">✅</tg-emoji> Куки перемешаны ({count} шт.).',
        
        # Настройки
        "settings_title": '<tg-emoji emoji-id="6048747647211148173">⚙️</tg-emoji> <b>Настройки чекера</b>\nНастройте параметры проверки:',
        "btn_checks": "Что проверять",
        "btn_ingame": "InGame Donate",
        "btn_playtime": "Playtime",
        "btn_badges": "Бейджи",
        "btn_gamepasses": "Геймпассы",
        "btn_output_format": "Формат вывода",
        
        # Выбор параметров проверки
        "checks_title": '<tg-emoji emoji-id="6021451978993834164">🔍</tg-emoji> <b>Выбор параметров проверки</b>\nВыберите, что проверять:',
        
        # Формат вывода
        "output_format_title": '<tg-emoji emoji-id="6021856393114426113">📤</tg-emoji> <b>Формат вывода результатов</b>\nТекущий: {current}\n\nВыберите формат:',
        "output_format_zip": 'ZIP-архив',
        "output_format_txt": 'Текстовыми файлами',
        
        # InGame Donate
        "ingame_title": '<tg-emoji emoji-id="5258508428212445001">🎮</tg-emoji> <b>Выбор игр для InGame Donate</b>\nВыберите игры для проверки донатов:',
        
        # Playtime
        "playtime_title": '<tg-emoji emoji-id="5199457120428249992">🕰️</tg-emoji> <b>Выбор игр для Playtime</b>\nВыберите игры для проверки времени игры:',
        
        # Бейджи
        "badges_title": '<tg-emoji emoji-id="6021594546138257831">🎖️</tg-emoji> <b>Выбор бейджей</b>\nВыберите игры для проверки бейджей:',
        "btn_custom_badges": "📥 Ввести свои бейджи",
        "btn_create_config_badges": "🆕 Создать конфиг",
        "badges_lists_title": '<tg-emoji emoji-id="6021594546138257831">📋</tg-emoji> <b>Готовые списки бейджей</b>\nВыберите списки для проверки:',
        
        # Геймпассы
        "gamepasses_title": '<tg-emoji emoji-id="6021428854889913572">🎟️</tg-emoji> <b>Выбор геймпассов</b>\nВыберите игры для проверки геймпассов:',
        "btn_custom_gamepasses": "📥 Ввести свои геймпассы",
        "btn_create_config_gamepasses": "🆕 Создать конфиг",
        "gamepasses_lists_title": '<tg-emoji emoji-id="6021428854889913572">📋</tg-emoji> <b>Готовые списки геймпассов</b>\nВыберите списки для проверки:',
        
        # Ввод ID
        "enter_ids": '<tg-emoji emoji-id="6021741116192201252">📥</tg-emoji> <b>Вставьте список ID {item}</b>\nЧерез запятую или новую строку:',
        "enter_config_name": '<tg-emoji emoji-id="6021741116192201252">🆕</tg-emoji> <b>Введите название конфига для {item}</b>:',
        "parse_error": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Ошибка парсинга ID',
        
        # Отправка файлов
        "send_file": '<tg-emoji emoji-id="6021856393114426113">📤</tg-emoji> <b>Отправьте файл с куками</b>\nПоддерживаемые форматы: .txt',
        "send_validation_file": '<tg-emoji emoji-id="6021856393114426113">📤</tg-emoji> <b>Отправьте файл с куками для валидации</b>\nПоддерживаемые форматы: .txt',
        "no_cookies": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Не найдено куков в файле',
        "no_valid_cookies": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Нет валидных куков после проверки.',
        "invalid_format": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Пожалуйста, отправьте файл в формате .txt',
        
        # Прогресс
        "progress_validating": '<tg-emoji emoji-id="5807492110059838726">🔄</tg-emoji> <b>Валидация куков...</b>\nПрогресс: {current} / {total}',
        "progress_checking_stats": '<tg-emoji emoji-id="5807492110059838726">🔄</tg-emoji> <b>Проверка статистики...</b>\nПрогресс: {current} / {total}',
        "progress_freshing": '<tg-emoji emoji-id="5807492110059838726">🔄</tg-emoji> <b>Фрешим куки...</b>',
        "progress_duplicating": '<tg-emoji emoji-id="5807492110059838726">🔄</tg-emoji> <b>Дублируем куки...</b>',
        
        # Лимиты
        "limit_exceeded": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Превышен лимит проверки куков за час!\n\nЛимит: 100 000 куков в час\nУже проверено за последний час: <code>{used:,}</code>\nВ этом файле: <code>{file:,}</code>\nВсего превысит лимит на: <code>{excess:,}</code>\n\nПодождите ~1 час или разделите файл на части поменьше.',
        
        # Результаты валидации
        "validation_results": '<tg-emoji emoji-id="5348025622654373581">✅</tg-emoji> <b>РЕЗУЛЬТАТЫ ВАЛИДАЦИИ</b>\n📊 Общая статистика:\n├ Всего куков: <code>{total:,}</code>\n├ Валидных: <code>{valid:,}</code>\n└ Невалидных: <code>{invalid:,}</code>',
        "no_valid_cookies_found": '<tg-emoji emoji-id="5348300225683410403">❌</tg-emoji> <b>Не найдено валидных куков</b>\n\nПопробуйте другой файл или проверьте формат куков.',
        
        # Результаты фреша
        "fresh_results_success": '<tg-emoji emoji-id="6019175208240289774">✅</tg-emoji> <b>Фреш завершён успешно!</b>\n\nУспешно обновлено: <code>{success:,}</code> куков\n❌ Не удалось: <code>{failed:,}</code>\n\n📄 Файл с новыми куками выше 👆',
        "fresh_results_no_success": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Не удалось зафрешить ни одного куки.',
        "fresh_file_error": '<tg-emoji emoji-id="5350539819200039889">⚠️</tg-emoji> Не удалось отправить файл (лимит Telegram или ошибка сети)',
        "send_cookie_file": '<tg-emoji emoji-id="5348495118414399621">❌</tg-emoji> <b>Отправьте файл с куками</b>\n<blockquote>Поддерживаемые форматы: .txt</blockquote>',
        # Результаты дубликатора
        "duplicate_results_success": '<tg-emoji emoji-id="6019175208240289774">✅</tg-emoji> <b>Дублирование завершено!</b>\n\nУспешно: <code>{success:,}</code> куков\n❌ Не удалось: <code>{failed:,}</code>\n\n📄 Файл с новыми (дублированными) куками выше 👆',
        "duplicate_results_no_success": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Не удалось дублировать ни одного куки.',
        
        # Результаты чекера
        "checker_results_title": '<tg-emoji emoji-id="5258278668936945760">🔫</tg-emoji> <b>РЕЗУЛЬТАТЫ ПРОВЕРКИ</b>',
        "checker_results_valid": '<tg-emoji emoji-id="6019175208240289774">✅</tg-emoji> Валидных <code>{valid:,}</code>',
        "checker_results_invalid": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Невалидных <code>{invalid:,}</code>\n\n',
        "checker_results_price": '<tg-emoji emoji-id="5258204546391351475">💰</tg-emoji> <b>Оценка пачки:</b> <code>~{price:,} USDT</code>\n\n',
        
        # Финансовая статистика
        "finance_title": '\n<tg-emoji emoji-id="5258204546391351475">💰</tg-emoji> <b>ФИНАНСОВАЯ СТАТИСТИКА\n</b>',
        "finance_balance": '\nБаланс: <code>{sum:,}</code> R$ (<code>{count}</code> акк, AVG: <code>{avg:.1f}</code>)',
"finance_donate_year": '\nДонат (год): <code>{sum:,}</code> R$ (<code>{count}</code> акк, AVG: <code>{avg:.1f}</code>)',
"finance_donate_lifetime": '\nВсего донат: <code>{sum:,}</code> R$ (<code>{count:,}</code> акк, AVG: <code>{avg:.1f}</code>)',
"finance_pending": '\nПендинг: <code>{sum:,}</code> R$',
"finance_rap": '\nRAP: <code>{sum:,}</code> R$',
"finance_billing": '\nБиллинг: <code>{sum:,}</code> R$',
        
        # Статистика аккаунтов
        "accounts_title": '\n\n<tg-emoji emoji-id="5257969839313526622">📂</tg-emoji> <b>СТАТИСТИКА АККАУНТОВ\n</b>',
        "accounts_cards": '\nКарты: <code>{count:,}</code>',
"accounts_premium": '\nПремиум: <code>{count:,}</code>',
"accounts_no_email": '\nБез почты: <code>{count:,}</code>',
"accounts_korblox": '\nKorblox: <code>{count:,}</code>',
"accounts_headless": '\nHeadless: <code>{count:,}</code>',
"accounts_badges": '\nБейджей: <code>{sum:,}</code>',
"accounts_gamepasses": '\nГеймпассов: <code>{sum:,}</code>',
"accounts_groups": '\nБаланс групп: <code>{sum:,}</code> R$',
"accounts_visits": '\nВизиты: <code>{sum:,}</code>',
"accounts_passable": '\nPassable: <code>{passable:,}</code>\nUnpassable: <code>{unpassable:,}</code>',
"accounts_rare_items": '\nRare Items: <code>{count:,}</code>',
        
        # In-Game Donations
        "ingame_results": '\n\n<tg-emoji emoji-id="5258508428212445001">🎮</tg-emoji> <b>IN-GAME DONATIONS:\n</b>',
        "playtime_results": '\n\n<tg-emoji emoji-id="5199457120428249992">🕘</tg-emoji> <b>PLAYTIME MINUTES:\n</b>',
        
        # Кнопки
        "btn_web_report": "📊 Веб-отчёт",
        "btn_back": "Назад",
        "btn_cancel": "❌ Отмена",
        
        # Команды
        "command_cancelled": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Действие отменено. Вернитесь в меню',
        "no_access": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Нет доступа',
        
        # Админские команды
        "keys_usage": '<tg-emoji emoji-id="5366077477573643872">❌</tg-emoji> Формат: /keys <plan> <count>\nДоступные планы: {plans}\nПример: /keys month 10',
        "keys_count_error": '<tg-emoji emoji-id="5364072548185165702">❌</tg-emoji> Количество ключей должно быть от 1 до 100',
        "keys_plan_error": '<tg-emoji emoji-id="5363872067701722306">❌</tg-emoji> Некорректный план. Доступные: {plans}',
        "keys_created": '<tg-emoji emoji-id="5366341798450973386">✅</tg-emoji> Создано <b>{count}</b> ключей для плана <b>{plan}</b>:\n\n<code>{keys}</code>',
        "keys_error": '<tg-emoji emoji-id="5364089324327423737">❌</tg-emoji> Ошибка при создании ключей',
        
        "check_usage": '<tg-emoji emoji-id="5364349719604646468">❌</tg-emoji> Формат: /check <user_id или username>',
        "user_not_found": '<tg-emoji emoji-id="5350374243915813874">❌</tg-emoji> Пользователь не найден по username',
        
        "addsub_usage": '<tg-emoji emoji-id="5348373068328751172">❌</tg-emoji> Формат: /addsub <user_id> <days>',
        "addsub_success": '<tg-emoji emoji-id="5366493793048611678">✅</tg-emoji> Подписка добавлена для {user_id} на {days} дней',
        "addsub_notify": '<tg-emoji emoji-id="5348120597266190780">✅</tg-emoji> Администратор добавил вам подписку на {days} дней!',
        
        "post_no_text": '<tg-emoji emoji-id="5348432867158412360">❌</tg-emoji> Укажите сообщение',
        "post_sent": '<tg-emoji emoji-id="5364081859674262626">✅</tg-emoji> Рассылка отправлена ({sent}/{total} получателей)',
        
        # Админ панель
        "admin_panel": '<tg-emoji emoji-id="5350685607569934181">📊</tg-emoji> <b>АДМИН ПАНЕЛЬ</b>\n\n<tg-emoji emoji-id="5348222877617375207">👥</tg-emoji> Всего пользователей: <code>{users:,}</code>\n<tg-emoji emoji-id="5348532407320463735">✅</tg-emoji> Активных подписок: <code>{active:,}</code>\n<tg-emoji emoji-id="5348127009652361348">💰</tg-emoji> Общий реф. заработок: <code>{ref_sum:,}</code> RUB',
        "btn_restart": "🔄 Перезапустить бота",
        "btn_edit_files": "📂 Изменить файлы",
        "btn_download_files": "📥 Скачать файлы",
        "btn_confirm_restart": "⚠️ Подтвердить перезапуск",
        "restart_cancelled": '<tg-emoji emoji-id="5348142956865932724">❌</tg-emoji> Перезапуск отменён',
        "restarting": '<tg-emoji emoji-id="5350322072948066951">🔄</tg-emoji> Перезапуск бота...',
        
        # Файлы
        "files_menu": '<tg-emoji emoji-id="5778407832776871799">📂</tg-emoji> <b>Файлы в текущей директории</b>\n\n📊 <b>Статистика:</b>\n• Файлов: <code>{count}</code>\n• Общий размер: <code>{size}</code>\n• Папки не отображаются\n\n<i>Выберите файл для скачивания:</i>',
        "no_files": '<tg-emoji emoji-id="5348341989945395276">📂</tg-emoji> <b>Нет файлов для скачивания</b>\n\nВ текущей директории не найдено файлов.\nПапки не отображаются - только файлы.',
        "file_not_found": '<tg-emoji emoji-id="5348527330669119684">❌</tg-emoji> Файл не найден или был удалён',
        "file_too_large": '<tg-emoji emoji-id="5348125703982303915">⚠️</tg-emoji> <b>Файл слишком большой</b>\n\n📄 Файл: <code>{name}</code>\n📏 Размер: {size:.1f} MB\n⏰ Изменен: {time}\n\n❌ Telegram не позволяет отправлять файлы больше 50MB.\nМаксимальный размер: 48 MB (с запасом).',
        "file_sent": '<tg-emoji emoji-id="5348241083983745758">📄</tg-emoji> <b>Файл отправлен</b>\n\nИмя: <code>{name}</code>\n📏 Размер: {size}\n⏰ Изменен: {time}\n👤 Отправитель: <code>{user_id}</code>',
        "file_send_error": '<tg-emoji emoji-id="5348319041935132191">❌</tg-emoji> <b>Ошибка отправки файла</b>\n\nФайл: <code>{name}</code>\nОшибка: {error}',
        "btn_refresh": "🔄 Обновить список",
    }
    
    # Английский язык
    en = {
        # Приветствие и главное меню
        "welcome": """<tg-emoji emoji-id="5855154023568510775">☠️</tg-emoji> Welcome to 227 Checker!
<blockquote>Check and fresh cookies easily and conveniently.</blockquote>

OOO "Разъеб хаха" """,
        "main_menu": """<tg-emoji emoji-id="5855015738506482494">🏠</tg-emoji> <b>Checker menu</b>
        Choose an option below:""",

        # Ошибки и уведомления
        "send_cookie_file": '<tg-emoji emoji-id="5348495118414399621">❌</tg-emoji> <b>Send cookie file</b>\n<blockquote>Supported formats: .txt</blockquote>',

        # Кнопки главного меню
        "btn_checker": "Cookie Checker",
        "btn_fresher": "Cookie Fresher",
        "btn_validator": "Cookie Validator",
        "btn_stats": "Statistics",
        "btn_profile": "Profile",
        "btn_other": "Other functions",
        "btn_language": "Language / Language",

        # Настройка пользовательских игр
        'btn_custom_game1': '🎮 Game 1',
        'btn_custom_game2': '🎮 Game 2',
        'custom_game_setup': '🔗 Custom game setup {num}',
        'custom_game_url_prompt': 'Send Roblox game link\nOr /skip to skip',
        'custom_game_name_prompt': 'Enter a name to display in results',
        'custom_game_added': '✅ Game "{name}" successfully added!',
        'custom_game_reset': '🔄 Game reset to default',

        # Магазин (ссылка)
        'shop_text': '<b>Buy for RUB/LOLZ</b> - <a href="https://t.me/S1PshopBot">@S1PshopBot</a>',

        # Языковое меню
        "select_language": '<tg-emoji emoji-id="6050689397630702147">🌐</tg-emoji> <b>Select language / Select language</b>',
        "btn_russian": "🇷🇺 Russian",
        "btn_english": "🇬🇧 English",
        "language_changed": '<tg-emoji emoji-id="6050689397630702147">✅</tg-emoji> Language changed to English',

        # Проверка подписки
        "need_subscription": '<tg-emoji emoji-id="5363790055301205826">❌</tg-emoji> To use the bot, you need to subscribe to our channel!\n\n<tg-emoji emoji-id="5366077477573643872">📢</tg-emoji> Click the button below and subscribe to the channel, then click \'Check subscription\'',
        "btn_subscribe": "Subscribe to channel",
        "btn_check_sub": "Check subscription",
        "not_subscribed": '<tg-emoji emoji-id="5366341798450973386">❌</tg-emoji> You are still not subscribed to the channel!',
        "sub_check_error": '<tg-emoji emoji-id="5364089324327423737">❌</tg-emoji> Subscription check error. Try again later.',

        # Профиль
        "profile_title": '<tg-emoji emoji-id="5855015738506482494">👤</tg-emoji> <b>Your profile</b><blockquote>',
        "profile_id": 'ID: <code>{user_id}</code>',
        "profile_reg": 'Registration: {reg_date}',
        "profile_sub_active_forever": 'Subscription: Active (forever) <tg-emoji emoji-id="5366493793048611678">🎉</tg-emoji>',
        "profile_sub_active_days": 'Subscription: Active ({days} {days_word} left)',
        "profile_sub_active_less_day": 'Subscription: Active (less than a day left)',
        "profile_sub_inactive": 'Subscription: None',
        "profile_ref_balance": 'Referral balance: {balance} RUB',
        "profile_ref_count": 'Referrals: {count}',
        "profile_checked": 'Cookies checked: <code>{checked:,}</code>',
        "profile_freshed": 'Cookies freshed: <code>{freshed:,}</code>',
        "profile_ref_link": 'Referral link: {link}</blockquote>',

        # Активация ключа
        'already_subscribed': '❌ You already have an active subscription',

        # Покупка подписки
        'exchange_rate': 'Current rate: 1 USDT ≈ {rate:.2f} RUB',
        'payment_url_error': '❌ Error: failed to get payment link',

        # Покупка с реферального баланса

        # Вывод средств
        'enter_payout_link': '📤 Enter payout link:',
        'invalid_amount': '❌ Invalid amount.',

        # Пробная подписка

        # Реферальная система
        'referral_purchase_notify': '💰 Your referral bought a subscription!\n+{amount} RUB added to referral balance',

        # Админские команды

        # Слова для дней
        "days_word_1": "day",
        "days_word_2": "days",
        "days_word_5": "days",

        # Кнопки профиля
        "btn_activate_key": "Activate key",
        "btn_buy_sub": "Buy subscription",
        "btn_withdraw_ref": "Withdraw referral balance",
        "btn_buy_with_ref": "Buy subscription with referral balance",
        "btn_back_menu": "Back to menu",
        "btn_ad_broadcast": "Ad broadcasts",
        "ad_broadcast_enabled": '<b>Ad broadcasts</b>\n\nStatus: <b>Enabled</b>\n\nYou will receive ad broadcasts from the bot.',
        "ad_broadcast_disabled": '<b>Ad broadcasts</b>\n\nStatus: <b>Disabled</b>\n\nYou will not receive ad broadcasts from the bot.',
        "ad_broadcast_sub_required": '<b>Ad broadcasts</b>\n\nDisabling ad broadcasts is only available for users with an active subscription.',
        "btn_toggle_ad_broadcast": "Toggle status",
        
        # Меню выбора действия для файла
        "file_action_menu": '<tg-emoji emoji-id="5348319041935132191">📄</tg-emoji> <b>File received!</b>\n\nChoose an action for the file:',
        "btn_check_file": "🔍 Check cookies",
        "btn_fresh_file": "🔄 Fresh cookies",
        "btn_validate_file": "✅ Validate cookies",
        "btn_duplicate_file": "📋 Duplicate cookies",
        "btn_cancel_file": "Cancel",

        # Активация ключа (подробнее)
        "activate_key_title": '<tg-emoji emoji-id="5348532407320463735">🔑</tg-emoji> <b>Activate subscription by key</b>\n\nEnter the key:',
        "key_not_found": '<tg-emoji emoji-id="5348127009652361348">❌</tg-emoji> Key not found or already used.',
        "key_activated": '<tg-emoji emoji-id="5348142956865932724">✅</tg-emoji> Key successfully activated!\nSubscription extended {days_text}',
        "try_another_key": 'Try another key or return to menu.',
        "btn_try_another": "Try another key",

        # Покупка подписки (подробнее)
        "buy_menu_title": '<tg-emoji emoji-id="5778407832776871799">💳</tg-emoji> <b>Choose subscription plan</b>\n{rate_info}\nPayment in USDT/TON at current rate',
        "buy_menu_forever": "Forever",
        "buy_menu_days": "{days} days",
        "btn_trial": "Get trial subscription (1 day)",
        "trial_unavailable": '<tg-emoji emoji-id="5348125703982303915">❌</tg-emoji> Trial subscription is currently unavailable.',
        "trial_already_claimed": '<tg-emoji emoji-id="5348241083983745758">❌</tg-emoji> You have already received a trial subscription.',
        "trial_activated": '<tg-emoji emoji-id="5348319041935132191">✅</tg-emoji> 1-day trial subscription activated!',
        "creating_payment": '🔄 Creating payment...\n💳 Plan: {plan}\n💰 Amount: {price} RUB\n🎯 Converted to USDT/TON at current rate',
        "invoice_created": '<tg-emoji emoji-id="5359719332542718652">💎</tg-emoji> <b>Click the button below to pay</b>\n<blockquote>Amount: {price} RUB\nPayment time: 1 hour</blockquote>\nAfter payment, click «Check payment»',
        "btn_pay": "💳 Pay in bot",
        "btn_check_payment": "🔄 Check payment",
        "payment_success": 'Payment successful!\nSubscription activated {days_text}',
        "payment_unknown": 'Payment successful, but payment type unknown. Contact support.',
        "payment_pending": 'Payment not completed yet. Wait or click the button again in 10 seconds.',
        "payment_expired": 'Invoice expired or cancelled.',
        "payment_error": 'Error connecting to payment system',
        "invoice_not_found": 'Invoice not found',
        # В словарь en добавьте:
"btn_check_subscription": "✅ I'm subscribed",
"bonus_sponsor_required": "🎁 <b>To receive bonus days you need to subscribe to all channels below:</b>\n\nAfter subscribing, click the 'I'm subscribed' button",
"bonus_not_subscribed_list": "❌ <b>You are not subscribed to the following channels:</b>\n\n{channels}\n\nPlease subscribe and click the button again.",

        # Покупка на реф. баланс (подробнее)
        "buy_with_ref_title": '<tg-emoji emoji-id="5350716634413681396">💳</tg-emoji> <b>Buy subscription with referral balance</b>\n\n<tg-emoji emoji-id="5348037463879207320">💰</tg-emoji> Your balance: {balance} RUB',
        "buy_with_ref_forever": 'Forever - {price} RUB (with referral balance)',
        "buy_with_ref_days": '{days} days - {price} RUB (with referral balance)',
        "insufficient_funds": '<tg-emoji emoji-id="5350519400925515717">❌</tg-emoji> Insufficient funds on referral balance.',
        "purchased_with_ref": '<tg-emoji emoji-id="5350688446543319173">✅</tg-emoji> Subscription purchased with referral balance! Activated {days_text}.',

        # Вывод средств (подробнее)
        "withdraw_title": '<tg-emoji emoji-id="5348495118414399621">💸</tg-emoji> <b>Withdraw referral balance</b>\nYour balance: {balance} RUB\n\nEnter amount to withdraw (from 200 to {balance}):',
        "withdraw_invalid_amount": '<tg-emoji emoji-id="5350456973575865566">❌</tg-emoji> Amount must be from 200 to your balance.',
        "withdraw_request_created": '<tg-emoji emoji-id="5350522390222752741">✅</tg-emoji> Withdrawal request for {amount} RUB created! Waiting for admin processing.',
        "withdraw_admin_notify": '<tg-emoji emoji-id="5350387030033451336">🆕</tg-emoji> New withdrawal request from {user_id}:\nAmount: {amount} RUB',
        "btn_complete_withdraw": "Complete request",
        "withdraw_completed": '<tg-emoji emoji-id="5350526607880635633">✅</tg-emoji> Request completed.',
        "withdraw_completed_user": '<tg-emoji emoji-id="5350411434037627118">✅</tg-emoji> Your withdrawal request has been approved!\nPayout link: {link}',
        "withdraw_not_found": '<tg-emoji emoji-id="5350499644075954298">❌</tg-emoji> Request not found or already completed.',

        # Глобальная статистика
        "stats_title": """<b><tg-emoji emoji-id="5803421391596294672">💸</tg-emoji> GLOBAL STATISTICS FOR ALL TIME</b>""",
        "stats_total_donate": "<blockquote>Total donate: <code>{total_donate:,}</code> R$",
        "stats_total_balance": "Total balance: <code>{total_balance:,}</code> R$",
        "stats_total_pending": "Total pending: <code>{total_pending:,}</code> R$",
        "stats_total_rap": 'Total RAP: <code>{total_rap:,}</code> R$',
        "stats_total_groups": 'Total groups balance: <code>{total_groups_balance:,}</code> R$',
        "stats_total_checked": 'Total cookies checked: <code>{total_cookies_checked:,}</code>',
        "stats_total_freshed": 'Total cookies freshed: <code>{total_cookies_freshed:,}</code> </blockquote>',

        # Меню чекера
        "checker_menu": '<tg-emoji emoji-id="5855015738506482494">🍪</tg-emoji> <b>Checker menu</b>\n<blockquote>Choose an option below:</blockquote>',
        "checker_no_sub": '<tg-emoji emoji-id="5801094756272444286">☠️</tg-emoji> Access to checker requires an active subscription.\n</blockquote>Go to profile to purchase</blockquote>',
        "btn_settings": "Settings",
        "btn_start_check": "Start check",
        'en': '❌ <b>Sorter is only available with an active subscription!</b>\n\nPurchase a subscription in your profile.',

        # Меню валидатора
        "validator_menu": '<tg-emoji emoji-id="5855015738506482494">🍪</tg-emoji> <b>Validator menu</b>\nSimple cookie validity check',
        "validator_no_sub": '<tg-emoji emoji-id="5801094756272444286">☠️</tg-emoji> Access to validator requires an active subscription.\nGo to profile to purchase.',
        "btn_start_validation": "Start validation",

        # Меню фрешера
        "fresher_menu": '<tg-emoji emoji-id="5855015738506482494">🍪</tg-emoji> <b>Fresher menu</b>\nChoose an option below:',
        "fresher_no_sub": '<tg-emoji emoji-id="5801094756272444286">☠️</tg-emoji> Access to fresher requires an active subscription.\nGo to profile to purchase.',
        "btn_start_fresh": "Start fresh",
        "fresher_warning": '<tg-emoji emoji-id="6048805272787357971">📤</tg-emoji> <b>Send cookie file for freshing</b>\nSupported formats: .txt \n\n<blockquote>WARNING\nWe are not responsible for the cookie fresher.\nUse at your own risk</blockquote>',

        # Остальные функции
        "other_functions_title": '<tg-emoji emoji-id="5800942272048533376">🔀</tg-emoji> <b>Other functions</b>\n\n<blockquote><b>Cookie duplicator</b>\n<b>Sorter</b></blockquote>',
        "btn_duplicator": "Duplicator",
        "btn_sorter": "Sorter",

        # Дубликатор
        "duplicator_menu": '<tg-emoji emoji-id="5855015738506482494">🍪</tg-emoji> <b>Duplicator menu</b>\n\nDuplicates an active Roblox session (creates a new valid cookie based on the current one, without logout from the current device, this session is invisible to anyone)\n',
        "btn_start_duplicate": "Start duplication",
        "duplicate_file_request": '<tg-emoji emoji-id="5348373068328751172">📤</tg-emoji> <b>Send cookie file for duplication</b>\n\n<blockquote>Supported formats: .txt</blockquote> \n',

        # Сортер
        "sorter_menu": '<tg-emoji emoji-id="5855015738506482494">🍪</tg-emoji> <b>Cookie sorter</b>\n\nThis function combines multiple cookie files into one, excluding duplicates.\n\nSend several cookie files (.txt), then click \'Merge\'.',
        "sorter_file_added": '<tg-emoji emoji-id="5348120597266190780">✅</tg-emoji> File added. Total files: {count}\n\nSend more or click \'Merge\'.',
        "sorter_no_files": '<tg-emoji emoji-id="5348432867158412360">❌</tg-emoji> No files to merge.',
        "sorter_merged": '<tg-emoji emoji-id="5364081859674262626">✅</tg-emoji> Merged {count} unique cookies.',
        "sorter_no_cookies": '<tg-emoji emoji-id="5350685607569934181">❌</tg-emoji> No cookies in files.',
        "btn_merge": "Merge",
        "btn_shuffle": "🔀 Shuffle cookies",
        "shuffled": '<tg-emoji emoji-id="5348532407320463735">✅</tg-emoji> Cookies shuffled ({count} pcs).',

        # Настройки
        "settings_title": '<tg-emoji emoji-id="6048747647211148173">⚙️</tg-emoji> <b>Checker settings</b>\n<blockquote>Configure check parameters:</blockquote>',
        "btn_checks": "What to check",
        "btn_ingame": "InGame Donate",
        "btn_playtime": "Playtime",
        "btn_badges": "Badges",
        "btn_gamepasses": "Gamepasses",
        "btn_output_format": "Output format",

        # Выбор параметров проверки
        "checks_title": '<tg-emoji emoji-id="6021451978993834164">🔍</tg-emoji> <b>Select check parameters</b>\n<blockquote>Choose what to check:</blockquote>',

        # Формат вывода
        "output_format_title": '<tg-emoji emoji-id="6021856393114426113">📤</tg-emoji> <b>Results output format</b>\nCurrent: {current}\n\n<blockquote>Choose format:</blockquote>',
        "output_format_zip": 'ZIP archive',
        "output_format_txt": 'Text files',

        # InGame Donate
        "ingame_title": '<tg-emoji emoji-id="5258508428212445001">🎮</tg-emoji> <b>Select games for InGame Donate</b>\n<blockquote>Choose games to check donations:</blockquote>',

        # Playtime
        "playtime_title": '<tg-emoji emoji-id="5199457120428249992">🕰️</tg-emoji> <b>Select games for Playtime</b>\n<blockquote>Choose games to check playtime:</blockquote>',

        # Бейджи
        "btn_custom_badges": "📥 Enter custom badges",
        "btn_create_config_badges": "🆕 Create config",
        "badges_lists_title": '<tg-emoji emoji-id="6021594546138257831">📋</tg-emoji> <b>Ready badge lists</b>\n<blockquote>Select lists to check:</blockquote>',

        # Геймпассы
        "btn_custom_gamepasses": "📥 Enter custom gamepasses",
        "btn_create_config_gamepasses": "🆕 Create config",
        "gamepasses_lists_title": '<tg-emoji emoji-id="6021428854889913572">📋</tg-emoji> <b>Ready gamepass lists</b>\n<blockquote>Select lists to check:</blockquote>',

        # Ввод ID
        "enter_ids": '<tg-emoji emoji-id="6021741116192201252">📥</tg-emoji> <b>Enter list of {item} IDs</b>\n<blockquote>Separated by commas or new lines:<',
        "enter_config_name": '<tg-emoji emoji-id="6021741116192201252">🆕</tg-emoji> <b>Enter config name for {item}</b>:',
        "config_saved": '<tg-emoji emoji-id="6019175208240289774">✅</tg-emoji> Custom {item} saved as \'{name}\', enable them to use',
        "parse_error": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Error parsing IDs',
         "btn_bonus_days": "🎁 Bonus days",
    "bonus_checking": "🔍 Checking subscription to sponsor channels...",
    "bonus_not_subscribed": "❌ You are not subscribed to all sponsor channels.\nPlease subscribe and press the button again.",
    "bonus_already_claimed": "⏳ You have already claimed bonus this month. Next bonus available in {days_left} days.",
    "bonus_no_sponsors": "❌ Bonus program is temporarily unavailable.",
    "bonus_success": "✅ Bonus activated! 2 days added to your subscription.\nNew expiration: {expiry}",
    "admin_work_title": "🛠 Sponsor channels management\n\nTotal channels: {count}/5",
    "admin_work_list": "📋 Channel list:\n",
    "admin_work_item": "{index}. {link} (ID: {channel_id})\n",
    "admin_work_no_channels": "The list is empty.",
    "btn_add_channel": "➕ Add channel",
    "btn_remove_channel": "➖ Remove channel",
    "btn_clear_channels": "🗑 Clear all",
    "enter_channel_link": "🔗 Send channel link or ID (e.g., @channel or -1001234567890):",
    "invalid_channel_link": "❌ Invalid channel link or ID.",
    "channel_added": "✅ Channel added.",
    "channel_not_found": "❌ Channel not found in the list.",
    "channel_removed": "✅ Channel removed.",
    "channels_cleared": "✅ All sponsor channels removed.",
    "confirm_clear_channels": "⚠️ Are you sure you want to remove ALL sponsor channels?",
    "btn_confirm_clear": "✅ Yes, remove",

        # Отправка файлов
        "send_file": '<tg-emoji emoji-id="6021856393114426113">📤</tg-emoji> <b>Send cookie file</b>\nSupported formats: .txt',
        "send_validation_file": '<tg-emoji emoji-id="6021856393114426113">📤</tg-emoji> <b>Send cookie file for validation</b>\n<blockquote>Supported formats: .txt</blockquote>',
        "no_cookies": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> No cookies found in file',
        "no_valid_cookies": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> No valid cookies after check.',
        "invalid_format": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Please send a file in .txt format',

        # Прогресс
        "progress_validating": '<tg-emoji emoji-id="5807492110059838726">🔄</tg-emoji> <b>Validating cookies...</b>\nProgress: {current} / {total}',
        "progress_checking_stats": '<tg-emoji emoji-id="5807492110059838726">🔄</tg-emoji> <b>Checking statistics...</b>\nProgress: {current} / {total}',
        "progress_freshing": '<tg-emoji emoji-id="5807492110059838726">🔄</tg-emoji> <b>Freshing cookies...</b>',
        "progress_duplicating": '<tg-emoji emoji-id="5807492110059838726">🔄</tg-emoji> <b>Duplicating cookies...</b>',

        # Лимиты
        "limit_exceeded": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Hourly cookie check limit exceeded!\n\nLimit: 100,000 cookies per hour\nChecked in last hour: <code>{used:,}</code>\nIn this file: <code>{file:,}</code>\nTotal would exceed limit by: <code>{excess:,}</code>\n\nWait ~1 hour or split the file into smaller parts.',

        # Результаты валидации
        "validation_results": '<tg-emoji emoji-id="5348025622654373581">✅</tg-emoji> <b>VALIDATION RESULTS</b>\n📊 Total statistics:\n├ Total cookies: <code>{total:,}</code>\n├ Valid: <code>{valid:,}</code>\n└ Invalid: <code>{invalid:,}</code>',
        "no_valid_cookies_found": '<tg-emoji emoji-id="5348300225683410403">❌</tg-emoji> <b>No valid cookies found</b>\n\nTry another file or check cookie format.',

        # Результаты фреша
        "fresh_results_success": '<tg-emoji emoji-id="6019175208240289774">✅</tg-emoji> <b>Fresh completed successfully!</b>\n\nSuccessfully updated: <code>{success:,}</code> cookies\n❌ Failed: <code>{failed:,}</code>\n\n📄 File with new cookies above 👆',
        "fresh_results_no_success": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Failed to fresh any cookies.',
        "fresh_file_error": '<tg-emoji emoji-id="5350539819200039889">⚠️</tg-emoji> Failed to send file (Telegram limit or network error)',

        # Результаты дубликатора
        "duplicate_results_success": '<tg-emoji emoji-id="6019175208240289774">✅</tg-emoji> <b>Duplication completed!</b>\n\nSuccessfully: <code>{success:,}</code> cookies\n❌ Failed: <code>{failed:,}</code>\n\n📄 File with new (duplicated) cookies above 👆',
        "duplicate_results_no_success": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Failed to duplicate any cookies.',

        # Результаты чекера
        "checker_results_title": '<tg-emoji emoji-id="5258278668936945760">🔫</tg-emoji> <b>CHECK RESULTS</b>',
        "checker_results_valid": '<tg-emoji emoji-id="6019175208240289774">✅</tg-emoji> Valid <code>{valid:,}</code>',
        "checker_results_invalid": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Invalid <code>{invalid:,}</code>\n\n',
        "checker_results_price": '<tg-emoji emoji-id="5258204546391351475">💰</tg-emoji> <b>Batch value:</b> <code>~{price:,} USDT</code>\n\n',

        # Финансовая статистика
        # Financial Statistics
"finance_title": '\n<tg-emoji emoji-id="5258204546391351475">💰</tg-emoji> <b>FINANCIAL STATISTICS</b>',
"finance_balance": '\nBalance: <code>{sum:,}</code> R$ (<code>{count}</code> acc, AVG: <code>{avg:.1f}</code>)',
"finance_donate_year": '\nDonate (year): <code>{sum:,}</code> R$ (<code>{count}</code> acc, AVG: <code>{avg:.1f}</code>)',
"finance_donate_lifetime": '\nTotal donate: <code>{sum:,}</code> R$ (<code>{count:,}</code> acc, AVG: <code>{avg:.1f}</code>)',
"finance_pending": '\nPending: <code>{sum:,}</code> R$',
"finance_rap": '\nRAP: <code>{sum:,}</code> R$',
"finance_billing": '\nBilling: <code>{sum:,}</code> R$',

# Account Statistics
"accounts_title": '\n\n<tg-emoji emoji-id="5257969839313526622">📂</tg-emoji> <b>ACCOUNT STATISTICS</b>',
"accounts_cards": '\nCards: <code>{count:,}</code>',
"accounts_premium": '\nPremium: <code>{count:,}</code>',
"accounts_no_email": '\nNo email: <code>{count:,}</code>',
"accounts_korblox": '\nKorblox: <code>{count:,}</code>',
"accounts_headless": '\nHeadless: <code>{count:,}</code>',
"accounts_badges": '\nBadges: <code>{sum:,}</code>',
"accounts_gamepasses": '\nGamepasses: <code>{sum:,}</code>',
"accounts_groups": '\nGroups balance: <code>{sum:,}</code> R$',
"accounts_visits": '\nVisits: <code>{sum:,}</code>',
"accounts_passable": '\nPassable: <code>{passable:,}</code>\nUnpassable: <code>{unpassable:,}</code>',
"accounts_rare_items": '\nRare Items: <code>{count:,}</code>',

# In-Game Donations
"ingame_results": '\n\n<tg-emoji emoji-id="5258508428212445001">🎮</tg-emoji> <b>IN-GAME DONATIONS:</b>\n',
"playtime_results": '\n\n<tg-emoji emoji-id="5199457120428249992">🕘</tg-emoji> <b>PLAYTIME MINUTES:</b>\n',

        # Кнопки
        "btn_web_report": "📊 Web report",
        "btn_back": "Back",
        "btn_cancel": "❌ Cancel",

        # Команды
        "command_cancelled": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> Action cancelled. <blockquote>Return to menu</blockquote>',
        "no_access": '<tg-emoji emoji-id="5260342697075416641">❌</tg-emoji> No access',

        # Админские команды
        "keys_usage": '<tg-emoji emoji-id="5366077477573643872">❌</tg-emoji> Format: /keys <plan> <count>\nAvailable plans: {plans}\nExample: /keys month 10',
        "keys_count_error": '<tg-emoji emoji-id="5364072548185165702">❌</tg-emoji> Number of keys must be from 1 to 100',
        "keys_plan_error": '<tg-emoji emoji-id="5363872067701722306">❌</tg-emoji> Invalid plan. Available: {plans}',
        "keys_created": '<tg-emoji emoji-id="5366341798450973386">✅</tg-emoji> Created <b>{count}</b> keys for plan <b>{plan}</b>:\n\n<code>{keys}</code>',
        "keys_error": '<tg-emoji emoji-id="5364089324327423737">❌</tg-emoji> Error creating keys',

        "check_usage": '<tg-emoji emoji-id="5364349719604646468">❌</tg-emoji> Format: /check <user_id or username>',
        "user_not_found": '<tg-emoji emoji-id="5350374243915813874">❌</tg-emoji> User not found by username',

        "addsub_usage": '<tg-emoji emoji-id="5348373068328751172">❌</tg-emoji> Format: /addsub <user_id> <days>',
        "addsub_success": '<tg-emoji emoji-id="5366493793048611678">✅</tg-emoji> Subscription added for {user_id} for {days} days',
        "addsub_notify": '<tg-emoji emoji-id="5348120597266190780">✅</tg-emoji> Administrator added a subscription for {days} days!',

        "post_no_text": '<tg-emoji emoji-id="5348432867158412360">❌</tg-emoji> Specify message',
        "post_sent": '<tg-emoji emoji-id="5364081859674262626">✅</tg-emoji> Broadcast sent ({sent}/{total} recipients)',

        # Админ панель
        "admin_panel": '<tg-emoji emoji-id="5350685607569934181">📊</tg-emoji> <b>ADMIN PANEL</b>\n\n<tg-emoji emoji-id="5348222877617375207">👥</tg-emoji> Total users: <code>{users:,}</code>\n<tg-emoji emoji-id="5348532407320463735">✅</tg-emoji> Active subscriptions: <code>{active:,}</code>\n<tg-emoji emoji-id="5348127009652361348">💰</tg-emoji> Total referral earnings: <code>{ref_sum:,}</code> RUB',
        "btn_restart": "🔄 Restart bot",
        "btn_edit_files": "📂 Edit files",
        "btn_download_files": "📥 Download files",
        "btn_confirm_restart": "⚠️ Confirm restart",
        "restart_cancelled": '<tg-emoji emoji-id="5348142956865932724">❌</tg-emoji> Restart cancelled',
        "restarting": '<tg-emoji emoji-id="5350322072948066951">🔄</tg-emoji> Restarting bot...',

        # Файлы
        "files_menu": '<tg-emoji emoji-id="5778407832776871799">📂</tg-emoji> <b>Files in current directory</b>\n\n📊 <b>Statistics:</b>\n• Files: <code>{count}</code>\n• Total size: <code>{size}</code>\n• Folders not shown\n\n<i>Select file to download:</i>',
        "no_files": '<tg-emoji emoji-id="5348341989945395276">📂</tg-emoji> <b>No files to download</b>\n\nNo files found in current directory.\nFolders not shown - only files.',
        "file_not_found": '<tg-emoji emoji-id="5348527330669119684">❌</tg-emoji> File not found or was deleted',
        "file_too_large": '<tg-emoji emoji-id="5348125703982303915">⚠️</tg-emoji> <b>File too large</b>\n\n📄 File: <code>{name}</code>\n📏 Size: {size:.1f} MB\n⏰ Modified: {time}\n\n❌ Telegram does not allow sending files larger than 50MB.\nMaximum size: 48 MB (with margin).',
        "file_sent": '<tg-emoji emoji-id="5348241083983745758">📄</tg-emoji> <b>File sent</b>\n\nName: <code>{name}</code>\n📏 Size: {size}\n⏰ Modified: {time}\n👤 Sender: <code>{user_id}</code>',
        "file_send_error": '<tg-emoji emoji-id="5348319041935132191">❌</tg-emoji> <b>File send error</b>\n\nFile: <code>{name}</code>\nError: {error}',
        "btn_refresh": "🔄 Refresh list",

        # Дополнительные ключи из начала ru (которые могли быть пропущены)
        'badges_title': '🎖️ <b>Badge selection</b>\nSelect games to check badges:',
        'gamepasses_title': '🎟️ <b>Gamepass selection</b>\nSelect games to check gamepasses:',
        'custom_badges_prompt': '📥 <b>Enter list of badge IDs</b>\nSeparated by commas or new lines:',
        'custom_gamepasses_prompt': '📥 <b>Enter list of gamepass IDs</b>\nSeparated by commas or new lines:',
        'config_name_prompt_badges': '🆕 <b>Enter config name for badges</b>:',
        'config_name_prompt_gamepasses': '🆕 <b>Enter config name for gamepasses</b>:',
        'config_created': '✅ Config "{name}" created',
        'custom_saved': '✅ Custom badges saved as "{name}", enable them to use',
        'custom_gamepasses_saved': '✅ Custom gamepasses saved as "{name}"',
        'game_changed_success': '✅ Game <b>{game_short}</b> changed to <b>{game_name}</b>',
        'invalid_game_url': '❌ Invalid link. Make sure it\'s a Roblox game link.',
        'game_not_found': '❌ Game not found or Roblox API error.',
        'send_game_url': '📤 Send new Roblox game link for <b>{game_name}</b>\n\nExample: https://www.roblox.com/games/126884695634066/Grow-a-Garden',
        'btn_change': '✏️ Change {name}',
        'btn_reset': '🔄 Reset {name}',
        'no_valid_ids': '❌ No valid IDs',
    }

# Функция для получения текста на нужном языке
def get_text(lang: str, key: str, **kwargs) -> str:
    """Возвращает текст на указанном языке с подстановкой параметров"""
    lang_dict = getattr(Languages, lang, Languages.ru)
    text = lang_dict.get(key, key)
    
    # Подстановка параметров
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            logging.error(f"Missing format key {e} in text '{key}' for language {lang}")
        except Exception as e:
            logging.error(f"Error formatting text '{key}': {e}")
    
    return text