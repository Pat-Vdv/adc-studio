# Étude — Contractualisation des blocs narratifs

**Aucune décision n'est prise dans cette étude.**

Elle ne recommande ni le Modèle A, ni le Modèle B. Elle mesure ce que chacun coûte et ce
que chacun change, bloc par bloc, selon une grille identique. La décision se prend ailleurs,
après lecture, et pourra différer d'un bloc à l'autre.

## Méthode

Chaque affirmation est marquée :

- **(mesuré)** — constaté en exécutant le code ou en comptant dans le dépôt ;
- **(déduit)** — conséquence raisonnée d'une règle écrite, non exécutée.

Aucune affirmation n'est marquée autrement. Ce qui n'est ni mesurable ni déductible est
rangé en fin d'étude, parmi les questions ouvertes, plutôt que tranché en passant.

Périmètre : les quatre blocs déclarés `ROOT_FRAGMENT` dans la table des fragments —
`incident_context`, `investigations`, `probable_cause`, `conclusion` — face aux deux modèles,
sur douze critères. Rien d'autre.

## Les deux modèles

Les définitions ci-dessous sont opérationnelles : elles décrivent ce qu'il faudrait
réellement faire dans ce dépôt, pas une idée de modèle.

### Modèle A — composant du catalogue

Le bloc reçoit un identifiant `C-0xx`, un répertoire sous `components/`, et la nature
`CATALOG_COMPONENT` dans la table des fragments. Il entre dans le catalogue, son cycle de
vie et sa documentation. Le profil le désigne par son identifiant au lieu du marqueur
`narrative`.

### Modèle B — fragment narratif contractuel

Le bloc garde son statut de fragment racine mais cesse d'être hors contrat : une **troisième
nature** est déclarée à côté de `CATALOG_COMPONENT` et `ROOT_FRAGMENT`, porteuse d'un schéma
sans identité de bibliothèque. Le profil continue de le désigner par `narrative`.

> Contrainte technique du Modèle B, souvent invisible à ce stade **(mesuré)** :
> `adc_contracts.schema_path()` ne sait lire un schéma qu'en `components/<id>/schema.json`.
> Un fragment contractuel hors catalogue n'a donc **aucun emplacement de contrat aujourd'hui**.
> Le Modèle B exige de décider où vit ce schéma et d'ouvrir `adc_contracts` à cet
> emplacement. Ce coût lui est propre : le Modèle A réutilise un chemin existant.

## État des lieux

Tel que le dépôt le déclare aujourd'hui **(mesuré)** :

| | `incident_context` | `investigations` | `probable_cause` | `conclusion` |
|---|---|---|---|---|
| Nature (table des fragments) | `ROOT_FRAGMENT` | `ROOT_FRAGMENT` | `ROOT_FRAGMENT` | `ROOT_FRAGMENT` |
| Mode de lecture | `NODE` | `OCCURRENCE` | `NODE` | `NODE` |
| Entrée de profil | `narrative :: incident-context` | `narrative-investigation` | `narrative :: probable-cause` | `narrative :: conclusion` |
| Cardinalité | 1..1 | 0..∞ | 0..1 | 1..1 |
| Exigé par le validateur | oui | non | non | oui |
| Forme source | objet | liste d'objets | objet | chaîne |
| Champs lus par le builder | `description`, `trigger`, `scope`, `status` | `id`, `title`, `description`, `result` | `statement`, `confidence`, `supporting_finding_ids` | *(le nœud entier)* |
| Références sortantes | — | — | `supporting_finding_ids` | — |
| Vocabulaire fermé attendu | `status` | — | `confidence` | — |

Aucun de ces quatre nœuds n'est confronté à un schéma. Un contenu arbitraire y traverse
contrat, validation, composition et rendu sans un seul diagnostic **(mesuré, ADR-0012)**.

## La grille

Les douze critères, définis une fois, appliqués identiquement aux quatre blocs.

| Critère | Ce qu'il mesure |
|---|---|
| **schéma** | où vit le contrat de forme, et sous quel mécanisme il est chargé |
| **cardinalité** | qui déclare combien d'occurrences sont admises |
| **builder** | ce que devient la clé de dispatch `(component_id, instance_id)` |
| **catalogue** | présence dans `COMPONENT_CATALOG.md` et dans l'inventaire `component_ids()` |
| **cycle de vie** | soumission au cycle `Planned → … → Archived` et à ses obligations de promotion |
| **ownership** | qui possède la forme du bloc, au sens de G1 |
| **validation locale** | ce que le schéma pourrait rejeter à la frontière d'entrée |
| **validation globale** | ce qui reste au validateur métier, invariant par construction |
| **coût de migration** | fichiers et lignes à modifier, mesurés |
| **impact ADR** | ADR à réviser ou à compléter |
| **impact résolution** | changements dans `adc_profile/resolution.py` |
| **impact renderers** | changements dans `render_docx.py` |

