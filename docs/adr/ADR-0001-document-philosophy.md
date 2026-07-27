# ADR-0001 — Document Philosophy

Status: Accepted
Version: 1.0

## Contexte

ADC Studio est développé comme un produit logiciel. Les livrables documentaires
constituent un actif de l'entreprise au même titre que le code source.

## Décision

Toute documentation est construite à partir de composants réutilisables.
Aucun rapport ne doit être créé par copier/coller.

## Principes

1. Les faits sont distingués des hypothèses.
2. Chaque conclusion est justifiée.
3. Les modèles sont versionnés.
4. Les données clients restent hors du dépôt Git.
5. Les composants sont la source unique de vérité.

## Conséquences

- Maintenance simplifiée.
- Qualité homogène.
- Génération automatisable.
