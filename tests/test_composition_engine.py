"""Tests du moteur de composition (Document Model / IR).

Développement incrémental — cas SQL Server Incident. Chaque composant pris en
charge ajoute ici une assertion ciblée.
"""
from __future__ import annotations

import json
from pathlib import Path

from adc_engine import ComponentInstance, Document, compose_document
from adc_engine.compose import incident_profile
from adc_profile import resolve

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "reference_reports" / "incident_report" / "data" / "sql_server_2014_incident.json"

# Volets du résumé exécutif, dans l'ordre attendu du composant C-003.
SUMMARY_SECTIONS = ("context", "business_impact", "conclusion", "recommended_action")


def _data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8-sig"))


def _component(doc, component_id: str) -> ComponentInstance:
    """Première instance d'un composant : robuste à l'insertion de blocs amont."""
    return next(c for c in doc.components if c.component_id == component_id)


def test_compose_returns_document():
    doc = compose_document(_data())
    assert isinstance(doc, Document)
    assert doc.id == "ADC-MECA-2026-SQL2014-001"
    assert doc.type == "incident_report"
    assert doc.metadata["client"] == "Soc01"


def test_cover_is_first_and_populated():
    doc = compose_document(_data())
    cover = doc.components[0]
    assert cover.component_id == "C-001-cover"
    assert cover.instance_id == "cover"
    assert cover.payload["title"] == "Investigation — Blocage SQL Server lors de DBCC CHECKDB"
    assert cover.payload["client"] == "Soc01"
    assert cover.payload["confidentiality"] == "Confidentiel"


def test_identity_page_follows_cover():
    doc = compose_document(_data())
    identity = doc.components[1]
    assert identity.component_id == "C-002-identity-page"
    assert identity.instance_id == "identity"
    identification = identity.payload["identification"]
    assert identification["id"] == "ADC-MECA-2026-SQL2014-001"
    assert identification["client"] == "Soc01"
    assert identification["language"] == "fr-BE"
    assert identification["confidentiality"] == "Confidentiel"


def test_identity_page_optional_blocks_are_empty_when_absent():
    # La source de référence ne porte ni révisions, ni validations, ni diffusion :
    # le payload reste homogène (tuples vides), sans clé manquante.
    identity = compose_document(_data()).components[1]
    assert identity.payload["revisions"] == ()
    assert identity.payload["validations"] == ()
    assert identity.payload["distribution"] == ()


def test_identity_page_reads_optional_blocks_when_present():
    data = _data()
    data["report"]["revisions"] = [
        {"version": "0.1-draft", "date": "2026-07-28", "author": "A.D.C. srl", "summary": "Création"},
        "entrée invalide ignorée",
    ]
    data["report"]["validations"] = [{"role": "Auteur", "name": "A.D.C. srl", "date": "2026-07-28"}]
    data["report"]["distribution"] = [{"name": "Soc01", "organisation": "Soc01", "role": "Client"}]
    identity = compose_document(data).components[1]
    assert identity.payload["revisions"] == (
        {"version": "0.1-draft", "date": "2026-07-28", "author": "A.D.C. srl", "summary": "Création"},
    )
    assert identity.payload["validations"][0]["role"] == "Auteur"
    assert identity.payload["distribution"][0]["name"] == "Soc01"


def test_executive_summary_follows_identity_page():
    doc = compose_document(_data())
    summary = doc.components[2]
    assert summary.component_id == "C-003-executive-summary"
    assert summary.instance_id == "executive-summary"
    assert summary.payload["heading"] == "Résumé exécutif"


def test_executive_summary_reads_every_section_from_source():
    # Volontairement indépendant du texte de la source : la rédaction du rapport
    # de référence est une évolution normale de la donnée, pas une régression.
    data = _data()
    source = data["executive_summary"]
    summary = compose_document(data).components[2]
    for key in SUMMARY_SECTIONS:
        blocks = summary.payload[key]
        assert blocks, f"volet '{key}' non lu depuis la source"
        assert all(isinstance(b, str) and b and b == b.strip() for b in blocks)
        # Aucun texte inventé : chaque paragraphe provient bien de la source.
        raw = source[key]
        haystack = "\n".join(raw) if isinstance(raw, list) else str(raw)
        assert all(b in haystack for b in blocks)


