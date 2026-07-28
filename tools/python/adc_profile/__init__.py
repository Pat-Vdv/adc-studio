"""Noyau « profil » : structure déclarée d'un rapport et résolution des blocs.

Ce paquet est **neutre** : il ne dépend ni du moteur de composition, ni d'un
format de sortie, ni du validateur. C'est la source unique de l'ordre des
blocs, et il peut être consommé par plusieurs outils sans les coupler entre
eux :

    p-003-incident-report.yaml
              │
              ├── composition de l'IR   (adc_engine)
              └── résumé du validateur  (validate_incident_report.py)
"""
from .contract import Profile, ProfileEntry, load_profile
from .resolution import resolve

__all__ = ["Profile", "ProfileEntry", "load_profile", "resolve"]
