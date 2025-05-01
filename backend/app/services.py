import httpx
from app.config import get_settings

settings = get_settings()


async def forward_data(data: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(settings.EXTERNAL_URL, json=data)
        response.raise_for_status()
