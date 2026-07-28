"""Tests de la couche de présentation des diagnostics (P3 du pont).

Elle range et elle nomme. Ce qu'elle ne fait pas — inventer un décompte,
rédiger un intitulé, confondre une section absente avec un contenu fautif — est
prouvé aussi explicitement que ce qu'elle fait.
"""
from __future__ import annotations

import pytest

import adc_presentation as presentation
from adc_diagnostics import BUSINESS, ValidationDiagnostic


def _missing(node: str) -> ValidationDiagnostic:
    return ValidationDiagnostic(
        path=f"$.{node}", message="required field missing", source=BUSINESS,
        code="required_field_missing",
    )


def _defect(path: str, code: str, message: str) -> ValidationDiagnostic:
    return ValidationDiagnostic(path=path, message=message, source=BUSINESS, code=code)


FRESH_MISSION = (
    _missing("schema_version"),
    _missing("executive_summary"),
    _missing("incident_context"),
    _missing("environment"),
    _missing("findings"),
    _missing("recommendations"),
    _missing("evidence"),
    _missing("conclusion"),
    _defect("$.schema_version", "unexpected_value", "expected '1.0'"),
)


# --- Ce qui est une section, et ce qui n'en est pas -------------------------


def test_a_missing_node_of_the_family_is_a_section_to_write():
    assert presentation.missing_sections(FRESH_MISSION) == (
        "executive_summary",
        "incident_context",
        "environment",
        "findings",
        "recommendations",
        "evidence",
        "conclusion",
    )


def test_a_node_that_is_nobody_s_fragment_is_not_a_section():
    """`schema_version` n'est le fragment de personne (ADR-0010).

    Rien qu'un rédacteur puisse écrire : l'annoncer comme une section à rédiger
    enverrait un humain chercher un texte qui n'existe pas.
    """
    assert "schema_version" not in presentation.missing_sections(FRESH_MISSION)
    assert any(d.path == "$.schema_version" for d in presentation.defects(FRESH_MISSION))


def test_the_declared_order_is_preserved():
    # L'ordre est celui du validateur, qui suit la déclaration de la famille.
    # Trier alphabétiquement remplacerait une information par une convention.
    sections = presentation.missing_sections(FRESH_MISSION)
    assert sections.index("findings") < sections.index("recommendations")
    assert sections.index("executive_summary") < sections.index("conclusion")


def test_a_defect_inside_an_existing_section_is_not_a_missing_section():
    diagnostics = (_defect("$.findings[0].evidence_ids[0]", "unknown_reference", "unknown"),)
    assert presentation.missing_sections(diagnostics) == ()
    assert presentation.defects(diagnostics) == diagnostics


@pytest.mark.parametrize(
    "path", ["$", "$.findings[0]", "$.findings[0].title", "$.report.title"]
)
def test_only_a_root_node_can_be_a_section(path):
    assert presentation.missing_sections((_defect(path, "required_field_missing", "x"),)) == ()


# --- Ce que la présentation n'ajoute pas -----------------------------------


def test_no_count_is_ever_produced():
    """Le moteur sait qu'il manque `findings`, jamais qu'il en faudrait trois.

    Un décompte inventerait une information — ce que toute la chaîne s'interdit.
    """
    # Restreint aux lignes de sections : un message du moteur peut légitimement
    # porter un chiffre — « expected '1.0' » — et il traverse verbatim.
    sections = [line for line in presentation.source_lines(FRESH_MISSION) if "•" in line]
    assert sections, "hypothèse du test caduque si plus aucune section n'est listée"
    assert not any(character.isdigit() for line in sections for character in line)


def test_a_label_is_the_node_name_made_readable():
    assert presentation.label("executive_summary") == "Executive summary"
    assert presentation.label("findings") == "Findings"


def test_a_label_stays_traceable_to_its_field():
    # Aucun intitulé rédigé ici : le lecteur doit pouvoir retrouver le champ.
    for node in presentation.missing_sections(FRESH_MISSION):
        assert presentation.label(node).lower().replace(" ", "_") == node


def test_the_presentation_validates_nothing():
    source = (presentation.__file__ or "").replace(".pyc", ".py")
    content = open(source, encoding="utf-8").read()
    assert "report_diagnostics" not in content
    assert "validate" not in content
    assert "Draft202012" not in content


# --- Les lignes produites ---------------------------------------------------


def test_a_clean_source_produces_no_line():
    assert presentation.source_lines(()) == ()


def test_the_two_natures_are_announced_apart():
    lines = presentation.source_lines(FRESH_MISSION)
    text = "\n".join(lines)
    assert "Le rapport est incomplet." in text
    assert text.index("Sections restant à rédiger :") < text.index("Défauts de la source :")
    assert "  • Findings" in lines
    assert "  - $.schema_version: expected '1.0'" in lines


def test_a_source_with_only_defects_announces_no_section():
    diagnostics = (_defect("$.evidence[1].id", "duplicate_id", "duplicate id 'evidence-001'"),)
    lines = presentation.source_lines(diagnostics)
    assert "Sections restant à rédiger :" not in lines
    assert "Le rapport est incomplet." not in lines
    assert lines[0] == "Défauts de la source :"


def test_a_source_with_only_missing_sections_announces_no_defect():
    lines = presentation.source_lines((_missing("findings"),))
    assert "Défauts de la source :" not in lines
    assert lines[-1] == "  • Findings"
