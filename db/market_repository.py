from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import MarketPrice, MarketSnapshot


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def save_market_observation(
    session: Session,
    *,
    symbol: str,
    price: float,
    change_pct: float | None,
    source: str,
    observed_at: datetime | None = None,
    write_history: bool = True,
) -> MarketPrice | None:
    normalized_symbol = symbol.strip()
    normalized_source = source.strip()

    if not normalized_symbol:
        raise ValueError("symbol is required")
    if not normalized_source:
        raise ValueError("source is required")

    timestamp = observed_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    history_row: MarketPrice | None = None
    if write_history:
        history_row = MarketPrice(
            observed_at=timestamp,
            symbol=normalized_symbol,
            price=float(price),
            change_pct=None if change_pct is None else float(change_pct),
            source=normalized_source,
        )
        session.add(history_row)

    snapshot = session.get(MarketSnapshot, normalized_symbol)
    if snapshot is None:
        snapshot = MarketSnapshot(
            symbol=normalized_symbol,
            observed_at=timestamp,
            price=float(price),
            change_pct=None if change_pct is None else float(change_pct),
            source=normalized_source,
        )
        session.add(snapshot)
    else:
        proxy_cannot_replace_verified_kis = (
            normalized_symbol == "FUTURES:KOSPI200"
            and snapshot.source.startswith("kis-efriend:")
            and ":proxy" in normalized_source
        )
        if timestamp >= _as_utc(snapshot.observed_at) and not proxy_cannot_replace_verified_kis:
            snapshot.observed_at = timestamp
            snapshot.price = float(price)
            snapshot.change_pct = None if change_pct is None else float(change_pct)
            snapshot.source = normalized_source

    session.commit()
    if history_row is not None:
        session.refresh(history_row)
    return history_row


def get_market_snapshot(session: Session) -> list[MarketSnapshot]:
    return list(
        session.scalars(select(MarketSnapshot).order_by(MarketSnapshot.symbol)).all()
    )


def get_market_history(
    session: Session,
    symbol: str,
    *,
    limit: int = 50,
) -> list[MarketPrice]:
    statement = (
        select(MarketPrice)
        .where(MarketPrice.symbol == symbol)
        .order_by(MarketPrice.observed_at.desc(), MarketPrice.id.desc())
        .limit(limit)
    )
    return list(session.scalars(statement).all())
