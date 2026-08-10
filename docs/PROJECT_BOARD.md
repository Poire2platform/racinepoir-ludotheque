# PROJECT_BOARD.md
## RacinePoir — Ludothèque distribuée

**Rôle du document :** tableau de suivi opérationnel du projet.  
**Dernière mise à jour :** 9 août 2026
**Sources complémentaires :**
- `docs/infra-plan.md`
- `docs/PRODUCTION_DATABASE.md`
- code et migrations de la branche active

---

# 1. Règles d’utilisation

| Statut | Signification |
|---|---|
| `DONE` | Terminé et vérifié |
| `VERIFY` | Présent ou probable, mais doit être testé |
| `NEXT` | Prochaine tâche à faire |
| `BLOCKED` | Bloqué par une décision ou un prérequis |
| `LATER` | Non requis pour la première mise en ligne |
| `CANCELLED` | Abandonné volontairement |

Règles :

1. Ne travailler que sur une carte `NEXT` à la fois.
2. Après chaque carte : tester, noter le résultat, committer et ajouter une entrée `logthis`.
3. Ne jamais déployer un changement non testé sur `pmax-host`.
4. Ne jamais utiliser `rescue/unstable-2026-07-22` comme branche de production.
5. Ne jamais exécuter un seed destructif sur une base contenant des données utiles.
6. Ne pas modifier l’infrastructure et le code dans la même étape sans checkpoint.

---

# 2. Situation actuelle

## Infrastructure

| Élément | État |
|---|---|
| Proxmox `Poire1` — `192.168.18.100` | Fonctionnel |
| Développement `pmax-host` — `192.168.18.18` | Fonctionnel |
| pfSense CE 2.8.1 — VM `100` | WAN, NAT, DNS et réseaux MGMT/DMZ/APP/DB validés; règles applicatives à faire |
| PostgreSQL `SQL01` — VM `101` — `192.168.18.30` | Base prod séparée fonctionnelle; migrations appliquées |
| DNS `poire1-dns` — `192.168.18.34` | Fonctionnel |
| Portal — `http://poire1-portal.home.arpa/` | Fonctionnel |
| WEB01 `poire1-ludoweb` — VM `104` — `10.10.20.10` | DMZ; Caddy, Gunicorn et accès PostgreSQL fonctionnels; `/healthz` validé |
| Domaine public prévu | `ludotheque.filsdepoire.ca` |
| Publication Internet | Non configurée |

## Récupération

| Élément | État |
|---|---|
| Branche de sauvegarde Codex | `rescue/unstable-2026-07-22` |
| Branche de réparation | `repair/manual-stabilization-2026-07-29` |
| Schéma PostgreSQL | Reconstruit |
| Migration courante | `b7c3d4e5f6a7` |
| Compte `admin` de développement (`Maxime`) | Présent, admin actif; compte production à vérifier/créer séparément |
| Token BGG | Configuré hors dépôt |
| Anciennes données | Non récupérées |
| Données de démonstration | Seed non destructif exécuté deux fois et vérifié |
| Tests automatisés actifs | 96 tests `pytest` réussis sur SQLite isolée |

---

# 3. Board principal

## PHASE -1 — Hygiène du dépôt

| ID | Statut | Tâche | Critère d’acceptation |
|---|---|---|---|
| REPO-01 | `DONE` | Inventorier la branche et les changements locaux | Branche et provenance des fichiers documentées |
| REPO-02 | `DONE` | Résoudre les marqueurs de conflit du README | Aucun marqueur de conflit restant |
| REPO-03 | `DONE` | Vérifier la branche de réparation | Branche `repair/manual-stabilization-2026-07-29` confirmée |
| REPO-04 | `DONE` | Configurer les dépendances de test | `pytest` installé via `requirements-dev.txt` |
| REPO-05 | `DONE` | Récupérer ou recréer les premiers tests critiques | 50 tests relus, adaptés et réussis |
| REPO-06 | `DONE` | Créer un checkpoint d’hygiène ciblé | Diff vérifié et commit sans `git add -A` aveugle |

Checkpoint historique du 29 juillet 2026 :

- les changements locaux concernaient le token BGG et le seed non destructif;
- le seed était alors inspecté statiquement; il a depuis été exécuté deux fois et
  vérifié par `STAB-08`;
- `tests/test_public_signup.py` existe dans `rescue/unstable-2026-07-22` et doit être
  relu avant toute récupération sélective; ses scénarios utiles ont été recréés
  proprement plutôt que de restaurer le fichier tel quel;
