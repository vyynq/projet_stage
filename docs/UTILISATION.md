# Documentation utilisateur

## Roles

- `admin` : gere les utilisateurs, les logements, les reservations et les missions.
- `proprietaire` : gere uniquement ses logements, reservations et missions associees.
- `responsable_conciergerie` : supervise les logements, reservations, missions et assignations.
- `agent_menage` : consulte uniquement ses missions assignees, coche la checklist, change le statut et signale les incidents.

## Parcours type

1. Un administrateur cree les comptes des responsables et agents.
2. Un proprietaire ou administrateur cree un logement avec adresse et code d'acces.
3. Une reservation est ajoutee manuellement ou importee par CSV.
4. Une reservation peut aussi venir d'un calendrier Airbnb, Booking, Vrbo ou autre via iCal.
5. L'application cree automatiquement une mission de menage a la date de depart.
6. Un admin ou responsable assigne la mission a un agent.
7. L'agent consulte la mission, coche la checklist et signale un incident avec photo si besoin.
8. Quand la mission passe en `termine`, le logement repasse au statut `pret`.

## Interface web

L'interface est disponible a la racine de l'application :

```text
http://localhost:8000
```

Les onglets principaux sont :

- Dashboard : suivi global des compteurs.
- Logements : creation et consultation des logements, consultation controlee du code d'acces.
- Reservations : creation manuelle et import CSV.
- Import calendrier : synchronisation iCal Airbnb, Booking, Vrbo ou autre.
- Missions : assignation, statut, checklist et incidents.
- Utilisateurs : creation d'utilisateurs par un administrateur.

## Import CSV

Colonnes obligatoires :

```csv
date_arrivee,date_depart,voyageur_nom
```

Colonne optionnelle :

```csv
voyageur_contact
```

Les dates doivent etre au format ISO, par exemple :

```csv
date_arrivee,date_depart,voyageur_nom,voyageur_contact
2026-07-10T15:00:00,2026-07-12T11:00:00,Camille Martin,camille@example.com
```

## Photos d'incident

Formats acceptes :

- JPG
- PNG
- WEBP

Taille maximale : 5 Mo.

## Import calendrier iCal

Les plateformes comme Airbnb, Booking ou Vrbo proposent generalement un export calendrier au format iCal.
Dans l'onglet Reservations :

1. Choisir le logement.
2. Choisir la plateforme.
3. Coller l'URL iCal ou envoyer un fichier `.ics`.
4. Cliquer sur Synchroniser.

Les doublons sont evites quand le calendrier fournit un identifiant `UID`.
