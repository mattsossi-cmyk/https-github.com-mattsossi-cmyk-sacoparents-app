"""FastAPI entrypoint for SA Coparents Relational Mediation Prep App."""
import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, Response
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from auth import router as auth_router  # noqa: E402
from mediation_routes import router as mediation_router  # noqa: E402
from analytics_routes import router as analytics_router  # noqa: E402
from journal_routes import router as journal_router  # noqa: E402
from mediator_routes import router as mediator_router  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SA Coparents Mediation Prep API")

# Mongo — keep connection limits modest so production Atlas free-tier (max ~500
# concurrent conns) is never exhausted. maxPoolSize defaults to 100 per client
# which combined with multiple pod replicas can blow past Atlas limits.
mongo_client = AsyncIOMotorClient(
    os.environ["MONGO_URL"],
    maxPoolSize=20,
    minPoolSize=1,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
    socketTimeoutMS=20000,
    retryWrites=True,
)
app.state.db = mongo_client[os.environ["DB_NAME"]]

# Routers under /api
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"app": "sa-coparents", "status": "ok"}


@api_router.get("/health")
async def health():
    """Lightweight liveness probe — must NOT touch the database so Kubernetes
    keeps the pod alive even during transient DB hiccups."""
    return {"status": "ok"}


@api_router.get("/ready")
async def ready(response: Response):
    """Readiness probe — runs a cheap Mongo ping with a tight timeout.
    Returns 503 if the pod cannot reach MongoDB so k8s removes it from
    the service endpoints and stops routing traffic to it. This is what
    prevents the 'one bad replica leaks 502s' production pattern."""
    if app.state.db is None:
        response.status_code = 503
        return {"status": "db-not-ready"}
    try:
        # 1.5s budget — fast enough to not block the probe, slow enough
        # to ride out transient blips without flapping.
        await asyncio.wait_for(app.state.db.command("ping"), timeout=1.5)
    except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
        logger.warning("Readiness probe DB ping failed: %s", exc)
        response.status_code = 503
        return {"status": "db-unreachable"}
    return {"status": "ready"}


api_router.include_router(auth_router)
api_router.include_router(mediation_router)
api_router.include_router(analytics_router)
api_router.include_router(journal_router)
api_router.include_router(mediator_router)
app.include_router(api_router)

# CORS — allow credentials for cookie-based auth.
#
# Browsers (per CORS spec) reject `Access-Control-Allow-Origin: *` when the
# request has credentials. To support cookie-based auth across BOTH same-origin
# production deploys AND cross-origin preview/mobile clients, we use
# `allow_origin_regex` whenever CORS_ORIGINS is "*". The regex reflects the
# request's Origin header back as ACAO, which IS allowed with credentials.
cors_origins_raw = os.environ.get("CORS_ORIGINS", "*")
cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]
if "*" in cors_origins:
    # Permissive: any origin, credentials enabled (Origin reflected per-request).
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origin_regex=".*",
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Explicit whitelist.
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("startup")
async def startup_log():
    logger.info("SA Coparents backend ready. DB=%s", os.environ.get("DB_NAME"))


@app.on_event("shutdown")
async def shutdown_db_client():
    mongo_client.close()
