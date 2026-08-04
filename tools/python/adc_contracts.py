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

Deux entrées, selon l'échelle :

- `validate_fragment` confronte un fragment au contrat d'un composant ;
- `validate_report` parcourt une source entière, en localisant chaque fragment
  par la table de sa famille de rapports (ADR-0010). Sa couverture est donc
  exactement ce que cette table décrit, ni plus.

Module neutre : il ne dépend ni du moteur de composition, ni d'un format de
sortie, ni du validateur.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adc_diagnostics import SCHEMA, ValidationDiagnostic
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS_DIR = ROOT / "components"

SCHEMA_FILE = "schema.json"
EXAMPLE_FILE = "example.json"

# La localisation des fragments est un fait structurel neutre, porté par son
# propre registre (ADR-0010) : situer n'est pas valider. Ce module la consomme
# comme les autres couches, il ne la possède pas.
from adc_fragments import (  # noqa: E402
    CATALOG_COMPONENT,
    COLLECTION,
    INCIDENT_REPORT_FRAGMENTS,
    NODE,
    OCCURRENCE,
    ROOT_FRAGMENT,
    ROOT_PATH,
    SOURCE,
    Fragment,
)

__all__ = [
    "CATALOG_COMPONENT",
    "COLLECTION",
    "Fragment",
    "INCIDENT_REPORT_FRAGMENTS",
    "NODE",
    "OCCURRENCE",
    "ROOT_FRAGMENT",
    "ROOT_PATH",
    "SOURCE",
    "component_ids",
    "example_errors",
    "fragment_diagnostics",
    "has_contract",
    "load_json",
    "load_schema",
    "report_diagnostics",
    "schema_path",
    "validate_fragment",
    "validate_report",
    "validation_diagnostics",
    "validation_errors",
]


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


def validation_diagnostics(
    fragment: Any, schema: dict[str, Any], *, component: str, at: str = ROOT_PATH
) -> tuple[ValidationDiagnostic, ...]:
    """Écarts d'un fragment au schéma, ordonnés et localisés.

    Chaque écart nomme le composant concerné et le chemin du champ fautif, de
    façon qu'un message soit exploitable sans relire le schéma.

    `at` préfixe ces chemins par la position du fragment dans la source : un
    écart signalé en `$.severity` lors d'une validation isolée devient
    `$.findings[1].severity` lors de la validation d'un rapport entier.

    Le `code` est le mot-clé du schéma qui a rejeté la valeur — `type`, `enum`,
    `required` — repris tel quel : le traduire inventerait un vocabulaire que
    rien n'atteste.
    """
    validator = Draft202012Validator(schema)
    return tuple(
        ValidationDiagnostic(
            path=f"{at}{error.json_path[1:]}",
            message=error.message,
            source=SCHEMA,
            component=component,
            code=str(error.validator),
        )
        for error in sorted(validator.iter_errors(fragment), key=lambda e: list(e.absolute_path))
    )


def validation_errors(
    fragment: Any, schema: dict[str, Any], *, component: str, at: str = ROOT_PATH
) -> tuple[str, ...]:
    """Rendu textuel de `validation_diagnostics`."""
    return tuple(
        str(diagnostic)
        for diagnostic in validation_diagnostics(fragment, schema, component=component, at=at)
    )


def fragment_diagnostics(
    component_id: str, fragment: Any, *, at: str = ROOT_PATH
) -> tuple[ValidationDiagnostic, ...]:
    """Écarts d'un fragment au contrat de son composant."""
    return validation_diagnostics(
        fragment, load_schema(component_id), component=component_id, at=at
    )


def validate_fragment(component_id: str, fragment: Any, *, at: str = ROOT_PATH) -> tuple[str, ...]:
    """Rendu textuel de `fragment_diagnostics`."""
    return tuple(str(diagnostic) for diagnostic in fragment_diagnostics(component_id, fragment, at=at))


def validate_report(
    data: Any, fragments: dict[str, Fragment] | None = None
) -> tuple[str, ...]:
    """Rendu textuel de `report_diagnostics`."""
    return tuple(str(diagnostic) for diagnostic in report_diagnostics(data, fragments))


def report_diagnostics(
    data: Any, fragments: dict[str, Fragment] | None = None
) -> tuple[ValidationDiagnostic, ...]:
    """Écarts de forme d'une source entière, contrat par contrat.

    Chaque composant est confronté au fragment que la table lui désigne, et
    chaque écart est localisé dans la source, pas dans le fragment.

    Cette fonction ne vérifie que des **formes locales**. Trois choses lui
    échappent par construction, et relèvent du validateur de rapport :

    - la présence et la cardinalité d'un noeud — un noeud absent est ignoré
      ici, le schéma d'un composant ne disant rien de sa propre présence ;
    - la nature d'une collection — une collection d'occurrences qui n'est pas
      une liste ne peut pas être parcourue, donc pas adressée par un contrat
      d'occurrence ;
    - toute règle globale : unicité, références, cohérences inter-composants.

    Un fragment racine n'est confronté à aucun schéma : il n'en a pas. Sa
    présence dans la table nomme son consommateur, elle ne lui accorde aucune
    couverture — la table est la seule description de ce partage (ADR-0010).
    """
    table = INCIDENT_REPORT_FRAGMENTS if fragments is None else fragments
    is_source = isinstance(data, dict)
    diagnostics: list[ValidationDiagnostic] = []

    for component_id, fragment_spec in table.items():
        if fragment_spec.nature != CATALOG_COMPONENT:
            continue  # un fragment racine n'a pas de schéma à opposer
        kind, path = fragment_spec.kind, fragment_spec.path
        if kind != SOURCE and (not is_source or path not in data):
            continue
        # Chargé une fois par composant : une collection de cent occurrences ne
        # relit pas cent fois le même schéma.
        schema = load_schema(component_id)

        if kind == SOURCE:
            targets = ((data, ROOT_PATH),)
        elif kind == OCCURRENCE:
            if not isinstance(data[path], list):
                continue
            targets = tuple(
                (item, f"{ROOT_PATH}.{path}[{index}]") for index, item in enumerate(data[path])
            )
        else:
            targets = ((data[path], f"{ROOT_PATH}.{path}"),)

        for fragment, at in targets:
            diagnostics += validation_diagnostics(fragment, schema, component=component_id, at=at)

    return tuple(diagnostics)


def example_errors(component_id: str) -> tuple[str, ...]:
    """Écarts de l'exemple d'un composant à son propre schéma."""
    return validate_fragment(component_id, load_json(example_path(component_id)))
