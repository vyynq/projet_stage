# Airbnb Menage

Prototype web securise pour gerer des logements en location courte duree, les reservations, les missions de menage, les checklists et les incidents.

## Lancer l'application

```bash
cp .env.example .env
# Modifier SECRET_KEY et FIELD_ENCRYPTION_KEY avec deux valeurs fortes.
docker compose up --build
```

Application web : http://localhost:8000  
API Swagger : http://localhost:8000/docs  
Sante API : http://localhost:8000/health

Pour tester sans Docker avec SQLite :

```bash
python3.10 -m venv .venv
.venv/bin/pip install -r requirements-local.txt
DATABASE_URL=sqlite:///./dev_airbnb_menage.db .venv/bin/uvicorn app.main:app --reload
```

Si `python3.10` n'est pas dans le PATH sur macOS, utiliser :

```bash
/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m venv .venv
```

## Premier demarrage

1. Creer le premier compte via l'onglet Inscription avec le role `Administrateur initial`.
2. Se connecter avec ce compte.
3. Creer les utilisateurs necessaires dans l'onglet Utilisateurs : proprietaire, responsable conciergerie, agent de menage.
4. Creer un logement, puis une reservation. Une mission de menage est automatiquement creee a la date de depart.
5. Assigner la mission a un agent, cocher la checklist, signaler un incident si besoin, puis passer le statut a `termine`.

## Fonctionnel aujourd'hui

- Interface web servie par FastAPI.
- Authentification email/mot de passe, mots de passe hashes, JWT.
- Verification email par code a 6 chiffres avant connexion pour les inscriptions publiques.
- Roles : admin, proprietaire, responsable conciergerie, agent_menage.
- Creation d'utilisateurs par admin.
- Creation, consultation, modification et suppression de logements.
- Code d'acces chiffre en base et consultable uniquement par les roles autorises.
- Creation de reservations et import CSV.
- Import calendrier iCal pour Airbnb, Booking, Vrbo ou autre calendrier.
- Generation automatique d'une mission et d'une checklist apres chaque reservation.
- Assignation des missions aux agents.
- Vue missions filtree : un agent ne voit que ses propres missions.
- Checklist cochable par l'agent assigne.
- Statuts : a_faire, en_cours, termine, probleme_signale.
- Signalement d'incidents avec commentaire, URL de photo ou upload local JPG/PNG/WEBP.
- Tableau de bord avec compteurs logements, reservations, missions et incidents.
- Journalisation des actions sensibles.
- Limitation simple des tentatives de connexion.
- Tests automatises du flux securise principal.

## Import CSV reservations

Le fichier doit contenir les colonnes suivantes :

```csv
date_arrivee,date_depart,voyageur_nom,voyageur_contact
2026-07-10T15:00:00,2026-07-12T11:00:00,Camille Martin,camille@example.com
```

## Import calendrier Airbnb / Booking / Vrbo

Dans l'onglet Reservations, utiliser `Import calendrier` avec une URL iCal ou un fichier `.ics`.
Chaque evenement importe cree automatiquement une reservation et une mission de menage.

## Tests

```bash
.venv/bin/python -m pytest -q
```

Derniere verification locale : `37 passed`.

## Limites restantes

- Pas encore de migrations Alembic appliquees : le prototype utilise `create_all` au demarrage.
- Pas encore de stockage objet pour les photos ; en cloud, utiliser un disque persistant ou S3-compatible.
- Pas encore de calendrier visuel avance ; le planning est consultable via la liste des missions.
- Les tests OWASP ZAP et Postman restent a executer en environnement lance.

Voir aussi :

- `docs/UTILISATION.md`
- `docs/ANALYSE_RISQUES.md`
- `docs/DEPLOIEMENT_CLOUD.md`
