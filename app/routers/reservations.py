import csv
import io
from datetime import datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.dependencies import can_manage_logement, get_db, get_current_user, log_action
from app.models import ChecklistItem, Logement, MissionMenage, Reservation, RoleEnum, User
from app.schemas import ReservationCreate, ReservationOut, ReservationUpdate

router = APIRouter(prefix="/reservations", tags=["reservations"])

DEFAULT_CHECKLIST = [
    "Aerer le logement",
    "Changer les draps et serviettes",
    "Nettoyer cuisine et salle de bain",
    "Vider les poubelles",
    "Verifier consommables et signaler les manques",
    "Prendre une photo de validation",
]


def _get_accessible_logement(db: Session, logement_id: str, current_user: User) -> Logement:
    logement = db.query(Logement).filter(Logement.id == logement_id).first()
    if not logement:
        raise HTTPException(status_code=404, detail="Logement introuvable")
    if not can_manage_logement(current_user, logement):
        raise HTTPException(status_code=403, detail="Acces refuse")
    return logement


def _get_accessible_reservation(db: Session, reservation_id: str, current_user: User) -> Reservation:
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation introuvable")
    if not can_manage_logement(current_user, reservation.logement):
        raise HTTPException(status_code=403, detail="Acces refuse")
    return reservation


def _create_reservation_with_mission(
    db: Session,
    logement_id: str,
    date_arrivee: datetime,
    date_depart: datetime,
    voyageur_nom: str,
    voyageur_contact: str | None,
    source: str = "manuel",
    external_id: str | None = None,
) -> Reservation:
    reservation = Reservation(
        logement_id=logement_id,
        date_arrivee=date_arrivee,
        date_depart=date_depart,
        voyageur_nom=voyageur_nom,
        voyageur_contact=voyageur_contact,
        source=source,
        external_id=external_id,
    )
    db.add(reservation)
    db.flush()

    mission = MissionMenage(
        logement_id=logement_id,
        reservation_id=reservation.id,
        date_prevue=date_depart,
    )
    db.add(mission)
    db.flush()

    for libelle in DEFAULT_CHECKLIST:
        db.add(ChecklistItem(mission_id=mission.id, libelle=libelle))

    return reservation


def _parse_ical_datetime(value: str) -> datetime:
    raw = value.strip()
    if ":" in raw:
        raw = raw.split(":", 1)[1]
    raw = raw.strip().replace("Z", "")
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError("Date iCal invalide")