Deux lignes sont **identiques dans les deux modèles pour les quatre blocs**, et ne sont donc
pas répétées ensuite :

- **validation globale** — la présence des nœuds racine, l'unicité des identifiants et la
  résolubilité des références restent au validateur métier (ADR-0012, G1). Aucun des deux
  modèles n'y touche **(déduit)** ;
- **impact renderers** — les fonctions de rendu ne changent dans aucun modèle. Seule la
  **clé** de leur table de dispatch change sous le Modèle A ; le corps des renderers, lui,
  ne lit que le payload **(mesuré : les quatre renderers n'accèdent qu'à `instance.payload`
  et au contexte)**.

---

## `incident_context`

| Critère | Modèle A | Modèle B |
|---|---|---|
| schéma | `components/C-0xx-incident-context/schema.json`, chargé par le mécanisme existant | emplacement à créer ; `adc_contracts.schema_path()` à ouvrir |
| cardinalité | inchangée (1..1, portée par le profil) | inchangée (1..1, portée par le profil) |
| builder | clé `("C-0xx-incident-context", "incident-context")` | clé `("narrative", "incident-context")` inchangée |
| catalogue | entre dans `COMPONENT_CATALOG.md` et dans `component_ids()` | absent du catalogue |
| cycle de vie | soumis au cycle complet ; toute promotion impose 5 mises à jour documentaires | aucun cycle défini — à inventer ou à assumer absent |
| ownership | le composant possède sa forme | la troisième nature possède sa forme |
| validation locale | `trigger`, `scope` textuels ; `status` en vocabulaire fermé ; `additionalProperties: false` | identique — la nature ne change pas ce qu'un schéma peut dire |
| coût de migration | répertoire + 2 fichiers minimum, entrée dans la table, `type:` du profil, clé de dispatch ×2 | 1 schéma + 1 nature + ouverture de `adc_contracts` |
| impact ADR | ADR-0010 (nature du fragment) : aucune révision — la nature existe | ADR-0010 **à réviser** : une troisième nature à déclarer |
| impact résolution | aucun — `_SINGLE_OCCURRENCE_SOURCES` est indexée par `instance_id`, pas par composant **(mesuré)** | aucun |

**Note propre au bloc.** ADR-0003 liste « Context » parmi les composants du noyau, et
`docs/specifications/component-library.md` classe « Contexte » comme *obligatoire et
réutilisable* **(mesuré)**. Un engagement doctrinal existe donc déjà pour ce bloc, et le
Modèle B le contredirait sans le dire — ou imposerait de réviser ces deux documents.

---

## `investigations`

| Critère | Modèle A | Modèle B |
|---|---|---|
| schéma | `components/C-0xx-investigation/schema.json`, forme `OCCURRENCE` | emplacement à créer |
| cardinalité | inchangée (0..∞) | inchangée (0..∞) |
| builder | clé `("C-0xx-investigation", None)` | clé `("narrative-investigation", None)` inchangée |
| catalogue | entre au catalogue | absent |
| cycle de vie | cycle complet | à définir |
| ownership | le composant | la troisième nature |
| validation locale | `id` non vide, `title`, `description`, `result` textuels | identique |
| coût de migration | **plus élevé que les trois autres** : la clé de `_MULTIPLE_OCCURRENCE_SOURCES` est le `component_id`, donc la table de résolution change aussi **(mesuré)** | 1 schéma + 1 nature |
| impact ADR | aucun | ADR-0010 à réviser |
| impact résolution | `_MULTIPLE_OCCURRENCE_SOURCES` : clé `narrative-investigation` → `C-0xx` | aucun |

**Note propre au bloc.** C'est le seul des quatre à être **répétable**, et le seul dont le
`id` sert d'identifiant d'occurrence dans l'IR **(mesuré)**. C'est aussi celui qui ressemble
le plus aux composants existants du catalogue — `C-004-finding`, `C-010-evidence` — dont il
partage la forme : collection d'objets identifiés. Le rapprochement est structurel, pas
éditorial.

