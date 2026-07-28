"""Tests de l'infrastructure de validation des contrats de composants.

Deux niveaux :

- le **mécanisme** est prouvé sur un schéma de test, seul moyen d'attester
  qu'une contrainte rejette vraiment tant que les schémas du dépôt restent
  permissifs ;
- l'**état du dépôt** est vérifié composant par composant : un schéma sans
  exemple, un exemple invalide ou un schéma mal formé fait échouer le cas
  portant le nom du composant.
"""
from __future__ import annotations

import json

import pytest
from jsonschema.exceptions import SchemaError

import adc_contracts

# Composants sans contrat déclaré, à ce stade du durcissement. La liste est
# volontairement explicite : elle échoue aussi bien quand un composant perd son
# contrat que lorsqu'un de ces trous est comblé sans mettre le suivi à jour.
COMPONENTS_WITHOUT_CONTRACT = ("C-002-identity-page",)

# Schéma de test : il porte les contraintes que les schémas du dépôt n'ont pas
# encore, pour prouver que la validation rejette réellement.
_FINDING_LIKE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["id", "title", "severity"],
    "properties": {
        "id": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1},
        "severity": {"enum": ["low", "medium", "high", "critical"]},
        "evidence_ids": {"type": "array", "items": {"type": "string", "minLength": 1}},
    },
}

_VALID_FRAGMENT = {
    "id": "finding-001",
    "title": "Blocage observé",
    "severity": "high",
    "evidence_ids": ["evidence-001"],
}


# --- Mécanisme ------------------------------------------------------------


def test_valid_fragment_produces_no_error():
    assert (
        adc_contracts.validation_errors(
            _VALID_FRAGMENT, _FINDING_LIKE_SCHEMA, component="C-004-finding"
        )
        == ()
    )


def test_invalid_fragment_names_the_component_and_the_field():
    fragment = dict(_VALID_FRAGMENT, severity="urgent")
    errors = adc_contracts.validation_errors(
        fragment, _FINDING_LIKE_SCHEMA, component="C-004-finding"
    )
    assert len(errors) == 1
    assert errors[0].startswith("C-004-finding: $.severity: ")


def test_missing_required_field_is_reported_at_the_root():
    fragment = {"title": "Sans identifiant", "severity": "high"}
    errors = adc_contracts.validation_errors(
        fragment, _FINDING_LIKE_SCHEMA, component="C-004-finding"
    )
    assert len(errors) == 1
    assert errors[0].startswith("C-004-finding: $: ")
    assert "'id'" in errors[0]


def test_nested_error_carries_its_path():
    fragment = dict(_VALID_FRAGMENT, evidence_ids=["evidence-001", 42])
    errors = adc_contracts.validation_errors(
        fragment, _FINDING_LIKE_SCHEMA, component="C-004-finding"
    )
    assert errors[0].startswith("C-004-finding: $.evidence_ids[1]: ")


def test_several_errors_are_ordered_by_position():
    fragment = {"id": "", "severity": "urgent"}
    errors = adc_contracts.validation_errors(
        fragment, _FINDING_LIKE_SCHEMA, component="C-004-finding"
    )
    paths = [error.split(": ")[1] for error in errors]
    assert paths == ["$", "$.id", "$.severity"]


def test_malformed_schema_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(adc_contracts, "COMPONENTS_DIR", tmp_path)
    component = tmp_path / "C-999-cassé"
    component.mkdir()
    (component / "schema.json").write_text(json.dumps({"type": "objet"}), encoding="utf-8")
    with pytest.raises(SchemaError):
        adc_contracts.load_schema("C-999-cassé")


def test_unreadable_json_names_the_file(tmp_path, monkeypatch):
    monkeypatch.setattr(adc_contracts, "COMPONENTS_DIR", tmp_path)
    component = tmp_path / "C-999-illisible"
    component.mkdir()
    (component / "schema.json").write_text("{ pas du json", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON invalide"):
        adc_contracts.load_schema("C-999-illisible")


# --- État du dépôt --------------------------------------------------------


def test_components_are_discovered():
    ids = adc_contracts.component_ids()
    assert "C-001-cover" in ids
    assert len(ids) >= 10


@pytest.mark.parametrize("component_id", adc_contracts.component_ids())
def test_component_contract_is_complete_and_consistent(component_id):
    if component_id in COMPONENTS_WITHOUT_CONTRACT:
        pytest.skip("contrat non encore rédigé — suivi par le test d'inventaire")
    assert adc_contracts.schema_path(component_id).is_file()
    assert adc_contracts.example_path(component_id).is_file(), "exemple manquant"
    adc_contracts.load_schema(component_id)  # schéma lui-même valide
    assert adc_contracts.example_errors(component_id) == ()


# --- C-003 Executive Summary ----------------------------------------------

C_003 = "C-003-executive-summary"
_SUMMARY_FIELDS = ("context", "business_impact", "conclusion", "recommended_action")


def _summary_errors(fragment) -> tuple[str, ...]:
    return adc_contracts.validation_errors(
        fragment, adc_contracts.load_schema(C_003), component=C_003
    )


def test_executive_summary_of_the_reference_report_is_valid():
    """Le durcissement ne doit pas invalider la source de référence."""
    source = json.loads(
        (
            adc_contracts.ROOT
            / "reference_reports"
            / "incident_report"
            / "data"
            / "sql_server_2014_incident.json"
        ).read_text(encoding="utf-8-sig")
    )
    assert _summary_errors(source["executive_summary"]) == ()


@pytest.mark.parametrize("field", _SUMMARY_FIELDS)
def test_executive_summary_accepts_a_single_field(field):
    # Aucun volet n'est requis : la composition tolère leur absence, le schéma
    # ne prétend donc pas l'inverse.
    assert _summary_errors({field: "Texte."}) == ()


def test_executive_summary_accepts_an_empty_fragment():
    assert _summary_errors({}) == ()


@pytest.mark.parametrize("value", [["Paragraphe"], 42, None, {"texte": "x"}])
def test_executive_summary_rejects_a_non_string_field(value):
    errors = _summary_errors({"context": value})
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_003}: $.context: ")


def test_executive_summary_rejects_an_unknown_field():
    errors = _summary_errors({"context": "Texte.", "impact_technique": "Hors contrat."})
    assert len(errors) == 1
    assert "impact_technique" in errors[0]


def test_executive_summary_rejects_a_non_object_fragment():
    errors = _summary_errors(["Texte."])
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_003}: $: ")


def test_executive_summary_example_covers_every_field():
    # L'exemple est la première preuve positive du contrat : il doit démontrer
    # le contrat entier, pas un sous-ensemble commode.
    example = adc_contracts.load_json(adc_contracts.example_path(C_003))
    assert set(example) == set(_SUMMARY_FIELDS)


def test_components_without_contract_are_exactly_the_declared_ones():
    """Suivi explicite des trous restants, plutôt qu'un silence.

    Ce test échoue dans les deux sens : un contrat rédigé sans mise à jour du
    suivi, comme un composant nouveau ou régressé sans contrat.
    """
    missing = tuple(c for c in adc_contracts.component_ids() if not adc_contracts.has_contract(c))
    assert missing == COMPONENTS_WITHOUT_CONTRACT
