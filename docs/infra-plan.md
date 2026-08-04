# RacinePoir Ludothèque — infrastructure

Ce document est la source de vérité courte pour l’infrastructure. Il décrit
l’état validé le 5 août 2026 et distingue cet état de la segmentation cible.

## Clarification importante

`pmax-host` n’est pas le serveur de production.

- `pmax-host` est la machine Ubuntu Desktop de développement et l’hôte
  QEMU/KVM + libvirt.
- `Poire1_PROX` est la VM imbriquée qui héberge Proxmox.
- `WEB01` est la VM applicative dédiée actuellement fonctionnelle sur le LAN
  historique.
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
| Application | VM `104`, `WEB01` | `192.168.18.38` | Déploiement LAN fonctionnel |

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
- DMZ, APP et DB n’ont encore aucune règle d’autorisation; leur blocage
  implicite est donc actif.

Important : WEB01 fonctionne actuellement sur le LAN historique. Les règles
applicatives interzones et la publication Internet ne sont pas encore déployées.

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

## Stockage Poire1-Proxmox

- Le disque virtuel de `Poire1_PROX` est passé de 80 Gio à 200 Gio.
- `local-lvm` / `pve-data` : 129,93 Gio, utilisé à 24,56 %.
- Métadonnées du thin-pool : 2,74 %.
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

Le flux prévu après configuration des règles est :

```text
Internet
  -> WAN TCP 443
  -> reverse proxy dans DMZ
  -> application Flask / Gunicorn dans APP
  -> PostgreSQL dans DB sur TCP 5432
```

Caddy est installé sur WEB01 en HTTP LAN. Le domaine public envisagé est
`ludotheque.filsdepoire.ca`, avec DNS public probablement géré par Cloudflare.

Le déploiement LAN validé est détaillé dans `docs/WEB01_DEPLOYMENT.md`.

## Prochaine phase

Ne pas déplacer SQL01 immédiatement. Préparer et valider les règles minimales :

1. MGMT vers les interfaces d’administration nécessaires;
2. WAN TCP 443 vers le futur reverse proxy en DMZ;
3. reverse proxy DMZ vers l’application dans APP;
4. application APP vers PostgreSQL sur TCP 5432;
5. refus de toute autre communication interzone;
6. décision ultérieure : conserver temporairement SQL01 sur `192.168.18.30`
   ou le migrer dans DB.

Ces opérations d’infrastructure précèdent le passage à l’architecture segmentée
et la publication Internet; elles ne remettent pas en cause le déploiement LAN
déjà fonctionnel. Elles ne nécessitent aucun changement au code Flask, aux
migrations ni au schéma PostgreSQL.
