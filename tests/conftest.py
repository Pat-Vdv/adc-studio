"""Rend importables les paquets du dépôt : `adc_engine` et `adc_workbench`.

`tools/python` porte le moteur et ses modules neutres ; la racine porte le
Workbench, qui est une application et non de l'outillage de développement.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _path in (_ROOT / "tools" / "python", _ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
