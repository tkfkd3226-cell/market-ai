from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import MarketSnapshot, NewsAIAnalysis, NewsArticle


ENGINE_VERSION = "stage6_rule_v3"


@dataclass(frozen=True)
class ComponentSpec:
    key: str
    label: str
    symbols: tuple[str, ...]
    scale_pct: float
    invert: bool = False


COMPONENT_SPECS = {
    "korea_semiconductors": ComponentSpec(
        key="korea_semiconductors",
        label="Korea semiconductors",
        symbols=("KRX:005930", "KRX:000660"),
        scale_pct=4.0,
    ),
    "us_semiconductors": ComponentSpec(
        key="us_semiconductors",
        label="US semiconductors",
        symbols=("NASDAQ:SKHY", "NASDAQ:NVDA", "NASDAQ:MU", "FUTURES:SOX"),
        scale_pct=4.0,
    ),
    "nasdaq_futures": ComponentSpec(
        key="nasdaq_futures",
        label="Nasdaq 100 futures",
        symbols=("FUTURES:NQ",),
        scale_pct=2.0,
    ),
    "kospi200_futures": ComponentSpec(
        key="kospi200_futures",
        label="KOSPI 200 futures",
        symbols=("FUTURES:KOSPI200",),
        scale_pct=2.0,
    ),
    "usdkrw": ComponentSpec(
        key="usdkrw",
        label="USD/KRW",
        symbols=("FX:USDKRW",),
        scale_pct=1.2,
        invert=True,
    ),
    "oil": ComponentSpec(
        key="oil",
        label="Crude oil",
        symbols=("COMMODITY:WTI", "COMMODITY:BRENT"),
        scale_pct=4.0,
        invert=True,
    ),
    "rates": ComponentSpec(
        key="rates",
        label="US Treasury yields",
        symbols=("RATE:US10Y", "RATE:US30Y"),
        scale_pct=3.0,
        invert=True,
    ),
}


KOSPI_WEIGHTS = {
    "kospi200_futures": 0.20,
    "korea_semiconductors": 0.15,
    "us_semiconductors": 0.15,
    "nasdaq_futures": 0.15,
    "rates": 0.10,
    "oil": 0.10,
    "usdkrw": 0.05,
    "news_kospi": 0.10,
}

SEMICONDUCTOR_WEIGHTS = {
    "kospi200_futures": 0.10,
    "korea_semiconductors": 0.15,
    "us_semiconductors": 0.25,
    "nasdaq_futures": 0.15,
    "rates": 0.10,
    "oil": 0.05,
    "usdkrw": 0.05,
    "news_semiconductors": 0.15,
}

