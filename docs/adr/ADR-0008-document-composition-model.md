# ADR-0008 — Document Composition Model

## Statut

Accepté

## Date

2026-07-28

## Contexte

ADC Studio doit produire plusieurs familles de rapports à partir de composants
documentaires réutilisables.

Le projet possède déjà :

- une bibliothèque de composants ;
- des profils de rapports ;
- une identité graphique ;
- des modèles Word ;
- des rapports de référence ;
- des outils de génération.

Cependant, le modèle qui relie ces éléments n’est pas encore formalisé.

Sans modèle de composition explicite, les risques sont les suivants :

- logique métier mélangée au rendu Word ;
- ordre des composants codé en dur ;
- dépendance directe entre les données source et le format de sortie ;
- difficulté à produire plusieurs formats ;
- règles de validation dispersées ;
- impossibilité de tester la composition indépendamment du rendu.

## Décision

ADC Studio adopte un modèle documentaire intermédiaire composé de quatre
concepts principaux :

1. `Document`
2. `Component`
3. `Profile`
4. `Renderer`

Le moteur de composition construit un `Document` à partir d’un `Profile`, de
données d’entrée et d’une bibliothèque de `Component`.

Le `Renderer` reçoit ensuite ce document composé et le matérialise dans un
format cible.

Le présent ADR décrit **ce que sont** ces concepts. L’enchaînement des étapes à
l’exécution et les règles qui s’imposent à chacune font l’objet d’ADR-0009 —
Composition Pipeline.

## 1. Document

Un `Document` représente le résultat logique d’une composition.

Il est indépendant du format de sortie.

Il contient au minimum :

- un identifiant ;
- un type de document ;
- un titre ;
- des métadonnées ;
- une liste ordonnée d’instances de composants ;
- les informations de contexte nécessaires au rendu ;
- les diagnostics produits pendant la composition.

Le `Document` est la **seule vérité métier** de la chaîne. Ce qui n’y figure
pas n’existe pas pour le rendu.

### 1.1 Instances de composants

La liste de composants d’un document n’est pas une liste de définitions, mais
une liste d’**occurrences**. Chaque occurrence porte :

- l’identifiant catalogue du composant, qui détermine comment la rendre ;
- un identifiant d’occurrence, unique dans le document, qui la distingue de ses
  semblables et permet d’y faire référence ;
- une charge utile (`payload`), c’est-à-dire les données déjà extraites et
  normalisées, prêtes pour le rendu.

Un composant à cardinalité multiple produit autant d’occurrences que la source
en déclare. L’ordre de la liste est celui du document final.

### 1.2 Métadonnées et contexte de rendu

Les métadonnées portent deux natures d’information, qu’il ne faut pas
confondre :

- les **métadonnées éditoriales** du rapport — client, référence, version,
  date, confidentialité, langue ;
- le **contexte de rendu**, rangé sous une clé dédiée, qui rassemble les index
  techniques dont la présentation a besoin.

Le contexte de rendu est **dérivé exclusivement du Document** : il se construit
à partir des instances déjà composées, jamais par une relecture des données
source. Il ne contient aucune information métier nouvelle, seulement une vue
indexée de ce que l’IR contient déjà.

### 1.3 Relations entre composants

Les relations entre composants — une recommandation qui traite un constat, un
constat qui s’appuie sur une preuve, un risque couvert par une recommandation —
sont portées **par des identifiants**, dans le payload du composant qui
référence.

Le composant référencé ignore qui le cite : la relation est déclarée dans un
seul sens. Aucun libellé n’est dupliqué d’un composant vers un autre ; la
résolution des identifiants en texte lisible appartient au contexte de rendu.

### 1.4 Diagnostics

Un document composé peut être incomplet sans être invalide. Les écarts observés
pendant la composition — composant non pris en charge, référence sans cible
lisible — sont enregistrés comme diagnostics et accompagnent le document.

La génération n’en dépend pas : elle produit un fichier, et l’écart reste
visible.

Un document porte **deux séries de diagnostics**, qui ne répondent pas à la
même question et ne sont donc pas fondues :

| | Ce qu’ils disent | Origine |
|---|---|---|
| `diagnostics` | ce que la composition n’a pas su faire | le moteur |
| `source_diagnostics` | ce que le contenu du rapport a de fautif | la validation métier |

Un builder manquant et une référence inconnue produiraient sinon des écarts
indistinguables, alors que le premier se corrige dans le moteur et le second
dans la source. Les écarts aux contrats de composants, eux, n’apparaissent dans
ni l’une ni l’autre : ils empêchent la composition d’avoir lieu (ADR-0009, I9).

### 1.5 Exemple conceptuel

