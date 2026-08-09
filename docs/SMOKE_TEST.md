# Test de fumée

Cette checklist valide le MVP sans utiliser le seed destructif.

## Vérification automatisée

Depuis la racine du projet :

```bash
python -m pytest
```

Les tests automatisés utilisent SQLite en mémoire. Ils couvrent :

- création de l’application et `/healthz`;
- connexion valide et invalide, compte désactivé, session et déconnexion;
- séparation membre/admin;
- refus des mutations par `GET`;
- rejet de tous les `POST` sans jeton CSRF;
- absence de mutation lors de l’affichage des formulaires;
- permissions des utilisateurs, propriétaires et administrateurs;
- navigation principale et fiches;
- création manuelle d’un jeu et d’une boîte sans BGG;
- création et modification d’une boîte non cataloguée avec `game_id = NULL`;
- recherche et filtres combinables par titre, propriétaire, détenteur et statut;
- ajout idempotent d’un signal « I would like », sans réservation ni annulation;
- scan, changement de détenteur et fulfillment.

## Vérification sur la base de développement

Ces parcours sont en lecture et ne doivent pas modifier SQL01 :

- [x] `/healthz`;
- [x] `/games`;
- [x] `/boxes`;
- [x] `/`;
- [x] fiche d’un jeu;
- [x] fiche d’une boîte;
- [x] scan `GET`, déclenchement automatique du `POST` protégé et résultat;
- [x] `/me/held-boxes`;
- [x] `/me/owned-boxes`;
- [x] `/sessions`;
- [x] `/players`;
- [x] `/users` comme administrateur;
- [x] connexion avec le mot de passe administratif courant.

Le 29 juillet 2026, le mot de passe de développement `admin123` a été renouvelé
avec l’autorisation du propriétaire, puis la connexion réelle sur SQL01 a été
validée.

## Avant un checkpoint

```bash
python -m pytest
python -m compileall app tests scripts
git diff --check
git status --short
```
