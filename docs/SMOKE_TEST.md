# Test de fumée

Cette checklist valide le MVP sans utiliser le seed destructif.

## Vérification automatisée

Depuis la racine du projet :

```bash
python -m pytest
```

Les tests automatisés utilisent SQLite en mémoire. Ils couvrent :

- création de l’application et `/healthz`;
- connexion valide et invalide;
- séparation membre/admin;
- refus des mutations par `GET`;
- rejet de tous les `POST` sans jeton CSRF;
- absence de mutation lors de l’affichage des formulaires;
- permissions des utilisateurs, propriétaires et administrateurs;
- navigation principale et fiches;
- création manuelle d’un jeu et d’une boîte sans BGG;
- création et annulation d’une demande;
- scan, changement de détenteur et fulfillment.

## Vérification sur la base de développement

Ces parcours sont en lecture et ne doivent pas modifier SQL101 :

- [x] `/healthz`;
- [x] `/games`;
- [x] `/boxes`;
- [x] `/`;
- [x] fiche d’un jeu;
- [x] fiche d’une boîte;
- [x] scan `GET` et écran de confirmation;
- [x] `/me/held-boxes`;
- [x] `/me/owned-boxes`;
- [x] `/sessions`;
- [x] `/players`;
- [x] `/users` comme administrateur;
- [x] connexion avec le mot de passe administratif courant.

Le 29 juillet 2026, le mot de passe de développement `admin123` a été renouvelé
avec l’autorisation du propriétaire, puis la connexion réelle sur SQL101 a été
validée.

## Avant un checkpoint

```bash
python -m pytest
python -m compileall app tests scripts
git diff --check
git status --short
```
