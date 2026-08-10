# RacinePoir Ludothèque — infrastructure

Ce document est la source de vérité courte pour l’infrastructure. Il décrit
l’état vérifié le 9 août 2026 et distingue cet état de la segmentation cible.

## Clarification importante

`pmax-host` n’est pas le serveur de production.

- `pmax-host` est la machine Ubuntu Desktop de développement et l’hôte
  QEMU/KVM + libvirt.
- `Poire1_PROX` est la VM imbriquée qui héberge Proxmox.
- `WEB01` est le nom Proxmox de la VM applicative dédiée; son hostname invité
  est `poire1-ludoweb`. Elle a été déplacée dans la DMZ le 9 août 2026.
- `SQL01` est la VM PostgreSQL séparée (VMID `101`).

Le code est développé et testé sur `pmax-host`. L’administration de Proxmox,
pfSense, WEB01, SQL01, du DNS et du pare-feu demeure une opération distincte,
effectuée par Maxime.

## Architecture actuelle

| Élément | Identité | Adresse actuelle | État |
|---|---|---:|---|
| Hôte physique | `pmax-host` | `192.168.18.18` | Développement; QEMU/KVM + libvirt |
| Hyperviseur imbriqué | `Poire1_PROX` / Poire1-Proxmox | `192.168.18.100` | Fonctionnel |
| Pare-feu | VM `100`, pfSense CE 2.8.1 | WAN par DHCP; MGMT `10.10.10.1` | Fonctionnel |
| PostgreSQL | VM `101`, `SQL01` | `192.168.18.30` | Fonctionnel; pas encore déplacé |
| DNS local | VM `102`, `poire1-dns` | `192.168.18.34` | Fonctionnel |
| Portail | VM `103`, `poire1-portal` | `192.168.18.35` | Fonctionnel |
| Application | VMID `104`, VM `WEB01`, hostname `poire1-ludoweb` | `10.10.20.10` | Caddy, Gunicorn et accès DB fonctionnels; `/healthz` validé |

La zone DNS locale est `home.arpa`. Un nom local possible pour l’application
est `ludotheque.home.arpa`.

## Réseaux pfSense

| Zone | Interface | Bridge Proxmox | Réseau / adresse pfSense |
|---|---|---|---|
| WAN | `vtnet0` | `vmbr0` | DHCP sur `192.168.18.0/24` |
| MGMT | `vtnet1` | `vmbr1` | `10.10.10.1/24` |
| DMZ | `vtnet2` | `vmbr2` | `10.10.20.1/24` |
| APP | `vtnet3` | `vmbr3` | `10.10.30.1/24` |
| DB | `vtnet4` | `vmbr4` | `10.10.40.1/24` |

- DHCP MGMT : `10.10.10.100` à `10.10.10.199`.
- NAT sortant : automatique.
- DNS pfSense : `192.168.18.34` et `1.1.1.1`.
- Internet, NAT et résolution DNS : validés.
- MGMT conserve temporairement les règles LAN par défaut.
- DMZ possède uniquement la règle ciblée WEB01 vers SQL01:5432; APP et DB n’ont
  encore aucune règle d’autorisation et leur blocage implicite demeure actif.

Important : WEB01 est maintenant dans la DMZ. Son ancienne adresse
`192.168.18.38` n’est plus configurée. Le 9 août, une règle pfSense limitée à
WEB01 `10.10.20.10` vers SQL01 `192.168.18.30:5432` a rétabli le transport.
Le NAT sortant présente temporairement la source `192.168.18.41` à PostgreSQL;
la règle HBA `/32` correspondante est active et `/healthz` réussit par Gunicorn
et Caddy. Les autres règles interzones et la publication Internet ne sont pas
encore validées.

## Administration pfSense

Depuis Windows, ouvrir un tunnel SSH vers l’hyperviseur :

```bash
ssh -L 8443:10.10.10.1:443 root@192.168.18.100
```

Puis ouvrir le WebGUI à l’adresse `https://localhost:8443`.

Le bootstrap a été appliqué depuis `/tmp/racinepoir-bootstrap.php`. Il configure
notamment le nom prévu `poire1-pfsense.home.arpa`, le fuseau
`America/Toronto`, ainsi que les aliases réseau et ports.

Sauvegarde créée avant le bootstrap :
`/root/config-before-racinepoir-20260804-121236.xml`.

