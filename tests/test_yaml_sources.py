"""Validation syntaxique des fichiers YAML déclaratifs du dépôt.

Périmètre volontairement limité à la syntaxe : profils et fiches machine des
composants doivent être analysables. Leur contrat métier — champs attendus,
cardinalités, ordre des composants — n'est pas vérifié ici.

    python -m pytest tests/test_yaml_sources.py
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]

YAML_SOURCES = sorted(
    [*ROOT.glob("profiles/*.yaml"), *ROOT.glob("components/*/metadata.yaml")]
)


def _relative(paths: list[Path]) -> list[str]:
    return [str(path.relative_to(ROOT)) for path in paths]


def test_yaml_sources_are_discovered():
    # Garde-fou : un glob devenu vide rendrait la suite verte sans rien vérifier.
    discovered = _relative(YAML_SOURCES)
    assert any(name.startswith("profiles/") for name in discovered)
    assert any(name.startswith("components/") for name in discovered)


@pytest.mark.parametrize("path", YAML_SOURCES, ids=_relative(YAML_SOURCES))
def test_yaml_source_is_syntactically_valid(path: Path):
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        pytest.fail(f"YAML invalide : {path.relative_to(ROOT)}\n{exc}")
