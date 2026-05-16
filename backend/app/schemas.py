from datetime import datetime
from typing import Any

from pydantic import BaseModel


class GraphPayload(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class HealthResponse(BaseModel):
    status: str = "ok"


class ServiceCheck(BaseModel):
    ok: bool
    latency_ms: float | None = None
    error: str | None = None


class MetricsResponse(BaseModel):
    status: str
    timestamp: datetime
    uptime_seconds: float
    service: str = "prodx-api"
    dependencies: dict[str, ServiceCheck]
    graph_count: int
