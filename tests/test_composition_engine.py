"""Tests du moteur de composition (Document Model / IR).

Développement incrémental — cas SQL Server Incident. Chaque composant pris en
charge ajoute ici une assertion ciblée.
"""
from __future__ import annotations

import json
from pathlib import Path

from adc_engine import Document, compose_document
from adc_engine.resolve import resolve

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "reference_reports" / "incident_report" / "data" / "sql_server_2014_incident.json"


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


def test_unsupported_components_are_reported_not_crashed():
    # À ce stade, seul C-001-cover a un builder : les autres composants résolus
    # doivent produire un diagnostic, jamais une exception.
    doc = compose_document(_data())
    assert any("C-002-identity-page" in d for d in doc.diagnostics)
    # Un seul composant instancié pour l'instant (la Cover).
    assert [c.component_id for c in doc.components] == ["C-001-cover"]


def test_composition_matches_resolution_order():
    data = _data()
    resolved = [cid for cid, _ in resolve(data)]
    doc = compose_document(data)
    supported = [c.component_id for c in doc.components]
    # Les composants instanciés apparaissent dans le même ordre relatif que la
    # résolution canonique (sous-suite ordonnée).
    it = iter(resolved)
    assert all(cid in it for cid in supported)
