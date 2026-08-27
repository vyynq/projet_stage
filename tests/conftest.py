import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_airbnb_menage.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["FIELD_ENCRYPTION_KEY"] = "test-field-encryption-key"
os.environ["UPLOAD_DIR"] = str(Path("test_uploads").resolve())
os.environ["LOGIN_WINDOW_SECONDS"] = "60"
os.environ["LOGIN_MAX_ATTEMPTS"] = "5"

from app.database import Base, engine
from app.main import app
from app.security import _login_attempts


@pytest.fixture(autouse=True)
def base_de_donnees_propre():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _login_attempts.clear()

    upload_dir = Path(os.environ["UPLOAD_DIR"])
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    yield

    Base.metadata.drop_all(bind=engine)
    _login_attempts.clear()


@pytest.fixture
def client():
    return TestClient(app)


def entetes_auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers():
    return entetes_auth


@pytest.fixture
def inscrire(client):
    def _inscrire(email: str, role: str, password: str = "motdepasse123"):
        return client.post(
            "/auth/register",
            json={"email": email, "password": password, "role": role},
        )

    return _inscrire


@pytest.fixture
def connecter(client):
    def _connecter(email: str, password: str = "motdepasse123") -> str:
        response = client.post(
            "/auth/login",
            data={"username": email, "password": password},
        )
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    return _connecter


@pytest.fixture
def creer_admin(inscrire, connecter):
    def _creer_admin(email: str = "admin@test.com") -> tuple[dict, str]:
        response = inscrire(email, "admin")
        assert response.status_code == 201, response.text
        return response.json(), connecter(email)

    return _creer_admin


@pytest.fixture
def creer_utilisateur(client, auth_headers):
    def _creer_utilisateur(admin_token: str, email: str, role: str, password: str = "motdepasse123") -> dict:
        response = client.post(
            "/auth/users",
            headers=auth_headers(admin_token),
            json={"email": email, "password": password, "role": role},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _creer_utilisateur


@pytest.fixture
def creer_logement(client, auth_headers):
    def _creer_logement(token: str, adresse: str = "12 rue de la Paix, Paris", code_acces: str = "4821") -> dict:
        response = client.post(
            "/logements",
            headers=auth_headers(token),
            json={"adresse": adresse, "code_acces": code_acces},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _creer_logement


@pytest.fixture
def creer_reservation(client, auth_headers):
    def _creer_reservation(token: str, logement_id: str, voyageur_nom: str = "Camille Martin") -> dict:
        response = client.post(
            "/reservations",
            headers=auth_headers(token),
            json={
                "logement_id": logement_id,
                "date_arrivee": "2026-07-10T15:00:00",
                "date_depart": "2026-07-12T11:00:00",
                "voyageur_nom": voyageur_nom,
                "voyageur_contact": "camille@example.com",
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _creer_reservation


@pytest.fixture
def mission_assignee(client, auth_headers, creer_admin, creer_utilisateur, connecter, creer_logement, creer_reservation):
    admin, admin_token = creer_admin()
    proprietaire = creer_utilisateur(admin_token, "proprietaire@test.com", "proprietaire")
    agent = creer_utilisateur(admin_token, "agent@test.com", "agent_menage")
    autre_agent = creer_utilisateur(admin_token, "autre-agent@test.com", "agent_menage")

    proprietaire_token = connecter("proprietaire@test.com")
    agent_token = connecter("agent@test.com")
    autre_agent_token = connecter("autre-agent@test.com")

    logement = creer_logement(proprietaire_token)
    reservation = creer_reservation(proprietaire_token, logement["id"])

    missions_response = client.get("/missions", headers=auth_headers(proprietaire_token))
    assert missions_response.status_code == 200, missions_response.text
    mission = missions_response.json()[0]

    assign_response = client.patch(
        f"/missions/{mission['id']}/assign",
        headers=auth_headers(admin_token),
        json={"agent_id": agent["id"]},
    )
    assert assign_response.status_code == 200, assign_response.text

    return {
        "admin": admin,
        "admin_token": admin_token,
        "proprietaire": proprietaire,
        "proprietaire_token": proprietaire_token,
        "agent": agent,
        "agent_token": agent_token,
        "autre_agent": autre_agent,
        "autre_agent_token": autre_agent_token,
        "logement": logement,
        "reservation": reservation,
        "mission": assign_response.json(),
    }
