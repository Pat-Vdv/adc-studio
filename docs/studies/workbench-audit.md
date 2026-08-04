# Workbench — audit, architecture et phasage

**Aucune implémentation n'est engagée par ce document.** Il livre ce qui doit précéder :
l'état de l'existant, ce qui est déjà observable, ce qui exige une instrumentation et où
elle appartient, les risques de duplication, une architecture et un découpage.

## 1. Audit de l'existant

### Ce qui n'existe pas — mesuré, pas supposé

| Recherché | Résultat |
|---|---|
| couche web, serveur, endpoint HTTP | **aucun** — pas de flask/fastapi/django/http.server/websocket |
| fichier front (`.html`, `.js`, `.css`, `.ts`) | **aucun** |
| instrumentation de temps (`perf_counter`, `elapsed`, …) | **aucune** |
| renderer PDF | **aucun** — le PDF est une intention de feuille de route |
| trace de rendu (quel chapitre vient de quelle instance) | **aucune** |

Conséquence directe : « les API publiques » du prompt n'existent pas au sens HTTP. La
surface consommable est **l'API Python des modules**. Le Workbench est donc à construire
sur cette surface, ou sur une couche de service qui l'expose — c'est un choix
d'architecture, pas un existant.

### La surface réellement consommable

| Module | Entrée publique | Ce que le Workbench en tire |
|---|---|---|
| `adc_mission` | `mission_source(mission)`, `load_metadata` | panneau 1, et la source contractuelle réellement envoyée |
| `adc_contracts` | `INCIDENT_REPORT_FRAGMENTS`, `report_diagnostics`, `load_schema`, `component_ids`, `has_contract` | panneau 2 entier, diagnostics de contrat |
| `adc_profile` | `load_profile` → `Profile.entries`, `resolve(data, profile)` → `(blocks, diagnostics)` | ordre, cardinalités, **occurrences résolues** |
| `validate_incident_report` | `validate(data)` | diagnostics métier, structurés |
| `adc_engine` | `compose_from_source`, `compose_document`, `SourceContractError.diagnostics` | l'IR et ses deux natures de diagnostic |
| `adc_presentation` | `missing_sections`, `defects`, `source_lines` | « section à rédiger » vs « contenu fautif » |
| `adc_engine.render_docx` | `render_docx(document, path) -> Path` | le fichier produit, **et rien d'autre** |

### Structures disponibles

`Document(id, type, title, metadata, components, diagnostics, source_diagnostics)`,
`ComponentInstance(component_id, instance_id, payload)`,
`ValidationDiagnostic(path, message, source, component, code)`,
`Fragment(nature, kind, path)`, `Profile` / `ProfileEntry(component_id, instance_id, minimum, maximum)`.

`Document.metadata["render_context"]` porte les index de libellés dérivés de l'IR.

## 2. Disponible aujourd'hui, ou à instrumenter

Les huit questions du prompt, confrontées à l'existant :

| Question | Répondable aujourd'hui ? | Par quoi |
|---|---|---|
| Pourquoi cette section apparaît-elle ? | **oui** | `resolve()` → occurrences ; profil → ordre |
| Pourquoi n'apparaît-elle pas ? | **partiellement** | nœud absent : `resolve` + validateur. Builder manquant : *chaîne libre* (G-1) |
| Quel contrat a validé ou rejeté ce nœud ? | **oui** | table des fragments + `report_diagnostics` (porte `component` et `code`) |
| Quel composant est responsable de ce rendu ? | **oui** | `ComponentInstance.component_id` |
| Quel renderer a produit ce chapitre ? | **non** | aucune trace de rendu (G-3) |
| Quelle résolution a été effectuée ? | **oui** | `resolve()` est public et appelable |
| Quels diagnostics existent ? | **oui, sauf gravité** | deux natures structurées ; la composition non (G-1) ; la gravité n'existe pas (G-5) |
| Quelle partie de la source correspond à cette sortie ? | **partiellement** | source → instance : oui (table + résolution). Instance → chapitre : non (G-3) |

### Les écarts, et à quelle couche ils appartiennent

**G-1 — Les diagnostics de composition ne sont pas structurés.**
`Document.diagnostics` est un `tuple[str, ...]` : « cardinalité non respectée: C-004-finding :: 2
occurrence(s) au minimum, 1 obtenue(s) ». Le panneau 3 exige propriétaire, code, gravité,
message et chemin — rien de cela n'est adressable sans analyser du texte, ce qui serait
reconstruire dans l'UI une information que le moteur détient.
*Propriétaire : la composition* (`adc_engine.model`), qui les produit.
*Impact doctrinal* : ADR-0009 décrit ce champ ; le structurer demande un ADR, pas un
refactor discret.

