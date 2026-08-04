#!/usr/bin/env python3
"""Génère le rapport DOCX d'une mission créée par `nouveau-rapport`.

Chaîne : `metadata.yml` -> traduction -> frontière d'entrée -> Document -> DOCX.

Usage :
    python tools/python/generate_mission_report.py <dossier-mission> [-o sortie.docx]
                                                   [--write-source]

Sans ``-o``, le document est écrit sous ``<mission>/rapport/<nom-mission>.docx``.

Cette commande **orchestre** : elle traduit, appelle le moteur, présente. Elle ne
compose rien, ne valide rien et ne réinterprète aucun diagnostic. La source
contractuelle n'existe qu'en mémoire ; ``--write-source`` la matérialise pour
inspection, ce qui reste exceptionnel et jamais requis (ADR-0011, R5).

Trois natures d'écart, trois comportements (ADR-0009, I9) :

- **contrat violé** : rien n'est généré ;
- **défaut métier** : le document est généré, l'écart l'accompagne. Une section
  absente dit ce qui reste à rédiger ; le reste dit ce qui est fautif ;
- **composant non rendu** : le document est généré, l'écart l'accompagne.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adc_mission  # noqa: E402
import adc_presentation  # noqa: E402
from adc_engine import SourceContractError, compose_from_source  # noqa: E402
from adc_engine.render_docx import render_docx  # noqa: E402

REPORT_DIR = "rapport"
SOURCE_FILE = "report.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Génère le rapport DOCX d'une mission.")
    parser.add_argument("mission", type=Path, help="Dossier de la mission")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Chemin du .docx")
    parser.add_argument(
        "--write-source",
        action="store_true",
        help=f"écrit aussi la source contractuelle sous {REPORT_DIR}/{SOURCE_FILE}, "
        "pour inspection",
    )
    args = parser.parse_args()

    try:
        source = adc_mission.mission_source(args.mission)
    except (FileNotFoundError, ValueError) as exc:
        print(f"MISSION ILLISIBLE : {exc}", file=sys.stderr)
        return 1

    try:
        document = compose_from_source(source)
    except SourceContractError as error:
        print(
            f"CONTRAT VIOLÉ : {len(error.diagnostics)} écart(s). Rien n'a été généré.",
            file=sys.stderr,
        )
        for diagnostic in error.diagnostics:
            print(f"- {diagnostic}", file=sys.stderr)
        return 1

    report_dir = args.mission / REPORT_DIR
    output = args.output or (report_dir / f"{args.mission.resolve().name}.docx")
    output.parent.mkdir(parents=True, exist_ok=True)
    render_docx(document, output)

    if args.write_source:
        report_dir.mkdir(parents=True, exist_ok=True)
        inspection = report_dir / SOURCE_FILE
        inspection.write_text(
            json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Source contractuelle écrite pour inspection -> {inspection}")

    print(f"OK : rapport généré -> {output}")
    print(f"Composants rendus : {len(document.components)}")
    for line in adc_presentation.source_lines(document.source_diagnostics):
        print(line)
    if document.diagnostics:
        print("Composants non rendus (diagnostics) :")
        for diagnostic in document.diagnostics:
            print(f"- {diagnostic}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
