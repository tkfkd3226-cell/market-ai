from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from ai.openai_analyzer import OpenAINewsAnalyzer
from backtest.schemas import MarketOutcomeInput
from backtest.service import build_backtest_summary, evaluate_all_final_outcomes, evaluate_outcome
from calibration.service import (
    CALIBRATION_METHOD,
    TARGETS as CALIBRATION_TARGETS,
    calibration_performance,
    calibration_readiness,
    get_active_models,
    get_signal_calibration,
    get_signal_calibration_map,
    list_calibration_models,
    serialize_model as serialize_calibration_model,
    serialize_signal_calibration,
    train_all_targets,
)
from ai.schemas import AI_CATEGORIES
from ai.service import NewsAIService
from collectors.service import MarketCollectorService
from bridges.kis_efriend import KisEFriendBridgeService, KisEFriendHeartbeat, KisEFriendTick
from collectors.yfinance_collector import YFinanceCollector
from config import (
    BACKTEST_MAX_FORECAST_AGE_HOURS,
    CALIBRATION_BIN_COUNT,
    CALIBRATION_MIN_CLASS_COUNT,
    CALIBRATION_MIN_SAMPLES,
    CALIBRATION_PRIOR_STRENGTH,
    AI_NEWS_ACTIVE,
    AI_NEWS_BATCH_SIZE,
    AI_NEWS_ENABLED,
    AI_NEWS_POLL_SECONDS,
    ALLOW_KOSPI200_INDEX_PROXY,
    COLLECTOR_ENABLED,
    COLLECTOR_POLL_SECONDS,
    GDELT_TIMEOUT_SECONDS,
    NEWS_COLLECTOR_ENABLED,
    NEWS_COLLECTOR_POLL_SECONDS,
    NEWS_LOOKBACK_HOURS,
    NEWS_MAX_RECORDS_PER_TOPIC,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TIMEOUT_SECONDS,
    SIGNAL_ENGINE_ENABLED,
    SIGNAL_ENGINE_POLL_SECONDS,
    SIGNAL_MINIMUM_DATA_WEIGHT,
    SIGNAL_NEWS_LOOKBACK_HOURS,
    YFINANCE_TIMEOUT_SECONDS,
    KIS_EFRIEND_HISTORY_INTERVAL_SECONDS,
    KIS_EFRIEND_HEARTBEAT_STALE_SECONDS,
    KIS_EFRIEND_KOSPI200_CODE,
    KIS_EFRIEND_KRX_CLOSED_DATES,
    KIS_EFRIEND_KRX_OPEN_DATES,
    KIS_EFRIEND_KRX_NIGHT_CLOSED_DATES,
)
from db.backtest_repository import (
    decode_outcome_details,
    get_backtest_counts,
    get_evaluation_dataset,
    get_latest_market_outcome,
    get_market_outcomes,
    upsert_market_outcome,
)
from db.database import Base, SessionLocal, check_database, engine
from db.market_repository import get_market_history, get_market_snapshot
from db.migrations import migrate_stage3_symbols
from db.models import MarketSignal, NewsAIAnalysis, NewsArticle
from db.news_ai_repository import (
    decode_affected_assets,
    get_ai_usage_summary,
    get_latest_news_ai_analyses,
    get_news_ai_counts,
)
from db.news_repository import get_latest_news, get_news_topics_for_articles
from db.signal_repository import decode_signal_details, get_latest_signal_run, get_signal_history
from market.catalog import MARKET_INSTRUMENTS, MARKET_SYMBOLS
from market.provider_map import get_yahoo_mappings
from news.gdelt_collector import GDELTNewsCollector
from news.service import NewsCollectorService
from news.topics import NEWS_TOPICS, NEWS_TOPIC_KEYS
from signals.engine import (
    COMPONENT_SPECS,
    ENGINE_VERSION,
    GAP_UP_WEIGHTS,
    KOSPI_WEIGHTS,
    SEMICONDUCTOR_WEIGHTS,
)
from signals.service import SignalService


def to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    return value.isoformat().replace("+00:00", "Z")


def serialize_market_row(row: object) -> dict[str, object]:
    return {
        "symbol": row.symbol,
        "price": row.price,
        "change_pct": row.change_pct,
        "source": row.source,
        "observed_at": to_utc_iso(row.observed_at),
    }


