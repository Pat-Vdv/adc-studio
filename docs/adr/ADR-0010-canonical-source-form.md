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
| C-001 Cover | les noeuds `report` et `client` de la racine | objet racine, non fermé |

Un composant répétable décrit donc **une occurrence**. La collection qui les
porte — sa présence, sa cardinalité, l'unicité de ses identifiants — relève du
noeud parent et du profil, jamais du schéma du composant.

### Noeud source partagé entre plusieurs composants

Les premiers composants durcis possédaient chacun leur noeud. Fermer l'objet
(`additionalProperties: false`) y disait quelque chose de vrai : ce composant
connaît tout ce que ce noeud porte, un champ non décrit est hors contrat.

La couverture rompt cette correspondance. Son builder ne reçoit pas un noeud
mais deux, `report` et `client`, dont il ne lit qu'une partie des champs — et
que l'identité documentaire lit également, comme la composition en tire par
ailleurs les métadonnées du document.

Un noeud partagé ne peut pas être fermé par le schéma d'un seul de ses
lecteurs : C-001 rejetterait `report.language` ou `report.revisions`, champs
qu'il ne consomme pas mais que C-002 consomme légitimement. Le premier
composant durci figerait le noeud pour tous les suivants. D'où la règle :

> Un schéma ne ferme que ce que son composant possède **en propre**. Sur un
> noeud partagé, il décrit les champs que son builder consomme, et reste muet —
> donc ouvert — sur les autres.

Le silence n'y est pas un aveu d'inachèvement : un champ non décrit n'est pas
hors contrat, il relève du contrat d'un autre composant. Deux conséquences :

- l'ouverture d'un noeud partagé se justifie dans la description du schéma,
  faute de quoi un lecteur la prendra pour un durcissement oublié et la
  « corrigera » ;
- un champ décrit par deux composants doit l'être de la même manière. Une
  divergence est un désaccord de contrat, jamais une spécialisation locale.

Le partage se constate **noeud par noeud** ; il ne se propage pas aux
descendants. `report` est partagé, mais `report.revisions` n'est lu que par
C-002, qui le possède donc en propre et le ferme. Un noeud ouvert peut porter
des sous-noeuds fermés : l'ouverture n'est pas une propriété héritée, c'est le
constat d'une lecture multiple.

## Localisation d'un fragment dans la source

Un `schema.json` décrit la **forme** d'un fragment ; rien n'y dit **où** ce
fragment se lit dans une source. Tant que les contrats n'ont servi qu'à leurs
propres tests, cette connaissance a pu rester implicite — répartie entre les
builders, qui la portent en dur, et les tests, qui la réécrivent composant par
composant. Valider une source entière l'exige explicite.

Cette localisation est une **table**, pas une convention : le nom du nœud ne se
déduit pas de l'identifiant du composant. C-007 Decision lit `actions_taken`.

| Nature | Ce qui est validé | Exemple |
|---|---|---|
| nœud | le nœud lui-même | C-003 → `executive_summary` |
| collection | la collection entière | C-008 → `timeline` |
| occurrence | chaque entrée, une validation par entrée | C-004 → `findings[*]` |
| racine | la source entière | C-001, C-002 |

La table appartient à une **famille de rapports**, non à la bibliothèque : deux
familles nomment différemment les mêmes composants. Son hébergement naturel à
terme est le profil, qui déclare déjà quels composants constituent la famille ;
elle reste hors du profil tant qu'une seule famille possède des builders.

### Un nœud que personne ne réclame

La table dit ce qui est couvert ; elle dit donc aussi, par différence, ce qui ne
l'est pas. Un nœud source qu'aucun contrat ne réclame ne serait vérifié par
aucun schéma, et rien ne le signalerait :

> Un nœud source hors de la table est **suivi explicitement**, jamais ignoré en
> silence. La liste des nœuds sans contrat est une donnée du dépôt, vérifiée
> dans les deux sens.

C'est la discipline déjà appliquée aux composants sans contrat, portée au
niveau du rapport. Elle rend visible un trou que l'inventaire des composants ne
pouvait pas voir : les blocs `narrative` — contexte de l'incident, cause
probable, conclusion, investigations — sont consommés par des builders sans être
des composants du catalogue. Ils n'ont donc ni répertoire, ni schéma, ni
exemple, et aucun test ne les réclamait.

Ce constat ne se corrige pas ici : il nomme le travail restant.

## Origine d'une contrainte

Avant d'ajouter une contrainte, il faut savoir **d'où elle tire sa légitimité**.
Quatre origines, dont trois seulement autorisent une entrée dans le schéma :

| Origine | Exemple | Dans le schéma ? |
|---|---|---|
| **Domaine** | `severity`, `priority` : vocabulaire fermé déjà appliqué par le validateur | Oui |
| **Structure** | `type`, `additionalProperties: false`, identifiant non vide | Oui |
| **Prérequis de consommation** | identifiant par lequel un builder sélectionne une occurrence | Oui |
| **Présentation** | libellés traduits, accords, mise en forme DOCX | Non |

- **Domaine** — une règle existe déjà et est attestée. Le schéma la reprend, il
  ne l'invente pas.
- **Structure** — la forme du contrat l'exige, indépendamment du métier. Un
  identifiant vide n'a aucune sémantique : il ne permet ni référence, ni
  résolution, ni unicité, ni diagnostic utile. Ces contraintes peuvent être
  posées même quand l'implémentation ne les vérifie pas encore.
- **Prérequis de consommation** — le moteur ne peut pas travailler sans. Un
  composant répétable est instancié par identifiant : une occurrence qui n'en
  porte pas est silencieusement absente du document. Ce n'est ni une règle
  métier ni une préférence, c'est un contrat de consommation déjà réel, et il
  peut être exigé même si le validateur ne le vérifie pas encore.
- **Présentation** — une couche aval qui *sait exploiter* une valeur n'atteste
  rien. Le renderer traduit `high` en « Élevé » par connaissance éditoriale ;
  cela ne ferme pas pour autant le vocabulaire du champ concerné.

Cette dernière ligne explique une asymétrie assumée : `severity` et `priority`
portent un `enum`, `level` non — le validateur ferme les deux premiers
vocabulaires, aucun ne ferme le troisième.

### Prérequis de consommation et qualité de restitution

Le prérequis de consommation se reconnaît à une question simple : **le moteur
peut-il encore travailler ?**

| Champ | Sans lui | Nature |
|---|---|---|
| `id` | l'occurrence n'est ni identifiée ni instanciée : elle est absente du document | prérequis de consommation |
| `title` | l'occurrence est composée et rendue ; seule la résolution d'une référence perd son libellé humain | qualité de restitution |

Les index de résolution utilisent les titres lorsqu'ils sont présents. L'absence
de titre n'empêche pas la consommation d'un composant, mais peut empêcher la
restitution d'un libellé lisible lors de la résolution des références : c'est
une **capacité dégradée**, pas un contrat violé.

Rendre `title` obligatoire pour préserver la richesse des renvois ferait porter
au contrat source une exigence de présentation. Cette promotion n'aura lieu que
si le domaine énonce la règle — « toute preuve, tout constat et toute
recommandation doivent être nommés » — et elle suivra alors le chemin habituel :
schéma, exemple, tests, éventuellement validation.

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
