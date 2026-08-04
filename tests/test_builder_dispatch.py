"""Tests du dispatch des builders par identité de bloc.

Plusieurs blocs peuvent partager un `component_id` — c'est le cas des blocs
narratifs — et viser des builders différents sans qu'aucun ne change d'identité
de composant.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from adc_engine import compose
from adc_engine.compose import compose_document

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "reference_reports" / "incident_report" / "data" / "sql_server_2014_incident.json"


def _data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8-sig"))


def _payload(_data_source: dict, instance_id: str) -> dict:
    return {"origine": instance_id}


# --- Table des builders ---------------------------------------------------


def test_duplicate_builder_key_is_refused():
    with pytest.raises(ValueError, match="builder déclaré deux fois: narrative :: conclusion"):
        compose._registry(
            (
                ("narrative", "conclusion", _payload),
                ("narrative", "conclusion", _payload),
            )
        )


def test_duplicate_generic_builder_key_is_refused():
    with pytest.raises(ValueError, match=r"builder déclaré deux fois: C-004-finding :: \*"):
        compose._registry((("C-004-finding", None, _payload), ("C-004-finding", None, _payload)))


def test_named_and_generic_builders_coexist():
    registry = compose._registry(
        (("narrative", None, _payload), ("narrative", "conclusion", _payload))
    )
    assert set(registry) == {("narrative", None), ("narrative", "conclusion")}


# --- Règles de résolution -------------------------------------------------


def test_named_builder_takes_precedence(monkeypatch):
    def generic(_data_source, instance_id):
        return {"builder": "générique"}

    def named(_data_source, instance_id):
        return {"builder": "nommé"}

    monkeypatch.setattr(
        compose,
        "_BUILDERS",
        compose._registry((("narrative", None, generic), ("narrative", "conclusion", named))),
    )
    assert compose._builder_for("narrative", "conclusion")(None, "conclusion") == {
        "builder": "nommé"
    }
    # Bloc nommé sans entrée propre : c'est le générique qui prend le relais.
    assert compose._builder_for("narrative", "incident-context")(None, "incident-context") == {
        "builder": "générique"
    }


def test_named_block_never_falls_back_to_another_named_block(monkeypatch):
    monkeypatch.setattr(
        compose, "_BUILDERS", compose._registry((("narrative", "conclusion", _payload),))
    )
    assert compose._builder_for("narrative", "conclusion") is not None
    # Aucun repli silencieux vers le builder d'un autre bloc nommé.
    assert compose._builder_for("narrative", "incident-context") is None
    assert compose._builder_for("narrative", "probable-cause") is None


def test_missing_builder_is_still_diagnosed(monkeypatch):
    # Tous les blocs du rapport de référence ont désormais un builder : on
    # vérifie le diagnostic en retirant celui d'un bloc nommé.
    monkeypatch.setattr(
        compose,
        "_BUILDERS",
        compose._registry(
            tuple(
                (component_id, instance_id, builder)
                for (component_id, instance_id), builder in compose._BUILDERS.items()
                if (component_id, instance_id) != ("narrative", "conclusion")
            )
        ),
    )
    doc = compose_document(_data())
    assert any("builder manquant: narrative :: conclusion" in d for d in doc.diagnostics)


# --- Preuve du dispatch sur les blocs narratifs ---------------------------


def test_the_remaining_narrative_block_reaches_its_builder(monkeypatch):
    """Le marqueur `narrative` ne porte plus qu'un bloc, et il atteint le sien.

    Ce test démontrait autrefois, de bout en bout, que plusieurs blocs partageant
    un `component_id` visaient des builders différents. Trois d'entre eux sont
    devenus des composants (ADR-0013) et seul `conclusion` reste sous le
    marqueur : la démonstration end-to-end n'a plus de matière dans le profil
    réel.

    Le mécanisme lui-même n'est pas moins couvert — les tests voisins le prouvent
    sur des registres synthétiques, où deux clés de même `component_id`
    coexistent et se distinguent. Ce qui disparaît ici est un cas de figure du
    profil, pas une garantie.
    """

    def conclusion_builder(_data_source, instance_id):
        return {"bloc": "conclusion"}

    monkeypatch.setattr(
        compose, "_BUILDERS", compose._registry((("narrative", "conclusion", conclusion_builder),))
    )
    composed = compose_document(_data())
    narratives = {
        instance.instance_id: instance.payload
        for instance in composed.components
        if instance.component_id == "narrative"
    }
    assert narratives == {"conclusion": {"bloc": "conclusion"}}
