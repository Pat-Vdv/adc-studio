# ADC Studio — Project Status

> Tableau de bord de référence du projet.

| Élément | Valeur |
|---|---|
| Version | **0.4.4** |
| Sprint | **004.4** |
| Statut global | 🟡 En développement |
| Dernière mise à jour | 2026-07-27 |
| Prochain jalon | Sprint 004.5 — Writing Guide |

## Progression globale

```text
ADC Studio Framework       ████░░░░░░ 40 %

Branding                   ██████████ 100 %
Design System              ██████████ 100 %
Word Template              ██████████ 100 %
Component Library          ████░░░░░░  40 %
Writing Guide              ░░░░░░░░░░   0 %
Sample Reports             ░░░░░░░░░░   0 %
PDF Engine                 ░░░░░░░░░░   0 %
PowerPoint                 ░░░░░░░░░░   0 %
```

> La progression globale est indicative. Elle mesure la maturité fonctionnelle du framework, pas le volume de fichiers.

## Bibliothèque de composants

| ID | Composant | Statut | Version | Validé | Utilisé |
|---|---|---|---:|:---:|:---:|
| C-001 | Cover | 🟢 Stable | 1.0 | ✅ | Oui |
| C-002 | Identity Page | 🟢 Stable | 1.0 | ✅ | Oui |
| C-003 | Executive Summary | 🟡 Draft | 0.8 | ❌ | Non |
| C-004 | Finding | 🟢 Stable | 1.0 | ✅ | Oui |
| C-005 | Recommendation | 🟢 Stable | 1.0 | ✅ | Oui |
| C-006 | Risk | 🟡 Draft | 0.7 | ❌ | Non |
| C-007 | Decision | 🟡 Draft | 0.7 | ❌ | Non |
| C-008 | Timeline | 🔵 Prototype | 0.1 | ❌ | Non |
| C-009 | Environment | 🟡 Draft | 0.6 | ❌ | Oui |
| C-010 | Evidence | 🟡 Draft | 0.6 | ❌ | Oui |

## Légende du cycle de vie

| Statut | Signification |
|---|---|
| ⚪ Planned | Prévu, non commencé |
| 🔵 Prototype | Première matérialisation, usage expérimental |
| 🟡 Draft | Fonctionnel, encore susceptible d’évoluer |
| 🟢 Stable | Validé pour les livrables clients |
| 🟣 Deprecated | Maintenu uniquement pour compatibilité |
| ⚫ Archived | Retiré du framework actif |

## Dernier sprint terminé

### Sprint 004.3 — Word Template Baseline

- Intégration de l’identité A.D.C.
- Création du modèle Word professionnel.
- Mise en place des styles, sections, en-têtes et pieds de page.
- Premiers composants incorporés au spécimen.
- Livraison DOCX, DOTX et PDF.

## Sprint courant

### Sprint 004.4 — Component Library Foundation

Objectif : transformer les éléments documentaires en composants autonomes, identifiés et suivis.

Livré :

- [x] Tableau de bord racine `PROJECT_STATUS.md`.
- [x] Catalogue officiel `COMPONENT_CATALOG.md`.
- [x] Arborescence `components/`.
- [x] Dix composants identifiés et numérotés.
- [x] Métadonnées YAML par composant.
- [x] Cycle de vie officiel documenté.
- [x] ADR-0006 rédigée.
- [x] README et roadmap mis à jour.

## Prochains sprints

| Sprint | Objectif | État |
|---|---|---|
| 004.5 | Writing Guide | ⚪ Planned |
| 004.6 | Premier rapport client complet — SQL Server | ⚪ Planned |
| 005.x | Consolidation Word/PDF | ⚪ Planned |
| 006.x | Automatisation documentaire | ⚪ Planned |
| 007.x | PowerPoint | ⚪ Planned |

## Règle de clôture d’un sprint

Un sprint n’est terminé que lorsque :

- les livrables sont présents ;
- les composants concernés sont documentés ;
- leurs statuts et versions sont actualisés ;
- `PROJECT_STATUS.md` est mis à jour ;
- `CHANGELOG.md` est complété ;
- un message de commit est fourni.
