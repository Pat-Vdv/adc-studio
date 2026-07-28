#!/usr/bin/env python3
"""Génère un rapport d'incident DOCX depuis un JSON source.

Chaîne : JSON -> validation -> compose_document (IR) -> render_docx.

Usage :
    python tools/python/generate_incident_report.py <input.json> [-o sortie.docx]

Sans -o, le fichier est écrit sous ``build/<report_id>.docx`` (répertoire
gitignoré). Les composants résolus mais non encore rendus sont listés comme
diagnostics — ils n'empêchent pas la génération.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adc_engine import compose_document  # noqa: E402
from adc_engine.render_docx import render_docx  # noqa: E402
from adc_engine.resolve import validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description="Génère un rapport d'incident DOCX.")
    parser.add_argument("input", type=Path, help="JSON source du rapport d'incident")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Chemin du .docx de sortie")
    args = parser.parse_args()

    try:
        data = json.loads(args.input.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        print(f"JSON INVALIDE : {exc}", file=sys.stderr)
        return 1

    issues = validate(data)
    if issues:
        print(f"SOURCE INVALIDE : {len(issues)} problème(s).", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    document = compose_document(data)

    output = args.output or (ROOT / "build" / f"{document.id or 'incident_report'}.docx")
    render_docx(document, output)

    print(f"OK : rapport généré -> {output}")
    print(f"Composants rendus : {len(document.components)}")
    if document.diagnostics:
        print("Composants non rendus (diagnostics) :")
        for diag in document.diagnostics:
            print(f"- {diag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
