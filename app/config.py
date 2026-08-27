import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_UPLOAD_DIR = BASE_DIR / "uploads"


def get_database_url() -> str:
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://airbnb_user:changeme@localhost:5432/airbnb_menage",
    )
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


def get_cors_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:8001,http://localhost:8000")
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


def get_upload_dir() -> Path:
    return Path(os.getenv("UPLOAD_DIR", str(DEFAULT_UPLOAD_DIR))).resolve()
