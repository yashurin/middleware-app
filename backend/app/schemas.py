from pydantic import BaseModel


class SchemaRequest(BaseModel):
    name: str
    schema: dict
    schema_type: str = "JSON"
