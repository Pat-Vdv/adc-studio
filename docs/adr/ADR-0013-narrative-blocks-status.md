# ADR-0013 — Statut contractuel des blocs narratifs

## Statut

Accepté

## Date

2026-07-29

## Contexte

ADR-0012 (G3) pose qu'aucun nœud consommé ne reste sans contrat, et laisse
explicitement ouverte la **forme** que prend ce contrat. Deux études ont instruit la
question sans la trancher : la comparaison des deux modèles, puis la qualification bloc par
bloc.

Deux écarts pouvaient encore brouiller l'interprétation de toute décision prise ici — une
référence validée par la mauvaise couche, et deux conventions opposées de rendu sur un bloc
vide. Ils ont été corrigés d'abord, **avant** cette ADR, de façon qu'aucun changement
ultérieur ne puisse être attribué à tort à la contractualisation. Les causes sont isolées :
ce qui bougera désormais viendra du contrat, et de lui seul.

### État de référence, mesuré avant toute contractualisation

Quatre contenus fautifs traversent aujourd'hui la chaîne entière sans un seul diagnostic —
ni de contrat, ni métier, ni de composition, ni de cardinalité :

| Contenu injecté | Effet observé |
|---|---|
| une investigation sans `id` | l'investigation disparaît du rapport |
| `conclusion` non textuelle | la conclusion, obligatoire, disparaît du rapport |
| un champ mal orthographié dans `incident_context` | la section est vide |
| `status` hors vocabulaire | la valeur s'imprime en anglais dans le DOCX client |

Ce tableau est le point de comparaison de tout ce qui suit.

## Décision

> **Le statut contractuel d'un bloc est déterminé par le comportement qu'il doit porter,
> jamais par sa position dans le document.**

Cette phrase gouverne toute l'ADR. Elle écarte deux raccourcis symétriques, également
tentants et également faux : « c'est un chapitre, donc ce n'est pas un composant », et
« c'est dans le corps du rapport, donc c'est un bloc narratif ». Ni la place dans le
sommaire, ni le nom du nœud, ni son appartenance à une famille de rapports ne décident de
son statut. Seul le décide ce que le bloc doit **garantir** : une identité, des références,
un vocabulaire fermé, une structure.

Elle explique aussi l'existant : `C-003-executive-summary` est un composant parce qu'il
porte une structure à garantir, non parce qu'il occupe telle page.

### D1 — L'uniformité n'est pas requise

Rien n'oblige les blocs narratifs à partager une nature. Aucune mesure ne soutient l'axiome
selon lequel ils formeraient une famille au sens contractuel : leurs formes, leurs
comportements et le gain qu'un contrat leur apporte diffèrent nettement.

### D2 — Chaque bloc narratif possède un statut propre

**Le statut est décidé individuellement, selon le comportement contractuel du bloc, et non
par appartenance à une famille.** Cette règle prime sur les statuts qui suivent : ceux-ci
sont son application à quatre cas, non une liste close.

**`incident_context` — composant du catalogue.**
Il doit garantir une **structure à champs connus** : un champ mal orthographié était
auparavant ignoré en silence et produisait une section vide. `C-003-executive-summary` porte
déjà exactement cette forme.

Le vocabulaire de `status` n'est en revanche **pas** fermé par ce contrat. Aucune règle de
domaine ne l'atteste, et la table de traduction du renderer relève de la présentation, qui
n'atteste rien (ADR-0010, origine d'une contrainte). Le fermer inventerait un vocabulaire —
même asymétrie assumée que pour le `level` d'un risque — et demandera que le domaine énonce
d'abord la liste des statuts admis.

**`investigations` — composant du catalogue.**
Il doit garantir une **identité** : `id` est l'identifiant d'occurrence dans l'IR, et une
entrée qui en est dépourvue est écartée sans diagnostic — la seule perte de contenu rédigé
mesurée dans la chaîne. Cette garantie est celle que `C-004-finding` et `C-010-evidence`
portent déjà, sur une forme identique.

**`probable_cause` — composant du catalogue.**
Il doit garantir la **forme exploitable de ses références** et un vocabulaire fermé
(`confidence`). Une liste de références écrite comme une chaîne est aujourd'hui ignorée en
silence. La *résolubilité* de ces références reste métier (ADR-0012, G1) : le contrat ne
garantit que la forme.

**`conclusion` — décision différée.**
Ce bloc porte une chaîne, sans identité, sans référence, sans vocabulaire. Le comportement
qu'il doit garantir tient en une ligne : être du texte.

*Motif du report* — le coût d'introduction d'une troisième nature n'est pas amorti. Créer
un « fragment narratif contractuel » ne coûte pas un contrat : il coûte un emplacement, une
ouverture d'`adc_contracts`, une doctrine, un cycle de vie, des conventions et des tests.
Payer cela pour un unique `{"type": "string"}` serait créer une catégorie avant d'avoir un
second cas qui la justifie.

Ce report est **assumé et daté**, non un oubli. Il sera levé par l'un ou l'autre de ces
faits : un second bloc appelant la même nature — d'une autre famille de rapports, ou d'un
nouveau profil — ou la démonstration qu'un statut de composant convient ici aussi. Tant
qu'aucun des deux ne se produit, `conclusion` reste un `ROOT_FRAGMENT`, et cette dette reste
visible au sens de G3.

La retenue est la même que celle qui a produit ADR-0011 plutôt qu'un élargissement
d'ADR-0010 : on n'élargit pas une catégorie pour un cas unique.

### D3 — L'emplacement d'un contrat découle de son statut, jamais de son nom