def serialize_news_article(
    article: NewsArticle,
    topics: list[str],
) -> dict[str, object]:
    return {
        "id": article.id,
        "published_at": None if article.published_at is None else to_utc_iso(article.published_at),
        "collected_at": to_utc_iso(article.collected_at),
        "provider": article.provider,
        "title": article.title,
        "url": article.url,
        "domain": article.domain,
        "language": article.language,
        "source_country": article.source_country,
        "social_image": article.social_image,
        "topics": topics,
        "ai_status": article.ai_status,
    }


def serialize_news_ai_analysis(
    analysis: NewsAIAnalysis,
    article: NewsArticle,
    topics: list[str],
) -> dict[str, object]:
    return {
        "article": {
            "id": article.id,
            "published_at": None if article.published_at is None else to_utc_iso(article.published_at),
            "provider": article.provider,
            "title": article.title,
            "url": article.url,
            "domain": article.domain,
            "topics": topics,
        },
        "analysis": {
            "analyzed_at": to_utc_iso(analysis.analyzed_at),
            "model": analysis.model,
            "prompt_version": analysis.prompt_version,
            "category": analysis.category,
            "event_type": analysis.event_type,
            "market_relevance": analysis.market_relevance,
            "sentiment": analysis.sentiment,
            "severity": analysis.severity,
            "confidence": analysis.confidence,
            "novelty": analysis.novelty,
            "time_horizon": analysis.time_horizon,
            "affected_assets": decode_affected_assets(analysis.affected_assets_json),
            "impact": {
                "kospi": analysis.kospi_impact,
                "semiconductors": analysis.semiconductor_impact,
                "nasdaq100": analysis.nasdaq100_impact,
                "oil": analysis.oil_impact,
                "rates": analysis.rates_impact,
                "usdkrw": analysis.usdkrw_impact,
            },
            "rationale": analysis.rationale,
        },
    }


def serialize_market_outcome(row: object) -> dict[str, object]:
    return {
        "id": row.id,
        "session_date": row.session_date.isoformat(),
        "finalized_at": to_utc_iso(row.finalized_at),
        "source": row.source,
        "source_reference": row.source_reference,
        "kospi_prev_close": row.kospi_prev_close,
        "kospi_open": row.kospi_open,
        "kospi_close": row.kospi_close,
        "kospi_gap_pct": row.kospi_gap_pct,
        "kospi_close_return_pct": row.kospi_close_return_pct,
        "semiconductor_return_pct": row.semiconductor_return_pct,
        "is_final": row.is_final,
        "actual": {
            "kospi_up": row.kospi_close_return_pct > 0,
            "gap_up": row.kospi_gap_pct > 0,
            "up_close": row.kospi_close_return_pct > 0,
            "semiconductor_up": (
                None
                if row.semiconductor_return_pct is None
                else row.semiconductor_return_pct > 0
            ),
        },
        "details": decode_outcome_details(row),
    }


def serialize_backtest_row(evaluation: object, signal: object, outcome: object) -> dict[str, object]:
    return {
        "session_date": evaluation.session_date.isoformat(),
        "evaluated_at": to_utc_iso(evaluation.evaluated_at),
        "selection_rule": evaluation.selection_rule,
        "forecast": {
            "signal_run_id": signal.id,
            "forecast_at": to_utc_iso(signal.created_at),
            "age_to_open_minutes": evaluation.forecast_age_minutes,
            "engine_version": signal.engine_version,
            "kospi_score": signal.kospi_score,
            "semiconductor_score": signal.semiconductor_score,
            "gap_up_score": signal.gap_up_probability,
            "up_close_score": signal.up_close_probability,
            "confidence": signal.confidence,
            "data_completeness": signal.data_completeness,
            "calibrated": signal.calibrated,
        },
        "actual": {
            "source": outcome.source,
            "kospi_gap_pct": outcome.kospi_gap_pct,
            "kospi_close_return_pct": outcome.kospi_close_return_pct,
            "semiconductor_return_pct": outcome.semiconductor_return_pct,
            "kospi_up": evaluation.kospi_up_actual,
            "semiconductor_up": evaluation.semiconductor_up_actual,
            "gap_up": evaluation.gap_up_actual,
            "up_close": evaluation.up_close_actual,
        },
        "correct": {
            "kospi_direction": evaluation.kospi_correct,
            "semiconductor_direction": evaluation.semiconductor_correct,
            "gap_up": evaluation.gap_up_correct,
            "up_close": evaluation.up_close_correct,
        },
    }


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        migrate_stage3_symbols(session)
        latest_signal = session.scalar(
            select(MarketSignal).order_by(MarketSignal.id.desc()).limit(1)
        )
        if latest_signal is None:
            session.add(
                MarketSignal(
                    kospi_score=50.0,
                    semiconductor_score=50.0,
                    gap_up_probability=50.0,
                    source="stage1_dummy",
                )
            )
            session.commit()


