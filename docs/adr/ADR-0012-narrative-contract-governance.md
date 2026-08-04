# ADR-0012 — Gouvernance du contrat narratif

## Statut

Accepté

## Date

2026-07-29

## Contexte

Le chantier suivant devait « définir le modèle narratif ». Le balayage du dépôt montre
que ce modèle n'est pas à inventer : il existe déjà, entièrement, mais **dispersé**. Le
travail n'est donc pas de concevoir, mais de révéler qui possède quoi.

### Où vivent les règles aujourd'hui

| Lieu | Ce qu'il déclare |
|---|---|
| `components/*/schema.json` | la forme locale d'un fragment : champs, types, vocabulaires fermés |
| `profiles/p-003-incident-report.yaml` | l'ordre des blocs et les cardinalités admises (`min` / `max`) |
| `adc_profile/resolution.py` | quel nœud source porte les occurrences d'un bloc, et si le bloc est présent |
| `adc_contracts.INCIDENT_REPORT_FRAGMENTS` | où lire chaque fragment, et sa **nature** — donc sa couverture contractuelle |
| `validate_incident_report.py` | présence des nœuds racine, unicité des identifiants, résolubilité des références |
| `adc_engine/compose.py` | ce que chaque builder lit réellement dans la source |

Rien de tout cela n'est fautif isolément. Le défaut est ailleurs : **le même fait y est
écrit plusieurs fois, sans que rien ne confronte les copies.**

Que le bloc `incident-context` se lise dans le nœud `incident_context` est déclaré
**trois fois** — dans la table des fragments, dans `_SINGLE_OCCURRENCE_SOURCES`, et dans
`_build_incident_context`. Aucun test ne les compare : les tables de `resolution.py` ne
sont confrontées à rien d'autre qu'à elles-mêmes.

### Deux constats vérifiés

**Un nœud narratif n'est confronté à aucun contrat.** Les quatre blocs narratifs —
`incident_context`, `investigations`, `probable_cause`, `conclusion` — sont déclarés
`ROOT_FRAGMENT` : la table les nomme pour désigner leur consommateur, ce qui ne leur
accorde aucune couverture (ADR-0010). Conséquence mesurée sur la source de référence :

```
incident_context: {"foo": "bar", "toto": 42, "banana": ["abc"]}

frontière d'entrée  : aucun écart
validation métier   : aucun écart
composition         : aucun diagnostic
document produit    : un titre « Contexte de l'incident », et rien dessous
```

Toute la chaîne se tait, et le silence va jusqu'au livrable client. C'est aujourd'hui
l'incohérence principale de l'architecture : la campagne de durcissement a fermé la
frontière sur les composants catalogue, et laissé ouverte la moitié narrative du rapport.

**« Vide » et « absent » reçoivent deux réponses contradictoires.** Sur `incident_context: {}` :

- le validateur métier le tient pour **présent** — le nœud figure à la racine, `required`
  est satisfait, aucun diagnostic ;
- la résolution le tient pour **absent** — sa présence est évaluée par `bool(data.get(key))`,
  et émet `cardinalité non respectée : 1 occurrence au minimum, 0 obtenue`.

Les deux couches ont raison selon leur propre règle, et personne n'arbitre. Une décision
sémantique — un nœud vide est-il une section absente ou une section à rédiger ? — est
tombée par accident dans un helper de résolution.

### Le problème posé

Ajouter un traducteur narratif au-dessus de cet état multiplierait les copies au lieu de
les réduire : il déclarerait une quatrième fois où vivent les nœuds, et produirait du
contenu qu'aucun contrat n'examine. La gouvernance doit précéder l'alimentation.

## Décision

> Chaque règle du contrat a **exactement un propriétaire**, et chaque nœud du contrat a
> **exactement un producteur**. Ce qui est écrit ailleurs en dérive ou est confronté par
> un test — jamais recopié.

Six règles en découlent.

