from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginSchema(BaseModel):
    email: str
    password: str


class TokenSchema(BaseModel):
    access_token: str
    token_type: str


class TokenDataSchema(BaseModel):
    email: str | None = None


class UserSchema(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRegisterSchema(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
