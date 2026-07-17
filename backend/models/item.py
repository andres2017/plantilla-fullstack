# Entidad de referencia: copia este archivo (y su repository/service/router)
# para crear una nueva entidad de negocio. Pasos:
#   1. models/<entidad>.py     -> este archivo: documento + payloads de entrada
#   2. repositories/<entidad>_repository.py -> acceso crudo a Mongo
#   3. services/<entidad>_service.py        -> reglas de negocio
#   4. routers/<entidad>.py                 -> endpoints HTTP (/api/<entidad>)
#   5. registrar el router nuevo en server.py (app.include_router(...))
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from .base import BaseDocument


class Item(BaseDocument):
    name: str
    description: Optional[str] = None
    active: bool = True
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ItemCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    active: bool = True


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    active: Optional[bool] = None
