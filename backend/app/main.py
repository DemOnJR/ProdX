import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session as OrmSession

import os

from app.cache import (
    get_client,
    get_graph as cache_get,
    init_redis,
    invalidate_graph,
    set_graph as cache_set,
)
from app.config import Settings, cors_origin_list, get_settings
from app.db import Base, configure_engine, get_engine, get_session
from app.models import Graph
from app.schemas import GraphPayload, HealthResponse, MetricsResponse, ServiceCheck
from app.seed import PRODX_GRAPH

GRAPH_ID = "prodx"


def seed(settings: Settings) -> None:
    """Insert the bundled prodx graph if missing. Overwrite if FORCE_SEED=true.

    Set FORCE_SEED=true on the api Deployment to make pod restarts replace
    the stored graph with whatever's in app.seed.PRODX_GRAPH — useful for
    shipping graph updates without manually PUTting through the API.
    """
    force = os.getenv("FORCE_SEED", "false").lower() in ("true", "1", "yes")
    engine = get_engine()
    with OrmSession(bind=engine) as db:
        existing = db.get(Graph, GRAPH_ID)
        if existing is None:
            db.add(Graph(id=GRAPH_ID, payload=PRODX_GRAPH))
            db.commit()
        elif force:
            existing.payload = PRODX_GRAPH
            db.commit()
            # Bust the Redis cache so the next GET returns the fresh payload.
            invalidate_graph(GRAPH_ID)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_engine(settings.database_url)
    init_redis(settings.redis_url)
    app.state.started_at_monotonic = time.monotonic()
    Base.metadata.create_all(bind=get_engine())
    seed(settings)
    yield


settings = get_settings()

app = FastAPI(title="ProdX API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origin_list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "PUT", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.get("/api/graphs/{graph_id}")
def get_graph(graph_id: str, db: Session = Depends(get_session)) -> dict:
    s = get_settings()
    cached = cache_get(graph_id)
    if cached is not None:
        return json.loads(cached)
    row = db.get(Graph, graph_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Graph not found")
    body = {"nodes": row.payload.get("nodes", []), "edges": row.payload.get("edges", [])}
    cache_set(graph_id, json.dumps(body), s.cache_ttl_seconds)
    return body


@app.put("/api/graphs/{graph_id}")
def put_graph(graph_id: str, body: GraphPayload, db: Session = Depends(get_session)) -> dict:
    payload = {"nodes": body.nodes, "edges": body.edges}
    row = db.get(Graph, graph_id)
    if row is None:
        db.add(Graph(id=graph_id, payload=payload))
    else:
        row.payload = payload
    db.commit()
    invalidate_graph(graph_id)
    return payload


@app.get("/api/metrics", response_model=MetricsResponse)
def metrics(request: Request, db: Session = Depends(get_session)) -> MetricsResponse:
    started = getattr(request.app.state, "started_at_monotonic", None)
    uptime = time.monotonic() - float(started) if started is not None else 0.0

    deps: dict[str, ServiceCheck] = {}
    pg_ok = False
    redis_ok = False

    t0 = time.perf_counter()
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        deps["postgres"] = ServiceCheck(ok=True, latency_ms=round((time.perf_counter() - t0) * 1000, 2))
        pg_ok = True
    except Exception as e:  # noqa: BLE001
        deps["postgres"] = ServiceCheck(ok=False, error=str(e))

    t0 = time.perf_counter()
    try:
        get_client().ping()
        deps["redis"] = ServiceCheck(ok=True, latency_ms=round((time.perf_counter() - t0) * 1000, 2))
        redis_ok = True
    except Exception as e:  # noqa: BLE001
        deps["redis"] = ServiceCheck(ok=False, error=str(e))

    graph_count = int(db.scalar(select(func.count()).select_from(Graph)) or 0)

    if not pg_ok:
        status = "unhealthy"
    elif not redis_ok:
        status = "degraded"
    else:
        status = "healthy"

    return MetricsResponse(
        status=status,
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=round(uptime, 3),
        dependencies=deps,
        graph_count=graph_count,
    )
