# RacinePoir — Box model v1

Ce paquet remplace le modèle autour de `Box`.

Ancien vocabulaire retiré :
- GameCopy
- CopyEvent
- Location
- current_location
- wanted_location

Nouveau vocabulaire :
- Game = fiche de référence optionnelle
- Box = boîte physique réelle, noyau du système
- BoxEvent = historique d'une boîte

Routes principales :
- `/boxes`
- `/boxes/<id>`
- `/scan/<token>`
- `/scan/<token>/confirm`
- `/games`

Anciens liens :
- `/copies` redirige vers `/boxes`
- `/copies/<id>` redirige vers `/boxes/<id>`

Installation des fichiers :

```bash
cd ~/racinepoir-ludotheque
unzip ~/Downloads/racinepoir_box_model_v1.zip -d .
```

Reset dev DB recommandé :

```bash
cd ~/racinepoir-ludotheque
source .venv/bin/activate

git status
git add .
git commit -m "Checkpoint before box model reset"
logthis "Ludothèque: checkpoint avant reset vers modèle Box"

rm -rf migrations

psql -h 192.168.18.30 -U racinepoir_app -d racinepoir_ludotheque -c "
DROP TABLE IF EXISTS box_events, boxes, copy_events, game_copies, locations, games, users, alembic_version CASCADE;
"

flask db init
flask db migrate -m "Create box model"
flask db upgrade

PYTHONPATH=. python scripts/seed_dev.py
```

Test :

```bash
python run.py
```

Pages à vérifier :
- `/login`
- `/boxes`
- `/boxes/1`
- `/scan/dev-catan-box-001`
- `/games`

Après validation :

```bash
git status
git add .
git commit -m "Rename copies to boxes and repair data model"
logthis "Ludothèque: modèle réparé autour des boîtes physiques"
```
