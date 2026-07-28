"""Tests de la frontière d'entrée de la composition (ADR-0009, I9).

La règle tient en une phrase : un écart de contrat interrompt, un défaut métier
non. Ce fichier la prouve dans les deux sens, et prouve aussi ce qu'elle ne dit
pas — `compose_document` reste sans garde, sous la frontière.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

import adc_contracts
from adc_engine import SourceContractError, compose_document, compose_from_source

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools" / "python" / "generate_incident_report.py"
DATA = ROOT / "reference_reports" / "incident_report" / "data" / "sql_server_2014_incident.json"


def _source() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8-sig"))


# --- Un écart de contrat interrompt ----------------------------------------

# Formes d'entrée que le moteur n'accepte plus : ce ne sont pas des rapports
# incomplets, ce sont des sources dont la forme n'est plus celle du contrat.
CONTRACT_BREAKS = (
    ("collection au lieu d'une occurrence", lambda d: d.update(findings=[["finding-001"]])),
    ("champ hors contrat", lambda d: d["findings"][0].update(hypothese="x")),
    ("vocabulaire fermé", lambda d: d["findings"][0].update(severity="urgent")),
    ("référence non textuelle", lambda d: d["findings"][0].update(evidence_ids=[{"id": "e"}])),
    ("champ requis absent", lambda d: d["findings"][0].pop("observation")),
    ("noeud de la racine non conforme", lambda d: d["report"].update(title=42)),
)


@pytest.mark.parametrize("label,break_it", CONTRACT_BREAKS, ids=[c[0] for c in CONTRACT_BREAKS])
def test_a_contract_break_stops_the_composition(label, break_it):
    source = _source()
    break_it(source)
    with pytest.raises(SourceContractError) as raised:
        compose_from_source(source)
    assert raised.value.diagnostics, "l'exception doit porter les écarts, pas seulement échouer"
    assert all(d.source == "schema" for d in raised.value.diagnostics)


def test_the_diagnostics_travel_with_the_exception():
    # L'appelant décide comment les présenter : rien n'est journalisé ni perdu.
    source = _source()
    source["findings"][0]["severity"] = "urgent"
    with pytest.raises(SourceContractError) as raised:
        compose_from_source(source)
    diagnostic = raised.value.diagnostics[0]
    assert (diagnostic.component, diagnostic.path) == ("C-004-finding", "$.findings[0].severity")


# --- Un défaut métier n'interrompt pas -------------------------------------

BUSINESS_DEFECTS = (
    ("référence inconnue", lambda d: d["findings"][0].update(evidence_ids=["evidence-404"])),
    ("identifiant dupliqué", lambda d: d["evidence"].append(copy.deepcopy(d["evidence"][0]))),
    ("noeud de la famille absent", lambda d: d.pop("conclusion")),
    ("version de schéma inattendue", lambda d: d.update(schema_version="2.0")),
)


@pytest.mark.parametrize("label,break_it", BUSINESS_DEFECTS, ids=[c[0] for c in BUSINESS_DEFECTS])
def test_a_business_defect_still_composes(label, break_it):
    source = _source()
    break_it(source)
    document = compose_from_source(source)  # ne doit pas lever
    assert document.components, "le rapport reste composable"
    assert document.source_diagnostics, "le défaut accompagne le document"
    assert all(d.source == "business" for d in document.source_diagnostics)


def test_a_clean_source_carries_no_source_diagnostic():
    document = compose_from_source(_source())
    assert document.source_diagnostics == ()
    assert document.diagnostics == ()


def test_the_two_natures_of_diagnostic_stay_apart():
    """Les fondre empêcherait de distinguer un trou du moteur d'un défaut du
    rapport. Ici les deux coexistent, chacun dans son champ."""
    source = _source()
    source["findings"][0]["evidence_ids"] = ["evidence-404"]  # défaut du contenu
    document = compose_from_source(source)
    assert [d.code for d in document.source_diagnostics] == ["unknown_reference"]
    # Le moteur, lui, signale une référence qu'il n'a pas pu résoudre au rendu.
    assert any("référence non résolue" in diagnostic for diagnostic in document.diagnostics)


# --- Ce que la frontière ne fait pas ---------------------------------------


def test_compose_document_stays_unguarded_below_the_boundary():
    """La composition reste une transformation pure, testable sur n'importe
    quelle entrée sans avoir à la rendre conforme d'abord."""
    source = _source()
    source["findings"][0]["severity"] = "urgent"  # contrat violé
    document = compose_document(source)  # ne doit pas lever
    assert document.components
    assert document.source_diagnostics == ()  # elle ne valide rien, donc ne dit rien


def test_a_root_fragment_is_not_a_gate():
    # Aucun contrat ne couvre les blocs narratifs : leur contenu ne peut pas
    # fermer la frontière (ADR-0010).
    source = _source()
    source["incident_context"] = {"n'importe quoi": 42}
    assert compose_from_source(source).components


# --- Le générateur ---------------------------------------------------------


def _generate(source: dict, tmp_path: Path) -> subprocess.CompletedProcess:
    document = tmp_path / "source.json"
    document.write_text(json.dumps(source), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(GENERATOR), str(document), "-o", str(tmp_path / "out.docx")],
        capture_output=True,
        text=True,
    )


def test_the_generator_refuses_a_source_that_violates_a_contract(tmp_path):
    source = _source()
    source["findings"][0]["severity"] = "urgent"
    result = _generate(source, tmp_path)
    assert result.returncode == 1
    assert "CONTRAT VIOLÉ" in result.stderr
    assert "C-004-finding" in result.stderr
    assert not (tmp_path / "out.docx").exists(), "rien ne doit être écrit"


def test_the_generator_produces_a_document_despite_a_business_defect(tmp_path):
    source = _source()
    source["findings"][0]["evidence_ids"] = ["evidence-404"]
    result = _generate(source, tmp_path)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "out.docx").exists()
    assert "Défauts métier du rapport" in result.stdout
    assert "unknown reference 'evidence-404'" in result.stdout


def test_the_generator_accepts_the_reference_source(tmp_path):
    result = _generate(_source(), tmp_path)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "out.docx").exists()
    assert "Défauts métier" not in result.stdout


def test_the_contract_check_precedes_the_business_one(tmp_path):
    # Une source fautive des deux côtés ne rapporte que le contrat : la
    # frontière est séquentielle, pas cumulative.
    source = _source()
    source["findings"][0]["severity"] = "urgent"
    source["findings"][0]["evidence_ids"] = ["evidence-404"]
    result = _generate(source, tmp_path)
    assert result.returncode == 1
    assert "unknown reference" not in result.stderr
