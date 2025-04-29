from sqlalchemy import Column, Integer, String
from .database import Base


class DataModel(Base):
    __tablename__ = "data"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(100))
    message = Column(String(250))
