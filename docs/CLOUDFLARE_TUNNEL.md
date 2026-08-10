# Publication par Cloudflare Tunnel

## Décision et portée

La décision `D-02` est Cloudflare Tunnel. Le tunnel distant
`racinepoir-web01` publiera :

```text
https://ludotheque.filsdepoire.ca
  -> Cloudflare Tunnel
  -> cloudflared sur WEB01
  -> http://127.0.0.1:80
  -> Caddy -> Gunicorn -> Flask -> PostgreSQL sur SQL01
```

Cette architecture ne nécessite aucune redirection entrante 80/443 vers WEB01.
PostgreSQL 5432 et Gunicorn 8000 demeurent non publics. La création du tunnel,
les changements DNS et la gestion du token relèvent de Maxime.

Références officielles :

- <https://developers.cloudflare.com/tunnel/setup/>
- <https://developers.cloudflare.com/tunnel/advanced/tunnel-tokens/>
- <https://developers.cloudflare.com/tunnel/advanced/run-parameters/>
- <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-with-firewall/>
- <https://pkg.cloudflare.com/>

## État préalable vérifié le 10 août 2026

- Caddy sert l’origine locale sur `http://127.0.0.1:80`.
- Gunicorn et Caddy retournent `/healthz` avec `status: ok` et `database: ok`.
- `cloudflared` n’est pas installé.
- DNS résout `region1.v2.argotunnel.com`.
- TCP 7844 vers Cloudflare et TCP 443 vers `api.cloudflare.com` expirent; les
  règles de sortie DMZ doivent être ajoutées avant l’installation.

## 1. Autoriser uniquement les sorties nécessaires

Dans pfSense, autoriser depuis WEB01 `10.10.20.10/32` :

- TCP et UDP 7844 vers les destinations Cloudflare Tunnel officielles;
- TCP 443 pour le dépôt signé `pkg.cloudflare.com`, l’API et les mises à jour;
- DNS vers le résolveur déjà retenu par l’infrastructure.

Ne créer aucune règle WAN entrante pour le tunnel. Si pfSense utilise des alias
FQDN, employer `region1.v2.argotunnel.com` et `region2.v2.argotunnel.com`.
Sinon, reprendre toutes les adresses courantes de la documentation Cloudflare,
car une seule adresse DNS observée ne constitue pas une allowlist complète.

Après application, vérifier TCP 7844 et 443 depuis WEB01. `cloudflared` 2026.5.2
ou ultérieur exécute aussi des précontrôles DNS, QUIC, HTTP/2 et API à chaque
démarrage.

## 2. Installer le paquet signé

Sur WEB01, après validation des sorties :

```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \
  | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' \
  | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt-get update
sudo apt-get install cloudflared
cloudflared --version
```

Utiliser le dépôt stable, jamais le dépôt nightly.

## 3. Créer le tunnel dans le tableau de bord

Dans Cloudflare, ouvrir **Networking > Tunnels**, puis :

1. créer un tunnel distant nommé `racinepoir-web01`;
2. ajouter le hostname public `ludotheque.filsdepoire.ca`;
3. choisir le service HTTP `http://localhost:80`;
4. ne pas ajouter de route vers PostgreSQL, SSH ou Gunicorn;
5. copier uniquement la valeur du token dans un terminal privé sur WEB01.

Ne jamais coller le token dans Git, un document, une conversation, une capture,
`logthis` ou une commande conservée dans l’historique. Toute personne possédant
ce token peut exécuter le tunnel; le faire pivoter immédiatement s’il est exposé.

## 4. Installer le token sans l’afficher

```bash
sudo useradd --system --home-dir /var/lib/cloudflared \
  --create-home --shell /usr/sbin/nologin cloudflared
sudo install -d -o root -g cloudflared -m 0750 /etc/cloudflared
```

Saisir le token dans une invite masquée, sans l’inscrire dans l’historique ni
les arguments d’un processus :

```bash
read -rsp 'Token du tunnel : ' RACINEPOIR_TUNNEL_TOKEN; echo
printf '%s' "$RACINEPOIR_TUNNEL_TOKEN" \
  | sudo install -o root -g cloudflared -m 0640 /dev/stdin \
      /etc/cloudflared/tunnel-token
unset RACINEPOIR_TUNNEL_TOKEN
sudo stat -c '%U:%G %a %n' /etc/cloudflared/tunnel-token
```

Le résultat attendu est `root:cloudflared 640`. Ne jamais afficher le contenu.

## 5. Installer le service versionné

Comparer `deploy/cloudflared.service` à tout service existant. S’il n’existe
aucun service concurrent :

```bash
sudo install -o root -g root -m 0644 \
  deploy/cloudflared.service /etc/systemd/system/cloudflared.service
sudo systemctl daemon-reload
sudo systemctl enable --now cloudflared.service
sudo systemctl status cloudflared.service --no-pager
```

Le service lit le token avec `--token-file`; il ne doit pas contenir le token
dans `ExecStart` ni l’exposer dans la liste des processus.

## 6. Ordre de validation publique

1. Confirmer le statut **Healthy** du tunnel dans Cloudflare.
2. Vérifier `https://ludotheque.filsdepoire.ca/healthz` hors Wi-Fi.
3. Vérifier le certificat HTTPS et la redirection vers la connexion.
4. Configurer `APP_BASE_URL=https://ludotheque.filsdepoire.ca` et les cookies
   sécurisés documentés dans le README.
5. Redémarrer l’application avec la procédure contrôlée.
6. Refaire `/healthz`, login, permissions, scan direct et QR.
7. Confirmer qu’aucun port 5432 ou 8000 n’est public.
8. Faire pivoter le token si une exposition est suspectée.

Ne pas imprimer les QR définitifs avant que le hostname public, HTTPS et
`APP_BASE_URL` soient stables.
