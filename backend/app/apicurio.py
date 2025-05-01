import httpx
from async_lru import alru_cache
from app.config import get_settings

settings = get_settings()


async def register_schema(name: str, schema: dict):
    url = f"{settings.APICURIO_URL}/groups/default/artifacts"
    headers = {
        "X-Registry-ArtifactId": name,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=schema)
        response.raise_for_status()
        return response.json()


@alru_cache(maxsize=32)
async def get_schema_by_name(name: str):
    url = f"{settings.APICURIO_URL}/groups/default/artifacts/{name}"
    headers = {
        "Accept": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 404:
            raise httpx.HTTPStatusError("Schema not found", request=response.request, response=response)
        response.raise_for_status()
        try:
            return response.json()
        except Exception:
            return {"raw_schema": response.text}
