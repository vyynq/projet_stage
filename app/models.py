import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Boolean, Enum, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class RoleEnum(str, enum.Enum):
    admin = "admin"
    proprietaire = "proprietaire"
    responsable_conciergerie = "responsable_conciergerie"
    agent_menage = "agent_menage"


class MissionStatusEnum(str, enum.Enum):
    a_faire = "a_faire"
    en_cours = "en_cours"
    termine = "termine"
    probleme_signale = "probleme_signale"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    email_verified_at = Column(DateTime, nullable=True)
    email_verification_code_hash = Column(String, nullable=True)
    email_verification_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    logements = relationship("Logement", back_populates="proprietaire")
    missions_assignees = relationship("MissionMenage", back_populates="agent")


class Logement(Base):
    __tablename__ = "logements"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    adresse = Column(String, nullable=False)
    # Le code de boite a cles est stocke chiffre applicativement (voir app/security.py)
    code_acces_chiffre = Column(String, nullable=True)
    proprietaire_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    statut = Column(String, default="pret")
    created_at = Column(DateTime, default=datetime.utcnow)

    proprietaire = relationship("User", back_populates="logements")
    reservations = relationship("Reservation", back_populates="logement", cascade="all, delete-orphan")
    missions = relationship("MissionMenage", back_populates="logement", cascade="all, delete-orphan")


class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    logement_id = Column(String(36), ForeignKey("logements.id"), nullable=False)
    date_arrivee = Column(DateTime, nullable=False)
    date_depart = Column(DateTime, nullable=False)
    voyageur_nom = Column(String, nullable=False)
    voyageur_contact = Column(String, nullable=True)
    source = Column(String, default="manuel", nullable=False)
    external_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    logement = relationship("Logement", back_populates="reservations")
    mission = relationship("MissionMenage", back_populates="reservation", uselist=False, cascade="all, delete-orphan")


class MissionMenage(Base):
    __tablename__ = "missions_menage"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    logement_id = Column(String(36), ForeignKey("logements.id"), nullable=False)
    reservation_id = Column(String(36), ForeignKey("reservations.id"), nullable=True)
    agent_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    statut = Column(Enum(MissionStatusEnum), default=MissionStatusEnum.a_faire)
    date_prevue = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    logement = relationship("Logement", back_populates="missions")
    reservation = relationship("Reservation", back_populates="mission")
    agent = relationship("User", back_populates="missions_assignees")
    checklist_items = relationship("ChecklistItem", back_populates="mission", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="mission", cascade="all, delete-orphan")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    mission_id = Column(String(36), ForeignKey("missions_menage.id"), nullable=False)
    libelle = Column(String, nullable=False)
    coche = Column(Boolean, default=False)

    mission = relationship("MissionMenage", back_populates="checklist_items")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    mission_id = Column(String(36), ForeignKey("missions_menage.id"), nullable=False)
    description = Column(Text, nullable=False)
    photo_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    mission = relationship("MissionMenage", back_populates="incidents")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)          # ex: "CONSULT_CODE_ACCES", "UPDATE_MISSION_STATUS"
    ressource = Column(String, nullable=False)        # ex: "logement:1234", "mission:5678"
    created_at = Column(DateTime, default=datetime.utcnow)
