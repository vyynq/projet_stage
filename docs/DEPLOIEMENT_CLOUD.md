# Deploiement cloud

## Architecture cible

L'application est prete pour ce schema :

- Service web FastAPI qui sert aussi l'interface HTML/CSS/JS.
- Base PostgreSQL managée.
- Variables d'environnement pour les secrets.
- Dossier persistant pour les photos d'incident.
- Route `/health` pour verifier que le service est disponible.

## Variables obligatoires

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
SECRET_KEY=valeur_longue_aleatoire
FIELD_ENCRYPTION_KEY=autre_valeur_longue_aleatoire
CORS_ORIGINS=https://votre-domaine.example.com
UPLOAD_DIR=/app/app/uploads
ACCESS_TOKEN_EXPIRE_MINUTES=30
LOGIN_WINDOW_SECONDS=60
LOGIN_MAX_ATTEMPTS=5
EMAIL_DELIVERY_MODE=console
```

Pour generer les secrets :

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Option recommandee : Render

1. Pousser le projet sur GitHub.
2. Creer un `Blueprint` Render depuis le fichier `render.yaml`.
3. Laisser Render creer la base PostgreSQL.
4. Renseigner manuellement :
   - `SECRET_KEY`
   - `FIELD_ENCRYPTION_KEY`
   - `CORS_ORIGINS`
5. Deployer.
6. Ouvrir l'URL Render et creer le premier compte admin.

## Verification email

Par defaut, `EMAIL_DELIVERY_MODE=console` affiche le code de verification dans les logs du service Render.
C'est suffisant pour une demonstration ou un test.

Pour envoyer le code par vrai email, configurer un service SMTP et ajouter ces variables dans Render :

```text
EMAIL_DELIVERY_MODE=smtp
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=compte@example.com
SMTP_PASSWORD=mot_de_passe_smtp
SMTP_FROM=no-reply@example.com
SMTP_USE_TLS=true
```

Apres inscription, l'utilisateur doit entrer le code recu avant de pouvoir se connecter.

Important : pour garder les photos apres redemarrage, ajouter un disque persistant ou passer a un stockage objet. Sans disque persistant, les uploads locaux peuvent etre perdus selon la plateforme.

## Option Railway

1. Pousser le projet sur GitHub.
2. Creer un projet Railway depuis le repository.
3. Ajouter un service PostgreSQL.
4. Configurer les variables depuis `.env.cloud.example`.
5. Railway utilisera le `Dockerfile` et `railway.json`.

## Verification apres deploiement

Tester :

```text
https://votre-url-cloud/health
https://votre-url-cloud/docs
https://votre-url-cloud/
```

Puis verifier le parcours :

1. Creation du premier admin.
2. Creation d'un proprietaire et d'un agent.
3. Creation d'un logement.
4. Import CSV ou calendrier Airbnb/Booking/Vrbo.
5. Mission creee automatiquement.
6. Assignation a un agent.
7. Checklist cochee.
8. Incident avec photo.
9. Statut `termine`.

## Fonctionnalites proches Lodgify / Turno / Guesty / Breezeway

- Lodgify : reservations, logements, tableau de bord, import calendrier.
- Turno : reservation vers mission de menage automatique, assignation agent, checklist, photos, statut termine.
- Guesty : gestion multi-logements, roles, suivi conciergerie.
- Breezeway : menage, incidents, photos et suivi terrain.

Ce prototype ne remplace pas encore ces produits en production, mais il pose la base technique pour construire ces parcours.
