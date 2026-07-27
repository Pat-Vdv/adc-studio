# ADC Studio — Roadmap

## Vision

ADC Studio fournit un système documentaire versionné permettant de composer,
valider et produire des livrables professionnels cohérents à partir de profils,
de composants réutilisables et d’une identité graphique centralisée.

## Livré

### Fondation

- dépôt et conventions de projet ;
- identité graphique et design tokens ;
- décisions d’architecture ;
- structure documentaire initiale.

### Bibliothèque documentaire

- composants de rapport ;
- métadonnées et règles de validation ;
- profils documentaires ;
- rapports de référence ;
- gold standard.

### Framework Word

- modèle Word versionné ;
- styles réutilisables ;
- composants visuels ;
- génération reproductible ;
- exemple de rapport.

### Espace de production client

- création guidée des rapports ;
- métadonnées de rapport ;
- arborescence client et annuelle ;
- exclusion des données client du dépôt Git.

## Sprint 010 — Document Composition Model

### P10.0 — Assainissement du dépôt

- supprimer les identifiants de composants dupliqués ;
- distinguer l’outillage actif des archives de sprint ;
- centraliser les feuilles de route et changelogs ;
- documenter les conventions de structure.

### P10.1 — Modèle conceptuel

- définir Document, Composition, Component, Profile et Renderer ;
- formaliser les invariants ;
- rédiger ADR-0008.

### P10.2 — Schéma de composition

- créer le schéma JSON canonique ;
- définir les métadonnées et sections ;
- versionner le format.

### P10.3 — Catalogue de composants

- découvrir les composants disponibles ;
- garantir l’unicité des identifiants ;
- vérifier leur état et leur compatibilité.

### P10.4 — Résolution des profils

- charger un profil documentaire ;
- résoudre les composants demandés ;
- appliquer les valeurs par défaut.

### P10.5 — Validation

- validation structurelle ;
- validation sémantique ;
- contrôle des composants et profils référencés ;
- messages d’erreur exploitables.

### P10.6 — Document Model

- produire une représentation intermédiaire indépendante du format ;
- séparer composition et rendu ;
- conserver la provenance des données.

### P10.7 — Render Pipeline

- préparer les renderers Word, PDF et HTML ;
- garantir un comportement déterministe ;
- séparer les règles documentaires des contraintes de format.

### P10.8 — Tests

- tests des schémas ;
- tests du catalogue ;
- tests des profils ;
- tests de composition ;
- tests de non-régression.

### P10.9 — Documentation

- guide de composition ;
- guide de création des composants ;
- guide de création des profils ;
- exemples validés.

## Après le Sprint 010

- renderer Word fondé sur le Document Model ;
- renderer HTML ;
- export PDF contrôlé ;
- interface de composition ;
- intégration avec des sources externes ;
- automatisation de la revue qualité.

## Objectif v1.0

Une version stable d’ADC Studio capable de produire un rapport complet à partir :

- d’un profil documentaire ;
- d’une composition déclarative ;
- de composants versionnés ;
- de données structurées ;
- d’un pipeline de validation et de rendu reproductible.