import httpx

EXTERNAL_URL = "https://httpbin.org/post"


def forward_data(data: dict):
    response = httpx.post(EXTERNAL_URL, json=data)
    response.raise_for_status()
