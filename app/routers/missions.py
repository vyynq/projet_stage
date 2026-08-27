import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_upload_dir
from app.dependencies import can_update_mission, can_view_mission, get_db, get_current_user, require_role, log_action
from app.models import ChecklistItem, Incident, Logement, MissionMenage, MissionStatusEnum, User, RoleEnum
from app.schemas import (
    ChecklistItemCreate,
    ChecklistItemOut,
    ChecklistItemUpdate,
    IncidentCreate,
    IncidentOut,
    MissionAssign,
    MissionOut,
    MissionStatusUpdate,
)

router = APIRouter(prefix="/missions", tags=["missions"])

UPLOAD_DIR = get_upload_dir()
INCIDENT_UPLOAD_DIR = UPLOAD_DIR / "incidents"
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024


@router.get("", response_model=list[MissionOut])
def list_missions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(MissionMenage)

    # Regle centrale du sujet : un agent ne voit QUE ses propres missions.
    if current_user.role == RoleEnum.agent_menage:
        query = query.filter(MissionMenage.agent_id == current_user.id)
    elif current_user.role == RoleEnum.proprietaire:
        query = query.join(Logement).filter(Logement.proprietaire_id == current_user.id)

    return query.all()


@router.get("/{mission_id}", response_model=MissionOut)
def get_mission(
    mission_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mission = db.query(MissionMenage).filter(MissionMenage.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission introuvable")

    if not can_view_mission(current_user, mission):
        raise HTTPException(status_code=403, detail="Acces refuse")

    return mission


@router.patch(
    "/{mission_id}/assign",
    response_model=MissionOut,
    dependencies=[Depends(require_role(RoleEnum.admin, RoleEnum.responsable_conciergerie))],
)
def assign_mission(
    mission_id: str,
    payload: MissionAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mission = db.query(MissionMenage).filter(MissionMenage.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    agent = db.query(User).filter(User.id == payload.agent_id).first()
    if not agent or agent.role != RoleEnum.agent_menage:
        raise HTTPException(status_code=400, detail="Agent de menage introuvable")

    mission.agent_id = payload.agent_id
    db.commit()
    db.refresh(mission)

    log_action(db, current_user, "ASSIGN_MISSION", f"mission:{mission_id}")
    return mission


@router.patch("/{mission_id}/status", response_model=MissionOut)
def update_mission_status(
    mission_id: str,
    payload: MissionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mission = db.query(MissionMenage).filter(MissionMenage.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission introuvable")

    # Un agent ne peut modifier le statut que de SA mission.
    if not can_update_mission(current_user, mission):
        raise HTTPException(status_code=403, detail="Acces refuse")

    mission.statut = payload.statut
    if payload.statut == MissionStatusEnum.termine:
        mission.logement.statut = "pret"
    elif payload.statut == MissionStatusEnum.en_cours:
        mission.logement.statut = "menage_en_cours"
    elif payload.statut == MissionStatusEnum.probleme_signale:
        mission.logement.statut = "probleme_signale"

    db.commit()
    db.refresh(mission)

    log_action(db, current_user, "UPDATE_MISSION_STATUS", f"mission:{mission_id}")
    return mission


@router.get("/{mission_id}/checklist", response_model=list[ChecklistItemOut])
def list_checklist(
    mission_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mission = db.query(MissionMenage).filter(MissionMenage.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if not can_view_mission(current_user, mission):
        raise HTTPException(status_code=403, detail="Acces refuse")
    return mission.checklist_items


@router.post("/{mission_id}/checklist", response_model=ChecklistItemOut, status_code=status.HTTP_201_CREATED)
def create_checklist_item(
    mission_id: str,
    payload: ChecklistItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.admin, RoleEnum.responsable_conciergerie)),
):
    mission = db.query(MissionMenage).filter(MissionMenage.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    item = ChecklistItem(mission_id=mission_id, libelle=payload.libelle)
    db.add(item)
    db.commit()
    db.refresh(item)
    log_action(db, current_user, "CREATE_CHECKLIST_ITEM", f"mission:{mission_id}")
    return item


@router.patch("/{mission_id}/checklist/{item_id}", response_model=ChecklistItemOut)
def update_checklist_item(
    mission_id: str,
    item_id: str,
    payload: ChecklistItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mission = db.query(MissionMenage).filter(MissionMenage.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if not can_update_mission(current_user, mission):
        raise HTTPException(status_code=403, detail="Acces refuse")

    item = (
        db.query(ChecklistItem)
        .filter(ChecklistItem.id == item_id, ChecklistItem.mission_id == mission_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Element introuvable")
    if payload.libelle is not None:
        item.libelle = payload.libelle
    if payload.coche is not None:
        item.coche = payload.coche

    db.commit()
    db.refresh(item)
    log_action(db, current_user, "UPDATE_CHECKLIST_ITEM", f"checklist:{item_id}")
    return item


@router.post("/{mission_id}/incidents", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
def create_incident(
    mission_id: str,
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mission = db.query(MissionMenage).filter(MissionMenage.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if not can_update_mission(current_user, mission):
        raise HTTPException(status_code=403, detail="Acces refuse")

    incident = Incident(
        mission_id=mission_id,
        description=payload.description,
        photo_url=payload.photo_url,
    )
    mission.statut = MissionStatusEnum.probleme_signale
    mission.logement.statut = "probleme_signale"
    db.add(incident)
    db.commit()
    db.refresh(incident)
    log_action(db, current_user, "CREATE_INCIDENT", f"mission:{mission_id}")
    return incident


@router.post("/{mission_id}/incidents/upload", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
def create_incident_with_photo(
    mission_id: str,
    description: str = Form(..., min_length=3, max_length=2000),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mission = db.query(MissionMenage).filter(MissionMenage.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if not can_update_mission(current_user, mission):
        raise HTTPException(status_code=403, detail="Acces refuse")

    extension = ALLOWED_IMAGE_TYPES.get(photo.content_type or "")
    if extension is None:
        raise HTTPException(status_code=400, detail="Photo JPG, PNG ou WEBP attendue")

    content = photo.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Photo vide")
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Photo trop volumineuse")

    INCIDENT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}{extension}"
    destination = INCIDENT_UPLOAD_DIR / filename
    destination.write_bytes(content)

    incident = Incident(
        mission_id=mission_id,
        description=description,
        photo_url=f"/uploads/incidents/{filename}",
    )
    mission.statut = MissionStatusEnum.probleme_signale
    mission.logement.statut = "probleme_signale"
    db.add(incident)
    db.commit()
    db.refresh(incident)
    log_action(db, current_user, "CREATE_INCIDENT_WITH_PHOTO", f"mission:{mission_id}")
    return incident


@router.get("/{mission_id}/incidents", response_model=list[IncidentOut])
def list_incidents(
    mission_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mission = db.query(MissionMenage).filter(MissionMenage.id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if not can_view_mission(current_user, mission):
        raise HTTPException(status_code=403, detail="Acces refuse")
    return mission.incidents
