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

# Noeuds de la source qui ne sont le fragment de personne : aucun builder ne
# les lit. Ni composants catalogue, ni fragments racine — les suivre à part
# évite de les confondre avec une couverture manquante (ADR-0010). La liste
# échoue dans les deux sens : un noeud qui trouve un consommateur doit la
# quitter, un noeud nouveau doit y entrer ou entrer dans la table.
SOURCE_NODES_CONSUMED_BY_NOBODY = ("annexes", "schema_version")


def _catalog_components() -> dict:
    return {k: f for k, f in FRAGMENTS.items() if f.nature == adc_contracts.CATALOG_COMPONENT}


def _root_fragments() -> dict:
    return {k: f for k, f in FRAGMENTS.items() if f.nature == adc_contracts.ROOT_FRAGMENT}


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
    assert set(_catalog_components()) == set(adc_contracts.component_ids())


def test_every_located_path_exists_in_the_reference_source():
    source = _reference_source()
    absent = [
        fragment.path
        for fragment in FRAGMENTS.values()
        if fragment.kind != adc_contracts.SOURCE and fragment.path not in source
    ]
    assert absent == [], "chemin sans contrepartie dans la source de référence"


def test_every_node_of_the_reference_source_is_located_or_tracked():
    """La table dit ce qui est couvert, donc aussi ce qui ne l'est pas.

    Ce test échoue dans les deux sens : un noeud qui trouve un consommateur
    sans entrer dans la table, comme un noeud nouveau que rien ne déclare.
    """
    located = {f.path for f in FRAGMENTS.values() if f.kind != adc_contracts.SOURCE}
    unclaimed = set(_reference_source()) - located - set(_NODES_READ_FROM_SOURCE)
    assert unclaimed == set(SOURCE_NODES_CONSUMED_BY_NOBODY)


def test_a_root_fragment_is_declared_without_being_covered():
    """Être dans la table n'accorde aucune couverture (ADR-0010).

    Les blocs `narrative` y nomment leur consommateur ; aucun schéma ne leur
    est opposé, et ce test échouera le jour où l'un d'eux gagnera un contrat —
    il faudra alors le déclarer composant catalogue, pas l'y laisser.
    """
    assert set(_root_fragments()) == {
        "incident_context",
        "probable_cause",
        "conclusion",
        "investigations",
    }
    for name in _root_fragments():
        assert not adc_contracts.has_contract(name)


def test_a_root_fragment_is_never_validated():
    source = _reference_source()
    source["incident_context"] = {"n'importe quoi": 42}
    source["conclusion"] = ["forme libre", 1, None]
    assert adc_contracts.report_diagnostics(source) == ()


def test_the_decision_component_does_not_read_the_node_its_name_suggests():
    # Le nom du noeud ne se déduit pas de l'identifiant du composant : c'est
    # pourquoi la localisation est une table et non une convention.
    decision = FRAGMENTS["C-007-decision"]
    assert (decision.kind, decision.path) == (adc_contracts.OCCURRENCE, "actions_taken")
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


# --- Support commun aux deux validations -----------------------------------


def test_a_schema_diagnostic_names_its_contract_and_its_keyword():
    source = _reference_source()
    source["findings"][0]["severity"] = "urgent"
    diagnostics = adc_contracts.report_diagnostics(source)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert (diagnostic.source, diagnostic.component) == ("schema", "C-004-finding")
    assert diagnostic.path == "$.findings[0].severity"
    # Le code est le mot-clé du schéma, repris tel quel : le traduire
    # inventerait un vocabulaire que rien n'atteste.
    assert diagnostic.code == "enum"


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("severity", "urgent", "enum"),
        ("title", 42, "type"),
        ("evidence_ids", "evidence-001", "type"),
        ("inconnu", "x", "additionalProperties"),
    ],
)
def test_the_keyword_that_rejected_the_value_is_the_code(field, value, code):
    source = _reference_source()
    source["findings"][0][field] = value
    assert [d.code for d in adc_contracts.report_diagnostics(source)] == [code]


def test_a_missing_required_field_is_coded_required():
    source = _reference_source()
    del source["findings"][0]["title"]
    assert [d.code for d in adc_contracts.report_diagnostics(source)] == ["required"]


def test_the_textual_form_is_the_rendering_of_the_diagnostics():
    source = _reference_source()
    source["findings"][0]["severity"] = "urgent"
    assert adc_contracts.validate_report(source) == tuple(
        str(diagnostic) for diagnostic in adc_contracts.report_diagnostics(source)
    )


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