---

## `probable_cause`

| Critère | Modèle A | Modèle B |
|---|---|---|
| schéma | `components/C-0xx-probable-cause/schema.json` | emplacement à créer |
| cardinalité | inchangée (0..1) | inchangée (0..1) |
| builder | clé `("C-0xx-probable-cause", "probable-cause")` | clé inchangée |
| catalogue | entre au catalogue | absent |
| cycle de vie | cycle complet | à définir |
| ownership | le composant | la troisième nature |
| validation locale | `statement` textuel, `confidence` en vocabulaire fermé, `supporting_finding_ids` liste de chaînes non vides | identique |
| coût de migration | répertoire + 2 fichiers, table, profil, dispatch ×2 | 1 schéma + 1 nature |
| impact ADR | aucun | ADR-0010 à réviser |
| impact résolution | aucun | aucun |

**Note propre au bloc — indépendante des deux modèles.** `supporting_finding_ids` est une
référence croisée que **le validateur métier ne contrôle pas** : il vérifie
`findings.evidence_ids`, `recommendations.related_finding_ids` et
`risks.mitigation_recommendation_ids`, et rien d'autre **(mesuré)**. Une référence inconnue
y est bien signalée, mais par la **composition**
(`référence non résolue: narrative :: probable-cause -> finding-404`), donc dans
`Document.diagnostics` — « ce que le moteur n'a pas su faire » — alors qu'ADR-0009 range une
référence inconnue parmi les défauts métier.

C'est un écart de propriété au sens de G1, et **aucun des deux modèles ne le corrige** :
un schéma local ne peut pas voir la résolubilité d'une référence (ADR-0010). À traiter
séparément, quel que soit le modèle retenu.

---

## `conclusion`

| Critère | Modèle A | Modèle B |
|---|---|---|
| schéma | `components/C-0xx-conclusion/schema.json`, fragment de type `string` | emplacement à créer |
| cardinalité | inchangée (1..1) | inchangée (1..1) |
| builder | clé `("C-0xx-conclusion", "conclusion")` | clé inchangée |
| catalogue | entre au catalogue | absent |
| cycle de vie | cycle complet | à définir |
| ownership | le composant | la troisième nature |
| validation locale | **la plus pauvre des quatre** : le nœud est une chaîne, un schéma ne peut guère dire plus que « chaîne » | identique |
| coût de migration | répertoire + 2 fichiers, table, profil, dispatch ×2 | 1 schéma + 1 nature |
| impact ADR | aucun | ADR-0010 à réviser |
| impact résolution | aucun | aucun |

**Note propre au bloc.** C'est le seul des quatre dont le fragment n'est pas un objet
**(mesuré)**. Un contrat y apporterait peu : il rejetterait un objet ou un nombre, ce que le
builder ignore déjà silencieusement (`text: ()`). Le rapport coût/bénéfice de la
contractualisation y est le plus défavorable des quatre — dans les deux modèles.

**Asymétrie de rendu, mesurée.** Les renderers ne traitent pas le vide de la même façon :
`_render_conclusion` sort sans rien écrire quand le texte est vide — « pas de titre
orphelin » — alors que `_render_incident_context` pose son titre sans garde. Un nœud vide
produit donc **rien** pour la conclusion, et **un titre suivi de rien** pour le contexte.

Cette divergence est antérieure aux deux modèles et n'est arbitrée par aucun d'eux : décider
si un titre orphelin est acceptable relève de la couche de rendu (ADR-0009, I3), pas d'un
contrat de source. Elle est notée ici parce qu'elle change ce qu'un lecteur observe d'un
bloc vide, et pourrait être confondue avec un effet de la contractualisation.

---

## Faits transversaux

**1. Le catalogue est déjà à moitié constitué de chapitres singuliers (mesuré).**
Sur les dix composants, cinq sont à occurrence unique et structurels — `C-001-cover`,
`C-002-identity-page`, `C-003-executive-summary`, `C-009-environment`, `C-008-timeline` —
et cinq sont des unités répétables — `C-004`, `C-005`, `C-006`, `C-007`, `C-010`. La
distinction « unité réutilisable » contre « chapitre structurel » ne recoupe donc pas
aujourd'hui la frontière du catalogue.

