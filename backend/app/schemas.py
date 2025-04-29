from pydantic import BaseModel


class InputData(BaseModel):
    name: str
    email: str
    message: str
