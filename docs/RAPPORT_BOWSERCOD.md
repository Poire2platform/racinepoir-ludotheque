# Rapport de relève pour BowserCod

**Projet :** RacinePoir Ludothèque

**État vérifié :** 10 août 2026

**Branche :** `repair/manual-stabilization-2026-07-29`

## Résumé exécutif

La ludothèque est maintenant publiée sur Internet à l’adresse
<https://ludotheque.filsdepoire.ca> par un Cloudflare Tunnel sortant. Aucun
port HTTP/HTTPS n’est redirigé depuis le WAN vers WEB01. L’application Flask
fonctionne sous Gunicorn derrière Caddy et utilise la base PostgreSQL de SQL01.

La collection officielle a été importée en production : 97 jeux, 97 boîtes et
97 événements de création. Un second aperçu a reconnu les 97 jeux et boîtes et
n’a proposé aucune création, ce qui valide l’idempotence de l’import.

## État Git et déploiement

| Élément | Valeur |
|---|---|
| Dépôt local et `origin` | `2ee9bf8` — `Record official collection import` |
| Commit applicatif exécuté sur WEB01 | `afa17e3` — `Add controlled collection import` |
| Différence | `2ee9bf8` ajoute seulement le compte rendu documentaire post-import |
| Tests locaux | 102 réussis, 117 avertissements de dépréciation connus |

Deux fichiers locaux demeurent volontairement hors Git :

- `docs/OFFICIAL_COLLECTION_IMPORT.md`;
- `docs/runtoken.sh`, vide lors de la dernière vérification.

Ne pas les ajouter automatiquement et ne jamais utiliser `git add -A`.

## Architecture active

```text
Internet
  -> Cloudflare HTTPS
  -> tunnel racinepoir-web01
  -> cloudflared sur WEB01
  -> Caddy sur 127.0.0.1:80
  -> Gunicorn sur 127.0.0.1:8000
  -> Flask
  -> PostgreSQL SQL01:5432
```

| Composant | État vérifié |
|---|---|
| WEB01 | VMID 104, IP DMZ `10.10.20.10`, hostname `poire1-ludoweb` |
| RacinePoir | service `active`, commit applicatif `afa17e3` |
| cloudflared | service `active`, version 2026.7.3 |
| Tunnel | `racinepoir-web01`, une réplique, statut Healthy |
| URL publique | `https://ludotheque.filsdepoire.ca` |
| Santé | `/healthz` local et public : `status: ok`, `database: ok` |
| SQL01 | `192.168.18.30`, base `racinepoir_ludotheque_prod` |

pfSense autorise depuis WEB01 : DNS, PostgreSQL ciblé vers SQL01, Cloudflare
TCP/UDP 7844 et mises à jour TCP 80/443. L’adresse NAT observée par PostgreSQL
est `192.168.18.41`; la règle HBA est limitée à cette source `/32`.

## Publication et sécurité

- HTTPS public et certificat Cloudflare validés.
- Cookies observés : `Secure`, `HttpOnly`, `SameSite=Lax`.
- `APP_BASE_URL=https://ludotheque.filsdepoire.ca` appliquée sur WEB01.
- Aucun token Cloudflare ou secret applicatif ne doit être copié dans Git, une
  conversation, une capture, une commande historisée ou `logthis`.
- Le token du tunnel est stocké dans `/etc/cloudflared/tunnel-token`, propriétaire
  `root:cloudflared`, mode `0640`.
- L’accès Codex passe par `deploy-racinepoir` et le wrapper limité
  `/usr/local/sbin/racinepoir-ops`.

Le routeur domestique `192.168.18.1` a conservé une réponse DNS négative après
la création du hostname. Le DNS interne `192.168.18.34` et Cloudflare `1.1.1.1`
résolvent correctement le domaine. Le DHCP du réseau client devrait distribuer
ces résolveurs afin d’éviter une configuration manuelle sur chaque appareil.

## Inscriptions

L’auto-inscription contrôlée est activée par :

```dotenv
REGISTRATION_INVITE_ENABLED=true
```

