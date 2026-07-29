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

# Composants sans contrat déclaré. La liste est vide depuis le durcissement de
# C-002 : elle reste explicite pour qu'un composant nouveau ou régressé fasse
# échouer le suivi plutôt que de passer inaperçu.
COMPONENTS_WITHOUT_CONTRACT: tuple[str, ...] = ()

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


def _reference_source() -> dict:
    """Source du rapport de référence : aucun durcissement ne doit l'invalider."""
    path = (
        adc_contracts.ROOT
        / "reference_reports"
        / "incident_report"
        / "data"
        / "sql_server_2014_incident.json"
    )
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_executive_summary_of_the_reference_report_is_valid():
    assert _summary_errors(_reference_source()["executive_summary"]) == ()


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


# --- C-009 Environment -----------------------------------------------------

C_009 = "C-009-environment"


def _environment_errors(fragment) -> tuple[str, ...]:
    return adc_contracts.validation_errors(
        fragment, adc_contracts.load_schema(C_009), component=C_009
    )


def test_environment_of_the_reference_report_is_valid():
    assert _environment_errors(_reference_source()["environment"]) == ()


def test_environment_accepts_a_partial_fragment():
    # Aucun champ requis : la composition tolère l'absence, le schéma aussi.
    assert _environment_errors({"server_name": "SRV-01"}) == ()
    assert _environment_errors({}) == ()


def test_environment_rejects_a_fractional_cpu_count():
    # Un décompte de processeurs logiques est entier par nature.
    errors = _environment_errors({"cpu_logical_count": 40.5})
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_009}: $.cpu_logical_count: ")


def test_environment_accepts_a_fractional_memory():
    # Quantité et non décompte : aucune règle n'impose un entier.
    assert _environment_errors({"memory_gb": 62.5}) == ()


def test_environment_rejects_an_unknown_field():
    errors = _environment_errors({"server_name": "SRV-01", "virtualisation": "VMware"})
    assert len(errors) == 1
    assert "virtualisation" in errors[0]


def test_storage_accepts_an_unmeasured_allocation_unit():
    fragment = {"storage": [{"volume": "C:", "role": "Système", "allocation_unit_kb": None}]}
    assert _environment_errors(fragment) == ()


def test_storage_rejects_a_textual_allocation_unit():
    fragment = {"storage": [{"volume": "D:", "role": "SQL", "allocation_unit_kb": "64"}]}
    errors = _environment_errors(fragment)
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_009}: $.storage[0].allocation_unit_kb: ")


def test_storage_rejects_an_unknown_field_inside_a_volume():
    fragment = {"storage": [{"volume": "D:", "taille_go": 500}]}
    errors = _environment_errors(fragment)
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_009}: $.storage[0]: ")


def test_storage_rejects_a_non_object_entry():
    errors = _environment_errors({"storage": ["D:"]})
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_009}: $.storage[0]: ")


def test_environment_example_covers_the_whole_contract():
    example = adc_contracts.load_json(adc_contracts.example_path(C_009))
    schema = adc_contracts.load_schema(C_009)
    assert set(example) == set(schema["properties"])
    volume_fields = schema["properties"]["storage"]["items"]["properties"]
    assert all(set(volume) == set(volume_fields) for volume in example["storage"])


# --- C-008 Timeline --------------------------------------------------------

C_008 = "C-008-timeline"


def _timeline_errors(fragment) -> tuple[str, ...]:
    return adc_contracts.validation_errors(
        fragment, adc_contracts.load_schema(C_008), component=C_008
    )


def test_timeline_of_the_reference_report_is_valid():
    assert _timeline_errors(_reference_source()["timeline"]) == ()


def test_timeline_accepts_an_empty_collection():
    # Cardinalité et présence relèvent du profil, pas du schéma local.
    assert _timeline_errors([]) == ()


def test_timeline_accepts_a_partial_entry():
    assert _timeline_errors([{"title": "Signalement"}]) == ()


@pytest.mark.parametrize(
    "timestamp",
    ["2026-07-23", "2026-07-23T10:15:00Z", "23/07/2026", "matinée du 23 juillet"],
)
def test_timeline_imposes_no_timestamp_format(timestamp):
    # Aucun format n'est attesté : le nom du champ ne fait pas contrat.
    assert _timeline_errors([{"id": "timeline-001", "timestamp": timestamp}]) == ()


