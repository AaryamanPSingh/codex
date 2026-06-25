from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base
from app.models import Repo, RepoFile, Symbol
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
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")