# Cycle de vie des composants ADC Studio

## États officiels

```text
Planned → Prototype → Draft → Stable → Deprecated → Archived
```

## Définitions

### ⚪ Planned

Le besoin est identifié, mais aucun composant exploitable n’existe encore.

Critères d’entrée :
- identifiant réservé ;
- objectif défini ;
- propriétaire désigné.

### 🔵 Prototype

Une première matérialisation existe. Elle sert à tester la pertinence, la structure et le rendu.

Restrictions :
- usage interne uniquement ;
- structure susceptible de changer sans compatibilité.

### 🟡 Draft

Le composant est fonctionnel et documenté, mais son comportement ou sa présentation peut encore évoluer.

Critères :
- README présent ;
- métadonnées présentes ;
- exemple disponible ou prévu ;
- usage réel limité et contrôlé.

### 🟢 Stable

Le composant est validé pour les livrables clients.

Critères :
- structure validée ;
- règles rédactionnelles documentées ;
- rendu Word/PDF contrôlé ;
- exemple réel ou représentatif ;
- absence de défaut bloquant ;
- version au moins `1.0`.

Règle : une modification incompatible impose une nouvelle version majeure.

### 🟣 Deprecated

Le composant ne doit plus être utilisé dans les nouveaux documents, mais reste maintenu pour la lecture ou la régénération d’anciens rapports.

### ⚫ Archived

Le composant est retiré du framework actif. Sa documentation peut être conservée pour l’historique.

## Règles de versionnement

ADC Studio applique une logique inspirée de Semantic Versioning :

- **MAJOR** : changement incompatible de structure ou de sens ;
- **MINOR** : ajout compatible ou nouvelle variante ;
- **PATCH** : correction sans impact fonctionnel.

Avant `1.0`, les versions `0.x` indiquent une API documentaire non stabilisée.

## Promotion d’un composant

Toute promotion doit mettre à jour :

- `metadata.yaml` ;
- le README du composant ;
- `COMPONENT_CATALOG.md` ;
- `PROJECT_STATUS.md` ;
- `CHANGELOG.md`.
