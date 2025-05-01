import time
import json
from fastapi import FastAPI, HTTPException, Depends, status, Path, Body
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DataModel
from app.database import get_db
from app.database import engine, Base
from app.schemas import SchemaRequest
from app.services import forward_data
from app.log import logger
from app.apicurio import get_schema_by_name, register_schema
from jsonschema import validate, ValidationError
from app.schema_registry import SCHEMA_REGISTRY

from app.config import get_settings

settings = get_settings()


app = FastAPI()


@app.get("/")
def main_endpoint():
    return {"message": "Hello World!"}


@app.post("/schemas")
async def add_schema(schema_req: SchemaRequest):
    if schema_req.name not in settings.SCHEMAS:
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


@app.post("/data/{schema_name}")
async def receive_data(
    schema_name: str = Path(..., description="Name of the schema to validate against"),
    payload: dict = Body(..., description="Raw JSON payload"),
    db: AsyncSession = Depends(get_db)
):
    try:
        schema = await get_schema_by_name(schema_name)
        validate(instance=payload, schema=schema)
    except httpx.HTTPStatusError as http_err:
        if http_err.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Schema '{schema_name}' not found")
        raise HTTPException(status_code=502, detail=f"Schema fetch error: {http_err}")
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=f"Schema validation error: {ve.message}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Unexpected schema error: {e}")

    schema_config = SCHEMA_REGISTRY.get(schema_name)
    if not schema_config:
        raise HTTPException(status_code=400, detail=f"No config found for schema '{schema_name}'")

    try:
        logger.info(payload)
        transformed_data = schema_config["transform"](payload)
        logger.info(transformed_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data transformation failed: {e}")

    db_item = DataModel(
        schema_name=schema_name,
        raw_data=payload,
        transformed_data=transformed_data,
        forwarded_to=schema_config["destination_url"]
    )

    try:
        db.add(db_item)
        await db.commit()
        await db.refresh(db_item, ["id"])
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    try:
        await forward_data(transformed_data, schema_config["destination_url"])
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
