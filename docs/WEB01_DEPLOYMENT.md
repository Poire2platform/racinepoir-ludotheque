# Déploiement WEB01

Ce document décrit le premier déploiement LAN validé le 4 août 2026. Il ne
contient aucun secret et ne remplace pas les fichiers privés du serveur.

## État déployé

| Élément | Valeur |
|---|---|
| Serveur | `WEB01` / `poire1-ludoweb` |
| Adresse LAN | `192.168.18.38` |
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

## Vérifications après un redéploiement

```bash
sudo systemctl status racinepoir.service --no-pager
sudo systemctl status caddy --no-pager
curl --fail --silent http://127.0.0.1:8000/healthz
curl --fail --silent http://127.0.0.1/healthz
```

Effectuer ensuite la checklist fonctionnelle de `docs/SMOKE_TEST.md`.

## Suite

1. créer le premier administrateur avec une procédure qui ne journalise pas le
   mot de passe;
2. produire et vérifier une première sauvegarde PostgreSQL;
3. ajouter `ludotheque.home.arpa` au DNS local;
4. exécuter le smoke test fonctionnel complet;
5. préparer HTTPS, puis seulement alors activer
   `SESSION_COOKIE_SECURE=true`, `REMEMBER_COOKIE_SECURE=true` et
   `TRUST_PROXY_HEADERS=true`;
6. fusionner la branche de stabilisation vers `main` après validation.

Le service demeure en HTTP LAN. Il ne doit pas être présenté comme une
publication Internet ou un déploiement HTTPS.
