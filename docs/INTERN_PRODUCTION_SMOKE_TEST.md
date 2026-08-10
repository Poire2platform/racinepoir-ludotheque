# Test de fumée WEB01 — guide pour stagiaire

Ce document permet de vérifier l’application RacinePoir après un déploiement.
Il ne donne aucune autorisation d’administrer WEB01, SQL01, pfSense, Caddy,
systemd, PostgreSQL ou Git.

Le testeur utilise seulement un navigateur et les comptes de test remis par la
personne responsable. Il ne doit jamais demander, copier, photographier ou
écrire un mot de passe dans ce document.

## 1. Fiche d’exécution

À remplir avant de commencer :

| Champ | Valeur |
|---|---|
| Date et heure de début | |
| Nom du testeur | |
| Responsable présent ou joignable | |
| URL fournie par le responsable | |
| Version ou commit annoncé | |
| Navigateur et appareil | |
| Compte membre de test | |
| Compte administrateur de test | |
| Boîte de test autorisée | |
| Détenteur attendu avant le scan | |
| Détenteur attendu après le scan | |

Ne pas continuer si l’URL, les deux comptes de test ou la boîte de test ne sont
pas fournis. Ne jamais improviser avec un compte ou une boîte réelle.

## 2. Règles de sécurité

- [ ] J’ai confirmé que je teste le bon environnement et la bonne URL.
- [ ] J’utilise uniquement les comptes et la boîte désignés pour ce test.
- [ ] Je n’exécuterai aucune commande dans un terminal ou sur un serveur.
- [ ] Je ne modifierai ni mot de passe, ni rôle, ni compte utilisateur.
- [ ] Je ne créerai, supprimerai ou modifierai aucun jeu ou boîte réelle.
- [ ] Je sais qu’un scan change immédiatement le détenteur de la boîte.
- [ ] Je n’inscrirai aucun secret dans mes notes ou captures d’écran.

Arrêter immédiatement et prévenir le responsable si :

- `/healthz` ne retourne pas `status: ok` et `database: ok`;
- une page affiche un traceback, une exception, un secret ou une URL de base de
  données;
- une action produit une erreur 500 ou prend plus de 10 secondes;
- l’identité, le propriétaire ou le détenteur de la boîte de test est ambigu;
- une permission semble permettre de modifier les données d’une autre personne;
- le résultat réel diffère du résultat attendu dans cette checklist.

## 3. Disponibilité et accès public local

Ouvrir chaque adresse dans un nouvel onglet.

- [ ] `URL/healthz` répond sans délai anormal.
- [ ] La réponse contient `"status":"ok"`.
- [ ] La réponse contient `"database":"ok"`.
- [ ] `URL/` affiche la page d’accueil sans erreur technique.
- [ ] La navigation est lisible sur l’appareil utilisé.
- [ ] Sans connexion, une page réservée redirige vers la connexion plutôt que
  d’afficher son contenu.

Preuve ou remarque :

```text

```

## 4. Connexion membre

Utiliser le compte membre de test remis par le responsable.

- [ ] Un mauvais mot de passe est refusé sans révéler si le mot de passe ou le
  compte est la cause exacte.
- [ ] Le bon mot de passe ouvre une session.
- [ ] Le nom affiché correspond au compte membre de test.
- [ ] La déconnexion ferme la session.
- [ ] Le bouton Retour du navigateur ne redonne pas accès à une page privée.
- [ ] Une nouvelle connexion valide fonctionne après la déconnexion.

Ne pas répéter volontairement les échecs de connexion : la protection contre
les tentatives répétées peut retourner HTTP 429.

Preuve ou remarque :

```text

```

## 5. Catalogue et inventaire en lecture

En étant connecté comme membre :

- [ ] La liste des jeux s’ouvre et présente des titres lisibles.
- [ ] La fiche d’un jeu s’ouvre et montre ses boîtes liées.
- [ ] La liste des boîtes s’ouvre sans identifiants techniques inutiles.
- [ ] La fiche de la boîte de test montre son propriétaire, son détenteur, son
  statut et son historique.
- [ ] Les recherches par titre donnent un résultat cohérent.
- [ ] Les filtres propriétaire, détenteur et statut peuvent être appliqués puis
  retirés.
