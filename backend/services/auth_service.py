from datetime import datetime, timezone, timedelta

from fastapi import HTTPException

from core.database import db
from core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from models.user import UserRegister, UserInDB
from repositories import user_repository

MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _public(user: UserInDB) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


async def _issue_tokens(user: UserInDB) -> tuple[str, str]:
    access = create_access_token(user.id, user.email, user.role)
    refresh, jti, expires_at = create_refresh_token(user.id)
    await db.refresh_tokens.insert_one({"jti": jti, "user_id": user.id, "expires_at": expires_at})
    return access, refresh


async def register(data: UserRegister) -> tuple[dict, str, str]:
    email = data.email.lower().strip()
    if await user_repository.find_by_email(email):
        raise HTTPException(status_code=409, detail="El email ya esta registrado")
    user = UserInDB(email=email, name=data.name.strip(), role="usuario",
                    password_hash=hash_password(data.password))
    user.id = await user_repository.insert(user)
    access, refresh = await _issue_tokens(user)
    return _public(user), access, refresh


async def login(email: str, password: str, ip: str) -> tuple[dict, str, str]:
    email = email.lower().strip()
    identifier = email
    await _check_lockout(identifier)
    user = await user_repository.find_by_email(email)
    if not user or not verify_password(password, user.password_hash):
        await _record_failure(identifier)
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    await db.login_attempts.delete_many({"identifier": identifier})
    access, refresh = await _issue_tokens(user)
    return _public(user), access, refresh


async def refresh_tokens(refresh_token: str) -> tuple[str, str]:
    payload = decode_token(refresh_token, "refresh")
    stored = await db.refresh_tokens.find_one_and_delete({"jti": payload["jti"]})
    if not stored:
        await db.refresh_tokens.delete_many({"user_id": payload["sub"]})
        raise HTTPException(status_code=401, detail="Refresh token invalido o reutilizado")
    user = await user_repository.find_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return await _issue_tokens(user)


async def logout(refresh_token: str | None):
    if not refresh_token:
        return
    try:
        payload = decode_token(refresh_token, "refresh")
        await db.refresh_tokens.delete_one({"jti": payload["jti"]})
    except HTTPException:
        pass


async def _check_lockout(identifier: str):
    since = datetime.now(timezone.utc) - timedelta(minutes=LOCKOUT_MINUTES)
    count = await db.login_attempts.count_documents(
        {"identifier": identifier, "created_at": {"$gte": since}})
    if count >= MAX_ATTEMPTS:
        raise HTTPException(status_code=429,
                            detail=f"Demasiados intentos fallidos. Intenta en {LOCKOUT_MINUTES} minutos")


async def _record_failure(identifier: str):
    await db.login_attempts.insert_one(
        {"identifier": identifier, "created_at": datetime.now(timezone.utc)})
