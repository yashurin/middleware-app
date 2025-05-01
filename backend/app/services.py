import httpx


async def forward_data(data: dict, url: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        response.raise_for_status()
