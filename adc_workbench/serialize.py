"""Représentation transportable d'un instantané (ADR-0014, W4).

L'interface reçoit **cet objet et rien d'autre**. Elle ne reçoit ni la mission,
ni le profil, ni le moteur : ce qui ne figure pas ici n'est pas affichable, et
c'est ce qui la rend structurellement incapable de décider quoi que ce soit.

La sérialisation est une **recopie**, pas une transformation : aucun champ n'est
renommé, regroupé, trié ni complété. Une interface qui recevrait une forme
remaniée devrait la comprendre, donc l'interpréter.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from .snapshot import WorkbenchSnapshot


def to_dict(snapshot: WorkbenchSnapshot) -> dict[str, Any]:
    """Instantané en structures primitives, champ pour champ."""
    return asdict(snapshot)


def to_json(snapshot: WorkbenchSnapshot) -> str:
    """Instantané en JSON, déterministe pour une même observation.

    `default=str` n'est pas une conversion métier : il évite qu'une valeur
    inattendue dans une source cliente prive l'observateur de tout l'écran. Une
    valeur ainsi rendue reste visible telle que Python la décrit, et c'est
    précisément ce qu'un outil de diagnostic doit montrer.
    """
    return json.dumps(to_dict(snapshot), ensure_ascii=False, default=str)