def test_executive_summary_splits_paragraphs():
    """Robustesse du builder, pas contrat (ADR-0010).

    La forme canonique d'un volet est une chaîne ; la liste est une tolérance
    d'implémentation, hors du contrat décrit par `schema.json`.
    """
    data = _data()
    data["executive_summary"]["context"] = "Premier paragraphe.\n\n  Second paragraphe.  \n\n\n"
    data["executive_summary"]["conclusion"] = ["Ligne A", "", "Ligne B"]
    summary = compose_document(data).components[2]
    assert summary.payload["context"] == ("Premier paragraphe.", "Second paragraphe.")
    assert summary.payload["conclusion"] == ("Ligne A", "Ligne B")


def test_executive_summary_missing_sections_are_empty():
    data = _data()
    data["executive_summary"] = {"context": "Seul volet renseigné."}
    summary = compose_document(data).components[2]
    assert summary.payload["context"] == ("Seul volet renseigné.",)
    assert summary.payload["business_impact"] == ()
    assert summary.payload["conclusion"] == ()
    assert summary.payload["recommended_action"] == ()


def test_environment_is_composed():
    doc = compose_document(_data())
    environment = _component(doc, "C-009-environment")
    assert environment.component_id == "C-009-environment"
    assert environment.instance_id == "environment"
    system = environment.payload["system"]
    assert system["server_name"] == "SRV-SQL-01"
    assert system["database_engine"] == "Microsoft SQL Server 2014 Standard"
    assert system["cpu_logical_count"] == 40  # valeur reprise telle quelle
    assert system["memory_gb"] == 64


def test_environment_storage_rows_are_normalized():
    environment = _component(compose_document(_data()), "C-009-environment")
    storage = environment.payload["storage"]
    assert [row["volume"] for row in storage] == ["C:", "D:", "E:", "I:"]
    assert all(set(row) == {"volume", "role", "allocation_unit_kb"} for row in storage)
    assert storage[1] == {"volume": "D:", "role": "SQL", "allocation_unit_kb": 64}
    assert storage[0]["allocation_unit_kb"] is None  # champ non renseigné, conservé


def test_environment_tolerates_missing_fields():
    data = _data()
    data["environment"] = {"server_name": "SRV-01"}
    environment = _component(compose_document(data), "C-009-environment")
    assert environment.payload["system"]["server_name"] == "SRV-01"
    assert environment.payload["system"]["collation"] is None
    assert environment.payload["storage"] == ()


def _timeline(doc) -> ComponentInstance:
    """Instance C-008 du document, localisée par son identifiant de composant."""
    return next(c for c in doc.components if c.component_id == "C-008-timeline")


def test_timeline_is_composed_in_source_order():
    data = _data()
    data["timeline"].append(
        {
            "id": "timeline-000",
            "timestamp": "2026-07-22",
            "title": "Signalement",
            "description": "Appel du client.",
        }
    )
    timeline = _timeline(compose_document(data))
    assert timeline.instance_id == "timeline"
    # Aucun tri : l'entrée ajoutée en fin de source reste en fin de payload,
    # bien que son horodatage soit antérieur.
    assert [e["timestamp"] for e in timeline.payload["entries"]] == ["2026-07-23", "2026-07-22"]
    assert timeline.payload["entries"][0] == {
        "id": "timeline-001",
        "timestamp": "2026-07-23",
        "title": "Sauvegardes préalables",
        "description": "Sauvegardes complètes et VERIFYONLY réalisés avant intervention.",
    }


def test_timeline_entries_have_homogeneous_fields():
    data = _data()
    data["timeline"] = [{"id": "t1", "title": "Sans horodatage"}, "entrée invalide ignorée"]
    entries = _timeline(compose_document(data)).payload["entries"]
    assert len(entries) == 1
    assert set(entries[0]) == {"id", "timestamp", "title", "description"}
    assert entries[0]["timestamp"] is None  # champ absent, jamais déduit


def test_timeline_absent_produces_no_instance():
    # La chronologie est optionnelle (0..1) : absente de la source, elle n'est
    # ni instanciée ni diagnostiquée.
    data = _data()
    data.pop("timeline")
    doc = compose_document(data)
    assert not any(c.component_id == "C-008-timeline" for c in doc.components)
    assert not any("C-008-timeline" in d for d in doc.diagnostics)


