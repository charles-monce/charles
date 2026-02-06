"""FastAPI application entry point for Charles."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import config
from .memory import _ensure_dirs
from .routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Charles API...")
    _ensure_dirs()
    logger.info(f"Data dir: {config.data_dir}")
    logger.info("Charles API ready")
    yield
    logger.info("Charles API shutting down")


app = FastAPI(
    title="Charles — Smart Notification Gateway",
    description="Bullshit filter + Telegram notifications for Charles Dana",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=config.api_host, port=config.api_port, reload=True)
