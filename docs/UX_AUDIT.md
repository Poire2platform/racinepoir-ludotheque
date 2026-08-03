# Mandat et inventaire UX

## Mandat produit

Le parcours principal est volontairement direct :

1. une personne scanne le QR d’une boîte;
2. elle se connecte si nécessaire;
3. elle confirme avoir la boîte;
4. la boîte change immédiatement de détenteur et l’historique est écrit.

Le bouton **I would like** ajoute seulement un marqueur de souhait. Il ne réserve
pas la boîte, ne crée aucun rang, ne bloque pas un transfert et ne propose pas
d’annulation. Si la personne intéressée reçoit ensuite la boîte, son propre
marqueur est complété par le scan; les autres marqueurs restent actifs.

Priorités UX : parcours scan court sur téléphone, actions explicites, état de la
boîte lisible et distinction nette entre propriétaire, détenteur, marqueur de
souhait et note en pourcentage d’un jeu.

## Inventaire des écrans

| Accès | Écrans |
|---|---|
| Public | Connexion, inscription, catalogue des jeux, fiche jeu, liste des boîtes, fiche boîte, sécurité pédagogique, santé technique |
| Membre | Accueil, profil, Chez moi, Mes boîtes, ajout de boîte, scan et confirmation, résultat du scan, parties, nouvelle partie, fiche partie, joueurs et fiche joueur |
| Propriétaire ou admin | Modification de boîte, transfert manuel, état perdue/active, étiquette et image QR |
| Admin | Utilisateurs, création/modification d’utilisateur, activation et code d’inscription |

## Constats pour les prochaines cartes

- La navigation principale utilise encore des séparateurs textuels et devient
  dense sur un téléphone.
- Les tableaux défilent horizontalement; les actions importantes doivent rester
  faciles à atteindre sur petit écran.
- Les formulaires héritent tous du même encadrement, y compris les petits
  boutons intégrés à une ligne.
- Les états vides principaux expliquent la prochaine action et les erreurs
  400/404/500 utilisent une page cohérente sans détail interne.
- Les statuts de boîte sont traduits et présentés avec des badges cohérents dans
  la liste, la fiche et les vues personnelles.
