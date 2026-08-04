"""Frontière d'entrée de la composition (ADR-0009, I9).

La chaîne suppose désormais que les fragments respectent leur contrat canonique
— c'est ce que la campagne de durcissement a construit. Cette hypothèse doit
être tenue par quelqu'un : c'est ici, une fois, et non dans chaque builder.

Deux natures d'écart, deux traitements, et la distinction n'est pas de degré :

- un **écart de contrat** interrompt. La source n'est plus celle que le moteur
  accepte ; composer reviendrait à demander aux builders de traiter un domaine
  qu'ils n'ont plus vocation à connaître ;
- un **diagnostic métier** n'interrompt pas. Il décrit un défaut du contenu,
  pas une impossibilité de transformer : une référence inconnue, un identifiant
  dupliqué laissent un rapport parfaitement composable.

Incomplet n'est pas malformé. Un document composé peut être incomplet sans être
invalide (ADR-0008 § 1.4) ; ce que cette frontière refuse, c'est une entrée
dont la forme n'est plus celle du contrat, ce qui est un autre sujet.

`compose_document` reste en dessous de cette frontière, sans garde : la
composition demeure une transformation pure, testable sur n'importe quelle
entrée sans avoir à la rendre conforme d'abord.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

import adc_contracts
from adc_diagnostics import ValidationDiagnostic

from .compose import compose_document
from .model import Document
from .validation import validate


class SourceContractError(Exception):
    """Une source viole le contrat d'au moins un composant : rien n'est composé.

    Les écarts sont portés par l'exception plutôt que journalisés : l'appelant
    décide comment les présenter, et rien ne se perd en chemin.
    """

    def __init__(self, diagnostics: tuple[ValidationDiagnostic, ...]) -> None:
        self.diagnostics = tuple(diagnostics)
        super().__init__(f"{len(self.diagnostics)} écart(s) de contrat dans la source")


def compose_from_source(data: Any, profile: Any = None) -> Document:
    """Compose un document depuis une source, contrat vérifié d'abord.

    Lève `SourceContractError` si un contrat est violé. Sinon, les diagnostics
    métier accompagnent le document sans l'empêcher : ils sont rangés à part
    des diagnostics de composition, qui ne disent pas la même chose.
    """
    contract = adc_contracts.report_diagnostics(data)
    if contract:
        raise SourceContractError(contract)
    document = compose_document(data, profile)
    return replace(document, source_diagnostics=tuple(validate(data)))
