# ADC Studio — Component Catalog

Ce catalogue décrit les composants documentaires officiels du framework.

> Les fichiers `components/*/metadata.yaml` constituent la source de vérité.
> Ce catalogue est une projection documentaire de ces métadonnées.

## Index

| ID | Composant | Version | Statut |
|---|---|---:|---|
| C-001 | Cover | 1.0-draft | 🟡 Draft |
| C-002 | Identity Page | 1.0 | 🟢 Stable |
| C-003 | Executive Summary | 1.0-draft | 🟡 Draft |
| C-004 | Finding | 1.0-draft | 🟡 Draft |
| C-005 | Recommendation | 1.0-draft | 🟡 Draft |
| C-006 | Risk | 1.0-draft | 🟡 Draft |
| C-007 | Decision | 1.0-draft | 🟡 Draft |
| C-008 | Timeline | 1.0-draft | 🟡 Draft |
| C-009 | Environment | 1.0-draft | 🟡 Draft |
| C-010 | Evidence | 1.0-draft | 🟡 Draft |
| C-011 | Incident Context | 1.0-draft | 🟡 Draft |
| C-012 | Investigation | 1.0-draft | 🟡 Draft |
| C-013 | Probable Cause | 1.0-draft | 🟡 Draft |
---

## C-001 — Cover

- **Version :** 1.0-draft
- **Statut :** 🟡 Draft 
- **Objectif :** identifier immédiatement le document, le client, le sujet, la version et le niveau de confidentialité.
- **Quand l’utiliser :** pour tout livrable client formel.
- **Quand ne pas l’utiliser :** pour une note interne courte ou un brouillon de travail.
- **Composition :** logo, type de document, titre, sous-titre, client, auteur, date, version, confidentialité.
- **Règle :** la couverture ne porte ni en-tête ni pied de page standard.

## C-002 — Identity Page

- **Version :** 1.0
- **Statut :** 🟢 Stable
- **Objectif :** centraliser les métadonnées du document.
- **Composition :** références, historique des versions, validation, diffusion, contacts.
- **Règle :** aucune information de fond ne doit être placée sur cette page.

## C-003 — Executive Summary

- **Version :** 1.0-draft
- **Statut :** 🟡 Draft
- **Objectif :** permettre à un décideur de comprendre le contexte, le résultat et les décisions requises sans lire tout le rapport.
- **Structure :** contexte, objectif, résultat principal, impact, décision attendue.
- **À éviter :** les détails de diagnostic et les extraits de journaux.

## C-004 — Finding

- **Version :** 1.0-draft
- **Statut :** 🟡 Draft
- **Objectif :** consigner un fait technique vérifiable.
- **Structure :** identifiant, titre, observation, impact, preuve, conclusion.
- **Règle :** un constat ne doit pas être formulé comme une recommandation.

## C-005 — Recommendation

- **Version :** 1.0-draft 
- **Statut :** 🟡 Draft
- **Objectif :** proposer une action reliée à un ou plusieurs constats.
- **Structure :** identifiant, priorité, effort, action, bénéfice, échéance, responsable éventuel.
- **Règle :** toute recommandation doit être actionnable et justifiée.

## C-006 — Risk

- **Version :** 1.0-draft
- **Statut :** 🟡 Draft
- **Objectif :** formaliser une menace, sa probabilité, son impact et les mesures prévues.
- **Structure :** description, probabilité, impact, niveau, traitement, statut.
- **À définir :** matrice de criticité officielle ADC Studio.

## C-007 — Decision

- **Version :** 1.0-draft
- **Statut :** 🟡 Draft
- **Objectif :** tracer une décision, sa justification, son propriétaire et sa date.
- **Structure :** décision, contexte, justification, décideur, échéance, conséquences.

## C-008 — Timeline

- **Version :** 1.0-draft
- **Statut :** 🟡 Draft
- **Objectif :** présenter chronologiquement les événements d’une intervention ou d’un incident.
- **Structure :** date/heure, événement, observation, référence éventuelle.
- **À valider :** rendu sur plusieurs pages et comportement avec des événements longs.

## C-009 — Environment

- **Version :** 1.0-draft
- **Statut :** 🟡 Draft
- **Objectif :** décrire de manière compacte l’environnement technique concerné.
- **Structure :** catégorie, élément, valeur, commentaire.
- **Exemples :** OS, SQL Server, mémoire, CPU, stockage, réseau, versions applicatives.

## C-010 — Evidence

- **Version :** 1.0-draft
- **Statut :** 🟡 Draft
- **Objectif :** enregistrer une preuve exploitable et traçable.
- **Structure :** identifiant, description, origine, date, référence, intégrité éventuelle.
- **Règle :** une preuve doit être distinguée de l’interprétation qui en est faite.

## C-011 — Incident Context

- **Version :** 1.0-draft
- **Statut :** 🟡 Draft
- **Objectif :** décrire les circonstances de l'incident, son déclencheur et son périmètre.
- **Structure :** description, déclencheur, périmètre, statut.
- **Règle :** le contexte décrit des circonstances, jamais une cause ou une conclusion.
- **Origine :** bloc narratif promu au catalogue par ADR-0013.

## C-012 — Investigation

- **Version :** 1.0-draft
- **Statut :** 🟡 Draft
- **Objectif :** consigner un travail d'investigation : ce qui a été cherché, comment, et ce que la recherche a donné.
- **Structure :** identifiant, intitulé, description, résultat.
- **Règle :** seul l'identifiant est requis — il conditionne l'existence de l'occurrence.
- **Origine :** bloc narratif promu au catalogue par ADR-0013.

## C-013 — Probable Cause

- **Version :** 1.0-draft
- **Statut :** 🟡 Draft
- **Objectif :** énoncer la cause probable, son niveau de confiance et les constats qui l'appuient.
- **Structure :** énoncé, confiance, constats à l'appui.
- **Règle :** une cause probable est une hypothèse argumentée, jamais un fait établi.
- **Origine :** bloc narratif promu au catalogue par ADR-0013.

---

## Discipline rédactionnelle transversale

ADC Studio sépare explicitement :

1. **Fait observé** — élément vérifiable ;
2. **Analyse** — interprétation technique argumentée ;
3. **Recommandation** — action proposée.

Cette séparation évite de présenter une hypothèse comme un fait ou une action comme une conclusion déjà acquise.
