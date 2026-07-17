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

ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
USER_EMAIL = os.environ["USER_EMAIL"]
USER_PASSWORD = os.environ["USER_PASSWORD"]

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 7
