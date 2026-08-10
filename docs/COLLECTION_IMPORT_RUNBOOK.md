# Import de la collection officielle

La source fournie contient 97 jeux et 97 boîtes. Elle demeure hors Git :

```text
/home/pmax/racinepoire-ludotheque/Anouk.html
```

La commande `flask import-official-collection` lit l’export HTML de la feuille,
ne crée jamais d’utilisateur et fonctionne en aperçu sans écriture par défaut.
Elle réutilise les jeux dont le titre existe déjà et identifie chaque boîte de
la collection par un jeton stable; une seconde exécution ne crée donc aucun
doublon.

## Correspondances validées

```text
Anouk  -> Anouk
Maxika -> Maxika
Anika  -> Maxika
Maxime -> Maxika
détenteur vide -> admin
Anouk et Maxika -> Anouk
```

Tous les comptes cités doivent exister avant l’import. Les correspondances sont
passées explicitement à chaque exécution; l’import s’arrête si une valeur ou un
compte manque.

## Aperçu obligatoire

```bash
flask import-official-collection \
  --source /chemin/prive/Anouk.html \
  --user-map Anouk=Anouk \
  --user-map Maxika=Maxika \
  --user-map Anika=Maxika \
  --user-map Maxime=Maxika \
  --default-holder admin
```

Le résultat attendu sur une base vide est `97` lignes, `97` jeux à créer et
`97` boîtes à créer, avec aucune correspondance ni aucun compte manquant.

## Écriture contrôlée

Après sauvegarde PostgreSQL et validation explicite de l’aperçu, reprendre la
même commande avec `--apply`. Relancer ensuite l’aperçu : il doit annoncer
`0` jeu et `0` boîte à créer, avec `97` boîtes existantes.

Ne jamais mettre la source, un mot de passe, un code d’invitation ou le contenu
de `.env` dans Git, une capture ou un journal.

## Exécution production du 10 août 2026

- sauvegarde préalable :
  `racinepoir_ludotheque_prod-pre-import-20260810T194144Z.dump`;
- SHA-256 :
  `e91ffd525902c49dc21ccbd0277f30ba3a2c8da5c1739cf34fcff28b18ad2441`;
- archive vérifiée lisible, `postgres:postgres`, mode `0600`, 39 265 octets;
- aperçu : 97 jeux et 97 boîtes à créer, aucune anomalie;
- import appliqué : 97 jeux et 97 boîtes créés;
- second aperçu : 0 création, 97 jeux et 97 boîtes existants;
- `/healthz` local et public : `status: ok`, `database: ok` après l’import.
