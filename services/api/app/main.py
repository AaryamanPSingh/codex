from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine, Base
from app.models import Repo

from app.routers import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="CodeX API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "ok"}