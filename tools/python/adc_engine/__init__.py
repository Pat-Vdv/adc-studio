"""ADC Studio — moteur de composition documentaire.

Chaîne : profil + données validées -> résolution des occurrences -> Document
Model (IR) -> contexte de rendu -> renderer. Le moteur est développé de manière
incrémentale à partir du cas réel « SQL Server Incident Report »
(voir ADR-0008 pour le modèle, ADR-0009 pour les invariants d'exécution).
"""
from adc_profile import Profile, load_profile

from .model import ComponentInstance, Document, SourceOccurrence
from .compose import compose_document, incident_profile
from .entry import SourceContractError, compose_from_source

__all__ = [
    "ComponentInstance",
    "Document",
    "Profile",
    "SourceContractError",
    "SourceOccurrence",
    "compose_document",
    "compose_from_source",
    "incident_profile",
    "load_profile",
]