- la branche de sauvetage complète ne doit pas être fusionnée;
- les tests utilisent SQLite en mémoire et ne touchent pas SQL01;
- les avertissements Flask-Login et SQLAlchemy sur des API dépréciées sont une
  dette technique non bloquante;
- le déploiement était alors en pause jusqu’au checkpoint stable, maintenant
  terminé.

---

## PHASE 0 — Stabilisation immédiate

| ID | Statut | Tâche | Critère d’acceptation |
|---|---|---|---|
| STAB-01 | `DONE` | Isoler les changements instables dans une branche de sauvetage | Branche de sauvetage présente |
| STAB-02 | `DONE` | Créer une branche de réparation manuelle | Branche de réparation présente |
| STAB-03 | `DONE` | Vérifier la compilation Python | `compileall` retourne `0` |
| STAB-04 | `DONE` | Reconstruire les tables PostgreSQL | 8 tables applicatives + Alembic |
| STAB-05 | `DONE` | Vérifier Alembic | `9a1f4e5d8c20 (head)` |
| STAB-06 | `DONE` | Recréer le compte `admin` de Maxime | Compte actif et connexion validée |
| STAB-07 | `DONE` | Configurer le token BGG hors dépôt | Recherche BGG ne réclame plus le token |
| STAB-08 | `DONE` | Exécuter et vérifier le seed non destructif | Deux exécutions stables; compte `admin` inchangé |
| STAB-09 | `DONE` | Effectuer un test de fumée complet | Login, fiches et navigation validés sans traceback |
| STAB-10 | `DONE` | Vérifier l’ajout manuel d’une boîte sans dépendre de BGG | Test automatisé réussi sans appel BGG |
| STAB-11 | `DONE` | Vérifier les routes POST sensibles | Audit et 31 tests dédiés réussis; aucun GET mutateur |
| STAB-12 | `DONE` | Committer le checkpoint stable | Branche propre, commit nommé et `logthis` |
| STAB-13 | `LATER` | Examiner la branche de sauvetage | Récupérer seulement les changements utiles |

La phase de stabilisation est terminée. `STAB-13` demeure volontairement reportée.

---

## PHASE 1 — MVP fonctionnel

| ID | Statut | Tâche | Critère d’acceptation |
|---|---|---|---|
| MVP-01 | `DONE` | Login/logout | Login valide/invalide, compte désactivé, session et logout testés |
| MVP-02 | `DONE` | Catalogue des jeux | Liste, fiche, données de référence, boîtes liées et absence testées |
| MVP-03 | `DONE` | Ajouter un jeu manuellement | Création sans BGG, propriétaire et historique testés |
| MVP-04 | `DONE` | Enrichissement BGG | Recherche sans mutation et import choisi testés |
| MVP-05 | `DONE` | Liste des boîtes | Boîtes cataloguées/non cataloguées, détenteurs et statuts testés |
| MVP-06 | `DONE` | Ajouter une boîte | Jeu existant, nouveau ou absent (`game_id = NULL`); propriétaire et détenteur valides |
| MVP-07 | `DONE` | Modifier une boîte | Propriétaire/admin contrôlés; champs, validation et historique testés |
| MVP-08 | `DONE` | Détail d’une boîte | Propriétaire, détenteur, statut, historique et absence testés |
| MVP-09 | `DONE` | Génération et affichage du QR | Token stable, URL publique et image PNG testés |
| MVP-10 | `DONE` | Scan direct | Transfert automatique après login, changement de détenteur et événement testés |
| MVP-11 | `DONE` | Retour au scan après login | Retour local au scan et rejet des redirections externes testés |
| MVP-12 | `DONE` | Indicateur “I would like” | Note sans priorité, doublon ni impact sur le scan |
| MVP-13 | `CANCELLED` | Annulation d’une demande | Sans objet : l’indicateur n’est pas une réservation |
| MVP-14 | `DONE` | Clôture du flag au scan | Seul le flag du scanneur est complété; autres intérêts conservés |
| MVP-15 | `DONE` | Vue “Chez moi” | Détention courante distincte de la propriété testée |
| MVP-16 | `DONE` | Vue “Mes boîtes” | Propriété, détenteur réel et intérêts testés |
| MVP-17 | `DONE` | Recherche et filtres | Titre, propriétaire, détenteur et statut combinables |
| MVP-18 | `DONE` | Permissions applicatives | Admin, membre, propriétaire et non-propriétaire testés |
| MVP-19 | `DONE` | Gestion des utilisateurs | Création, activation, rôle, mot de passe et permissions testés |
| MVP-20 | `DONE` | `/healthz` | Disponibilité DB, panne 503 et journalisation testées |
| MVP-21 | `DONE` | Rate limiting | Login et scan bloqués en 429 sans mutation supplémentaire |
| MVP-22 | `LATER` | Statistiques de parties | Non bloquant |
| MVP-23 | `DONE` | Notes des jeux | Une note de 0 à 100 par joueur; médiane affichée au catalogue et sur la fiche |

