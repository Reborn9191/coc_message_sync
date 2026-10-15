from __future__ import annotations

import asyncio
import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse

from .config import Settings
from .db import Database
from .models import HealthResponse, IncomingMessage, IngestResponse
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
worker = DeliveryWorker(database, adapter, settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.initialize()
    await worker.start()
    yield
    await worker.stop()


app = FastAPI(
    title="Clash of Clans → QQ Message Bridge",
    version="0.1.0",
    lifespan=lifespan,
)


def require_collector_token(x_collector_token: str | None = Header(default=None)) -> None:
    expected = settings.collector_token
    if not expected or not x_collector_token or not hmac.compare_digest(x_collector_token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid collector token")


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
    if not duplicate:
        worker.notify()
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
