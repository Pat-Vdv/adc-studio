# C-011 Incident Context

Statut : Draft — promu depuis un bloc narratif par ADR-0013.

## Objectif

Décrire les circonstances de l'incident : ce qui l'a déclenché, le périmètre
technique concerné, et l'état d'avancement déclaré du traitement.

## Fragment source

Le nœud `incident_context` de la source, lu en entier par le builder.

| Champ | Type | Rôle |
|---|---|---|
| `description` | chaîne | circonstances rédigées ; les paragraphes sont séparés par une ligne vide |
| `trigger` | chaîne | ce qui a déclenché l'incident |
| `scope` | chaîne | périmètre technique concerné |
| `status` | chaîne | statut déclaré du traitement |

Aucun champ n'est obligatoire : un contexte partiellement rédigé se compose et se
rend. Aucun champ inconnu n'est accepté — c'est la garantie principale de ce
contrat, un champ mal orthographié étant auparavant ignoré en silence.

## Ce que le contrat ne dit pas

Le vocabulaire de `status` n'est pas fermé. Aucune règle de domaine ne l'atteste
aujourd'hui : que le renderer sache traduire certaines valeurs relève de la
présentation et ne ferme rien (ADR-0010, origine d'une contrainte). Le fermer
demandera que le domaine énonce d'abord la liste des statuts admis.

## Règle rédactionnelle

Le contexte décrit des circonstances, pas des conclusions. Une cause probable se
rédige dans son propre bloc, un constat dans C-004.
