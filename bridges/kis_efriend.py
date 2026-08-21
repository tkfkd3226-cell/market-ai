from __future__ import annotations

from datetime import date, datetime, timezone
from threading import Lock
from typing import Literal

from bridges.kospi200_contract import (
    resolve_kospi200_front_month,
    resolve_kospi200_market_session,
)

from pydantic import BaseModel, Field
from sqlalchemy import select

from db.database import SessionLocal
from db.market_repository import save_market_observation
from db.models import MarketPrice


KOSPI200_SYMBOL = "FUTURES:KOSPI200"
KIS_SOURCE_PREFIX = "kis-efriend"


class KisEFriendTick(BaseModel):
    instrument_code: str = Field(min_length=1, max_length=9)
    service: Literal["FC_R", "CMEC_R"]
    session: Literal["day", "night"]
    business_time: str = Field(pattern=r"^\d{6}$")
    price: float = Field(gt=0)
    change_pct: float | None = Field(default=None, ge=-100, le=100)
    cumulative_volume: int | None = Field(default=None, ge=0)
    ask1: float | None = Field(default=None, ge=0)
    bid1: float | None = Field(default=None, ge=0)
    sent_at: datetime | None = None
    tick_count: int | None = Field(default=None, ge=0)


class KisEFriendHeartbeat(BaseModel):
    instrument_code: str = Field(min_length=1, max_length=9)
    service: Literal["FC_R", "CMEC_R"] | None = None
    session: Literal["day", "night", "closed"]
    bridge_time: datetime
    last_tick_at: datetime | None = None
    tick_count: int = Field(default=0, ge=0)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _as_utc(value).isoformat().replace("+00:00", "Z")


