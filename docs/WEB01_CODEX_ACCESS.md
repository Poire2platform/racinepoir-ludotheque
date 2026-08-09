# Accès de déploiement à WEB01

Ce document décrit l’accès SSH en écriture à WEB01 depuis `pmax-host`. Maxime a
installé puis autorisé cet accès le 9 août 2026. La révocation demeure une
opération d’infrastructure sous son contrôle.

## État vérifié le 9 août 2026

- l’alias SSH `web01-racinepoir` ouvre une session avec le compte dédié
  `deploy-racinepoir` vers `10.10.20.10`;
- `/opt/racinepoir` est monté en lecture-écriture par SSHFS dans
  `/home/pmax/web01-racinepoir` sur `pmax-host`;
- ce montage est ajouté comme deuxième dossier du workspace Codex;
- le checkout WEB01 est propre au commit `c3711c2` sur la branche
  `repair/manual-stabilization-2026-07-29`;
- `/opt/racinepoir` appartient à `pmax:racinepoir-deploy`, est en mode `3775`,
  et `.env` demeure protégé sous `pmax:pmax` en mode `600`;
- `/usr/local/sbin/racinepoir-ops` et sa règle `sudoers` limitée sont installés;
- `racinepoir-ops status` fonctionne et confirme que Gunicorn et Caddy sont
  actifs;
- la commande `racinepoir-ops health` n’a pas terminé dans le délai de contrôle.
  Les journaux montraient des redémarrages de workers Gunicorn après timeout.

L’accès en écriture est donc opérationnel, mais sa validation reste incomplète
tant que le test de santé et un essai contrôlé de révocation n’ont pas réussi.

## Portée retenue

Le compte dédié `deploy-racinepoir` peut :

- lire et modifier le checkout `/opt/racinepoir`, historique Git inclus;
- utiliser Git et transférer des fichiers par SSH ou SFTP;
- monter ce checkout sur `pmax-host` avec SSHFS en lecture-écriture;
- demander au programme contrôlé `racinepoir-ops` d’afficher l’état et les
  journaux, vérifier la santé, appliquer les migrations, créer le premier
  administrateur ou redémarrer le service.

Il ne peut pas :

- ouvrir `/opt/racinepoir/.env`;
- modifier directement `/opt/racinepoir/.venv`;
- utiliser `sudo` pour une autre commande;
- administrer Caddy, PostgreSQL, pfSense ou Proxmox;
- ouvrir un tunnel SSH ou transférer un agent SSH.

Cet accès est puissant : un changement écrit dans le checkout peut devenir le
code exécuté par le service après redémarrage. Toute modification doit donc
continuer à suivre le parcours dépôt local, tests, commit, push, déploiement
d’un commit précis, migration, redémarrage et test de santé.

## Fichiers préparés

| Fichier | Destination ou usage |
|---|---|
| `deploy/web01-access/install-web01-access` | Installation contrôlée sur WEB01 |
| `deploy/web01-access/racinepoir-ops` | `/usr/local/sbin/racinepoir-ops` sur WEB01 |
| `deploy/web01-access/racinepoir-ops.sudoers` | `/etc/sudoers.d/racinepoir-ops` sur WEB01 |
| `deploy/web01-access/ssh_config.example` | Modèle pour `~/.ssh/config` sur `pmax-host` |

Aucune clé privée ou publique réelle n’est versionnée.

## 1. Vérifications préalables et réutilisables

Sur WEB01, Maxime vérifie d’abord :

```bash
hostname
ip -brief address
git -C /opt/racinepoir status --short --branch
git -C /opt/racinepoir log -1 --oneline --decorate
stat -c '%U:%G %a %n' /opt/racinepoir /opt/racinepoir/.env
sudo systemctl status racinepoir.service --no-pager
```

Résultats attendus : WEB01 est `poire1-ludoweb` à `10.10.20.10`, le checkout
est propre, et `.env` appartient à `pmax`, en mode `600`. Arrêter si ces faits
ne correspondent pas à l’état réel.

## 2. Recréer la clé sur pmax-host au besoin

À exécuter par Maxime sur `pmax-host` :

```bash
ssh-keygen -t ed25519 \
  -f ~/.ssh/id_ed25519_web01_racinepoir \
  -C 'deploy-racinepoir@pmax-host'
```

La clé privée ne doit jamais être copiée dans Git, WEB01, une conversation ou
un journal. Seul le fichier terminé par `.pub` est transmis à WEB01.