def test_timeline_rejects_a_non_textual_timestamp():
    errors = _timeline_errors([{"id": "timeline-001", "timestamp": 20260723}])
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_008}: $[0].timestamp: ")


def test_timeline_rejects_an_empty_identifier():
    errors = _timeline_errors([{"id": ""}])
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_008}: $[0].id: ")


def test_timeline_rejects_an_unknown_field():
    errors = _timeline_errors([{"id": "timeline-001", "auteur": "A.D.C. srl"}])
    assert len(errors) == 1
    assert "auteur" in errors[0]


def test_timeline_rejects_a_non_object_entry():
    errors = _timeline_errors(["2026-07-23"])
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_008}: $[0]: ")


def test_timeline_rejects_a_non_array_fragment():
    errors = _timeline_errors({"entries": []})
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_008}: $: ")


def test_timeline_says_nothing_about_order():
    # Propriété globale : elle appartient à la composition et à ses tests.
    unordered = [
        {"id": "timeline-002", "timestamp": "2026-07-24"},
        {"id": "timeline-001", "timestamp": "2026-07-23"},
    ]
    assert _timeline_errors(unordered) == ()
    assert _timeline_errors(list(reversed(unordered))) == ()


def test_timeline_example_covers_the_whole_contract():
    example = adc_contracts.load_json(adc_contracts.example_path(C_008))
    entry_fields = adc_contracts.load_schema(C_008)["items"]["properties"]
    assert example, "exemple vide : il ne démontrerait aucun contrat"
    assert all(set(entry) == set(entry_fields) for entry in example)


# --- C-004 Finding ---------------------------------------------------------

C_004 = "C-004-finding"
_FINDING_REQUIRED = ("id", "title", "severity", "observation", "impact", "analysis", "evidence_ids")


def _finding_errors(fragment) -> tuple[str, ...]:
    return adc_contracts.validation_errors(
        fragment, adc_contracts.load_schema(C_004), component=C_004
    )


def _valid_finding() -> dict:
    return adc_contracts.load_json(adc_contracts.example_path(C_004))


def test_finding_of_the_reference_report_is_valid():
    # Le schéma décrit une occurrence : c'est bien une entrée qui est validée.
    for finding in _reference_source()["findings"]:
        assert _finding_errors(finding) == ()


@pytest.mark.parametrize("field", _FINDING_REQUIRED)
def test_finding_requires_every_field_the_validator_requires(field):
    # `required` est ici attesté : le validateur exige déjà ces sept champs.
    fragment = {k: v for k, v in _valid_finding().items() if k != field}
    errors = _finding_errors(fragment)
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_004}: $: ")
    assert f"'{field}'" in errors[0]


@pytest.mark.parametrize("severity", ["low", "medium", "high", "critical"])
def test_finding_accepts_the_canonical_vocabulary(severity):
    assert _finding_errors(dict(_valid_finding(), severity=severity)) == ()


@pytest.mark.parametrize("severity", ["urgent", "High", "élevée", 3, None])
def test_finding_rejects_a_severity_outside_the_vocabulary(severity):
    # Vocabulaire fermé attesté par le validateur, y compris sa casse.
    errors = _finding_errors(dict(_valid_finding(), severity=severity))
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_004}: $.severity: ")


def test_finding_accepts_an_empty_reference_list():
    assert _finding_errors(dict(_valid_finding(), evidence_ids=[])) == ()


def test_finding_rejects_a_non_textual_reference():
    errors = _finding_errors(dict(_valid_finding(), evidence_ids=["evidence-001", 42]))
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_004}: $.evidence_ids[1]: ")


def test_finding_rejects_an_empty_reference():
    errors = _finding_errors(dict(_valid_finding(), evidence_ids=[""]))
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_004}: $.evidence_ids[0]: ")


def test_finding_says_nothing_about_reference_resolvability():
    # Cible inexistante et doublon : formes valides ici, écarts pour le
    # validateur global. Le schéma ne connaît qu'une entrée à la fois.
    fragment = dict(_valid_finding(), evidence_ids=["evidence-404", "evidence-404"])
    assert _finding_errors(fragment) == ()


