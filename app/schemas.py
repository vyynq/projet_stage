from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.models import RoleEnum, MissionStatusEnum


# ---------- Users / Auth ----------

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: RoleEnum


class UserOut(BaseModel):
    id: str
    email: EmailStr
    role: RoleEnum

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Logements ----------

class LogementCreate(BaseModel):
    adresse: str = Field(min_length=3, max_length=255)
    code_acces: str | None = Field(default=None, max_length=50)


class LogementUpdate(BaseModel):
    adresse: str | None = Field(default=None, min_length=3, max_length=255)
    code_acces: str | None = Field(default=None, max_length=50)
    statut: str | None = Field(default=None, max_length=50)


class LogementOut(BaseModel):
    id: str
    adresse: str
    statut: str
    proprietaire_id: str

    class Config:
        from_attributes = True


class CodeAccesOut(BaseModel):
    logement_id: str
    code_acces: str | None


# ---------- Reservations ----------

class ReservationCreate(BaseModel):
    logement_id: str
    date_arrivee: datetime
    date_depart: datetime
    voyageur_nom: str = Field(min_length=1, max_length=255)
    voyageur_contact: str | None = Field(default=None, max_length=255)
    source: str = Field(default="manuel", max_length=80)
    external_id: str | None = Field(default=None, max_length=255)


class ReservationUpdate(BaseModel):
    date_arrivee: datetime | None = None
    date_depart: datetime | None = None
    voyageur_nom: str | None = Field(default=None, min_length=1, max_length=255)
    voyageur_contact: str | None = Field(default=None, max_length=255)


class ReservationOut(BaseModel):
    id: str
    logement_id: str
    date_arrivee: datetime
    date_depart: datetime
    voyageur_nom: str
    voyageur_contact: str | None
    source: str
    external_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Missions ----------

class MissionOut(BaseModel):
    id: str
    logement_id: str
    reservation_id: str | None
    agent_id: str | None
    statut: MissionStatusEnum
    date_prevue: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class MissionAssign(BaseModel):
    agent_id: str


class MissionStatusUpdate(BaseModel):
    statut: MissionStatusEnum


class ChecklistItemCreate(BaseModel):
    libelle: str = Field(min_length=1, max_length=255)


class ChecklistItemUpdate(BaseModel):
    libelle: str | None = Field(default=None, min_length=1, max_length=255)
    coche: bool | None = None


class ChecklistItemOut(BaseModel):
    id: str
    mission_id: str
    libelle: str
    coche: bool

    class Config:
        from_attributes = True


class IncidentCreate(BaseModel):
    description: str = Field(min_length=3, max_length=2000)
    photo_url: str | None = Field(default=None, max_length=500)


class IncidentOut(BaseModel):
    id: str
    mission_id: str
    description: str
    photo_url: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardOut(BaseModel):
    logements: int
    reservations: int
    missions_a_faire: int
    missions_en_cours: int
    missions_terminees: int
    incidents: int
