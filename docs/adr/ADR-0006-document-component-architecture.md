# ADR-0006 — Document Component Architecture

- **Statut :** Acceptée
- **Date :** 2026-07-27
- **Décision :** construire ADC Studio autour de composants documentaires autonomes et versionnés.

## Contexte

Un modèle Word monolithique devient rapidement difficile à maintenir : les changements de mise en page, de structure et de rédaction se propagent sans traçabilité et les rapports anciens deviennent difficiles à reproduire.

ADC Studio doit pouvoir produire des rapports variés — audit, intervention, SQL Server, Linux, réseau, cybersécurité, IA — sans recréer à chaque fois les mêmes structures.

## Décision

Chaque structure réutilisable est traitée comme un composant documentaire :

- identifiant stable `C-xxx` ;
- nom et objectif explicites ;
- version ;
- statut de maturité ;
- documentation ;
- métadonnées ;
- exemples et rendus lorsque nécessaire.

Les rapports sont des assemblages de composants. Un composant stable ne peut subir de changement incompatible sans nouvelle version majeure.

## Conséquences positives

- traçabilité des évolutions ;
- cohérence entre rapports ;
- réutilisation multi-domaines ;
- reprise du projet facilitée ;
- automatisation future plus sûre ;
- possibilité d’identifier précisément la composition d’un rapport.

## Coûts et contraintes

- documentation plus rigoureuse ;
- gestion explicite des versions ;
- validation visuelle nécessaire ;
- davantage de fichiers et de discipline de maintenance.

## Alternatives rejetées

### Modèle Word unique

Simple au départ, mais trop couplé et difficile à faire évoluer.

### Bibliothèque sans versionnement

Réutilisable, mais insuffisante pour reproduire les anciens livrables et gérer les ruptures.

### Automatisation immédiate

Rejetée : automatiser avant de stabiliser le framework risquerait de figer des choix encore immatures.