---

## PHASE 2 — Qualité avant déploiement

| ID | Statut | Tâche | Critère d’acceptation |
|---|---|---|---|
| QA-01 | `DONE` | Créer une checklist de test manuel | `docs/SMOKE_TEST.md` |
| QA-02 | `DONE` | Ajouter des tests automatisés critiques | 96 tests couvrent login, utilisateurs, création d’admin, jeux, notes, boîtes, filtres, scan, demandes, CSRF, permissions, accessibilité et artefacts d’accès WEB01 |
| QA-03 | `DONE` | Vérifier les migrations sur une DB vide | SQLite vide migrée jusqu’à `b7c3d4e5f6a7` |
| QA-04 | `DONE` | Tester un redémarrage de l’application | Données, login, catalogue, boîtes et santé vérifiés après recréation |
| QA-05 | `DONE` | Vérifier les erreurs utilisateur | Réponses 404/500 sans traceback ni détail interne |
| QA-06 | `DONE` | Vérifier les secrets Git | Fichiers suivis et historique contrôlés sans secret détecté |
| QA-07 | `DONE` | Vérifier `requirements.txt` | Venv neuf et imports vérifiés; suite courante de 96 tests réussie |
| QA-08 | `DONE` | Préparer un tag de déploiement | Checkpoint QA identifié par `mvp-2026-08-03` |
| QA-09 | `DONE` | Revalider après la passe UX | 89 tests, head Alembic et tag `mvp-2026-08-03-ux` vérifiés |

---

## PHASE 3 — Préparer WEB01

Cette phase commence seulement après `DB-01` à `DB-05`. Le code et les fichiers de
configuration sont préparés côté développement; leur installation sur WEB01 relève
de l’administration système.

| ID | Statut | Tâche | Critère d’acceptation |
|---|---|---|---|
| WEB-01 | `DONE` | Confirmer le VMID de WEB01 | VM `104` |
| WEB-02 | `NEXT` | Activer le démarrage automatique de la VM | `onboot: 1` dans Proxmox |
| WEB-03 | `NEXT` | Prendre un snapshot propre | Snapshot visible |
| WEB-04 | `DONE` | Installer les paquets système | Déploiement opérationnel |
| WEB-05 | `DONE` | Rétablir et tester WEB01 → SQL01 après segmentation | TCP 5432, Gunicorn `/healthz` et Caddy `/healthz` réussis depuis WEB01 |
| WEB-06 | `DONE` | Choisir l’utilisateur système | Service sous `pmax`, sans root |
| WEB-07 | `DONE` | Créer le répertoire applicatif | `/opt/racinepoir` |
| WEB-08 | `DONE` | Créer l’environnement privé | `/opt/racinepoir/.env`, mode `600` |
| WEB-09 | `DONE` | Déployer le code | Commit `4329325` déployé; checkout propre, migration et redémarrage validés |
| WEB-10 | `DONE` | Créer le venv de production | `/opt/racinepoir/.venv` fonctionnel |
| WEB-11 | `DONE` | Appliquer les migrations | Head `b7c3d4e5f6a7` appliqué |
| WEB-12 | `DONE` | Tester Gunicorn | Répond sur `127.0.0.1:8000` |
| WEB-13 | `DONE` | Créer le service systemd | Activé et actif |
| WEB-14 | `DONE` | Installer et configurer Caddy | Reverse proxy HTTP validé |
| WEB-15 | `DONE` | Tester depuis le LAN | `/` et `/healthz` accessibles depuis Windows |
| WEB-16 | `VERIFY` | Valider l’accès SSH de déploiement dédié | SSHFS en écriture et secrets protégés vérifiés; santé et révocation à tester |

---

## PHASE 4 — Base de production

Malgré sa numérotation, la préparation `DB-01` à `DB-05` précède le déploiement
applicatif `WEB-08` à `WEB-11`.

