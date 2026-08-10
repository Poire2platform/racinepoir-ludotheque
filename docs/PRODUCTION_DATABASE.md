# Base PostgreSQL de production

## Décision

La production utilise une base séparée sur SQL01 :

```text
Serveur : SQL01 / 192.168.18.30
Base : racinepoir_ludotheque_prod
Rôle applicatif : racinepoir_prod
Client applicatif actuel : WEB01 / 10.10.20.10
```

La base de développement `racinepoir_ludotheque` et son rôle ne sont pas
réutilisés par WEB01. Aucun seed de développement ne doit être exécuté sur la
base de production.

## 1. Vérifications en lecture seule sur SQL01

À exécuter par Maxime sur SQL01 :

```bash
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -c "SELECT datname FROM pg_database WHERE datname = 'racinepoir_ludotheque_prod';"
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -c "SELECT rolname, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = 'racinepoir_prod';"
sudo -u postgres psql -X -At -c "SHOW hba_file;"
```

Si le rôle ou la base existe déjà, arrêter avant les commandes de création et
vérifier leur propriétaire et leur usage.

## 2. Créer le rôle et la base

`--pwprompt` demande le secret sans l’inscrire dans la commande :

```bash
sudo -u postgres createuser --no-superuser --no-createdb --no-createrole --pwprompt racinepoir_prod
sudo -u postgres createdb --owner=racinepoir_prod --encoding=UTF8 racinepoir_ludotheque_prod
```

Vérifier le résultat :

```bash
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -c "SELECT datname, pg_catalog.pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datname = 'racinepoir_ludotheque_prod';"
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -c "SELECT rolname, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = 'racinepoir_prod';"
```

Le rôle doit avoir `false` pour superuser, création de base et création de rôle.

## 3. Restreindre l’accès réseau

Depuis le déplacement de WEB01 dans la DMZ, les journaux PostgreSQL ont confirmé
que le NAT sortant pfSense présente temporairement la source `192.168.18.41`, et
non l’adresse propre de WEB01 `10.10.20.10`. L’ancienne autorisation
`192.168.18.38/32` a donc été remplacée par la règle ciblée suivante :

```text
hostssl  racinepoir_ludotheque_prod  racinepoir_prod  192.168.18.41/32  scram-sha-256
```

Cette source NAT demeure acceptable pour l’état transitoire seulement parce que
la règle pfSense limite TCP 5432 à WEB01 `10.10.20.10` vers SQL01
`192.168.18.30`. Si le NAT est retiré, remettre simultanément la règle HBA à
`10.10.20.10/32` après confirmation dans les journaux PostgreSQL.

Ne pas ajouter de règle publique ou de sous-réseau plus large. Valider puis
recharger la configuration :

```bash
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -c "SELECT pg_reload_conf();"
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -c "SELECT type, database, user_name, address, auth_method, error FROM pg_hba_file_rules WHERE database @> ARRAY['racinepoir_ludotheque_prod'];"
```

## 4. Tester depuis WEB01

Installer le client PostgreSQL sur WEB01, puis utiliser une invite de mot de
passe plutôt qu’une URL contenant le secret :

```bash
PGSSLMODE=require psql --host=192.168.18.30 --username=racinepoir_prod --dbname=racinepoir_ludotheque_prod --command='\conninfo'
```

La connexion doit annoncer SSL. Une connexion depuis une autre machine ne doit
pas être autorisée par une règle plus large.

Au premier contrôle du 9 août, TCP 5432 expirait avant d’atteindre PostgreSQL.
Une règle pfSense limitée à WEB01 vers SQL01:5432 a ensuite rétabli le transport;
les journaux PostgreSQL ont révélé la source NAT `192.168.18.41`, puis la règle
HBA corrigée et rechargée a permis à `/healthz` de retourner `database: ok`. Si
SQL01 est ensuite déplacé dans le réseau DB,
mettre simultanément à jour son adresse, la règle pfSense, `pg_hba.conf` et
`DATABASE_URL`, puis refaire ce test.

## 5. Configuration privée de WEB01

Le fichier déployé `/opt/racinepoir/.env`, non versionné, contient notamment :

```env
DATABASE_URL=postgresql://racinepoir_prod:MOT_DE_PASSE_ENCODE@192.168.18.30:5432/racinepoir_ludotheque_prod
```

Les caractères spéciaux du mot de passe doivent être encodés pour une URL. Le
secret réel ne doit apparaître ni dans Git, ni dans ce document, ni dans les
logs de déploiement.

## 6. Étapes ultérieures

Après préparation de WEB01 et de son environnement privé :

```bash
.venv/bin/flask db upgrade
.venv/bin/flask db current
```

Le head attendu est `b7c3d4e5f6a7`.

## 7. Premier administrateur vérifié

Le 10 août 2026, une lecture SQL a d’abord confirmé l’absence d’administrateur
dans `racinepoir_ludotheque_prod`. Le compte production `admin`, affiché comme
`Maxime`, a ensuite été créé avec la commande interactive contrôlée. Une seconde
lecture SQL a confirmé son rôle administrateur et son état actif, puis une
connexion réelle a réussi. Le mot de passe n’a été ni journalisé ni documenté.

Pour une future installation où l’administrateur est absent, exécuter ceci sur
WEB01 depuis `/opt/racinepoir`, après avoir confirmé que l’environnement privé
vise bien `racinepoir_ludotheque_prod` :

```bash
.venv/bin/flask create-admin \
  --username NOM_DE_CONNEXION \
  --email ADRESSE_COURRIEL \
  --display-name NOM_AFFICHE
```

La commande demande le mot de passe deux fois dans une invite masquée. Ne pas
mettre le mot de passe dans la commande, le terminal, `logthis` ou un document.
Elle refuse un nom d’utilisateur ou une adresse courriel déjà présents et ne
modifie aucun compte existant.

## 8. Premier dump vérifié

Le 10 août 2026, le premier dump de `racinepoir_ludotheque_prod` a été créé sur
SQL01 au format custom de PostgreSQL. L’archive est non vide, appartient à
`postgres:postgres`, est protégée en mode `600` et sa table des matières est
lisible par `pg_restore --list`.

Preuve enregistrée :

```text
Fichier : racinepoir_ludotheque_prod-20260810T165707Z.dump
Taille : 38232 octets
SHA-256 : 44f77b63bcbd4f181a4a8ba2334341da17f29aa0c9d98c41707f28339085af38
```

Ce dump local constitue le checkpoint `DB-08`; il ne remplace pas encore la
sauvegarde automatisée, la copie hors SQL01 ni le test de restauration prévus
par `OPS-01` à `OPS-04`.
