# RacinePoir templates — claim UI v2

Ce paquet remplace les templates Flask/Jinja.

Changement principal :
- interface normale = "Claim cette copie"
- plus de liste de destinations sur la fiche copie
- le scan sert à confirmer que la copie est maintenant à la location principale du user connecté
- base.html contient le header commun, la navigation et le statut login

Installation depuis le dossier du projet :

```bash
cd ~/racinepoir-ludotheque
unzip ~/Downloads/racinepoir_templates_claim_v2.zip -d .
```

Puis tester :

```bash
python run.py
```

Pages à vérifier :
- /login
- /copies
- /copies/1
- /scan/dev-catan-copy-001

Après validation :

```bash
git status
git add app/templates/
git commit -m "Use claim flow in copy templates"
logthis "Ludothèque: interface claim au lieu de déplacements manuels"
```
