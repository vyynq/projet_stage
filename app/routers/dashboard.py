from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models import Incident, Logement, MissionMenage, MissionStatusEnum, Reservation, RoleEnum, User
from app.schemas import DashboardOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == RoleEnum.agent_menage:
        missions_query = db.query(MissionMenage).filter(MissionMenage.agent_id == current_user.id)
        return DashboardOut(
            logements=0,
            reservations=0,
            missions_a_faire=missions_query.filter(MissionMenage.statut == MissionStatusEnum.a_faire).count(),
            missions_en_cours=missions_query.filter(MissionMenage.statut == MissionStatusEnum.en_cours).count(),
            missions_terminees=missions_query.filter(MissionMenage.statut == MissionStatusEnum.termine).count(),
            incidents=(
                db.query(Incident)
                .join(MissionMenage)
                .filter(MissionMenage.agent_id == current_user.id)
                .count()
            ),
        )

    logements_query = db.query(Logement)
    reservations_query = db.query(Reservation)
    missions_query = db.query(MissionMenage)
    incidents_query = db.query(Incident)

    if current_user.role == RoleEnum.proprietaire:
        logements_query = logements_query.filter(Logement.proprietaire_id == current_user.id)
        reservations_query = reservations_query.join(Logement).filter(Logement.proprietaire_id == current_user.id)
        missions_query = missions_query.join(Logement).filter(Logement.proprietaire_id == current_user.id)
        incidents_query = incidents_query.join(MissionMenage).join(Logement).filter(
            Logement.proprietaire_id == current_user.id
        )
    elif current_user.role not in {RoleEnum.admin, RoleEnum.responsable_conciergerie}:
        raise HTTPException(status_code=403, detail="Acces refuse")

    return DashboardOut(
        logements=logements_query.count(),
        reservations=reservations_query.count(),
        missions_a_faire=missions_query.filter(MissionMenage.statut == MissionStatusEnum.a_faire).count(),
        missions_en_cours=missions_query.filter(MissionMenage.statut == MissionStatusEnum.en_cours).count(),
        missions_terminees=missions_query.filter(MissionMenage.statut == MissionStatusEnum.termine).count(),
        incidents=incidents_query.count(),
    )
