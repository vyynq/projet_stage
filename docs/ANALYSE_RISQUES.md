# Analyse courte des risques cybersecurite

## Donnees sensibles

- Adresses de logements.
- Codes de boites a cles.
- Coordonnees voyageurs.
- Photos d'incidents.
- Historique des interventions.

## Risques principaux et protections

| Risque | Impact | Protection actuelle |
| --- | --- | --- |
| Vol de mot de passe | Acces non autorise aux donnees | Mots de passe hashes avec bcrypt |
| Consultation du code d'acces par un mauvais utilisateur | Acces physique au logement | Controle par role et ownership, journalisation |
| IDOR sur une mission | Un agent voit ou modifie une mission d'un autre agent | Filtrage des missions par `agent_id` et verification avant modification |
| Modification frauduleuse d'une reservation | Planning de menage incorrect | Routes protegees par JWT et roles |
| Fuite de photos | Exposition d'informations sur un bien | Upload local limite en type et taille |
| Bruteforce login | Compromission de compte | Limitation simple des tentatives par identifiant |
| Injection ou donnees invalides | Erreurs applicatives ou corruption | Validation Pydantic et ORM SQLAlchemy |

## Points a renforcer avant production

- Remplacer `create_all` par des migrations Alembic.
- Stocker les uploads hors du dossier applicatif avec controle d'acces plus strict.
- Ajouter un antivirus ou scan de contenu sur les fichiers uploades.
- Mettre en place HTTPS obligatoire derriere un reverse proxy.
- Renforcer la politique de mot de passe et ajouter une rotation des secrets.
- Ajouter des tests OWASP ZAP sur une instance lancee.
- Ajouter des logs centralises et alertes sur les actions sensibles.
- Prevoir une suppression ou anonymisation des donnees voyageurs apres delai legal.
