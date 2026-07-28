"""Renderer DOCX — matérialise un Document (IR) en fichier Word.

Le renderer est **maître de la mise en page** : il construit le document
directement depuis l'IR avec python-docx (aucun template rempli par
substitution). Développement incrémental — composants rendus :
  - C-001-cover

Un composant présent dans l'IR mais sans renderer est **ignoré proprement**
(pas d'exception, pas de contenu fantôme) : la traçabilité des composants non
rendus reste portée par `Document.diagnostics`, jamais masquée.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from .model import ComponentInstance, Document

# Un renderer reçoit (docx, instance) et écrit dans le document Word en place.
Renderer = Callable[[Any, ComponentInstance], None]


def _add_label_value(docx: Any, label: str, value: Any) -> None:
    """Ligne « Label : valeur », omise si la valeur est absente."""
    if value in (None, ""):
        return
    paragraph = docx.add_paragraph()
    run = paragraph.add_run(f"{label} : ")
    run.bold = True
    paragraph.add_run(str(value))


def _render_cover(docx: Any, instance: ComponentInstance) -> None:
    payload = instance.payload

    document_type = payload.get("document_type")
    if document_type:
        p = docx.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(str(document_type).upper())
        run.bold = True
        run.font.size = Pt(14)

    title = docx.add_heading(payload.get("title") or "", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subtitle = payload.get("subtitle")
    if subtitle:
        p = docx.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(str(subtitle))
        run.italic = True
        run.font.size = Pt(12)

    docx.add_paragraph()  # respiration

    _add_label_value(docx, "Client", payload.get("client"))
    _add_label_value(docx, "Auteur", payload.get("author"))
    _add_label_value(docx, "Date", payload.get("date"))
    _add_label_value(docx, "Version", payload.get("version"))
    _add_label_value(docx, "Référence", payload.get("reference"))
    _add_label_value(docx, "Confidentialité", payload.get("confidentiality"))


_RENDERERS: dict[str, Renderer] = {
    "C-001-cover": _render_cover,
}


def render_docx(document: Document, output_path: str | Path) -> Path:
    """Rend le Document (IR) dans un fichier .docx et retourne son chemin.

    Les composants sans renderer sont ignorés sans erreur ; la génération ne
    dépend pas de leur prise en charge.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    docx = DocxDocument()
    for instance in document.components:
        renderer = _RENDERERS.get(instance.component_id)
        if renderer is None:
            continue  # non rendu à ce stade — voir Document.diagnostics
        renderer(docx, instance)

    docx.save(str(output_path))
    return output_path
