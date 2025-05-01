import time
import json
from fastapi import FastAPI, HTTPException, Depends, status
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DataModel
from app.database import get_db
from app.database import engine, Base
from app.schemas import InputData, SchemaRequest
from app.services import forward_data
from app.log import logger
from app.apicurio import get_schema_by_name, register_schema
from jsonschema import validate, ValidationError

from app.config import get_settings

settings = get_settings()


app = FastAPI()


@app.get("/")
def main_endpoint():
    return {"message": "Hello World!"}


@app.post("/schemas")
async def add_schema(schema_req: SchemaRequest):
    schemas = json.loads(settings.SCHEMAS)
    if schema_req.name not in schemas:
        raise HTTPException(status_code=400, detail=f"Schema name '{schema_req.name}' is not allowed.")

    if schema_req.schema_type.upper() != "JSON":
        raise HTTPException(status_code=400, detail="Only JSON schemas are supported.")
    try:
        result = await register_schema(
            name=schema_req.name,
            schema=schema_req.schema
        )
        return {"message": "Schema registered", "response": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/schemas/{name}")
async def fetch_schema(name: str):
    try:
        schema = await get_schema_by_name(name)
        return {"name": name, "schema": schema}
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Schema '{name}' not found.")
        raise HTTPException(status_code=500, detail="Error fetching schema from Apicurio.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/data")
async def receive_data(payload: InputData, db: AsyncSession = Depends(get_db)):
    try:
        schema = await get_schema_by_name("contact-message-schema")
        validate(instance=payload.dict(), schema=schema)
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=f"Schema validation error: {ve.message}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to load schema: {e}")

    transformed_data = payload.dict()
    db_item = DataModel(**transformed_data)

    try:
        db.add(db_item)
        await db.commit()
        await db.refresh(db_item, ["id"])  # selective refresh for better performance
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    try:
        await forward_data(transformed_data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to forward data: {e}")

    return {"message": "Data received, validated, stored, and forwarded successfully."}


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)):
    # Execute a simple query to verify the connection
    start = time.time()
    result = await db.execute(text("SELECT 1"))
    end = time.time()
    return {"status": "healthy", "db_response_time": f"{(end-start):.4f}s"}


@app.on_event("startup")
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
