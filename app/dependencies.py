from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.security import decode_access_token
from app.models import Logement, MissionMenage, User, RoleEnum, AuditLog

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou expires",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def require_role(*allowed_roles: RoleEnum):
    """
    Dependency factory : usage -> Depends(require_role(RoleEnum.admin, RoleEnum.proprietaire))
    Leve une 403 si le role de l'utilisateur courant n'est pas autorise.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acces refuse : role insuffisant",
            )
        return current_user
    return role_checker


def log_action(db: Session, user: User | None, action: str, ressource: str):
    entry = AuditLog(
        user_id=user.id if user else None,
        action=action,
        ressource=ressource,
    )
    db.add(entry)
    db.commit()


def can_manage_logement(user: User, logement: Logement) -> bool:
    if user.role in {RoleEnum.admin, RoleEnum.responsable_conciergerie}:
        return True
    return user.role == RoleEnum.proprietaire and logement.proprietaire_id == user.id


def can_view_mission(user: User, mission: MissionMenage) -> bool:
    if user.role in {RoleEnum.admin, RoleEnum.responsable_conciergerie}:
        return True
    if user.role == RoleEnum.proprietaire:
        return mission.logement.proprietaire_id == user.id
    if user.role == RoleEnum.agent_menage:
        return mission.agent_id == user.id
    return False


def can_update_mission(user: User, mission: MissionMenage) -> bool:
    if user.role in {RoleEnum.admin, RoleEnum.responsable_conciergerie}:
        return True
    return user.role == RoleEnum.agent_menage and mission.agent_id == user.id
