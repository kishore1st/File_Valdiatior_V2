import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_pool, close_pool
from .config import settings
from .routers import (
    auth, uploads, batches, files, databricks, watchers, health,
)
from .services.ingestion_worker import run_worker_loop
from .services.watchers.scheduler import run_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    tasks = [asyncio.create_task(run_worker_loop())]
    if settings.WATCHER_ENABLED:
        tasks.append(asyncio.create_task(run_scheduler()))
    try:
        yield
    finally:
        for t in tasks:
            t.cancel()
        await close_pool()


app = FastAPI(title="FVI API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
for r in (auth, uploads, batches, files, databricks, watchers, health):
    app.include_router(r.router)