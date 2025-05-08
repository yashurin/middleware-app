from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()


class Record(BaseModel):
    name: str
    email: str
    message: str


@app.get("/records", response_model=List[Record])
async def get_records():
    sample_data = [
        Record(name="Bob", email="bob@example.com", message="Hello Bob"),
        Record(name="Alice", email="alice@example.com", message="Hello Alice"),
        Record(name="Charlie", email="charlie@example.com", message="Hello Charlie"),
    ]
    return sample_data


@app.get("/status")
async def status():
    return {"message": "Backend 2 is running"}