def _findings(doc) -> list[ComponentInstance]:
    return [c for c in doc.components if c.component_id == "C-004-finding"]


def test_finding_instance_matches_its_source_entry():
    data = _data()
    data["findings"].append(
        {
            "id": "finding-002",
            "title": "Second constat",
            "severity": "low",
            "observation": "Observation du second constat.",
            "impact": "Impact mineur.",
            "analysis": "Analyse du second constat.",
            "evidence_ids": [],
        }
    )
    findings = _findings(compose_document(data))
    # Une instance par constat, chacune alimentée par sa propre entrée source.
    assert [f.instance_id for f in findings] == ["finding-001", "finding-002"]
    second = findings[1].payload
    assert second["id"] == "finding-002"
    assert second["title"] == "Second constat"
    assert second["severity"] == "low"
    assert second["observation"] == ("Observation du second constat.",)


def test_finding_narrative_fields_are_paragraphs():
    data = _data()
    data["findings"][0]["observation"] = "Premier paragraphe.\n\nSecond paragraphe."
    payload = _findings(compose_document(data))[0].payload
    assert payload["observation"] == ("Premier paragraphe.", "Second paragraphe.")
    assert all(isinstance(b, str) for b in payload["analysis"])


def test_finding_payload_keeps_evidence_ids_only():
    # Le modèle relie par identifiant : aucun libellé de preuve n'est dupliqué
    # dans le payload du constat.
    payload = _findings(compose_document(_data()))[0].payload
    assert payload["evidence_ids"] == ("evidence-001",)
    assert "evidence_titles" not in payload
    assert not any("État et configuration" in str(v) for v in payload.values())


def test_evidence_titles_are_exposed_as_render_context():
    # Index technique namespacé : il ne se confond pas avec les métadonnées
    # éditoriales du rapport (client, référence, version…).
    doc = compose_document(_data())
    assert doc.metadata["render_context"]["evidence_titles"] == {
        "evidence-001": "État et configuration de l’environnement SQL"
    }
    assert "evidence_titles" not in doc.metadata


def _decisions(doc) -> list[ComponentInstance]:
    return [c for c in doc.components if c.component_id == "C-007-decision"]


def test_decision_instance_matches_its_source_entry():
    data = _data()
    data["actions_taken"].append(
        {
            "id": "decision-002",
            "title": "Seconde mesure",
            "description": "Description de la seconde mesure.",
            "status": "in_progress",
        }
    )
    decisions = _decisions(compose_document(data))
    assert [d.instance_id for d in decisions] == ["decision-001", "decision-002"]
    first = decisions[0].payload
    source = data["actions_taken"][0]
    assert first["id"] == source["id"]
    assert first["title"] == source["title"]
    assert first["description"] == (source["description"],)
    assert decisions[1].payload["status"] == "in_progress"


def test_decision_status_is_kept_canonical():
    # Valeur de la source, sans traduction ni statut déduit d'une date.
    payload = _decisions(compose_document(_data()))[0].payload
    assert payload["status"] == "completed"


def test_decision_tolerates_missing_fields():
    data = _data()
    data["actions_taken"] = [{"id": "decision-001", "title": "Mesure sans détail"}]
    payload = _decisions(compose_document(data))[0].payload
    assert payload["title"] == "Mesure sans détail"
    assert payload["status"] is None  # jamais déduit
    assert payload["description"] == ()


def _recommendations(doc) -> list[ComponentInstance]:
    return [c for c in doc.components if c.component_id == "C-005-recommendation"]


def test_recommendation_instance_matches_its_source_entry():
    data = _data()
    data["recommendations"].append(
        {
            "id": "recommendation-002",
            "title": "Seconde recommandation",
            "priority": "low",
            "description": "Description de la seconde recommandation.",
            "rationale": "Justification de la seconde recommandation.",
            "related_finding_ids": [],
        }
    )
    recommendations = _recommendations(compose_document(data))
    assert [r.instance_id for r in recommendations] == [
        "recommendation-001",
        "recommendation-002",
    ]
    first = recommendations[0].payload
    source = data["recommendations"][0]
    assert first["id"] == source["id"]
    assert first["title"] == source["title"]
    assert first["description"] == (source["description"],)
    assert first["rationale"] == (source["rationale"],)


