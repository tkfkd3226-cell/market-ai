from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import MarketSnapshot


ENGINE_VERSION = "stage6_rule_v6"


@dataclass(frozen=True)
class ComponentSpec:
    key: str
    label: str
    symbols: tuple[str, ...]
    scale_pct: float
    invert: bool = False


# Signal names are intentionally literal: each score uses only inputs that match
# the meaning shown in the dashboard tooltip. Macro/news inputs are collected by
# Market AI for other uses, but they are not blended into these four rule scores.
COMPONENT_SPECS = {
    "kospi_index": ComponentSpec(
        key="kospi_index",
        label="KOSPI spot index",
        symbols=("INDEX:KOSPI",),
        scale_pct=2.0,
    ),
    "kospi200_futures": ComponentSpec(
        key="kospi200_futures",
        label="KOSPI 200 futures",
        symbols=("FUTURES:KOSPI200",),
        scale_pct=2.0,
    ),
    "samsung_electronics": ComponentSpec(
        key="samsung_electronics",
        label="Samsung Electronics",
        symbols=("KRX:005930",),
        scale_pct=4.0,
    ),
    "sk_hynix": ComponentSpec(
        key="sk_hynix",
        label="SK hynix",
        symbols=("KRX:000660",),
        scale_pct=4.0,
    ),
    "sox_index": ComponentSpec(
        key="sox_index",
        label="PHLX Semiconductor Index",
        symbols=("INDEX:SOX",),
        scale_pct=3.0,
    ),
    "nvidia": ComponentSpec(
        key="nvidia",
        label="NVIDIA",
        symbols=("NASDAQ:NVDA",),
        scale_pct=4.0,
    ),
    "micron": ComponentSpec(
        key="micron",
        label="Micron",
        symbols=("NASDAQ:MU",),
        scale_pct=4.0,
    ),
    "sk_hynix_adr": ComponentSpec(
        key="sk_hynix_adr",
        label="SK hynix ADR",
        symbols=("NASDAQ:SKHY",),
        scale_pct=4.0,
    ),
    "nasdaq100_futures": ComponentSpec(
        key="nasdaq100_futures",
        label="Nasdaq 100 futures",
        symbols=("FUTURES:NQ",),
        scale_pct=2.0,
    ),
    "usdkrw": ComponentSpec(
        key="usdkrw",
        label="USD/KRW",
        symbols=("FX:USDKRW",),
        scale_pct=1.2,
        invert=True,
    ),
}


# Literal KOSPI direction: current KOSPI spot + leading KOSPI200 futures.
KOSPI_WEIGHTS = {
    "kospi_index": 0.35,
    "kospi200_futures": 0.65,
}

# Semiconductor direction: only direct Korean/US semiconductor assets and SOX.
SEMICONDUCTOR_WEIGHTS = {
    "samsung_electronics": 0.20,
    "sk_hynix": 0.20,
    "sox_index": 0.20,
    "nvidia": 0.15,
    "sk_hynix_adr": 0.15,
    "micron": 0.10,
}

# Pre-open gap signal: leading overnight inputs in the requested priority order.
GAP_UP_WEIGHTS = {
    "kospi200_futures": 0.50,
    "sox_index": 0.25,
    "nasdaq100_futures": 0.20,
    "usdkrw": 0.05,
}

# Up-close signal is now a direct market score, not a KOSPI/semi score blend.
UP_CLOSE_WEIGHTS = {
    "kospi_index": 0.45,
    "kospi200_futures": 0.35,
    "sox_index": 0.12,
    "nasdaq100_futures": 0.08,
}


@dataclass
class SignalResult:
    created_at: datetime
    engine_version: str
    kospi_score: float
    semiconductor_score: float
    gap_up_probability: float
    up_close_probability: float
    confidence: float
    data_completeness: float
    calibrated: bool
    details: dict[str, object]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _direction_to_score(direction: float) -> float:
    return round(50.0 + 50.0 * _clamp(direction, -1.0, 1.0), 2)


def _freshness_weight(observed_at: datetime, now: datetime) -> float:
    age_hours = max(0.0, (now - _as_utc(observed_at)).total_seconds() / 3600.0)
    if age_hours <= 0.25:
        return 1.0
    if age_hours <= 6.0:
        return 0.85
    if age_hours <= 36.0:
        return 0.65
    if age_hours <= 96.0:
        return 0.40
    return 0.0


