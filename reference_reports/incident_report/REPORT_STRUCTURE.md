# Structure du rapport d’incident

| Ordre | Partie | Composant | Cardinalité |
|---:|---|---|---|
| 1 | Page de garde | `C-001-cover` | 1 |
| 2 | Identité documentaire | `C-002-identity-page` | 1 |
| 3 | Résumé exécutif | `C-003-executive-summary` | 1 |
| 4 | Contexte | narratif | 1 |
| 5 | Environnement | `C-009-environment` | 1 |
| 6 | Chronologie | `C-008-timeline` | 0..1 |
| 7 | Investigations | narratif structuré | 0..n |
| 8 | Constats | `C-004-finding` | 0..n |
| 9 | Cause probable | narratif | 0..1 |
| 10 | Mesures prises | `C-007-decision` | 0..n |
| 11 | Recommandations | `C-005-recommendation` | 0..n |
| 12 | Risques | `C-006-risk` | 0..n |
| 13 | Conclusion | narratif | 1 |
| 14 | Preuves | `C-010-evidence` | 0..n |
