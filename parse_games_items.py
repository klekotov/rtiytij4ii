import asyncio
import os
import sys
from typing import Optional

# Позволяет запускать скрипт автономно с ПК/сервера даже без настроенного BOT_TOKEN
os.environ.setdefault("BOT_TOKEN", "100000000:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")

from cookie_processor import CookieProcessor  # noqa: E402


async def get_paid_gamepasses_async(game_ids_csv: str, user_id: Optional[int] = None) -> str:
    """
    Принимает строку ID игр через запятую (place_id или universe_id).
    Возвращает строку ID ТОЛЬКО ПЛАТНЫХ геймпассов через запятую.
    Если по игре найдены ID из игры, которая уже проверяется в геймпассах — пропускает её.
    """
    processor = CookieProcessor()
    return await processor.get_paid_gamepasses_by_game_ids(game_ids_csv, user_id=user_id)


async def get_all_badges_async(game_ids_csv: str, user_id: Optional[int] = None) -> str:
    """
    Принимает строку ID игр через запятую (place_id или universe_id).
    Возвращает строку ID АБСОЛЮТНО ВСЕХ бейджей этих игр через запятую.
    Если по игре найдены ID из игры, которая уже проверяется в бейджах — пропускает её.
    """
    processor = CookieProcessor()
    return await processor.get_all_badges_by_game_ids(game_ids_csv, user_id=user_id)


def get_paid_gamepasses(game_ids_csv: str, user_id: Optional[int] = None) -> str:
    """Синхронная функция: принимает ID игр через запятую -> возвращает платные GamePass ID через запятую."""
    return asyncio.run(get_paid_gamepasses_async(game_ids_csv, user_id=user_id))


def get_all_badges(game_ids_csv: str, user_id: Optional[int] = None) -> str:
    """Синхронная функция: принимает ID игр через запятую -> возвращает все Badge ID через запятую."""
    return asyncio.run(get_all_badges_async(game_ids_csv, user_id=user_id))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raw_games = " ".join(sys.argv[1:])
    else:
        raw_games = input("Введите ID игр через запятую: ").strip()

    async def _cli_main():
        proc = CookieProcessor()
        gp_res = await proc.fetch_paid_gamepasses_for_games(raw_games)
        b_res = await proc.fetch_all_badges_for_games(raw_games)

        print(f"\n=== PAID GAMEPASSES ({len(gp_res['ids'])} шт., пропущено игр: {len(gp_res['skipped_games'])}) ===")
        print(gp_res["csv"])
        print(f"\n=== ALL BADGES ({len(b_res['ids'])} шт., пропущено игр: {len(b_res['skipped_games'])}) ===")
        print(b_res["csv"])

        with open("parsed_paid_gamepasses.txt", "w", encoding="utf-8") as f:
            f.write(gp_res["csv"])
        with open("parsed_all_badges.txt", "w", encoding="utf-8") as f:
            f.write(b_res["csv"])
        print("\nСохранено также в parsed_paid_gamepasses.txt и parsed_all_badges.txt")

    asyncio.run(_cli_main())