def test_finding_rejects_an_unknown_field():
    errors = _finding_errors(dict(_valid_finding(), recommandation="Hors contrat."))
    assert len(errors) == 1
    assert "recommandation" in errors[0]


def test_finding_rejects_a_collection_instead_of_an_occurrence():
    errors = _finding_errors([_valid_finding()])
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_004}: $: ")


def test_finding_example_covers_the_whole_contract():
    schema = adc_contracts.load_schema(C_004)
    assert set(_valid_finding()) == set(schema["properties"])


# --- C-005 Recommendation --------------------------------------------------

C_005 = "C-005-recommendation"
_RECOMMENDATION_REQUIRED = (
    "id",
    "title",
    "priority",
    "description",
    "rationale",
    "related_finding_ids",
)


def _recommendation_errors(fragment) -> tuple[str, ...]:
    return adc_contracts.validation_errors(
        fragment, adc_contracts.load_schema(C_005), component=C_005
    )


def _valid_recommendation() -> dict:
    return adc_contracts.load_json(adc_contracts.example_path(C_005))


def test_recommendation_of_the_reference_report_is_valid():
    for recommendation in _reference_source()["recommendations"]:
        assert _recommendation_errors(recommendation) == ()


@pytest.mark.parametrize("field", _RECOMMENDATION_REQUIRED)
def test_recommendation_requires_every_field_the_validator_requires(field):
    fragment = {k: v for k, v in _valid_recommendation().items() if k != field}
    errors = _recommendation_errors(fragment)
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_005}: $: ")
    assert f"'{field}'" in errors[0]


@pytest.mark.parametrize("priority", ["low", "medium", "high", "critical"])
def test_recommendation_accepts_the_canonical_vocabulary(priority):
    assert _recommendation_errors(dict(_valid_recommendation(), priority=priority)) == ()


@pytest.mark.parametrize("priority", ["urgent", "High", "élevée", 3, None])
def test_recommendation_rejects_a_priority_outside_the_vocabulary(priority):
    errors = _recommendation_errors(dict(_valid_recommendation(), priority=priority))
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_005}: $.priority: ")


def test_recommendation_accepts_an_empty_reference_list():
    assert _recommendation_errors(dict(_valid_recommendation(), related_finding_ids=[])) == ()


def test_recommendation_rejects_a_non_textual_reference():
    fragment = dict(_valid_recommendation(), related_finding_ids=["finding-001", 42])
    errors = _recommendation_errors(fragment)
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_005}: $.related_finding_ids[1]: ")


def test_recommendation_rejects_an_empty_reference():
    errors = _recommendation_errors(dict(_valid_recommendation(), related_finding_ids=[""]))
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_005}: $.related_finding_ids[0]: ")


def test_recommendation_says_nothing_about_reference_resolvability():
    # Même partage que pour les preuves d'un constat : cible inexistante et
    # doublon sont des formes valides ici, des écarts pour le validateur.
    fragment = dict(_valid_recommendation(), related_finding_ids=["finding-404", "finding-404"])
    assert _recommendation_errors(fragment) == ()


def test_recommendation_rejects_an_unknown_field():
    errors = _recommendation_errors(dict(_valid_recommendation(), echeance="2026-09-01"))
    assert len(errors) == 1
    assert "echeance" in errors[0]


def test_recommendation_rejects_a_collection_instead_of_an_occurrence():
    errors = _recommendation_errors([_valid_recommendation()])
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_005}: $: ")


def test_recommendation_example_covers_the_whole_contract():
    schema = adc_contracts.load_schema(C_005)
    assert set(_valid_recommendation()) == set(schema["properties"])


# --- C-006 Risk ------------------------------------------------------------

C_006 = "C-006-risk"


def _risk_errors(fragment) -> tuple[str, ...]:
    return adc_contracts.validation_errors(
        fragment, adc_contracts.load_schema(C_006), component=C_006
    )


def _valid_risk() -> dict:
    return adc_contracts.load_json(adc_contracts.example_path(C_006))


def test_risk_of_the_reference_report_is_valid():
    for risk in _reference_source()["risks"]:
        assert _risk_errors(risk) == ()


