# Base PostgreSQL de production

## Décision

La production utilise une base séparée sur SQL01 :

```text
Serveur : SQL01 / 192.168.18.30
Base : racinepoir_ludotheque_prod
Rôle applicatif : racinepoir_prod
Client applicatif autorisé : WEB01 / 192.168.18.38
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

Dans le fichier retourné par `SHOW hba_file;`, ajouter une règle ciblée :

```text
hostssl  racinepoir_ludotheque_prod  racinepoir_prod  192.168.18.38/32  scram-sha-256
```

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

Le head attendu est `b7c3d4e5f6a7`. Il faudra ensuite créer le premier admin par
une procédure contrôlée et produire immédiatement un premier dump vérifié.
