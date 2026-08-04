# C-012 Investigation

Statut : Draft — promu depuis un bloc narratif par ADR-0013.

## Objectif

Consigner un travail d'investigation mené pendant l'intervention : ce qui a été
cherché, comment, et ce que la recherche a donné.

## Fragment source

Une occurrence du nœud `investigations`. Le composant est répétable : chaque
entrée produit sa propre section, dans l'ordre de la source.

| Champ | Type | Requis | Rôle |
|---|---|:---:|---|
| `id` | chaîne non vide | **oui** | identifiant d'occurrence |
| `title` | chaîne | non | intitulé, repris dans l'en-tête de la section |
| `description` | chaîne | non | ce qui a été cherché ; paragraphes séparés par une ligne vide |
| `result` | chaîne | non | résultat déclaré |

## Pourquoi `id` est le seul champ requis

C'est un **prérequis de consommation** (ADR-0010) : le moteur instancie
l'occurrence par cet identifiant. Une entrée qui n'en porte pas n'est ni
identifiée ni instanciée — elle disparaît du document sans diagnostic. Ce n'est
donc ni une règle métier ni une préférence, mais la condition d'existence du
bloc.

Les autres champs relèvent de la **qualité de restitution** : leur absence
dégrade le rendu sans empêcher la consommation. Les rendre obligatoires ferait
porter au contrat une exigence de présentation, ce qu'ADR-0010 réserve au cas où
le domaine énonce la règle.

## Ce que le contrat ne dit pas

- Le vocabulaire de `result` n'est pas fermé : aucune règle de domaine ne
  l'atteste, et le renderer restitue la valeur telle quelle.
- L'**unicité** des identifiants n'est pas de son ressort : un schéma local ne
  voit qu'une occurrence à la fois. Elle appartient au validateur métier
  (ADR-0012, G1).

## Règle rédactionnelle

Une investigation décrit une démarche et son résultat. Le fait établi qui en
découle se consigne dans un constat (C-004), la preuve dans C-010.