def test_risk_requires_only_its_identifier():
    # Prérequis de consommation : le moteur instancie l'occurrence par son
    # identifiant. Rien d'autre n'est exigé, ni par le validateur ni par la
    # composition.
    assert _risk_errors({"id": "risk-001"}) == ()
    errors = _risk_errors({k: v for k, v in _valid_risk().items() if k != "id"})
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_006}: $: ")
    assert "'id'" in errors[0]


def test_risk_rejects_an_empty_identifier():
    errors = _risk_errors(dict(_valid_risk(), id=""))
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_006}: $.id: ")


@pytest.mark.parametrize("level", ["low", "high", "majeur", "P1", "à qualifier"])
def test_risk_level_is_deliberately_not_a_closed_vocabulary(level):
    """Absence d'`enum` assumée, pas oubliée (ADR-0010).

    Aucun vocabulaire n'est fermé pour ce champ : ni le validateur ni une
    règle documentée ne le font. Que le rendu sache traduire « high » relève
    de la présentation et n'atteste rien. Ne pas aligner sur `severity` ou
    `priority` par symétrie apparente.
    """
    assert _risk_errors(dict(_valid_risk(), level=level)) == ()


def test_risk_rejects_an_empty_level():
    errors = _risk_errors(dict(_valid_risk(), level=""))
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_006}: $.level: ")


def test_risk_says_nothing_about_reference_resolvability():
    fragment = dict(_valid_risk(), mitigation_recommendation_ids=["reco-404", "reco-404"])
    assert _risk_errors(fragment) == ()


def test_risk_rejects_a_non_textual_reference():
    fragment = dict(_valid_risk(), mitigation_recommendation_ids=["recommendation-001", 42])
    errors = _risk_errors(fragment)
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_006}: $.mitigation_recommendation_ids[1]: ")


def test_risk_rejects_an_unknown_field():
    errors = _risk_errors(dict(_valid_risk(), probabilite="moyenne"))
    assert len(errors) == 1
    assert "probabilite" in errors[0]


def test_risk_rejects_a_collection_instead_of_an_occurrence():
    errors = _risk_errors([_valid_risk()])
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_006}: $: ")


def test_risk_example_covers_the_whole_contract():
    schema = adc_contracts.load_schema(C_006)
    assert set(_valid_risk()) == set(schema["properties"])


# --- C-007 Decision --------------------------------------------------------

C_007 = "C-007-decision"


def _decision_errors(fragment) -> tuple[str, ...]:
    return adc_contracts.validation_errors(
        fragment, adc_contracts.load_schema(C_007), component=C_007
    )


def _valid_decision() -> dict:
    return adc_contracts.load_json(adc_contracts.example_path(C_007))


def test_decision_of_the_reference_report_is_valid():
    for decision in _reference_source()["actions_taken"]:
        assert _decision_errors(decision) == ()


def test_decision_requires_only_its_identifier():
    assert _decision_errors({"id": "decision-001"}) == ()
    errors = _decision_errors({k: v for k, v in _valid_decision().items() if k != "id"})
    assert len(errors) == 1
    assert "'id'" in errors[0]


def test_decision_rejects_an_empty_identifier():
    errors = _decision_errors(dict(_valid_decision(), id=""))
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_007}: $.id: ")


@pytest.mark.parametrize("status", ["completed", "in_progress", "planifiée", "à confirmer"])
def test_decision_status_is_deliberately_not_a_closed_vocabulary(status):
    """Absence d'`enum` assumée, pas oubliée (ADR-0010).

    Le validateur n'impose aucun vocabulaire pour ce champ. Que le rendu
    sache présenter « completed » relève de la présentation.
    """
    assert _decision_errors(dict(_valid_decision(), status=status)) == ()


def test_decision_rejects_an_empty_status():
    errors = _decision_errors(dict(_valid_decision(), status=""))
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_007}: $.status: ")


def test_decision_rejects_an_unknown_field():
    errors = _decision_errors(dict(_valid_decision(), responsable="A.D.C. srl"))
    assert len(errors) == 1
    assert "responsable" in errors[0]


def test_decision_rejects_a_collection_instead_of_an_occurrence():
    errors = _decision_errors([_valid_decision()])
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_007}: $: ")


def test_decision_example_covers_the_whole_contract():
    schema = adc_contracts.load_schema(C_007)
    assert set(_valid_decision()) == set(schema["properties"])


