# Matrice de décision — nature contractuelle des blocs narratifs

Cette fiche qualifie **chaque bloc indépendamment**. Elle ne rouvre pas la comparaison
globale Modèle A / Modèle B : l'étude précédente a montré qu'aucune mesure ne soutient
l'axiome selon lequel les quatre blocs doivent partager un même statut.

Elle formule une **recommandation motivée par bloc**. La décision est entérinée par l'ADR
proposée en fin de document.

Les deux écarts indépendants — `supporting_finding_ids` validé par la mauvaise couche, et
le traitement hétérogène du vide par les renderers — sont **hors périmètre** : ils sont
traités avant toute contractualisation et n'influencent aucune recommandation ci-dessous.

## Synthèse

| Bloc | Type porté | Identité / références | Comportement propre | Gain d'un contrat | Recommandation |
|---|---|---|---|---|---|
| `incident_context` | objet, 4 champs | aucune | non | ferme un vocabulaire, attrape un champ inconnu | **composant catalogue** |
| `investigations` | collection d'objets | `id` = identité d'occurrence | oui — occurrences | supprime une perte de contenu rédigé | **composant catalogue** |
| `probable_cause` | objet, 3 champs | références sortantes | non | garantit une forme de référence exploitable | **composant catalogue** |
| `conclusion` | chaîne | aucune | non | empêche la disparition d'une section obligatoire | **à décider en dernier** — voir § dédié |

## Ce qu'un contrat achète ici, mesuré

Avant les blocs, le constat commun. Depuis G4, un nœud **présent mais vide** est présent et
silencieux — c'est voulu : la section reste à rédiger. Mais un nœud **présent et faux** est
tout aussi silencieux, et rien ne les distingue.

> **Un contrat est aujourd'hui la seule chose capable de séparer « à rédiger » de « mal
> écrit ».** C'est la valeur générale ; ce qui suit mesure sa valeur particulière, bloc par bloc.

Quatre mesures, prises sur la source de référence :

| Contenu fautif injecté | Ce que la chaîne en dit | Ce que le lecteur obtient |
|---|---|---|
| `investigations: [{title, description}]` — sans `id` | **rien** | l'investigation disparaît du rapport |
| `conclusion: {"texte": "…"}` — objet au lieu de chaîne | **rien** | la conclusion, obligatoire, disparaît du rapport |
| `incident_context: {"descriptio": "…"}` — champ mal orthographié | **rien** | section vide |
| `incident_context: {"status": "TOTALEMENT_INVENTE"}` | **rien** | « Statut : TOTALEMENT_INVENTE » en clair dans le DOCX |

Aucun de ces quatre cas ne produit de diagnostic — ni de contrat, ni métier, ni de
composition, ni de cardinalité.

---

## `incident_context`

| | |
|---|---|
| **Forme réelle** | objet : `description` (texte ou paragraphes), `trigger`, `scope`, `status` |
| **Consommateur** | `_build_incident_context` → `_render_incident_context`, bloc unique 1..1 |
| **Références** | aucune |
| **Résolution** | présent ssi la clé existe (G4) ; le profil exige 1..1 |
| **Rendu** | titre posé **sans garde** : un nœud vide produit un titre orphelin |
| **Valeur d'un contrat** | ferme le vocabulaire de `status` ; rejette un champ inconnu (`descriptio`) ; distingue vide et faux |
| **Coût « composant catalogue »** | répertoire + schéma + exemple ; inscription d'office dans la famille P-003 ; cycle de vie complet |
| **Coût « fragment contractuel »** | emplacement de schéma à créer, `adc_contracts` à ouvrir, ADR-0010 à réviser, cycle de vie à inventer |

**Recommandation : composant catalogue.**

Trois motifs mesurés. `C-003-executive-summary` est un précédent trait pour trait — chapitre
unique, non réutilisable d'un document à l'autre, objet plat, `additionalProperties: false`.
ADR-0003 et `component-library.md` nomment déjà « Context » parmi les composants du noyau :
le statut de fragment exigerait de réviser deux documents doctrinaux pour ce seul bloc. Enfin
le coût du Modèle B est une **infrastructure**, pas une écriture : la payer pour un bloc dont
le catalogue sait déjà accueillir la forme n'achète rien.

