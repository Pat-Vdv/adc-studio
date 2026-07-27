# ADR-0002 - Word Framework

Status: Accepted  
Date: 2026-07-27

## Contexte

Les rapports A.D.C. doivent présenter une identité homogène sans dépendre du copier-coller d’anciens documents.

## Décision

Adopter un modèle Word versionné comme source unique des styles et composants de rapport. Le format `.dotx` est le livrable principal ; une version `.docx` reste fournie pour inspection et compatibilité.

## Principes

- styles nommés plutôt que mise en forme locale ;
- couverture, en-têtes, pieds de page et champs communs ;
- composants sobres et accessibles ;
- aucune donnée client dans le modèle ;
- exemples séparés du modèle de production ;
- contrôle visuel obligatoire avant publication.

## Conséquences

Les changements d’identité visuelle sont centralisés. Les anciens rapports ne sont pas modifiés automatiquement. Toute adaptation client spécifique doit rester une extension explicite et documentée.
