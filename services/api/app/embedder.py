import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

COLLECTION_NAME = "codex_symbols"
VECTOR_DIM = 768
OLLAMA_URL = "http://ollama:11434"


def get_qdrant_client():
    return QdrantClient(host="qdrant", port=6333)


def ensure_collection(client: QdrantClient):
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_DIM,
                distance=Distance.COSINE,
            ),
        )


async def get_embedding(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={
                "model": "nomic-embed-text",
                "prompt": text,
            },
        )
        response.raise_for_status()
        return response.json()["embedding"]


async def embed_symbols(symbols: list[dict], repo_id: str):
    client = get_qdrant_client()
    ensure_collection(client)

    points = []
    for sym in symbols:
        # build a rich text representation of the symbol
        text = f"{sym['kind']}: {sym['name']}\n"
        if sym.get("signature"):
            text += f"signature: {sym['signature']}\n"
        if sym.get("docstring"):
            text += f"docstring: {sym['docstring']}\n"
        if sym.get("raw_source"):
            text += f"source:\n{sym['raw_source'][:500]}"

        embedding = await get_embedding(text)

        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "symbol_id": sym["id"],
                "repo_id": repo_id,
                "name": sym["name"],
                "kind": sym["kind"],
                "signature": sym.get("signature"),
                "file_path": sym.get("file_path"),
                "start_line": sym.get("start_line"),
                "end_line": sym.get("end_line"),
            }
        ))

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    return len(points)