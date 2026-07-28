"""ADC Studio — moteur de composition documentaire.

Chaîne : données validées -> résolution des composants -> Document Model (IR)
-> renderer. Le moteur est développé de manière incrémentale à partir du cas
réel « SQL Server Incident Report » (voir ADR-0008).
"""
from .model import ComponentInstance, Document
from .compose import compose_document

__all__ = ["ComponentInstance", "Document", "compose_document"]