def _normalize_change(change_pct: float, scale_pct: float, invert: bool) -> float:
    direction = math.tanh(change_pct / max(0.01, scale_pct))
    return -direction if invert else direction


def _build_market_component(
    spec: ComponentSpec,
    snapshot_map: dict[str, MarketSnapshot],
    now: datetime,
) -> dict[str, object]:
    inputs: list[dict[str, object]] = []
    weighted_directions: list[tuple[float, float]] = []

    for symbol in spec.symbols:
        row = snapshot_map.get(symbol)
        if row is None or row.change_pct is None:
            inputs.append({
                "symbol": symbol,
                "available": False,
                "reason": "missing snapshot or change_pct",
            })
            continue

        freshness = _freshness_weight(row.observed_at, now)
        direction = _normalize_change(float(row.change_pct), spec.scale_pct, spec.invert)
        is_proxy = ":proxy" in row.source
        if spec.key == "kospi200_futures" and is_proxy:
            inputs.append({
                "symbol": symbol,
                "available": False,
                "price": float(row.price),
                "change_pct": float(row.change_pct),
                "source": row.source,
                "observed_at": _as_utc(row.observed_at).isoformat().replace("+00:00", "Z"),
                "reason": "KOSPI200 spot proxy is visible but excluded from futures signal",
            })
            continue

        if freshness > 0:
            weighted_directions.append((direction, freshness))

        inputs.append({
            "symbol": symbol,
            "available": freshness > 0,
            "price": float(row.price),
            "change_pct": float(row.change_pct),
            "source": row.source,
            "observed_at": _as_utc(row.observed_at).isoformat().replace("+00:00", "Z"),
            "freshness_weight": round(freshness, 4),
            "direction": round(direction, 4),
        })

    quality = _clamp(
        sum(weight for _, weight in weighted_directions) / max(1, len(spec.symbols)),
        0.0,
        1.0,
    )
    if not weighted_directions or quality <= 0:
        return {
            "key": spec.key,
            "label": spec.label,
            "available": False,
            "direction": None,
            "quality": 0.0,
            "score": None,
            "inputs": inputs,
        }

    total_weight = sum(weight for _, weight in weighted_directions)
    direction = sum(value * weight for value, weight in weighted_directions) / total_weight
    return {
        "key": spec.key,
        "label": spec.label,
        "available": True,
        "direction": round(direction, 4),
        "quality": round(quality, 4),
        "score": _direction_to_score(direction),
        "inputs": inputs,
    }


def _combine(
    weights: dict[str, float],
    directions: dict[str, float | None],
    qualities: dict[str, float],
) -> tuple[float, float]:
    effective_weight = 0.0
    weighted_sum = 0.0
    for key, configured_weight in weights.items():
        direction = directions.get(key)
        quality = _clamp(float(qualities.get(key, 0.0)), 0.0, 1.0)
        if direction is None or quality <= 0:
            continue
        component_weight = configured_weight * quality
        effective_weight += component_weight
        weighted_sum += direction * component_weight

    if effective_weight <= 0:
        return 0.0, 0.0
    return _clamp(weighted_sum / effective_weight, -1.0, 1.0), effective_weight


def _directional_agreement(values: list[float]) -> float:
    if len(values) < 2:
        return 1.0
    differences = [
        abs(left - right) / 2.0
        for index, left in enumerate(values)
        for right in values[index + 1:]
    ]
    return _clamp(1.0 - sum(differences) / max(1, len(differences)), 0.0, 1.0)


