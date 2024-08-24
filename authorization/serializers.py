from serpy import Serializer
from pydantic import BaseModel, field_validator
import regex

class Token(BaseModel):
    verified: bool
    version: str
    username: str

    @field_validator('version')
    def validate_version(cls, value):
        if regex.search(r"(\d+(\.)?)(?R)?", value) is not None:
            return value
        raise Exception("token version number must be of form x.y.z.w...")
