"""Résolution : profil + données + localisation -> occurrences résolues.

Le partage des responsabilités est strict :

- la **localisation** dit dans quel nœud de la source vit un bloc. Elle est un
  fait structurel neutre (ADR-0010) et ce module ne la possède pas : elle lui
  est **fournie**. Il n'en garde aucune table, n'en déduit rien d'un
  identifiant de composant, et n'importe aucun registre ;
- le **profil** déclare l'ordre, les cardinalités et le caractère obligatoire
  ou optionnel de chaque bloc ;
- la **résolution** sélectionne la donnée, ordonne les occurrences et confronte
  leur nombre aux cardinalités déclarées.

Elle **sélectionne une fois pour toutes** : l'occurrence résolue porte la donnée
elle-même, et la composition n'a plus à la retrouver. La resélectionner en aval
serait une seconde déclaration du même fait (ADR-0012, G2).

Aucune occurrence n'est fabriquée pour satisfaire une cardinalité : un écart
produit un diagnostic, jamais un bloc vide.

**La présence d'un bloc suit celle de son fragment déclaré.** Un fragment racine
— la source entière — est toujours présent ; un fragment nommé ne l'est que si
la source porte son nœud. Cette règle vaut pour tous les blocs uniques, sans
exception : deux d'entre eux y échappaient par héritage, faute qu'une règle ait
jamais été écrite, ce qui donnait deux régimes de présence dont un seul était
attesté.

La présence d'un nœud est **structurelle**, jamais booléenne (ADR-0012, G4) : un
nœud présent mais vide est présent, et porte l'occurrence que le profil attend.
Le juger par la véracité de sa valeur confondrait cinq états — clé absente,
`None`, objet vide, liste vide, chaîne vide — et ferait dire à la cardinalité ce
que la présence a déjà dit autrement, en contredisant le validateur métier qui en
est propriétaire. Qu'un contenu vide soit recevable ne se décide pas ici.

Ce module ne connaît ni la composition, ni le rendu, ni la validation : c'est
ce qui permet à plusieurs outils de partager la même description de l'ordre.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contract import Profile, ProfileEntry

ROOT_PATH = "$"

# Identité d'un bloc du profil : son composant, et son occurrence nommée s'il en
# déclare une. C'est la clé sous laquelle la localisation lui est fournie.
BlockKey = tuple[str, str | None]

# Localisation d'un bloc : le nom du nœud source qui le porte, ou `None` pour le
# fragment racine — la source entière.
Locations = Mapping[BlockKey, str | None]


@dataclass(frozen=True)
class ResolvedOccurrence:
    """Une occurrence sélectionnée, et tout ce qui permet de la situer.

    Un type nommé plutôt qu'un tuple : la valeur porte quatre faits de natures
    différentes, et leur position ne doit pas devenir un contrat implicite.

    - `source_path` est le chemin canonique du fragment consommé — `$`,
      `$.environment`, `$.findings[0]`. Il désigne **l'occurrence**, jamais un
      champ : aucune relation champ-à-champ n'est décrite ici.
    - `fragment` est la donnée déjà sélectionnée. La composition la reçoit ; la
      retrouver serait sélectionner deux fois.
    """

    component_id: str
    instance_id: str
    source_path: str
    fragment: Any


def _single(entry: ProfileEntry, data: dict[str, Any], node: str | None):
    """Occurrence d'un bloc unique, si son fragment déclaré est présent."""
    if node is None:
        # Fragment racine : la source entière, toujours présente.
        return (ResolvedOccurrence(entry.component_id, entry.instance_id, ROOT_PATH, data),)
    if node not in data:
        return ()
    return (
        ResolvedOccurrence(
            entry.component_id, entry.instance_id, f"{ROOT_PATH}.{node}", data[node]
        ),
    )


def _repeatable(entry: ProfileEntry, data: dict[str, Any], node: str | None):
    """Occurrences d'un bloc répétable, dans l'ordre de la source.

    L'index appartient au chemin canonique au même titre que le nom du nœud. Une
    entrée sans identifiant exploitable n'est pas instanciable et n'est donc pas
    résolue : c'est son contrat qui doit l'exiger, pas la résolution qui doit la
    deviner.
    """
    if node is None:
        return ()
    collection = data.get(node, [])
    if not isinstance(collection, list):
        return ()
    return tuple(
        ResolvedOccurrence(entry.component_id, item["id"], f"{ROOT_PATH}.{node}[{index}]", item)
        for index, item in enumerate(collection)
        if isinstance(item, dict) and item.get("id")
    )


def _occurrences(
    entry: ProfileEntry, data: dict[str, Any], locations: Locations
) -> tuple[tuple[ResolvedOccurrence, ...], str | None]:
    """Occurrences produites par la source pour ce bloc, et leur diagnostic.

    Un bloc dont la localisation n'est pas fournie ne peut pas être résolu :
    mieux vaut le signaler que l'omettre en silence.
    """
    key: BlockKey = (entry.component_id, entry.instance_id)
    if key not in locations:
        named = f"{entry.component_id} :: {entry.instance_id}" if entry.instance_id else entry.component_id
        return (), f"source d'occurrences inconnue: {named}"
    node = locations[key]
    if entry.instance_id is not None:
        return _single(entry, data, node), None
    return _repeatable(entry, data, node), None


def _cardinality_diagnostic(entry: ProfileEntry, count: int) -> str | None:
    if count < entry.minimum:
        return (
            f"cardinalité non respectée: {entry.component_id} :: "
            f"{entry.minimum} occurrence(s) au minimum, {count} obtenue(s)"
        )
    if entry.maximum is not None and count > entry.maximum:
        return (
            f"cardinalité non respectée: {entry.component_id} :: "
            f"{entry.maximum} occurrence(s) au maximum, {count} obtenue(s)"
        )
    return None


def resolve(
    data: dict[str, Any], profile: Profile, locations: Locations
) -> tuple[tuple[ResolvedOccurrence, ...], tuple[str, ...]]:
    """Occurrences ordonnées selon le profil, et diagnostics de résolution."""
    resolved: list[ResolvedOccurrence] = []
    diagnostics: list[str] = []

    for entry in profile.entries:
        occurrences, missing_source = _occurrences(entry, data, locations)
        if missing_source:
            diagnostics.append(missing_source)
        resolved += occurrences

        cardinality = _cardinality_diagnostic(entry, len(occurrences))
        if cardinality:
            diagnostics.append(cardinality)

    return tuple(resolved), tuple(diagnostics)
