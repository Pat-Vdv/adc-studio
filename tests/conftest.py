"""Rend le paquet `adc_engine` (tools/python) importable dans les tests."""
import sys
from pathlib import Path

_TOOLS_PYTHON = Path(__file__).resolve().parents[1] / "tools" / "python"
if str(_TOOLS_PYTHON) not in sys.path:
    sys.path.insert(0, str(_TOOLS_PYTHON))
