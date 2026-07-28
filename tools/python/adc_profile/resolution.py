"""Résolution : profil + données -> liste ordonnée d'occurrences.

Le partage des responsabilités est strict :

- le **profil** déclare l'ordre, les cardinalités et le caractère obligatoire
  ou optionnel de chaque bloc ;
- la **source** détermine, via les tables ci-dessous, si un bloc produit zéro,
  une ou plusieurs occurrences ;
- la **résolution** ordonne les occurrences selon le profil et confronte leur
  nombre aux cardinalités déclarées.

Aucune occurrence n'est fabriquée pour satisfaire une cardinalité : un écart
produit un diagnostic, jamais un bloc vide.

Ce module ne connaît ni la composition, ni le rendu, ni la validation : c'est
ce qui permet à plusieurs outils de partager la même description de l'ordre.
"""
from __future__ import annotations

from typing import Any

from .contract import Profile, ProfileEntry

# Bloc à occurrence unique -> clé source dont dépend sa présence.
# `None` : le bloc est présent dès que le profil le déclare.
_SINGLE_OCCURRENCE_SOURCES: dict[str, str | None] = {
    "cover": None,
    "identity": None,
    "executive-summary": None,
    "incident-context": None,
    "environment": None,
    "timeline": "timeline",
    "probable-cause": "probable_cause",
    "conclusion": None,
}

# Bloc répétable -> collection source qui porte ses occurrences.
_MULTIPLE_OCCURRENCE_SOURCES: dict[str, str] = {
    "narrative-investigation": "investigations",
    "C-004-finding": "findings",
    "C-007-decision": "actions_taken",
    "C-005-recommendation": "recommendations",
    "C-006-risk": "risks",
    "C-010-evidence": "evidence",
}


def _occurrences(entry: ProfileEntry, data: dict[str, Any]) -> tuple[tuple[str, ...], str | None]:
    """Identifiants d'occurrence produits par la source pour ce bloc.

    Retourne aussi un diagnostic quand le bloc déclaré par le profil n'a aucune
    source connue : mieux vaut le signaler que l'omettre en silence.
    """
    if entry.instance_id is not None:
        if entry.instance_id not in _SINGLE_OCCURRENCE_SOURCES:
            return (), f"source d'occurrences inconnue: {entry.component_id} :: {entry.instance_id}"
        key = _SINGLE_OCCURRENCE_SOURCES[entry.instance_id]
        present = True if key is None else bool(data.get(key))
        return ((entry.instance_id,) if present else ()), None

    if entry.component_id not in _MULTIPLE_OCCURRENCE_SOURCES:
        return (), f"source d'occurrences inconnue: {entry.component_id}"

    collection = data.get(_MULTIPLE_OCCURRENCE_SOURCES[entry.component_id], [])
    if not isinstance(collection, list):
        return (), None
    return (
        tuple(item["id"] for item in collection if isinstance(item, dict) and item.get("id")),
        None,
    )


def _cardinality_diagnostic(entry: ProfileEntry, count: int) -> str | None:
    if count < entry.minimum:
        return (
            f"cardinalité non respectée: {entry.component_id} :: "
            f"{entry.minimum} occurrence(s) au minimum, {count} obtenue(s)"
        )
    if entry.maximum is not None and count > entry.maximum:
        return (
            f"cardinalité non respectée: {entry.component_id} :: "
            f"{entry.maximum} occurrence(s) au maximum, {count} obtenue(s)"
        )
    return None


def resolve(
    data: dict[str, Any], profile: Profile
) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...]]:
    """Occurrences ordonnées selon le profil, et diagnostics de résolution."""
    blocks: list[tuple[str, str]] = []
    diagnostics: list[str] = []

    for entry in profile.entries:
        instance_ids, missing_source = _occurrences(entry, data)
        if missing_source:
            diagnostics.append(missing_source)
        blocks += [(entry.component_id, instance_id) for instance_id in instance_ids]

        cardinality = _cardinality_diagnostic(entry, len(instance_ids))
        if cardinality:
            diagnostics.append(cardinality)

    return tuple(blocks), tuple(diagnostics)