# --- C-010 Evidence --------------------------------------------------------

C_010 = "C-010-evidence"


def _evidence_errors(fragment) -> tuple[str, ...]:
    return adc_contracts.validation_errors(
        fragment, adc_contracts.load_schema(C_010), component=C_010
    )


def _valid_evidence() -> dict:
    return adc_contracts.load_json(adc_contracts.example_path(C_010))


def test_evidence_of_the_reference_report_is_valid():
    for evidence in _reference_source()["evidence"]:
        assert _evidence_errors(evidence) == ()


def test_evidence_requires_only_its_identifier():
    # Ici l'identifiant est attesté deux fois : le validateur l'exige pour
    # cette collection, et le moteur instancie l'occurrence par lui.
    assert _evidence_errors({"id": "evidence-001"}) == ()
    errors = _evidence_errors({k: v for k, v in _valid_evidence().items() if k != "id"})
    assert len(errors) == 1
    assert "'id'" in errors[0]


def test_evidence_rejects_an_empty_identifier():
    errors = _evidence_errors(dict(_valid_evidence(), id=""))
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_010}: $.id: ")


@pytest.mark.parametrize(
    "kind", ["technical_observation", "log_extract", "capture d'écran", "témoignage"]
)
def test_evidence_kind_is_deliberately_not_a_closed_vocabulary(kind):
    """Absence d'`enum` assumée, pas oubliée (ADR-0010).

    La donnée de référence porte « technical_observation », mais rien ne
    ferme la liste des natures de preuve.
    """
    assert _evidence_errors(dict(_valid_evidence(), kind=kind)) == ()


@pytest.mark.parametrize("source", ["Serveur SRV-SQL-01", "annexe-A.pdf", "Entretien client"])
def test_evidence_source_imposes_no_convention(source):
    assert _evidence_errors(dict(_valid_evidence(), source=source)) == ()


def test_evidence_rejects_an_empty_kind():
    errors = _evidence_errors(dict(_valid_evidence(), kind=""))
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_010}: $.kind: ")


def test_evidence_rejects_an_unknown_field():
    errors = _evidence_errors(dict(_valid_evidence(), hash_sha256="…"))
    assert len(errors) == 1
    assert "hash_sha256" in errors[0]


def test_evidence_rejects_a_collection_instead_of_an_occurrence():
    errors = _evidence_errors([_valid_evidence()])
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_010}: $: ")


def test_evidence_example_covers_the_whole_contract():
    schema = adc_contracts.load_schema(C_010)
    assert set(_valid_evidence()) == set(schema["properties"])


# --- C-001 Cover -----------------------------------------------------------

C_001 = "C-001-cover"
_COVER_REPORT_FIELDS = (
    "title",
    "subtitle",
    "reference",
    "version",
    "date",
    "author",
    "confidentiality",
)


def _cover_errors(fragment) -> tuple[str, ...]:
    return adc_contracts.validation_errors(
        fragment, adc_contracts.load_schema(C_001), component=C_001
    )


def _valid_cover() -> dict:
    return adc_contracts.load_json(adc_contracts.example_path(C_001))


def test_cover_of_the_reference_report_is_valid():
    # Le builder de la couverture reçoit la source entière et y prélève deux
    # noeuds : c'est donc bien la racine que ce contrat valide.
    assert _cover_errors(_reference_source()) == ()


@pytest.mark.parametrize("node", ["report", "client"])
def test_cover_requires_the_two_nodes_the_validator_requires(node):
    fragment = {k: v for k, v in _valid_cover().items() if k != node}
    errors = _cover_errors(fragment)
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_001}: $: ")
    assert f"'{node}'" in errors[0]


def test_cover_requires_no_field_inside_those_nodes():
    # Aucun champ n'est un prérequis de consommation : la couverture se compose
    # et se rend sans titre. Un titre absent est une restitution dégradée, pas
    # un contrat violé (ADR-0010).
    assert _cover_errors({"report": {}, "client": {}}) == ()


