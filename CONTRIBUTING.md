# Contribution à ADC Studio

## Principes

Toute contribution doit respecter :

- la cohérence graphique A.D.C. ;
- la séparation entre framework générique et données clients ;
- la lisibilité des fichiers sources ;
- la traçabilité des changements ;
- la compatibilité Windows et Linux lorsque cela s’applique.

## Workflow Git recommandé

```bash
git checkout -b feature/nom-court
git add .
git commit -m "Description claire du changement"
git push
```

## Conventions de commit

Exemples :

```text
Add ADC Brand Book cover
Update Word heading styles
Fix PDF export margins
Document confidentiality rules
```

## Revue avant commit

Vérifier systématiquement :

- absence de données client ;
- absence de secrets ;
- absence de fichiers temporaires ;
- cohérence des noms de fichiers ;
- mise à jour du CHANGELOG si nécessaire.
