# ADR-0009 — Composition Pipeline

## Statut

Accepté

## Date

2026-07-28

## Contexte

ADR-0008 a défini le *modèle* documentaire (Document, Component, Profile,
Renderer). Il ne dit pas comment ces concepts s’enchaînent à l’exécution, ni ce
qu’il est interdit de faire à chaque étape.

Le moteur est désormais implémenté et couvre tous les composants catalogue
résolus par le profil incident :

- composition : `tools/python/adc_engine/compose.py` ;
- modèle intermédiaire : `tools/python/adc_engine/model.py` ;
- résolution de l’ordre : `tools/python/adc_engine/resolve.py` ;
- rendu Word : `tools/python/adc_engine/render_docx.py`.

Cette implémentation a fait émerger des règles qui ne sont écrites nulle part.
Elles ont pourtant été décidées explicitement, une par une, et plusieurs
d’entre elles ont déjà résisté à la tentation inverse : résoudre une référence
dans le renderer, trier des occurrences pendant la composition, ou traduire une
valeur d’énumération dans le modèle.

Sans formalisation, ces règles s’éroderont : chacune peut être contournée « pour
aller plus vite » sans qu’aucun test global ne s’y oppose. Le coût du
contournement est différé et élevé — c’est exactement ce que le renderer
indépendant du format devait éviter.

## Décision

La production d’un document suit une chaîne à sens unique, sans retour ni
raccourci :

```
Source (JSON)
      │
      ▼
Frontière d'entrée          contrats de composants ; au-delà, la forme est acquise
      │
      ▼
Composition                 données métier -> instances de composants
      │
      ▼
Document IR                 seule vérité métier, indépendante du format
      │
      ▼
RenderContext               index de présentation dérivés de l'IR
      │
      ▼
Renderer                    matérialisation dans un format cible
```

Chaque étape ne connaît que la précédente. Aucune étape ne relit une étape
antérieure à son entrée.

### Étapes

1. **Source** — JSON. Elle est la seule entrée du moteur, et n’est lue que par
   la frontière puis par la composition.
2. **Frontière d’entrée** — confronte la source aux contrats de composants
   (ADR-0010). Un écart interrompt ; en deçà, aucune étape ne revérifie la
   forme.
3. **Composition** — construit les instances de composants à partir de la
   résolution déterministe du profil. Un composant sans builder produit un
   diagnostic, jamais une exception.
4. **Document IR** — porte l’ordre des instances, leurs payloads, les
   métadonnées et les diagnostics. Il ne connaît ni Word, ni PDF, ni HTML.
5. **RenderContext** — index de présentation (libellés des cibles référencées),
   dérivés des instances de l’IR et rangés sous `metadata["render_context"]`.
6. **Renderer** — transforme l’IR enrichi du contexte en fichier. Il est maître
   de la mise en page et de rien d’autre.

## Invariants

Ces invariants sont normatifs. Une modification qui en viole un doit faire
l’objet d’un ADR qui les révise, pas d’une exception locale.

**I1 — Le renderer ne lit jamais la source.**
Sa seule entrée est le `Document` et le `RenderContext` qui en dérive. Aucun
accès au JSON d’entrée, direct ou indirect.

**I2 — Le renderer ne résout jamais les références.**
Il consomme des libellés déjà résolus. Il ne parcourt pas les autres instances
pour retrouver une cible, et ne construit aucun index.

**I3 — Le renderer ne traduit jamais la structure métier.**
Il ne décide ni de l’ordre, ni de la présence, ni du regroupement des
composants : il rend ce que l’IR contient, dans l’ordre où il le contient. En
revanche, les libellés destinés au lecteur — titres de sections, vocabulaire
d’énumérations, accords grammaticaux — lui appartiennent entièrement.

**I4 — Toutes les références sont résolues avant le rendu.**
Le modèle relie par identifiant ; la présentation affiche des titres. Un
identifiant technique n’apparaît jamais dans un document produit. Une référence
sans libellé n’est ni affichée telle quelle, ni remplacée par un texte inventé,
ni perdue en silence : elle sort en diagnostic à la composition.

**I5 — L’IR est la seule vérité métier.**
Les valeurs y sont canoniques (`low`, `medium`, `high`, `critical`,
`completed`, …) et anglaises. Aucune traduction, aucune normalisation, aucun
libellé de présentation n’entre dans un payload.

**I6 — La composition ne déduit rien.**
Ni ordre, ni date, ni statut, ni niveau, ni valeur manquante. Un champ absent
de la source reste absent du payload ; l’ordre de la source est conservé tel
quel. Le moteur est piloté par le contrat machine réel, pas par l’intention
fonctionnelle décrite au catalogue.

