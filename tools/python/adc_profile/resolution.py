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

**La présence d'un bloc suit celle de son fragment déclaré.** Un fragment racine
— la source entière — est toujours présent ; un fragment nommé ne l'est que si
la source porte son nœud. Cette règle vaut pour tous les blocs uniques, sans
exception : deux d'entre eux y échappaient par héritage, faute qu'une règle ait
jamais été écrite, ce qui donnait deux régimes de présence dont un seul était
attesté.

La présence d'un nœud est **structurelle**, jamais booléenne (ADR-0012, G4) : un
nœud présent mais vide est présent, et porte l'occurrence que le profil attend.
Le juger par la véracité de sa valeur confondrait cinq états — clé absente,
`None`, objet vide, liste vide, chaîne vide — et ferait dire à la cardinalité ce
que la présence a déjà dit autrement, en contredisant le validateur métier qui en
est propriétaire. Qu'un contenu vide soit recevable ne se décide pas ici.

Ce module ne connaît ni la composition, ni le rendu, ni la validation : c'est
ce qui permet à plusieurs outils de partager la même description de l'ordre.
"""
from __future__ import annotations

from typing import Any

from .contract import Profile, ProfileEntry

# Bloc à occurrence unique -> nœud source dont dépend sa présence.
#
# `None` désigne le **fragment racine** : le bloc consomme la source entière,
# qui est toujours présente. Ce n'est pas une exception à la règle, c'en est
# l'application — la présence d'un bloc suit celle de son fragment déclaré.
_SINGLE_OCCURRENCE_SOURCES: dict[str, str | None] = {
    "cover": None,
    "identity": None,
    "executive-summary": "executive_summary",
    "incident-context": "incident_context",
    "environment": "environment",
    "timeline": "timeline",
    "probable-cause": "probable_cause",
    "conclusion": "conclusion",
}

# Bloc répétable -> collection source qui porte ses occurrences.
_MULTIPLE_OCCURRENCE_SOURCES: dict[str, str] = {
    "C-012-investigation": "investigations",
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
        present = True if key is None else key in data
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
