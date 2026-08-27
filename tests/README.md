# Tests unitaires et API

Ce dossier contient les tests automatises de l'application.

## Lancer les tests

```bash
.venv/bin/python -m pytest -q
```

## Organisation

- `conftest.py` prepare une base SQLite de test et fournit des aides reutilisables : creer un admin, creer un utilisateur, se connecter, creer un logement, creer une reservation.
- `test_authentification.py` verifie l'inscription, la connexion, les roles et la limitation des tentatives de connexion.
- `test_logements.py` verifie la gestion des logements, la protection du code d'acces et l'isolation entre proprietaires.
- `test_reservations.py` verifie les reservations manuelles, l'import CSV, l'import iCal et la creation automatique des missions de menage.
- `test_missions.py` verifie l'assignation des missions, la checklist, les statuts et les incidents.
- `test_dashboard.py` verifie que le tableau de bord retourne les bons compteurs selon le role.
- `test_securite_unitaire.py` verifie directement les fonctions de securite : mot de passe, JWT et chiffrement des champs sensibles.
- `test_api_security_flow.py` garde deux tests de parcours complet, proches d'un scenario utilisateur reel.

Les noms des tests sont volontairement explicites et en francais pour montrer clairement ce que chaque test controle.