- [ ] La vue « Chez moi » distingue les boîtes détenues des boîtes possédées.
- [ ] La vue « Mes boîtes » indique correctement le détenteur réel.
- [ ] La vue des intérêts s’ouvre sans erreur.
- [ ] La mise en page demeure utilisable à la largeur d’un téléphone.

Ne pas créer ou modifier de jeu, de boîte ou de note pendant cette section.

Preuve ou remarque :

```text

```

## 6. Scan direct contrôlé

Cette section modifie les données. Obtenir l’accord du responsable juste avant
de continuer et utiliser uniquement la boîte de test indiquée dans la fiche
d’exécution.

- [ ] Le responsable confirme le détenteur attendu avant le scan.
- [ ] J’ouvre l’URL ou le QR de scan fourni pour la boîte de test.
- [ ] Si une connexion est demandée, l’application revient au scan après la
  connexion.
- [ ] Le scan est traité automatiquement, sans second bouton de confirmation.
- [ ] La page de résultat identifie clairement la boîte et le nouveau détenteur.
- [ ] La fiche de la boîte montre le nouveau détenteur attendu.
- [ ] L’historique contient un nouvel événement de scan cohérent.
- [ ] Un intérêt du scanneur est fermé si le scénario en prévoyait un.
- [ ] Les intérêts des autres membres restent inchangés.

Si le détenteur doit être restauré après le test, arrêter ici et demander au
responsable d’effectuer ou d’autoriser la restauration. Le stagiaire ne doit pas
inventer une procédure d’annulation.

Preuve ou remarque :

```text

```

## 7. Permissions administratives

Se déconnecter, puis utiliser uniquement le compte administrateur de test remis
par le responsable.

- [ ] La page de gestion des utilisateurs est visible comme administrateur.
- [ ] Le compte membre de test apparaît avec le bon rôle et le bon état.
- [ ] Une fiche de boîte autorisée présente les actions administratives prévues.
- [ ] Après reconnexion comme membre, les fonctions réservées aux administrateurs
  ne sont plus visibles ou sont refusées.

Ce test est une inspection seulement. Ne pas créer de compte, changer un rôle,
réinitialiser un mot de passe, désactiver un utilisateur ou modifier une boîte.

Preuve ou remarque :

```text

```

## 8. Pages de parties et joueurs

- [ ] La liste des parties s’ouvre sans erreur.
- [ ] La liste des joueurs s’ouvre sans erreur.
- [ ] Une fiche joueur existante affiche ses statistiques sans détail technique.
- [ ] Une partie existante peut être consultée sans modifier ses données.

Ne pas enregistrer de partie ou de joueur invité sans scénario de test approuvé.

Preuve ou remarque :

```text

```

## 9. Résultat final

- [ ] Toutes les cases obligatoires ont réussi.
- [ ] Toute donnée modifiée pendant le scan est dans l’état convenu avec le
  responsable.
- [ ] Aucune donnée non autorisée n’a été créée, modifiée ou supprimée.
- [ ] Les captures et notes ne contiennent aucun secret.
- [ ] Les anomalies ont un numéro, une heure, une page et des étapes de
  reproduction.

Résultat :

- [ ] **RÉUSSI** — aucune anomalie bloquante.
- [ ] **ÉCHEC** — au moins une anomalie bloquante; déploiement à ne pas approuver.
- [ ] **INCOMPLET** — prérequis ou autorisation manquant; aucun verdict rendu.

| Champ | Valeur |
|---|---|
| Heure de fin | |
| Résultat | |
| Numéros des anomalies | |
| Données à restaurer | |
| Nom du testeur | |
| Validation du responsable | |

## 10. Modèle d’anomalie

Créer une fiche distincte par problème :

```text
Titre :
Date et heure :
URL ou page :
Compte de test utilisé, sans mot de passe :
Étapes exactes :
Résultat attendu :
Résultat obtenu :
Erreur visible, sans secret :
Capture d’écran nettoyée : oui / non
Données possiblement modifiées :
Test interrompu : oui / non
```

Le responsable décide ensuite si le problème exige un rollback, une correction
ou une simple note de suivi. Le stagiaire ne redémarre aucun service et ne tente
aucune réparation sur l’infrastructure.
