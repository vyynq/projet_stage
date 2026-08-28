from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_role
from app.models import RoleEnum, User
from app.schemas import EmailVerificationConfirm, EmailVerificationRequest, UserCreate, UserOut, Token
from app.security import (
    clear_failed_logins,
    create_access_token,
    hash_password,
    is_login_limited,
    record_failed_login,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _find_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(func.lower(User.email) == email.lower()).first()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    email = payload.email.lower()
    existing = _find_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=400, detail="Cet email est deja utilise")

    user_count = db.query(User).count()
    if user_count > 0 and payload.role != RoleEnum.proprietaire:
        raise HTTPException(
            status_code=403,
            detail="Inscription publique limitee aux proprietaires",
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        email_verified_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.from_orm_user(user)


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(RoleEnum.admin))],
)
def create_user_by_admin(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    email = payload.email.lower()
    existing = _find_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=400, detail="Cet email est deja utilise")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        email_verified_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.from_orm_user(user)


@router.get(
    "/users",
    response_model=list[UserOut],
    dependencies=[Depends(require_role(RoleEnum.admin, RoleEnum.responsable_conciergerie))],
)
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [UserOut.from_orm_user(user) for user in users]


@router.post("/request-email-code")
def request_email_code(payload: EmailVerificationRequest, db: Session = Depends(get_db)):
    return {"message": "Verification email desactivee pour le moment"}


@router.post("/verify-email")
def verify_email(payload: EmailVerificationConfirm, db: Session = Depends(get_db)):
    user = _find_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=400, detail="Code de verification invalide")
    user.email_verified_at = datetime.utcnow()
    user.email_verification_code_hash = None
    user.email_verification_expires_at = None
    db.commit()
    return {"message": "Email verifie"}


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    identifier = form_data.username.lower()
    if is_login_limited(identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives. Reessayez plus tard.",
        )

    user = _find_user_by_email(db, identifier)

    # Meme message d'erreur que l'email existe ou non -> evite l'enumeration de comptes
    if not user or not verify_password(form_data.password, user.password_hash):
        record_failed_login(identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    clear_failed_logins(identifier)
    token = create_access_token(data={"sub": user.id, "role": user.role.value})
    return Token(access_token=token)