Sur le vocabulaire, la mesure est nette : `_INCIDENT_STATUS_LABELS` ne contient qu'une seule
entrée, `investigated`, construite sur l'unique valeur de la source de référence. Toute autre
valeur traverse et s'imprime en anglais. `C-004` et `C-005` ferment leur vocabulaire par
contrat ; ce bloc ne le ferme nulle part.

---

## `investigations`

| | |
|---|---|
| **Forme réelle** | collection d'objets : `id`, `title`, `description`, `result` |
| **Consommateur** | `_build_investigation` → `_render_investigation`, bloc répétable 0..∞ |
| **Références** | aucune sortante ; `id` **est** l'identifiant d'occurrence dans l'IR |
| **Résolution** | occurrences = entrées portant un `id` non vide — une entrée sans `id` est écartée sans diagnostic |
| **Rendu** | une section autonome par occurrence, renderer sans état (I7) |
| **Valeur d'un contrat** | `id` requis : supprime la seule perte de **contenu rédigé** mesurée dans la chaîne |
| **Coût « composant catalogue »** | le plus élevé des quatre : la clé de `_MULTIPLE_OCCURRENCE_SOURCES` est le `component_id`, donc `resolution.py` change aussi |
| **Coût « fragment contractuel »** | identique aux autres blocs |

**Recommandation : composant catalogue.**

Ce bloc est structurellement identique à `C-004-finding` et `C-010-evidence` : collection
d'objets identifiés, occurrences énumérées depuis la source, identité portée par `id`. Lui
donner un statut différent créerait deux traitements pour une même forme, sans qu'aucune
mesure ne distingue les deux cas.

C'est aussi le bloc où le contrat achète le plus : un rédacteur qui oublie un `id` perd son
texte, et rien ne le lui dit — ni à lui, ni au générateur.

---

## `probable_cause`

| | |
|---|---|
| **Forme réelle** | objet : `statement`, `confidence`, `supporting_finding_ids` |
| **Consommateur** | `_build_probable_cause` → `_render_probable_cause`, bloc unique 0..1 |
| **Références** | `supporting_finding_ids` → `findings` |
| **Résolution** | présent ssi la clé existe ; profil 0..1 |
| **Rendu** | titre sans garde ; références affichées en libellés, jamais en identifiants (I4) |
| **Valeur d'un contrat** | ferme `confidence` ; garantit que `supporting_finding_ids` est une liste de chaînes — une chaîne y est aujourd'hui **silencieusement ignorée**, donc des références rédigées disparaissent sans trace |
| **Coût « composant catalogue »** | répertoire + schéma + exemple ; aucun changement de résolution |
| **Coût « fragment contractuel »** | identique aux autres blocs |

**Recommandation : composant catalogue.**

C'est le seul bloc narratif porteur de références sortantes. `C-004-finding` ferme la forme
de ses `evidence_ids` par contrat ; ce bloc doit offrir la même garantie, sans quoi la
liaison entre cause probable et constats repose sur une forme que rien ne tient.

À ne pas confondre avec l'écart hors périmètre : le contrat garantit la **forme
exploitable** de la référence ; la **résolubilité** reste au validateur métier (G1), et
c'est précisément ce que corrige le correctif indépendant.

---

## `conclusion`

| | |
|---|---|
| **Forme réelle** | chaîne |
| **Consommateur** | `_build_conclusion` → `_render_conclusion`, bloc unique 1..1 **obligatoire** |
| **Références** | aucune |
| **Résolution** | présent ssi la clé existe ; profil 1..1 |
| **Rendu** | **sort sans rien écrire** si le texte est vide — seul renderer narratif à se garder du titre orphelin |
| **Valeur d'un contrat** | pauvre en expression (`type: string`), maximale en conséquence : empêche qu'une section obligatoire disparaisse en silence |
| **Coût « composant catalogue »** | une entrée de catalogue dont la documentation d'accompagnement n'aurait presque rien à dire |
| **Coût « fragment contractuel »** | **toute l'infrastructure du Modèle B, payée pour un seul champ** |

**Recommandation : décider ce bloc en dernier — sa décision n'est pas locale.**