## 3. Réinstaller l’accès sur WEB01 au besoin

Après avoir poussé puis placé sur WEB01 le commit contenant ces fichiers,
transférer seulement la clé publique dans un fichier temporaire. Depuis
`/opt/racinepoir`, Maxime exécute :

```bash
sudo deploy/web01-access/install-web01-access \
  /chemin/vers/id_ed25519_web01_racinepoir.pub
```

Le programme :

1. vérifie le checkout, `.env`, l’environnement Flask et la clé publique;
2. crée `deploy-racinepoir` et le groupe `racinepoir-deploy` si nécessaire;
3. limite la clé à la source `192.168.18.18` et désactive les redirections;
4. rend le checkout inscriptible par le groupe, sauf `.env` et `.venv`;
5. protège `.env` avec son propriétaire `pmax`, le mode `600` et le sticky bit
   sur la racine du checkout;
6. installe le programme d’exploitation et sa règle `sudoers` comme fichiers
   appartenant à `root`;
7. valide `sudoers` et la configuration SSH;
8. ne redémarre aucun service et n’applique aucune migration.

Garder la session administrative ouverte pendant le premier test. Ne supprimer
aucun accès existant avant que la nouvelle connexion soit validée.

## 4. Configurer le client SSH

Ajouter le contenu de `deploy/web01-access/ssh_config.example` dans
`~/.ssh/config`, puis protéger le fichier :

```bash
chmod 600 ~/.ssh/config
ssh web01-racinepoir 'id; git -C /opt/racinepoir status --short --branch'
ssh web01-racinepoir 'sudo /usr/local/sbin/racinepoir-ops status'
```

La première connexion doit présenter l’empreinte de WEB01. Maxime doit comparer
cette empreinte à celle affichée localement sur WEB01 avant de l’accepter.

## 5. Montage SSHFS facultatif

Le montage sert à parcourir simultanément le dépôt local et le checkout WEB01.
Il ne remplace pas Git ni les commandes d’exploitation contrôlées.

Sur `pmax-host` :

```bash
sudo apt install sshfs
mkdir -p /home/pmax/web01-racinepoir
sshfs web01-racinepoir:/opt/racinepoir \
  /home/pmax/web01-racinepoir \
  -o rw,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3
```

Ajouter ensuite `/home/pmax/web01-racinepoir` comme deuxième dossier du
workspace. Selon les permissions de la session Codex, un rechargement du
workspace peut être nécessaire avant que ce nouveau dossier soit visible.

Ne jamais monter WEB01 à l’intérieur de
`/home/pmax/racinepoir-ludotheque`. Pour démonter :

```bash
fusermount3 -u /home/pmax/web01-racinepoir
```

## 6. Commandes autorisées

Depuis `pmax-host` :

```bash
ssh -t web01-racinepoir 'sudo /usr/local/sbin/racinepoir-ops status'
ssh -t web01-racinepoir 'sudo /usr/local/sbin/racinepoir-ops logs 100'
ssh -t web01-racinepoir 'sudo /usr/local/sbin/racinepoir-ops health'
ssh -t web01-racinepoir 'sudo /usr/local/sbin/racinepoir-ops migrate'
ssh -t web01-racinepoir 'sudo /usr/local/sbin/racinepoir-ops create-admin'
ssh -t web01-racinepoir 'sudo /usr/local/sbin/racinepoir-ops restart'
```

`migrate`, `create-admin` et `restart` refusent de continuer si le checkout
contient un changement ou un fichier non suivi. Le mot de passe administrateur
est demandé deux fois par `create-admin`; il ne doit jamais être fourni dans la
commande ou dans `logthis`.

Le programme n’offre volontairement aucune commande générique, aucun shell
`root` et aucune commande de suppression.

## 7. Révocation

En cas de doute, Maxime retire d’abord la clé publique ou verrouille le compte :

```bash
sudo usermod --lock deploy-racinepoir
sudo mv /home/deploy-racinepoir/.ssh/authorized_keys \
  /home/deploy-racinepoir/.ssh/authorized_keys.disabled
```

Après vérification, retirer la règle privilégiée :

```bash
sudo rm /etc/sudoers.d/racinepoir-ops
sudo rm /usr/local/sbin/racinepoir-ops
sudo visudo --check
```

Le compte et le groupe ne doivent être supprimés qu’après avoir vérifié les
propriétaires et permissions du checkout. La révocation SSH ne modifie pas le
service en cours d’exécution.
