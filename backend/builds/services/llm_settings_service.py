"""BYOK: API key de Claude por usuario (cifrada en Mongo)."""
from __future__ import annotations

import base64
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from core.config import JWT_SECRET
from core.database import db

logger = logging.getLogger("builds.llm_settings")

COLLECTION = "user_llm_settings"

# Catálogo visible en UI (nombres reales de producto Anthropic)
MODEL_CATALOG = [
    {
        "id": "haiku",
        "name": "Haiku 4.5",
        "label_es": "Haiku 4.5",
        "label_en": "Haiku 4.5",
        "desc_es": "Más rápido · ideal para guías y cambios pequeños",
        "desc_en": "Fastest · great for guides and small edits",
        "tier": "fast",
    },
    {
        "id": "sonnet",
        "name": "Sonnet 5",
        "label_es": "Sonnet 5",
        "label_en": "Sonnet 5",
        "desc_es": "Equilibrado · recomendado para el día a día",
        "desc_en": "Balanced · recommended for daily work",
        "tier": "balanced",
    },
    {
        "id": "opus",
        "name": "Opus 4.8",
        "label_es": "Opus 4.8",
        "label_en": "Opus 4.8",
        "desc_es": "Máxima calidad · tareas difíciles / arquitectura",
        "desc_en": "Highest quality · hard tasks / architecture",
        "tier": "max",
    },
]


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _derive_key() -> bytes:
    return hashlib.sha256(f"fabrica-llm:{JWT_SECRET}".encode("utf-8")).digest()


def encrypt_api_key(plain: str) -> str:
    raw = plain.strip().encode("utf-8")
    token = _xor_bytes(raw, _derive_key())
    return base64.urlsafe_b64encode(token).decode("ascii")


def decrypt_api_key(token: str) -> str:
    data = base64.urlsafe_b64decode(token.encode("ascii"))
    return _xor_bytes(data, _derive_key()).decode("utf-8")


def mask_key(plain: str) -> str:
    k = plain.strip()
    if len(k) <= 12:
        return "****"
    return f"{k[:7]}…{k[-4:]}"


def _validate_key_format(api_key: str) -> None:
    k = api_key.strip()
    if len(k) < 20:
        raise ValueError("La API key parece demasiado corta")
    if not (k.startswith("sk-ant-") or k.startswith("sk-")):
        raise ValueError("La key debe empezar por sk-ant- (Anthropic)")


async def get_settings(user_id: str) -> Optional[dict]:
    return await db[COLLECTION].find_one({"_id": str(user_id)})


async def get_status(user_id: str) -> dict:
    from builds.config import ANTHROPIC_API_KEY, BUILDS_MODEL_MAP

    doc = await get_settings(user_id)
    user_has = bool(doc and doc.get("api_key_enc"))
    env_has = bool(ANTHROPIC_API_KEY)
    connected = user_has or env_has
    source = "user" if user_has else ("env" if env_has else None)

    models = []
    for m in MODEL_CATALOG:
        models.append({
            **m,
            "model_id": BUILDS_MODEL_MAP.get(m["id"], m["id"]),
        })

    return {
        "connected": connected,
        "mode": "agent" if connected else "stub",
        "source": source,
        "key_masked": doc.get("key_masked") if doc else None,
        "preferred_model": (doc or {}).get("preferred_model") or "sonnet",
        "models": models,
        "hint_es": (
            "Claude conectado. Los gastos de IA van a tu cuenta de Anthropic."
            if connected
            else "Pega tu API key de Anthropic para builds reales. Sin key = modo prueba."
        ),
        "hint_en": (
            "Claude connected. AI usage is billed to your Anthropic account."
            if connected
            else "Paste your Anthropic API key for real builds. Without a key = trial mode."
        ),
    }


async def save_api_key(user_id: str, api_key: str, preferred_model: str = "sonnet") -> dict:
    _validate_key_format(api_key)
    model = preferred_model if preferred_model in ("haiku", "sonnet", "opus") else "sonnet"
    plain = api_key.strip()
    now = datetime.now(timezone.utc)
    doc = {
        "_id": str(user_id),
        "api_key_enc": encrypt_api_key(plain),
        "key_masked": mask_key(plain),
        "preferred_model": model,
        "updated_at": now,
    }
    existing = await get_settings(user_id)
    if existing is None:
        doc["created_at"] = now
        await db[COLLECTION].insert_one(doc)
    else:
        await db[COLLECTION].update_one({"_id": str(user_id)}, {"$set": doc})
    return await get_status(user_id)


async def clear_api_key(user_id: str) -> dict:
    await db[COLLECTION].delete_one({"_id": str(user_id)})
    return await get_status(user_id)


async def update_preferred_model(user_id: str, preferred_model: str) -> dict:
    model = preferred_model if preferred_model in ("haiku", "sonnet", "opus") else "sonnet"
    await db[COLLECTION].update_one(
        {"_id": str(user_id)},
        {"$set": {"preferred_model": model, "updated_at": datetime.now(timezone.utc)}},
        upsert=False,
    )
    return await get_status(user_id)


async def resolve_api_key_for_user(user_id: str | None) -> str | None:
    from builds.config import ANTHROPIC_API_KEY

    if user_id:
        doc = await get_settings(str(user_id))
        if doc and doc.get("api_key_enc"):
            try:
                return decrypt_api_key(doc["api_key_enc"])
            except Exception:
                logger.exception("No se pudo descifrar key de usuario %s", user_id)
    return ANTHROPIC_API_KEY or None
