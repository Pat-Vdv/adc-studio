# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Nature du dépôt

ADC Studio est un framework documentaire : il compose des livrables Word à partir de
composants versionnés (`components/C-00x-*`), d'un profil déclaratif (`profiles/`) et
d'une source de données JSON. Le dépôt ne contient **que du générique** — les données
clients restent hors dépôt (`rapports-clients/` est gitignoré).

La langue de travail est le **français** : docstrings, commentaires, ADR, messages de
commit. Les identifiants de code, les valeurs canoniques de l'IR et les noms de tests
sont en anglais.

## Commandes

Environnement : `.venv/` à la racine (Python 3.12), dépendances dans `requirements-dev.txt`.

```bash
.venv/bin/python -m pytest -q                              # suite complète (~700 tests, ~8 s)
.venv/bin/python -m pytest tests/test_entry_boundary.py    # un fichier
.venv/bin/python -m pytest tests/test_presentation.py::test_no_count_is_ever_produced   # un test
.venv/bin/python -m pytest -k "contract"                   # par motif
```

`tests/conftest.py` met `tools/python/` sur le `sys.path` : aucune installation du paquet
n'est nécessaire.

```bash
# Générer un rapport depuis une source contractuelle (sortie par défaut : build/<report_id>.docx)
.venv/bin/python tools/python/generate_incident_report.py reference_reports/incident_report/data/sql_server_2014_incident.json

# Valider une source : forme (contrats) puis métier, rapportées ensemble
.venv/bin/python tools/python/validate_incident_report.py <source.json> [--summary]

# Générer le rapport d'une mission créée par nouveau-rapport
.venv/bin/python tools/python/generate_mission_report.py <dossier-mission> [-o sortie.docx] [--write-source]
```

`nouveau-rapport.bat` / `nouveau-rapport.ps1` (Windows) créent un **atelier de mission** sous
`rapports-clients/<client>/<année>/<date>_<titre>/` avec un `metadata.yml`.

## Architecture — la chaîne à sens unique

ADR-0009 fixe une chaîne sans retour ni raccourci. Chaque étape ne connaît que la précédente.

```
metadata.yml (atelier)  --adc_mission-->  Source JSON contractuelle
                                                │
                                                ▼
                            Frontière d'entrée   adc_engine/entry.py     ← contrats vérifiés ICI, une fois
                                                │
                                                ▼
                            Composition          adc_engine/compose.py   ← builders par composant
                                                │
                                                ▼
                            Document IR          adc_engine/model.py     ← seule vérité métier, sans format
                                                │
                                                ▼
                            RenderContext        (metadata["render_context"])
                                                │
                                                ▼
                            Renderer             adc_engine/render_docx.py
```

### Modules et leurs frontières

| Module | Rôle | Dépendances autorisées |
|---|---|---|
| `adc_diagnostics.py` | `ValidationDiagnostic`, support commun aux deux validations | aucune |
| `adc_contracts.py` | validation JSON Schema des fragments source ; table `INCIDENT_REPORT_FRAGMENTS` | neutre (ni moteur, ni format) |
| `adc_profile/` | ordre et cardinalités des blocs, résolution des occurrences | neutre |
| `adc_mission.py` | pont atelier → source contractuelle (ADR-0011) | neutre |
| `adc_presentation.py` | mise en forme CLI des diagnostics ; ne valide rien | `adc_contracts` |
| `adc_engine/` | frontière, composition, IR, rendu | tout ce qui précède |
| `validate_incident_report.py` | règles **métier** seules | modules neutres, jamais le moteur |

`adc_engine/validation.py` charge le validateur *dynamiquement* pour que la dépendance
reste à sens unique (le validateur ignore le moteur).

### Deux validations, jamais fondues

- **Forme** (`adc_contracts`) : un fragment contre le `schema.json` de son composant. Écart = la
  composition s'arrête, rien n'est généré (`SourceContractError`).
- **Métier** (`validate_incident_report.validate`) : références, unicité, présence des nœuds.
  Écart = le document est **quand même** généré, l'écart l'accompagne dans
  `Document.source_diagnostics`.