| ID | Statut | Tâche | Critère d’acceptation |
|---|---|---|---|
| DB-01 | `DONE` | Choisir DB actuelle ou DB prod séparée | Base séparée `racinepoir_ludotheque_prod` sur SQL01 |
| DB-02 | `DONE` | Créer le rôle production | Rôle `racinepoir_prod` opérationnel |
| DB-03 | `DONE` | Créer la base production | `racinepoir_ludotheque_prod` opérationnelle |
| DB-04 | `DONE` | Adapter `pg_hba.conf` à la nouvelle source WEB01 | Source NAT observée `192.168.18.41/32`; règle HBA ciblée et rechargée |
| DB-05 | `DONE` | Revalider TLS PostgreSQL après segmentation | Connexion SSL et `/healthz` avec `database: ok` depuis WEB01 |
| DB-06 | `DONE` | Appliquer les migrations | Head `b7c3d4e5f6a7` appliqué |
| DB-07 | `NEXT` | Créer le premier admin prod | Mot de passe non journalisé |
| DB-08 | `NEXT` | Créer le premier dump prod | Fichier vérifié |

Recommandation :

```text
DB : racinepoir_ludotheque_prod
Rôle : racinepoir_prod
Source transitoire observée après NAT pfSense : 192.168.18.41/32
```

Ordre de passage vers WEB01 :

```text
DB-01 → DB-05
→ WEB-08 → WEB-10
→ WEB-11 / DB-06
→ DB-07
→ DB-08
```

---

## PHASE 5 — Mise en ligne publique

| ID | Statut | Tâche | Critère d’acceptation |
|---|---|---|---|
| PUB-01 | `BLOCKED` | Choisir la méthode d’exposition | Tunnel ou redirection |
| PUB-02 | `NEXT` | Configurer le DNS public | Domaine résolu |
| PUB-03 | `NEXT` | Configurer HTTPS | Certificat valide |
| PUB-04 | `NEXT` | Configurer les cookies production | Secure, HttpOnly, SameSite |
| PUB-05 | `NEXT` | Configurer l’URL publique | `APP_BASE_URL` correcte |
| PUB-06 | `NEXT` | Préparer les QR définitifs | URL publique, tokens stables |
| PUB-07 | `NEXT` | Tester hors Wi-Fi | Accès LTE/5G |
| PUB-08 | `NEXT` | Vérifier les ports exposés | Pas de 5432 ni 8000 publics |
| PUB-09 | `NEXT` | Test de sécurité minimal | Auth, permissions, erreurs |
| PUB-10 | `NEXT` | Publier la première version | Tag et journal de déploiement |

---

## PHASE 6 — Sauvegardes et exploitation

| ID | Statut | Tâche | Critère d’acceptation |
|---|---|---|---|
| OPS-01 | `NEXT` | Script `pg_dump` automatisé | Dump quotidien |
| OPS-02 | `NEXT` | Stockage hors SQL01 | Deuxième emplacement |
| OPS-03 | `NEXT` | Politique de rétention | Quotidien/hebdo/mensuel |
| OPS-04 | `NEXT` | Test de restauration | DB temporaire validée |
| OPS-05 | `NEXT` | Monitoring `/healthz` | Alerte en cas de panne |
| OPS-06 | `NEXT` | Monitoring espace disque | WEB01 et SQL01 |
| OPS-07 | `NEXT` | Monitoring certificat TLS | Alerte avant expiration |
| OPS-08 | `NEXT` | Procédure de mise à jour | Déploiement reproductible |
| OPS-09 | `NEXT` | Procédure de rollback | Code, DB et VM |
| OPS-10 | `NEXT` | Vérifier les logs | App, Caddy, PostgreSQL, `logthis` |

---

## PHASE 7 — UX/UI et portfolio

| ID | Statut | Tâche | Critère d’acceptation |
|---|---|---|---|
| UX-01 | `DONE` | Mettre à jour le mandat UX/UI | Scan direct et intérêt informatif documentés |
| UX-02 | `DONE` | Inventorier les écrans actuels | Écrans publics, membres et admin recensés |
| UX-03 | `DONE` | Améliorer la navigation mobile | Navigation flexible et scan sans confirmation humaine |
| UX-04 | `DONE` | Harmoniser badges et statuts | Libellés français et badges cohérents sur les vues de boîtes |
| UX-05 | `DONE` | États vides et erreurs | Pages 400/404/500 et listes vides expliquées avec une action utile |
| UX-06 | `DONE` | Accessibilité de base | Focus visible, accès direct au contenu, labels et tableaux descriptifs |
| UX-07 | `DONE` | Mode liste / miniatures | Vues commutables, listes mobiles lisibles et résumés récents sur l’accueil |
| UX-08 | `LATER` | Page Communauté | Après déploiement |
| UX-09 | `LATER` | Scanner caméra intégré | Après HTTPS |
| UX-10 | `LATER` | Design final portfolio | Après validation fonctionnelle |

