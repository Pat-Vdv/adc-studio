"""Passe d'observation du Workbench (ADR-0014).

Ce que ces tests prouvent n'est pas qu'un écran affiche quelque chose, mais que
l'instantané **porte les faits que les couches propriétaires ont produits**, sans
en ajouter ni en réécrire. C'est la surface qu'une interface consommera plus
tard ; elle est testée avant d'exister.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import adc_contracts
from adc_workbench import observe, observe_mission

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "reference_reports" / "incident_report" / "data" / "sql_server_2014_incident.json"


def _source() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8-sig"))


# --- Le parcours nominal ---------------------------------------------------


def test_a_clean_source_produces_a_document_and_no_diagnostic():
    snapshot = observe(_source())
    assert snapshot.document is not None
    assert snapshot.document.id == "ADC-MECA-2026-SQL2014-001"
    assert snapshot.contract_diagnostics == ()
    assert snapshot.source_diagnostics == ()
    assert snapshot.composition_diagnostics == ()


def test_the_resolution_is_observed_in_the_declared_order():
    # L'ordre vient du profil, via la résolution : l'instantané le transporte,
    # il ne le reconstitue pas.
    snapshot = observe(_source())
    assert [block.component_id for block in snapshot.resolution][:3] == [
        "C-001-cover",
        "C-002-identity-page",
        "C-003-executive-summary",
    ]
    assert all(block.composed for block in snapshot.resolution)


def test_every_component_of_the_ir_is_observed_with_its_payload():
    snapshot = observe(_source())
    composed = {(c.component_id, c.instance_id) for c in snapshot.components}
    resolved = {(b.component_id, b.instance_id) for b in snapshot.resolution}
    assert composed == resolved
    cover = next(c for c in snapshot.components if c.instance_id == "cover")
    assert cover.payload["client"] == "Soc01"


def test_the_snapshot_carries_the_canonical_vocabulary_untranslated():
    """Le français appartient au renderer (ADR-0009, I5).

    L'instantané observe l'IR : il porte donc `investigated`, jamais « Investigé ».
    """
    snapshot = observe(_source())
    context = next(c for c in snapshot.components if c.instance_id == "incident-context")
    assert context.payload["status"] == "investigated"
    assert "Investigé" not in json.dumps(context.payload, ensure_ascii=False)


# --- Les contrats ----------------------------------------------------------


def test_every_fragment_of_the_table_is_observed():
    snapshot = observe(_source())
    assert {c.key for c in snapshot.contracts} == set(adc_contracts.INCIDENT_REPORT_FRAGMENTS)


def test_a_catalog_component_carries_its_cardinality_from_the_profile():
    snapshot = observe(_source())
    cover = next(c for c in snapshot.contracts if c.key == "C-001-cover")
    assert (cover.minimum, cover.maximum) == (1, 1)
    assert cover.has_contract


def test_a_root_fragment_has_no_cardinality_rather_than_an_invented_one():
    """Rien ne relie un fragment racine à son entrée de profil (W2).

    La table l'indexe par nom de nœud, le profil par marqueur de bloc. Fabriquer
    ce lien ici l'inventerait ; le laisser vide rend l'écart visible.
    """
    snapshot = observe(_source())
    roots = [c for c in snapshot.contracts if c.nature == adc_contracts.ROOT_FRAGMENT]
    assert roots, "la table doit encore porter au moins un fragment racine"
    for fragment in roots:
        assert (fragment.minimum, fragment.maximum, fragment.instance_id) == (None, None, None)
        assert not fragment.has_contract


# --- Un contrat violé : la composition s'arrête, pas l'observation ---------


def test_a_contract_break_still_produces_a_snapshot():
    source = _source()
    source["findings"][0]["severity"] = "urgent"
    snapshot = observe(source)
    assert snapshot.document is None
    assert [d.component for d in snapshot.contract_diagnostics] == ["C-004-finding"]
    assert snapshot.contract_diagnostics[0].code == "enum"
    assert snapshot.components == ()


def test_the_business_validator_still_concludes_when_the_contract_is_broken():
    # Les deux validations sont indépendantes : un contrat violé n'empêche pas
    # de dire ce que le contenu a de fautif.
    source = _source()
    source["findings"][0]["severity"] = "urgent"
    source["recommendations"][0]["related_finding_ids"] = ["finding-404"]
    snapshot = observe(source)
    assert any(d.code == "unknown_reference" for d in snapshot.source_diagnostics)


def test_the_resolution_is_observed_even_without_a_document():
    source = _source()
    source["findings"][0]["severity"] = "urgent"
    snapshot = observe(source)
    assert snapshot.resolution, "la résolution ne dépend pas de la frontière"
    assert not any(block.composed for block in snapshot.resolution)


# --- Ce que l'instantané ne prétend pas savoir -----------------------------


def test_composition_diagnostics_are_carried_verbatim():
    """Chaînes libres, transportées telles quelles (W3).

    Les analyser pour en extraire un code ou un chemin reconstituerait une
    structure que le moteur ne produit pas. L'instantané préfère montrer
    l'absence de structure.
    """
    source = _source()
    source["probable_cause"]["supporting_finding_ids"] = ["finding-404"]
    snapshot = observe(source)
    assert snapshot.composition_diagnostics
    assert all(isinstance(d, str) for d in snapshot.composition_diagnostics)


def test_no_diagnostic_carries_a_severity():
    # Aucune couche n'en déclare : l'inventer ici serait la dérive qu'ADR-0010
    # interdit.
    snapshot = observe(_source())
    for view in (*snapshot.contract_diagnostics, *snapshot.source_diagnostics):
        assert not hasattr(view, "severity")


def test_a_source_that_is_not_an_object_is_observed_not_crashed():
    # Le cas où l'outil sert le plus est celui où la source est cassée.
    snapshot = observe(["pas une source"])
    assert snapshot.document is None
    assert snapshot.contract_diagnostics
    assert snapshot.resolution == ()
    assert any("résolution" in note for note in snapshot.observation_notes)


# --- Déterminisme (W4) -----------------------------------------------------


def test_two_passes_on_the_same_source_are_identical():
    source = _source()
    assert observe(source) == observe(copy.deepcopy(source))


# --- Depuis une mission ----------------------------------------------------


def test_a_mission_is_observed_through_its_bridge(tmp_path):
    (tmp_path / "metadata.yml").write_text(
        'client: "Soc01"\ntitre: "Blocage"\nauteur: "A.D.C. srl"\n', encoding="utf-8"
    )
    snapshot = observe_mission(tmp_path)
    assert snapshot.document is not None  # contractuellement valide, éditorialement vide
    assert snapshot.source_diagnostics, "les sections restant à rédiger sont visibles"


def test_observing_a_mission_writes_nothing(tmp_path):
    """W1, et R5 d'ADR-0011 : la source contractuelle n'est pas matérialisée."""
    (tmp_path / "metadata.yml").write_text('titre: "Blocage"\n', encoding="utf-8")
    observe_mission(tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["metadata.yml"]


def test_a_missing_mission_is_refused_by_its_bridge(tmp_path):
    with pytest.raises(FileNotFoundError):
        observe_mission(tmp_path)
