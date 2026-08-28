def test_premier_utilisateur_peut_devenir_admin(inscrire):
    response = inscrire("admin@test.com", "admin")

    assert response.status_code == 201, response.text
    assert response.json()["role"] == "admin"
    assert response.json()["email_verified"] is True


def test_connexion_possible_apres_inscription(client, inscrire):
    assert inscrire("admin@test.com", "admin").status_code == 201

    response = client.post(
        "/auth/login",
        data={"username": "admin@test.com", "password": "motdepasse123"},
    )

    assert response.status_code == 200, response.text
    assert "access_token" in response.json()


def test_inscription_refuse_un_email_deja_utilise(inscrire):
    assert inscrire("admin@test.com", "admin").status_code == 201

    response = inscrire("admin@test.com", "admin")
    assert response.status_code == 400
    assert response.json()["detail"] == "Cet email est deja utilise"


def test_verification_email_desactivee_pour_la_demo(client, inscrire):
    assert inscrire("admin@test.com", "admin").status_code == 201

    response = client.post("/auth/request-email-code", json={"email": "admin@test.com"})

    assert response.status_code == 200
    assert response.json()["message"] == "Verification email desactivee pour le moment"


def test_email_insensible_aux_majuscules_pour_verification_et_connexion(client, inscrire, verifier_email):
    assert inscrire("Admin@Test.com", "admin").status_code == 201
    response = client.post(
        "/auth/login",
        data={"username": "ADMIN@test.com", "password": "motdepasse123"},
    )

    assert response.status_code == 200, response.text


def test_inscription_publique_refuse_un_deuxieme_admin(inscrire):
    assert inscrire("admin@test.com", "admin").status_code == 201

    response = inscrire("autre-admin@test.com", "admin")

    assert response.status_code == 403
    assert response.json()["detail"] == "Inscription publique limitee aux proprietaires"


def test_inscription_publique_accepte_un_proprietaire_apres_le_premier_compte(inscrire):
    assert inscrire("admin@test.com", "admin").status_code == 201

    response = inscrire("proprietaire@test.com", "proprietaire")

    assert response.status_code == 201, response.text
    assert response.json()["role"] == "proprietaire"


def test_connexion_retourne_un_token_bearer(inscrire, connecter):
    assert inscrire("admin@test.com", "admin").status_code == 201

    token = connecter("admin@test.com")

    assert isinstance(token, str)
    assert len(token) > 20


def test_un_admin_peut_creer_et_lister_les_utilisateurs(client, auth_headers, creer_admin, creer_utilisateur):
    _, admin_token = creer_admin()

    agent = creer_utilisateur(admin_token, "agent@test.com", "agent_menage")
    response = client.get("/auth/users", headers=auth_headers(admin_token))

    assert response.status_code == 200, response.text
    assert agent["email_verified"] is True
    emails = {utilisateur["email"] for utilisateur in response.json()}
    assert {"admin@test.com", "agent@test.com"}.issubset(emails)


def test_un_proprietaire_ne_peut_pas_creer_un_utilisateur_admin(client, auth_headers, inscrire, connecter):
    assert inscrire("admin@test.com", "admin").status_code == 201
    assert inscrire("proprietaire@test.com", "proprietaire").status_code == 201
    proprietaire_token = connecter("proprietaire@test.com")

    response = client.post(
        "/auth/users",
        headers=auth_headers(proprietaire_token),
        json={"email": "intrus@test.com", "password": "motdepasse123", "role": "admin"},
    )

    assert response.status_code == 403


def test_trop_de_mauvaises_connexions_bloque_temporairement_le_compte(client, inscrire):
    assert inscrire("admin@test.com", "admin").status_code == 201

    for _ in range(5):
        response = client.post(
            "/auth/login",
            data={"username": "admin@test.com", "password": "mauvais-mot-de-passe"},
        )
        assert response.status_code == 401

    response = client.post(
        "/auth/login",
        data={"username": "admin@test.com", "password": "motdepasse123"},
    )

    assert response.status_code == 429
