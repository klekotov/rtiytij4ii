import os
import tempfile

TELEGRAM_TOKEN = "8926815398:AAGBD0BBKSoB7QK2B0c0NPOphEDL8Z6p2Y4" # Замените на ваш токен
ADMIN_IDS = [8282736339]
CRYPTO_PAY_TOKEN = "654951:AANCAVHx7XH7ryn0V8jz6nTUakXmZZhJYrn"  # Замените на токен Crypto Pay
REF_PERCENT = 0.15
BOT_USERNAME = "ertui4ewtjrierjit_bot"
# Константы из оригинального скрипта
COOKIE_PATTERN = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_"

CHANNEL_ID = "-1003536600807"
CHANNEL_URL = "https://t.me/ertyu34o8itr"
HEADLESS_ID = 131592085
KORBLOX_ID = 139610147
REQUEST_TIMEOUT = 10

# ─────────── Тюнинг скорости проверки (крути под количество прокси) ───────────
VALIDATE_SEMAPHORE = 96         # макс одновременных валидаций в пачке
STATS_SEMAPHORE = 72            # макс одновременного сбора статы
FRESH_SEMAPHORE = 56            # макс одновременных фреш/дубликат операций
# Здоровье и нагрузка прокси:
PER_PROXY_LIMIT = 3             # макс одновременных запросов на ОДИН прокси-IP (меньше = меньше 429)
PROXY_MAX_FAILS = 7             # столько фейлов подряд → прокси временно отключается
PROXY_COOLDOWN_SEC = 25         # на сколько секунд отключается проблемный прокси

# ─────────── Оценка стоимости аккаунта (всё в USDT) ───────────
PRICE_PER_1K_ROBUX = 3.8         # за 1000 R$ баланса
PRICE_GROUP_DISCOUNT = 0.8       # баланс групп = цена баланса −20%
PRICE_PER_1K_RAP = 2.2           # за 1000 RAP
PRICE_RAP_MIN = 10000            # RAP ниже этого порога не оцениваем (0)
PRICE_KORBLOX = 20               # Korblox обычная цена
PRICE_KORBLOX_DISCOUNT = 10      # Korblox если биллинг + активный акк
PRICE_HEADLESS = 55              # Headless обычная цена
PRICE_HEADLESS_DISCOUNT = 40     # Headless если биллинг + активный акк
PRICE_COMBO = 90                 # Korblox + Headless вместе
PRICE_COMBO_DISCOUNT = 60        # комбо если биллинг + активный акк
PRICE_PREMIUM = 1.5              # + если есть Premium И есть RAP
PRICE_ACTIVE_MIN_MINUTES = 60    # суммарный плейтайм выше = «активный» (включает скидку)

