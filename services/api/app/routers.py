from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database import get_db
from app.models import Repo

router = APIRouter()


@router.post("/repos/ingest")
async def ingest_repo(
    folder_path: str,
    db: AsyncSession = Depends(get_db),
):
    repo = Repo(
        name=folder_path.split("/")[-1],
        source="local",
        status="pending",
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    return {
        "id": str(repo.id),
        "name": repo.name,
        "status": repo.status,
    }


@router.get("/repos")
async def list_repos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Repo))
    repos = result.scalars().all()
    return [
        {"id": str(r.id), "name": r.name, "status": r.status}
        for r in repos
    ]