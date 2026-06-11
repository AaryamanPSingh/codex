import os
import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.parser import parse_python_file
from app.models import Repo, RepoFile, Symbol

from app.database import get_db
from app.models import Repo, RepoFile

router = APIRouter()


@router.post("/repos/ingest")
async def ingest_repo(
    folder_path: str,
    db: AsyncSession = Depends(get_db),
):
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=400, detail="Folder not found")

    repo = Repo(
        name=folder_path.split("/")[-1],
        source="local",
        status="indexing",
    )
    db.add(repo)
    await db.flush()  # get repo.id

    files_found = []
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if d not in {
            "__pycache__", ".git", ".venv", "venv", "node_modules"
        }]
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, folder_path)

                content = open(full_path, "rb").read()
                content_hash = hashlib.sha256(content).hexdigest()

                repo_file = RepoFile(
                    repo_id=repo.id,
                    path=relative_path,
                    language="python",
                    content_hash=content_hash,
                )
                db.add(repo_file)
                await db.flush()  # get repo_file.id

                source_code = open(full_path, "r", errors="replace").read()
                symbols = parse_python_file(source_code)

                for sym in symbols:
                    db.add(Symbol(
                        file_id=repo_file.id,
                        repo_id=repo.id,
                        name=sym["name"],
                        kind=sym["kind"],
                        start_line=sym["start_line"],
                        end_line=sym["end_line"],
                        signature=sym["signature"],
                        docstring=sym.get("docstring"),
                        raw_source=sym["raw_source"][:2000],
                    ))
                    for method in sym.get("methods", []):
                        db.add(Symbol(
                            file_id=repo_file.id,
                            repo_id=repo.id,
                            name=method["name"],
                            kind=method["kind"],
                            start_line=method["start_line"],
                            end_line=method["end_line"],
                            signature=method["signature"],
                            docstring=method.get("docstring"),
                            raw_source=method["raw_source"][:2000],
                        ))

                files_found.append(relative_path)

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