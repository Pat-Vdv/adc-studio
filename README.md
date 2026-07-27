# ADC Studio

Suite documentaire générique d’A.D.C.

ADC Studio regroupe l’identité documentaire, les composants graphiques, les modèles Word/PDF et les outils de génération utilisés pour produire des livrables techniques cohérents et professionnels.

## Objectifs

- centraliser les règles de mise en page ;
- versionner les modèles comme un produit logiciel ;
- réutiliser les mêmes composants dans tous les rapports ;
- séparer strictement le framework générique des données clients ;
- permettre l’automatisation progressive de la génération documentaire.

## Structure

```text
assets/       Ressources graphiques génériques
brand/        Brand Book et règles d’identité
components/   Composants documentaires réutilisables
docs/         Documentation du projet
examples/     Exemples fictifs ou anonymisés
templates/    Modèles Word et PDF
tools/        Scripts et outils de génération
build/        Fichiers temporaires de construction
exports/      Livrables générés localement
```

## Confidentialité

Ce dépôt ne doit contenir aucune donnée client réelle, aucun secret, aucune configuration de production et aucun rapport confidentiel.

Les rapports clients doivent être conservés hors du dépôt, par exemple dans :

```text
D:\Projets\ADC-Clients\
```

## Version

Version initiale : `0.1.0`