@pytest.mark.parametrize(
    "fragment",
    [
        {"report": {"id": "ADC-MECA-2026-SQL2014-001"}, "client": {}},
        {"report": {"language": "fr-BE"}, "client": {}},
        {"report": {"revisions": [{"version": "0.1-draft"}]}, "client": {}},
        {"report": {}, "client": {"vat_number": "BE0123456789"}},
        {"report": {}, "client": {}, "conclusion": "Hors du fragment de la couverture."},
    ],
)
def test_cover_does_not_close_a_shared_node(fragment):
    """Ouverture assumée, pas un durcissement oublié (ADR-0010).

    `report` et `client` sont lus par C-002 comme par C-001, et la racine porte
    les noeuds de tous les autres composants. Fermer l'un d'eux ici ferait
    rejeter par la couverture des champs qu'un autre composant consomme
    légitimement. Ne pas ajouter d'`additionalProperties: false`.
    """
    assert _cover_errors(fragment) == ()


@pytest.mark.parametrize("field", _COVER_REPORT_FIELDS)
def test_cover_rejects_a_non_textual_report_field(field):
    errors = _cover_errors({"report": {field: 42}, "client": {}})
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_001}: $.report.{field}: ")


def test_cover_rejects_a_non_textual_client_name():
    errors = _cover_errors({"report": {}, "client": {"name": ["Soc01"]}})
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_001}: $.client.name: ")


@pytest.mark.parametrize("date", ["2026-07-28", "28/07/2026", "juillet 2026"])
def test_cover_imposes_no_date_format(date):
    # Comme l'horodatage d'un événement : le nom du champ ne fait pas contrat,
    # la valeur est imprimée telle quelle.
    assert _cover_errors({"report": {"date": date}, "client": {}}) == ()


@pytest.mark.parametrize(
    "confidentiality", ["Confidentiel", "Public", "Diffusion restreinte", "TLP:AMBER"]
)
def test_cover_confidentiality_is_deliberately_not_a_closed_vocabulary(confidentiality):
    """Absence d'`enum` assumée, pas oubliée (ADR-0010).

    Aucun vocabulaire n'est fermé pour cette mention : ni le validateur ni une
    règle documentée n'en arrête la liste. Que la donnée de référence porte
    « Confidentiel » n'atteste rien de plus.
    """
    assert _cover_errors({"report": {"confidentiality": confidentiality}, "client": {}}) == ()


@pytest.mark.parametrize("node", ["report", "client"])
def test_cover_rejects_a_textual_node(node):
    errors = _cover_errors(dict(_valid_cover(), **{node: "Soc01"}))
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_001}: $.{node}: ")


def test_cover_says_nothing_about_the_document_type():
    # Le type de document figure au payload mais pas au contrat : le builder le
    # pose, il ne le lit pas dans la source.
    schema = adc_contracts.load_schema(C_001)
    assert "document_type" not in schema["properties"]["report"]["properties"]
    assert "document_type" not in schema["properties"]


def test_cover_example_covers_the_whole_contract():
    example = _valid_cover()
    schema = adc_contracts.load_schema(C_001)
    assert set(example) == set(schema["properties"])
    assert set(example["report"]) == set(schema["properties"]["report"]["properties"])
    assert set(example["client"]) == set(schema["properties"]["client"]["properties"])


# --- C-002 Identity Page ---------------------------------------------------

C_002 = "C-002-identity-page"
_IDENTITY_TABLES = {
    "revisions": ("version", "date", "author", "summary"),
    "validations": ("role", "name", "date"),
    "distribution": ("name", "organisation", "role"),
}


def _identity_errors(fragment) -> tuple[str, ...]:
    return adc_contracts.validation_errors(
        fragment, adc_contracts.load_schema(C_002), component=C_002
    )


def _valid_identity() -> dict:
    return adc_contracts.load_json(adc_contracts.example_path(C_002))


def test_identity_page_of_the_reference_report_is_valid():
    # Comme la couverture, ce builder reçoit la source entière et y prélève
    # deux noeuds : c'est la racine qui est validée.
    assert _identity_errors(_reference_source()) == ()


@pytest.mark.parametrize("node", ["report", "client"])
def test_identity_page_requires_the_two_nodes_the_validator_requires(node):
    fragment = {k: v for k, v in _valid_identity().items() if k != node}
    errors = _identity_errors(fragment)
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_002}: $: ")
    assert f"'{node}'" in errors[0]