def test_recommendation_priority_stays_canonical_in_the_ir():
    # Règle du moteur : anglais canonique dans l'IR, français uniquement au rendu.
    payload = _recommendations(compose_document(_data()))[0].payload
    assert payload["priority"] == "high"
    assert "Élevée" not in str(payload)


def test_recommendation_keeps_related_finding_ids_only():
    payload = _recommendations(compose_document(_data()))[0].payload
    assert payload["related_finding_ids"] == ("finding-001",)
    assert not any("Blocage observé" in str(v) for v in payload.values())


def test_recommendation_order_follows_the_source():
    data = _data()
    data["recommendations"].append(
        {
            "id": "recommendation-002",
            "title": "Priorité critique déclarée en second",
            "priority": "critical",
            "description": "…",
            "rationale": "…",
            "related_finding_ids": [],
        }
    )
    # Aucun tri par priorité : l'ordre de la source est conservé.
    priorities = [r.payload["priority"] for r in _recommendations(compose_document(data))]
    assert priorities == ["high", "critical"]


def test_recommendation_tolerates_missing_fields():
    data = _data()
    data["recommendations"] = [{"id": "recommendation-001", "title": "Sans détail"}]
    payload = _recommendations(compose_document(data))[0].payload
    assert payload["priority"] is None  # jamais déduite
    assert payload["description"] == ()
    assert payload["rationale"] == ()
    assert payload["related_finding_ids"] == ()


def test_finding_titles_are_exposed_as_render_context():
    doc = compose_document(_data())
    assert doc.metadata["render_context"]["finding_titles"] == {
        "finding-001": "Blocage observé pendant DBCC CHECKDB"
    }


def _risks(doc) -> list[ComponentInstance]:
    return [c for c in doc.components if c.component_id == "C-006-risk"]


def test_risk_instance_matches_its_source_entry():
    data = _data()
    data["risks"].append(
        {
            "id": "risk-002",
            "title": "Second risque",
            "level": "critical",
            "description": "Description du second risque.",
            "mitigation_recommendation_ids": [],
        }
    )
    risks = _risks(compose_document(data))
    assert [r.instance_id for r in risks] == ["risk-001", "risk-002"]
    first = risks[0].payload
    source = data["risks"][0]
    assert first["id"] == source["id"]
    assert first["title"] == source["title"]
    assert first["description"] == (source["description"],)
    # Aucun tri : le risque « critical » déclaré en second y reste.
    assert [r.payload["level"] for r in risks] == ["high", "critical"]


def test_risk_level_stays_canonical_in_the_ir():
    payload = _risks(compose_document(_data()))[0].payload
    assert payload["level"] == "high"
    assert "Élevée" not in str(payload)


def test_risk_keeps_mitigation_ids_only():
    payload = _risks(compose_document(_data()))[0].payload
    assert payload["mitigation_recommendation_ids"] == ("recommendation-001",)
    assert not any("Exécuter DBCC CHECKDB" in str(v) for v in payload.values())


def test_risk_tolerates_missing_fields():
    data = _data()
    data["risks"] = [{"id": "risk-001", "title": "Risque sans détail"}]
    payload = _risks(compose_document(data))[0].payload
    assert payload["level"] is None  # jamais déduit
    assert payload["description"] == ()
    assert payload["mitigation_recommendation_ids"] == ()


def test_recommendation_titles_are_exposed_as_render_context():
    doc = compose_document(_data())
    assert doc.metadata["render_context"]["recommendation_titles"] == {
        "recommendation-001": "Exécuter DBCC CHECKDB hors production"
    }


def test_render_context_is_derived_from_the_ir_instances():
    # Invariant : les index de libellés reflètent ce que l'IR contient
    # réellement, et non une lecture parallèle du JSON source.
    doc = compose_document(_data())
    context = doc.metadata["render_context"]
    for component_id, index in (
        ("C-004-finding", "finding_titles"),
        ("C-005-recommendation", "recommendation_titles"),
        ("C-010-evidence", "evidence_titles"),
    ):
        composed = {
            c.payload["id"]: c.payload["title"]
            for c in doc.components
            if c.component_id == component_id
        }
        assert composed
        assert context[index] == composed


