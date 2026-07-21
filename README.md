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
- Play session logging with registered users or guest player profiles.
- First player stats pages with played games, high scores, and frequent teammates.

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
flask db upgrade
PYTHONPATH=. python scripts/seed_dev.py
```

Dev accounts from the seed script:

```text
admin / admin123
max / max123
anouk / anouk123
frere / frere123
```

WHC / cPanel Staging Deploy
---------------------------

Assumption: the hosting account supports a Python app through cPanel / Passenger,
with environment variables and a database available.

Suggested staging URL:

```text
https://testmax.yoannpearson.com/
```

Suggested cPanel setup:

1. Create a Python application in cPanel.
2. Use the project folder as the application root.
3. Use `passenger_wsgi.py` as the startup file.
4. Install dependencies from `requirements.txt`.
5. Configure the environment variables:

```env
DATABASE_URL=postgresql://...
SECRET_KEY=...
BGG_API_TOKEN=...
```

`BGG_API_TOKEN` is optional. Without it, the app still works, but BoardGameGeek
lookup/enrichment actions will show a configuration message.

After dependencies and environment variables are set:

```bash
flask db upgrade
```

Optional staging data:

```bash
PYTHONPATH=. python scripts/seed_dev.py
```

Do not run the seed script on a real production database unless you intentionally
want to reset/demo-fill the data.

Deployment notes:

- Keep `.env` and real secrets out of Git.
- Use HTTPS for the public/staging URL before printing real QR labels.
- QR labels should be generated from the final stable hostname, because the QR
  code stores the scan URL.
- If WHC only provides MySQL instead of PostgreSQL, add a MySQL driver and use a
  MySQL `DATABASE_URL` before running migrations.

Self-Hosted Server Deploy
-------------------------

This is the preferred path if the Ludothèque runs on the dedicated home/server
machine and WHC only hosts a public landing page.

Recommended public shape:

```text
Internet
  -> Cloudflare / DNS
  -> reverse proxy on the server
  -> Flask app
  -> local/private database
```

Minimum server checklist:

- Expose only HTTP/HTTPS publicly.
- Keep SSH restricted by firewall, VPN, allowlist, or key-only access.
- Keep the database private; do not expose PostgreSQL/MySQL to the public Internet.
- Put Caddy, Nginx, or another reverse proxy in front of Flask.
- Terminate HTTPS at the reverse proxy.
- Redirect plain HTTP to HTTPS.
- Run the Flask app as a non-root service user.
- Keep real secrets in environment variables or a private `.env` file.
- Run `flask db upgrade` during deploys.
- Back up the database before migrations and on a regular schedule.

Production environment flags when HTTPS is active:

```env
SESSION_COOKIE_SECURE=true
REMEMBER_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SAMESITE=Lax
TRUST_PROXY_HEADERS=true
```

Security notes already enforced by the app:

- POST forms require a session CSRF token.
- Logout and box state changes use POST instead of GET.
- Visiting a scan URL shows a confirmation page before changing the holder.
- Login and scan confirmation routes have simple in-memory rate limits for playtesting.
- Login and scan security events are written through the `racinepoir.security` logger.
- Session cookies are `HttpOnly`.
- Basic browser security headers are sent on every response.
- HSTS is sent when secure cookies are enabled, meaning production should already
  be served through HTTPS before turning those flags on.

Good next hardening steps:

- Move rate limiting to shared storage, such as Redis, if running multiple workers.
- Add richer structured app logs for important security events.
- Add an automated database backup script.
- Add a `/healthz` endpoint for local monitoring.
- Add a production service file, such as systemd, once the server path is known.

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
