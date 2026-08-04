# Promotion d'un bloc narratif vers un composant du catalogue

Ce document décrit un **motif reproductible**, éprouvé trois fois sans divergence
sur `incident_context` (C-011), `investigations` (C-012) et `probable_cause`
(C-013). Il ne décide rien : la décision de statut appartient à ADR-0013.

## Pourquoi ce motif existe

Un bloc narratif est consommé par un builder sans être confronté à aucun contrat.
Sa forme n'est donc opposable nulle part : un contenu fautif traverse la chaîne
entière — frontière, validation, composition, rendu — sans un seul diagnostic, et
le silence va jusqu'au livrable client.

Promouvoir un bloc ne le durcit pas : cela **déplace la propriété de sa forme**
vers un contrat, là où ADR-0012 (G1) la situe.

## Les sept pièces

| Pièce | Où | Remarque |
|---|---|---|
| contrat | `components/<id>/schema.json` | décrit la forme du fragment, jamais sa présence |
| exemple | `components/<id>/example.json` | doit démontrer le contrat entier |
| métadonnées | `components/<id>/metadata.yaml` | source de vérité du statut |
| entrée documentaire | `components/<id>/README.md` et `COMPONENT_CATALOG.md` | |
| inventaire | table des fragments (`adc_contracts`) | nature `ROOT_FRAGMENT` → `CATALOG_COMPONENT` |
| profil | `profiles/p-003-incident-report.yaml` | `type:` devient l'identifiant du composant |
| dispatch | `compose.py` et `render_docx.py` | la clé change, les builders et renderers non |

**Résolution** — elle ne change que pour un bloc **répétable** : sa table est
indexée par identifiant de composant, alors que celle des blocs uniques l'est par
identifiant d'occurrence, que la promotion ne modifie pas. C'est la seule
variation observée entre les trois promotions.

## Ce que la promotion ne change pas

Ni le builder, ni le renderer, ni la place du bloc dans le document, ni sa
cardinalité, ni la règle de présence — un nœud présent mais vide reste présent et
reste une section à rédiger (ADR-0012, G4). L'effet d'une promotion doit être
mesurable et **circonscrit à la forme** : c'est ce qui permet d'attribuer sans
ambiguïté tout changement de comportement au contrat.

## L'origine d'une contrainte

Une contrainte n'entre dans un schéma que si son origine l'autorise (ADR-0010).
Les trois promotions l'ont illustré :

- **structure** — `additionalProperties: false` a fermé les trois blocs. C'est ce
  qui attrape un champ mal orthographié, auparavant ignoré en silence ;
- **prérequis de consommation** — `id` est requis sur C-012 : le moteur instancie
  l'occurrence par lui, et une entrée qui n'en porte pas disparaît du document ;
- **qualité de restitution** — `title` n'est *pas* requis sur C-012 : son absence
  dégrade l'en-tête sans empêcher la consommation ;
- **présentation** — aucun vocabulaire n'a été fermé. Que le renderer sache
  traduire `investigated` ou `unknown` n'atteste rien : ces tables sont de la
  présentation, et fermer `status`, `result` ou `confidence` inventerait un
  vocabulaire que le domaine n'a jamais énoncé.

## Deux validations, deux questions

C-013 en donne l'illustration la plus nette. Le contrat garantit **la forme et
jamais la cible** :

```
Contrat  ── supporting_finding_ids est-il une liste de chaînes non vides ?
Métier   ── « finding-404 » désigne-t-il un constat qui existe ?
```

Aucune des deux ne peut répondre à la question de l'autre : un schéma local ne
voit qu'un fragment à la fois, et ne peut donc juger ni une référence, ni une
unicité, ni une cardinalité. C'est la raison d'être des deux validations
successives, et le partage que G1 formalise.

## Le verrou

`tests/test_catalog_component_status.py` exprime ce que le statut de composant
**oblige** : contrat et exemple, inventaire, builder, résolution déclarée,
renderer, documentation minimale. Il a signalé deux entrées de catalogue
manquantes avant qu'on ne les remarque.

Ce n'est pas un test parmi d'autres : c'est un **invariant d'architecture**. S'il
échoue, le dépôt est incomplet même si tout le reste est vert.

## État

| Bloc | Statut |
|---|---|
| `incident_context` | contractualisé — C-011 |
| `investigations` | contractualisé — C-012 |
| `probable_cause` | contractualisé — C-013 |
| `conclusion` | **décision différée** (ADR-0013, D2) |

`conclusion` est le seul `ROOT_FRAGMENT` restant. Ce n'est pas un oubli : son
statut engage l'existence d'une troisième nature contractuelle, dont le coût —
emplacement, ouverture d'`adc_contracts`, doctrine, cycle de vie, conventions,
tests — n'est pas amorti par un unique champ textuel. Le report est levé par les
faits, non par la symétrie : un second cas appelant cette nature, ou la
démonstration qu'un statut de composant convient ici aussi.