**G-2 — La résolution n'est pas exposée sur le `Document`.**
`compose_document` appelle `resolve()`, consomme `blocks` et le jette. Un bloc résolu mais
sans builder disparaît des `components` et ne laisse qu'une chaîne.
*Aucune instrumentation n'est cependant nécessaire en V1* : `resolve(data, profile)` est
public et le Workbench dispose des mêmes entrées. L'appeler n'est pas une duplication —
c'est la fonction propriétaire elle-même. L'exposer sur le `Document` reste souhaitable, mais
c'est une commodité, pas un prérequis.

**G-3 — Aucune carte de rendu.** *L'écart le plus structurant.*
`render_docx` écrit dans un document python-docx et retourne un chemin. Rien n'enregistre
que les paragraphes *n* à *m* proviennent de telle instance. Or les panneaux 4 et la
navigation croisée reposent entièrement là-dessus.
*Propriétaire : le renderer, et lui seul* — aucune autre couche ne peut la produire, puisque
lui seul connaît la mise en page (ADR-0009, I3). La carte doit sortir **à côté** de l'IR, en
valeur de retour, et surtout **pas** être écrite dans le `Document` : le renderer ne remonte
jamais dans l'IR (I1).

**G-4 — Aucune mesure de temps.**
*Propriétaire : la couche d'observation, pas le moteur.* Le temps est une mesure, pas une
donnée métier ; l'inscrire dans le moteur ferait porter à la chaîne une préoccupation
d'outillage. Au grain « traduction / frontière / composition / rendu », il est mesurable de
l'extérieur **sans aucune instrumentation**. Au grain builder-par-builder, il exigerait des
points d'ancrage — à différer jusqu'à ce qu'un besoin réel l'exige.

**G-5 — La gravité n'a aucun propriétaire.**
Le panneau 3 demande une gravité par diagnostic. Aucune couche n'en déclare aujourd'hui.
La produire dans l'UI inventerait un vocabulaire que le domaine n'a jamais énoncé —
exactement ce qu'ADR-0010 interdit, et le raisonnement qui a laissé `status` ouvert sur
C-011. *Recommandation V1 : ne pas afficher de colonne gravité.* Afficher `source` et `code`,
qui existent et sont déjà machine-lisibles. Si la gravité devient nécessaire, elle sera
déclarée par la couche propriétaire de chaque règle, jamais dérivée d'un message.

**G-6 — Aucun pipeline PDF.** Hors périmètre V1, sans contournement honnête.

**G-7 — Aucun `narrative` structuré.** Le brouillon de mission est un Markdown libre : le
panneau 1 ne peut en montrer que le texte brut. C'est cohérent avec l'état du projet, la
question du format de rédaction n'ayant jamais été tranchée.

## 3. Risques de duplication de logique métier

Classés par probabilité de survenue, chacun avec la règle qu'il violerait.

| # | Risque | Règle violée | Parade |
|---|---|---|---|
| R-1 | reconstruire dans l'UI la carte nœud → composant | ADR-0012 **G2** : un fait n'est déclaré qu'une fois | lire `INCIDENT_REPORT_FRAGMENTS` |
| R-2 | trier ou regrouper les sections dans l'UI | ADR-0012 **G1** : l'ordre appartient au profil | consommer l'ordre de `resolve()` |
| R-3 | recalculer « section manquante » vs « contenu fautif » | déjà porté par `adc_presentation` | appeler `missing_sections` / `defects` |
| R-4 | traduire les valeurs canoniques (`high` → « Élevée ») | ADR-0009 **I5/I3** : le français appartient au renderer | **le Workbench affiche l'IR canonique, jamais traduit** |
| R-5 | inventer une gravité, un niveau, un code | ADR-0010, origine d'une contrainte | cf. G-5 |
| R-6 | recalculer présence ou cardinalité | ADR-0012 **G1/G4** | profil + validateur |
| R-7 | rappeler `jsonschema` depuis l'UI | ADR-0009 **I9** : les contrats sont consommés à la frontière | `report_diagnostics` uniquement |

**Règle proposée pour le Workbench** — une seule, qui les couvre toutes :

> Toute donnée affichée doit être traçable à une fonction publique qui la produit. Le
> Workbench n'a le droit de *lire*, *filtrer* et *mettre en page* — jamais de *décider*.

Elle est vérifiable, sur le modèle de `test_the_contracts_are_consumed_at_the_boundary_only` :
un test d'architecture interdisant à `adc_workbench` d'importer `jsonschema`, d'ouvrir un
`components/*/schema.json`, ou de porter une table de correspondance. À écrire dès P1.