GAP_UP_WEIGHTS = {
    "kospi200_futures": 0.15,
    "us_semiconductors": 0.25,
    "nasdaq_futures": 0.25,
    "rates": 0.10,
    "oil": 0.05,
    "usdkrw": 0.05,
    "news_kospi": 0.10,
    "news_semiconductors": 0.05,
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


def _score_to_heuristic_probability(score: float) -> float:
    # Stage 6 is intentionally not statistically calibrated. Keep extremes bounded.
    value = 50.0 + (score - 50.0) * 0.85
    return round(_clamp(value, 10.0, 90.0), 2)


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
                "reason": "KOSPI200 spot proxy is visible but excluded from Stage 6 futures signal",
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


def _news_time_weight(published_at: datetime | None, analyzed_at: datetime, now: datetime) -> float:
    reference = _as_utc(published_at or analyzed_at)
    age_hours = max(0.0, (now - reference).total_seconds() / 3600.0)
    # A smooth half-life-like decay without requiring additional dependencies.
    return math.exp(-age_hours / 8.0)


def _horizon_weight(value: str) -> float:
    return {
        "intraday": 1.00,
        "1d": 0.95,
        "multiday": 0.75,
        "longer": 0.50,
    }.get(value, 0.60)


def _aggregate_news(
    rows: Iterable[tuple[NewsAIAnalysis, NewsArticle]],
    *,
    now: datetime,
) -> dict[str, object]:
    kospi_sum = 0.0
    semiconductor_sum = 0.0
    total_weight = 0.0
    items: list[dict[str, object]] = []

    for analysis, article in rows:
        time_weight = _news_time_weight(article.published_at, analysis.analyzed_at, now)
        quality_weight = (
            float(analysis.market_relevance)
            * float(analysis.confidence)
            * (0.35 + 0.65 * float(analysis.novelty))
            * (0.30 + 0.70 * float(analysis.severity) / 100.0)
            * _horizon_weight(analysis.time_horizon)
            * time_weight
        )
        if quality_weight <= 0:
            continue

        kospi_sum += float(analysis.kospi_impact) * quality_weight
        semiconductor_sum += float(analysis.semiconductor_impact) * quality_weight
        total_weight += quality_weight
        items.append({
            "article_id": article.id,
            "title": article.title,
            "category": analysis.category,
            "event_type": analysis.event_type,
            "published_at": None if article.published_at is None else _as_utc(article.published_at).isoformat().replace("+00:00", "Z"),
            "quality_weight": round(quality_weight, 5),
            "kospi_impact": float(analysis.kospi_impact),
            "semiconductor_impact": float(analysis.semiconductor_impact),
        })

    if total_weight <= 0:
        return {
            "available": False,
            "count": 0,
            "quality": 0.0,
            "kospi_direction": None,
            "semiconductor_direction": None,
            "items": [],
        }

    kospi_direction = _clamp(kospi_sum / total_weight, -1.0, 1.0)
    semiconductor_direction = _clamp(semiconductor_sum / total_weight, -1.0, 1.0)

    # Keep direction and evidence quality separate. One strong article can provide
    # high-quality evidence, while multiple moderate articles reinforce it without
    # allowing quality to exceed 1.0.
    combined_quality = 0.0
    for item in items:
        item_quality = _clamp(float(item["quality_weight"]), 0.0, 1.0)
        combined_quality = 1.0 - (1.0 - combined_quality) * (1.0 - item_quality)

    return {
        "available": True,
        "count": len(items),
        "quality": round(_clamp(combined_quality, 0.0, 1.0), 4),
        "kospi_direction": round(kospi_direction, 4),
        "semiconductor_direction": round(semiconductor_direction, 4),
        "kospi_score": _direction_to_score(kospi_direction),
        "semiconductor_score": _direction_to_score(semiconductor_direction),
        "items": items[:20],
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


def build_signal(
    session: Session,
    *,
    news_lookback_hours: int,
    minimum_data_weight: float,
    ai_news_active: bool,
    now: datetime | None = None,
) -> SignalResult | None:
    now_utc = _as_utc(now or datetime.now(timezone.utc))
    snapshots = list(session.scalars(select(MarketSnapshot)).all())
    snapshot_map = {row.symbol: row for row in snapshots}

    market_components = {
        key: _build_market_component(spec, snapshot_map, now_utc)
        for key, spec in COMPONENT_SPECS.items()
    }

    if ai_news_active:
        cutoff = now_utc.timestamp() - float(news_lookback_hours * 3600)
        news_rows = list(
            session.execute(
                select(NewsAIAnalysis, NewsArticle)
                .join(NewsArticle, NewsArticle.id == NewsAIAnalysis.article_id)
                .order_by(NewsAIAnalysis.analyzed_at.desc(), NewsAIAnalysis.id.desc())
                .limit(250)
            ).all()
        )
        filtered_news_rows: list[tuple[NewsAIAnalysis, NewsArticle]] = []
        for analysis, article in news_rows:
            reference = _as_utc(article.published_at or analysis.analyzed_at)
            if reference.timestamp() >= cutoff:
                filtered_news_rows.append((analysis, article))
        news = _aggregate_news(filtered_news_rows, now=now_utc)
    else:
        news = {
            "available": False,
            "enabled": False,
            "state": "disabled_by_config",
            "count": 0,
            "quality": 0.0,
            "kospi_direction": None,
            "semiconductor_direction": None,
            "items": [],
        }

    directions: dict[str, float | None] = {
        key: (
            None if not component["available"] else float(component["direction"])
        )
        for key, component in market_components.items()
    }
    directions["news_kospi"] = (
        None if not news["available"] else float(news["kospi_direction"])
    )
    directions["news_semiconductors"] = (
        None if not news["available"] else float(news["semiconductor_direction"])
    )

    qualities: dict[str, float] = {
        key: (
            0.0 if not component["available"] else float(component.get("quality", 0.0))
        )
        for key, component in market_components.items()
    }
    news_quality = 0.0 if not news["available"] else float(news.get("quality", 0.0))
    qualities["news_kospi"] = news_quality
    qualities["news_semiconductors"] = news_quality

    kospi_direction, kospi_available_weight = _combine(KOSPI_WEIGHTS, directions, qualities)
    semi_direction, semi_available_weight = _combine(SEMICONDUCTOR_WEIGHTS, directions, qualities)
    gap_direction, gap_available_weight = _combine(GAP_UP_WEIGHTS, directions, qualities)

    eligible_weights = {
        "kospi": sum(
            weight for key, weight in KOSPI_WEIGHTS.items()
            if ai_news_active or not key.startswith("news_")
        ),
        "semiconductors": sum(
            weight for key, weight in SEMICONDUCTOR_WEIGHTS.items()
            if ai_news_active or not key.startswith("news_")
        ),
        "gap_up": sum(
            weight for key, weight in GAP_UP_WEIGHTS.items()
            if ai_news_active or not key.startswith("news_")
        ),
    }
    completeness_parts = [
        kospi_available_weight / max(eligible_weights["kospi"], 1e-9),
        semi_available_weight / max(eligible_weights["semiconductors"], 1e-9),
        gap_available_weight / max(eligible_weights["gap_up"], 1e-9),
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
    up_close_score = round(kospi_score * 0.55 + semiconductor_score * 0.45, 2)

    # Confidence is a data/consensus indicator, not forecast accuracy.
    directional_agreement = 1.0 - min(1.0, abs(kospi_direction - semi_direction) / 2.0)
    confidence = round(
        _clamp(0.65 * data_completeness + 0.35 * directional_agreement, 0.0, 1.0),
        4,
    )

    details = {
        "method": ENGINE_VERSION,
        "calibrated": False,
        "probability_note": (
            "Stage 6 probabilities are bounded heuristic mappings from rule-based scores; "
            "they are not yet statistically calibrated."
        ),
        "created_at": now_utc.isoformat().replace("+00:00", "Z"),
        "weights": {
            "kospi": KOSPI_WEIGHTS,
            "semiconductors": SEMICONDUCTOR_WEIGHTS,
            "gap_up": GAP_UP_WEIGHTS,
        },
        "news_policy": {
            "active": ai_news_active,
            "state": "active" if ai_news_active else "disabled_by_config",
            "completeness_policy": (
                "news weights are eligible and missing AI news reduces completeness"
                if ai_news_active
                else "news weights are excluded from completeness and confidence"
            ),
        },
        "eligible_weight": {
            key: round(value, 4) for key, value in eligible_weights.items()
        },
        "effective_weight": {
            "kospi": round(kospi_available_weight, 4),
            "semiconductors": round(semi_available_weight, 4),
            "gap_up": round(gap_available_weight, 4),
        },
        "market_components": market_components,
        "news": news,
        "directions": {key: None if value is None else round(value, 4) for key, value in directions.items()},
        "qualities": {key: round(value, 4) for key, value in qualities.items()},
        "scores": {
            "kospi": kospi_score,
            "semiconductors": semiconductor_score,
            "gap_up_raw": gap_score,
            "up_close_raw": up_close_score,
        },
    }

    return SignalResult(
        created_at=now_utc,
        engine_version=ENGINE_VERSION,
        kospi_score=kospi_score,
        semiconductor_score=semiconductor_score,
        gap_up_probability=_score_to_heuristic_probability(gap_score),
        up_close_probability=_score_to_heuristic_probability(up_close_score),
        confidence=confidence,
        data_completeness=data_completeness,
        calibrated=False,
        details=details,
    )


def encode_details(details: dict[str, object]) -> str:
    return json.dumps(details, ensure_ascii=False, separators=(",", ":"))