class KisEFriendBridgeService:
    """Accepts localhost eFriend Expert ticks and persists verified KOSPI200 futures data.

    The bridge heartbeat is intentionally separate from market-data freshness. A live bridge
    does not make an old quote fresh; only a newly received FC_R / CMEC_R tick updates the
    market snapshot timestamp.
    """

    def __init__(
        self,
        *,
        history_interval_seconds: int = 60,
        heartbeat_stale_seconds: int = 30,
        expected_instrument_code: str = "",
        krx_closed_dates: frozenset[date] | None = None,
        krx_open_dates: frozenset[date] | None = None,
        krx_night_closed_dates: frozenset[date] | None = None,
    ) -> None:
        self.history_interval_seconds = max(1, int(history_interval_seconds))
        self.heartbeat_stale_seconds = max(5, int(heartbeat_stale_seconds))
        self.instrument_code_override = expected_instrument_code.strip().upper()
        self.krx_closed_dates = frozenset(krx_closed_dates or ())
        self.krx_open_dates = frozenset(krx_open_dates or ())
        self.krx_night_closed_dates = frozenset(krx_night_closed_dates or ())
        self._lock = Lock()

        self.total_ticks_received = 0
        self.total_snapshot_updates = 0
        self.total_history_rows = 0
        self.total_heartbeats = 0
        self.last_received_at: datetime | None = None
        self.last_heartbeat_at: datetime | None = None
        self.last_tick_at_reported: datetime | None = None
        self.last_instrument_code: str | None = None
        self.last_service: str | None = None
        self.last_session: str | None = None
        self.last_business_time: str | None = None
        self.last_price: float | None = None
        self.last_change_pct: float | None = None
        self.last_volume: int | None = None
        self.last_ask1: float | None = None
        self.last_bid1: float | None = None
        self.last_bridge_tick_count: int | None = None
        self.last_error: str | None = None

    def expected_contract(self, at: datetime | None = None) -> dict[str, object]:
        if self.instrument_code_override:
            return {
                "instrument_code": self.instrument_code_override,
                "mode": "override",
                "trade_date": None,
                "expiry": None,
                "nominal_last_trading_day": None,
                "actual_last_trading_day": None,
                "calendar_source": "override",
            }

        resolution = resolve_kospi200_front_month(
            at,
            closed_dates=self.krx_closed_dates,
            open_dates=self.krx_open_dates,
        )
        return {
            "instrument_code": resolution.instrument_code,
            "mode": "auto",
            "trade_date": resolution.trade_date.isoformat(),
            "expiry": f"{resolution.expiry_year:04d}-{resolution.expiry_month:02d}",
            "nominal_last_trading_day": resolution.nominal_last_trading_day.isoformat(),
            "actual_last_trading_day": resolution.actual_last_trading_day.isoformat(),
            "calendar_source": resolution.calendar_source,
        }

    def expected_route(self, at: datetime | None = None) -> dict[str, object]:
        contract = self.expected_contract(at)
        session = resolve_kospi200_market_session(
            at,
            closed_dates=self.krx_closed_dates,
            open_dates=self.krx_open_dates,
            night_closed_dates=self.krx_night_closed_dates,
        )
        return {
            **contract,
            "service": session.service,
            "session": session.session,
            "market_open": session.market_open,
            "session_start_date": (
                None if session.session_start_date is None else session.session_start_date.isoformat()
            ),
            "session_calendar_source": session.calendar_source,
        }

    def _expected_contract(self) -> dict[str, object]:
        return self.expected_contract()

    def _validate_instrument_code(self, instrument_code: str) -> str:
        code = instrument_code.strip().upper()
        expected = self._expected_contract()["instrument_code"]
        if code != expected:
            raise ValueError(
                f"instrument_code must be {expected} for {KOSPI200_SYMBOL}"
            )
        return code

    @staticmethod
    def _validate_service_session(service: str, session_name: str) -> None:
        expected = "day" if service == "FC_R" else "night"
        if session_name != expected:
            raise ValueError(f"{service} requires session={expected}")

    @staticmethod
    def _source(tick: KisEFriendTick) -> str:
        return f"{KIS_SOURCE_PREFIX}:{tick.session}:{tick.service}:{tick.instrument_code.strip().upper()}"

    def ingest_tick(self, tick: KisEFriendTick) -> dict[str, object]:
        code = self._validate_instrument_code(tick.instrument_code)
        self._validate_service_session(tick.service, tick.session)
        now = datetime.now(timezone.utc)
        source = self._source(tick)

        try:
            with SessionLocal() as db:
                latest_history = db.scalar(
                    select(MarketPrice)
                    .where(MarketPrice.symbol == KOSPI200_SYMBOL)
                    .order_by(MarketPrice.observed_at.desc(), MarketPrice.id.desc())
                    .limit(1)
                )

                write_history = latest_history is None
                if latest_history is not None:
                    history_time = _as_utc(latest_history.observed_at)
                    history_age = max(0.0, (now - history_time).total_seconds())
                    write_history = (
                        latest_history.source != source
                        or history_age >= self.history_interval_seconds
                    )

                save_market_observation(
                    db,
                    symbol=KOSPI200_SYMBOL,
                    price=tick.price,
                    change_pct=tick.change_pct,
                    source=source,
                    observed_at=now,
                    write_history=write_history,
                )

            with self._lock:
                self.total_ticks_received += 1
                self.total_snapshot_updates += 1
                if write_history:
                    self.total_history_rows += 1
                self.last_received_at = now
                self.last_instrument_code = code
                self.last_service = tick.service
                self.last_session = tick.session
                self.last_business_time = tick.business_time
                self.last_price = float(tick.price)
                self.last_change_pct = None if tick.change_pct is None else float(tick.change_pct)
                self.last_volume = tick.cumulative_volume
                self.last_ask1 = tick.ask1
                self.last_bid1 = tick.bid1
                self.last_bridge_tick_count = tick.tick_count
                self.last_error = None

            return {
                "accepted": True,
                "symbol": KOSPI200_SYMBOL,
                "source": source,
                "observed_at": _iso(now),
                "snapshot_updated": True,
                "history_written": write_history,
            }
        except Exception as exc:
            with self._lock:
                self.last_error = str(exc)
            raise

    def ingest_heartbeat(self, heartbeat: KisEFriendHeartbeat) -> dict[str, object]:
        code = self._validate_instrument_code(heartbeat.instrument_code)
        if heartbeat.session == "closed":
            if heartbeat.service is not None:
                raise ValueError("session=closed requires service=null")
        else:
            if heartbeat.service is None:
                raise ValueError(f"session={heartbeat.session} requires a service")
            self._validate_service_session(heartbeat.service, heartbeat.session)

        now = datetime.now(timezone.utc)
        with self._lock:
            self.total_heartbeats += 1
            self.last_heartbeat_at = now
            self.last_tick_at_reported = (
                None if heartbeat.last_tick_at is None else _as_utc(heartbeat.last_tick_at)
            )
            self.last_instrument_code = code
            self.last_service = heartbeat.service
            self.last_session = heartbeat.session
            self.last_bridge_tick_count = heartbeat.tick_count

        return {
            "accepted": True,
            "received_at": _iso(now),
        }

    def status(self) -> dict[str, object]:
        now = datetime.now(timezone.utc)
        with self._lock:
            heartbeat_age = (
                None
                if self.last_heartbeat_at is None
                else max(0.0, (now - self.last_heartbeat_at).total_seconds())
            )
            tick_age = (
                None
                if self.last_received_at is None
                else max(0.0, (now - self.last_received_at).total_seconds())
            )
            connected = heartbeat_age is not None and heartbeat_age <= self.heartbeat_stale_seconds

            expected_route = self.expected_route()
            return {
                "provider": KIS_SOURCE_PREFIX,
                "symbol": KOSPI200_SYMBOL,
                "expected_instrument_code": expected_route["instrument_code"],
                "instrument_code_mode": expected_route["mode"],
                "contract_trade_date": expected_route["trade_date"],
                "contract_expiry": expected_route["expiry"],
                "nominal_last_trading_day": expected_route["nominal_last_trading_day"],
                "actual_last_trading_day": expected_route["actual_last_trading_day"],
                "contract_calendar_source": expected_route["calendar_source"],
                "expected_service": expected_route["service"],
                "expected_session": expected_route["session"],
                "market_open": expected_route["market_open"],
                "session_start_date": expected_route["session_start_date"],
                "session_calendar_source": expected_route["session_calendar_source"],
                "connected": connected,
                "heartbeat_stale_seconds": self.heartbeat_stale_seconds,
                "history_interval_seconds": self.history_interval_seconds,
                "last_heartbeat_at": _iso(self.last_heartbeat_at),
                "heartbeat_age_seconds": None if heartbeat_age is None else round(heartbeat_age, 3),
                "last_received_at": _iso(self.last_received_at),
                "tick_age_seconds": None if tick_age is None else round(tick_age, 3),
                "last_tick_at_reported": _iso(self.last_tick_at_reported),
                "instrument_code": self.last_instrument_code,
                "service": self.last_service,
                "session": self.last_session,
                "business_time": self.last_business_time,
                "price": self.last_price,
                "change_pct": self.last_change_pct,
                "cumulative_volume": self.last_volume,
                "ask1": self.last_ask1,
                "bid1": self.last_bid1,
                "bridge_tick_count": self.last_bridge_tick_count,
                "total_ticks_received": self.total_ticks_received,
                "total_snapshot_updates": self.total_snapshot_updates,
                "total_history_rows": self.total_history_rows,
                "total_heartbeats": self.total_heartbeats,
                "last_error": self.last_error,
            }
