"""Tests du pont atelier -> source contractuelle (ADR-0011).

Trois choses à prouver, et une seule compte vraiment :

- la correspondance des clés, champ par champ ;
- le pont traduit sans normaliser — les valeurs traversent inchangées ;
- **la source produite ne présente aucun écart de contrat**, vérifiée contre les
  schémas eux-mêmes plutôt que contre une forme réécrite ici. Un test qui
  décrirait la forme attendue à la main ne prouverait que ma lecture du contrat.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

import adc_contracts
import adc_mission

# `metadata.yml` tel que `New-ADCClientReport` l'écrit aujourd'hui, verbatim.
# Le reproduire ici fige la forme réelle : si le script change, le test doit
# être confronté à la nouvelle forme, pas continuer à valider l'ancienne.
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

    livrables:
      word: ""
      pdf: ""

    repertoires:
      rapport: "rapport"
      captures: "captures"
      annexes: "annexes"
      travail: "travail"
    """
)


@pytest.fixture
def mission(tmp_path: Path) -> Path:
    (tmp_path / adc_mission.METADATA_FILE).write_text(MISSION_METADATA, encoding="utf-8")
    return tmp_path


# --- Ce que le contrat dit de la source produite ---------------------------


def test_a_fresh_mission_produces_a_contract_clean_source(mission):
    # L'assertion qui compte : les schémas eux-mêmes valident la traduction.
    source = adc_mission.mission_source(mission)
    assert adc_contracts.report_diagnostics(source) == ()


def test_an_empty_mission_produces_a_contract_clean_source(tmp_path):
    (tmp_path / adc_mission.METADATA_FILE).write_text("", encoding="utf-8")
    source = adc_mission.mission_source(tmp_path)
    assert source == {"report": {}, "client": {}}
    assert adc_contracts.report_diagnostics(source) == ()


# --- Correspondance des clés ------------------------------------------------


def test_the_workshop_vocabulary_becomes_the_canonical_one(mission):
    source = adc_mission.mission_source(mission)
    assert source["report"] == {
        "title": "Blocage SQL Server lors de DBCC CHECKDB",
        "date": "2026-07-28",
        "author": "Auteur Exemple",
        "version": "0.1",
        "confidentiality": "Confidentiel",
    }
    # Une chaîne devient un objet : la forme change, pas la valeur.
    assert source["client"] == {"name": "Soc01"}


@pytest.mark.parametrize(
    "workshop_key", ["etat", "annee", "framework_version", "livrables", "repertoires"]
)
def test_a_workshop_field_without_counterpart_does_not_cross(mission, workshop_key):
    """Ces champs décrivent l'atelier, pas le rapport (ADR-0011).

    Les laisser passer ferait entrer dans la source des clés qu'aucun contrat ne
    décrit — et que les objets fermés rejetteraient.
    """
    source = adc_mission.mission_source(mission)
    assert workshop_key not in source["report"]
    assert workshop_key not in source["client"]


def test_the_two_nodes_exist_even_when_the_mission_is_bare(tmp_path):
    # Leur absence serait un défaut de la source, pas de sa traduction : le
    # validateur métier les exige à la racine.
    (tmp_path / adc_mission.METADATA_FILE).write_text("titre: X\n", encoding="utf-8")
    source = adc_mission.mission_source(tmp_path)
    assert set(source) == {"report", "client"}


# --- Traduire n'est pas normaliser (R3) ------------------------------------


@pytest.mark.parametrize(
    "value",
    ["28/07/2026", "juillet 2026", "2026-7-8", "  espaces autour  ", "CONFIDENTIEL", "0.1-draft"],
)
def test_a_value_crosses_the_bridge_unchanged(value):
    """Le pont n'est pas un correcteur (ADR-0011, R3).

    Une date mal écrite reste mal écrite : la corriger ici ferait mentir la
    source sur ce que la mission déclare. Le contrat n'impose d'ailleurs aucun
    format de date, et ce qu'il impose est refusé plus loin, à la frontière.
    """
    source = adc_mission.to_source({"date": value, "classification": value})
    assert source["report"]["date"] == value
    assert source["report"]["confidentiality"] == value


def test_the_bridge_infers_nothing(tmp_path):
    # Ni date du jour, ni auteur par défaut, ni identifiant fabriqué : ce que la
    # mission ne dit pas, la source ne le dit pas.
    (tmp_path / adc_mission.METADATA_FILE).write_text("client: Soc01\n", encoding="utf-8")
    source = adc_mission.mission_source(tmp_path)
    assert source["report"] == {}