TARGET_ITEMS = [
    131592085,  # Headless Horseman
    139610147,  # Korblox Deathspeaker
]
ROBLOX_ENDPOINTS = "sd"
MAX_CONCURRENT_REQUESTS = 64
GAMES_FOR_TRANSACTIONS = "d"
RARE_ITEMS = "h"
PROXIES_FILE = "proxies.txt"
STATS_PUBLIC_URL = "11"
PLAYTIME_RANGES = 1
# Emojis for game names (optional: can be toggled in settings)
EMOJI_GAMES = {
    'SAB': '🧠',       # Steal a Brainrot
    'GAG': '🐱‍👤',       # Grow a Garden
    'AdoptMe': '🐶',   # Adopt Me
    'BladeBall': '⚔️', # Blade Ball
    'PS99': '💎',      # PS99
    'MM2': '🔪',       # MM2
    'BSS': '🐝',       # BSS (Bee Swarm Simulator?)
    'Jailbreak': '🚔', # Jailbreak
    'BloxFruits': '🍎', # Blox Fruits
}
# 102 ID игр для InGame Donate / Playtime (2753915549 = BloxFruits и 142823291 = MM2 уже есть среди базовых выше)
CUSTOM_GAME_IDS = [
    2753915549, 4872321990, 537413528, 4520749081, 2788229376, 6284583030, 3804232548, 2358128856,
    1561949052, 7354037751, 1075048329, 7221329622, 4897827543, 1375738876, 1327559369, 1840998922,
    7711666911, 6367261314, 5914078542, 7382788524, 4362561475, 7926219401, 3288314109, 6517241571,
    7016395565, 8134656919, 4708689346, 6440995451, 6564935095, 5796783987, 4909137463, 8456009476,
    3060089934, 4130789796, 1434243388, 6365471049, 8275374033, 4731615904, 8910472142, 8575091559,
    8649834246, 7675962506, 4858265199, 7838244318, 6589531622, 8304191832, 5774334848, 7469118499,
    7516057191, 3382441567, 9535395449, 5408605962, 4401285174, 7715458935, 8279745627, 6824511104,
    9099406543, 7969614886, 5246073395, 4546641663, 4437954297, 2336934726, 4769344152, 217525785,
    9257144131, 4558600844, 8443673955, 2152912822, 6961384969, 4787364275, 2546019376, 3284106108,
    2429948100, 4730816383, 8164126786, 4476362187, 4529305851, 4895131698, 8436561802, 3248144112,
    3776002382, 5193982650, 2147454610, 7862387210, 6517042954, 2715912650, 1570660386, 1130875492,
    3558780272, 1797824685, 2564026587, 4084895316, 5685346437, 7032934679, 4876583403, 2063348596,
    2262643476, 3284508990, 142823291, 2145768081, 4519700982, 277751495,
]

_KNOWN_PLACE_TITLES = {
    4872321990: "Islands",
    537413528: "Build A Boat For Treasure",
    4520749081: "King Legacy",
    2788229376: "Da Hood",
    6284583030: "Pet Simulator X",
}

EXTRA_EMPTY_CUSTOM_SLOTS = 30  # дополнительные пустые слоты под ручное добавление через ✏️

GAMES = {
    "SAB": {"name": "Steal a Brainrot", "place_id": 109983668079237, "universe_id": 7709344486},
    "GAG": {"name": "Grow a Garden", "place_id": 126884695634066, "universe_id": 7436755782},
    "AdoptMe": {"name": "Adopt Me", "place_id": 920587237, "universe_id": 383310974},
    "BladeBall": {"name": "Blade Ball", "place_id": 13772394625, "universe_id": 4777817887},
    "PS99": {"name": "PS99", "place_id": 8737899170, "universe_id": 3317771874},
    "MM2": {"name": "MM2", "place_id": 142823291, "universe_id": 66654135},
    "BSS": {"name": "BSS", "place_id": 1537690962, "universe_id": 601130232},
    "Jailbreak": {"name": "Jailbreak", "place_id": 606849621, "universe_id": 245662005},
    "BloxFruits": {"name": "Blox Fruits", "place_id": 2753915549, "universe_id": 994732206},
}

_BUILTIN_PLACE_IDS = {v["place_id"] for v in GAMES.values() if v.get("place_id")}
_custom_idx = 0
for _gid in CUSTOM_GAME_IDS:
    if _gid in _BUILTIN_PLACE_IDS:
        continue
    _custom_idx += 1
    _slot_key = f"CUSTOM{_custom_idx}"
    GAMES[_slot_key] = {
        "name": _KNOWN_PLACE_TITLES.get(_gid, f"Game {_gid}"),
        "place_id": _gid,
        "universe_id": None,  # автоматически подтягивается через Roblox API и кэшируется в БД
        "raw_id": _gid,
    }

for _empty_i in range(1, EXTRA_EMPTY_CUSTOM_SLOTS + 1):
    _custom_idx += 1
    GAMES[f"CUSTOM{_custom_idx}"] = {
        "name": f"Empty #{_empty_i}",
        "place_id": None,
        "universe_id": None,
    }
