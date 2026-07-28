"""Contrats de composants : validation JSON Schema des fragments source.

Un `schema.json` de composant décrit **le fragment source** que ce composant
consomme — ce qu'un rédacteur ou un modèle de langage doit produire — et non le
payload de l'IR, qui est un contrat interne dérivé par les builders :

    Source JSON
        | validation par schema.json      <- ce module
    Composition / builders
        |
    Payload IR
        |
    Renderer

Le schéma valide la **forme locale** d'un fragment. Les règles globales — unicité
des identifiants, références résolubles, cardinalités, cohérences entre champs —
restent du ressort du validateur de rapport et du profil.

Module neutre : il ne dépend ni du moteur de composition, ni d'un format de
sortie, ni du validateur.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS_DIR = ROOT / "components"

SCHEMA_FILE = "schema.json"
EXAMPLE_FILE = "example.json"


def component_ids() -> tuple[str, ...]:
    """Identifiants des composants de la bibliothèque, dans l'ordre du catalogue."""
    return tuple(sorted(path.name for path in COMPONENTS_DIR.iterdir() if path.is_dir()))


def schema_path(component_id: str) -> Path:
    return COMPONENTS_DIR / component_id / SCHEMA_FILE


def example_path(component_id: str) -> Path:
    return COMPONENTS_DIR / component_id / EXAMPLE_FILE


def has_contract(component_id: str) -> bool:
    """Un composant a un contrat dès lors qu'il déclare un schéma."""
    return schema_path(component_id).is_file()


def load_json(path: Path) -> Any:
    """Charge un document JSON en nommant le fichier fautif s'il est illisible."""
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: JSON invalide: {exc}") from exc


def load_schema(component_id: str) -> dict[str, Any]:
    """Schéma d'un composant, lui-même vérifié comme schéma valide.

    Un schéma mal formé doit échouer ici, bruyamment : sinon il validerait
    n'importe quoi sans que personne ne s'en aperçoive.
    """
    path = schema_path(component_id)
    schema = load_json(path)
    if not isinstance(schema, dict):
        raise ValueError(f"{path}: objet attendu à la racine du schéma")
    Draft202012Validator.check_schema(schema)
    return schema


def validation_errors(
    fragment: Any, schema: dict[str, Any], *, component: str
) -> tuple[str, ...]:
    """Écarts d'un fragment au schéma, ordonnés et localisés.

    Chaque écart nomme le composant concerné et le chemin du champ fautif, de
    façon qu'un message soit exploitable sans relire le schéma.
    """
    validator = Draft202012Validator(schema)
    return tuple(
        f"{component}: {error.json_path}: {error.message}"
        for error in sorted(validator.iter_errors(fragment), key=lambda e: list(e.absolute_path))
    )


def example_errors(component_id: str) -> tuple[str, ...]:
    """Écarts de l'exemple d'un composant à son propre schéma."""
    fragment = load_json(example_path(component_id))
    return validation_errors(fragment, load_schema(component_id), component=component_id)