def _unfold_ical(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw_line.startswith((" ", "\t")) and lines:
            lines[-1] += raw_line[1:]
        else:
            lines.append(raw_line)
    return lines


def _parse_ical_events(text: str) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in _unfold_ical(text):
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT" and current is not None:
            events.append(current)
            current = None
        elif current is not None and ":" in line:
            key, value = line.split(":", 1)
            current[key.split(";", 1)[0].upper()] = value.strip()
    return events


@router.post("", response_model=ReservationOut, status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == RoleEnum.agent_menage:
        raise HTTPException(status_code=403, detail="Acces refuse")
    if payload.date_depart <= payload.date_arrivee:
        raise HTTPException(status_code=400, detail="La date de depart doit etre apres l'arrivee")

    _get_accessible_logement(db, payload.logement_id, current_user)

    reservation = _create_reservation_with_mission(
        db=db,
        logement_id=payload.logement_id,
        date_arrivee=payload.date_arrivee,
        date_depart=payload.date_depart,
        voyageur_nom=payload.voyageur_nom,
        voyageur_contact=payload.voyageur_contact,
        source=payload.source,
        external_id=payload.external_id,
    )

    db.commit()
    db.refresh(reservation)
    log_action(db, current_user, "CREATE_RESERVATION", f"reservation:{reservation.id}")
    log_action(db, current_user, "AUTO_CREATE_MISSION", f"reservation:{reservation.id}")
    return reservation


@router.post("/import", response_model=list[ReservationOut], status_code=status.HTTP_201_CREATED)
def import_reservations(
    logement_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == RoleEnum.agent_menage:
        raise HTTPException(status_code=403, detail="Acces refuse")
    _get_accessible_logement(db, logement_id, current_user)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Import CSV attendu")

    content = file.file.read()
    if len(content) > 2_000_000:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux")

    try:
        text = content.decode("utf-8-sig")
        rows = csv.DictReader(io.StringIO(text))
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV illisible en UTF-8")

    required = {"date_arrivee", "date_depart", "voyageur_nom"}
    if not rows.fieldnames or not required.issubset(set(rows.fieldnames)):
        raise HTTPException(
            status_code=400,
            detail="Colonnes requises: date_arrivee,date_depart,voyageur_nom",
        )

    created: list[Reservation] = []
    for index, row in enumerate(rows, start=2):
        try:
            date_arrivee = datetime.fromisoformat(row["date_arrivee"])
            date_depart = datetime.fromisoformat(row["date_depart"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"Dates invalides ligne {index}")
        if date_depart <= date_arrivee:
            raise HTTPException(status_code=400, detail=f"Depart avant arrivee ligne {index}")
        voyageur_nom = (row.get("voyageur_nom") or "").strip()
        if not voyageur_nom:
            raise HTTPException(status_code=400, detail=f"Nom voyageur manquant ligne {index}")

        created.append(
            _create_reservation_with_mission(
                db=db,
                logement_id=logement_id,
                date_arrivee=date_arrivee,
                date_depart=date_depart,
                voyageur_nom=voyageur_nom,
                voyageur_contact=(row.get("voyageur_contact") or None),
                source=(row.get("source") or "csv"),
                external_id=(row.get("external_id") or None),
            )
        )

    db.commit()
    for reservation in created:
        db.refresh(reservation)
        log_action(db, current_user, "IMPORT_RESERVATION", f"reservation:{reservation.id}")
    return created


@router.post("/import-ical", response_model=list[ReservationOut], status_code=status.HTTP_201_CREATED)
def import_ical_reservations(
    logement_id: str = Form(...),
    source: str = Form(default="calendrier"),
    calendar_url: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == RoleEnum.agent_menage:
        raise HTTPException(status_code=403, detail="Acces refuse")
    _get_accessible_logement(db, logement_id, current_user)

    content: bytes | None = None
    if file and file.filename:
        if not file.filename.lower().endswith((".ics", ".ical")):
            raise HTTPException(status_code=400, detail="Fichier calendrier .ics attendu")
        content = file.file.read()
    elif calendar_url:
        if not calendar_url.startswith(("https://", "http://")):
            raise HTTPException(status_code=400, detail="URL calendrier invalide")
        try:
            request = Request(calendar_url, headers={"User-Agent": "Airbnb-Menage/1.0"})
            with urlopen(request, timeout=10) as response:
                content = response.read(2_000_001)
        except URLError:
            raise HTTPException(status_code=400, detail="Calendrier inaccessible")

    if not content:
        raise HTTPException(status_code=400, detail="Fichier ou URL calendrier requis")
    if len(content) > 2_000_000:
        raise HTTPException(status_code=413, detail="Calendrier trop volumineux")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Calendrier illisible en UTF-8")

    created: list[Reservation] = []
    for index, event in enumerate(_parse_ical_events(text), start=1):
        if "DTSTART" not in event or "DTEND" not in event:
            continue
        try:
            date_arrivee = _parse_ical_datetime(event["DTSTART"])
            date_depart = _parse_ical_datetime(event["DTEND"])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Dates invalides evenement {index}")
        if date_depart <= date_arrivee:
            continue

        uid = event.get("UID")
        if uid:
            existing = (
                db.query(Reservation)
                .filter(Reservation.logement_id == logement_id, Reservation.external_id == uid)
                .first()
            )
            if existing:
                continue

        created.append(
            _create_reservation_with_mission(
                db=db,
                logement_id=logement_id,
                date_arrivee=date_arrivee,
                date_depart=date_depart,
                voyageur_nom=event.get("SUMMARY") or f"Reservation {source}",
                voyageur_contact=None,
                source=source[:80],
                external_id=uid,
            )
        )

    db.commit()
    for reservation in created:
        db.refresh(reservation)
        log_action(db, current_user, "IMPORT_ICAL_RESERVATION", f"reservation:{reservation.id}")
    return created


@router.get("", response_model=list[ReservationOut])
def list_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == RoleEnum.agent_menage:
        raise HTTPException(status_code=403, detail="Acces refuse")

    query = db.query(Reservation)
    if current_user.role == RoleEnum.proprietaire:
        query = query.join(Logement).filter(Logement.proprietaire_id == current_user.id)
    return query.all()


@router.get("/{reservation_id}", response_model=ReservationOut)
def get_reservation(
    reservation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reservation = _get_accessible_reservation(db, reservation_id, current_user)
    log_action(db, current_user, "CONSULT_RESERVATION", f"reservation:{reservation_id}")
    return reservation


@router.patch("/{reservation_id}", response_model=ReservationOut)
def update_reservation(
    reservation_id: str,
    payload: ReservationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reservation = _get_accessible_reservation(db, reservation_id, current_user)

    date_arrivee = payload.date_arrivee or reservation.date_arrivee
    date_depart = payload.date_depart or reservation.date_depart
    if date_depart <= date_arrivee:
        raise HTTPException(status_code=400, detail="La date de depart doit etre apres l'arrivee")

    reservation.date_arrivee = date_arrivee
    reservation.date_depart = date_depart
    if payload.voyageur_nom is not None:
        reservation.voyageur_nom = payload.voyageur_nom
    if payload.voyageur_contact is not None:
        reservation.voyageur_contact = payload.voyageur_contact
    if reservation.mission:
        reservation.mission.date_prevue = date_depart

    db.commit()
    db.refresh(reservation)
    log_action(db, current_user, "UPDATE_RESERVATION", f"reservation:{reservation_id}")
    return reservation


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reservation(
    reservation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reservation = _get_accessible_reservation(db, reservation_id, current_user)
    db.delete(reservation)
    db.commit()
    log_action(db, current_user, "DELETE_RESERVATION", f"reservation:{reservation_id}")