**G1 — Une règle, un propriétaire.**

| Règle | Propriétaire |
|---|---|
| la forme locale d'un fragment — champs, types, vocabulaires | le `schema.json` du composant |
| l'ordre des blocs et les cardinalités admises | le profil |
| quel nœud source porte les occurrences d'un bloc | la résolution |
| où se lit un fragment, et de quelle nature il est | la table des fragments |
| présence des nœuds racine, unicité, résolubilité des références | le validateur métier |

Une règle qui n'a pas de propriétaire dans ce tableau n'est pas une règle : c'est une
habitude. Une couche qui veut appliquer une règle dont elle n'est pas propriétaire la
demande à son propriétaire, ou l'ADR est révisée.

**G2 — Un fait n'est déclaré qu'une fois.**
La correspondance entre un bloc et le nœud source qui le porte est un fait unique. Elle a
un propriétaire — la table des fragments, seule à décrire aussi la **nature** du fragment
— et toute autre couche qui en a besoin la dérive, ou est confrontée à elle par un test
qui échoue quand les deux divergent. Trois déclarations indépendantes du même fait sont
trois occasions de dériver en silence.

**G3 — Aucun nœud consommé ne reste sans contrat.**
`ROOT_FRAGMENT` est un **état transitoire tracé**, jamais une destination. Un nœud qu'un
builder lit doit finir par déclarer la forme qu'il attend, sans quoi la frontière d'entrée
ne protège qu'une moitié du rapport et le durcissement reste inachevé.

La nature `ROOT_FRAGMENT` garde son utilité : elle nomme ce qui n'est pas couvert, au lieu
de le laisser invisible. C'est le même mécanisme que `SOURCE_NODES_CONSUMED_BY_NOBODY`,
qui suit à part les nœuds que personne ne lit. Ces deux listes disent l'état d'un chantier ;
elles ne l'excusent pas.

**G4 — Vide et absent sont deux faits distincts, arbitrés une seule fois.**
La **présence** d'un nœud est un fait, propriété du validateur métier. Le **nombre
d'occurrences** qu'il porte en est un autre, propriété de la résolution. Un nœud présent
mais vide est présent : il décrit une section qui reste à rédiger — un défaut de contenu,
que la chaîne signale sans refuser de composer — et non une absence.

Aucune couche ne redéfinit la présence pour son propre usage. Évaluer la présence par la
véracité d'une valeur confond les deux faits et fait dire à la cardinalité ce que la
présence avait déjà dit autrement.

**G5 — Un nœud, un producteur.**
Chaque nœud du contrat canonique est écrit par **exactement un** producteur. Deux
producteurs ne se partagent jamais un nœud, et aucun ne complète ce qu'un autre a écrit.

Cette règle est indépendante des formats d'entrée : elle vaut pour deux fichiers d'un
même atelier comme pour deux outils sans rapport. Elle rend décidable, sans lire le code,
la question « d'où vient cette valeur ? » — et empêche que la fusion de plusieurs sources
devienne une fusion de plusieurs vérités.

Corollaire : la propriété d'un nœud se déclare, elle ne s'observe pas. Un nœud dont deux
producteurs se croient propriétaires est un défaut de gouvernance, pas un conflit à
résoudre au moment de l'écriture.

**G6 — Traduire et produire sont deux métiers, soumis à deux doctrines.**

| | Pont | Producteur |
|---|---|---|
| Ce qu'il fait | change les clés et la forme | fabrique de la donnée métier |
| Ce qu'il ne fait pas | déduire, compléter, forger une identité | — |
| Déterminisme | total : même entrée, même sortie | non garanti |
| Doctrine | ADR-0011 | à écrire, hors de ADR-0011 |
| Place dans la chaîne | frontière amont | strictement en amont de la chaîne (ADR-0009) |

