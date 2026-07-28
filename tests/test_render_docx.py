"""Tests du renderer DOCX (increment 2).

Périmètre : rendu de la Cover (C-001-cover), de l'identité documentaire
(C-002-identity-page), du résumé exécutif (C-003-executive-summary) et de
l'environnement (C-009-environment) depuis le Document IR.
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


_REVISIONS_HEADER = ["Version", "Date", "Auteur", "Objet"]


def _table_rows(path: Path, header: list[str]) -> list[list[str]]:
    """Lignes de la table portant cet en-tête (liste vide si aucune)."""
    for table in DocxDocument(str(path)).tables:
        rows = [[cell.text for cell in row.cells] for row in table.rows]
        if rows and rows[0] == header:
            return rows
    return []


def test_identity_page_omits_empty_optional_tables(tmp_path):
    document = compose_document(_data())
    out = render_docx(document, tmp_path / "report.docx")
    text = _texts(out)
    assert "Révisions" not in text
    assert "Diffusion" not in text
    assert _table_rows(out, _REVISIONS_HEADER) == []


def test_identity_page_renders_optional_tables(tmp_path):
    data = _data()
    data["report"]["revisions"] = [
        {"version": "0.1-draft", "date": "2026-07-28", "author": "A.D.C. srl", "summary": "Création"}
    ]
    document = compose_document(data)
    out = render_docx(document, tmp_path / "report.docx")
    assert "Révisions" in "\n".join(p.text for p in DocxDocument(str(out)).paragraphs)
    rows = _table_rows(out, _REVISIONS_HEADER)
    assert rows[1:] == [["0.1-draft", "2026-07-28", "A.D.C. srl", "Création"]]


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


def test_environment_texts_present(tmp_path):
    document = compose_document(_data())
    out = render_docx(document, tmp_path / "report.docx")
    text = _texts(out)
    assert "Environnement" in text
    assert "SRV-SQL-01" in text
    assert "Microsoft SQL Server 2014 Standard" in text
    assert "French_CI_AS" in text
    assert "40" in text  # processeurs logiques, valeur numérique rendue


def test_environment_storage_table(tmp_path):
    document = compose_document(_data())
    out = render_docx(document, tmp_path / "report.docx")
    assert "Stockage" in _texts(out)
    rows = _table_rows(out, ["Volume", "Rôle", "Unité d'allocation (Ko)"])
    assert rows[1] == ["C:", "Système", ""]  # unité non renseignée : cellule vide
    assert rows[2] == ["D:", "SQL", "64"]
    assert [row[0] for row in rows[1:]] == ["C:", "D:", "E:", "I:"]


def test_environment_without_storage_has_no_table(tmp_path):
    data = _data()
    data["environment"].pop("storage")
    document = compose_document(data)
    out = render_docx(document, tmp_path / "report.docx")
    assert "Stockage" not in _texts(out)
    assert _table_rows(out, ["Volume", "Rôle", "Unité d'allocation (Ko)"]) == []


_TIMELINE_HEADER = ["Horodatage", "Événement", "Description"]


def test_timeline_table_follows_source_order(tmp_path):
    data = _data()
    data["timeline"].append(
        {
            "id": "timeline-000",
            "timestamp": "2026-07-22",
            "title": "Signalement",
            "description": "Appel du client.",
        }
    )
    document = compose_document(data)
    out = render_docx(document, tmp_path / "report.docx")
    assert "Chronologie" in _texts(out)
    rows = _table_rows(out, _TIMELINE_HEADER)
    assert rows[1] == [
        "2026-07-23",
        "Sauvegardes préalables",
        "Sauvegardes complètes et VERIFYONLY réalisés avant intervention.",
    ]
    assert [row[0] for row in rows[1:]] == ["2026-07-23", "2026-07-22"]  # ordre source


def test_timeline_empty_renders_no_section(tmp_path):
    # Instance présente mais sans entrée : ni titre ni tableau vide.
    data = _data()
    data["timeline"] = ["entrée invalide ignorée"]
    document = compose_document(data)
    out = render_docx(document, tmp_path / "report.docx")
    assert "Chronologie" not in _texts(out)
    assert _table_rows(out, _TIMELINE_HEADER) == []


def test_timeline_absent_renders_no_section(tmp_path):
    data = _data()
    data.pop("timeline")
    document = compose_document(data)
    out = render_docx(document, tmp_path / "report.docx")
    assert "Chronologie" not in _texts(out)
    assert "Environnement" in _texts(out)  # le reste du rapport est intact


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
