#!/usr/bin/env python3
"""Génère un rapport d'incident DOCX depuis un JSON source.

Chaîne : JSON -> frontière d'entrée -> Document IR -> render_docx.

Usage :
    python tools/python/generate_incident_report.py <input.json> [-o sortie.docx]

Sans -o, le fichier est écrit sous ``build/<report_id>.docx`` (répertoire
gitignoré).

Trois natures d'écart, trois comportements (ADR-0009, I9) :

- **contrat violé** : rien n'est généré. La source n'est plus celle que le
  moteur accepte ;
- **défaut métier** — référence inconnue, identifiant dupliqué : le document
  est généré, l'écart l'accompagne. Le contenu est fautif, sa transformation
  ne l'est pas ;
- **composant non rendu** : le document est généré, l'écart l'accompagne.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adc_engine import SourceContractError, compose_from_source  # noqa: E402
from adc_engine.render_docx import render_docx  # noqa: E402

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

    try:
        document = compose_from_source(data)
    except SourceContractError as error:
        print(f"CONTRAT VIOLÉ : {len(error.diagnostics)} écart(s). Rien n'a été généré.", file=sys.stderr)
        for diagnostic in error.diagnostics:
            print(f"- {diagnostic}", file=sys.stderr)
        return 1

    output = args.output or (ROOT / "build" / f"{document.id or 'incident_report'}.docx")
    render_docx(document, output)

    print(f"OK : rapport généré -> {output}")
    print(f"Composants rendus : {len(document.components)}")
    if document.source_diagnostics:
        # Le document existe et reste exploitable : ces écarts décrivent son
        # contenu, pas un échec de la chaîne.
        print("Défauts métier du rapport :")
        for diagnostic in document.source_diagnostics:
            print(f"- {diagnostic}")
    if document.diagnostics:
        print("Composants non rendus (diagnostics) :")
        for diag in document.diagnostics:
            print(f"- {diag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
