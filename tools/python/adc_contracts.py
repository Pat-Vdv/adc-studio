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
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS_DIR = ROOT / "components"

SCHEMA_FILE = "schema.json"
EXAMPLE_FILE = "example.json"

ROOT_PATH = "$"

# Où lire, dans une source, le fragment que chaque composant consomme (ADR-0010).
# Le nom du noeud ne se déduit pas de l'identifiant : C-007 lit `actions_taken`.
#
#   NODE       le noeud lui-même
#   COLLECTION la collection entière
#   OCCURRENCE chaque entrée de la collection, validée séparément
#   SOURCE     la source entière, dont le builder prélève plusieurs noeuds
NODE, COLLECTION, OCCURRENCE, SOURCE = "node", "collection", "occurrence", "source"

# Table de la famille « rapport d'incident » (profil P-003). Elle appartient à
# une famille de rapports, pas à la bibliothèque : une autre famille nommerait
# les mêmes composants autrement.
INCIDENT_REPORT_FRAGMENTS: dict[str, tuple[str, str]] = {
    "C-001-cover": (SOURCE, ROOT_PATH),
    "C-002-identity-page": (SOURCE, ROOT_PATH),
    "C-003-executive-summary": (NODE, "executive_summary"),
    "C-004-finding": (OCCURRENCE, "findings"),
    "C-005-recommendation": (OCCURRENCE, "recommendations"),
    "C-006-risk": (OCCURRENCE, "risks"),
    "C-007-decision": (OCCURRENCE, "actions_taken"),
    "C-008-timeline": (COLLECTION, "timeline"),
    "C-009-environment": (NODE, "environment"),
    "C-010-evidence": (OCCURRENCE, "evidence"),
}


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
    fragment: Any, schema: dict[str, Any], *, component: str, at: str = ROOT_PATH
) -> tuple[str, ...]:
    """Écarts d'un fragment au schéma, ordonnés et localisés.

    Chaque écart nomme le composant concerné et le chemin du champ fautif, de
    façon qu'un message soit exploitable sans relire le schéma.

    `at` préfixe ces chemins par la position du fragment dans la source : un
    écart signalé en `$.severity` lors d'une validation isolée devient
    `$.findings[1].severity` lors de la validation d'un rapport entier.
    """
    validator = Draft202012Validator(schema)
    return tuple(
        f"{component}: {at}{error.json_path[1:]}: {error.message}"
        for error in sorted(validator.iter_errors(fragment), key=lambda e: list(e.absolute_path))
    )


def validate_fragment(component_id: str, fragment: Any, *, at: str = ROOT_PATH) -> tuple[str, ...]:
    """Écarts d'un fragment au contrat de son composant."""
    return validation_errors(
        fragment, load_schema(component_id), component=component_id, at=at
    )


def validate_report(
    data: Any, fragments: dict[str, tuple[str, str]] | None = None
) -> tuple[str, ...]:
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

    Un noeud source qu'aucun contrat ne réclame n'est vérifié par personne : la
    table est la seule description de cette couverture (ADR-0010).
    """
    table = INCIDENT_REPORT_FRAGMENTS if fragments is None else fragments
    is_source = isinstance(data, dict)
    errors: list[str] = []

    for component_id, (kind, path) in table.items():
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
            errors += validation_errors(fragment, schema, component=component_id, at=at)

    return tuple(errors)


def example_errors(component_id: str) -> tuple[str, ...]:
    """Écarts de l'exemple d'un composant à son propre schéma."""
    return validate_fragment(component_id, load_json(example_path(component_id)))
