"""Ce que le statut « composant du catalogue » implique (ADR-0013).

Jusqu'ici, un seul test disait quelque chose de l'appartenance au catalogue :
tous les composants sont **localisés** dans la table des fragments. C'est
nécessaire et très insuffisant — un composant pouvait exister sans renderer,
sans résolution déclarée, ou sans la moindre ligne de documentation, et rien
n'en disait rien.

ADR-0013 fait du statut une décision, donc un **engagement** : promouvoir un
bloc au catalogue, c'est s'obliger à un ensemble d'artefacts. Ce fichier
transforme cet engagement en test, de façon que la contractualisation des blocs
suivants ne puisse pas en oublier une pièce.

Portée assumée : la vérification de la résolution passe par le profil P-003,
seul profil de composition existant. Elle suppose donc que bibliothèque et
famille « rapport d'incident » coïncident — couplage qu'ADR-0013 assume
explicitement, et dont le desserrage relèverait d'une autre ADR.
"""
from __future__ import annotations

import pytest

import adc_contracts
from adc_engine import incident_profile
from adc_engine.compose import _BUILDERS
from adc_engine.render_docx import _RENDERERS
from adc_profile import resolution

CATALOG = adc_contracts.ROOT / "COMPONENT_CATALOG.md"

COMPONENTS = adc_contracts.component_ids()


def _profile_entry(component_id: str):
    """Entrée de profil d'un composant, ou rien s'il n'y figure pas."""
    return next(
        (entry for entry in incident_profile().entries if entry.component_id == component_id),
        None,
    )


def _short_id(component_id: str) -> str:
    """« C-011-incident-context » -> « C-011 », l'identifiant du catalogue."""
    family, number, *_ = component_id.split("-")
    return f"{family}-{number}"


@pytest.mark.parametrize("component_id", COMPONENTS)
def test_a_catalog_component_has_a_contract(component_id):
    assert adc_contracts.has_contract(component_id), "schéma manquant"
    assert adc_contracts.example_path(component_id).is_file(), "exemple manquant"


@pytest.mark.parametrize("component_id", COMPONENTS)
def test_a_catalog_component_is_inventoried(component_id):
    # Localisé, et déclaré comme composant : un composant rangé en fragment
    # racine serait un contrat que la frontière n'opposerait à rien.
    fragment = adc_contracts.INCIDENT_REPORT_FRAGMENTS.get(component_id)
    assert fragment is not None, "absent de la table des fragments"
    assert fragment.nature == adc_contracts.CATALOG_COMPONENT


@pytest.mark.parametrize("component_id", COMPONENTS)
def test_a_catalog_component_has_a_builder(component_id):
    # Sans builder, le composant est résolu puis abandonné : le document sort
    # avec un diagnostic au lieu de la section attendue.
    assert any(key[0] == component_id for key in _BUILDERS), "aucun builder"


@pytest.mark.parametrize("component_id", COMPONENTS)
def test_a_catalog_component_has_a_renderer(component_id):
    assert any(key[0] == component_id for key in _RENDERERS), "aucun renderer"


@pytest.mark.parametrize("component_id", COMPONENTS)
def test_a_catalog_component_has_a_declared_resolution(component_id):
    """Un composant doit savoir d'où viennent ses occurrences.

    Bloc unique : la source de sa présence est déclarée sous son `instance_id`.
    Bloc répétable : la collection qui le porte est déclarée sous son
    identifiant de composant. Sans l'une ni l'autre, la résolution produit un
    diagnostic « source d'occurrences inconnue » et le bloc n'existe jamais.
    """
    entry = _profile_entry(component_id)
    assert entry is not None, "absent du profil"
    if entry.instance_id is not None:
        assert entry.instance_id in resolution._SINGLE_OCCURRENCE_SOURCES
    else:
        assert component_id in resolution._MULTIPLE_OCCURRENCE_SOURCES


@pytest.mark.parametrize("component_id", COMPONENTS)
def test_a_catalog_component_has_a_documentary_entry(component_id):
    # Le catalogue est la projection documentaire des métadonnées : un
    # composant qui n'y figure pas est invisible à tout lecteur humain.
    assert (adc_contracts.COMPONENTS_DIR / component_id / "README.md").is_file()
    assert (adc_contracts.COMPONENTS_DIR / component_id / "metadata.yaml").is_file()
    assert _short_id(component_id) in CATALOG.read_text(encoding="utf-8")
