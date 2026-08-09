# Déploiement WEB01

Ce document décrit le premier déploiement LAN validé le 4 août 2026. Il ne
contient aucun secret et ne remplace pas les fichiers privés du serveur.

## État déployé

| Élément | Valeur |
|---|---|
| Serveur | `WEB01` / `poire1-ludoweb` |
| Adresse actuelle | `10.10.20.10/24` dans DMZ, passerelle `10.10.20.1` |
| Répertoire | `/opt/racinepoir` |
| Branche | `repair/manual-stabilization-2026-07-29` |
| Dépôt | `Poire2platform/racinepoir-ludotheque` |
| Environnement Python | `/opt/racinepoir/.venv` |
| Gunicorn | 26.0.0, deux workers, `127.0.0.1:8000` uniquement |
| Service systemd | `racinepoir.service`, activé et actif |
| Reverse proxy | Caddy, HTTP sur le port 80 |

La configuration privée se trouve dans `/opt/racinepoir/.env`, créée depuis
`.env.example` avec les permissions `600`. Elle contient une `SECRET_KEY`
aléatoire et la connexion PostgreSQL; elle ne doit jamais être copiée dans Git,
la documentation ou les journaux.

## Base de production

- Serveur PostgreSQL : `192.168.18.30`.
- Base : `racinepoir_ludotheque_prod`.
- Rôle applicatif : `racinepoir_prod`.
- SSL : obligatoire avec `sslmode=require`.
- Migrations appliquées : `6f4a524a0619` (box waitlist), `9a1f4e5d8c20`
  (game sessions) et `b7c3d4e5f6a7` (game ratings).

## Artefacts reproductibles

- `requirements-production.txt` ajoute Gunicorn aux dépendances applicatives.
- `deploy/racinepoir.service` représente le service systemd validé.
- `deploy/Caddyfile` représente le reverse proxy LAN actuel.
- `docs/WEB01_CODEX_ACCESS.md` et `deploy/web01-access/` décrivent l’accès SSH
  en écriture dédié installé le 9 août 2026 et ses limites.

Le checkout WEB01 demeure propre au commit `c3711c2`. Le dépôt de développement
et sa branche distante sont synchronisés au commit `b012a0c`; les six commits de
`e444c30` à `b012a0c` sont poussés, mais ne sont pas encore déployés sur WEB01.
Ils couvrent la documentation du déploiement LAN, le scan direct sans
confirmation, la commande contrôlée de création d’administrateur, les artefacts
d’accès WEB01, l’activation du montage SSHFS et la réconciliation de l’état DMZ.

## Effet de la segmentation sur Caddy et Gunicorn

La configuration active reste correcte pour l’état transitoire : Caddy écoute
sur le port 80 de WEB01 et transmet à Gunicorn sur `127.0.0.1:8000`. Le contrôle
du 9 août a obtenu HTTP 302 directement auprès des deux services. Leur liaison
locale n’explique donc pas la panne de `/healthz`.

Si le proxy et l’application sont séparés conformément à l’architecture cible,
ne pas réutiliser cette configuration telle quelle :

- placer Caddy dans DMZ et Gunicorn dans APP;
- faire écouter Gunicorn sur l’adresse APP prévue, jamais sur une adresse WAN;
- remplacer la cible locale de `reverse_proxy` par l’adresse APP de Gunicorn;
- n’autoriser dans pfSense que le proxy DMZ vers ce port TCP 8000;
- valider Caddy, `/healthz`, les en-têtes de proxy et les cookies sécurisés avant
  la publication HTTPS.

Après copie contrôlée sur WEB01 :

```bash
sudo cp deploy/racinepoir.service /etc/systemd/system/racinepoir.service
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl daemon-reload
sudo systemctl enable --now racinepoir.service
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Ces commandes modifient le serveur et doivent être exécutées par Maxime après
comparaison avec sa configuration en place. Elles ne doivent pas écraser un
fichier contenant des adaptations non reportées dans le dépôt.

## Validation effectuée

La chaîne suivante répond correctement :

```text
Caddy -> Gunicorn -> Flask -> PostgreSQL
```

- `http://192.168.18.38/` est accessible depuis Windows.
- `http://192.168.18.38/healthz` retourne HTTP 200.
- `/healthz` rapporte `status: ok` et `database: ok`.

Ces résultats décrivent la validation initiale du 4 août à l’ancienne adresse
`192.168.18.38`. Lors du contrôle du 9 août, WEB01 avait été déplacée vers
`10.10.20.10` dans la DMZ. Gunicorn et Caddy répondaient toujours localement,
mais les connexions TCP vers PostgreSQL à `192.168.18.30:5432` et vers
`10.10.40.10:5432` expiraient. `/healthz` bloquait et les journaux Gunicorn
montraient des workers arrêtés puis relancés après timeout. Rétablir et limiter
le flux PostgreSQL avant tout redéploiement ou nouvelle affirmation de santé.

## Vérifications après un redéploiement

```bash
sudo systemctl status racinepoir.service --no-pager
sudo systemctl status caddy --no-pager
curl --fail --silent http://127.0.0.1:8000/healthz
curl --fail --silent http://127.0.0.1/healthz
```

Effectuer ensuite la checklist fonctionnelle de `docs/SMOKE_TEST.md`.

## Suite

1. rétablir le flux TCP 5432 minimal de WEB01 vers SQL01 et obtenir un
   `/healthz` réussi;
2. vérifier si le premier administrateur production existe déjà, puis utiliser
   au besoin la commande interactive `flask create-admin` documentée dans
   `docs/PRODUCTION_DATABASE.md`, sans journaliser le mot de passe;
3. produire et vérifier une première sauvegarde PostgreSQL;
4. ajouter `ludotheque.home.arpa` au DNS local;
5. exécuter le smoke test fonctionnel complet;
6. préparer HTTPS, puis seulement alors activer
   `SESSION_COOKIE_SECURE=true`, `REMEMBER_COOKIE_SECURE=true` et
   `TRUST_PROXY_HEADERS=true`;
7. fusionner la branche de stabilisation vers `main` après validation.

Le service demeure en HTTP LAN. Il ne doit pas être présenté comme une
publication Internet ou un déploiement HTTPS.
