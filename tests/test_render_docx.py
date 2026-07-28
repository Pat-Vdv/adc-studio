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


def test_finding_is_rendered_as_its_own_section(tmp_path):
    data = _data()
    data["findings"][0]["observation"] = "Symptôme attesté.\n\nSecond paragraphe."
    document = compose_document(data)
    out = render_docx(document, tmp_path / "report.docx")
    paragraphs = [p.text for p in DocxDocument(str(out)).paragraphs]
    assert "Constat — Blocage observé pendant DBCC CHECKDB" in paragraphs
    assert "Observation" in paragraphs
    assert "Symptôme attesté." in paragraphs
    assert "Second paragraphe." in paragraphs
    assert "Analyse" in paragraphs


def test_finding_renders_evidence_titles_never_ids(tmp_path):
    document = compose_document(_data())
    out = render_docx(document, tmp_path / "report.docx")
    text = _texts(out)
    assert "Preuves : État et configuration de l’environnement SQL" in text
    assert "evidence-001" not in text  # identifiant technique jamais affiché
    assert "finding-001" not in text


def test_finding_omits_evidence_line_without_references(tmp_path):
    data = _data()
    data["findings"][0]["evidence_ids"] = []
    document = compose_document(data)
    out = render_docx(document, tmp_path / "report.docx")
    text = _texts(out)
    assert "Constat — Blocage observé pendant DBCC CHECKDB" in text
    assert "Preuves" not in text


def test_findings_are_rendered_independently(tmp_path):
    data = _data()
    data["findings"].append(
        {
            "id": "finding-002",
            "title": "Second constat",
            "severity": "low",
            "observation": "Observation du second constat.",
            "impact": "Impact mineur.",
            "analysis": "Analyse du second constat.",
            "evidence_ids": ["evidence-001"],
        }
    )
    document = compose_document(data)
    out = render_docx(document, tmp_path / "report.docx")
    paragraphs = [p.text for p in DocxDocument(str(out)).paragraphs]
    # Deux sections autonomes, aucun titre de partie « Constats » commun.
    assert "Constat — Blocage observé pendant DBCC CHECKDB" in paragraphs
    assert "Constat — Second constat" in paragraphs
    assert "Constats" not in paragraphs


def test_decision_is_rendered_as_its_own_section(tmp_path):
    data = _data()
    data["actions_taken"][0]["description"] = "Première partie.\n\nSeconde partie."
    document = compose_document(data)
    out = render_docx(document, tmp_path / "report.docx")
    paragraphs = [p.text for p in DocxDocument(str(out)).paragraphs]
    assert "Mesure prise — Sécurisation préalable par sauvegarde" in paragraphs
    assert "Statut : completed" in paragraphs  # valeur canonique, non traduite
    assert "Première partie." in paragraphs
    assert "Seconde partie." in paragraphs


def test_decision_omits_absent_blocks(tmp_path):
    data = _data()
    data["actions_taken"] = [{"id": "decision-001", "title": "Mesure sans détail"}]
    document = compose_document(data)
    out = render_docx(document, tmp_path / "report.docx")
    paragraphs = [p.text for p in DocxDocument(str(out)).paragraphs]
    assert "Mesure prise — Mesure sans détail" in paragraphs
    assert not any(p.startswith("Statut") for p in paragraphs)


def test_decisions_are_rendered_independently(tmp_path):
    data = _data()
    data["actions_taken"].append(
        {
            "id": "decision-002",
            "title": "Seconde mesure",
            "description": "Description de la seconde mesure.",
            "status": "in_progress",
        }
    )
    document = compose_document(data)
    out = render_docx(document, tmp_path / "report.docx")
    paragraphs = [p.text for p in DocxDocument(str(out)).paragraphs]
    assert "Mesure prise — Sécurisation préalable par sauvegarde" in paragraphs
    assert "Mesure prise — Seconde mesure" in paragraphs
    assert "Mesures prises" not in paragraphs  # aucun titre de partie commun


def test_recommendation_is_rendered_as_its_own_section(tmp_path):
    document = compose_document(_data())
    out = render_docx(document, tmp_path / "report.docx")
    paragraphs = [p.text for p in DocxDocument(str(out)).paragraphs]
    assert "Recommandation — Exécuter DBCC CHECKDB hors production" in paragraphs
    assert "Description" in paragraphs
    assert "Justification" in paragraphs
    assert "Recommandations" not in paragraphs  # aucun titre de partie commun


def test_recommendation_renders_finding_titles_never_ids(tmp_path):
    document = compose_document(_data())
    out = render_docx(document, tmp_path / "report.docx")
    text = _texts(out)
    assert "Constats liés : Blocage observé pendant DBCC CHECKDB" in text
    assert "finding-001" not in text
    assert "recommendation-001" not in text


def test_enumerations_are_english_in_the_ir_and_french_in_the_docx(tmp_path):
    # Règle figée : valeurs canoniques anglaises dans le Document (IR),
    # libellés français produits uniquement par la couche DOCX.
    data = _data()
    data["findings"][0]["severity"] = "critical"
    data["recommendations"][0]["priority"] = "medium"
    document = compose_document(data)

    payloads = [c.payload for c in document.components]
    assert any(p.get("severity") == "critical" for p in payloads)
    assert any(p.get("priority") == "medium" for p in payloads)
    assert not any("Critique" in str(p) or "Moyenne" in str(p) for p in payloads)

    text = _texts(render_docx(document, tmp_path / "report.docx"))
    assert "Gravité : Critique" in text
    assert "Priorité : Moyenne" in text
    assert "critical" not in text
    assert "medium" not in text


def test_unknown_enumeration_value_is_rendered_verbatim(tmp_path):
    # Hors vocabulaire : on restitue la valeur de la source plutôt que
    # d'inventer une traduction.
    data = _data()
    data["recommendations"][0]["priority"] = "blocking"
    document = compose_document(data)
    text = _texts(render_docx(document, tmp_path / "report.docx"))
    assert "Priorité : blocking" in text


def test_recommendations_are_rendered_in_source_order(tmp_path):
    data = _data()
    data["recommendations"].append(
        {
            "id": "recommendation-002",
            "title": "Priorité critique déclarée en second",
            "priority": "critical",
            "description": "Description.",
            "rationale": "Justification.",
            "related_finding_ids": [],
        }
    )
    document = compose_document(data)
    out = render_docx(document, tmp_path / "report.docx")
    paragraphs = [p.text for p in DocxDocument(str(out)).paragraphs]
    first = paragraphs.index("Recommandation — Exécuter DBCC CHECKDB hors production")
    second = paragraphs.index("Recommandation — Priorité critique déclarée en second")
    assert first < second  # aucun regroupement ni tri par priorité


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
