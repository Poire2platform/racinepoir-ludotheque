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
- [ ] connexion manuelle avec le mot de passe administratif courant.

Le 29 juillet 2026, le mot de passe de développement documenté `admin123` n’était
plus valide sur SQL101. Ne pas réinitialiser ce mot de passe dans le cadre d’un test
de fumée; le propriétaire doit confirmer ou renouveler l’identifiant séparément.

## Avant un checkpoint

```bash
python -m pytest
python -m compileall app tests scripts
git diff --check
git status --short
```