Un contrat vit là où son statut le place :

| Statut | Emplacement |
|---|---|
| composant du catalogue | `components/<id>/schema.json` — mécanisme existant, aucune ouverture d'`adc_contracts` |
| fragment narratif contractuel | emplacement à déclarer **par l'ADR qui créera cette nature**, hors `components/` |

Placer sous `components/` le contrat d'un fragment qui n'est pas un composant est interdit,
quelle qu'en soit la commodité. Le répertoire est l'expression d'un statut : un schéma qui y
figure sans identité de catalogue rendrait l'inventaire faux et ferait mentir le seul
mécanisme qui décrit aujourd'hui la couverture contractuelle.

### D4 — La cardinalité ne change pas de propriétaire

Elle reste au profil (ADR-0012, G1). La contractualisation n'en déplace aucune : un contrat
décrit la forme d'un nœud, jamais le nombre d'occurrences admises.

### D5 — La résolution ne change pas de règle

La présence reste **structurelle** (ADR-0012, G4). Un contrat ne décide pas qu'un nœud est
présent : il décrit la forme du nœud présent. Un nœud vide reste présent et reste une
section à rédiger.

### D6 — Le cycle de vie suit le statut

Un composant du catalogue hérite du cycle existant et de ses obligations de promotion
(`metadata.yaml`, README, `COMPONENT_CATALOG.md`, `PROJECT_STATUS.md`, `CHANGELOG.md`).

Une troisième nature, si elle est créée un jour, devra recevoir un cycle propre dans l'ADR
qui l'introduit : un artefact versionné sans règle de version n'est pas un statut, c'est un
angle mort.

Les identifiants des nouveaux composants sont attribués à l'implémentation, dans l'ordre de
D7, à partir du premier libre — `C-011` à ce jour.

### D7 — Extinction de la dette `ROOT_FRAGMENT`

Un bloc à la fois, mené jusqu'au bout — contrat, inventaire, frontière, tests, composition
réelle — avant d'ouvrir le suivant. L'ordre :

1. `incident_context` — établit le motif : aucune machinerie nouvelle, `C-003` à copier,
   aucun changement de résolution ;
2. `investigations` — le gain le plus élevé, mais il touche `resolution.py`, dont la clé est
   l'identifiant de composant : il bénéficie d'un motif déjà établi ;
3. `probable_cause` — après le correctif de validation déjà livré, pour que forme et
   résolubilité soient traitées dans le bon ordre.

État attendu à la fin : `conclusion` est le seul `ROOT_FRAGMENT` restant, et son statut est
la seule question narrative ouverte.

Tant que `conclusion` est différée, le marqueur `narrative` survit dans le profil et dans
les tables de dispatch — pour ce bloc seul.

## Portée

Cette ADR statue sur quatre nœuds nommés. Elle ne crée aucune nature nouvelle, ne modifie
aucun invariant d'ADR-0009, et ne rouvre aucune règle d'ADR-0012 : elle les applique.

Elle ne dit pas quelle forme précise prend chaque schéma — cela relève de l'implémentation,
bloc par bloc, sous le contrôle des tests d'inventaire existants.

## Conséquences

Deviennent interdits, sans révision de cette ADR :

- décider du statut d'un bloc par sa position dans le document, son nom, ou son
  appartenance à une famille de rapports ;
- placer sous `components/` le contrat d'un fragment qui n'est pas un composant ;
- faire décider par un contrat la présence d'un nœud ou sa cardinalité ;
- créer la troisième nature sans le second cas qui l'amortit et sans le cycle de vie qui la
  gouverne ;
- traiter le report de `conclusion` comme un statut définitif, ou comme un oubli à combler
  en silence.

Sont acceptés comme conséquences directes :

- les trois nouveaux composants entrent d'office dans la table de la famille « rapport
  d'incident », le test d'inventaire l'exigeant. Ce couplage entre bibliothèque et famille
  est **assumé ici** ; le desserrer relèverait d'une autre ADR, et n'est pas requis par la
  présente décision.

Restent ouverts :

- le statut de `conclusion`, et avec lui l'existence même de la troisième nature ;
- le sort d'`annexes`, nœud que personne ne consomme, hors périmètre depuis ADR-0012.

## Vérification

Ce que cette ADR décide sera observable, et l'est déjà en partie :

- **D5** est tenu par les tests de gouvernance narrative — un nœud présent mais vide est
  résolu comme présent, un nœud absent reste absent ;
- **D2 et D7** seront attestés bloc par bloc : chaque contractualisation doit faire passer
  la nature du fragment de `ROOT_FRAGMENT` à `CATALOG_COMPONENT`, et rendre refusé à la
  frontière un contenu qui traversait auparavant. Les quatre lignes de l'état de référence
  ci-dessus sont les cas à confronter ;
- **D3** est vérifiable par construction : un schéma hors `components/` ne serait pas
  chargeable aujourd'hui, ce qui rend l'infraction impossible à commettre par inadvertance
  tant que la troisième nature n'existe pas.

## Liens

- ADR-0012 — Gouvernance du contrat narratif : G1 (propriété des règles), G3 (aucun nœud
  consommé hors contrat), G4 (vide ≠ absent).
- ADR-0010 — Forme canonique : la nature d'un fragment, qu'une troisième catégorie
  étendrait.
- ADR-0011 — Frontière atelier / contrat : le précédent de retenue invoqué par D2.
- `docs/studies/narrative-contractualisation.md` et
  `docs/studies/narrative-blocks-decision-matrix.md` — les mesures qui fondent D2.
