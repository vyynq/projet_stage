def test_un_proprietaire_cree_un_logement_sans_exposer_le_code_acces(
    client,
    auth_headers,
    creer_admin,
    creer_utilisateur,
    connecter,
):
    _, admin_token = creer_admin()
    creer_utilisateur(admin_token, "proprietaire@test.com", "proprietaire")
    proprietaire_token = connecter("proprietaire@test.com")

    response = client.post(
        "/logements",
        headers=auth_headers(proprietaire_token),
        json={"adresse": "8 rue du Test, Lyon", "code_acces": "1234"},
    )

    assert response.status_code == 201, response.text
    assert response.json()["adresse"] == "8 rue du Test, Lyon"
    assert "code_acces" not in response.json()


def test_le_code_acces_est_lisible_uniquement_par_un_role_autorise(
    client,
    auth_headers,
    creer_admin,
    creer_utilisateur,
    connecter,
    creer_logement,
):
    _, admin_token = creer_admin()
    creer_utilisateur(admin_token, "proprietaire@test.com", "proprietaire")
    creer_utilisateur(admin_token, "autre@test.com", "proprietaire")
    proprietaire_token = connecter("proprietaire@test.com")
    autre_token = connecter("autre@test.com")
    logement = creer_logement(proprietaire_token, code_acces="7890")

    ok_response = client.get(f"/logements/{logement['id']}/code-acces", headers=auth_headers(proprietaire_token))
    forbidden_response = client.get(f"/logements/{logement['id']}/code-acces", headers=auth_headers(autre_token))

    assert ok_response.status_code == 200, ok_response.text
    assert ok_response.json()["code_acces"] == "7890"
    assert forbidden_response.status_code == 403


def test_un_proprietaire_ne_voit_pas_les_logements_des_autres(
    client,
    auth_headers,
    creer_admin,
    creer_utilisateur,
    connecter,
    creer_logement,
):
    _, admin_token = creer_admin()
    creer_utilisateur(admin_token, "alice@test.com", "proprietaire")
    creer_utilisateur(admin_token, "bob@test.com", "proprietaire")
    alice_token = connecter("alice@test.com")
    bob_token = connecter("bob@test.com")
    logement_alice = creer_logement(alice_token, "Appartement Alice")
    creer_logement(bob_token, "Appartement Bob")

    response = client.get("/logements", headers=auth_headers(alice_token))

    assert response.status_code == 200, response.text
    assert [logement["id"] for logement in response.json()] == [logement_alice["id"]]


def test_un_agent_menage_ne_peut_pas_lister_les_logements(
    client,
    auth_headers,
    creer_admin,
    creer_utilisateur,
    connecter,
):
    _, admin_token = creer_admin()
    creer_utilisateur(admin_token, "agent@test.com", "agent_menage")
    agent_token = connecter("agent@test.com")

    response = client.get("/logements", headers=auth_headers(agent_token))

    assert response.status_code == 403


def test_un_proprietaire_peut_modifier_puis_supprimer_son_logement(
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

    update_response = client.patch(
        f"/logements/{logement['id']}",
        headers=auth_headers(proprietaire_token),
        json={"adresse": "10 rue Modifiee", "statut": "maintenance"},
    )
    delete_response = client.delete(f"/logements/{logement['id']}", headers=auth_headers(proprietaire_token))
    get_response = client.get(f"/logements/{logement['id']}", headers=auth_headers(proprietaire_token))

    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["adresse"] == "10 rue Modifiee"
    assert update_response.json()["statut"] == "maintenance"
    assert delete_response.status_code == 204
    assert get_response.status_code == 404
