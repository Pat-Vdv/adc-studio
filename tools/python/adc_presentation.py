"""Présentation des diagnostics d'une source, pour une ligne de commande.

Le moteur produit des diagnostics techniques ; cette couche décide seulement de
leur **présentation**. Elle ne valide rien, ne recompose rien, et n'ajoute
aucune information : elle range et elle nomme.

Deux natures se cachent dans `source_diagnostics`, et les annoncer ensemble
induirait en erreur :

- un **nœud de la source absent** est une section qui reste à rédiger. C'est
  l'état normal d'une mission neuve, pas un défaut ;
- tout le reste — référence inconnue, identifiant dupliqué, valeur inattendue —
  est un défaut d'un contenu qui existe déjà.

Ce qu'un nœud absent n'autorise pas à dire : **combien** d'éléments il devrait
porter. Le moteur sait qu'il manque `findings`, jamais qu'il en faudrait trois.
Annoncer un décompte inventerait une information, ce que toute la chaîne
s'interdit.

Le libellé d'une section est le nom du nœud lui-même, mis en forme — jamais un
intitulé rédigé ici. « Executive summary » se lit dans `$.executive_summary` ;
il n'y a rien à traduire ni à embellir, et le lecteur peut retrouver le champ.
"""
from __future__ import annotations

import adc_contracts
from adc_diagnostics import ValidationDiagnostic

MISSING = "required_field_missing"


def _root_node(path: str) -> str | None:
    """Nom du nœud si le chemin désigne la racine d'un nœud, sinon rien.

    `$.findings` en désigne un ; `$.findings[0].title` non — celui-là parle du
    contenu d'une section présente.
    """
    if not path.startswith("$.") or path == "$":
        return None
    node = path[2:]
    return node if node.isidentifier() else None


def _is_section(node: str) -> bool:
    """Un nœud est une section si la table des fragments le déclare.

    `schema_version` n'y figure pas : ce n'est le fragment de personne
    (ADR-0010), donc rien qu'un rédacteur puisse écrire. Le décider ici par une
    liste réécrite à la main dériverait de la table à la première évolution.
    """
    return any(
        fragment.path == node for fragment in adc_contracts.INCIDENT_REPORT_FRAGMENTS.values()
    )


def missing_sections(diagnostics: tuple[ValidationDiagnostic, ...]) -> tuple[str, ...]:
    """Sections absentes, dans l'ordre où la source les déclare attendues."""
    sections = []
    for diagnostic in diagnostics:
        if diagnostic.code != MISSING:
            continue
        node = _root_node(diagnostic.path)
        if node and _is_section(node) and node not in sections:
            sections.append(node)
    return tuple(sections)


def defects(
    diagnostics: tuple[ValidationDiagnostic, ...]
) -> tuple[ValidationDiagnostic, ...]:
    """Tout ce qui n'est pas une section absente : des contenus fautifs."""
    absent = set(missing_sections(diagnostics))
    return tuple(
        diagnostic
        for diagnostic in diagnostics
        if not (diagnostic.code == MISSING and _root_node(diagnostic.path) in absent)
    )


def label(node: str) -> str:
    """Libellé d'une section : son propre nom, rendu lisible."""
    return node.replace("_", " ").capitalize()


def source_lines(diagnostics: tuple[ValidationDiagnostic, ...]) -> tuple[str, ...]:
    """Lignes prêtes à afficher, ou rien si la source ne présente aucun écart."""
    if not diagnostics:
        return ()
    lines: list[str] = []
    sections = missing_sections(diagnostics)
    if sections:
        lines.append("Le rapport est incomplet.")
        lines.append("")
        lines.append("Sections restant à rédiger :")
        lines += [f"  • {label(node)}" for node in sections]
    remaining = defects(diagnostics)
    if remaining:
        if lines:
            lines.append("")
        lines.append("Défauts de la source :")
        lines += [f"  - {diagnostic}" for diagnostic in remaining]
    return tuple(lines)
