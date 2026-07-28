"""Tests du moteur de composition (Document Model / IR).

Développement incrémental — cas SQL Server Incident. Chaque composant pris en
charge ajoute ici une assertion ciblée.
"""
from __future__ import annotations

import json
from pathlib import Path

from adc_engine import ComponentInstance, Document, compose_document
from adc_engine.resolve import resolve

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "reference_reports" / "incident_report" / "data" / "sql_server_2014_incident.json"

# Volets du résumé exécutif, dans l'ordre attendu du composant C-003.
SUMMARY_SECTIONS = ("context", "business_impact", "conclusion", "recommended_action")


def _data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8-sig"))


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
    environment = doc.components[3]
    assert environment.component_id == "C-009-environment"
    assert environment.instance_id == "environment"
    system = environment.payload["system"]
    assert system["server_name"] == "SRV-SQL-01"
    assert system["database_engine"] == "Microsoft SQL Server 2014 Standard"
    assert system["cpu_logical_count"] == 40  # valeur reprise telle quelle
    assert system["memory_gb"] == 64


def test_environment_storage_rows_are_normalized():
    environment = compose_document(_data()).components[3]
    storage = environment.payload["storage"]
    assert [row["volume"] for row in storage] == ["C:", "D:", "E:", "I:"]
    assert all(set(row) == {"volume", "role", "allocation_unit_kb"} for row in storage)
    assert storage[1] == {"volume": "D:", "role": "SQL", "allocation_unit_kb": 64}
    assert storage[0]["allocation_unit_kb"] is None  # champ non renseigné, conservé


def test_environment_tolerates_missing_fields():
    data = _data()
    data["environment"] = {"server_name": "SRV-01"}
    environment = compose_document(data).components[3]
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


def test_narrative_incident_context_stays_diagnosed():
    # Le bloc narratif n'est pas un composant du catalogue : il reste un
    # diagnostic tant qu'aucun builder dédié n'est livré.
    doc = compose_document(_data())
    assert any("narrative :: incident-context" in d for d in doc.diagnostics)


def test_unsupported_components_are_reported_not_crashed():
    # À ce stade, C-001 à C-003, C-009 et C-008 ont un builder : les autres
    # composants résolus doivent produire un diagnostic, jamais une exception.
    doc = compose_document(_data())
    assert any("C-004-finding" in d for d in doc.diagnostics)
    assert not any("C-008-timeline" in d for d in doc.diagnostics)
    assert [c.component_id for c in doc.components] == [
        "C-001-cover",
        "C-002-identity-page",
        "C-003-executive-summary",
        "C-009-environment",
        "C-008-timeline",
    ]


def test_composition_matches_resolution_order():
    data = _data()
    resolved = [cid for cid, _ in resolve(data)]
    doc = compose_document(data)
    supported = [c.component_id for c in doc.components]
    # Les composants instanciés apparaissent dans le même ordre relatif que la
    # résolution canonique (sous-suite ordonnée).
    it = iter(resolved)
    assert all(cid in it for cid in supported)
