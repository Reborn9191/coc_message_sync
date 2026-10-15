from __future__ import annotations

import asyncio
import hmac
import logging
import time
from collections import deque
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response

from .config import Settings
from .db import Database
from .models import HealthResponse, IncomingMessage, IngestResponse
from .metrics import RuntimeMetrics
from .qq import DryRunQQAdapter, OneBotAdapter
from .service import DeliveryWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = Settings.from_env()
database = Database(settings.db_path)
adapter = (
    OneBotAdapter(settings.onebot_url, settings.onebot_access_token)
    if settings.onebot_url and not settings.dry_run
    else DryRunQQAdapter()
)
metrics = RuntimeMetrics()
worker = DeliveryWorker(database, adapter, settings, metrics)


class SlidingWindowRateLimiter:
    """Small in-process limiter for the collector endpoint.

    The collector is expected to call one bridge instance. Deploying several
    replicas should use a shared gateway/Redis limiter instead.
    """

    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = max(1, limit)
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        async with self._lock:
            events = self._events.setdefault(key, deque())
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            # Avoid unbounded growth if a device keeps changing source IPs.
            if len(self._events) > 2048:
                self._events = {
                    item: values
                    for item, values in self._events.items()
                    if values and values[-1] > cutoff
                }
            return True


collector_limiter = SlidingWindowRateLimiter(settings.collector_rate_limit_per_minute)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not settings.dry_run:
        missing = [
            name
            for name, value in (
                ("ONEBOT_URL", settings.onebot_url),
                ("QQ_GROUP_ID", settings.qq_group_id),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "DRY_RUN=false requires: " + ", ".join(missing)
            )
    database.initialize()
    await worker.start()
    yield
    await worker.stop()


app = FastAPI(
    title="Clash of Clans → QQ Message Bridge",
    version="0.1.0",
    lifespan=lifespan,
)


async def require_collector_token(
    request: Request,
    x_collector_token: str | None = Header(default=None),
) -> None:
    expected = settings.collector_token
    if not expected or not x_collector_token or not hmac.compare_digest(x_collector_token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid collector token")
    source_ip = request.client.host if request.client else "unknown"
    if not await collector_limiter.allow(source_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="collector rate limit exceeded",
            headers={"Retry-After": "60"},
        )


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    expected = settings.admin_token
    if not expected or not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse(
        status="ok",
        dry_run=settings.dry_run or not settings.onebot_url,
        qq_configured=bool(settings.qq_group_id and settings.onebot_url and not settings.dry_run),
    )


@app.post(
    "/api/v1/messages",
    response_model=IngestResponse,
    dependencies=[Depends(require_collector_token)],
)
async def ingest_message(payload: IncomingMessage) -> JSONResponse:
    if len(payload.content) > settings.max_message_length:
        raise HTTPException(status_code=422, detail="content is too long")
    message_id, duplicate = await asyncio.to_thread(
        database.insert_message,
        clan_id=payload.clan_id,
        sender=payload.sender,
        content=payload.content,
        observed_at=payload.observed_at,
        source=payload.source,
        source_message_id=payload.source_message_id,
    )
    metrics.received += 1
    if not duplicate:
        metrics.queued += 1
        worker.notify()
    else:
        metrics.duplicates += 1
    result = IngestResponse(
        message_id=message_id,
        duplicate=duplicate,
        delivery_status="duplicate" if duplicate else "queued",
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK if duplicate else status.HTTP_202_ACCEPTED,
        content=result.dict(),
    )


@app.get("/api/v1/admin/outbox", dependencies=[Depends(require_admin_token)])
async def outbox_status() -> dict[str, object]:
    return {"counts": await asyncio.to_thread(database.counts)}


@app.post("/api/v1/admin/outbox/retry", dependencies=[Depends(require_admin_token)])
async def retry_failed(
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, int]:
    retried = await asyncio.to_thread(database.retry_failed, limit)
    if retried:
        worker.notify()
    return {"retried": retried}


@app.get("/api/v1/admin/messages", dependencies=[Depends(require_admin_token)])
async def recent_messages(
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, object]:
    return {"messages": await asyncio.to_thread(database.recent_messages, limit)}


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics() -> Response:
    return Response(content=metrics.prometheus(), media_type="text/plain; version=0.0.4")
