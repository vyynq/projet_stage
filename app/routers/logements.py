from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import can_manage_logement, get_db, get_current_user, require_role, log_action
from app.models import Logement, User, RoleEnum
from app.schemas import CodeAccesOut, LogementCreate, LogementOut, LogementUpdate
from app.security import decrypt_sensitive_value, encrypt_sensitive_value

router = APIRouter(prefix="/logements", tags=["logements"])


@router.post(
    "",
    response_model=LogementOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(RoleEnum.admin, RoleEnum.proprietaire))],
)
def create_logement(
    payload: LogementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logement = Logement(
        adresse=payload.adresse,
        code_acces_chiffre=encrypt_sensitive_value(payload.code_acces),
        proprietaire_id=current_user.id,
    )
    db.add(logement)
    db.commit()
    db.refresh(logement)
    return logement


@router.get("", response_model=list[LogementOut])
def list_logements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Logement)

    # Un proprietaire ne voit que ses propres logements. Admin et conciergerie voient tout.
    if current_user.role == RoleEnum.proprietaire:
        query = query.filter(Logement.proprietaire_id == current_user.id)
    elif current_user.role == RoleEnum.agent_menage:
        raise HTTPException(status_code=403, detail="Acces refuse")

    return query.all()


@router.get("/{logement_id}", response_model=LogementOut)
def get_logement(
    logement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logement = db.query(Logement).filter(Logement.id == logement_id).first()
    if not logement:
        raise HTTPException(status_code=404, detail="Logement introuvable")

    # Verification d'ownership : un proprietaire ne peut consulter que ses biens
    if current_user.role == RoleEnum.proprietaire and logement.proprietaire_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acces refuse")

    log_action(db, current_user, "CONSULT_LOGEMENT", f"logement:{logement_id}")
    return logement


@router.patch("/{logement_id}", response_model=LogementOut)
def update_logement(
    logement_id: str,
    payload: LogementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logement = db.query(Logement).filter(Logement.id == logement_id).first()
    if not logement:
        raise HTTPException(status_code=404, detail="Logement introuvable")
    if not can_manage_logement(current_user, logement):
        raise HTTPException(status_code=403, detail="Acces refuse")

    if payload.adresse is not None:
        logement.adresse = payload.adresse
    if payload.code_acces is not None:
        logement.code_acces_chiffre = encrypt_sensitive_value(payload.code_acces)
    if payload.statut is not None:
        logement.statut = payload.statut

    db.commit()
    db.refresh(logement)
    log_action(db, current_user, "UPDATE_LOGEMENT", f"logement:{logement_id}")
    return logement


@router.get("/{logement_id}/code-acces", response_model=CodeAccesOut)
def get_code_acces(
    logement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logement = db.query(Logement).filter(Logement.id == logement_id).first()
    if not logement:
        raise HTTPException(status_code=404, detail="Logement introuvable")
    if not can_manage_logement(current_user, logement):
        raise HTTPException(status_code=403, detail="Acces refuse")

    log_action(db, current_user, "CONSULT_CODE_ACCES", f"logement:{logement_id}")
    return CodeAccesOut(
        logement_id=logement.id,
        code_acces=decrypt_sensitive_value(logement.code_acces_chiffre),
    )


@router.delete("/{logement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_logement(
    logement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.admin, RoleEnum.proprietaire)),
):
    logement = db.query(Logement).filter(Logement.id == logement_id).first()
    if not logement:
        raise HTTPException(status_code=404, detail="Logement introuvable")
    if not can_manage_logement(current_user, logement):
        raise HTTPException(status_code=403, detail="Acces refuse")

    db.delete(logement)
    db.commit()
    log_action(db, current_user, "DELETE_LOGEMENT", f"logement:{logement_id}")