## Snapshot pfSense

La VM `100` possède le snapshot `pfsense-bootstrap-stable`. Il correspond à
l’état fonctionnel après installation, bootstrap et validation du WAN, du NAT
et du DNS.

## Snapshot WEB01

La VM `WEB01` (104) possède le snapshot `web01-post-deploy-20260810`, créé sans
état RAM après le déploiement du commit `4329325`, la validation Alembic, la
création de l’administrateur production et le premier dump vérifié. La santé de
l’application et de la base a été confirmée après le snapshot.

Proxmox a averti que la somme des tailles virtuelles des volumes thin
surprovisionnés dépasse la capacité physique du thin-pool et du volume group.
Le snapshot a réussi, mais la consommation réelle de `local-lvm` doit demeurer
surveillée et aucun nouveau surprovisionnement ne doit être banalisé.

## Stockage Poire1-Proxmox

- Le disque virtuel de `Poire1_PROX` est passé de 80 Gio à 200 Gio.
- `local-lvm` / `pve-data` : 129,93 Gio, utilisé à 40,73 % après les snapshots
  du 10 août 2026; environ 76,96 Gio demeurent disponibles.
- Métadonnées du thin-pool : 3,50 %.
- Espace libre restant dans le volume group `pve` : environ 29,88 Gio.
- Le thin-pool est surveillé par `lvm2-monitor`.
- Autoextension : `thin_pool_autoextend_threshold = 80` et
  `thin_pool_autoextend_percent = 10`.
- Sauvegarde de l’ancienne configuration :
  `/etc/lvm/lvm.conf.before-thin-autoextend`.

L’adresse `10.10.10.2/24` de `vmbr1` sur Poire1-Proxmox a été ajoutée
temporairement avec `ip`. Elle n’est pas persistante dans
`/etc/network/interfaces`.

## Cible applicative

Le flux public retenu après configuration des règles est :

```text
Internet
  -> Cloudflare HTTPS
  -> tunnel sortant cloudflared sur WEB01
  -> Caddy dans DMZ
  -> application Flask / Gunicorn dans APP
  -> PostgreSQL dans DB sur TCP 5432
```

Caddy est installé sur WEB01 et écoute actuellement sur toutes ses interfaces
au port 80. Gunicorn écoute seulement sur `127.0.0.1:8000`; ce couple convient
à l’état transitoire où proxy et application partagent WEB01 dans la DMZ. Le
domaine public retenu est `ludotheque.filsdepoire.ca`, avec DNS public et tunnel
gérés dans Cloudflare. La procédure est versionnée dans
`docs/CLOUDFLARE_TUNNEL.md`.

Dans la cible segmentée, le reverse proxy demeure dans la DMZ et l’application
est déplacée dans APP. À ce moment seulement, Gunicorn devra écouter l’adresse
APP de la machine applicative plutôt que `127.0.0.1`, Caddy devra joindre cette
adresse sur TCP 8000, et pfSense devra limiter ce flux à la seule source du
proxy. Le port 8000 ne doit jamais être exposé au WAN.

Le déploiement LAN validé est détaillé dans `docs/WEB01_DEPLOYMENT.md`.

## Prochaine phase

Le chemin contrôlé transitoire entre WEB01 et SQL01 est rétabli. Préparer et
valider ensuite les autres règles minimales :

1. MGMT vers les interfaces d’administration nécessaires;
2. sorties WEB01 TCP/UDP 7844 vers Cloudflare Tunnel et TCP 443 pour le dépôt et
   l’API Cloudflare; aucune redirection WAN entrante 80/443;
3. reverse proxy DMZ vers l’application dans APP;
4. état transitoire validé : WEB01 `10.10.20.10` vers SQL01 `192.168.18.30` sur
   TCP 5432, avec `pg_hba.conf` limité à la source NAT observée
   `192.168.18.41/32`;
5. cible : application APP vers PostgreSQL dans DB sur TCP 5432;
6. refus de toute autre communication interzone;
7. décision ultérieure : conserver temporairement SQL01 sur `192.168.18.30`
   ou le migrer dans DB.

Ces opérations d’infrastructure précèdent le passage à l’architecture segmentée
et la publication Internet; elles ne remettent pas en cause le déploiement LAN
déjà fonctionnel. Elles ne nécessitent aucun changement au code Flask, aux
migrations ni au schéma PostgreSQL.