## 4. Architecture proposée

### Le pivot : un instantané d'observation

Une passe unique du pipeline réel produit **un seul document JSON** — l'instantané — et
l'interface est une **fonction pure** de cet instantané.

```
API publiques  ──►  observation  ──►  instantané JSON  ──►  interface
                    (une passe)        (déterministe)       (pure lecture)
```

Trois propriétés en découlent :

- **déterminisme** — même source, même instantané, même écran ;
- **impossibilité structurelle de la logique métier dans l'UI** — elle ne voit que le
  résultat, jamais les entrées qui permettraient de recalculer quoi que ce soit ;
- **artefact de régression** — un instantané se versionne, se compare, sert de référence de
  validation visuelle. C'est ce qui rend tenable la dernière exigence du prompt.

### Découpage

```
adc_workbench/
    observation.py   appelle les API publiques, produit l'instantané
    snapshot.py      structures de l'instantané (dataclasses gelées)
    serve.py         serveur local en lecture seule (GET uniquement, stdlib)
    ui/              HTML + CSS + JS autonomes, aucun framework
```

- **Aucune dépendance nouvelle** : `http.server` de la bibliothèque standard, front en
  vanilla. Le dépôt n'a que pytest, python-docx, pyyaml, jsonschema ; le Workbench n'en
  ajoute aucune.
- **Lecture seule structurelle** : le serveur n'implémente que `GET`. L'observation n'écrit
  que le DOCX, dans un répertoire de travail hors dépôt.
- **Sélection synchronisée** : une identité unique par élément — le couple
  `(component_id, instance_id)` et le chemin source `$.nœud[i]`. Tous les panneaux
  s'indexent sur ces deux clés ; la synchronisation est alors une conséquence, pas une
  fonctionnalité à écrire cinq fois.

### Pourquoi pas une TUI

Une interface terminal (textual/rich) coûterait une dépendance et rendrait les panneaux
redimensionnables et la sélection croisée nettement plus laborieux. Le navigateur les donne
gratuitement. Le coût — un serveur local — est de quinze lignes de stdlib.

## 5. Phasage

Chaque phase est utilisable seule et n'anticipe rien de la suivante.

| Phase | Contenu | Instrumentation requise |
|---|---|---|
| **P1** | instantané + panneaux 2 (contrat), 3 (diagnostics), 5 (résolution) ; test d'architecture anti-duplication | **aucune** |
| **P2** | panneau 1 (mission), confidentialité des données client | aucune |
| **P3** | diagnostics de composition structurés | **G-1** — ADR préalable |
| **P4** | carte de rendu | **G-3** — ADR préalable |
| **P5** | panneau 4 réel et navigation croisée complète | dépend de P4 |
| **P6** | temps par étape, au grain mesurable de l'extérieur | G-4, sans toucher au moteur |

P1 et P2 livrent déjà six des huit questions du prompt sans modifier une ligne du moteur.
C'est le découpage qui maximise ce qu'on obtient avant toute instrumentation.

## 6. Doctrine à écrire — ADR-0014

La dernière exigence du prompt ne doit pas rester une consigne de conversation :

> Chaque nouvelle capacité du moteur est observable dans le Workbench avant d'être
> exploitée par une interface métier.

C'est une règle de gouvernance, au même titre que G1 à G6. Sans ADR, elle sera contournée à
la première urgence, et le Workbench dérivera vers l'« UI de debug » que le prompt redoute.
Décisions à y porter : le Workbench comme couche d'observabilité pérenne ; l'interdiction
d'y placer une décision ; l'obligation d'un point d'observation pour toute capacité
nouvelle ; le propriétaire de chaque donnée observée.

## 7. Points ouverts et risques

**Données client.** `rapports-clients/` est gitignoré, et un instantané contient le contenu
du rapport. Il ne doit jamais être écrit dans le dépôt ni committé : répertoire de sortie
hors dépôt, et gitignore explicite. C'est le risque le plus concret de tout le chantier.

**Fidélité du panneau 4.** Afficher un DOCX dans un navigateur demande une conversion. Sans
elle, le panneau 4 montrera une reconstruction structurelle dérivée de l'IR et de la carte
de rendu — utile pour la navigation, **jamais un aperçu fidèle**. À ne pas promettre.

**Profil mis en cache.** `incident_profile()` est décoré `@lru_cache` : modifier
`p-003-incident-report.yaml` ne se reflète pas sans redémarrage. Acceptable pour une passe
unique, à traiter si le Workbench devient un outil quotidien à chaud.

**Une seule famille de rapports.** Toute la chaîne est indexée sur P-003. Le Workbench
héritera de ce couplage, qu'ADR-0013 assume déjà.
