import os
import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.parser import parse_python_file
from app.models import Repo, RepoFile, Symbol

from app.database import get_db
from app.models import Repo, RepoFile

from app.embedder import embed_symbols

from app.docgen import generate_readme

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

    result = await db.execute(
        select(Symbol, RepoFile.path)
        .join(RepoFile, Symbol.file_id == RepoFile.id)
        .where(Symbol.repo_id == repo_id)
        .limit(10)
    )
    rows = result.all()

    symbols_for_embedding = [
        {
            "id": str(row.Symbol.id),
            "name": row.Symbol.name,
            "kind": row.Symbol.kind,
            "signature": row.Symbol.signature,
            "docstring": row.Symbol.docstring,
            "raw_source": row.Symbol.raw_source,
            "file_path": row.path,
            "start_line": row.Symbol.start_line,
            "end_line": row.Symbol.end_line,
        }
        for row in rows
    ]

    embedded_count = await embed_symbols(symbols_for_embedding, str(repo.id))
    repo.status = "ready"
    await db.commit()

    return {
        "id": str(repo.id),
        "name": repo.name,
        "status": repo.status,
        "files_found": len(files_found),
        "symbols_found": len(symbols_for_embedding),
        "symbols_embedded": embedded_count,
    }


@router.get("/repos")
async def list_repos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Repo))
    repos = result.scalars().all()
    return [
        {"id": str(r.id), "name": r.name, "status": r.status}
        for r in repos
    ]

@router.get("/repos/{repo_id}/search")
async def search_repo(
    repo_id: str,
    query: str,
    db: AsyncSession = Depends(get_db),
):
    from app.embedder import get_embedding, get_qdrant_client, COLLECTION_NAME

    # embed the search query
    query_vector = await get_embedding(query)

    # search qdrant
    client = get_qdrant_client()
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        query_filter={
            "must": [{"key": "repo_id", "match": {"value": repo_id}}]
        },
        limit=5,
    )

    return [
        {
            "name": r.payload["name"],
            "kind": r.payload["kind"],
            "file_path": r.payload["file_path"],
            "start_line": r.payload["start_line"],
            "signature": r.payload["signature"],
            "score": round(r.score, 4),
        }
        for r in results
    ]

@router.post("/repos/{repo_id}/readme")
async def generate_repo_readme(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
):
    # get repo
    result = await db.execute(select(Repo).where(Repo.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")

    # get all symbols
    result = await db.execute(
        select(Symbol, RepoFile.path)
        .join(RepoFile, Symbol.file_id == RepoFile.id)
        .where(Symbol.repo_id == repo_id)
    )
    rows = result.all()

    symbols = [
        {
            "name": row.Symbol.name,
            "kind": row.Symbol.kind,
            "signature": row.Symbol.signature,
            "docstring": row.Symbol.docstring,
            "file_path": row.path,
        }
        for row in rows
    ]

    readme = await generate_readme(repo.name, symbols)

    return {"readme": readme}