**I7 — Le renderer est sans état entre les instances.**
Chaque instance est rendue indépendamment. Un titre de partie commun à
plusieurs occurrences relève de la structure du document, donc de l’IR, jamais
d’une logique « émettre une seule fois » dans le renderer.

**I8 — L’absence de prise en charge est tracée, jamais masquée.**
Un composant sans builder, un composant sans renderer ou une référence non
résolue n’interrompent pas la génération. La traçabilité est portée par
`Document.diagnostics`.

**I9 — La composition n’accepte qu’une source conforme aux contrats.**
Un écart aux contrats de composants (ADR-0010) interrompt la chaîne : rien
n’est composé, rien n’est rendu. Un défaut métier — référence inconnue,
identifiant dupliqué, nœud de la famille absent — ne l’interrompt pas : il
accompagne le document, dans `Document.source_diagnostics`.

Cette vérification a lieu **une fois**, à la frontière. Aucun builder n’appelle
un schéma : il resterait une transformation pure, mais ne pourrait plus être
testé sans que son entrée soit d’abord rendue conforme.

### Incomplet n’est pas malformé

I8 et I9 ne se contredisent pas, parce qu’ils parlent de deux choses :

| | Incomplet | Malformé |
|---|---|---|
| Ce qui manque | une information métier, une prise en charge du moteur | la forme d’entrée elle-même |
| Exemple | référence sans cible, composant sans builder | `findings` qui n’est pas un tableau, `report` absent |
| Composition | possible, avec diagnostics | refusée |

Un document composé peut donc être incomplet sans être invalide (ADR-0008
§ 1.4) : I8 traite de ce cas, et de lui seul. Ce que I9 refuse est autre chose
— une entrée dont la forme n’est plus celle que les builders ont vocation à
recevoir. Composer malgré tout leur demanderait de traiter un domaine que la
campagne de durcissement leur a précisément retiré.

## Conséquences

Deviennent interdits, sans révision de cet ADR :

- passer les données source au renderer, sous quelque forme que ce soit ;
- construire un index de libellés dans la couche de rendu ;
- écrire un identifiant technique dans un document produit ;
- trier, regrouper ou filtrer des instances pendant le rendu ;
- stocker un libellé français dans un payload ou dans les métadonnées métier ;
- appeler un schéma de composant ailleurs qu'à la frontière d'entrée ;
- fondre les diagnostics métier dans `Document.diagnostics` : on ne saurait
  plus distinguer un trou du moteur d'un défaut du rapport.

Restent ouverts et non contraints par cet ADR :

- l’ajout de renderers (HTML, PDF) : ils consomment le même IR et le même
  contexte, et sont soumis aux mêmes invariants ;
- les thèmes graphiques, internes à la couche de rendu ;
- les blocs narratifs, aujourd’hui sans contrat, déclarés fragments racine
  (ADR-0010) : leur contenu ne peut donc pas fermer la frontière ;
- la génération du JSON source, y compris par un modèle de langage : elle se
  situe strictement en amont de la chaîne, et n’en modifie aucun maillon.

## Vérification

Les invariants sont tenus par des tests, pas seulement par convention :

- I1 et I2 — le contexte est comparé aux instances composées
  (`test_render_context_is_derived_from_the_ir_instances`) ;
- I4 — absence des identifiants dans le DOCX et diagnostic explicite
  (`test_finding_renders_evidence_titles_never_ids`,
  `test_risk_unknown_reference_is_not_displayed`,
  `test_unresolved_reference_is_diagnosed_not_crashed`) ;
- I5 — payload anglais et document français dans le même test
  (`test_enumerations_are_english_in_the_ir_and_french_in_the_docx`) ;
- I6 — ordre source conservé malgré un horodatage ou une priorité qui
  inviteraient à trier (`test_timeline_is_composed_in_source_order`,
  `test_recommendation_order_follows_the_source`) ;
- I7 — absence de titre de partie commun aux occurrences
  (`test_findings_are_rendered_independently`) ;
- I8 — composant inconnu ignoré sans exception
  (`test_unsupported_component_is_skipped_not_crashed`) ;
- I9 — écart de contrat bloquant et défaut métier non bloquant, prouvés dans
  les deux sens (`test_a_contract_break_stops_the_composition`,
  `test_a_business_defect_still_composes`), la séparation des deux natures de
  diagnostic (`test_the_two_natures_of_diagnostic_stay_apart`), et l'absence
  d'appel aux schémas hors de la frontière
  (`test_the_contracts_are_consumed_at_the_boundary_only`,
  `test_compose_document_stays_unguarded_below_the_boundary`).

## Notes

Le porteur du `RenderContext` est aujourd’hui `Document.metadata`, sous une clé
namespacée. Un champ dédié dans le dataclass `Document` reste possible ; il
n’apporterait pour l’instant aucun bénéfice concret et n’est pas requis par les
invariants ci-dessus.