UNIVERSE_IDS = {
    "SAB": 7709344486,
    "GAG": 7436755782,
    "AdoptMe": 383310974,
    "BladeBall": 4777817887,
    "PS99": 3317771874, 
    "MM2": 66654135,
    "BSS": 601130232,
    "Jailbreak": 245662005,
    "BloxFruits": 994732206,
}
BADGES_PER_GAME = {
    "Pet Simulator 99": [2153913164, 3317771874, 3189151177666639, 3317771874, 754796678735151, 3317771874, 327631483993374, 3317771874],
    "MM2 70+": [196200625, 196200691, 196200785],
    "MM2 40+": [96199518, 196200089, 196200207],
    "MM2 10+": [196198137, 196198654, 196198776],
    "Jailbreak": [958186367, 245662005, 958186842, 245662005, 958186941, 245662005, 958187053, 245662005, 958187226, 245662005, 958187343, 245662005, 958187470, 245662005, 2129891386, 245662005],
    "Grow a Garden": [3181581226889239, 2432009301742310, 3495711621999816, 3310355054544865, 3195330021311033, 34852060037844, 3602894446235962, 4330691652818014, 2213702621912050, 397821235877805, 3966694991137927, 674039989298417, 3833249137800902, 3046817076424642, 1013473936180275, 4429839651101981, 393879997365151, 2585648043281722],
    "Blox Fruits 3 SEA": [2125253113],
    "Blox Fruits 2 SEA": [2125253106],
    "Bee Swarm": [1749468648,601130232,1749519033,601130232,1749523673,601130232,1749534539,601130232,1749564142,601130232,1749566481,601130232,1749568562,601130232,1749570424,601130232,1749604083,601130232,1749606287,601130232,1749608577,601130232,1749610498,601130232,1749628495,601130232,1749630489,601130232,1749631489,601130232,1749632737,601130232,1749673718,601130232,1749675237,601130232,1749676247,601130232,1749677419,601130232,1749679114,601130232,1749680097,601130232,1749680902,601130232,1749681692,601130232,1749684261,601130232,1749685928,601130232,1749686750,601130232,1749688211,601130232,1749770193,601130232,1749771674,601130232,1749772538,601130232,1749773617,601130232,1749775523,601130232,1749776451,601130232,1749777194,601130232,1749779193,601130232,1749780645,601130232,1749781861,601130232,1749782542,601130232,1749783500,601130232,1749784769,601130232,1749786138,601130232,1749787209,601130232,1749788323,601130232,1749833884,601130232,1749835166,601130232,1749835972,601130232,1749836699,601130232,1749838495,601130232],
    "Adopt Me": [2124439922,383310974,2124439923,383310974,2124439924,383310974,2124439925,383310974,2124439926,383310974,2124439927,383310974,2124439928,383310974,2129488028,383310974,2129488030,383310974,135520552767917,383310974,1048893619880427,383310974,763171671267524,383310974,925260774262149,383310974,89650026776535,383310974,292596439745713,383310974,1683279614525471,383310974,1065569517641022,383310974,3865916040798951,383310974,160677344563654,383310974,211728180632535,383310974,639601989428398,383310974,2388128713374485,383310974]
}
GAMEPASSES_PER_GAME = {
    "Steal a Brainrot": [1228591447,1229510262,1227013099],
    "Pet Simulator 99": [205379487,257803774,257811346,258567677,259437976,264808140,265320491,265324265,651611000,655859720,690997523,720275150,975558264,1099764410],
    "MM2": [429957,1308795,79419,79442,429356,1201672,1491260,1531578,1712843,2002511,3346253,3646351,5299081,5593012,7435036,7795820,8456434,10747452,12448341,13308756,13502690,15066851,16462794,21348436,24102758,26304638,26304640,26304644,55292828,55292879,55292987,93780280,93780323,93780371,112956652,131048794,131048887,131048950,156618021,156618061,156618096,200073999,200074115,200074174,273009597,273009641,273009675,658376309,658667213,674830453],
    "Jailbreak": [2070427,2218187,2219040,2296901,2725211,4974038,56149618,2068240,6631507],
    "Blox Fruits": [6028662,6028786,6240746,6525589,6738811,7578721],
    "Blade Ball": [223367086,226785981,229765926,895596060,1203969437],
    "Bee Swarm": [4231119,4231126,4257788,4492467],
    "Adopt Me": [3196348,5300198,6040696,6408694,6965379,7124470,189425850,951441773,951395729,951065968,3745845,4785795,4796463,5246776,5704158,5785139,5885873,5904007,6164327,6558811,6558813,6858591]
}
_RAP_RANGES = [(1_000_000, "1M+"), (500_000, "500k+"), (250_000, "250k+"),
              (100_000, "100k+"), (50_000, "50k+"), (25_000, "25k+"),
              (10_000, "10k+"), (5_000, "5k+"), (1_000, "1k+")]