def test_identity_page_requires_no_field_inside_those_nodes():
    # Les trois collections sont facultatives : la source de référence n'en
    # porte aucune et l'identité se compose sans elles.
    assert _identity_errors({"report": {}, "client": {}}) == ()


@pytest.mark.parametrize(
    "fragment",
    [
        {"report": {"subtitle": "Analyse technique et recommandations"}, "client": {}},
        {"report": {}, "client": {"vat_number": "BE0123456789"}},
        {"report": {}, "client": {}, "environment": {"server_name": "SRV-01"}},
    ],
)
def test_identity_page_does_not_close_a_shared_node(fragment):
    """Ouverture assumée, pas un durcissement oublié (ADR-0010).

    `report` et `client` sont lus par C-001 comme par C-002 : le sous-titre est
    porté par la couverture, pas par cette page, et le rejeter ici ferait
    trancher un composant sur le contrat d'un autre.
    """
    assert _identity_errors(fragment) == ()


def test_identity_page_rejects_an_empty_report_identifier():
    errors = _identity_errors({"report": {"id": ""}, "client": {}})
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_002}: $.report.id: ")


@pytest.mark.parametrize("language", ["fr-BE", "fr", "français", "nl-BE"])
def test_identity_page_language_is_deliberately_not_a_closed_vocabulary(language):
    """Absence d'`enum` assumée, pas oubliée (ADR-0010).

    Aucune norme d'étiquetage n'est attestée : que la donnée de référence porte
    « fr-BE » n'en impose ni la forme ni la liste.
    """
    assert _identity_errors({"report": {"language": language}, "client": {}}) == ()


@pytest.mark.parametrize("table", sorted(_IDENTITY_TABLES))
def test_identity_page_accepts_an_empty_table(table):
    # Cardinalité et présence relèvent du profil, pas du schéma local.
    assert _identity_errors({"report": {table: []}, "client": {}}) == ()


@pytest.mark.parametrize("table", sorted(_IDENTITY_TABLES))
def test_identity_page_accepts_a_partial_row(table):
    field = _IDENTITY_TABLES[table][0]
    assert _identity_errors({"report": {table: [{field: "x"}]}, "client": {}}) == ()


@pytest.mark.parametrize("table", sorted(_IDENTITY_TABLES))
def test_identity_page_closes_the_tables_it_owns(table):
    """Fermeture assumée : ces collections ne sont lues que par ce composant.

    Le partage se constate noeud par noeud et ne s'hérite pas (ADR-0010) :
    `report` reste ouvert, ses trois tableaux non.
    """
    errors = _identity_errors({"report": {table: [{"commentaire": "Hors contrat."}]}, "client": {}})
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_002}: $.report.{table}[0]: ")
    assert "commentaire" in errors[0]


@pytest.mark.parametrize("table", sorted(_IDENTITY_TABLES))
def test_identity_page_rejects_a_non_object_row(table):
    # Le builder ignore silencieusement une entrée non conforme : tolérance
    # d'implémentation, hors contrat (ADR-0010).
    errors = _identity_errors({"report": {table: ["0.1-draft"]}, "client": {}})
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_002}: $.report.{table}[0]: ")


@pytest.mark.parametrize("table", sorted(_IDENTITY_TABLES))
def test_identity_page_rejects_a_non_array_table(table):
    errors = _identity_errors({"report": {table: {}}, "client": {}})
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_002}: $.report.{table}: ")


def test_identity_page_says_nothing_about_its_heading():
    # L'intitulé de la page figure au payload mais pas au contrat : le builder
    # le pose, il ne le lit pas dans la source.
    assert "heading" not in adc_contracts.load_schema(C_002)["properties"]["report"]["properties"]


def test_identity_page_and_cover_describe_shared_fields_identically():
    """Un champ décrit par deux composants doit l'être de la même manière.

    Sans ce test, les sept champs que la couverture et l'identité lisent tous
    deux dériveraient au fil des durcissements, et la source n'aurait plus de
    forme canonique unique (ADR-0010).
    """
    cover = adc_contracts.load_schema(C_001)["properties"]
    identity = adc_contracts.load_schema(C_002)["properties"]
    for node in ("report", "client"):
        shared = set(cover[node]["properties"]) & set(identity[node]["properties"])
        assert shared, f"aucun champ partagé sur `{node}` : hypothèse du test caduque"
        for field in shared:
            expected = {k: v for k, v in cover[node]["properties"][field].items() if k != "description"}
            actual = {k: v for k, v in identity[node]["properties"][field].items() if k != "description"}
            assert actual == expected, f"contrats divergents sur `{node}.{field}`"


