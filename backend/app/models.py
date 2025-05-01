from sqlalchemy import Column, Integer, String, JSON, DateTime, func
from app.database import Base


class DataModel(Base):
    __tablename__ = "data"

    id = Column(Integer, primary_key=True, index=True)
    schema_name = Column(String(100), nullable=False)
    raw_data = Column(JSON, nullable=False)
    transformed_data = Column(JSON, nullable=False)
    forwarded_to = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
