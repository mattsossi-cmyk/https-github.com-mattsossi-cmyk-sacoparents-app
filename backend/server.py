"""FastAPI entrypoint for SA Coparents Relational Mediation Prep App."""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from auth import router as auth_router  # noqa: E402
from mediation_routes import router as mediation_router  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SA Coparents Mediation Prep API")

# Mongo
mongo_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
app.state.db = mongo_client[os.environ["DB_NAME"]]

# Routers under /api
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"app": "sa-coparents", "status": "ok"}


@api_router.get("/health")
async def health():
    return {"status": "ok"}


api_router.include_router(auth_router)
api_router.include_router(mediation_router)
app.include_router(api_router)

# CORS — allow credentials for cookie-based auth
cors_origins_raw = os.environ.get("CORS_ORIGINS", "*")
cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]
allow_credentials = "*" not in cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_credentials=allow_credentials,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    mongo_client.close()
