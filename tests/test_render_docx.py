"""Tests du renderer DOCX (increment 2).

Périmètre : rendu de la Cover (C-001-cover) uniquement, depuis le Document IR.
"""
from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

from docx import Document as DocxDocument

from adc_engine import ComponentInstance, compose_document
from adc_engine.render_docx import render_docx

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "reference_reports" / "incident_report" / "data" / "sql_server_2014_incident.json"


def _data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8-sig"))


def _texts(path: Path) -> str:
    doc = DocxDocument(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def test_render_creates_file(tmp_path):
    document = compose_document(_data())
    out = render_docx(document, tmp_path / "report.docx")
    assert out.exists()
    assert out.stat().st_size > 0


def test_cover_texts_present(tmp_path):
    document = compose_document(_data())
    out = render_docx(document, tmp_path / "report.docx")
    text = _texts(out)
    assert "Investigation — Blocage SQL Server lors de DBCC CHECKDB" in text
    assert "Soc01" in text
    assert "Confidentiel" in text
    assert "0.1-draft" in text  # version
    assert "2026-07-28" in text  # date
    assert "A.D.C. srl" in text  # auteur
    assert "ADC-MECA-2026-SQL2014-001" in text  # référence


def test_unsupported_component_is_skipped_not_crashed(tmp_path):
    document = compose_document(_data())
    # Injecte une instance sans renderer : le rendu ne doit ni planter ni la rendre.
    document = replace(
        document,
        components=document.components
        + (ComponentInstance("C-999-unknown", "ghost", {"title": "NE DOIT PAS APPARAITRE"}),),
    )
    out = render_docx(document, tmp_path / "report.docx")
    text = _texts(out)
    assert "Soc01" in text  # la Cover est bien rendue
    assert "NE DOIT PAS APPARAITRE" not in text  # le composant inconnu est ignoré


def test_render_does_not_mutate_document(tmp_path):
    document = compose_document(_data())
    before = copy.deepcopy(document)
    render_docx(document, tmp_path / "report.docx")
    assert document == before
