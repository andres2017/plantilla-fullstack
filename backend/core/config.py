import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

# Nombre visible de la app (titulo de la API, seed de usuarios, etc).
# Bautiza tu proyecto cambiando esta variable en .env — ver README.md.
APP_NAME = os.environ.get("APP_NAME", "APP_NAME")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

# Opcional: patron regex de origenes permitidos (para previews con URL dinamica,
# ej. Vercel por rama). IMPORTANTE: anclar al proyecto/team real al usarlo, NUNCA
# algo generico como "https://.*\.vercel\.app" a secas -- eso acepta el subdominio
# de CUALQUIER proyecto de Vercel de CUALQUIER persona, lo que con cookies
# cross-site (ver COOKIE_SAMESITE abajo) abre CSRF.
CORS_ORIGIN_REGEX = os.environ.get("CORS_ORIGIN_REGEX") or None

# Cookies de auth: en local (mismo sitio, http) el default sirve tal cual.
# En despliegue real con frontend y backend en dominios distintos (ej. Vercel +
# Render), el navegador NO envia cookies SameSite=Lax en llamadas cross-site,
# asi que hay que fijar COOKIE_SAMESITE=none (lo cual exige COOKIE_SECURE=true
# por spec: SameSite=None sin Secure es rechazado por los navegadores).
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").strip().lower() == "true"
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax").strip().lower()

if COOKIE_SAMESITE not in ("strict", "lax", "none"):
    raise RuntimeError(
        f"COOKIE_SAMESITE debe ser 'strict', 'lax' o 'none' (valor actual: "
        f"'{COOKIE_SAMESITE}'). Revisa la configuracion de entorno."
    )

if COOKIE_SAMESITE == "none" and not COOKIE_SECURE:
    raise RuntimeError(
        "COOKIE_SAMESITE=none requiere COOKIE_SECURE=true (los navegadores "
        "rechazan SameSite=None sin Secure). Revisa la configuracion de entorno."
    )

ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
USER_EMAIL = os.environ["USER_EMAIL"]
USER_PASSWORD = os.environ["USER_PASSWORD"]

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 7
