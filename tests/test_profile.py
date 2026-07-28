"""Tests du profil documentaire : contrat minimal et pilotage de l'ordre.

Le test clé est `test_swapping_two_components_swaps_the_ir` : inverser deux
blocs dans le YAML doit inverser l'IR, sans toucher une ligne de moteur.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from adc_engine import compose_document
from adc_engine.compose import incident_profile
from adc_profile import load_profile, resolve

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "profiles" / "p-003-incident-report.yaml"
DATA = ROOT / "reference_reports" / "incident_report" / "data" / "sql_server_2014_incident.json"


def _data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8-sig"))


def _raw_profile() -> dict:
    return yaml.safe_load(PROFILE.read_text(encoding="utf-8"))


def _write_profile(path: Path, document: dict) -> Path:
    path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


# --- Contrat minimal ------------------------------------------------------


def test_incident_profile_declares_the_report_structure():
    profile = incident_profile()
    assert profile.id == "P-003"
    entries = {(e.component_id, e.instance_id): e for e in profile.entries}
    cover = entries[("C-001-cover", "cover")]
    assert (cover.minimum, cover.maximum) == (1, 1)
    timeline = entries[("C-008-timeline", "timeline")]
    assert (timeline.minimum, timeline.maximum) == (0, 1)
    finding = entries[("C-004-finding", None)]
    assert (finding.minimum, finding.maximum) == (0, None)  # illimité


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        ({"min": 1, "max": 1}, "champ 'type' requis"),
        ({"type": "C-001-cover", "max": 1}, "champ 'min' requis"),
        ({"type": "C-001-cover", "min": 1}, "champ 'max' requis"),
        ({"type": "C-001-cover", "min": 2, "max": 1}, "inférieur à 'min'"),
        ({"type": "C-001-cover", "min": 0, "max": -1}, "inférieur à 'min'"),
        ({"type": "C-001-cover", "instance": "cover", "min": 0, "max": None}, "au plus une"),
        ({"type": "C-001-cover", "instance": "", "min": 1, "max": 1}, "champ 'instance' optionnel"),
        ("pas un objet", "objet attendu"),
    ],
)
def test_invalid_entry_is_rejected_with_its_position(tmp_path, entry, message):
    path = _write_profile(tmp_path / "profile.yaml", {"id": "P-999", "components": [entry]})
    with pytest.raises(ValueError) as error:
        load_profile(path)
    assert "components[0]" in str(error.value)
    assert message in str(error.value)


def test_profile_without_components_is_rejected(tmp_path):
    path = _write_profile(tmp_path / "profile.yaml", {"id": "P-999", "components": []})
    with pytest.raises(ValueError, match=r"\$\.components"):
        load_profile(path)


def test_duplicate_repeatable_block_is_rejected(tmp_path):
    # Deux entrées sans `instance` pour un même type se confondent : c'est la
    # cardinalité qui exprime la répétition, pas la répétition de l'entrée.
    entry = {"type": "C-004-finding", "min": 0, "max": None}
    path = _write_profile(tmp_path / "profile.yaml", {"id": "P-999", "components": [entry, entry]})
    with pytest.raises(ValueError, match="déclaré deux fois"):
        load_profile(path)


def test_duplicate_named_block_is_rejected(tmp_path):
    entry = {"type": "narrative", "instance": "conclusion", "min": 1, "max": 1}
    path = _write_profile(tmp_path / "profile.yaml", {"id": "P-999", "components": [entry, entry]})
    with pytest.raises(ValueError, match="déclaré deux fois"):
        load_profile(path)


def test_same_type_with_distinct_instances_is_accepted(tmp_path):
    # Le couple (type, instance) est la clé : plusieurs blocs narratifs nommés
    # coexistent sans créer de faux types de composants.
    document = {
        "id": "P-999",
        "components": [
            {"type": "narrative", "instance": "incident-context", "min": 1, "max": 1},
            {"type": "narrative", "instance": "conclusion", "min": 1, "max": 1},
        ],
    }
    profile = load_profile(_write_profile(tmp_path / "profile.yaml", document))
    assert [e.instance_id for e in profile.entries] == ["incident-context", "conclusion"]


# --- Le profil pilote réellement l'ordre ----------------------------------


def test_swapping_two_components_swaps_the_ir(tmp_path):
    document = _raw_profile()
    components = document["components"]
    positions = {c.get("type"): i for i, c in enumerate(components)}
    left, right = positions["C-005-recommendation"], positions["C-006-risk"]
    components[left], components[right] = components[right], components[left]
    swapped = load_profile(_write_profile(tmp_path / "profile.yaml", document))

    reference = [c.component_id for c in compose_document(_data()).components]
    modified = [c.component_id for c in compose_document(_data(), swapped).components]

    assert reference.index("C-005-recommendation") < reference.index("C-006-risk")
    assert modified.index("C-006-risk") < modified.index("C-005-recommendation")
    # Seul l'ordre change : aucun composant n'apparaît ni ne disparaît.
    assert sorted(modified) == sorted(reference)


def test_removing_a_component_removes_it_from_the_ir(tmp_path):
    document = _raw_profile()
    document["components"] = [c for c in document["components"] if c.get("type") != "C-006-risk"]
    profile = load_profile(_write_profile(tmp_path / "profile.yaml", document))
    composed = compose_document(_data(), profile)
    assert not any(c.component_id == "C-006-risk" for c in composed.components)
    assert any(c.component_id == "C-005-recommendation" for c in composed.components)


# --- Cardinalités ---------------------------------------------------------


def test_mandatory_block_without_source_is_diagnosed_not_fabricated(tmp_path):
    # La cause probable devient obligatoire alors que la source ne la porte pas.
    document = _raw_profile()
    for component in document["components"]:
        if component.get("instance") == "probable-cause":
            component["min"] = 1
    profile = load_profile(_write_profile(tmp_path / "profile.yaml", document))

    data = _data()
    data.pop("probable_cause")
    blocks, diagnostics = resolve(data, profile)

    assert not any(instance == "probable-cause" for _, instance in blocks)  # rien de fabriqué
    assert any(
        "cardinalité non respectée: narrative :: 1 occurrence(s) au minimum, 0 obtenue(s)" == d
        for d in diagnostics
    )


def test_optional_block_absent_produces_no_diagnostic():
    data = _data()
    data.pop("timeline")
    _, diagnostics = resolve(data, incident_profile())
    assert not any("C-008-timeline" in d for d in diagnostics)


def test_cardinality_violation_is_reported_with_the_expected_bounds(tmp_path):
    document = _raw_profile()
    for component in document["components"]:
        if component.get("type") == "C-004-finding":
            component["min"], component["max"] = 2, 3
    profile = load_profile(_write_profile(tmp_path / "profile.yaml", document))
    composed = compose_document(_data(), profile)  # la source ne porte qu'un constat
    assert any(
        "cardinalité non respectée: C-004-finding :: 2 occurrence(s) au minimum, 1 obtenue(s)" == d
        for d in composed.diagnostics
    )
    # Aucune occurrence fabriquée pour satisfaire le minimum.
    assert len([c for c in composed.components if c.component_id == "C-004-finding"]) == 1


def test_unknown_block_is_diagnosed_not_silently_dropped(tmp_path):
    document = _raw_profile()
    document["components"].append({"type": "C-404-inconnu", "min": 0, "max": None})
    profile = load_profile(_write_profile(tmp_path / "profile.yaml", document))
    composed = compose_document(_data(), profile)
    assert any("source d'occurrences inconnue: C-404-inconnu" in d for d in composed.diagnostics)


def test_unsupported_narrative_blocks_stay_diagnosed():
    composed = compose_document(_data())
    for instance_id in ("probable-cause", "conclusion"):
        assert any(f"narrative :: {instance_id}" in d for d in composed.diagnostics)
    assert any("narrative-investigation :: investigation-001" in d for d in composed.diagnostics)
