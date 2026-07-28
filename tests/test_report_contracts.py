"""Tests de la validation d'une source entière par les contrats de composants.

Le fichier voisin `test_component_contracts.py` prouve chaque contrat isolément.
Ici, deux choses seulement :

- la **table de localisation** — ce qu'elle couvre, et ce qu'elle laisse
  découvert, suivi explicitement plutôt qu'ignoré en silence ;
- la **localisation des écarts** — un écart doit se lire dans la source, pas
  dans le fragment, sans quoi il est inexploitable sur un rapport entier.
"""
from __future__ import annotations

import json

import pytest

import adc_contracts

FRAGMENTS = adc_contracts.INCIDENT_REPORT_FRAGMENTS

# Noeuds de la racine prélevés par les composants qui reçoivent la source
# entière : la table les désigne par `$`, jamais par leur nom.
_NODES_READ_FROM_SOURCE = ("report", "client")

# Noeuds de la source de la famille P-003 qu'aucun contrat ne réclame. Les
# quatre premiers sont pourtant consommés : ce sont les blocs `narrative` du
# profil, bâtis par des builders sans être des composants du catalogue. La
# liste est explicite pour que le trou reste visible (ADR-0010) ; elle échoue
# aussi bien quand un de ces noeuds gagne un contrat que lorsqu'un noeud
# nouveau apparaît sans en avoir un.
SOURCE_NODES_WITHOUT_CONTRACT = (
    "annexes",
    "conclusion",
    "incident_context",
    "investigations",
    "probable_cause",
    "schema_version",
)


def _reference_source() -> dict:
    path = (
        adc_contracts.ROOT
        / "reference_reports"
        / "incident_report"
        / "data"
        / "sql_server_2014_incident.json"
    )
    return json.loads(path.read_text(encoding="utf-8-sig"))


# --- Table de localisation -------------------------------------------------


def test_every_component_of_the_library_is_located():
    # Un composant nouveau doit entrer dans la table, sans quoi son contrat ne
    # serait jamais confronté à une source réelle.
    assert set(FRAGMENTS) == set(adc_contracts.component_ids())


def test_every_located_path_exists_in_the_reference_source():
    source = _reference_source()
    absent = [
        path
        for kind, path in FRAGMENTS.values()
        if kind != adc_contracts.SOURCE and path not in source
    ]
    assert absent == [], "chemin sans contrepartie dans la source de référence"


def test_every_node_of_the_reference_source_is_located_or_tracked():
    """La table dit ce qui est couvert, donc aussi ce qui ne l'est pas.

    Ce test échoue dans les deux sens : un noeud qui gagne un contrat sans
    quitter le suivi, comme un noeud source apparu sans contrat ni suivi.
    """
    located = {path for kind, path in FRAGMENTS.values() if kind != adc_contracts.SOURCE}
    uncovered = set(_reference_source()) - located - set(_NODES_READ_FROM_SOURCE)
    assert uncovered == set(SOURCE_NODES_WITHOUT_CONTRACT)


def test_the_decision_component_does_not_read_the_node_its_name_suggests():
    # Le nom du noeud ne se déduit pas de l'identifiant du composant : c'est
    # pourquoi la localisation est une table et non une convention.
    assert FRAGMENTS["C-007-decision"] == (adc_contracts.OCCURRENCE, "actions_taken")
    assert "decisions" not in _reference_source()


# --- Validation d'une source ----------------------------------------------


def test_the_reference_source_satisfies_every_contract():
    assert adc_contracts.validate_report(_reference_source()) == ()


def test_an_error_is_located_in_the_source_not_in_the_fragment():
    source = _reference_source()
    source["findings"][0]["severity"] = "urgent"
    errors = adc_contracts.validate_report(source)
    assert errors == (
        f"C-004-finding: $.findings[0].severity: {errors[0].split(': ', 2)[2]}",
    )
    assert "urgent" in errors[0]


def test_each_occurrence_is_validated_separately():
    source = _reference_source()
    source["evidence"].append({"id": "", "kind": ""})
    paths = [error.split(": ")[1] for error in adc_contracts.validate_report(source)]
    index = len(source["evidence"]) - 1
    assert paths == [f"$.evidence[{index}].id", f"$.evidence[{index}].kind"]


def test_an_error_on_a_node_carries_the_node_path():
    source = _reference_source()
    source["environment"]["cpu_logical_count"] = 40.5
    errors = adc_contracts.validate_report(source)
    assert len(errors) == 1
    assert errors[0].startswith("C-009-environment: $.environment.cpu_logical_count: ")


def test_an_error_on_the_root_keeps_the_root_path():
    source = _reference_source()
    source["report"]["title"] = 42
    errors = adc_contracts.validate_report(source)
    # Deux contrats lisent ce champ, deux contrats sont violés : le rapporter
    # une seule fois masquerait l'un des deux (ADR-0010).
    assert [error.split(": ")[0] for error in errors] == ["C-001-cover", "C-002-identity-page"]
    assert all(error.split(": ")[1] == "$.report.title" for error in errors)


def test_an_absent_node_produces_no_error():
    # Présence et cardinalité relèvent du profil et du validateur de rapport :
    # un schéma de composant ne dit rien de sa propre présence.
    source = _reference_source()
    del source["timeline"]
    del source["risks"]
    assert adc_contracts.validate_report(source) == ()


def test_a_malformed_collection_is_left_to_the_report_validator():
    # Une collection d'occurrences qui n'est pas une liste ne peut pas être
    # parcourue : aucun contrat d'occurrence ne peut l'adresser.
    source = _reference_source()
    source["findings"] = {"finding-001": {}}
    assert adc_contracts.validate_report(source) == ()


def test_a_source_that_is_not_an_object_is_refused_by_the_root_contracts():
    errors = adc_contracts.validate_report(["pas une source"])
    assert [error.split(": ")[0] for error in errors] == ["C-001-cover", "C-002-identity-page"]
    assert all(error.split(": ")[1] == "$" for error in errors)


def test_an_empty_table_validates_nothing():
    assert adc_contracts.validate_report(_reference_source(), fragments={}) == ()


# --- Préfixe de localisation ----------------------------------------------


def test_a_fragment_validated_alone_keeps_local_paths():
    errors = adc_contracts.validate_fragment(
        "C-009-environment", {"cpu_logical_count": 40.5}
    )
    assert errors[0].startswith("C-009-environment: $.cpu_logical_count: ")


def test_a_root_error_takes_the_prefix_without_trailing_separator():
    # Champs requis manquants : les écarts portent sur le fragment lui-même,
    # dont le chemin est le préfixe nu — ni « $.findings[3]$ », ni
    # « $.findings[3]. ».
    errors = adc_contracts.validate_fragment(
        "C-004-finding", {"id": "finding-001"}, at="$.findings[3]"
    )
    assert errors, "un constat réduit à son identifiant viole son contrat"
    assert all(error.split(": ")[1] == "$.findings[3]" for error in errors)


@pytest.mark.parametrize("component_id", sorted(FRAGMENTS))
def test_no_contract_is_consumed_by_the_composition_chain(component_id):
    """P1 est une bibliothèque : rien ne l'appelle encore (ADR-0009).

    Brancher la validation dans un builder ferait de lui autre chose qu'une
    transformation pure. La frontière d'entrée viendra, et sera ailleurs.
    """
    engine = adc_contracts.ROOT / "tools" / "python" / "adc_engine"
    sources = [path.read_text(encoding="utf-8") for path in engine.glob("*.py")]
    assert not any("adc_contracts" in source for source in sources)