Le code d’invitation est quotidien, stable entre les workers Gunicorn et dérivé
du secret serveur. Pour l’afficher uniquement dans un terminal privé sur WEB01 :

```bash
cd /opt/racinepoir
.venv/bin/flask show-registration-invite
```

Ne jamais inscrire ce code dans ce rapport ou dans Git. Le compte administrateur
production existe sous le username `admin`, affiché « Maxime »; son mot de passe
n’est pas connu de Codex et n’est pas conservé en clair.

## Import de la collection officielle

Source privée installée sur WEB01 :

```text
/var/lib/racinepoir-import/Anouk.html
```

Correspondances validées et appliquées :

```text
Anouk -> compte Anouk
Maxika -> compte Maxika
Anika -> compte Maxika
Maxime -> compte Maxika
détenteur vide -> compte admin
Anouk et Maxika -> compte Anouk
```

Sauvegarde préalable SQL01 :

```text
/var/backups/postgresql/racinepoir/
racinepoir_ludotheque_prod-pre-import-20260810T194144Z.dump
```

- propriétaire `postgres:postgres`;
- mode `0600`;
- taille 39 265 octets;
- SHA-256 :
  `e91ffd525902c49dc21ccbd0277f30ba3a2c8da5c1739cf34fcff28b18ad2441`;
- archive validée avec `pg_restore --list`.

La commande d’import fonctionne en aperçu par défaut. Ne jamais ajouter
`--apply` sans sauvegarde récente et validation humaine de l’aperçu. La
procédure complète est dans `docs/COLLECTION_IMPORT_RUNBOOK.md`.

## Infrastructure et récupération déjà validées

- Administrateur production créé et connexion antérieurement validée.
- Premier dump PostgreSQL vérifié, puis sauvegarde pré-import vérifiée.
- WEB01 activé au démarrage de Proxmox.
- Snapshot `web01-post-deploy-20260810` présent.
- Thin-pool `local-lvm` observé à 40,73 % de données et 3,50 % de métadonnées.
- Révocation et restauration de la clé WEB01 testées.
- Snapshot et sauvegarde ne remplacent pas un test de restauration.

## Travail restant, dans l’ordre

1. `PUB-06` — valider un QR définitif avec une boîte de test autorisée.
2. `PUB-07` — tester le site depuis LTE/5G, Wi-Fi désactivé.
3. `PUB-08` — confirmer hors réseau que 5432 et 8000 ne sont pas exposés
   directement par l’origine/WAN.
4. `PUB-09` — smoke test authentifié : admin, membre, permissions, déconnexion,
   scan direct et absence de fuite technique.
5. `PUB-10` — créer le tag et le journal de première publication seulement
   après les quatre validations précédentes.
6. `OPS-01` à `OPS-10` — automatiser les sauvegardes, ajouter une copie hors
   SQL01, définir la rétention, tester une restauration et installer le
   monitoring.

## Règles de conduite pour la relève

- Inspecter `docs/PROJECT_BOARD.md` et `git status` avant toute modification.
- Une carte à la fois : changement ciblé, test, commit, puis `logthis`.
- Ne pas modifier la base production sans aperçu, sauvegarde et autorisation.
- Ne jamais créer silencieusement les utilisateurs manquants pendant un import.
- Ne pas exposer PostgreSQL, Gunicorn, SSH ou un secret par Cloudflare.
- Conserver séparées les étapes code, déploiement, migration et opération
  destructive.
- Préserver les changements non liés et les fichiers non suivis de Maxime.

## Documents de référence

- `docs/PROJECT_BOARD.md`
- `docs/CLOUDFLARE_TUNNEL.md`
- `docs/COLLECTION_IMPORT_RUNBOOK.md`
- `docs/WEB01_DEPLOYMENT.md`
- `docs/WEB01_CODEX_ACCESS.md`
- `docs/PRODUCTION_DATABASE.md`
- `docs/INTERN_PRODUCTION_SMOKE_TEST.md`
- `docs/infra-plan.md`