```yaml
document:
  id: ADC-SOC01-2026-SQL2014-001
  type: incident_report
  title: "Investigation — Blocage SQL Server lors de DBCC CHECKDB"
  metadata:
    client: Soc01
    reference: ADC-SOC01-2026-SQL2014-001
    version: "0.1-draft"
    date: "2026-07-28"
    confidentiality: Confidentiel
    language: fr-BE
    render_context:
      evidence_titles:
        evidence-001: "État et configuration de l’environnement SQL"
      finding_titles:
        finding-001: "Blocage observé pendant DBCC CHECKDB"
      recommendation_titles:
        recommendation-001: "Exécuter DBCC CHECKDB hors production"
  components:
    - component_id: C-001-cover
      instance_id: cover
      payload:
        title: "Investigation — Blocage SQL Server lors de DBCC CHECKDB"
        client: Soc01
        confidentiality: Confidentiel
    - component_id: C-002-identity-page
      instance_id: identity
      payload:
        identification:
          reference: ADC-SOC01-2026-SQL2014-001
          language: fr-BE
        revisions: []
    - component_id: C-004-finding
      instance_id: finding-001
      payload:
        title: "Blocage observé pendant DBCC CHECKDB"
        severity: high
        evidence_ids:
          - evidence-001
  diagnostics:
    - "builder manquant: narrative :: incident-context"
```

Les valeurs d’énumération y figurent sous leur forme canonique — `high`, et non
son libellé de lecture.

## 2. Component

Un `Component` est une unité documentaire réutilisable, enregistrée dans la
bibliothèque officielle sous un identifiant stable.

Il possède :

- une fiche lisible par un humain : objectif, structure attendue, règles
  rédactionnelles, critères de validation ;
- une description lisible par une machine : identifiant, version, statut,
  intégrations supportées ;
- éventuellement un exemple représentatif et des règles de validation.

Le composant est une **définition**, pas une donnée. Il ne contient le contenu
d’aucun rapport : il décrit ce qu’une occurrence doit porter et comment elle se
comporte.

Un composant peut apparaître zéro, une ou plusieurs fois dans un document,
selon la cardinalité que le profil lui reconnaît.

Le catalogue décrit une **intention fonctionnelle**. Il ne se substitue pas au
contrat machine réel : un champ décrit au catalogue mais absent des données
source ne donne lieu à aucune composition.

## 3. Profile

Un `Profile` définit une famille de rapports : quels composants la constituent,
lesquels sont obligatoires, lesquels sont facultatifs, et dans quel ordre ils
se succèdent.

Il répond à la question « de quoi ce type de rapport est-il fait ? », là où le
composant répond à « qu’est-ce que cet élément ? ».

Le profil est le point de variation entre familles de rapports : deux profils
partageant la même bibliothèque de composants produisent des documents de
structures différentes sans qu’aucun composant ne soit modifié.

La **résolution** est l’opération qui transforme un profil et des données en une
liste ordonnée d’occurrences à composer. Elle est déterministe : les mêmes
entrées produisent toujours la même liste, dans le même ordre.

## 4. Renderer

Un `Renderer` matérialise un document composé dans un format cible.

Il est **maître de la mise en page** et de rien d’autre : styles, hiérarchie de
titres, tableaux, sauts de page, libellés destinés au lecteur. Il ne construit
pas le document au sens logique, il le met en forme.

Plusieurs renderers coexistent pour un même document. Chacun consomme le même
`Document` et le même contexte de rendu ; aucun ne dispose d’une information que
les autres n’auraient pas.

Un composant présent dans le document mais que le renderer ne sait pas rendre
est ignoré proprement : ni exception, ni contenu approximatif. L’écart reste
porté par les diagnostics du document.

Les règles d’exécution qui s’imposent à tout renderer — ne pas lire la source,
ne pas résoudre de référence, ne pas réordonner les composants — sont énoncées
et vérifiées par ADR-0009.

## État de l’implémentation

Le modèle est implémenté et couvre le profil incident, avec deux écarts connus,
qui n’en remettent pas en cause la structure :

- la résolution est aujourd’hui portée par le code, source unique de l’ordre,
  et non pilotée par le fichier de profil, qui reste déclaratif ;
- les descriptions machine des composants sont encore partielles pour certains
  d’entre eux.

Ces écarts relèvent de l’avancement, non d’une divergence de modèle.

## Hors périmètre

Cet ADR ne traite pas :

- la génération des données source, notamment par un modèle de langage : elle
  se situe strictement en amont de la composition ;
- le schéma de données propre à chaque famille de rapports ;
- les choix graphiques d’un renderer donné — typographie, couleurs, gabarits ;
- le contrat détaillé de chaque composant du catalogue, qui appartient à sa
  fiche ;
- les invariants d’exécution de la chaîne, qui appartiennent à ADR-0009.

## Liens

- ADR-0003 — Document Components
- ADR-0006 — Document Component Architecture
- ADR-0007 — Machine Readable Document Components
- **ADR-0009 — Composition Pipeline** : enchaînement des étapes et invariants
  d’exécution du présent modèle.