def test_unresolved_reference_is_diagnosed_not_crashed():
    # Référence sans libellé : elle ne peut pas être rendue (aucun identifiant
    # technique dans le document) et ne doit pas non plus disparaître en silence.
    data = _data()
    data["risks"][0]["mitigation_recommendation_ids"] = ["recommendation-001", "recommendation-404"]
    doc = compose_document(data)
    payload = _risks(doc)[0].payload
    assert payload["mitigation_recommendation_ids"] == (
        "recommendation-001",
        "recommendation-404",
    )  # l'IR conserve la référence déclarée
    assert any(
        "référence non résolue: C-006-risk :: risk-001 -> recommendation-404" in d
        for d in doc.diagnostics
    )
    assert not any("recommendation-001" in d for d in doc.diagnostics)


def _evidence(doc) -> list[ComponentInstance]:
    return [c for c in doc.components if c.component_id == "C-010-evidence"]


def test_evidence_instance_matches_its_source_entry():
    data = _data()
    data["evidence"].append(
        {
            "id": "evidence-002",
            "title": "Seconde preuve",
            "kind": "log_extract",
            "description": "Description de la seconde preuve.",
            "content": "Extrait de journal.",
            "source": "Instance APPPROD",
        }
    )
    items = _evidence(compose_document(data))
    assert [e.instance_id for e in items] == ["evidence-001", "evidence-002"]
    first = items[0].payload
    source = data["evidence"][0]
    assert first["id"] == source["id"]
    assert first["title"] == source["title"]
    assert first["kind"] == source["kind"]  # nature déclarée, jamais déduite
    assert first["source"] == source["source"]
    assert first["description"] == (source["description"],)
    assert first["content"] == (source["content"],)
    assert items[1].payload["kind"] == "log_extract"


def test_evidence_tolerates_missing_fields():
    data = _data()
    data["evidence"] = [{"id": "evidence-001", "title": "Preuve sans détail"}]
    payload = _evidence(compose_document(data))[0].payload
    assert payload["kind"] is None
    assert payload["source"] is None
    assert payload["description"] == ()
    assert payload["content"] == ()


def test_evidence_payload_carries_no_referencing_component_data():
    # La preuve ne connaît pas les constats qui la citent : la liaison est
    # portée par le constat, dans un seul sens.
    payload = _evidence(compose_document(_data()))[0].payload
    assert "finding_ids" not in payload
    assert not any("Blocage observé" in str(v) for v in payload.values())


def _incident_context(doc) -> ComponentInstance:
    return next(c for c in doc.components if c.instance_id == "incident-context")


def test_incident_context_is_composed():
    context = _incident_context(compose_document(_data()))
    assert context.component_id == "C-011-incident-context"  # promu au catalogue (ADR-0013)
    source = _data()["incident_context"]
    assert context.payload["description"] == (source["description"],)
    assert context.payload["trigger"] == source["trigger"]
    assert context.payload["scope"] == source["scope"]


def test_incident_context_status_stays_canonical_in_the_ir():
    payload = _incident_context(compose_document(_data())).payload
    assert payload["status"] == "investigated"
    assert "Investigé" not in str(payload)


def test_incident_context_splits_description_paragraphs():
    data = _data()
    data["incident_context"]["description"] = "Premier paragraphe.\n\nSecond paragraphe."
    payload = _incident_context(compose_document(data)).payload
    assert payload["description"] == ("Premier paragraphe.", "Second paragraphe.")


def test_incident_context_tolerates_missing_fields():
    data = _data()
    data["incident_context"] = {"description": "Seules les circonstances."}
    payload = _incident_context(compose_document(data)).payload
    assert payload["description"] == ("Seules les circonstances.",)
    assert payload["trigger"] is None  # jamais déduit d'un autre champ
    assert payload["scope"] is None
    assert payload["status"] is None


def test_incident_context_absent_produces_no_instance():
    data = _data()
    data.pop("incident_context")
    doc = compose_document(data)
    assert not any(c.instance_id == "incident-context" for c in doc.components)
    # Le profil le déclare obligatoire : son absence est une anomalie tracée.
    assert any("cardinalité non respectée: C-011-incident-context" in d for d in doc.diagnostics)


