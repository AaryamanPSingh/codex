import os
import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Repo, RepoFile

router = APIRouter()


@router.post("/repos/ingest")
async def ingest_repo(
    folder_path: str,
    db: AsyncSession = Depends(get_db),
):
    # check folder exists
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=400, detail="Folder not found")

    # save repo record
    repo = Repo(
        name=folder_path.split("/")[-1],
        source="local",
        status="indexing",
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    # walk the folder and find python files
    files_found = []
    for root, dirs, files in os.walk(folder_path):
        # skip junk folders
        dirs[:] = [d for d in dirs if d not in {
            "__pycache__", ".git", ".venv", "venv", "node_modules"
        }]
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, folder_path)

                # hash the file content
                content = open(full_path, "rb").read()
                content_hash = hashlib.sha256(content).hexdigest()

                repo_file = RepoFile(
                    repo_id=repo.id,
                    path=relative_path,
                    language="python",
                    content_hash=content_hash,
                )
                db.add(repo_file)
                files_found.append(relative_path)

    # update repo status
    repo.status = "parsed"
    await db.commit()

    return {
        "id": str(repo.id),
        "name": repo.name,
        "status": repo.status,
        "files_found": len(files_found),
        "files": files_found,
    }


@router.get("/repos")
async def list_repos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Repo))
    repos = result.scalars().all()
    return [
        {"id": str(r.id), "name": r.name, "status": r.status}
        for r in repos
    ]