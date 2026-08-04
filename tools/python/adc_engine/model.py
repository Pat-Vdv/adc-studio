"""Document Model (IR) — représentation intermédiaire indépendante du format.

Le `Document` est le résultat logique d'une composition (ADR-0008). Il ne
connaît ni Word, ni PDF : un renderer le matérialise ensuite dans un format
cible. Les structures sont gelées pour garantir un résultat déterministe.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from adc_diagnostics import ValidationDiagnostic


@dataclass(frozen=True)
class ComponentInstance:
    """Une occurrence de composant dans le document composé.

    - `component_id` : identifiant catalogue (ex. « C-001-cover »).
    - `instance_id`  : identifiant d'occurrence, unique dans le document.
    - `payload`      : données prêtes pour le rendu, extraites de la source.
    """

    component_id: str
    instance_id: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceOccurrence:
    """Où une occurrence composée a été prélevée dans la source.

    Produite par la résolution, qui sélectionne — donc par la seule couche qui
    connaisse simultanément le chemin et l'identité de l'occurrence.

    `source_path` désigne **l'occurrence entière** (`$.findings[0]`), jamais un
    champ : aucune relation entre un champ source et un champ de payload n'est
    décrite ici, et aucune ne peut en être déduite.
    """

    component_id: str
    instance_id: str
    source_path: str


@dataclass(frozen=True)
class Document:
    """Résultat logique d'une composition, indépendant du format de sortie.

    Deux natures de diagnostic, délibérément séparées : `diagnostics` dit ce que
    la composition n'a pas su faire — builder manquant, référence non résolue —
    tandis que `source_diagnostics` dit ce que le contenu a de fautif, sans que
    la transformation en souffre. Les fondre empêcherait de distinguer un trou
    du moteur d'un défaut du rapport.
    """

    id: str
    type: str
    title: str
    metadata: dict[str, Any] = field(default_factory=dict)
    components: tuple[ComponentInstance, ...] = ()
    diagnostics: tuple[str, ...] = ()
    source_diagnostics: tuple[ValidationDiagnostic, ...] = ()
    # D'où chaque occurrence a été prélevée. Fait d'observation, distinct des
    # deux natures de diagnostic comme des données métier du payload.
    source_occurrences: tuple[SourceOccurrence, ...] = ()
