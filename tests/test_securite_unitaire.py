from app.security import (
    create_access_token,
    decode_access_token,
    decrypt_sensitive_value,
    encrypt_sensitive_value,
    hash_password,
    verify_password,
)


def test_mot_de_passe_est_hashe_et_verifiable():
    password_hash = hash_password("motdepasse123")

    assert password_hash != "motdepasse123"
    assert verify_password("motdepasse123", password_hash) is True
    assert verify_password("mauvais", password_hash) is False


def test_token_jwt_encode_et_decode_les_informations_utilisateur():
    token = create_access_token({"sub": "user-123", "role": "admin"})

    payload = decode_access_token(token)

    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"


def test_chiffrement_cache_la_valeur_sensible_et_permet_de_la_relire():
    valeur_chiffree = encrypt_sensitive_value("4821")

    assert valeur_chiffree != "4821"
    assert decrypt_sensitive_value(valeur_chiffree) == "4821"


def test_dechiffrement_retourne_none_si_la_valeur_est_invalide():
    assert decrypt_sensitive_value("valeur-invalide") is None
