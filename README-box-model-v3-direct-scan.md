# RacinePoir — Box model v3 direct scan

Cette version garde le modèle `Box` + `BoxRequest` et change le comportement mobile.

Changement principal :
- `/scan/<token>` agit directement.
- Si le user n’est pas connecté, Flask-Login redirige vers `/login?next=/scan/<token>`.
- Après login, le scan continue.
- La session utilise `remember=True`.

Installation :

```bash
cd ~/racinepoir-ludotheque
unzip -o ~/Downloads/racinepoir_box_model_v3_direct_scan.zip -d .
```

Si tu n’as pas encore appliqué le modèle Box/waitlist, fais le reset DB dev :

```bash
cd ~/racinepoir-ludotheque
source .venv/bin/activate

git status
git add .
git commit -m "Checkpoint before direct scan model reset"
logthis "Ludothèque: checkpoint avant reset modèle Box direct scan"

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
- Ouvre une fenêtre privée ou logout.
- Va directement à `/scan/dev-catan-box-001`.
- Login avec `max / max123`.
- Tu dois revenir automatiquement au scan.
- La boîte doit devenir entre les mains de Max.