---

# 4. Décisions ouvertes

## D-01 — Base de production

```text
A. Réutiliser racinepoir_ludotheque
B. Créer racinepoir_ludotheque_prod
```

**Décision : B — créer `racinepoir_ludotheque_prod` sur SQL01.**

## D-02 — Exposition publique

```text
A. Redirection 80/443
B. Cloudflare Tunnel
C. Accès privé seulement
```

## D-03 — Scan direct (`CLOSED`)

Décision MVP : après l’authentification, l’application reprend automatiquement
le scan, transfère la boîte et affiche le résultat. Aucune confirmation humaine
supplémentaire n’est demandée. Aucun mécanisme d’annulation ou de réservation
n’est ajouté. L’historique demeure visible sur la fiche de la boîte.

## D-04 — Données initiales

```text
- données réelles;
- données de démonstration;
- aucune donnée préchargée.
```

## D-05 — Accès Codex à WEB01 (`CLOSED`)

Décision : utiliser le compte SSH dédié `deploy-racinepoir`, installé et
autorisé par Maxime le 9 août 2026, avec écriture sur le seul checkout
RacinePoir et des commandes d’exploitation limitées. Les secrets,
l’environnement Python et l’administration générale du serveur ne sont pas
directement exposés. Le montage SSHFS est disponible dans
`/home/pmax/web01-racinepoir`; la santé et la révocation restent à valider selon
`docs/WEB01_CODEX_ACCESS.md`.

---

# 5. Prochain sprint recommandé

## Sprint Finaliser WEB01 après rétablissement de la base

Une seule carte `NEXT` ou `VERIFY` doit être traitée à la fois, avec preuve,
checkpoint et séparation stricte entre infrastructure et code.

1. `WEB-16` — terminer la validation de l’accès dédié par un essai contrôlé de
   révocation; le test de santé est maintenant réussi.
2. `DB-07` — vérifier si un administrateur existe déjà dans la base de production;
   le créer interactivement seulement s’il est absent.
3. `DB-08` — produire et vérifier le premier dump de production.
4. `WEB-02` puis `WEB-03` — activer l’autostart et prendre un snapshot propre.

Après ce sprint, décider `D-02` avant d’entamer `PUB-02` à `PUB-10`.

---

# 6. Matrice de responsabilités

| Domaine | Responsable principal |
|---|---|
| Produit et décisions finales | Maxime |
| Code applicatif | Codex, sous validation de Maxime |
| Revue technique et planification | ChatGPT Projet |
| Proxmox et WEB01 | Maxime |
| PostgreSQL et SQL01 | Maxime |
| DNS interne et public | Maxime |
| UX/UI visuel | Designer et Maxime |
| Déclenchement du déploiement | Maxime |
| Réception des alertes | Maxime |
| Rollback | Maxime, selon la procédure documentée |

Pour les éléments partagés comme systemd, Caddy, les migrations et les sauvegardes,
Codex prépare les fichiers, commandes et validations. Maxime autorise et exécute les
changements sur l’infrastructure.

---

# 7. Définition de “première version web prête”

- [ ] branche stable et propre;
- [x] migrations reproductibles;
- [x] admin créable sans seed destructif avec `flask create-admin`;
- [x] login, jeux, boîtes, scan et intérêts fonctionnent dans la suite automatisée;
- [x] ajout manuel indépendant de BGG vérifié automatiquement;
- [x] application sur WEB01 avec Gunicorn/systemd;
- [x] Caddy fonctionne sur le LAN en HTTP;
- [x] base prod séparée créée et migrée;
- [ ] HTTPS public;
- [ ] QR avec domaine public;
- [ ] backup créé;
- [ ] restauration testée;
- [x] redémarrage applicatif automatisé validé sur base isolée;
- [ ] redémarrage complet WEB01 et SQL01 validé en production;
- [ ] test externe hors Wi-Fi.

---

# 8. Commandes de suivi

Afficher les tâches `NEXT` :

```bash
grep -n '`NEXT`' docs/PROJECT_BOARD.md
```

Afficher les tâches bloquées :

```bash
grep -n '`BLOCKED`' docs/PROJECT_BOARD.md
```

Commit :

```bash
git add docs/PROJECT_BOARD.md
git commit -m "Add project execution board"
logthis "Ludothèque: ajout du tableau de suivi du projet"
```
