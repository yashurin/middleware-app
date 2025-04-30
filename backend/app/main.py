import os
import json
from fastapi import FastAPI, HTTPException, Depends
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
#from app.database import get_db, engine, Base
from sqlalchemy.orm import sessionmaker
from app.models import DataModel
from app.schemas import InputData, SchemaRequest
from app.services import forward_data
from app.log import logger
from app.apicurio import get_schema_by_name, register_schema
from jsonschema import validate, ValidationError

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base

import os
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"mysql+asyncmy://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

#Base = declarative_base()

# Create your async SQLAlchemy engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True) # future was added
#engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session

# from dotenv import load_dotenv
#
# load_dotenv()

SCHEMAS = os.getenv("SCHEMAS")

app = FastAPI()

#Base.metadata.create_all(bind=engine)

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
def main_endpoint():
    return {"message": "Hello World!"}


@app.post("/schemas")
async def add_schema(schema_req: SchemaRequest):
    schemas = json.loads(SCHEMAS)
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
        await db.refresh(db_item)
        logger.info('AFTER THE DB REFRESH')
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    try:
        logger.info('BEFORE SENDING A REQUEST')
        await forward_data(transformed_data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to forward data: {e}")

    return {"message": "Data received, validated, stored, and forwarded successfully."}


@app.on_event("startup")
async def on_startup():
    await init_models()

# @app.post("/data")
# def receive_data(payload: InputData, db: Session = Depends(get_db)):
#     try:
#         schema = get_schema_by_name("contact-message-schema")
#         validate(instance=payload.dict(), schema=schema)
#     except ValidationError as ve:
#         raise HTTPException(status_code=422, detail=f"Schema validation error: {ve.message}")
#     except Exception as e:
#         raise HTTPException(status_code=502, detail=f"Failed to load schema: {e}")
#
#     transformed_data = payload.dict()
#
#     db_item = DataModel(**transformed_data)
#     db.add(db_item)
#     db.commit()
#     db.refresh(db_item)
#
#     try:
#         forward_data(transformed_data)
#     except Exception as e:
#         raise HTTPException(status_code=502, detail=f"Failed to forward data: {e}")
#
#     return {"message": "Data received, validated, stored, and forwarded successfully."}
