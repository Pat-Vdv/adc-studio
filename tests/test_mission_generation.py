"""Tests de la génération d'un rapport depuis une mission (P2 du pont).

La commande orchestre : elle traduit, appelle le moteur, présente. Ce qui est
prouvé ici est donc son orchestration — où le document atterrit, ce qui est
écrit et ce qui ne l'est pas — jamais la composition, déjà prouvée ailleurs.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import adc_contracts
import adc_mission

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "tools" / "python" / "generate_mission_report.py"

MISSION_METADATA = textwrap.dedent(
    """\
    client: "Soc01"
    titre: "Blocage SQL Server lors de DBCC CHECKDB"
    date: "2026-07-28"
    annee: "2026"
    auteur: "Auteur Exemple"
    version: "0.1"
    etat: "Brouillon"
    classification: "Confidentiel"

    reference: ""
    framework_version: "1.0"
    """
)


def _mission(tmp_path: Path, metadata: str = MISSION_METADATA, name: str = "2026-07-28_Blocage") -> Path:
    mission = tmp_path / name
    (mission / "rapport").mkdir(parents=True)
    (mission / adc_mission.METADATA_FILE).write_text(metadata, encoding="utf-8")
    return mission


def _run(mission: Path, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(COMMAND), str(mission), *arguments],
        capture_output=True,
        text=True,
    )


# --- Le parcours nominal ---------------------------------------------------


def test_a_mission_produces_a_document_in_its_report_folder(tmp_path):
    mission = _mission(tmp_path)
    result = _run(mission)
    assert result.returncode == 0, result.stderr
    produced = mission / "rapport" / "2026-07-28_Blocage.docx"
    assert produced.is_file()
    assert produced.stat().st_size > 10_000, "un DOCX réel, pas une coquille"


def test_the_report_folder_is_created_when_missing(tmp_path):
    mission = tmp_path / "mission-sans-dossier-rapport"
    mission.mkdir()
    (mission / adc_mission.METADATA_FILE).write_text(MISSION_METADATA, encoding="utf-8")
    assert _run(mission).returncode == 0
    assert (mission / "rapport").is_dir()


def test_an_explicit_output_is_honoured(tmp_path):
    mission = _mission(tmp_path)
    elsewhere = tmp_path / "ailleurs" / "rapport-final.docx"
    assert _run(mission, "-o", str(elsewhere)).returncode == 0
    assert elsewhere.is_file()
    assert not (mission / "rapport" / "2026-07-28_Blocage.docx").exists()


def test_a_fresh_mission_is_composable_though_editorially_empty(tmp_path):
    """Le parcours de bout en bout existe dès la création de la mission.

    Le document produit est réel et squelettique : c'est ce que la frontière
    d'entrée rend possible — incomplet n'est pas malformé (ADR-0009).
    """
    result = _run(_mission(tmp_path))
    assert "Composants rendus : 4" in result.stdout
    assert "Le rapport est incomplet." in result.stdout
    assert "  • Findings" in result.stdout


def test_the_two_natures_of_diagnostic_are_presented_apart(tmp_path):
    result = _run(_mission(tmp_path))
    sections = result.stdout.index("Sections restant à rédiger :")
    engine = result.stdout.index("Composants non rendus (diagnostics) :")
    assert sections < engine
    assert "cardinalité non respectée" in result.stdout[engine:]


def test_a_missing_section_is_never_shown_as_a_raw_diagnostic(tmp_path):
    # C'est tout l'objet de la couche de présentation : un rédacteur lit des
    # sections, pas des chemins JSON.
    result = _run(_mission(tmp_path))
    assert "$.findings: required field missing" not in result.stdout


# --- La source ne persiste pas (ADR-0011, R5) ------------------------------


def test_no_contract_source_is_written_by_default(tmp_path):
    mission = _mission(tmp_path)
    _run(mission)
    assert not (mission / "rapport" / "report.json").exists()
    assert list(mission.rglob("*.json")) == [], "aucune source persistée nulle part"


def test_the_source_is_written_only_when_explicitly_asked(tmp_path):
    mission = _mission(tmp_path)
    result = _run(mission, "--write-source")
    assert result.returncode == 0
    inspection = mission / "rapport" / "report.json"
    assert inspection.is_file()
    assert "inspection" in result.stdout


def test_the_inspected_source_is_exactly_what_the_engine_received(tmp_path):
    # L'artefact d'inspection doit montrer la traduction, pas une variante
    # réécrite pour l'occasion — sinon il ne servirait pas à déboguer.
    mission = _mission(tmp_path)
    _run(mission, "--write-source")
    written = json.loads((mission / "rapport" / "report.json").read_text(encoding="utf-8"))
    assert written == adc_mission.mission_source(mission)
    assert adc_contracts.report_diagnostics(written) == ()


# --- Un contrat violé n'écrit rien -----------------------------------------


def test_a_contract_break_writes_nothing(tmp_path):
    # `version: 0.1` sans guillemets arrive en nombre : le pont le transporte
    # tel quel (R3), le contrat le refuse.
    mission = _mission(tmp_path, metadata='client: "X"\ntitre: "Y"\nversion: 0.1\n')
    result = _run(mission)
    assert result.returncode == 1
    assert "CONTRAT VIOLÉ" in result.stderr
    assert "$.report.version" in result.stderr
    assert list(mission.rglob("*.docx")) == []


def test_a_contract_break_writes_nothing_even_when_the_source_is_asked(tmp_path):
    # L'inspection ne doit pas devenir un moyen détourné de produire un artefact
    # à partir d'une source refusée.
    mission = _mission(tmp_path, metadata='client: "X"\nversion: 0.1\n')
    assert _run(mission, "--write-source").returncode == 1
    assert list(mission.rglob("*.json")) == []


# --- Une mission illisible --------------------------------------------------


def test_a_folder_without_metadata_is_refused(tmp_path):
    empty = tmp_path / "pas-une-mission"
    empty.mkdir()
    result = _run(empty)
    assert result.returncode == 1
    assert "MISSION ILLISIBLE" in result.stderr
    assert "introuvables" in result.stderr


@pytest.mark.parametrize(
    "metadata,expected", [("client: [\n", "YAML invalide"), ("- Soc01\n", "objet attendu")]
)
def test_malformed_metadata_is_refused_with_its_reason(tmp_path, metadata, expected):
    mission = _mission(tmp_path, metadata=metadata)
    result = _run(mission)
    assert result.returncode == 1
    assert expected in result.stderr
    assert list(mission.rglob("*.docx")) == []


# --- Ce que la commande ne fait pas ----------------------------------------


def test_the_command_orchestrates_and_nothing_more():
    """Elle ne recompose ni ne revalide : elle appelle le moteur.

    Un jour où quelqu'un voudrait « juste vérifier une petite chose » avant de
    composer, ce test le lui rappellera.
    """
    source = COMMAND.read_text(encoding="utf-8")
    assert "compose_from_source" in source
    assert "compose_document" not in source, "la frontière ne se contourne pas"
    assert "adc_contracts" not in source, "la validation appartient à la frontière"
    assert "Draft202012" not in source
