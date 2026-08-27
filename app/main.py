from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, get_cors_origins, get_upload_dir
from app.database import Base, engine
from app.routers import auth, dashboard, logements, missions, reservations

STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = get_upload_dir()

# En dev : cree les tables directement depuis les modeles.
# En prod : remplacer par des migrations Alembic (alembic upgrade head).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Airbnb Menage API",
    description="API de gestion de logements courte duree, reservations et missions de menage",
    version="0.1.0",
)

# CORS : restreindre a l'origine exacte du frontend en prod, jamais "*" avec des credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(logements.router)
app.include_router(reservations.router)
app.include_router(missions.router)
app.include_router(dashboard.router)

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


@app.get("/health")
def health_check():
    return {"status": "ok"}


if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