collector_service = MarketCollectorService(
    YFinanceCollector(
        get_yahoo_mappings(
            allow_kospi200_index_proxy=ALLOW_KOSPI200_INDEX_PROXY,
        ),
        timeout_seconds=YFINANCE_TIMEOUT_SECONDS,
    ),
    enabled=COLLECTOR_ENABLED,
    poll_seconds=COLLECTOR_POLL_SECONDS,
)

news_service = NewsCollectorService(
    GDELTNewsCollector(
        timeout_seconds=GDELT_TIMEOUT_SECONDS,
        lookback_hours=NEWS_LOOKBACK_HOURS,
        max_records_per_topic=NEWS_MAX_RECORDS_PER_TOPIC,
    ),
    enabled=NEWS_COLLECTOR_ENABLED,
    poll_seconds=NEWS_COLLECTOR_POLL_SECONDS,
)


ai_news_service = NewsAIService(
    OpenAINewsAnalyzer(
        api_key=OPENAI_API_KEY,
        model=OPENAI_MODEL,
        timeout_seconds=OPENAI_TIMEOUT_SECONDS,
    ),
    enabled=AI_NEWS_ENABLED,
    poll_seconds=AI_NEWS_POLL_SECONDS,
    batch_size=AI_NEWS_BATCH_SIZE,
)


kis_efriend_bridge_service = KisEFriendBridgeService(
    history_interval_seconds=KIS_EFRIEND_HISTORY_INTERVAL_SECONDS,
    heartbeat_stale_seconds=KIS_EFRIEND_HEARTBEAT_STALE_SECONDS,
    expected_instrument_code=KIS_EFRIEND_KOSPI200_CODE,
    krx_closed_dates=KIS_EFRIEND_KRX_CLOSED_DATES,
    krx_open_dates=KIS_EFRIEND_KRX_OPEN_DATES,
    krx_night_closed_dates=KIS_EFRIEND_KRX_NIGHT_CLOSED_DATES,
)


