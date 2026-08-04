# C-013 Probable Cause

Statut : Draft — promu depuis un bloc narratif par ADR-0013.

## Objectif

Énoncer la cause probable de l'incident, le niveau de confiance qui l'accompagne,
et les constats sur lesquels elle s'appuie.

## Fragment source

Le nœud `probable_cause` de la source, bloc unique et facultatif (0..1).

| Champ | Type | Rôle |
|---|---|---|
| `statement` | chaîne | énoncé de la cause ; paragraphes séparés par une ligne vide |
| `confidence` | chaîne | niveau de confiance déclaré |
| `supporting_finding_ids` | liste de chaînes non vides | constats à l'appui, dans l'ordre de la source |

Aucun champ n'est requis : une cause probable en cours de rédaction se compose.

## Ce que le contrat garantit sur les références

`supporting_finding_ids` doit être une **liste de chaînes non vides**. C'est la
raison d'être principale de ce contrat : une chaîne écrite à la place d'une liste
était auparavant ignorée en silence, et les constats cités disparaissaient du
rapport sans que rien ne le signale.

Le contrat garantit la **forme exploitable** de la référence, jamais sa cible.

## Ce que le contrat ne dit pas

- La **résolubilité** des références appartient au validateur métier
  (ADR-0012, G1) : un identifiant inconnu y est diagnostiqué, pas ici.
- Le vocabulaire de `confidence` n'est pas fermé : aucune règle de domaine ne
  l'atteste, et la table de traduction du renderer relève de la présentation
  (ADR-0010).

## Règle rédactionnelle

Une cause probable est une hypothèse argumentée, pas un fait établi. Le fait
vérifiable se consigne dans un constat (C-004) ; c'est le niveau de confiance qui
dit ce que l'analyse tient pour acquis.
