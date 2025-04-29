import os
import httpx

from dotenv import load_dotenv

load_dotenv()

EXTERNAL_URL = os.getenv("EXTERNAL_URL")


def forward_data(data: dict):
    response = httpx.post(EXTERNAL_URL, json=data)
    response.raise_for_status()
