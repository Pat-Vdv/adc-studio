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
  - C-004-finding
  - C-007-decision
  - C-005-recommendation
  - C-006-risk
  - C-010-evidence
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


def _entry_by_id(raw: Any, instance_id: str) -> dict[str, Any]:
    """Entrée source d'un composant répétable, retrouvée par son identifiant.

    Introuvable, elle donne un dictionnaire vide : le builder produit alors un
    payload aux champs vides plutôt qu'une exception.
    """
    if not isinstance(raw, list):
        return {}
    return next(
        (item for item in raw if isinstance(item, dict) and item.get("id") == instance_id),
        {},
    )


def _build_finding(data: dict[str, Any], instance_id: str) -> dict[str, Any]:
    """Constat : l'occurrence dont l'identifiant est `instance_id`.

    Le payload ne porte que les `evidence_ids` : les identifiants restent les
    clés de liaison internes du modèle, leur libellé lisible relève du rendu.
    """
    source = _entry_by_id(data.get("findings"), instance_id)
    evidence_ids = source.get("evidence_ids")
    return {
        "id": source.get("id"),
        "title": source.get("title"),
        "severity": source.get("severity"),
        "observation": _paragraphs(source.get("observation")),
        "impact": _paragraphs(source.get("impact")),
        "analysis": _paragraphs(source.get("analysis")),
        "evidence_ids": tuple(evidence_ids) if isinstance(evidence_ids, list) else (),
    }


def _build_decision(data: dict[str, Any], instance_id: str) -> dict[str, Any]:
    """Mesure prise : l'occurrence de `actions_taken` portant `instance_id`.

    Le statut est repris tel quel, dans sa valeur canonique : ni traduit, ni
    déduit d'une date ou d'un résultat.
    """
    source = _entry_by_id(data.get("actions_taken"), instance_id)
    return {
        "id": source.get("id"),
        "title": source.get("title"),
        "status": source.get("status"),
        "description": _paragraphs(source.get("description")),
    }


def _build_recommendation(data: dict[str, Any], instance_id: str) -> dict[str, Any]:
    """Recommandation : l'occurrence de `recommendations` portant `instance_id`.

    La priorité reste dans sa valeur canonique anglaise : la traduction est une
    affaire de rendu, jamais de modèle. Les constats liés sont conservés comme
    identifiants, à l'image des preuves du constat.
    """
    source = _entry_by_id(data.get("recommendations"), instance_id)
    related = source.get("related_finding_ids")
    return {
        "id": source.get("id"),
        "title": source.get("title"),
        "priority": source.get("priority"),
        "description": _paragraphs(source.get("description")),
        "rationale": _paragraphs(source.get("rationale")),
        "related_finding_ids": tuple(related) if isinstance(related, list) else (),
    }


def _build_risk(data: dict[str, Any], instance_id: str) -> dict[str, Any]:
    """Risque : l'occurrence de `risks` portant `instance_id`.

    Le niveau garde sa valeur canonique anglaise et les traitements prévus
    restent des identifiants de recommandations.
    """
    source = _entry_by_id(data.get("risks"), instance_id)
    mitigations = source.get("mitigation_recommendation_ids")
    return {
        "id": source.get("id"),
        "title": source.get("title"),
        "level": source.get("level"),
        "description": _paragraphs(source.get("description")),
        "mitigation_recommendation_ids": (
            tuple(mitigations) if isinstance(mitigations, list) else ()
        ),
    }


def _build_evidence(data: dict[str, Any], instance_id: str) -> dict[str, Any]:
    """Preuve : l'occurrence de `evidence` portant `instance_id`.

    Nature, origine et contenu sont repris tels que déclarés : rien n'est
    déduit, et la preuve n'emporte aucune interprétation.
    """
    source = _entry_by_id(data.get("evidence"), instance_id)
    return {
        "id": source.get("id"),
        "title": source.get("title"),
        "kind": source.get("kind"),
        "source": source.get("source"),
        "description": _paragraphs(source.get("description")),
        "content": _paragraphs(source.get("content")),
    }


# Composant cible d'une référence -> index de libellés qu'il alimente.
_TITLE_INDEXES: dict[str, str] = {
    "C-010-evidence": "evidence_titles",
    "C-004-finding": "finding_titles",
    "C-005-recommendation": "recommendation_titles",
}


def _render_context(instances: list[ComponentInstance]) -> dict[str, Any]:
    """Index de présentation, au sens du contexte de rendu d'ADR-0008.

    Les libellés sont dérivés des instances déjà composées, jamais relus dans
    la source : la chaîne reste source -> composition -> IR -> contexte de
    rendu -> DOCX, sans information parallèle extraite du JSON.
    """
    context: dict[str, Any] = {name: {} for name in _TITLE_INDEXES.values()}
    for instance in instances:
        index = _TITLE_INDEXES.get(instance.component_id)
        if index is None:
            continue
        identifier = instance.payload.get("id")
        title = instance.payload.get("title")
        if identifier and title:
            context[index][identifier] = title
    return context


# Champ de référence d'un payload -> index de libellés qui doit le résoudre.
_REFERENCE_INDEXES: dict[str, str] = {
    "evidence_ids": "evidence_titles",
    "related_finding_ids": "finding_titles",
    "mitigation_recommendation_ids": "recommendation_titles",
}


def _unresolved_references(
    payload: dict[str, Any], context: dict[str, Any]
) -> tuple[str, ...]:
    """Références dont aucun libellé n'est disponible pour la présentation.

    Le renderer n'affichant jamais un identifiant technique, ces références
    seraient invisibles dans le document : elles sortent donc en diagnostic
    plutôt que d'être silencieusement perdues.
    """
    unresolved: list[str] = []
    for field, index in _REFERENCE_INDEXES.items():
        titles = context.get(index) or {}
        unresolved += [ref for ref in payload.get(field) or () if ref not in titles]
    return tuple(unresolved)


_BUILDERS: dict[str, Builder] = {
    "C-001-cover": _build_cover,
    "C-002-identity-page": _build_identity_page,
    "C-003-executive-summary": _build_executive_summary,
    "C-009-environment": _build_environment,
    "C-008-timeline": _build_timeline,
    "C-004-finding": _build_finding,
    "C-007-decision": _build_decision,
    "C-005-recommendation": _build_recommendation,
    "C-006-risk": _build_risk,
    "C-010-evidence": _build_evidence,
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
        instances.append(ComponentInstance(component_id, instance_id, builder(data, instance_id)))

    # Le contexte se déduit des instances : les références ne sont donc
    # confrontées qu'à ce que l'IR contient réellement.
    context = _render_context(instances)
    for instance in instances:
        diagnostics += [
            f"référence non résolue: {instance.component_id} :: {instance.instance_id} -> {ref}"
            for ref in _unresolved_references(instance.payload, context)
        ]

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
            # Index techniques destinés au renderer, isolés des métadonnées
            # éditoriales du rapport (ADR-0008 : contexte nécessaire au rendu).
            "render_context": context,
        },
        components=tuple(instances),
        diagnostics=tuple(diagnostics),
    )
