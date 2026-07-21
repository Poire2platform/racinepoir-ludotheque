RacinePoir Ludothèque
=====================

Private Flask app for managing a small shared board game library.

Core Concepts
-------------

- A `Game` is the reference title, such as Catan.
- A `Box` is one physical copy of a game.
- A box has an owner and a current holder.
- Scanning a box QR means: "I have this box now."
- Requests are informational/social and do not enforce reservations.

Current Features
----------------

- Login/logout with remembered sessions.
- Admin user management.
- User self-service profile and password update.
- Create and edit boxes.
- Choose an existing game or create a new reference game.
- Owner/admin manual holder transfer.
- QR label page with dynamic QR image.
- Box scan flow with login redirect.
- Box event history.
- Lost/active lifecycle actions for owner/admin.
- Reference game pages with linked boxes.
- BoardGameGeek recognition/enrichment flow.

Development Setup
-----------------

```bash
cd ~/racinepoir-ludotheque
source .venv/bin/activate
python run.py
```

The app runs on:

```text
http://localhost:5000
```

Environment
-----------

Keep secrets in `.env`; do not commit that file.

Required:

```env
DATABASE_URL=postgresql://...
SECRET_KEY=...
```

Optional, for BoardGameGeek enrichment:

```env
BGG_API_TOKEN=...
```

BGG API access currently requires registering an application/token with BoardGameGeek.
Without `BGG_API_TOKEN`, the app still works, but BGG lookup actions show a configuration message.

Development Data
----------------

Seed the dev data from the project root:

```bash
PYTHONPATH=. python scripts/seed_dev.py
```

Dev accounts from the seed script:

```text
admin / admin123
max / max123
anouk / anouk123
frere / frere123
```

QR Labels
---------

Each box has:

- `/boxes/<id>/label` for a printable label
- `/boxes/<id>/qr.png` for the QR image
- `/scan/<token>` as the scan target

For printed QR labels, use a stable hostname/base URL when running the app. A QR printed with a temporary local URL may stop working if the app moves.

Checks
------

Quick syntax check:

```bash
cd app
python3 -m compileall .
```
