"""Profil documentaire : ordre et cardinalités des composants d'un rapport.

Le profil déclare **la structure** : quels blocs se succèdent, dans quel ordre,
et combien d'occurrences chacun admet. Il ne déclare aucune condition sur les
données — pas de langage `when`, pas d'expression : savoir si la source produit
zéro, une ou plusieurs occurrences relève de la résolution (ADR-0008 § 3).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ProfileEntry:
    """Un bloc déclaré par le profil.

    - `component_id` : identifiant catalogue, ou marqueur de bloc narratif.
    - `instance_id`  : occurrence unique nommée par le profil ; absent, les
      occurrences sont énumérées depuis la source.
    - `minimum` / `maximum` : cardinalité admise, `maximum=None` pour illimité.
    """

    component_id: str
    instance_id: str | None
    minimum: int
    maximum: int | None


@dataclass(frozen=True)
class Profile:
    """Structure déclarée d'une famille de rapports."""

    id: str
    name: str
    entries: tuple[ProfileEntry, ...]


def _fail(path: Path, position: str, message: str) -> None:
    raise ValueError(f"{path}: {position}: {message}")


def _entry(path: Path, index: int, raw: Any) -> ProfileEntry:
    position = f"components[{index}]"
    if not isinstance(raw, dict):
        _fail(path, position, "objet attendu")

    component_id = raw.get("type")
    if not isinstance(component_id, str) or not component_id.strip():
        _fail(path, position, "champ 'type' requis, chaîne non vide")

    instance_id = raw.get("instance")
    if instance_id is not None and (not isinstance(instance_id, str) or not instance_id.strip()):
        _fail(path, position, "champ 'instance' optionnel, chaîne non vide si présent")

    minimum = raw.get("min")
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 0:
        _fail(path, position, "champ 'min' requis, entier positif ou nul")

    # `max` doit être écrit, fût-ce `null` : une clé oubliée ne doit pas valoir
    # silencieusement « illimité ».
    if "max" not in raw:
        _fail(path, position, "champ 'max' requis, entier ou null pour illimité")
    maximum = raw.get("max")
    if maximum is not None and (not isinstance(maximum, int) or isinstance(maximum, bool)):
        _fail(path, position, "champ 'max' requis, entier ou null pour illimité")
    if isinstance(maximum, int) and maximum < minimum:
        _fail(path, position, f"'max' ({maximum}) inférieur à 'min' ({minimum})")

    if instance_id is not None and maximum != 1:
        _fail(path, position, "un bloc nommé par 'instance' admet au plus une occurrence")

    return ProfileEntry(component_id, instance_id, minimum, maximum)


def load_profile(path: str | Path) -> Profile:
    """Charge un profil et vérifie son contrat minimal.

    Toute violation lève une `ValueError` nommant le fichier et la position
    fautive : un profil incohérent doit échouer à la lecture, pas produire un
    document silencieusement amputé.
    """
    path = Path(path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        _fail(path, "$", "objet attendu à la racine")

    raw_entries = document.get("components")
    if not isinstance(raw_entries, list) or not raw_entries:
        _fail(path, "$.components", "liste non vide attendue")

    entries = tuple(_entry(path, index, raw) for index, raw in enumerate(raw_entries))

    declared = [(e.component_id, e.instance_id) for e in entries]
    if len(set(declared)) != len(declared):
        _fail(path, "$.components", "bloc déclaré deux fois")

    return Profile(
        id=str(document.get("id", "")),
        name=str(document.get("name", "")),
        entries=entries,
    )
