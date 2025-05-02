import time

import httpx
from app.apicurio import get_schema_by_name, register_schema
from app.config import get_settings
from app.crud import DataRepository
from app.database import Base, engine, get_db
from app.log import logger
from app.models import DataModel, record_to_dict
from app.schema_registry import SCHEMA_REGISTRY
from app.schemas import SchemaRequest
from app.services import forward_data, process_file
from fastapi import (
    Body,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Path,
    Query,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from jsonschema import ValidationError, validate
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can narrow this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def main_endpoint():
    return {"message": "Hello World!"}


@app.post("/schemas")
async def add_schema(schema_req: SchemaRequest):
    if schema_req.name not in settings.SCHEMAS:
        raise HTTPException(
            status_code=400, detail=f"Schema name '{schema_req.name}' is not allowed."
        )

    if schema_req.schema_type.upper() != "JSON":
        raise HTTPException(status_code=400, detail="Only JSON schemas are supported.")
    try:
        result = await register_schema(name=schema_req.name, schema=schema_req.schema)
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
        raise HTTPException(
            status_code=500, detail="Error fetching schema from Apicurio."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/data/{schema_name}")
async def receive_data(
    schema_name: str = Path(..., description="Name of the schema to validate against"),
    payload: dict = Body(..., description="Raw JSON payload"),
    db: AsyncSession = Depends(get_db),
):
    try:
        schema = await get_schema_by_name(schema_name)
        validate(instance=payload, schema=schema)
    except httpx.HTTPStatusError as http_err:
        if http_err.response.status_code == 404:
            raise HTTPException(
                status_code=404, detail=f"Schema '{schema_name}' not found"
            )
        raise HTTPException(status_code=502, detail=f"Schema fetch error: {http_err}")
    except ValidationError as ve:
        raise HTTPException(
            status_code=422, detail=f"Schema validation error: {ve.message}"
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Unexpected schema error: {e}")

    schema_config = SCHEMA_REGISTRY.get(schema_name)
    if not schema_config:
        raise HTTPException(
            status_code=400, detail=f"No config found for schema '{schema_name}'"
        )

    try:
        logger.info(payload)
        transformed_data = schema_config["transform"](payload)
        logger.info(transformed_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data transformation failed: {e}")

    repo = DataRepository(db)
    try:
        db_item = await repo.create(
            {
                "schema_name": schema_name,
                "raw_data": payload,
                "transformed_data": transformed_data,
                "forwarded_to": schema_config["destination_url"],
            },
            refresh_fields=["id"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    try:
        await forward_data(transformed_data, schema_config["destination_url"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to forward data: {e}")

    return {"message": "Data received, validated, stored, and forwarded successfully."}


@app.post("/upload/{schema_name}")
async def upload_file(
    schema_name: str = Path(..., description="Name of the schema to validate against"),
    file: UploadFile = File(..., description="CSV or XML file"),
    db: AsyncSession = Depends(get_db),
):
    try:
        schema = await get_schema_by_name(schema_name)
    except httpx.HTTPStatusError as http_err:
        if http_err.response.status_code == 404:
            raise HTTPException(
                status_code=404, detail=f"Schema '{schema_name}' not found"
            )
        raise HTTPException(status_code=502, detail=f"Schema fetch error: {http_err}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Unexpected schema error: {e}")

    schema_config = SCHEMA_REGISTRY.get(schema_name)

    if not schema_config:
        raise HTTPException(
            status_code=400, detail=f"No config found for schema '{schema_name}'"
        )

    contents = await file.read()
    try:
        records = await process_file(file.filename, contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")

    repo = DataRepository(db)
    results = []
    validation_errors = []
    errors = []

    for record in records:
        try:
            validate(instance=record, schema=schema)
            transformed_data = schema_config["transform"](record)
            db_item = await repo.create(
                {
                    "schema_name": schema_name,
                    "raw_data": record,
                    "transformed_data": transformed_data,
                    "forwarded_to": schema_config["destination_url"],
                },
                refresh_fields=["id"],
            )
            await forward_data(transformed_data, schema_config["destination_url"])
            results.append({"id": db_item.id, "status": "success"})
        except ValidationError as ve:
            validation_errors.append(
                {"record": record, "status": "validation error", "detail": ve.message}
            )
        except Exception as e:
            errors.append({"record": record, "status": "error", "detail": str(e)})

    num_validation_errors = len(validation_errors)
    if num_validation_errors != 0:
        logger.warning(f"Validation errors: {validation_errors}")
    num_errors = len(errors)
    if num_errors != 0:
        logger.warning(f"Other errors: {errors}")
    if len(results) == 0:
        raise HTTPException(
            status_code=400,
            detail=f"File records could not be processed. Validation errors: {num_validation_errors}. Other errors: {num_errors}",
        )
    if num_validation_errors != 0 or num_errors != 0:
        return {
            "message": f"Some file records could not be processed. Validation errors: {num_validation_errors}. Other errors: {num_errors}",
            "results": results,
        }

    return {"message": "All file records successfully processed", "results": results}


@app.get("/records")
async def get_records_by_schema(
    schema_name: str = Query(..., description="Schema name to filter records by"),
    limit: int = Query(10, ge=1, le=100, description="Max records to return (1–100)"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: AsyncSession = Depends(get_db),
):
    repo = DataRepository(db)
    try:
        records = await repo.get_many_by_schema(schema_name, limit, offset)

        return [record_to_dict(record) for record in records]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


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
