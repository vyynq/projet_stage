from pathlib import Path


def test_agent_ne_voit_que_sa_mission_assignee(client, auth_headers, mission_assignee):
    response = client.get("/missions", headers=auth_headers(mission_assignee["agent_token"]))

    assert response.status_code == 200, response.text
    assert [mission["id"] for mission in response.json()] == [mission_assignee["mission"]["id"]]


def test_autre_agent_ne_peut_pas_modifier_la_checklist(client, auth_headers, mission_assignee):
    mission_id = mission_assignee["mission"]["id"]
    checklist_response = client.get(
        f"/missions/{mission_id}/checklist",
        headers=auth_headers(mission_assignee["agent_token"]),
    )
    item_id = checklist_response.json()[0]["id"]

    response = client.patch(
        f"/missions/{mission_id}/checklist/{item_id}",
        headers=auth_headers(mission_assignee["autre_agent_token"]),
        json={"coche": True},
    )

    assert response.status_code == 403


def test_agent_assigne_peut_cocher_la_checklist(client, auth_headers, mission_assignee):
    mission_id = mission_assignee["mission"]["id"]
    checklist_response = client.get(
        f"/missions/{mission_id}/checklist",
        headers=auth_headers(mission_assignee["agent_token"]),
    )
    item_id = checklist_response.json()[0]["id"]

    response = client.patch(
        f"/missions/{mission_id}/checklist/{item_id}",
        headers=auth_headers(mission_assignee["agent_token"]),
        json={"coche": True},
    )

    assert response.status_code == 200, response.text
    assert response.json()["coche"] is True


def test_changement_de_statut_met_a_jour_le_statut_du_logement(client, auth_headers, mission_assignee):
    mission_id = mission_assignee["mission"]["id"]
    logement_id = mission_assignee["logement"]["id"]

    response = client.patch(
        f"/missions/{mission_id}/status",
        headers=auth_headers(mission_assignee["agent_token"]),
        json={"statut": "en_cours"},
    )
    logement_response = client.get(
        f"/logements/{logement_id}",
        headers=auth_headers(mission_assignee["proprietaire_token"]),
    )

    assert response.status_code == 200, response.text
    assert response.json()["statut"] == "en_cours"
    assert logement_response.json()["statut"] == "menage_en_cours"


def test_incident_signale_passe_la_mission_en_probleme(client, auth_headers, mission_assignee):
    mission_id = mission_assignee["mission"]["id"]

    response = client.post(
        f"/missions/{mission_id}/incidents",
        headers=auth_headers(mission_assignee["agent_token"]),
        json={"description": "Vitres cassees dans le salon", "photo_url": "https://example.com/photo.jpg"},
    )
    mission_response = client.get(f"/missions/{mission_id}", headers=auth_headers(mission_assignee["agent_token"]))

    assert response.status_code == 201, response.text
    assert response.json()["description"] == "Vitres cassees dans le salon"
    assert mission_response.json()["statut"] == "probleme_signale"


def test_upload_incident_refuse_un_fichier_non_image(client, auth_headers, mission_assignee):
    mission_id = mission_assignee["mission"]["id"]

    response = client.post(
        f"/missions/{mission_id}/incidents/upload",
        headers=auth_headers(mission_assignee["agent_token"]),
        data={"description": "Document non autorise"},
        files={"photo": ("preuve.txt", b"pas une image", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Photo JPG, PNG ou WEBP attendue"


def test_upload_incident_accepte_une_image_png(client, auth_headers, mission_assignee):
    mission_id = mission_assignee["mission"]["id"]

    response = client.post(
        f"/missions/{mission_id}/incidents/upload",
        headers=auth_headers(mission_assignee["agent_token"]),
        data={"description": "Photo de validation"},
        files={"photo": ("preuve.png", b"image de test", "image/png")},
    )

    assert response.status_code == 201, response.text
    assert response.json()["photo_url"].startswith("/uploads/incidents/")

    upload_path = Path("test_uploads") / "incidents" / Path(response.json()["photo_url"]).name
    assert upload_path.exists()
