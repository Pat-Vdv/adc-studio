# Project Status

Version du dépôt : voir le fichier VERSION

## Focus

- End-to-end validation
- Reference report
- Component assembly
- Feedback loop

## Contrat documentaire

Le catalogue compte 13 composants. Les blocs narratifs `incident_context`,
`investigations` et `probable_cause` ont été promus au catalogue selon un motif
reproductible (voir `docs/architecture/narrative-block-promotion.md`).

La propriété de chaque règle est établie : la forme locale appartient au contrat
du composant, la présence et les règles globales au validateur métier, l'ordre et
les cardinalités au profil (ADR-0012).

## Décision ouverte

`conclusion` est le seul fragment racine restant. Son statut engage l'existence
d'une troisième nature contractuelle, dont le coût n'est pas amorti par un unique
champ textuel : la décision est différée jusqu'à ce qu'un second cas l'appelle, ou
qu'un statut de composant se démontre suffisant (ADR-0013, D2).
