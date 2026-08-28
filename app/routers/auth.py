import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import Base, engine
from app.dependencies import get_current_user, get_db, require_role
from app.email import send_verification_email
from app.models import RoleEnum, User
from app.schemas import EmailVerificationConfirm, EmailVerificationRequest, UserCreate, UserOut, Token
from app.security import (
    SECRET_KEY,
    clear_failed_logins,
    create_access_token,
    hash_password,
    is_login_limited,
    record_failed_login,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_CODE_EXPIRE_MINUTES = 10


def _hash_email_code(email: str, code: str) -> str:
    payload = f"{email.lower()}:{code}".encode("utf-8")
    return hmac.new(SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _generate_email_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _set_and_send_email_code(user: User, db: Session):
    code = _generate_email_code()
    user.email_verification_code_hash = _hash_email_code(user.email, code)
    user.email_verification_expires_at = datetime.utcnow() + timedelta(minutes=EMAIL_CODE_EXPIRE_MINUTES)
    db.commit()
    send_verification_email(user.email, code)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    user_count = db.query(User).count()
    if user_count > 0 and payload.role != RoleEnum.proprietaire:
        raise HTTPException(
            status_code=403,
            detail="Inscription publique limitee aux proprietaires",
        )

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Cet email est deja utilise")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _set_and_send_email_code(user, db)
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
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Cet email est deja utilise")

    user = User(
        email=payload.email,
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
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        return {"message": "Si le compte existe, un code de verification a ete envoye"}
    if user.email_verified_at is not None:
        return {"message": "Email deja verifie"}

    _set_and_send_email_code(user, db)
    return {"message": "Si le compte existe, un code de verification a ete envoye"}


@router.post("/verify-email")
def verify_email(payload: EmailVerificationConfirm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Code de verification invalide")
    if user.email_verified_at is not None:
        return {"message": "Email deja verifie"}
    if not user.email_verification_code_hash or not user.email_verification_expires_at:
        raise HTTPException(status_code=400, detail="Code de verification invalide")
    if user.email_verification_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Code de verification expire")

    expected = _hash_email_code(user.email, payload.code)
    if not hmac.compare_digest(user.email_verification_code_hash, expected):
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

    user = db.query(User).filter(User.email == form_data.username).first()

    # Meme message d'erreur que l'email existe ou non -> evite l'enumeration de comptes
    if not user or not verify_password(form_data.password, user.password_hash):
        record_failed_login(identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email non verifie. Entrez le code recu par email.",
        )

    clear_failed_logins(identifier)
    token = create_access_token(data={"sub": user.id, "role": user.role.value})
    return Token(access_token=token)