def _investigations(doc) -> list[ComponentInstance]:
    return [c for c in doc.components if c.component_id == "narrative-investigation"]


def test_investigation_instance_matches_its_source_entry():
    investigation = _investigations(compose_document(_data()))[0]
    source = _data()["investigations"][0]
    assert investigation.instance_id == source["id"]
    assert investigation.payload["id"] == source["id"]
    assert investigation.payload["title"] == source["title"]
    assert investigation.payload["description"] == (source["description"],)
    assert investigation.payload["result"] == source["result"]  # repris tel quel


def test_investigation_order_follows_the_source():
    data = _data()
    # Identifiant et titre suggèrent une antériorité : l'ordre source prime.
    data["investigations"].append(
        {
            "id": "investigation-000",
            "title": "A — Analyse préliminaire",
            "description": "Contrôles préalables.",
            "result": "inconclusive",
        }
    )
    investigations = _investigations(compose_document(data))
    assert [i.instance_id for i in investigations] == ["investigation-001", "investigation-000"]
    assert investigations[1].payload["title"] == "A — Analyse préliminaire"


def test_investigation_splits_description_paragraphs():
    data = _data()
    data["investigations"][0]["description"] = "Premier paragraphe.\n\nSecond paragraphe."
    payload = _investigations(compose_document(data))[0].payload
    assert payload["description"] == ("Premier paragraphe.", "Second paragraphe.")


def test_investigation_tolerates_missing_fields():
    data = _data()
    data["investigations"] = [{"id": "investigation-001", "title": "Sans détail"}]
    payload = _investigations(compose_document(data))[0].payload
    assert payload["title"] == "Sans détail"
    assert payload["description"] == ()
    assert payload["result"] is None  # jamais déduit de la description


def test_investigations_absent_or_empty_produce_no_instance():
    for data in (_data(), _data()):
        data["investigations"] = []
        assert _investigations(compose_document(data)) == []
    data = _data()
    data.pop("investigations")
    doc = compose_document(data)
    assert _investigations(doc) == []
    # Cardinalité 0..n : aucune anomalie, aucune occurrence fabriquée.
    assert not any("narrative-investigation" in d for d in doc.diagnostics)


def _probable_cause(doc) -> ComponentInstance:
    return next(c for c in doc.components if c.instance_id == "probable-cause")


def test_probable_cause_is_composed():
    payload = _probable_cause(compose_document(_data())).payload
    source = _data()["probable_cause"]
    assert payload["statement"] == (source["statement"],)
    assert payload["supporting_finding_ids"] == ("finding-001",)


def test_probable_cause_confidence_stays_canonical_in_the_ir():
    payload = _probable_cause(compose_document(_data())).payload
    assert payload["confidence"] == "unknown"
    assert "Indéterminée" not in str(payload)


def test_probable_cause_keeps_reference_order_and_duplicates():
    data = _data()
    data["findings"].append(
        {
            "id": "finding-002",
            "title": "Second constat",
            "severity": "low",
            "observation": "…",
            "impact": "…",
            "analysis": "…",
            "evidence_ids": [],
        }
    )
    # Ordre inverse de la déclaration des constats, et un doublon assumé.
    data["probable_cause"]["supporting_finding_ids"] = [
        "finding-002",
        "finding-001",
        "finding-002",
    ]
    payload = _probable_cause(compose_document(data)).payload
    assert payload["supporting_finding_ids"] == ("finding-002", "finding-001", "finding-002")


def test_probable_cause_tolerates_missing_fields():
    data = _data()
    data["probable_cause"] = {"statement": "Énoncé seul."}
    payload = _probable_cause(compose_document(data)).payload
    assert payload["statement"] == ("Énoncé seul.",)
    assert payload["confidence"] is None
    assert payload["supporting_finding_ids"] == ()


def test_probable_cause_unknown_reference_is_diagnosed():
    data = _data()
    data["probable_cause"]["supporting_finding_ids"] = ["finding-001", "finding-404"]
    doc = compose_document(data)
    assert _probable_cause(doc).payload["supporting_finding_ids"] == (
        "finding-001",
        "finding-404",
    )  # l'IR conserve la référence déclarée
    assert any(
        "référence non résolue: narrative :: probable-cause -> finding-404" in d
        for d in doc.diagnostics
    )


