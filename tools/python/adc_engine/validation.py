"""Accès à la validation structurelle de la source.

Le validateur est un script autonome : il est chargé dynamiquement plutôt
qu'importé, pour ne pas imposer sa présence sur le `sys.path` des outils qui
n'en ont pas besoin.

Ce module est volontairement à sens unique : le validateur ne connaît pas le
moteur, seulement le noyau neutre `adc_profile`. Aucun cycle n'est donc
possible entre les deux.
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
