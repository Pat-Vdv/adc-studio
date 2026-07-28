"""Tests du renderer DOCX (increment 2).

Périmètre : rendu de la Cover (C-001-cover), de l'identité documentaire
(C-002-identity-page) et du résumé exécutif (C-003-executive-summary) depuis
le Document IR.
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


def test_identity_page_texts_present(tmp_path):
    document = compose_document(_data())
    out = render_docx(document, tmp_path / "report.docx")
    text = _texts(out)
    assert "Identité du document" in text
    assert "fr-BE" in text  # langue, propre à la page d'identité


def test_identity_page_omits_empty_optional_tables(tmp_path):
    document = compose_document(_data())
    out = render_docx(document, tmp_path / "report.docx")
    text = _texts(out)
    docx = DocxDocument(str(out))
    assert "Révisions" not in text
    assert "Diffusion" not in text
    assert docx.tables == []


def test_identity_page_renders_optional_tables(tmp_path):
    data = _data()
    data["report"]["revisions"] = [
        {"version": "0.1-draft", "date": "2026-07-28", "author": "A.D.C. srl", "summary": "Création"}
    ]
    document = compose_document(data)
    out = render_docx(document, tmp_path / "report.docx")
    docx = DocxDocument(str(out))
    assert "Révisions" in "\n".join(p.text for p in docx.paragraphs)
    assert len(docx.tables) == 1
    rows = [[c.text for c in row.cells] for row in docx.tables[0].rows]
    assert rows[0] == ["Version", "Date", "Auteur", "Objet"]
    assert rows[1] == ["0.1-draft", "2026-07-28", "A.D.C. srl", "Création"]


def test_executive_summary_renders_payload_faithfully(tmp_path):
    # Le rendu est comparé au payload composé, pas au texte de la source : la
    # rédaction du rapport de référence n'a aucune incidence sur ce test.
    data = _data()
    data["executive_summary"]["context"] = "Contexte du blocage.\n\nSeconde partie du contexte."
    document = compose_document(data)
    summary = document.components[2]
    out = render_docx(document, tmp_path / "report.docx")
    paragraphs = [p.text for p in DocxDocument(str(out)).paragraphs]

    assert summary.payload["heading"] in paragraphs
    for key, heading in (
        ("context", "Contexte"),
        ("business_impact", "Impact métier"),
        ("conclusion", "Conclusion"),
        ("recommended_action", "Action recommandée"),
    ):
        blocks = summary.payload[key]
        assert (heading in paragraphs) is bool(blocks)  # titre ssi volet renseigné
        for block in blocks:
            assert block in paragraphs


def test_executive_summary_omits_empty_sections(tmp_path):
    data = _data()
    data["executive_summary"] = {"context": "Seul volet renseigné."}
    document = compose_document(data)
    out = render_docx(document, tmp_path / "report.docx")
    paragraphs = [p.text for p in DocxDocument(str(out)).paragraphs]
    assert "Contexte" in paragraphs
    assert "Impact métier" not in paragraphs  # pas de titre sans contenu
    assert "Action recommandée" not in paragraphs


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