def build_signal(
    session: Session,
    *,
    news_lookback_hours: int,
    minimum_data_weight: float,
    ai_news_active: bool,
    now: datetime | None = None,
) -> SignalResult | None:
    # news_lookback_hours / ai_news_active remain in the public function signature
    # for service/API compatibility. v5 deliberately does not use news inputs.
    del news_lookback_hours, ai_news_active

    now_utc = _as_utc(now or datetime.now(timezone.utc))
    snapshots = list(session.scalars(select(MarketSnapshot)).all())
    snapshot_map = {row.symbol: row for row in snapshots}

    market_components = {
        key: _build_market_component(spec, snapshot_map, now_utc)
        for key, spec in COMPONENT_SPECS.items()
    }

    directions: dict[str, float | None] = {
        key: (None if not component["available"] else float(component["direction"]))
        for key, component in market_components.items()
    }
    qualities: dict[str, float] = {
        key: (0.0 if not component["available"] else float(component.get("quality", 0.0)))
        for key, component in market_components.items()
    }

    kospi_direction, kospi_available_weight = _combine(KOSPI_WEIGHTS, directions, qualities)
    semi_direction, semi_available_weight = _combine(SEMICONDUCTOR_WEIGHTS, directions, qualities)
    gap_direction, gap_available_weight = _combine(GAP_UP_WEIGHTS, directions, qualities)
    up_close_direction, up_close_available_weight = _combine(UP_CLOSE_WEIGHTS, directions, qualities)

    eligible_weights = {
        "kospi": sum(KOSPI_WEIGHTS.values()),
        "semiconductors": sum(SEMICONDUCTOR_WEIGHTS.values()),
        "gap_up": sum(GAP_UP_WEIGHTS.values()),
        "up_close": sum(UP_CLOSE_WEIGHTS.values()),
    }
    available_weights = {
        "kospi": kospi_available_weight,
        "semiconductors": semi_available_weight,
        "gap_up": gap_available_weight,
        "up_close": up_close_available_weight,
    }
    completeness_parts = [
        available_weights[key] / max(eligible_weights[key], 1e-9)
        for key in eligible_weights
    ]
    data_completeness = round(
        _clamp(sum(completeness_parts) / len(completeness_parts), 0.0, 1.0),
        4,
    )
    if data_completeness < minimum_data_weight:
        return None

    kospi_score = _direction_to_score(kospi_direction)
    semiconductor_score = _direction_to_score(semi_direction)
    gap_score = _direction_to_score(gap_direction)
    up_close_score = _direction_to_score(up_close_direction)

    # Confidence remains a data/consensus indicator, not forecast accuracy.
    directional_agreement = _directional_agreement([
        kospi_direction,
        semi_direction,
        gap_direction,
        up_close_direction,
    ])
    confidence = round(
        _clamp(0.65 * data_completeness + 0.35 * directional_agreement, 0.0, 1.0),
        4,
    )

    details = {
        "method": ENGINE_VERSION,
        "calibrated": False,
        "probability_note": (
            "Rule scores are bounded heuristic 0-100 signals; they are not statistically "
            "calibrated unless a Stage 9 calibration model is returned separately."
        ),
        "created_at": now_utc.isoformat().replace("+00:00", "Z"),
        "input_policy": {
            "news_used": False,
            "macro_used": ["USD/KRW"] ,
            "note": (
                "v5 keeps each dashboard signal literal: KOSPI uses KOSPI/KOSPI200 futures; "
                "semiconductors use direct semiconductor assets; gap/up-close use their explicit maps."
            ),
        },
        "weights": {
            "kospi": KOSPI_WEIGHTS,
            "semiconductors": SEMICONDUCTOR_WEIGHTS,
            "gap_up": GAP_UP_WEIGHTS,
            "up_close": UP_CLOSE_WEIGHTS,
        },
        "eligible_weight": {
            key: round(value, 4) for key, value in eligible_weights.items()
        },
        "effective_weight": {
            key: round(value, 4) for key, value in available_weights.items()
        },
        "market_components": market_components,
        "directions": {
            key: None if value is None else round(value, 4)
            for key, value in directions.items()
        },
        "qualities": {key: round(value, 4) for key, value in qualities.items()},
        "scores": {
            "kospi": kospi_score,
            "semiconductors": semiconductor_score,
            "gap_up": gap_score,
            "up_close": up_close_score,
        },
    }

    return SignalResult(
        created_at=now_utc,
        engine_version=ENGINE_VERSION,
        kospi_score=kospi_score,
        semiconductor_score=semiconductor_score,
        # Legacy API/DB field names are preserved, but all four uncalibrated
        # Rule Signals now expose the same direct weighted 0-100 score.
        gap_up_probability=gap_score,
        up_close_probability=up_close_score,
        confidence=confidence,
        data_completeness=data_completeness,
        calibrated=False,
        details=details,
    )


def encode_details(details: dict[str, object]) -> str:
    return json.dumps(details, ensure_ascii=False, separators=(",", ":"))