def test_identity_page_example_covers_the_whole_contract():
    example = _valid_identity()
    schema = adc_contracts.load_schema(C_002)
    assert set(example) == set(schema["properties"])
    report_fields = schema["properties"]["report"]["properties"]
    assert set(example["report"]) == set(report_fields)
    assert set(example["client"]) == set(schema["properties"]["client"]["properties"])
    for table, fields in _IDENTITY_TABLES.items():
        assert set(report_fields[table]["items"]["properties"]) == set(fields)
        assert example["report"][table], f"tableau `{table}` vide : il ne démontrerait rien"
        assert all(set(row) == set(fields) for row in example["report"][table])


def test_components_without_contract_are_exactly_the_declared_ones():
    """Suivi explicite des trous restants, plutôt qu'un silence.

    Ce test échoue dans les deux sens : un contrat rédigé sans mise à jour du
    suivi, comme un composant nouveau ou régressé sans contrat.
    """
    missing = tuple(c for c in adc_contracts.component_ids() if not adc_contracts.has_contract(c))
    assert missing == COMPONENTS_WITHOUT_CONTRACT


# --- C-011 Incident Context ------------------------------------------------
#
# Premier bloc narratif promu au catalogue (ADR-0013). Son contrat suit le motif
# de C-003 : un chapitre unique, objet plat, aucun champ requis, aucun champ
# inconnu toléré.

C_011 = "C-011-incident-context"
_CONTEXT_FIELDS = ("description", "trigger", "scope", "status")


def _context_errors(fragment) -> tuple[str, ...]:
    return adc_contracts.validation_errors(
        fragment, adc_contracts.load_schema(C_011), component=C_011
    )


def test_incident_context_of_the_reference_report_is_valid():
    assert _context_errors(_reference_source()["incident_context"]) == ()


@pytest.mark.parametrize("field", _CONTEXT_FIELDS)
def test_incident_context_accepts_a_single_field(field):
    # Aucun champ n'est requis : un contexte partiellement rédigé se compose.
    assert _context_errors({field: "Texte."}) == ()


def test_incident_context_accepts_an_empty_fragment():
    # Vide n'est pas malformé (ADR-0012, G4) : le nœud présent et vide reste
    # une section à rédiger, que le contrat n'a aucune raison de refuser.
    assert _context_errors({}) == ()


def test_incident_context_rejects_a_misspelled_field():
    """Le cas de référence de la contractualisation (ADR-0013).

    `descriptio` traversait toute la chaîne sans un seul diagnostic et produisait
    une section vide. Le contrat est désormais propriétaire de la forme, et c'est
    la seule chose qui a changé pour ce bloc.
    """
    errors = _context_errors({"descriptio": "Tout le contexte rédigé."})
    assert len(errors) == 1
    assert "descriptio" in errors[0]


@pytest.mark.parametrize("value", [["Paragraphe"], 42, None, {"texte": "x"}])
def test_incident_context_rejects_a_non_string_field(value):
    errors = _context_errors({"description": value})
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_011}: $.description: ")


def test_incident_context_rejects_a_non_object_fragment():
    errors = _context_errors("Contexte libre.")
    assert len(errors) == 1
    assert errors[0].startswith(f"{C_011}: $: ")


def test_incident_context_leaves_the_status_vocabulary_open():
    """Aucune règle de domaine ne ferme `status` (ADR-0010).

    Que le renderer sache traduire `investigated` relève de la présentation et
    n'atteste rien : le fermer ici inventerait un vocabulaire, comme un `enum`
    sur le `level` d'un risque en inventerait un. Ce test tombera le jour où le
    domaine énoncera la liste — et ce jour-là, il devra être remplacé, pas
    contourné.
    """
    assert _context_errors({"status": "totalement_inventé"}) == ()


def test_incident_context_example_covers_every_field():
    example = adc_contracts.load_json(adc_contracts.example_path(C_011))
    assert set(example) == set(_CONTEXT_FIELDS)
