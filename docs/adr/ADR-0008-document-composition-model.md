# ADR-0008 — Document Composition Model

## Statut

Proposé

## Date

2026-07-28

## Contexte

ADC Studio doit produire plusieurs familles de rapports à partir de composants
documentaires réutilisables.

Le projet possède déjà :

- une bibliothèque de composants ;
- des profils de rapports ;
- une identité graphique ;
- des modèles Word ;
- des rapports de référence ;
- des outils de génération.

Cependant, le modèle qui relie ces éléments n’est pas encore formalisé.

Sans modèle de composition explicite, les risques sont les suivants :

- logique métier mélangée au rendu Word ;
- ordre des composants codé en dur ;
- dépendance directe entre les données source et le format de sortie ;
- difficulté à produire plusieurs formats ;
- règles de validation dispersées ;
- impossibilité de tester la composition indépendamment du rendu.

## Décision

ADC Studio adopte un modèle documentaire intermédiaire composé de quatre
concepts principaux :

1. `Document`
2. `Component`
3. `Profile`
4. `Renderer`

Le moteur de composition construit un `Document` à partir d’un `Profile`, de
données d’entrée et d’une bibliothèque de `Component`.

Le `Renderer` reçoit ensuite ce document composé et le matérialise dans un
format cible.

## 1. Document

Un `Document` représente le résultat logique d’une composition.

Il est indépendant du format de sortie.

Il contient au minimum :

- un identifiant ;
- un type de document ;
- un titre ;
- des métadonnées ;
- une liste ordonnée d’instances de composants ;
- les informations de contexte nécessaires au rendu ;
- les diagnostics produits pendant la composition.

Exemple conceptuel :

```yaml
document:
  id: report-2026-001
  type: sql_server_audit
  title: Audit SQL Server
  metadata:
    client: Soc01
    version: "1.0"
    confidentiality: Confidentiel
  components:
    - component_id: C-001-cover
      instance_id: cover
    - component_id: C-002-identity-page
      instance_id: identity
    - component_id: C-003-executive-summary
      instance_id: summary