signal_service = SignalService(
    enabled=SIGNAL_ENGINE_ENABLED,
    poll_seconds=SIGNAL_ENGINE_POLL_SECONDS,
    news_lookback_hours=SIGNAL_NEWS_LOOKBACK_HOURS,
    minimum_data_weight=SIGNAL_MINIMUM_DATA_WEIGHT,
    ai_news_active=ai_news_service.active,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    await collector_service.start()
    await news_service.start()
    await ai_news_service.start()
    await signal_service.start()
    try:
        yield
    finally:
        await signal_service.stop()
        await ai_news_service.stop()
        await news_service.stop()
        await collector_service.stop()


app = FastAPI(
    title="Market AI API",
    version="0.11.1",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, object]:
    try:
        check_database()
        return {
            "status": "ok",
            "database": "ok",
            "collector_enabled": collector_service.enabled,
            "collector_running": collector_service.status()["running"],
            "news_enabled": news_service.enabled,
            "news_running": news_service.status()["running"],
            "ai_enabled": ai_news_service.enabled,
            "ai_configured": ai_news_service.analyzer.configured,
            "ai_active": ai_news_service.active,
            "ai_state": ai_news_service.status()["state"],
            "ai_running": ai_news_service.status()["running"],
            "signal_enabled": signal_service.enabled,
            "signal_running": signal_service.status()["running"],
            "kis_efriend_bridge": kis_efriend_bridge_service.status(),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc


@app.get("/api/market-signal")
def market_signal() -> dict[str, object]:
    with SessionLocal() as session:
        stage6 = get_latest_signal_run(session)
        if stage6 is not None:
            return {
                "kospi_score": stage6.kospi_score,
                "semiconductor_score": stage6.semiconductor_score,
                "gap_up_probability": stage6.gap_up_probability,
                "up_close_probability": stage6.up_close_probability,
                "confidence": stage6.confidence,
                "data_completeness": stage6.data_completeness,
                "calibrated": stage6.calibrated,
                "calibration": serialize_signal_calibration(
                    get_signal_calibration(session, stage6.id)
                ),
                "source": stage6.engine_version,
                "updated_at": to_utc_iso(stage6.created_at),
            }

        signal = session.scalar(
            select(MarketSignal).order_by(MarketSignal.id.desc()).limit(1)
        )
        if signal is None:
            raise HTTPException(status_code=404, detail="market signal not found")

        return {
            "kospi_score": signal.kospi_score,
            "semiconductor_score": signal.semiconductor_score,
            "gap_up_probability": signal.gap_up_probability,
            "up_close_probability": None,
            "confidence": None,
            "data_completeness": None,
            "calibrated": False,
            "source": signal.source,
            "updated_at": to_utc_iso(signal.created_at),
        }


@app.get("/api/market-data/catalog")
def market_data_catalog() -> dict[str, object]:
    return {
        "count": len(MARKET_INSTRUMENTS),
        "items": list(MARKET_INSTRUMENTS),
    }


@app.get("/api/market-data/snapshot")
def market_data_snapshot() -> dict[str, object]:
    with SessionLocal() as session:
        rows = [row for row in get_market_snapshot(session) if row.symbol in MARKET_SYMBOLS]
        return {
            "count": len(rows),
            "items": [serialize_market_row(row) for row in rows],
        }


@app.get("/api/market-data/history/{symbol}")
def market_data_history(
    symbol: str,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, object]:
    if symbol not in MARKET_SYMBOLS:
        raise HTTPException(status_code=404, detail="unknown market symbol")

    with SessionLocal() as session:
        rows = get_market_history(session, symbol, limit=limit)
        return {
            "symbol": symbol,
            "count": len(rows),
            "items": [serialize_market_row(row) for row in rows],
        }


@app.get("/api/bridge/kis-efriend/status")
def kis_efriend_bridge_status() -> dict[str, object]:
    return kis_efriend_bridge_service.status()


@app.get("/api/bridge/kis-efriend/contract")
def kis_efriend_bridge_contract(
    at: datetime | None = Query(default=None),
) -> dict[str, object]:
    return kis_efriend_bridge_service.expected_contract(at)


@app.get("/api/bridge/kis-efriend/contract-code", response_class=PlainTextResponse)
def kis_efriend_bridge_contract_code() -> str:
    return str(kis_efriend_bridge_service.expected_contract()["instrument_code"])


@app.get("/api/bridge/kis-efriend/route")
def kis_efriend_bridge_route(
    at: datetime | None = Query(default=None),
) -> dict[str, object]:
    return kis_efriend_bridge_service.expected_route(at)


@app.get("/api/bridge/kis-efriend/route-code", response_class=PlainTextResponse)
def kis_efriend_bridge_route_code() -> str:
    route = kis_efriend_bridge_service.expected_route()
    service = route["service"] or "CLOSED"
    return f'{route["instrument_code"]}|{service}|{route["session"]}'


@app.post("/api/bridge/kis-efriend/tick")
def kis_efriend_bridge_tick(payload: KisEFriendTick) -> dict[str, object]:
    try:
        return kis_efriend_bridge_service.ingest_tick(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to persist KIS eFriend tick") from exc


@app.post("/api/bridge/kis-efriend/heartbeat")
def kis_efriend_bridge_heartbeat(payload: KisEFriendHeartbeat) -> dict[str, object]:
    try:
        return kis_efriend_bridge_service.ingest_heartbeat(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/collector/status")
def collector_status() -> dict[str, object]:
    return collector_service.status()


@app.get("/api/collector/mappings")
def collector_mappings() -> dict[str, object]:
    items = []
    for mapping in collector_service.provider.mappings:
        items.append(
            {
                "symbol": mapping.symbol,
                "provider": collector_service.provider.source_name,
                "provider_symbol": mapping.provider_symbol,
                "enabled": mapping.provider_symbol is not None,
                "is_proxy": mapping.is_proxy,
                "note": mapping.note,
            }
        )

    return {
        "count": len(items),
        "items": items,
    }


@app.post("/api/collector/run-once")
async def collector_run_once() -> dict[str, object]:
    return await collector_service.run_once()


@app.get("/api/news/status")
def news_status() -> dict[str, object]:
    return news_service.status()


@app.get("/api/news/topics")
def news_topics() -> dict[str, object]:
    return {
        "count": len(NEWS_TOPICS),
        "items": [
            {
                "key": topic.key,
                "label": topic.label,
                "query": topic.query,
            }
            for topic in NEWS_TOPICS
        ],
    }


@app.get("/api/news/latest")
def news_latest(
    limit: int = Query(default=50, ge=1, le=200),
    topic: str | None = Query(default=None),
) -> dict[str, object]:
    if topic is not None and topic not in NEWS_TOPIC_KEYS:
        raise HTTPException(status_code=404, detail="unknown news topic")

    with SessionLocal() as session:
        articles = get_latest_news(session, limit=limit, topic=topic)
        topic_map = get_news_topics_for_articles(
            session,
            [article.id for article in articles],
        )
        return {
            "topic": topic,
            "count": len(articles),
            "items": [
                serialize_news_article(article, topic_map.get(article.id, []))
                for article in articles
            ],
        }


@app.post("/api/news/run-once")
async def news_run_once() -> dict[str, object]:
    return await news_service.run_once()


@app.get("/api/ai-news/status")
def ai_news_status() -> dict[str, object]:
    with SessionLocal() as session:
        counts = get_news_ai_counts(session)
        usage = get_ai_usage_summary(session)
    return {
        **ai_news_service.status(),
        "database": counts,
        "usage": usage,
    }


@app.get("/api/ai-news/categories")
def ai_news_categories() -> dict[str, object]:
    return {
        "count": len(AI_CATEGORIES),
        "items": list(AI_CATEGORIES),
    }


@app.get("/api/ai-news/latest")
def ai_news_latest(
    limit: int = Query(default=50, ge=1, le=200),
    category: str | None = Query(default=None),
) -> dict[str, object]:
    if category is not None and category not in AI_CATEGORIES:
        raise HTTPException(status_code=404, detail="unknown AI news category")

    with SessionLocal() as session:
        rows = get_latest_news_ai_analyses(
            session,
            limit=limit,
            category=category,
        )
        topic_map = get_news_topics_for_articles(
            session,
            [article.id for _, article in rows],
        )
        return {
            "category": category,
            "count": len(rows),
            "items": [
                serialize_news_ai_analysis(
                    analysis,
                    article,
                    topic_map.get(article.id, []),
                )
                for analysis, article in rows
            ],
        }


@app.post("/api/ai-news/run-once")
async def ai_news_run_once(
    limit: int | None = Query(default=None, ge=1, le=25),
) -> dict[str, object]:
    return await ai_news_service.run_once(limit=limit)

@app.get("/api/backtest/status")
def backtest_status() -> dict[str, object]:
    with SessionLocal() as session:
        counts = get_backtest_counts(session)
        latest_outcome = get_latest_market_outcome(session)
        latest_signal = get_latest_signal_run(session)
    return {
        "prediction_ledger": "signal_runs",
        "checkpoint": "latest signal before 09:00 KST",
        "max_forecast_age_hours": BACKTEST_MAX_FORECAST_AGE_HOURS,
        "actual_outcome_policy": (
            "Stage 8 stores only explicitly supplied, source-labeled market outcomes. "
            "It does not infer missing KOSPI open/close values from unrelated snapshots."
        ),
        "counts": counts,
        "latest_signal_at": None if latest_signal is None else to_utc_iso(latest_signal.created_at),
        "latest_outcome_date": (
            None if latest_outcome is None else latest_outcome.session_date.isoformat()
        ),
    }


@app.get("/api/backtest/forecasts")
def backtest_forecasts(
    limit: int = Query(default=100, ge=1, le=5000),
) -> dict[str, object]:
    with SessionLocal() as session:
        rows = get_signal_history(session, limit=limit)
        return {
            "count": len(rows),
            "ledger": "signal_runs",
            "items": [
                {
                    "signal_run_id": row.id,
                    "forecast_at": to_utc_iso(row.created_at),
                    "engine_version": row.engine_version,
                    "kospi_score": row.kospi_score,
                    "semiconductor_score": row.semiconductor_score,
                    "gap_up_score": row.gap_up_probability,
                    "up_close_score": row.up_close_probability,
                    "confidence": row.confidence,
                    "data_completeness": row.data_completeness,
                    "calibrated": row.calibrated,
                }
                for row in rows
            ],
        }


@app.get("/api/backtest/outcomes")
def backtest_outcomes(
    limit: int = Query(default=100, ge=1, le=5000),
) -> dict[str, object]:
    with SessionLocal() as session:
        rows = get_market_outcomes(session, limit=limit)
        return {
            "count": len(rows),
            "items": [serialize_market_outcome(row) for row in rows],
        }


@app.post("/api/backtest/outcomes")
def backtest_save_outcome(payload: MarketOutcomeInput) -> dict[str, object]:
    with SessionLocal() as session:
        outcome = upsert_market_outcome(
            session,
            session_date=payload.session_date,
            source=payload.source,
            source_reference=payload.source_reference,
            kospi_prev_close=payload.kospi_prev_close,
            kospi_open=payload.kospi_open,
            kospi_close=payload.kospi_close,
            semiconductor_return_pct=payload.semiconductor_return_pct,
            is_final=payload.is_final,
            details=payload.details,
        )
        evaluation = evaluate_outcome(
            session,
            outcome,
            max_forecast_age_hours=BACKTEST_MAX_FORECAST_AGE_HOURS,
        )
        session.commit()
        return {
            "outcome": serialize_market_outcome(outcome),
            "evaluation_created": evaluation.evaluation is not None,
            "evaluation_reason": evaluation.reason,
        }


@app.post("/api/backtest/evaluate")
def backtest_evaluate() -> dict[str, object]:
    with SessionLocal() as session:
        return evaluate_all_final_outcomes(
            session,
            max_forecast_age_hours=BACKTEST_MAX_FORECAST_AGE_HOURS,
        )


@app.get("/api/backtest/evaluations")
def backtest_evaluations(
    limit: int = Query(default=100, ge=1, le=5000),
) -> dict[str, object]:
    with SessionLocal() as session:
        rows = get_evaluation_dataset(session, limit=limit)
        return {
            "count": len(rows),
            "items": [serialize_backtest_row(*row) for row in rows],
        }


@app.get("/api/backtest/summary")
def backtest_summary(
    limit: int = Query(default=5000, ge=1, le=50000),
) -> dict[str, object]:
    with SessionLocal() as session:
        summary = build_backtest_summary(session, limit=limit)
    return {
        **summary,
        "max_forecast_age_hours": BACKTEST_MAX_FORECAST_AGE_HOURS,
    }


@app.get("/api/backtest/dataset")
def backtest_dataset(
    limit: int = Query(default=1000, ge=1, le=50000),
) -> dict[str, object]:
    with SessionLocal() as session:
        rows = get_evaluation_dataset(session, limit=limit)
        active = get_active_models(session, engine_version=ENGINE_VERSION)
        return {
            "count": len(rows),
            "calibration_ready": bool(active),
            "active_calibration_targets": sorted(active),
            "note": (
                "These are the raw evaluation rows used to train Stage 9 calibration. "
                "Active models are applied only to future SignalRuns and never retroactively."
            ),
            "items": [serialize_backtest_row(*row) for row in rows],
        }


@app.get("/api/calibration/status")
def calibration_status() -> dict[str, object]:
    with SessionLocal() as session:
        active = get_active_models(session, engine_version=ENGINE_VERSION)
        readiness = calibration_readiness(
            session,
            engine_version=ENGINE_VERSION,
            min_samples=CALIBRATION_MIN_SAMPLES,
            min_class_count=CALIBRATION_MIN_CLASS_COUNT,
        )
        return {
            "engine_version": ENGINE_VERSION,
            "method": CALIBRATION_METHOD,
            "config": {
                "min_samples": CALIBRATION_MIN_SAMPLES,
                "min_class_count": CALIBRATION_MIN_CLASS_COUNT,
                "bin_count": CALIBRATION_BIN_COUNT,
                "prior_strength": CALIBRATION_PRIOR_STRENGTH,
            },
            "targets": list(CALIBRATION_TARGETS),
            "active_target_count": len(active),
            "readiness": readiness,
            "active_models": {
                target: serialize_calibration_model(model, include_nodes=False)
                for target, model in active.items()
            },
            "safety": {
                "retroactive_application": False,
                "raw_signal_fields_preserved": True,
                "minimum_data_required": True,
            },
        }


@app.post("/api/calibration/train")
def calibration_train() -> dict[str, object]:
    with SessionLocal() as session:
        return train_all_targets(
            session,
            engine_version=ENGINE_VERSION,
            min_samples=CALIBRATION_MIN_SAMPLES,
            min_class_count=CALIBRATION_MIN_CLASS_COUNT,
            bin_count=CALIBRATION_BIN_COUNT,
            prior_strength=CALIBRATION_PRIOR_STRENGTH,
        )


@app.get("/api/calibration/models")
def calibration_models(
    limit: int = Query(default=50, ge=1, le=500),
    active_only: bool = Query(default=False),
    include_nodes: bool = Query(default=False),
) -> dict[str, object]:
    with SessionLocal() as session:
        rows = list_calibration_models(
            session,
            engine_version=ENGINE_VERSION,
            active_only=active_only,
            limit=limit,
        )
        return {
            "engine_version": ENGINE_VERSION,
            "count": len(rows),
            "items": [
                serialize_calibration_model(row, include_nodes=include_nodes)
                for row in rows
            ],
        }


@app.get("/api/calibration/performance")
def calibration_performance_api(
    limit: int = Query(default=5000, ge=1, le=20000),
) -> dict[str, object]:
    with SessionLocal() as session:
        return calibration_performance(session, limit=limit)


@app.get("/api/signal/status")
def signal_status() -> dict[str, object]:
    with SessionLocal() as session:
        latest = get_latest_signal_run(session)
    return {
        **signal_service.status(),
        "latest": None if latest is None else {
            "updated_at": to_utc_iso(latest.created_at),
            "engine_version": latest.engine_version,
            "kospi_score": latest.kospi_score,
            "semiconductor_score": latest.semiconductor_score,
            "gap_up_probability": latest.gap_up_probability,
            "up_close_probability": latest.up_close_probability,
            "confidence": latest.confidence,
            "data_completeness": latest.data_completeness,
            "calibrated": latest.calibrated,
            "calibration": serialize_signal_calibration(
                get_signal_calibration(session, latest.id)
            ),
        },
    }


@app.get("/api/signal/weights")
def signal_weights() -> dict[str, object]:
    return {
        "engine_version": ENGINE_VERSION,
        "calibrated": False,
        "probability_note": (
            "The top-level Stage 6 score fields remain heuristic 0-100 signals for backward "
            "compatibility. Stage 9 calibrated probabilities are returned separately under "
            "the signal calibration object when an eligible active model existed at signal time."
        ),
        "components": {
            key: {
                "label": spec.label,
                "symbols": list(spec.symbols),
                "scale_pct": spec.scale_pct,
                "invert": spec.invert,
            }
            for key, spec in COMPONENT_SPECS.items()
        },
        "weights": {
            "kospi": KOSPI_WEIGHTS,
            "semiconductors": SEMICONDUCTOR_WEIGHTS,
            "gap_up": GAP_UP_WEIGHTS,
        },
    }


@app.get("/api/signal/latest")
def signal_latest(
    include_details: bool = Query(default=True),
) -> dict[str, object]:
    with SessionLocal() as session:
        row = get_latest_signal_run(session)
        if row is None:
            raise HTTPException(status_code=404, detail="signal run not found")
        payload = {
            "updated_at": to_utc_iso(row.created_at),
            "engine_version": row.engine_version,
            "kospi_score": row.kospi_score,
            "semiconductor_score": row.semiconductor_score,
            "gap_up_probability": row.gap_up_probability,
            "up_close_probability": row.up_close_probability,
            "confidence": row.confidence,
            "data_completeness": row.data_completeness,
            "calibrated": row.calibrated,
            "calibration": serialize_signal_calibration(
                get_signal_calibration(session, row.id)
            ),
        }
        if include_details:
            payload["details"] = decode_signal_details(row.details_json)
        return payload


@app.get("/api/signal/history")
def signal_history(
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, object]:
    with SessionLocal() as session:
        rows = get_signal_history(session, limit=limit)
        calibration_map = get_signal_calibration_map(session, [row.id for row in rows])
        return {
            "count": len(rows),
            "items": [
                {
                    "updated_at": to_utc_iso(row.created_at),
                    "engine_version": row.engine_version,
                    "kospi_score": row.kospi_score,
                    "semiconductor_score": row.semiconductor_score,
                    "gap_up_probability": row.gap_up_probability,
                    "up_close_probability": row.up_close_probability,
                    "confidence": row.confidence,
                    "data_completeness": row.data_completeness,
                    "calibrated": row.calibrated,
                    "calibration": serialize_signal_calibration(calibration_map.get(row.id)),
                }
                for row in rows
            ],
        }


@app.post("/api/signal/run-once")
async def signal_run_once() -> dict[str, object]:
    return await signal_service.run_once()