Le critère est unique et vérifiable : **un composant qui forge une valeur que son entrée
ne portait pas est un producteur**, quel que soit son nom. Forger un identifiant, établir
un lien `evidence_ids` ou `related_finding_ids` que rien ne déclarait, c'est produire.

R3 ne sera donc pas assouplie pour accueillir un tel composant. L'assouplir ferait du
contrat l'union des libertés de ses producteurs — l'élargissement par accident qu'ADR-0010
et ADR-0011 existent pour empêcher. Un producteur reçoit sa propre doctrine, à côté, et le
contrat reste unique.

## Portée

Cette ADR gouverne **la répartition des règles et la propriété des nœuds**. Elle ne décrit
aucun format d'entrée, aucun outil de rédaction, aucun moyen d'assistance : ces choix
découlent de la doctrine et ne la précèdent pas.

Elle ne dit pas non plus quelle forme prendront les contrats narratifs — seulement
qu'aucun nœud consommé ne reste durablement sans contrat (G3).

## Conséquences

Deviennent interdits, sans révision de cette ADR :

- déclarer une règle dont G1 attribue la propriété à une autre couche ;
- recopier la correspondance entre un bloc et son nœud source, plutôt que la dériver ou la
  confronter par un test ;
- ajouter un `ROOT_FRAGMENT` sans le rendre visible comme dette, ou l'y laisser au motif
  qu'il fonctionne ;
- évaluer la présence d'un nœud par la véracité de sa valeur ;
- écrire un nœud du contrat depuis deux producteurs, ou compléter le nœud d'un autre ;
- appeler « pont » un composant qui forge une valeur, ou étendre ADR-0011 pour l'accueillir.

Restent ouverts :

- la forme contractuelle des quatre blocs narratifs : composants du catalogue, ou troisième
  nature déclarée. Le choix engage le catalogue et son cycle de vie, et se tranche
  bloc par bloc ;
- l'ordre dans lequel la dette `ROOT_FRAGMENT` est résorbée ;
- le nombre de producteurs, leur technologie et leurs formats d'entrée ;
- la doctrine propre aux producteurs, qui reste à écrire ;
- le sort de `annexes`, nœud que personne ne consomme : le couvrir ou le retirer.

## Vérification

Ce que cette ADR affirme du dépôt a été mesuré, non déduit :

- l'absence de contrat narratif — un `incident_context` arbitraire traverse contrat,
  validation, composition et rendu sans un seul diagnostic ;
- le désaccord sur le nœud vide — `incident_context: {}` est présent pour le validateur,
  absent pour la résolution ;
- l'absence de confrontation entre les tables de `resolution.py` et la table des fragments.

G2 et G4 appellent chacune un test, mais de deux natures qu'il ne faut pas confondre :

- **G4 échoue aujourd'hui.** La divergence sur le nœud vide est un défaut constaté, et son
  test restera rouge jusqu'à la mise en conformité de la résolution ;
- **G2 passe aujourd'hui.** Les deux tables s'accordent : aucun nœud réclamé par la
  résolution ne manque à la table des fragments. Son test est donc un **verrou**, pas un
  constat de défaut — il ne répare rien, il empêche une dérive future que rien n'aurait
  signalée.

Un verrou vert dès son écriture n'est pas un test inutile : c'est la seule forme que peut
prendre G2, puisque la règle interdit une divergence qui n'a pas encore eu lieu.

Écrire ces tests fait partie de l'adoption : une règle de gouvernance que rien ne vérifie
se dégrade comme n'importe quelle convention.

## Liens

- ADR-0009 — Composition Pipeline : la frontière d'entrée, et la génération de la source
  déclarée strictement en amont de la chaîne.
- ADR-0010 — Forme canonique : la portée d'un schéma, la nature d'un fragment, et la
  raison pour laquelle le contrat ne s'élargit pas par accident.
- ADR-0011 — Frontière atelier / contrat : ce qu'un pont a le droit de faire, et R3 que
  G6 refuse d'assouplir.
