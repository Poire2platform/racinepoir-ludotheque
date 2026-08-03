# RacinePoir Ludothèque — plan infra

Ce document est la source de vérité courte pour l’infrastructure cible.

## Clarification importante

`pmax-host` n’est pas le serveur de production.

- `pmax-host` = machine de développement contrôlée.
- `WEB01` = futur serveur applicatif dédié.
- `SQL101` = serveur PostgreSQL séparé.

Le projet est développé et testé sur `pmax-host`, mais le déploiement sérieux
doit se faire sur une nouvelle VM dédiée.

## Architecture cible

```text
Windows / VS Code / Codex
        ↓ SSH
pmax-host
        ↓ git / copie / déploiement
WEB01 — Flask / Gunicorn / Caddy / systemd
        ↓ LAN
SQL101 — PostgreSQL
```

Flux applicatif prévu :

```text
Client web
  → Caddy
  → Gunicorn
  → Flask app
  → PostgreSQL sur SQL101
```

## Machines

### DEV — pmax-host

- Rôle : développement seulement.
- IP locale actuelle : `192.168.18.18`.
- Projet : `~/racinepoir-ludotheque`.
- Usage : VS Code, Codex, tests contrôlés, Git.
- Pas destiné à rester le serveur public final.

### APP — WEB01

- Rôle : serveur applicatif Ludothèque.
- Statut : VM créée; SSH et DNS fonctionnels.
- OS recommandé : Ubuntu Server LTS.
- IP locale : `192.168.18.38`.
- Nom : `WEB01` / `poire1-ludoweb`.
- Doit rester allumée 24/7 : oui.

Services prévus :

- Flask app.
- Gunicorn.
- Caddy.
- systemd service.
- accès réseau vers SQL101.

Specs recommandées :

- CPU : 1 à 2 vCPU.
- RAM : 2 Go.
- Disque : 20 à 32 Go.

### DB — SQL101

- Rôle : serveur PostgreSQL séparé.
- VMID Proxmox : `101`.
- IP locale : `192.168.18.30`.
- Database : `racinepoir_ludotheque`.
- User applicatif : `racinepoir_app`.
- Database production choisie : `racinepoir_ludotheque_prod`.
- User applicatif production prévu : `racinepoir_prod`.
- PostgreSQL : déjà fonctionnel.

Choix important : on garde PostgreSQL sur SQL101. On ne met pas PostgreSQL
localement sur WEB01 pour l’instant, parce que la séparation app/DB est déjà en
place, testée, et plus propre.

### Hyperviseur — Poire1

- Rôle : Proxmox host.
- IP locale : `192.168.18.100`.

### DNS local

- VM DNS : `poire1-dns`.
- IP : `192.168.18.34`.
- Zone locale : `home.arpa`.
- Nom local futur possible : `ludotheque.home.arpa`.

## Domaine public envisagé

- Domaine futur : `ludotheque.filsdepoire.ca`.
- DNS public : probablement Cloudflare.

Le projet reste en mode LAN/dev tant que WEB01, Caddy, HTTPS et les backups ne
sont pas prêts.

## Proxy / HTTPS

Choix recommandé : Caddy.

Raisons :

- configuration simple;
- HTTPS automatique;
- bon choix pour petit serveur Flask/Gunicorn.

## Prochaine étape infra

Préparer la base et le rôle de production séparés sur SQL101, puis préparer
WEB01 sans installer de service applicatif directement sur l’hyperviseur Poire1.
La procédure contrôlée est dans `docs/PRODUCTION_DATABASE.md`.

Checklist WEB01 :

- Ubuntu Server LTS.
- 1–2 vCPU.
- 2 Go RAM.
- 20–32 Go disque.
- réseau LAN sur `vmbr0`.
- IP réservée ou fixe.
- SSH fonctionnel.
- user sudo créé.

Test minimal attendu :

```bash
ssh user@IP_WEB01
```

Quand ce test fonctionne, on peut passer à :

1. installation paquets Python/Git/Caddy;
2. clone ou copie du repo;
3. création du `.env` production;
4. test connexion vers SQL101;
5. service systemd Gunicorn;
6. reverse proxy Caddy;
7. backup PostgreSQL.
