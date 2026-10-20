import asyncio
import logging
import time
from typing import List, Optional


class ProxyPool:
    """
    Пул прокси с двумя задачами:
      1) лимит одновременных запросов на КАЖДЫЙ прокси-IP (per_proxy_limit) —
         не даём одному IP получить столько запросов, что Roblox отдаёт 429;
      2) здоровье прокси — если прокси подряд фейлит (таймаут/429/обрыв),
         он временно выводится из ротации на cooldown секунд.

    Использование:
        pool = ProxyPool(proxies, per_proxy_limit=6, max_fails=6, cooldown=90)
        proxy = await pool.acquire()      # взять прокси (или None, если их нет)
        try:
            ... запрос через proxy ...
            pool.release(proxy, success=True)
        except Exception:
            pool.release(proxy, success=False)

    Балансировка: acquire() выдаёт слот любого здорового прокси, у которого
    есть свободная «квота». Если все слоты заняты — ждёт освобождения.
    """

    def __init__(self, proxies: List[str], per_proxy_limit: int = 6,
                 max_fails: int = 6, cooldown: int = 90):
        self.proxies = [p for p in (proxies or []) if p]
        self.enabled = bool(self.proxies)
        self.per = max(1, int(per_proxy_limit))
        self.max_fails = max(1, int(max_fails))
        self.cooldown = max(1, int(cooldown))

        self._q: asyncio.Queue = asyncio.Queue()
        self._fails = {p: 0 for p in self.proxies}
        self._disabled = set()
        # Кладём по per слотов на каждый прокси
        for p in self.proxies:
            for _ in range(self.per):
                self._q.put_nowait(p)

    async def acquire(self) -> Optional[str]:
        """Берёт слот здорового прокси. None — если прокси вообще нет."""
        if not self.enabled:
            return None
        while True:
            # Сначала вычерпываем уже лежащие в очереди слоты, пропуская отключённые
            while not self._q.empty():
                try:
                    p = self._q.get_nowait()
                except asyncio.QueueEmpty:
                    break
                if p in self._disabled:
                    # слот отключённого прокси — выкидываем, вернётся после cooldown
                    continue
                return p

            # Если внезапно отключены вообще все прокси — принудительно возвращаем один в ротацию,
            # чтобы не "залипать" на долгом ожидании cooldown.
            if self._disabled and len(self._disabled) >= len(self.proxies):
                p = next(iter(self._disabled))
                self._disabled.discard(p)
                self._fails[p] = max(0, self.max_fails - 1)
                self._q.put_nowait(p)
                tail = p[-18:] if len(p) > 18 else p
                logging.warning(f"🔁 Анти-залипание пула: прокси ...{tail} возвращён досрочно")
                continue

            # Очередь пуста — ждём освобождения любого слота, но не вечно.
            try:
                p = await asyncio.wait_for(self._q.get(), timeout=3.0)
            except asyncio.TimeoutError:
                continue
            if p in self._disabled:
                continue
            return p

    def release(self, proxy: Optional[str], success: bool):
        """Возвращает слот в пул и обновляет здоровье прокси."""
        if not self.enabled or proxy is None:
            return
        if proxy in self._disabled:
            # слот отключённого прокси в оборот не возвращаем (он дренируется)
            return

        if success:
            self._fails[proxy] = 0
            self._q.put_nowait(proxy)
            return

        # неудача
        self._fails[proxy] = self._fails.get(proxy, 0) + 1
        if self._fails[proxy] >= self.max_fails:
            self._disabled.add(proxy)
            tail = proxy[-18:] if len(proxy) > 18 else proxy
            logging.warning(f"🔌 Прокси ...{tail} отключён на {self.cooldown}с "
                            f"({self._fails[proxy]} фейлов подряд)")
            asyncio.create_task(self._enable_later(proxy))
            # слот не возвращаем — прокси выведен
        else:
            self._q.put_nowait(proxy)

    async def _enable_later(self, proxy: str):
        await asyncio.sleep(self.cooldown)
        self._disabled.discard(proxy)
        self._fails[proxy] = 0
        # возвращаем ровно per слотов прокси обратно в ротацию
        for _ in range(self.per):
            self._q.put_nowait(proxy)
        tail = proxy[-18:] if len(proxy) > 18 else proxy
        logging.info(f"🔌 Прокси ...{tail} снова в ротации")

    def stats(self) -> dict:
        return {
            "total": len(self.proxies),
            "disabled": len(self._disabled),
            "active": len(self.proxies) - len(self._disabled),
        }
