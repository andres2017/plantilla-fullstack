from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from .base import BaseDocument

Role = Literal["admin", "usuario"]


class UserRegister(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(BaseDocument):
    email: EmailStr
    name: str
    role: Role = "usuario"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserInDB(User):
    password_hash: str
