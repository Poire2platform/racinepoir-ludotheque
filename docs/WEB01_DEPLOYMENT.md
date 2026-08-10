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

Le checkout WEB01 est propre au commit `4329325`, déployé le 9 août 2026. Le
déploiement a été effectué par fast-forward depuis `c3711c2`, suivi de la
vérification Alembic au head `b7c3d4e5f6a7`, d’un redémarrage contrôlé et de
contrôles `/healthz` réussis par Gunicorn et Caddy.

Le compte dédié ne pouvait pas terminer un `git fetch` HTTPS non interactif.
Les objets du commit exact ont donc été transférés dans un bundle Git vérifié
par SSH, puis le fast-forward a été exécuté par `pmax`, propriétaire des fichiers
du checkout. Toujours comparer les SHA et exiger un fast-forward avant un futur
déploiement; ne pas contourner le sticky bit ou exposer des identifiants GitHub.

## Effet de la segmentation sur Caddy et Gunicorn

La configuration active reste correcte pour l’état transitoire : Caddy écoute
sur le port 80 de WEB01 et transmet à Gunicorn sur `127.0.0.1:8000`. Le contrôle
du 9 août a obtenu HTTP 302 directement auprès des deux services. Leur liaison
locale n’expliquait donc pas la panne initiale de `/healthz`.

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
montraient des workers arrêtés puis relancés après timeout.

Plus tard le 9 août, une règle pfSense limitée de WEB01 `10.10.20.10` vers
SQL01 `192.168.18.30:5432` a rétabli le transport. PostgreSQL observait la source
NAT `192.168.18.41`; après mise à jour et rechargement de la règle HBA `/32`, les
contrôles TCP 5432, Gunicorn `/healthz` et Caddy `/healthz` ont tous réussi. Les
deux réponses de santé rapportaient `status: ok` et `database: ok`.

## Vérifications après un redéploiement

```bash
sudo systemctl status racinepoir.service --no-pager
sudo systemctl status caddy --no-pager
curl --fail --silent http://127.0.0.1:8000/healthz
curl --fail --silent http://127.0.0.1/healthz
```

Effectuer ensuite la checklist fonctionnelle de `docs/SMOKE_TEST.md`. Pour une
exécution déléguée sans accès serveur, utiliser le guide autonome
`docs/INTERN_PRODUCTION_SMOKE_TEST.md`.

## Suite

1. ajouter `ludotheque.home.arpa` au DNS local;
2. exécuter le smoke test fonctionnel complet;
3. préparer HTTPS, puis seulement alors activer
   `SESSION_COOKIE_SECURE=true`, `REMEMBER_COOKIE_SECURE=true` et
   `TRUST_PROXY_HEADERS=true`;
4. fusionner la branche de stabilisation vers `main` après validation.

Le service demeure en HTTP LAN. Il ne doit pas être présenté comme une
publication Internet ou un déploiement HTTPS.
