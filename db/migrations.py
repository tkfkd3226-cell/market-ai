from datetime import timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from .models import MarketPrice, MarketSnapshot


LEGACY_SKHY_SYMBOL = "OTC:SKHY"
CURRENT_SKHY_SYMBOL = "NASDAQ:SKHY"


def migrate_stage3_symbols(session: Session) -> None:
    """Keep Stage 2 data if the pre-Nasdaq SKHY internal symbol already exists."""
    session.execute(
        update(MarketPrice)
        .where(MarketPrice.symbol == LEGACY_SKHY_SYMBOL)
        .values(symbol=CURRENT_SKHY_SYMBOL)
    )

    legacy = session.get(MarketSnapshot, LEGACY_SKHY_SYMBOL)
    current = session.get(MarketSnapshot, CURRENT_SKHY_SYMBOL)

    if legacy is not None:
        if current is None:
            session.add(
                MarketSnapshot(
                    symbol=CURRENT_SKHY_SYMBOL,
                    observed_at=legacy.observed_at,
                    price=legacy.price,
                    change_pct=legacy.change_pct,
                    source=legacy.source,
                )
            )
        else:
            legacy_time = legacy.observed_at
            current_time = current.observed_at
            if legacy_time.tzinfo is None:
                legacy_time = legacy_time.replace(tzinfo=timezone.utc)
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=timezone.utc)

            if legacy_time > current_time:
                current.observed_at = legacy.observed_at
                current.price = legacy.price
                current.change_pct = legacy.change_pct
                current.source = legacy.source

        session.delete(legacy)

    session.commit()
