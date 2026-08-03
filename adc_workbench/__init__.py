"""ADC Studio — Workbench : couche d'observation de la chaîne documentaire.

Le Workbench est une **projection en lecture seule de faits produits par leurs
couches propriétaires** (ADR-0014). Il lit, sélectionne, filtre et présente ; il
ne valide, ne résout, ne déduit et ne reconstitue aucune décision.

Ce paquet ne porte à ce stade aucune interface : une passe d'observation et le
modèle de son instantané. C'est délibéré — un état inspectable et testé précède
tout écran, faute de quoi l'interface servirait à découvrir ce que fait le
moteur, et finirait par l'expliquer à sa place.
"""
from .observation import observe, observe_mission
from .snapshot import (
    ComponentView,
    ContractView,
    DiagnosticView,
    DocumentView,
    ResolvedBlock,
    WorkbenchSnapshot,
)

__all__ = [
    "ComponentView",
    "ContractView",
    "DiagnosticView",
    "DocumentView",
    "ResolvedBlock",
    "WorkbenchSnapshot",
    "observe",
    "observe_mission",
]
