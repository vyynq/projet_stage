def test_dashboard_proprietaire_compte_uniquement_ses_donnees(
    client,
    auth_headers,
    creer_admin,
    creer_utilisateur,
    connecter,
    creer_logement,
    creer_reservation,
):
    _, admin_token = creer_admin()
    creer_utilisateur(admin_token, "alice@test.com", "proprietaire")
    creer_utilisateur(admin_token, "bob@test.com", "proprietaire")
    alice_token = connecter("alice@test.com")
    bob_token = connecter("bob@test.com")

    logement_alice = creer_logement(alice_token, "Appartement Alice")
    logement_bob = creer_logement(bob_token, "Appartement Bob")
    creer_reservation(alice_token, logement_alice["id"], "Voyageur Alice")
    creer_reservation(bob_token, logement_bob["id"], "Voyageur Bob")

    response = client.get("/dashboard", headers=auth_headers(alice_token))

    assert response.status_code == 200, response.text
    assert response.json() == {
        "logements": 1,
        "reservations": 1,
        "missions_a_faire": 1,
        "missions_en_cours": 0,
        "missions_terminees": 0,
        "incidents": 0,
    }


def test_dashboard_agent_compte_uniquement_ses_missions(client, auth_headers, mission_assignee):
    response = client.get("/dashboard", headers=auth_headers(mission_assignee["agent_token"]))

    assert response.status_code == 200, response.text
    assert response.json()["logements"] == 0
    assert response.json()["reservations"] == 0
    assert response.json()["missions_a_faire"] == 1


def test_dashboard_admin_compte_toutes_les_donnees(client, auth_headers, mission_assignee):
    response = client.get("/dashboard", headers=auth_headers(mission_assignee["admin_token"]))

    assert response.status_code == 200, response.text
    assert response.json()["logements"] == 1
    assert response.json()["reservations"] == 1
    assert response.json()["missions_a_faire"] == 1