**2. `C-003-executive-summary` est un précédent exact (mesuré).**
Chapitre unique, non réutilisable d'un document à l'autre, lu en `NODE`, contrat = objet plat
à quatre champs textuels avec `additionalProperties: false`. C'est, trait pour trait, la
forme qu'appellerait `incident_context` ou `probable_cause`.

**3. Deux documents doctrinaux nomment déjà « Context » comme composant (mesuré).**
ADR-0003 (« Composants du noyau : … Context … Annexes ») et `component-library.md`. Le
Modèle B exige de les réviser pour au moins un bloc, ou de vivre avec une contradiction
documentée.

**4. Bibliothèque et famille de rapports sont couplées par un test (mesuré).**
`test_every_component_of_the_library_is_located` impose que **tout** répertoire de
`components/` figure dans `INCIDENT_REPORT_FRAGMENTS` comme composant catalogue. Sous le
Modèle A, créer un composant, c'est donc l'inscrire d'office dans la famille « rapport
d'incident » — y compris un composant qui ne la concernerait pas. Le Modèle B n'ajoute
aucun couplage de ce type.

**5. Coût de migration mesuré.**
67 lignes mentionnent `narrative` dans le code, les tests et les profils **(mesuré)**,
réparties ainsi :

| Fichier | Lignes |
|---|---:|
| `tests/test_builder_dispatch.py` | 22 |
| `tests/test_composition_engine.py` | 13 |
| `tools/python/adc_engine/compose.py` | 8 |
| `tools/python/adc_engine/render_docx.py` | 8 |
| `tests/test_profile.py` | 8 |
| `profiles/p-003-incident-report.yaml` | 4 |
| autres (4 fichiers) | 4 |

Le Modèle A touche la majorité de ces lignes ; le Modèle B n'en touche aucune **(déduit)**.
La charge du Modèle A est donc concentrée dans les tests, non dans le moteur.

**6. Le Modèle A ferait disparaître la notion de « famille narrative » (déduit).**
Trois blocs partagent aujourd'hui le `component_id` `narrative`, distingués par leur
`instance_id`. C'est précisément le cas pour lequel la clé de dispatch
`(component_id, instance_id)` a été introduite. Sous le Modèle A, chaque bloc reçoit son
identifiant propre et ce partage disparaît — la clé composite resterait correcte mais
n'aurait plus d'emploi. Le Modèle B le conserve.

**7. Le Modèle B laisse un vide de cycle de vie (déduit).**
`docs/architecture/component-lifecycle.md` ne gouverne que les composants. Un fragment
contractuel hors catalogue n'aurait ni statut, ni règle de version, ni obligation de
promotion — sauf à écrire pour lui un cycle parallèle. Le Modèle A hérite du cycle existant
sans rien écrire.

## Ce que l'étude ne peut pas trancher

Ces questions ne sont ni mesurables ni déductibles depuis l'état du dépôt. Les trancher
relève de la décision, pas de l'étude.

1. **Un « chapitre » doit-il partager le cycle de vie d'une « unité » ?** Le fait n° 1
   montre que le catalogue ne fait pas cette distinction aujourd'hui ; il ne dit pas qu'il
   a raison de ne pas la faire.
2. **La réutilisabilité est-elle un critère d'appartenance au catalogue ?** Ni ADR-0003, ni
   ADR-0006, ni ADR-0007 ne l'exigent explicitement — mais `component-library.md` porte une
   colonne « Réutilisable », dont aucun mécanisme ne dépend.
3. **Le catalogue doit-il rester lié à une seule famille de rapports ?** Le fait n° 4 est un
   couplage réel ; il n'est pas dit qu'il soit voulu.
4. **La décision doit-elle être uniforme pour les quatre blocs ?** Les grilles divergent
   nettement : `investigations` est structurellement proche des composants existants,
   `conclusion` est le cas où un contrat apporte le moins.
5. **Quel est le sort d'`annexes` ?** Nœud que personne ne consomme, mais listé comme
   composant du noyau par ADR-0003. Il n'entre pas dans le périmètre de cette étude et reste
   ouvert depuis ADR-0012.

## Liens

- ADR-0012 — Gouvernance du contrat narratif : G3 (aucun nœud consommé hors contrat) est ce
  qui rend cette étude nécessaire ; la forme y est explicitement laissée ouverte.
- ADR-0010 — Forme canonique : la nature d'un fragment, que le Modèle B propose d'étendre.
- ADR-0003, `docs/specifications/component-library.md` — ce que le dépôt dit déjà de
  l'appartenance au catalogue.
