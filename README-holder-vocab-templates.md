# RacinePoir templates — vocabulaire détenteur v3

Ce paquet remplace les templates Flask/Jinja.

Changement principal :
- On n'affiche plus "location" comme un lieu physique.
- L'interface parle plutôt de :
  - Détenteur actuel
  - J’ai cette copie
  - Demandé par / destination souhaitée

La base de données reste inchangée pour l'instant :
- `current_location_id` reste utilisé techniquement
- `wanted_location_id` reste utilisé techniquement

Installation :

```bash
cd ~/racinepoir-ludotheque
unzip ~/Downloads/racinepoir_templates_holder_vocab_v3.zip -d .
```

Test :

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
git commit -m "Use holder vocabulary in copy templates"
logthis "Ludothèque: vocabulaire interface aligné sur détenteur actuel plutôt que location physique"
```
