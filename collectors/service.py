import asyncio
from datetime import datetime, timezone

from db.database import SessionLocal
from db.market_repository import save_market_observation
from db.models import MarketSnapshot

from .types import MarketObservation
from .yfinance_collector import YFinanceCollector


class MarketCollectorService:
    def __init__(
        self,
        provider: YFinanceCollector,
        *,
        enabled: bool,
        poll_seconds: int,
    ) -> None:
        self.provider = provider
        self.enabled = enabled
        self.poll_seconds = poll_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._run_lock = asyncio.Lock()

        self.last_started_at: datetime | None = None
        self.last_finished_at: datetime | None = None
        self.last_error: str | None = None
        self.last_symbol_errors: dict[str, str] = {}
        self.last_fetched = 0
        self.last_saved = 0
        self.last_skipped = 0

    async def start(self) -> None:
        if not self.enabled or self._task is not None:
            return

        self._stop_event.clear()
        self._task = asyncio.create_task(self._loop(), name="market-ai-collector")

    async def stop(self) -> None:
        if self._task is None:
            return

        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def run_once(self) -> dict[str, object]:
        async with self._run_lock:
            self.last_started_at = datetime.now(timezone.utc)
            self.last_error = None
            self.last_symbol_errors = {}
            self.last_fetched = 0
            self.last_saved = 0
            self.last_skipped = 0

            try:
                observations, symbol_errors = await asyncio.to_thread(self.provider.fetch)
                self.last_symbol_errors = symbol_errors
                self.last_fetched = len(observations)
                saved, skipped = await asyncio.to_thread(self._persist, observations)
                self.last_saved = saved
                self.last_skipped = skipped
            except Exception as exc:
                self.last_error = str(exc)
            finally:
                self.last_finished_at = datetime.now(timezone.utc)

            return self.status()

    def status(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "running": self._task is not None and not self._task.done(),
            "poll_seconds": self.poll_seconds,
            "provider": self.provider.source_name,
            "configured_symbols": len(self.provider.enabled_mappings),
            "disabled_symbols": [
                {
                    "symbol": item.symbol,
                    "reason": item.note or "provider mapping disabled",
                }
                for item in self.provider.disabled_mappings
            ],
            "last_started_at": self._iso_or_none(self.last_started_at),
            "last_finished_at": self._iso_or_none(self.last_finished_at),
            "last_error": self.last_error,
            "last_symbol_errors": self.last_symbol_errors,
            "last_fetched": self.last_fetched,
            "last_saved": self.last_saved,
            "last_skipped": self.last_skipped,
        }

    async def _loop(self) -> None:
        while not self._stop_event.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.poll_seconds,
                )
            except TimeoutError:
                continue

    @staticmethod
    def _persist(observations: list[MarketObservation]) -> tuple[int, int]:
        saved = 0
        skipped = 0

        with SessionLocal() as session:
            for observation in observations:
                snapshot = session.get(MarketSnapshot, observation.symbol)
                if MarketCollectorService._same_observation(snapshot, observation):
                    skipped += 1
                    continue

                save_market_observation(
                    session,
                    symbol=observation.symbol,
                    price=observation.price,
                    change_pct=observation.change_pct,
                    source=observation.source,
                    observed_at=observation.observed_at,
                )
                saved += 1

        return saved, skipped

    @staticmethod
    def _same_observation(snapshot: MarketSnapshot | None, observation: MarketObservation) -> bool:
        if snapshot is None:
            return False

        snapshot_time = snapshot.observed_at
        if snapshot_time.tzinfo is None:
            snapshot_time = snapshot_time.replace(tzinfo=timezone.utc)
        else:
            snapshot_time = snapshot_time.astimezone(timezone.utc)

        return (
            snapshot_time == observation.observed_at.astimezone(timezone.utc)
            and float(snapshot.price) == float(observation.price)
            and snapshot.change_pct == observation.change_pct
            and snapshot.source == observation.source
        )

    @staticmethod
    def _iso_or_none(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
