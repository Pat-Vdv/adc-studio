"""Support commun aux deux validations.

Deux validations coexistent et ne disent pas la même chose :

- la **validation de forme** confronte un fragment au contrat de son composant.
  Elle sait quel contrat est violé, où, et pourquoi ;
- la **validation métier** vérifie ce qu'aucun schéma local ne peut voir :
  références, unicité, cardinalités, cohérences entre composants.

Leurs textes restent distincts. Les unifier reviendrait à faire dire à l'une ce
que l'autre a constaté, et à reformater des messages que la première produit
déjà mieux qu'on ne saurait les réécrire. Seul le **support** est commun, de
façon qu'une couche d'affichage les présente ensemble sans les confondre.

`path` et `message` viennent en tête, dans cet ordre : c'est la forme que les
diagnostics métier avaient déjà, et leurs points d'appel n'ont pas à changer
pour que le support devienne commun.

Module neutre : il ne dépend de rien.
"""
from __future__ import annotations

from dataclasses import dataclass

SCHEMA = "schema"
BUSINESS = "business"


@dataclass(frozen=True)
class ValidationDiagnostic:
    """Un écart constaté, quelle que soit la validation qui l'a produit.

    `component` n'est renseigné que lorsqu'un contrat nommé est violé : un
    écart métier porte sur la source, pas sur un composant. Le rendu textuel
    suit cette distinction, chaque validation gardant sa forme d'origine.

    `code` est la part lisible par une machine : le mot-clé du schéma pour la
    forme — `type`, `enum`, `required` — le vocabulaire du validateur pour le
    métier. Il permet de trier ou de filtrer sans analyser un message.
    """

    path: str
    message: str
    source: str = BUSINESS
    component: str | None = None
    code: str = ""

    def __str__(self) -> str:
        prefix = f"{self.component}: " if self.component else ""
        return f"{prefix}{self.path}: {self.message}"
