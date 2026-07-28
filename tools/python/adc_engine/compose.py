"""Composition : données validées -> Document Model (IR).

Le moteur parcourt la résolution déterministe des composants et délègue, pour
chaque composant, la construction du payload à un *builder* dédié. Ajouter la
prise en charge d'un composant = ajouter un builder dans `_BUILDERS`. Un
composant résolu mais sans builder ne casse rien : il produit un diagnostic.

Développement incrémental (cas SQL Server Incident) — composants pris en charge :
  - C-001-cover
"""
from __future__ import annotations

from typing import Any, Callable

from .model import ComponentInstance, Document
from .resolve import resolve

# Un builder reçoit (data_source, instance_id) et retourne le payload de rendu.
Builder = Callable[[dict[str, Any], str], dict[str, Any]]


def _build_cover(data: dict[str, Any], instance_id: str) -> dict[str, Any]:
    report = data.get("report", {})
    client = data.get("client", {})
    return {
        "document_type": "Rapport d'incident",
        "title": report.get("title"),
        "subtitle": report.get("subtitle"),
        "client": client.get("name"),
        "author": report.get("author"),
        "date": report.get("date"),
        "version": report.get("version"),
        "reference": report.get("reference"),
        "confidentiality": report.get("confidentiality"),
    }


_BUILDERS: dict[str, Builder] = {
    "C-001-cover": _build_cover,
}


def compose_document(data: dict[str, Any]) -> Document:
    """Construit le Document (IR) à partir de la source validée."""
    report = data.get("report", {})
    client = data.get("client", {})

    instances: list[ComponentInstance] = []
    diagnostics: list[str] = []

    for component_id, instance_id in resolve(data):
        builder = _BUILDERS.get(component_id)
        if builder is None:
            diagnostics.append(f"builder manquant: {component_id} :: {instance_id}")
            continue
        payload = builder(data, instance_id)
        instances.append(ComponentInstance(component_id, instance_id, payload))

    return Document(
        id=report.get("id", ""),
        type="incident_report",
        title=report.get("title", ""),
        metadata={
            "client": client.get("name"),
            "reference": report.get("reference"),
            "version": report.get("version"),
            "date": report.get("date"),
            "confidentiality": report.get("confidentiality"),
            "language": report.get("language"),
        },
        components=tuple(instances),
        diagnostics=tuple(diagnostics),
    )
