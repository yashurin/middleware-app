import httpx
from app.config import EXTERNAL_URL


async def forward_data(data: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(EXTERNAL_URL, json=data)
        response.raise_for_status()
