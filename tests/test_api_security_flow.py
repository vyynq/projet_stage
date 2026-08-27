def test_parcours_complet_reservation_mission_menage_et_incident(
    client,
    auth_headers,
    inscrire,
    connecter,
    creer_utilisateur,
):
    assert inscrire("admin@test.com", "admin").status_code == 201
    admin_token = connecter("admin@test.com")

    proprietaire = creer_utilisateur(admin_token, "proprio@test.com", "proprietaire")
    agent = creer_utilisateur(admin_token, "agent@test.com", "agent_menage")
    creer_utilisateur(admin_token, "autre-agent@test.com", "agent_menage")

    proprietaire_token = connecter("proprio@test.com")
    agent_token = connecter("agent@test.com")
    autre_agent_token = connecter("autre-agent@test.com")

    logement_response = client.post(
        "/logements",
        headers=auth_headers(proprietaire_token),
        json={"adresse": "12 rue de la Paix, Paris", "code_acces": "4821"},
    )
    assert logement_response.status_code == 201, logement_response.text
    logement_id = logement_response.json()["id"]
    assert logement_response.json()["proprietaire_id"] == proprietaire["id"]
    assert "code_acces" not in logement_response.json()

    code_response = client.get(f"/logements/{logement_id}/code-acces", headers=auth_headers(proprietaire_token))
    assert code_response.status_code == 200, code_response.text
    assert code_response.json()["code_acces"] == "4821"

    reservation_response = client.post(
        "/reservations",
        headers=auth_headers(proprietaire_token),
        json={
            "logement_id": logement_id,
            "date_arrivee": "2026-07-10T15:00:00",
            "date_depart": "2026-07-12T11:00:00",
            "voyageur_nom": "Camille Martin",
            "voyageur_contact": "camille@example.com",
        },
    )
    assert reservation_response.status_code == 201, reservation_response.text
    assert reservation_response.json()["source"] == "manuel"

    missions_response = client.get("/missions", headers=auth_headers(proprietaire_token))
    assert missions_response.status_code == 200, missions_response.text
    mission = missions_response.json()[0]
    assert mission["reservation_id"] == reservation_response.json()["id"]
    assert mission["statut"] == "a_faire"

    assign_response = client.patch(
        f"/missions/{mission['id']}/assign",
        headers=auth_headers(admin_token),
        json={"agent_id": agent["id"]},
    )
    assert assign_response.status_code == 200, assign_response.text

    forbidden_response = client.get(f"/missions/{mission['id']}", headers=auth_headers(autre_agent_token))
    assert forbidden_response.status_code == 403

    agent_missions_response = client.get("/missions", headers=auth_headers(agent_token))
    assert agent_missions_response.status_code == 200, agent_missions_response.text
    assert [item["id"] for item in agent_missions_response.json()] == [mission["id"]]

    checklist_response = client.get(f"/missions/{mission['id']}/checklist", headers=auth_headers(agent_token))
    assert checklist_response.status_code == 200, checklist_response.text
    checklist_item = checklist_response.json()[0]

    check_response = client.patch(
        f"/missions/{mission['id']}/checklist/{checklist_item['id']}",
        headers=auth_headers(agent_token),
        json={"coche": True},
    )
    assert check_response.status_code == 200, check_response.text
    assert check_response.json()["coche"] is True

    incident_response = client.post(
        f"/missions/{mission['id']}/incidents",
        headers=auth_headers(agent_token),
        json={"description": "Ampoule cassee dans le salon", "photo_url": "https://example.com/photo.jpg"},
    )
    assert incident_response.status_code == 201, incident_response.text

    mission_response = client.get(f"/missions/{mission['id']}", headers=auth_headers(agent_token))
    assert mission_response.status_code == 200, mission_response.text
    assert mission_response.json()["statut"] == "probleme_signale"

    public_admin_response = inscrire("fake-admin@test.com", "admin")
    assert public_admin_response.status_code == 403


def test_import_ical_cree_une_reservation_et_une_mission(
    client,
    auth_headers,
    inscrire,
    connecter,
    creer_utilisateur,
    creer_logement,
):
    assert inscrire("admin-ical@test.com", "admin").status_code == 201
    admin_token = connecter("admin-ical@test.com")
    proprietaire = creer_utilisateur(admin_token, "owner-ical@test.com", "proprietaire")
    proprietaire_token = connecter("owner-ical@test.com")

    logement = creer_logement(proprietaire_token, "24 rue du Calendrier, Paris", "1978")
    assert logement["proprietaire_id"] == proprietaire["id"]

    ical_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:airbnb-booking-1
SUMMARY:Reservation Airbnb
DTSTART:20260810T150000
DTEND:20260812T110000
END:VEVENT
END:VCALENDAR
"""
    response = client.post(
        "/reservations/import-ical",
        headers=auth_headers(proprietaire_token),
        data={"logement_id": logement["id"], "source": "airbnb"},
        files={"file": ("airbnb.ics", ical_content, "text/calendar")},
    )
    assert response.status_code == 201, response.text
    reservations = response.json()
    assert len(reservations) == 1
    assert reservations[0]["source"] == "airbnb"
    assert reservations[0]["external_id"] == "airbnb-booking-1"

    missions_response = client.get("/missions", headers=auth_headers(proprietaire_token))
    assert missions_response.status_code == 200, missions_response.text
    assert len(missions_response.json()) == 1
    assert missions_response.json()[0]["reservation_id"] == reservations[0]["id"]
