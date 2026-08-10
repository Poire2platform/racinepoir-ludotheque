# Enrichissement BGG en lots

La collection ne doit pas être réimportée ni remise à zéro pour ajouter les
données BoardGameGeek. Les références existantes peuvent être enrichies sans
rompre leurs liens avec les boîtes, propriétaires, détenteurs ou historiques.

## Aperçu sans écriture

Sur WEB01, produire un manifeste privé avec une pause de deux secondes entre
les recherches :

```bash
cd /opt/racinepoir
.venv/bin/flask preview-bgg-enrichment \
  --output /var/lib/racinepoir-import/bgg-preview.json \
  --delay 2
```

La commande inspecte seulement les jeux sans `bgg_id`. Elle recherche jusqu’à
huit candidats et sélectionne automatiquement uniquement un titre normalisé
exact et unique. Un premier résultat partiel n’est jamais retenu : par exemple,
`5211: Azul` est ignoré au profit de l’exact `Azul` BGG #230802.

Le manifeste classe chaque jeu :

- `exact_unique` : admissible à l’enrichissement automatique;
- `exact_ambiguous` : plusieurs titres exacts, décision humaine requise;
- `no_exact` : aucun titre exact, décision humaine requise;
- `error` : appel BGG échoué, à reprendre plus tard.

L’aperçu ne modifie jamais la base. Le fichier contient seulement des données
publiques BGG et des identifiants locaux, mais il demeure hors Git.

## Application contrôlée

Après validation du résumé, sauvegarde PostgreSQL fraîche et inspection du
manifeste, enrichir uniquement les correspondances `exact_unique` :

```bash
.venv/bin/flask apply-bgg-enrichment \
  --manifest /var/lib/racinepoir-import/bgg-preview.json \
  --delay 2 \
  --apply
```

Chaque jeu est vérifié à nouveau avant écriture. Un jeu déjà lié, supprimé,
renommé ou en conflit avec un `bgg_id` existant est ignoré ou signalé. Les
ambiguïtés restent inchangées pour une révision manuelle.

Le jeton BGG reste dans `/home/pmax/.config/racinepoir/bgg_token`, mode `0600`,
et son chemin est fourni par `BGG_API_TOKEN_FILE`. Ne jamais afficher le jeton.

Références :

- <https://boardgamegeek.com/using_the_xml_api>
- <https://boardgamegeek.com/wiki/page/bgg_xml_api2>
