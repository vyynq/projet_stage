def test_creation_reservation_cree_automatiquement_mission_et_checklist(
    client,
    auth_headers,
    creer_admin,
    creer_utilisateur,
    connecter,
    creer_logement,
    creer_reservation,
):
    _, admin_token = creer_admin()
    creer_utilisateur(admin_token, "proprietaire@test.com", "proprietaire")
    proprietaire_token = connecter("proprietaire@test.com")
    logement = creer_logement(proprietaire_token)

    reservation = creer_reservation(proprietaire_token, logement["id"])

    missions_response = client.get("/missions", headers=auth_headers(proprietaire_token))
    assert missions_response.status_code == 200, missions_response.text
    mission = missions_response.json()[0]
    assert mission["reservation_id"] == reservation["id"]
    assert mission["date_prevue"].startswith("2026-07-12T11:00:00")

    checklist_response = client.get(f"/missions/{mission['id']}/checklist", headers=auth_headers(proprietaire_token))
    assert checklist_response.status_code == 200, checklist_response.text
    assert len(checklist_response.json()) == 6


def test_reservation_refuse_une_date_de_depart_avant_l_arrivee(
    client,
    auth_headers,
    creer_admin,
    creer_utilisateur,
    connecter,
    creer_logement,
):
    _, admin_token = creer_admin()
    creer_utilisateur(admin_token, "proprietaire@test.com", "proprietaire")
    proprietaire_token = connecter("proprietaire@test.com")
    logement = creer_logement(proprietaire_token)

    response = client.post(
        "/reservations",
        headers=auth_headers(proprietaire_token),
        json={
            "logement_id": logement["id"],
            "date_arrivee": "2026-07-12T15:00:00",
            "date_depart": "2026-07-10T11:00:00",
            "voyageur_nom": "Camille Martin",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "La date de depart doit etre apres l'arrivee"


def test_import_csv_cree_plusieurs_reservations_et_missions(
    client,
    auth_headers,
    creer_admin,
    creer_utilisateur,
    connecter,
    creer_logement,
):
    _, admin_token = creer_admin()
    creer_utilisateur(admin_token, "proprietaire@test.com", "proprietaire")
    proprietaire_token = connecter("proprietaire@test.com")
    logement = creer_logement(proprietaire_token)
    csv_content = """date_arrivee,date_depart,voyageur_nom,voyageur_contact
2026-08-01T15:00:00,2026-08-03T11:00:00,Alice,alice@example.com
2026-08-05T15:00:00,2026-08-07T11:00:00,Bob,bob@example.com
"""

    response = client.post(
        f"/reservations/import?logement_id={logement['id']}",
        headers=auth_headers(proprietaire_token),
        files={"file": ("reservations.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 201, response.text
    assert [reservation["voyageur_nom"] for reservation in response.json()] == ["Alice", "Bob"]

    missions_response = client.get("/missions", headers=auth_headers(proprietaire_token))
    assert len(missions_response.json()) == 2


def test_import_ical_ignore_une_reservation_deja_importee(
    client,
    auth_headers,
    creer_admin,
    creer_utilisateur,
    connecter,
    creer_logement,
):
    _, admin_token = creer_admin()
    creer_utilisateur(admin_token, "proprietaire@test.com", "proprietaire")
    proprietaire_token = connecter("proprietaire@test.com")
    logement = creer_logement(proprietaire_token)
    ical_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:booking-unique-1
SUMMARY:Reservation deja connue
DTSTART:20260810T150000
DTEND:20260812T110000
END:VEVENT
END:VCALENDAR
"""

    first_response = client.post(
        "/reservations/import-ical",
        headers=auth_headers(proprietaire_token),
        data={"logement_id": logement["id"], "source": "airbnb"},
        files={"file": ("airbnb.ics", ical_content, "text/calendar")},
    )
    second_response = client.post(
        "/reservations/import-ical",
        headers=auth_headers(proprietaire_token),
        data={"logement_id": logement["id"], "source": "airbnb"},
        files={"file": ("airbnb.ics", ical_content, "text/calendar")},
    )

    assert first_response.status_code == 201, first_response.text
    assert len(first_response.json()) == 1
    assert second_response.status_code == 201, second_response.text
    assert second_response.json() == []


def test_agent_menage_ne_peut_pas_consulter_les_reservations(
    client,
    auth_headers,
    creer_admin,
    creer_utilisateur,
    connecter,
):
    _, admin_token = creer_admin()
    creer_utilisateur(admin_token, "agent@test.com", "agent_menage")
    agent_token = connecter("agent@test.com")

    response = client.get("/reservations", headers=auth_headers(agent_token))

    assert response.status_code == 403
