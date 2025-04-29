from fastapi import FastAPI, HTTPException, Depends
#from sqlalchemy.orm import Session
#from .database import get_db, engine, Base
from .models import DataModel
from .schemas import InputData
from .services import forward_data
from app.log import logger

app = FastAPI()

# Create tables
#Base.metadata.create_all(bind=engine)

@app.get("/")
def main_endpoint():
    print('PRINTING')
    logger.info("WE ARE HERE")
    return {"message": "Hello World!"}


# @app.post("/data")
# def receive_data(payload: InputData, db: Session = Depends(get_db)):
#     # Placeholder for schema transformation (e.g., via Apicurio)
#     transformed_data = payload.dict()  # For now, just use as-is
#
#     # Store to DB
#     db_item = DataModel(**transformed_data)
#     db.add(db_item)
#     db.commit()
#     db.refresh(db_item)
#
#     # Forward to external URL (placeholder logic)
#     try:
#         forward_data(transformed_data)
#     except Exception as e:
#         raise HTTPException(status_code=502, detail=f"Failed to forward data: {e}")
#
#     return {"message": "Data received, stored, and forwarded successfully."}
