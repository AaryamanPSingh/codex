import httpx

OLLAMA_URL = "http://ollama:11434"


async def generate_readme(repo_name: str, symbols: list[dict]) -> str:
    # build context from symbols
    context = ""
    for sym in symbols:
        context += f"{sym['kind']}: {sym['name']}\n"
        if sym.get("signature"):
            context += f"  signature: {sym['signature']}\n"
        if sym.get("docstring"):
            context += f"  docstring: {sym['docstring']}\n"
        context += "\n"

    prompt = f"""You are a technical documentation expert.
Generate a README.md for a software project called '{repo_name}'.

Here are the functions and classes found in the codebase:

{context}

Generate a comprehensive README.md with these sections:
1. Project name and description
2. Architecture overview based on the code structure
3. Key components and what they do
4. Installation and usage

Only include information grounded in the provided code.
Write in Markdown format."""

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": "mistral",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.2,
                }
            }
        )
        response.raise_for_status()
        return response.json()["message"]["content"]