def test_a_non_textual_value_is_carried_as_is():
    # Le pont ne convertit pas davantage qu'il ne reformate. Une version écrite
    # sans guillemets arrive en nombre ; c'est au contrat de la refuser.
    source = adc_mission.to_source({"version": 0.1})
    assert source["report"]["version"] == 0.1
    errors = adc_contracts.report_diagnostics(source)
    assert [d.path for d in errors] == ["$.report.version", "$.report.version"]


# --- Une valeur absente ne s'écrit pas (R4) --------------------------------


@pytest.mark.parametrize("empty", ["", "   ", None])
def test_an_empty_field_is_omitted_never_written(empty):
    source = adc_mission.to_source({"titre": "X", "reference": empty})
    assert "reference" not in source["report"]


def test_the_empty_reference_of_a_fresh_mission_does_not_reach_the_source(mission):
    # `New-ADCClientReport` écrit `reference: ""`. Le contrat de C-001 tolère
    # une référence vide, mais l'écrire serait déclarer une valeur qui n'existe
    # pas — et le même réflexe sur `id` bloquerait toute génération.
    assert "reference" not in adc_mission.mission_source(mission)["report"]


def test_writing_an_empty_identifier_would_break_the_contract():
    """Ce test dit pourquoi R4 existe, pas ce que le pont fait.

    Il échouera si un jour le contrat de C-002 cesse d'exiger un identifiant non
    vide — auquel cas la règle perdrait sa démonstration la plus nette, sans
    perdre sa raison d'être.
    """
    errors = adc_contracts.report_diagnostics({"report": {"id": ""}, "client": {}})
    assert [d.component for d in errors] == ["C-002-identity-page"]


# --- Métadonnées illisibles -------------------------------------------------


def test_a_missing_metadata_file_names_the_path(tmp_path):
    with pytest.raises(FileNotFoundError, match="introuvables"):
        adc_mission.mission_source(tmp_path)


def test_malformed_yaml_names_the_file(tmp_path):
    (tmp_path / adc_mission.METADATA_FILE).write_text("client: [\n", encoding="utf-8")
    with pytest.raises(ValueError, match="YAML invalide"):
        adc_mission.mission_source(tmp_path)


def test_metadata_that_is_not_a_mapping_is_refused(tmp_path):
    (tmp_path / adc_mission.METADATA_FILE).write_text("- Soc01\n", encoding="utf-8")
    with pytest.raises(ValueError, match="objet attendu"):
        adc_mission.mission_source(tmp_path)


def test_a_utf8_bom_does_not_prevent_reading(tmp_path):
    # PowerShell écrit en UTF-8 ; un BOM ne doit pas rendre la mission illisible.
    path = tmp_path / adc_mission.METADATA_FILE
    path.write_bytes(b"\xef\xbb\xbf" + MISSION_METADATA.encode("utf-8"))
    assert adc_mission.mission_source(tmp_path)["client"] == {"name": "Soc01"}


def test_accented_values_survive_the_crossing(tmp_path):
    metadata = {"client": "Société Générale", "titre": "Panne réseau — étude"}
    path = tmp_path / adc_mission.METADATA_FILE
    path.write_text(yaml.safe_dump(metadata, allow_unicode=True), encoding="utf-8")
    source = adc_mission.mission_source(tmp_path)
    assert source["client"]["name"] == "Société Générale"
    assert source["report"]["title"] == "Panne réseau — étude"


# --- Le pont ne connaît que sa moitié de la chaîne -------------------------


def test_the_bridge_is_the_only_place_that_knows_the_workshop():
    """Ni le contrat ni le moteur ne savent qu'un `metadata.yml` existe (ADR-0011)."""
    watched = [adc_contracts.ROOT / "tools" / "python" / "adc_contracts.py"]
    watched += list((adc_contracts.ROOT / "tools" / "python" / "adc_engine").glob("*.py"))
    watched += list((adc_contracts.ROOT / "components").glob("*/schema.json"))
    for path in watched:
        content = path.read_text(encoding="utf-8")
        assert "metadata.yml" not in content, path
        for workshop_key in ("titre", "auteur", "classification"):
            assert f'"{workshop_key}"' not in content, f"{path}: alias d'atelier"
