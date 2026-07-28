"""Résolution des composants.

La résolution (ordre déterministe des composants pour le profil « incident »)
est déjà définie et testée dans `validate_incident_report.compose_block_index`.
Le moteur la **réutilise** au lieu de la redéfinir : source unique de l'ordre.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_VALIDATOR_PATH = Path(__file__).resolve().parents[1] / "validate_incident_report.py"
_VALIDATOR_MODULE = "adc_incident_validator"


def _load_validator():
    spec = importlib.util.spec_from_file_location(_VALIDATOR_MODULE, _VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    # Enregistré avant exec_module : @dataclass résout cls.__module__ via sys.modules.
    sys.modules[_VALIDATOR_MODULE] = module
    spec.loader.exec_module(module)
    return module


_validator = _load_validator()


def validate(data: dict[str, Any]) -> list[Any]:
    """Diagnostics structurels de la source (liste vide = valide)."""
    return _validator.validate(data)


def resolve(data: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    """Liste ordonnée de couples (component_id, instance_id)."""
    return _validator.compose_block_index(data)
