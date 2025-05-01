from app.database import Base
from sqlalchemy import JSON, Column, DateTime, Integer, String, func


class DataModel(Base):
    __tablename__ = "data"

    id = Column(Integer, primary_key=True, index=True)
    schema_name = Column(String(100), nullable=False)
    raw_data = Column(JSON, nullable=False)
    transformed_data = Column(JSON, nullable=False)
    forwarded_to = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def record_to_dict(record: DataModel) -> dict:
    return {
        "id": record.id,
        "schema_name": record.schema_name,
        "raw_data": record.raw_data,
        "transformed_data": record.transformed_data,
        "forwarded_to": record.forwarded_to,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