def test_probable_cause_absent_produces_no_instance():
    data = _data()
    data.pop("probable_cause")
    doc = compose_document(data)
    assert not any(c.instance_id == "probable-cause" for c in doc.components)
    # Cardinalité 0..1 : aucune anomalie.
    assert not any("cardinalité non respectée: narrative" in d for d in doc.diagnostics)


def _conclusion(doc) -> ComponentInstance:
    return next(c for c in doc.components if c.instance_id == "conclusion")


def test_conclusion_is_composed_from_the_source_string():
    payload = _conclusion(compose_document(_data())).payload
    assert payload["heading"] == "Conclusion"
    assert payload["text"] == (_data()["conclusion"],)  # texte non transformé


def test_conclusion_payload_has_no_derived_field():
    # Ni identifiant, ni champ dérivé : le bloc ne porte que son titre et son
    # texte, donc rien d'autre ne peut atteindre le document.
    payload = _conclusion(compose_document(_data())).payload
    assert set(payload) == {"heading", "text"}


def test_conclusion_splits_paragraphs():
    data = _data()
    data["conclusion"] = "Premier paragraphe.\n\n  Second paragraphe.  "
    payload = _conclusion(compose_document(data)).payload
    assert payload["text"] == ("Premier paragraphe.", "Second paragraphe.")


def test_conclusion_ignores_a_non_string_source():
    data = _data()
    data["conclusion"] = {"texte": "structure inattendue"}
    # L'occurrence est résolue (la clé existe) mais rien n'est interprété.
    assert _conclusion(compose_document(data)).payload["text"] == ()


def test_conclusion_absent_produces_no_instance():
    data = _data()
    data.pop("conclusion")
    doc = compose_document(data)
    assert not any(c.instance_id == "conclusion" for c in doc.components)
    # Le profil la déclare obligatoire : l'écart est tracé, rien n'est fabriqué.
    assert any("cardinalité non respectée: narrative" in d for d in doc.diagnostics)


def test_conclusion_present_but_empty_produces_an_instance():
    """Vide n'est pas absent (ADR-0012, G4).

    La clé existe : la source déclare cette partie, son texte reste à écrire.
    L'occurrence est donc résolue — comme pour une source non textuelle, que le
    test voisin décrit — et son payload est vide sans que rien ne soit fabriqué.
    Aucune cardinalité n'est violée : le profil attend une occurrence, il en a une.
    """
    data = _data()
    data["conclusion"] = ""
    doc = compose_document(data)
    assert any(c.instance_id == "conclusion" for c in doc.components)
    assert not any("cardinalité non respectée: narrative" in d for d in doc.diagnostics)
    assert _conclusion(doc).payload["text"] == ()


def test_reference_report_composes_without_diagnostics():
    # Objectif du chantier : plus aucun bloc non pris en charge sur la source
    # de référence, et donc aucun diagnostic du tout.
    doc = compose_document(_data())
    assert doc.diagnostics == ()


def test_unsupported_components_are_reported_not_crashed():
    # À ce stade, C-001 à C-004, C-008 et C-009 ont un builder : les autres
    # composants résolus doivent produire un diagnostic, jamais une exception.
    doc = compose_document(_data())
    assert not any(d.startswith("builder manquant") for d in doc.diagnostics)
    assert [c.component_id for c in doc.components] == [
        "C-001-cover",
        "C-002-identity-page",
        "C-003-executive-summary",
        "C-011-incident-context",
        "C-009-environment",
        "C-008-timeline",
        "narrative-investigation",
        "C-004-finding",
        "narrative",  # probable-cause
        "C-007-decision",
        "C-005-recommendation",
        "C-006-risk",
        "narrative",  # conclusion
        "C-010-evidence",
    ]


def test_composition_matches_resolution_order():
    data = _data()
    blocks, _ = resolve(data, incident_profile())
    resolved = [cid for cid, _ in blocks]
    doc = compose_document(data)
    supported = [c.component_id for c in doc.components]
    # Les composants instanciés apparaissent dans le même ordre relatif que la
    # résolution canonique (sous-suite ordonnée).
    it = iter(resolved)
    assert all(cid in it for cid in supported)
