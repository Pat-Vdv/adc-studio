"""Rebuild the ADC Design System specimen.

The canonical implementation is currently generated from the Sprint 004.1
design tokens. This script is intentionally minimal; the full report engine
will be introduced in a later sprint.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
TOKENS = json.loads((ROOT / "tokens" / "adc_design_tokens.json").read_text(encoding="utf-8"))

if __name__ == "__main__":
    print(f"ADC Design System {TOKENS['meta']['version']}")
    print("Canonical specimen:", ROOT / "examples" / "ADC-Design-System-Specimen-v0.4.1.docx")
