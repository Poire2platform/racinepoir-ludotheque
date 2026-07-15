# RacinePoir — Box model v2 avec file d’attente

Nouveau modèle :
- `Box` = boîte physique réelle
- `Game` = fiche de référence optionnelle
- `BoxRequest` = entrée dans la file d’attente d’une boîte
- `BoxEvent` = historique

Installation :

```bash
cd ~/racinepoir-ludotheque
unzip -o ~/Downloads/racinepoir_box_model_v2_waitlist.zip -d .
```

Reset DB dev recommandé :

```bash
cd ~/racinepoir-ludotheque
source .venv/bin/activate

git status
git add .
git commit -m "Checkpoint before box waitlist model reset"
logthis "Ludothèque: checkpoint avant reset vers modèle Box avec file d’attente"

rm -rf migrations

psql -h 192.168.18.30 -U racinepoir_app -d racinepoir_ludotheque -c "
DROP TABLE IF EXISTS box_events, box_requests, boxes, copy_events, game_copies, locations, games, users, alembic_version CASCADE;
"

flask db init
flask db migrate -m "Create box waitlist model"
flask db upgrade

PYTHONPATH=. python scripts/seed_dev.py
```

Test :
- `/login`
- `/boxes`
- `/boxes/1`
- `/scan/dev-catan-box-001`
- `/games`
