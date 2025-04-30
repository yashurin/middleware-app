from pydantic import BaseModel


class InputData(BaseModel):
    name: str
    email: str
    message: str


class SchemaRequest(BaseModel):
    name: str
    schema: dict
    schema_type: str = "JSON"
