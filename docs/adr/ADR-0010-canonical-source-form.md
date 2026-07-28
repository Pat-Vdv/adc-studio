# ADR-0010 — Forme canonique et tolérances de compatibilité

## Statut

Accepté

## Date

2026-07-28

## Contexte

Les `schema.json` de la bibliothèque décrivent le **fragment source** consommé
par un composant (ADR-0008 § 2). Les builders, eux, sont volontairement
tolérants : ils acceptent parfois des formes supplémentaires, par robustesse ou
par héritage.

Le cas est réel et déjà présent. Le champ `executive_summary.context` est
déclaré comme une chaîne, mais l'utilitaire interne `_paragraphs` accepte aussi
une liste de chaînes, et un test exerce cette forme.

Sans règle écrite, un lecteur du code en conclura que le schéma est incomplet et
« corrigera » le contrat — typiquement en ajoutant un `oneOf` — parce qu'il aura
constaté que l'implémentation accepte davantage. Le contrat public s'élargirait
alors par accident, au rythme des tolérances internes, et deviendrait impossible
à resserrer sans casser des sources déjà écrites.

## Décision

Deux notions distinctes, qui ne doivent pas être confondues :

**Forme canonique.** Ce que les `schema.json` décrivent : la seule écriture que
le projet promeut auprès des rédacteurs et des modèles de langage. C'est aussi
la forme des `example.json`.

**Tolérance de compatibilité.** Ce qu'un builder accepte en plus, sans que cela
constitue un engagement. Une tolérance est un détail d'implémentation : elle
peut être retirée sans révision de contrat.

Une tolérance ne devient contrat que par une **promotion explicite**, c'est-à-dire
un commit qui fait évoluer ensemble le schéma, l'exemple et les tests — jamais
par simple constat de son existence dans le code.

## Portée d'un schéma de composant

Une seule règle détermine ce qu'un `schema.json` décrit :

> Le `schema.json` d'un composant décrit exactement le fragment source
> **consommé par son builder**, ni plus ni moins.

Elle explique, sans convention particulière, que la forme du schéma varie d'un
composant à l'autre :

| Composant | Ce que le builder reçoit | Forme du schéma |
|---|---|---|
| C-003 Executive Summary | le noeud `executive_summary` | objet |
| C-009 Environment | le noeud `environment` | objet |
| C-008 Timeline | la collection `timeline` entière | tableau |
| C-004 Finding | **une** occurrence de `findings` | objet |

Un composant répétable décrit donc **une occurrence**. La collection qui les
porte — sa présence, sa cardinalité, l'unicité de ses identifiants — relève du
noeud parent et du profil, jamais du schéma du composant.

## Contraintes de structure et règles métier

Deux natures de contraintes cohabitent dans un schéma, et seule la seconde
demande une attestation dans le domaine :

- **Structure** — `type`, `additionalProperties: false`, et `minLength: 1` sur
  un identifiant. Un identifiant vide n'a aucune sémantique : il ne permet ni
  référence, ni résolution, ni unicité, ni diagnostic utile. Ces contraintes
  peuvent être posées même quand l'implémentation ne les vérifie pas encore.
- **Règles métier** — `enum`, bornes numériques, `format`, longueurs minimales
  sur du texte rédigé. Elles ne sont posées que si un vocabulaire ou une règle
  existe déjà et est attesté, jamais par intuition à partir du nom d'un champ.

## Conséquences

- Un schéma n'est pas élargi au motif que l'implémentation accepte davantage.
  L'écart entre schéma et tolérance est **attendu**, pas un défaut.
- Un test qui exerce une forme tolérée est un **test de robustesse du builder**,
  non un test de contrat. Son intitulé et son commentaire doivent le dire.
- Un `example.json` est toujours écrit sous la forme canonique : il est la
  première preuve positive du contrat.
- Retirer une tolérance ne requiert pas de révision d'ADR ; élargir le contrat,
  si.
- Inversement, le schéma ne doit jamais décrire une forme que l'implémentation
  **refuse** : le contrat peut être plus étroit que le code, jamais plus large.

## Exemple

État actuel, conforme à cette décision :

| | `executive_summary.context` |
|---|---|
| Schéma | `{"type": "string"}` |
| Exemple | une chaîne |
| Builder | chaîne **ou** liste de chaînes |
| Statut de la liste | tolérance, hors contrat |

## Liens

- ADR-0008 — Document Composition Model : rôle du fragment source.
- ADR-0009 — Composition Pipeline : invariants d'exécution de la chaîne.
