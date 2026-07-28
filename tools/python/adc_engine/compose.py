"""Composition : données validées -> Document Model (IR).

Le moteur parcourt la résolution déterministe des composants et délègue, pour
chaque composant, la construction du payload à un *builder* dédié. Ajouter la
prise en charge d'un composant = ajouter un builder dans `_BUILDERS`. Un
composant résolu mais sans builder ne casse rien : il produit un diagnostic.

Développement incrémental (cas SQL Server Incident) — composants pris en charge :
  - C-001-cover
  - C-002-identity-page
  - C-003-executive-summary
  - C-009-environment
  - C-008-timeline
"""
from __future__ import annotations

from typing import Any, Callable

from .model import ComponentInstance, Document
from .resolve import resolve

# Un builder reçoit (data_source, instance_id) et retourne le payload de rendu.
Builder = Callable[[dict[str, Any], str], dict[str, Any]]


def _rows(raw: Any, fields: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
    """Normalise une liste d'objets source en lignes aux champs connus.

    Les entrées non conformes (non-dict) sont ignorées : le payload reste
    homogène et le rendu n'a aucune vérification défensive à faire.
    """
    if not isinstance(raw, list):
        return ()
    return tuple({f: item.get(f) for f in fields} for item in raw if isinstance(item, dict))


def _paragraphs(raw: Any) -> tuple[str, ...]:
    """Normalise un texte source en paragraphes.

    Une chaîne est découpée sur les lignes vides, une liste est reprise telle
    quelle. Les fragments vides disparaissent : au rendu, un champ absent et un
    champ vide se comportent identiquement.
    """
    if isinstance(raw, str):
        blocks = raw.split("\n\n")
    elif isinstance(raw, list):
        blocks = [item for item in raw if isinstance(item, str)]
    else:
        return ()
    return tuple(block.strip() for block in blocks if block.strip())


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


def _build_identity_page(data: dict[str, Any], instance_id: str) -> dict[str, Any]:
    """Identité documentaire : métadonnées, révisions, validations, diffusion.

    Les trois derniers blocs sont optionnels dans la source : absents, ils
    produisent un tuple vide et la section correspondante n'est pas rendue.
    """
    report = data.get("report", {})
    client = data.get("client", {})
    return {
        "heading": "Identité du document",
        "identification": {
            "id": report.get("id"),
            "reference": report.get("reference"),
            "title": report.get("title"),
            "client": client.get("name"),
            "author": report.get("author"),
            "version": report.get("version"),
            "date": report.get("date"),
            "language": report.get("language"),
            "confidentiality": report.get("confidentiality"),
        },
        "revisions": _rows(report.get("revisions"), ("version", "date", "author", "summary")),
        "validations": _rows(report.get("validations"), ("role", "name", "date")),
        "distribution": _rows(report.get("distribution"), ("name", "organisation", "role")),
    }


def _build_executive_summary(data: dict[str, Any], instance_id: str) -> dict[str, Any]:
    """Résumé exécutif : quatre volets narratifs, chacun en paragraphes.

    Un volet absent de la source produit un tuple vide ; c'est le rendu qui
    décide d'omettre la sous-section correspondante.
    """
    summary = data.get("executive_summary", {})
    if not isinstance(summary, dict):
        summary = {}
    return {
        "heading": "Résumé exécutif",
        "context": _paragraphs(summary.get("context")),
        "business_impact": _paragraphs(summary.get("business_impact")),
        "conclusion": _paragraphs(summary.get("conclusion")),
        "recommended_action": _paragraphs(summary.get("recommended_action")),
    }


def _build_environment(data: dict[str, Any], instance_id: str) -> dict[str, Any]:
    """Environnement technique : caractéristiques système et volumes de stockage.

    Les caractéristiques sont reprises telles quelles (aucune conversion
    d'unité, aucune valeur déduite) ; les volumes absents donnent un tuple vide.
    """
    environment = data.get("environment", {})
    if not isinstance(environment, dict):
        environment = {}
    return {
        "heading": "Environnement",
        "system": {
            "server_name": environment.get("server_name"),
            "operating_system": environment.get("operating_system"),
            "database_engine": environment.get("database_engine"),
            "database_engine_version": environment.get("database_engine_version"),
            "instance": environment.get("instance"),
            "primary_database": environment.get("primary_database"),
            "collation": environment.get("collation"),
            "cpu_logical_count": environment.get("cpu_logical_count"),
            "memory_gb": environment.get("memory_gb"),
        },
        "storage": _rows(environment.get("storage"), ("volume", "role", "allocation_unit_kb")),
    }


def _build_timeline(data: dict[str, Any], instance_id: str) -> dict[str, Any]:
    """Chronologie : une entrée par événement, dans l'ordre de la source.

    Aucun tri, aucune date déduite, aucun statut inféré : la chronologie rendue
    est exactement celle que la source déclare.
    """
    return {
        "heading": "Chronologie",
        "entries": _rows(data.get("timeline"), ("id", "timestamp", "title", "description")),
    }


_BUILDERS: dict[str, Builder] = {
    "C-001-cover": _build_cover,
    "C-002-identity-page": _build_identity_page,
    "C-003-executive-summary": _build_executive_summary,
    "C-009-environment": _build_environment,
    "C-008-timeline": _build_timeline,
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