_DONATE_RANGES = [(50_000, "50k+"), (25_000, "25k+"), (10_000, "10k+"),
                 (5_000, "5k+"), (2_500, "2.5k+"), (1_000, "1k+"),
                 (500, "500+"), (100, "100+")]
_LIFETIME_RANGES = [
    (1_000_000, "1M+"),
    (500_000, "500k+"),
    (250_000, "250k+"),
    (100_000, "100k+"),
    (50_000, "50k+"),
    (25_000, "25k+"),
    (10_000, "10k+"),
    (5_000, "5k+"),
    (2_500, "2.5k+"),
    (1_000, "1k+"),
    (500, "500+"),
    (250, "250+"),
    (100, "100+")
]
_BALANCE_RANGES = [(10_000, "10k+"), (5_000, "5k+"), (2_500, "2.5k+"),
                  (1_000, "1k+"), (500, "500+"), (100, "100+"),
                  (50, "50+"), (10, "10+"), (1, "1+")]
_BADGES_RANGES = [(100, "100+"), (50, "50+"), (25, "25+"), (10, "10+"), (5, "5+"), (1, "1+")]
_GAMEPASSES_RANGES = [(100, "100+"), (50, "50+"), (25, "25+"), (10, "10+"), (5, "5+"), (1, "1+")]
_BILLING_RANGES = [(100, "100+"), (50, "50+"), (25, "25+"), (10, "10+"), (5, "5+"), (1, "1+")]
_PLAYTIME_RANGES = [
    (1000, "1000+"),
    (500, "500+"),
    (250, "250+"),
    (100, "100+"),
    (50, "50+"),
    (25, "25+"),
    (10, "10+"),
    (5, "5+"),
    (1, "1+")
]
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>228 Checker — Statistics</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --accent: #7c5cff;
            --accent-2: #9d7bff;
            --bg: #0d0d12;
            --surface: #16161e;
            --surface-2: #1c1c26;
            --border: #2a2a38;
            --text: #e8e8f0;
            --text-dim: #9a9ab0;
            --good: #34d399;
            --radius: 16px;
            --shadow: 0 10px 40px rgba(0,0,0,.4);
            --glow: 0 0 0 1px color-mix(in srgb, var(--accent) 25%, transparent);
        }
        body.light {
            --bg: #f3f4fb;
            --surface: #ffffff;
            --surface-2: #f4f5fb;
            --border: #e4e6f0;
            --text: #1b1b28;
            --text-dim: #6c6c82;
            --shadow: 0 10px 40px rgba(25,25,60,.08);
        }
        body[data-accent="blue"]   { --accent:#3b82f6; --accent-2:#60a5fa; }
        body[data-accent="green"]  { --accent:#22c55e; --accent-2:#4ade80; }
        body[data-accent="red"]    { --accent:#f04444; --accent-2:#f87171; }
        body[data-accent="pink"]   { --accent:#ec4899; --accent-2:#f472b6; }
        body[data-accent="orange"] { --accent:#f59e0b; --accent-2:#fbbf24; }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        html { scroll-behavior: smooth; }

        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
            transition: background .3s ease, color .3s ease;
        }
        body::before {
            content: "";
            position: fixed;
            inset: 0;
            background:
                radial-gradient(1200px 600px at 15% -10%, color-mix(in srgb, var(--accent) 18%, transparent), transparent 60%),
                radial-gradient(900px 500px at 100% 0%, color-mix(in srgb, var(--accent-2) 12%, transparent), transparent 55%);
            pointer-events: none;
            z-index: 0;
        }

        .container {
            position: relative;
            z-index: 1;
            max-width: 1180px;
            margin: 0 auto;
            padding: 40px 24px 60px;
        }

        /* ===== Header ===== */
        header {
            text-align: center;
            margin-bottom: 38px;
        }
        header h1 {
            font-size: clamp(2rem, 5vw, 3rem);
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(120deg, var(--accent), var(--accent-2));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        header p {
            color: var(--text-dim);
            font-size: 0.95rem;
            margin-top: 6px;
        }

        /* ===== Summary cards ===== */
        .stats-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }
        .stat-card {
            position: relative;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 22px 24px;
            overflow: hidden;
            transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;
        }
        .stat-card::before {
            content: "";
            position: absolute;
            left: 0; top: 0; bottom: 0;
            width: 4px;
            background: linear-gradient(var(--accent), var(--accent-2));
        }
        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow);
            border-color: color-mix(in srgb, var(--accent) 45%, var(--border));
        }
        .stat-card h3 {
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--text-dim);
            margin-bottom: 10px;
        }
        .stat-card p {
            font-size: 1.85rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            display: flex;
            align-items: baseline;
            gap: 8px;
            flex-wrap: wrap;
        }

        .highlight {
            color: var(--accent);
            font-weight: 600;
        }
        .stat-card .highlight { font-size: 1rem; }

        /* ===== Tables ===== */
        .table-container {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 4px;
            margin-bottom: 26px;
            box-shadow: 0 4px 24px rgba(0,0,0,.08);
            overflow: hidden;
        }
        .table-container h2 {
            font-size: 1.05rem;
            font-weight: 700;
            padding: 18px 20px 14px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .table-container h2::before {
            content: "";
            width: 8px; height: 8px;
            border-radius: 50%;
            background: var(--accent);
            box-shadow: 0 0 12px var(--accent);
        }
        .table-scroll {
            overflow-x: auto;
            border-radius: 12px;
        }
        .gradient-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
            white-space: nowrap;
        }
        .gradient-table thead th {
            position: sticky;
            top: 0;
            background: var(--surface-2);
            color: var(--text-dim);
            font-weight: 600;
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            text-align: center;
            padding: 13px 14px;
            border-bottom: 1px solid var(--border);
        }
        .gradient-table tbody td {
            text-align: center;
            padding: 12px 14px;
            border-bottom: 1px solid color-mix(in srgb, var(--border) 55%, transparent);
            color: var(--text);
        }
        .gradient-table tbody tr:last-child td { border-bottom: none; }
        .gradient-table tbody tr {
            transition: background .15s ease;
        }
        .gradient-table tbody tr:nth-child(even) td {
            background: color-mix(in srgb, var(--surface-2) 45%, transparent);
        }
        .gradient-table tbody tr:hover td {
            background: color-mix(in srgb, var(--accent) 12%, transparent);
        }
        .gradient-table td.highlight {
            color: var(--accent);
            font-weight: 600;
        }

        /* ===== Footer ===== */
        footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 24px;
            border-top: 1px solid var(--border);
            color: var(--text-dim);
            font-size: 0.85rem;
        }

        /* ===== Floating controls ===== */
        .controls {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 50;
            display: flex;
            gap: 10px;
        }
        .ctrl-btn {
            width: 44px; height: 44px;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--surface);
            color: var(--text);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            transition: all .2s ease;
            box-shadow: 0 4px 16px rgba(0,0,0,.15);
        }
        .ctrl-btn:hover {
            border-color: var(--accent);
            color: var(--accent);
            transform: translateY(-2px);
        }
        .palette {
            position: absolute;
            top: 54px;
            right: 0;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 12px;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            box-shadow: var(--shadow);
            opacity: 0;
            visibility: hidden;
            transform: translateY(-8px);
            transition: all .2s ease;
        }
        .palette.show {
            opacity: 1;
            visibility: visible;
            transform: translateY(0);
        }
        .swatch {
            width: 30px; height: 30px;
            border-radius: 50%;
            cursor: pointer;
            border: 2px solid transparent;
            transition: transform .15s ease, border-color .15s ease;
        }
        .swatch:hover { transform: scale(1.15); }
        .swatch.active { border-color: var(--text); }

        @media (max-width: 768px) {
            .container { padding: 28px 14px 50px; }
            .stats-summary { grid-template-columns: 1fr 1fr; gap: 12px; }
            .stat-card { padding: 16px; }
            .stat-card p { font-size: 1.4rem; }
            .gradient-table { font-size: 0.82rem; }
            .gradient-table thead th { padding: 10px 10px; }
            .gradient-table tbody td { padding: 10px 10px; }
        }
        @media (max-width: 600px) {
            .controls { top: 12px; right: 12px; gap: 8px; }
            .ctrl-btn { width: 40px; height: 40px; font-size: 0.95rem; }
            header { margin-bottom: 26px; }
            .container { padding: 24px 12px 44px; }

            /* Широкие таблицы превращаем в карточки "подпись → значение" */
            .table-container { padding: 0; }
            .table-container h2 { padding: 16px 16px 8px; font-size: 1rem; }
            .table-scroll { overflow: visible; }
            .gradient-table { white-space: normal; font-size: 0.88rem; }
            .gradient-table thead { display: none; }
            .gradient-table tbody,
            .gradient-table tr,
            .gradient-table td { display: block; width: 100%; }
            .gradient-table tbody tr {
                border: 1px solid var(--border);
                border-radius: 12px;
                margin: 10px;
                overflow: hidden;
                background: color-mix(in srgb, var(--surface-2) 35%, transparent);
            }
            .gradient-table tbody tr:nth-child(even) td { background: transparent; }
            .gradient-table tbody tr:hover td { background: transparent; }
            .gradient-table tbody td {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 16px;
                text-align: right;
                padding: 11px 14px;
                border-bottom: 1px solid color-mix(in srgb, var(--border) 50%, transparent);
            }
            .gradient-table tbody td:last-child { border-bottom: none; }
            .gradient-table tbody td::before {
                content: attr(data-label);
                text-align: left;
                color: var(--text-dim);
                font-size: 0.7rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                flex: 0 0 auto;
            }
        }
        @media (max-width: 460px) {
            .stats-summary { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body data-accent="purple">
    <div class="controls">
        <button class="ctrl-btn" id="modeToggle" title="Тема"><i class="fas fa-moon"></i></button>
        <div style="position: relative;">
            <button class="ctrl-btn" id="paletteToggle" title="Цвет"><i class="fas fa-palette"></i></button>
            <div class="palette" id="palette">
                <div class="swatch" data-accent="purple" style="background:#7c5cff"></div>
                <div class="swatch" data-accent="blue"   style="background:#3b82f6"></div>
                <div class="swatch" data-accent="green"  style="background:#22c55e"></div>
                <div class="swatch" data-accent="red"    style="background:#f04444"></div>
                <div class="swatch" data-accent="pink"   style="background:#ec4899"></div>
                <div class="swatch" data-accent="orange" style="background:#f59e0b"></div>
            </div>
        </div>
    </div>

    <div class="container">
        <header>
            <h1>Statistics</h1>
            <p>228 Checker</p>
        </header>

        <div class="stats-summary">
            <div class="stat-card">
                <h3>Valid cookie</h3>
                <p>{valid}</p>
            </div>
            <div class="stat-card">
                <h3>Donate Accounts</h3>
                <p>{donate_accounts}<span class="highlight">({donate_percent}%)</span></p>
            </div>
            <div class="stat-card">
                <h3>Balance Accounts</h3>
                <p>{balance_accounts}<span class="highlight">({balance_percent}%)</span></p>
            </div>
            <div class="stat-card">
                <h3>Total donation</h3>
                <p>{sum_donate_lifetime}</p>
            </div>
        </div>

        {total_values_section}

        <div class="table-container">
            <h2>Top values</h2>
            <div class="table-scroll">
                <table class="gradient-table">
                    <thead><tr>{top_headers}</tr></thead>
                    <tbody>{top_rows}</tbody>
                </table>
            </div>
        </div>

        <div class="table-container">
            <h2>InGame Donate Summary</h2>
            <div class="table-scroll">
                <table class="gradient-table">
                    <thead><tr>{game_headers}</tr></thead>
                    <tbody><tr>{game_totals}</tr></tbody>
                </table>
            </div>
        </div>

        <div class="table-container">
            <h2>Top 10 InGame Donate</h2>
            <div class="table-scroll">
                <table class="gradient-table">
                    <thead><tr>{top_game_headers}</tr></thead>
                    <tbody>{top_game_rows}</tbody>
                </table>
            </div>
        </div>

        <div class="table-container">
            <h2>InGame Playtime Summary</h2>
            <div class="table-scroll">
                <table class="gradient-table">
                    <thead><tr>{playtime_headers}</tr></thead>
                    <tbody><tr>{playtime_totals}</tr></tbody>
                </table>
            </div>
        </div>

        <div class="table-container">
            <h2>Top 10 InGame Playtime</h2>
            <div class="table-scroll">
                <table class="gradient-table">
                    <thead><tr>{top_playtime_headers}</tr></thead>
                    <tbody>{top_playtime_rows}</tbody>
                </table>
            </div>
        </div>

        <footer>
            <p>Statistics by 228 Checker &middot; Data checked: {current_time}</p>
        </footer>
    </div>

    <script>
        (function () {
            const body = document.body;
            const modeToggle = document.getElementById('modeToggle');
            const paletteToggle = document.getElementById('paletteToggle');
            const palette = document.getElementById('palette');

            const savedMode = localStorage.getItem('mode') || 'dark';
            const savedAccent = localStorage.getItem('accent') || 'purple';

            function applyMode(mode) {
                if (mode === 'light') {
                    body.classList.add('light');
                    modeToggle.innerHTML = '<i class="fas fa-sun"></i>';
                } else {
                    body.classList.remove('light');
                    modeToggle.innerHTML = '<i class="fas fa-moon"></i>';
                }
            }
            function applyAccent(accent) {
                body.setAttribute('data-accent', accent);
                document.querySelectorAll('.swatch').forEach(function (s) {
                    s.classList.toggle('active', s.getAttribute('data-accent') === accent);
                });
            }

            applyMode(savedMode);
            applyAccent(savedAccent);

            modeToggle.addEventListener('click', function () {
                const next = body.classList.contains('light') ? 'dark' : 'light';
                localStorage.setItem('mode', next);
                applyMode(next);
            });

            paletteToggle.addEventListener('click', function (e) {
                e.stopPropagation();
                palette.classList.toggle('show');
            });
            document.addEventListener('click', function (e) {
                if (!palette.contains(e.target) && e.target !== paletteToggle) {
                    palette.classList.remove('show');
                }
            });
            document.querySelectorAll('.swatch').forEach(function (s) {
                s.addEventListener('click', function () {
                    const accent = s.getAttribute('data-accent');
                    localStorage.setItem('accent', accent);
                    applyAccent(accent);
                    palette.classList.remove('show');
                });
            });

            // Мобильные карточки: подпись из шапки в каждую ячейку
            document.querySelectorAll('.gradient-table').forEach(function (table) {
                const heads = Array.prototype.map.call(
                    table.querySelectorAll('thead th'),
                    function (th) { return th.textContent.trim(); }
                );
                if (!heads.length) return;
                table.querySelectorAll('tbody tr').forEach(function (tr) {
                    Array.prototype.forEach.call(tr.children, function (td, i) {
                        if (heads[i]) td.setAttribute('data-label', heads[i]);
                    });
                });
            });

            // Прячем пустые таблицы (нет ни одной ячейки с данными)
            document.querySelectorAll('.table-container').forEach(function (tc) {
                const cells = tc.querySelectorAll('tbody td');
                let hasData = false;
                cells.forEach(function (c) { if (c.textContent.trim() !== '') hasData = true; });
                if (cells.length === 0 || !hasData) tc.style.display = 'none';
            });
        })();
    </script>
</body>
</html>"""
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
# Хост для ссылок на отчёты. None = автоопределение. Можно указать IP, домен или полный URL.
# Примеры:
#   STATS_HOST = None                      # авто-определит публичный IP (подходит не для bothost.ru)
#   STATS_HOST = "147.45.230.226"          # старый вариант — прямой IP:8001 (требует открытый порт/проброс)
#   STATS_HOST = "mybot.bothost.tech"      # ✅ для bothost.ru — вкл. Веб-интерфейс в панели, укажи выданный домен
#   STATS_HOST = "mydomain.com"            # свой домен (A-запись → IP хоста, порт 8001 должен быть открыт)
#   STATS_HOST = "https://mydomain.com"    # если стоит Nginx/Cloudflare с HTTPS без порта
STATS_HOST = "bot-1792475546-1397-s4234sfdsfsdf.bothost.tech"  # bothost.ru домен для этого бота (выдаёт панель → Веб-интерфейс)
stats_public_url = "http://127.0.0.1:8001"  # перезаписывается в start_stats_server() / из PORT env → https://bot-1792475546-1397...
stats_server_ports = []  # реальные локальные порты, которые слушает сервер отчётов
CHECK_PARAMS = {
    'price': 'Price ($)',
    'balance': 'Balance',
    'pending': 'Pending',
    'badges_by_name': 'Badge names',
    'gamepasses_by_name': 'Pass names',
    'donate_year': 'Donate (year)',
    'donate_lifetime': 'Donate (life)',
    'ingame_donate': 'InGame Donate',
    'playtime': 'Playtime',
    'rap': 'RAP',
    'billing': 'Billing',
    'card': 'Cards',
    'premium': 'Premium',
    'email_verified': 'Email',
    'rares': 'Korblox/Headless',
    'badges': 'Badges',
    'gamepasses': 'Gamepasses',
    'groups_balance': 'Groups balance',
    'places_visits': 'Places visits',
    'country': 'Country',
    'passable': 'Passable',
    'rare_items_check': 'Rare Items',
}
PLANS = {
    '2day': {'days': 2, 'price': 150},
    '7days': {'days': 7, 'price': 450},
    '31days': {'days': 31, 'price': 750},
    '62days': {'days': 62, 'price': 1250},
}
CRYPTO_PAY_API_URL = "https://pay.crypt.bot/api/"
# Курс USDT->RUB, задаётся вручную (показывается в меню покупки). Меняй это число.
MANUAL_USDT_RATE = 71.92
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]
DB_FILE = "bot.db"
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession

# Прокси для обхода блокировки Telegram (локальный v2rayN HTTP-инбаунд на домашнем ПК).
# None или "" = подключаться напрямую (например на VPS, где Telegram не заблокирован).
# ВАЖНО: для работы прокси нужен модуль aiohttp_socks (pip install aiohttp_socks).
TELEGRAM_PROXY = None

def _build_bot():
    if TELEGRAM_PROXY:
        try:
            return Bot(token=TELEGRAM_TOKEN, session=AiohttpSession(proxy=TELEGRAM_PROXY))
        except Exception as e:
            import logging
            logging.warning(
                f"⚠️ Прокси Telegram не подключён ({type(e).__name__}: {e}). "
                f"Если нужен прокси — установи: pip install aiohttp_socks. "
                f"Сейчас подключаюсь к Telegram напрямую."
            )
    return Bot(token=TELEGRAM_TOKEN)

bot = _build_bot()
