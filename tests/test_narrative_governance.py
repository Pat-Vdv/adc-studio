"""Gouvernance du contrat narratif (ADR-0012).

Deux règles seulement sont vérifiables par un test, et elles ne sont pas de la
même nature :

- **G2 — un fait n'est déclaré qu'une fois.** La correspondance entre un bloc et
  le nœud source qui le porte appartient à la table des fragments. La résolution
  la redéclare pour son propre usage ; rien ne confrontait les deux. Ces tests
  passent dès leur écriture : ils ne réparent rien, ils interdisent une dérive
  que personne n'aurait vue ;
- **G4 — vide et absent sont deux faits distincts.** Ceux-là échouent tant que la
  résolution évalue la présence par une vérité booléenne.

Ils atteignent délibérément les tables privées de la résolution : c'est la
déclaration réelle qu'il faut confronter, pas une projection publique qui
pourrait elle-même dériver.
"""
from __future__ import annotations

import json

import pytest

import adc_contracts
from adc_engine import incident_profile
from adc_engine.validation import validate
from adc_profile import resolve
from adc_profile import resolution

FRAGMENTS = adc_contracts.INCIDENT_REPORT_FRAGMENTS

# Blocs à occurrence unique dont la présence dépend de la source. Les autres —
# ceux que `_SINGLE_OCCURRENCE_SOURCES` associe à `None` — sont présents dès que
# le profil les déclare, et ne disent donc rien de la distinction vide/absent.
#
# La forme vide est celle que la source utilise réellement pour ce nœud : un
# objet pour un bloc structuré, une chaîne pour la conclusion, une liste pour la
# chronologie.
EMPTY_FORMS = (
    ("incident-context", "incident_context", {}),
    ("probable-cause", "probable_cause", {}),
    ("conclusion", "conclusion", ""),
    ("timeline", "timeline", []),
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


def _blocks(data: dict) -> tuple[tuple[str, str], ...]:
    blocks, _ = resolve(data, incident_profile())
    return blocks


def _resolution_diagnostics(data: dict) -> tuple[str, ...]:
    _, diagnostics = resolve(data, incident_profile())
    return diagnostics


# --- G2 : un fait n'est déclaré qu'une fois --------------------------------


def test_every_node_claimed_by_the_resolution_is_located_by_the_table():
    """La table des fragments possède la localisation ; la résolution en dérive.

    Un nœud que la résolution réclame sans que la table le situe serait un
    cinquième lieu de vérité, invisible à la frontière d'entrée.
    """
    claimed = {node for node in resolution._SINGLE_OCCURRENCE_SOURCES.values() if node}
    claimed |= set(resolution._MULTIPLE_OCCURRENCE_SOURCES.values())
    located = {f.path for f in FRAGMENTS.values() if f.kind != adc_contracts.SOURCE}
    assert claimed <= located, "nœud réclamé par la résolution et situé nulle part"


@pytest.mark.parametrize(
    "component_id,node", sorted(resolution._MULTIPLE_OCCURRENCE_SOURCES.items())
)
def test_both_tables_name_the_same_node_for_a_repeatable_block(component_id, node):
    """Deux déclarations indépendantes du même fait doivent coïncider.

    Que C-007-decision se lise dans `actions_taken` est écrit dans les deux
    tables. Le jour où l'une change seule, ce test le dit — sans lui, le moteur
    composerait un nœud pendant que la frontière en contrôlerait un autre.

    Les blocs narratifs sont hors de portée de cette confrontation : la table les
    indexe par nom de nœud, la résolution par marqueur de bloc, et rien ne relie
    les deux clés tant que ces blocs n'ont pas de contrat (G3).
    """
    fragment = FRAGMENTS.get(component_id)
    if fragment is None:
        pytest.skip(f"{component_id} n'est pas indexé par identifiant dans la table")
    assert fragment.path == node


# --- G4 : vide et absent sont deux faits distincts -------------------------


@pytest.mark.parametrize("instance_id,node,empty", EMPTY_FORMS)
def test_a_present_but_empty_node_is_resolved_as_present(instance_id, node, empty):
    """Présent et vide reste présent (ADR-0012, G4).

    Le nœud existe dans la source : la partie est déclarée, son contenu reste à
    écrire. C'est un défaut de contenu, que la chaîne signale sans refuser de
    composer — jamais une absence.
    """
    data = {**_reference_source(), node: empty}
    assert any(block[1] == instance_id for block in _blocks(data))


@pytest.mark.parametrize("instance_id,node,empty", EMPTY_FORMS)
def test_an_absent_node_stays_absent(instance_id, node, empty):
    # L'autre moitié de G4 : distinguer les deux faits interdit aussi de les
    # confondre dans l'autre sens.
    data = {key: value for key, value in _reference_source().items() if key != node}
    assert not any(block[1] == instance_id for block in _blocks(data))


def test_the_validator_and_the_resolution_agree_on_a_present_but_empty_node():
    """Les deux couches propriétaires ne peuvent pas se contredire (G1, G4).

    Le validateur possède la présence, la résolution la cardinalité. Tant que la
    seconde évalue la présence pour son propre compte, elle rend un verdict qui
    ne lui appartient pas — et le contredit.
    """
    data = {**_reference_source(), "incident_context": {}}
    assert [d for d in validate(data) if d.path == "$.incident_context"] == []
    assert ("narrative", "incident-context") in _blocks(data)


def test_an_empty_node_produces_no_cardinality_diagnostic():
    # Le corollaire lisible : un nœud vide n'a jamais violé une cardinalité, il
    # porte l'occurrence que le profil attend, vide.
    data = {**_reference_source(), "incident_context": {}}
    assert [d for d in _resolution_diagnostics(data) if "cardinalité" in d] == []