De même, `Document.diagnostics` (ce que le moteur n'a pas su faire) et
`Document.source_diagnostics` (ce que le contenu a de fautif) ne doivent jamais être fondus.

### Ajouter la prise en charge d'un composant

Un builder dans `_BUILDERS` (`compose.py`) + un renderer dans la table de `render_docx.py`.
Un composant sans builder ou sans renderer **ne casse rien** : il produit un diagnostic (I8).
La clé de dispatch est `(component_id, instance_id | None)` — plusieurs blocs peuvent partager
un `component_id` (cas des blocs `narrative`).

### La table des fragments

`INCIDENT_REPORT_FRAGMENTS` (dans `adc_contracts.py`) dit **où** lire, dans une source, le
fragment de chaque consommateur. Elle appartient à une *famille de rapports*, pas à la
bibliothèque : le nom du nœud ne se déduit pas de l'identifiant (C-007 lit `actions_taken`).
Un `ROOT_FRAGMENT` y est déclaré pour nommer son consommateur — cela ne lui accorde **aucune**
couverture de schéma. Cette table est aussi la source de vérité de `adc_presentation._is_section`.

## Doctrine — ADR normatifs

Les ADR ne sont pas de la documentation d'accompagnement : ils sont **normatifs**. Une
modification qui viole un invariant exige un ADR qui le révise, jamais une exception locale.
Lire `docs/adr/ADR-0009` (invariants I1–I9), `ADR-0010` (forme canonique, portée des schémas),
`ADR-0011` (pont atelier/contrat, règles R1–R6) avant de toucher au moteur, aux schémas ou au pont.

Interdits explicites, à connaître avant d'écrire :

- passer la source au renderer, ou y résoudre une référence / construire un index (I1, I2) ;
- trier, regrouper, filtrer ou déduire quoi que ce soit pendant la composition (I6) ;
- écrire un identifiant technique dans le document produit — les références sont résolues en
  libellés avant le rendu, une référence sans cible sort en diagnostic (I4) ;
- stocker un libellé français dans un payload : l'IR est anglais et canonique (`low`, `critical`,
  `completed`), le français appartient au renderer (I5) ;
- appeler un schéma de composant ailleurs qu'à la frontière d'entrée (I9) ;
- ajouter à un `schema.json` un alias venant du vocabulaire d'un atelier (R1) ;
- normaliser une valeur dans le pont — dates, casse, valeurs déduites (R3) ; écrire une propriété
  vide plutôt que de l'omettre (R4) ; matérialiser la source contractuelle par défaut (R5).

**Incomplet n'est pas malformé.** Un document composé peut être incomplet sans être invalide.
Une section absente est « ce qui reste à rédiger », pas un défaut — `adc_presentation` existe
pour tenir cette distinction à l'affichage, et n'annonce jamais *combien* d'éléments manquent
(le moteur ne le sait pas, l'inventer serait une information fabriquée).

## Conventions

**Méthode : la doctrine avant le code.** L'ADR se décide et se commite séparément du code
qu'il gouverne. Le balayage systématique d'un domaine précède le traitement des cas nommés.

**Commits** — conventional commits, sujet en français, présent : `feat(mission):`,
`docs(adr):`, `fix(validation):`, `refactor(validation):`, `chore:`. (Les exemples anglais de
`CONTRIBUTING.md` sont périmés ; l'historique fait foi.) Jamais de `git add -A` : chaque fichier
est ajouté délibérément.

**Docstrings** — elles disent *pourquoi*, pas *quoi* : la contrainte respectée, l'alternative
écartée et sa raison, ce que la fonction ne fait volontairement pas. Chaque module en-tête
nomme sa neutralité (« ne dépend ni du moteur, ni d'un format de sortie »). Suivre ce registre.

**Tests** — un nom de test est une phrase anglaise qui énonce la règle
(`test_a_business_defect_still_composes`, `test_no_count_is_ever_produced`). Les invariants
d'ADR-0009 sont tenus par des tests nommés dans la section « Vérification » de l'ADR : les
renommer, c'est périmer l'ADR.

**Composants** — `components/*/metadata.yaml` est la source de vérité ; `COMPONENT_CATALOG.md`
en est une projection. Une promotion de statut (cycle `Planned → Prototype → Draft → Stable →
Deprecated → Archived`) met à jour `metadata.yaml`, le README du composant, `COMPONENT_CATALOG.md`,
`PROJECT_STATUS.md` et `CHANGELOG.md`.

**Encodage** — les sources sont lues en `utf-8-sig` (les fichiers produits par PowerShell portent
un BOM). Fins de ligne LF partout sauf `.ps1`/`.bat`/`.cmd` en CRLF (`.gitattributes`).

## État courant

Branche `feature/mission-bridge`. Le pont de mission est **complet** : ADR-0011 R6 est
implémentée (`schema_version` produite par le pont), ses garde-fous sont en place — dont le
test d'accord entre `adc_mission.CONTRACT_VERSION` et le validateur métier, seul garant qu'ils
ne divergent pas. Suite verte : 712 tests. La chaîne
`metadata.yml → traduction → contrat → validation → composition → DOCX` est utilisable de
bout en bout.

Chantier suivant : la gouvernance du contrat narratif (ADR-0012). Les quatre blocs narratifs —
`incident_context`, `investigations`, `probable_cause`, `conclusion` — sont des `ROOT_FRAGMENT` :
aucun contrat ne les couvre, et un contenu arbitraire y traverse toute la chaîne sans un seul
diagnostic. G3 en fait une dette à résorber, G4 arbitre le désaccord entre validateur et
résolution sur le nœud vide.

Note de décalage : ADR-0009 cite `adc_engine/resolve.py` et `adc_profile.py`, qui sont aujourd'hui
le paquet `adc_profile/` (`contract.py`, `resolution.py`).
