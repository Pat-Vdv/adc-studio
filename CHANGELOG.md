## Contractualisation des blocs narratifs (ADR-0013)

Une même évolution architecturale, livrée en trois promotions suivant un motif
unique — et non trois fonctionnalités indépendantes.

- **Gouvernance** — ADR-0012 attribue un propriétaire à chaque règle du contrat
  et un producteur à chaque nœud ; ADR-0013 décide le statut de chaque bloc
  narratif, indépendamment, selon le comportement qu'il doit porter.
- **C-011 Incident Context** — le contrat ferme la structure. Un champ mal
  orthographié était ignoré en silence et produisait une section vide.
- **C-012 Investigation** — le contrat exige l'identifiant, prérequis de
  consommation. Une entrée sans `id` disparaissait du rapport sans diagnostic.
- **C-013 Probable Cause** — le contrat garantit la forme des références, jamais
  leur cible. Une liste écrite comme une chaîne était ignorée en silence.
- **Unicité des identifiants d'occurrence** — règle uniformisée sur les six blocs
  répétables : elle est une propriété de l'identité d'occurrence, pas un service
  rendu aux références.
- **Invariant d'architecture** — le statut de composant oblige à un ensemble
  d'artefacts, désormais vérifié.
- `conclusion` reste un fragment racine : décision explicitement différée.

## Sprint 009
- First end-to-end validation report.