C'est le seul des quatre dont le statut détermine l'existence même de la troisième nature.
Si les trois autres rejoignent le catalogue, retenir « fragment narratif contractuel » pour
`conclusion` revient à créer une nature nouvelle, un emplacement de schéma, une ouverture de
`adc_contracts`, une révision d'ADR-0010 et un cycle de vie à inventer — **pour un
`{"type": "string"}`**.

Ce n'est pas un argument contre le statut de fragment : c'est un coût qui doit être amorti
par autre chose que ce bloc. Deux raisons pourraient l'amortir, et aucune n'est mesurable
aujourd'hui : d'autres familles de rapports apportant leurs propres blocs narratifs, ou une
volonté explicite de ne pas laisser le catalogue absorber tout ce qui porte un contrat.

Mesure à garder en vue pour trancher : c'est ici que la chaîne perd le plus — une conclusion
non textuelle fait **disparaître du rapport une section que le profil déclare obligatoire**,
sans un seul diagnostic. Quel que soit le statut retenu, ce trou se ferme avec un contrat
d'une ligne.

---

## ADR proposée — contenu précis

**ADR-0013 — Nature contractuelle des blocs narratifs.** Statut : à décider. Elle entérine,
elle n'instruit pas : l'instruction est ici et dans l'étude précédente.

- **D1 — L'uniformité n'est pas requise.** Chaque bloc reçoit le statut que sa forme et son
  comportement justifient. Aucune règle n'oblige les quatre à partager une nature.
- **D2 — Statut de chaque bloc.** `incident_context`, `investigations`, `probable_cause` :
  composants du catalogue. `conclusion` : statut arrêté par cette ADR, à la lumière de son
  effet sur l'existence de la troisième nature.
- **D3 — Emplacement du contrat.** Pour un composant catalogue :
  `components/<id>/schema.json`, mécanisme existant, aucune ouverture d'`adc_contracts`. Si
  une troisième nature est retenue, l'ADR déclare son emplacement et l'ouverture requise.
- **D4 — Propriétaire de la cardinalité.** Inchangé : le profil (ADR-0012, G1). La
  contractualisation ne déplace aucune cardinalité.
- **D5 — Règle de résolution.** Inchangée : présence structurelle (G4). Un contrat ne
  décide pas de la présence, il décrit la forme du nœud présent.
- **D6 — Cycle de vie applicable.** Un composant catalogue hérite du cycle existant et de
  ses obligations de promotion. Une troisième nature exigerait un cycle propre, que l'ADR
  devrait écrire — sans quoi elle créerait un artefact versionné sans règle de version.
- **D7 — Extinction de la dette `ROOT_FRAGMENT`.** L'ADR énonce l'ordre de résorption et
  l'état attendu à la fin : plus aucun nœud consommé sans contrat (ADR-0012, G3).
- **Conséquence à écrire** : le couplage bibliothèque ↔ famille de rapports
  (`test_every_component_of_the_library_is_located`) devient assumé, ou l'ADR le desserre.

## Ordre d'implémentation

Les deux correctifs indépendants d'abord — ils ne dépendent d'aucune décision de statut :

1. `fix(validation)` — la résolubilité de `supporting_finding_ids` rejoint le validateur métier ;
2. `fix(rendering)` — comportement homogène des renderers narratifs sur un bloc vide.

Puis un bloc à la fois, chacun mené jusqu'au bout — contrat, inventaire, frontière, tests,
composition réelle — avant d'ouvrir le suivant :

3. **`incident_context`** — établit le motif. Aucune machinerie nouvelle, `C-003` à copier,
   aucun changement de résolution, et son défaut est visible dans le DOCX ;
4. **`investigations`** — le gain le plus élevé, mais touche `resolution.py` : il bénéficie
   d'un motif déjà établi ;
5. **`probable_cause`** — après le correctif de validation, pour que forme et résolubilité
   soient traitées dans le bon ordre ;
6. **`conclusion`** — en dernier, parce que sa décision engage l'existence de la troisième
   nature et se prend mieux quand les trois autres sont faites.

## Liens

- `narrative-contractualisation.md` — l'étude comparative, ses mesures et ses questions ouvertes.
- ADR-0012 — G1 (propriété des règles), G3 (aucun nœud consommé hors contrat), G4 (vide ≠ absent).
