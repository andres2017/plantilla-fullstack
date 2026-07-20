from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from core.config import (
    APP_NAME, CORS_ORIGINS, CORS_ORIGIN_REGEX, COOKIE_SECURE,
    ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD,
)
from core.database import client, create_indexes, db
from core.responses import error_response, success_response
from core.security import hash_password, verify_password
from routers import auth, items

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(APP_NAME.lower().replace(" ", "-"))


async def seed_users():
    seeds = [
        {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "name": "Admin", "role": "admin"},
        {"email": USER_EMAIL, "password": USER_PASSWORD, "name": "Usuario Demo", "role": "usuario"},
    ]
    from datetime import datetime, timezone
    for seed in seeds:
        existing = await db.users.find_one({"email": seed["email"]})
        if existing is None:
            await db.users.insert_one({
                "email": seed["email"], "name": seed["name"], "role": seed["role"],
                "password_hash": hash_password(seed["password"]),
                "created_at": datetime.now(timezone.utc),
            })
            logger.info("Usuario semilla creado: %s (%s)", seed["email"], seed["role"])
        elif not verify_password(seed["password"], existing["password_hash"]):
            await db.users.update_one({"email": seed["email"]},
                                      {"$set": {"password_hash": hash_password(seed["password"])}})


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_indexes()
    await seed_users()
    yield
    client.close()


app = FastAPI(title=f"{APP_NAME} API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content=error_response(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = "; ".join(
        f"{'.'.join(str(loc) for loc in err['loc'][1:])}: {err['msg']}" for err in exc.errors())
    return JSONResponse(status_code=422, content=error_response(messages))


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/auth"):
        response.headers["Cache-Control"] = "no-store"
    if COOKIE_SECURE:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


app.include_router(auth.router, prefix="/api")
# Plantilla de referencia: duplica routers/items.py -> services -> repositories -> models
# para cada nueva entidad de negocio. Ver docs/COMO-USAR-PLANTILLA.md.
app.include_router(items.router, prefix="/api")


@app.get("/api/health")
async def health():
    return success_response({"status": "ok", "service": f"{APP_NAME} API"})


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
