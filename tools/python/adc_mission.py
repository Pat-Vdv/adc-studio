"""Pont entre l'atelier de mission et la source contractuelle (ADR-0011).

`nouveau-rapport` décrit une mission dans un vocabulaire humain — `titre`,
`auteur`, `classification` — plat et français. Le moteur consomme un vocabulaire
canonique, imbriqué et anglais. Ce module fait la correspondance, et il est le
seul endroit du dépôt qui la connaisse : ni le contrat ni le moteur ne savent
qu'un `metadata.yml` existe.

Il **traduit sans normaliser** (ADR-0011, R3) : les clés et la forme changent,
les valeurs sont transportées telles quelles. Aucune date reformatée, aucune
casse modifiée, aucune valeur déduite. Une mission dont la date est mal écrite
produira une source portant cette date mal écrite — le pont n'est pas un
correcteur, et un champ que le contrat contraint sera refusé plus loin, à la
frontière d'entrée.

Il **n'écrit pas ce qui n'a pas de valeur** (R4) : un champ vide de l'atelier
produit une propriété absente. `"id": ""` violerait le contrat de C-002 là où
l'omettre le satisfait.

Ce que le pont ne fait pas : produire le contenu du rapport. Constats,
recommandations et preuves se rédigent ailleurs. Une source issue d'une mission
neuve est contractuellement valide et éditorialement vide — elle compose un
document réel dont les diagnostics métier disent ce qui reste à écrire.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

METADATA_FILE = "metadata.yml"

# Correspondance atelier -> source, clé par clé. Elle est une donnée, pas une
# convention : aucune règle ne permet de deviner que `classification` devient
# `confidentiality`. Les clés d'atelier absentes de cette table — `etat`,
# `annee`, `framework_version`, `livrables`, `repertoires` — n'ont pas de
# contrepartie contractuelle et ne traversent pas (ADR-0011).
REPORT_FIELDS: dict[str, str] = {
    "titre": "title",
    "date": "date",
    "auteur": "author",
    "version": "version",
    "reference": "reference",
    "classification": "confidentiality",
}

CLIENT_FIELDS: dict[str, str] = {
    "client": "name",
}


def metadata_path(mission: Path) -> Path:
    return Path(mission) / METADATA_FILE


def load_metadata(mission: Path) -> dict[str, Any]:
    """Métadonnées d'une mission, en nommant le fichier fautif s'il est illisible."""
    path = metadata_path(mission)
    if not path.is_file():
        raise FileNotFoundError(f"{path}: métadonnées de mission introuvables")
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: YAML invalide: {exc}") from exc
    if document is None:
        return {}
    if not isinstance(document, dict):
        raise ValueError(f"{path}: objet attendu à la racine des métadonnées")
    return document


def _carried(metadata: dict[str, Any], fields: dict[str, str]) -> dict[str, Any]:
    """Champs traversant le pont, valeurs inchangées, vides omis.

    Une chaîne n'est écartée que si elle est vide une fois dépouillée de ses
    espaces : `"  "` ne porte pas davantage de sens que `""`. La valeur
    transportée reste celle de l'atelier, espaces compris — dépouiller pour
    décider n'autorise pas à dépouiller pour écrire (R3).
    """
    carried = {}
    for source_key, target_key in fields.items():
        value = metadata.get(source_key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        carried[target_key] = value
    return carried


def to_source(metadata: dict[str, Any]) -> dict[str, Any]:
    """Source contractuelle correspondant aux métadonnées d'une mission.

    Les deux noeuds `report` et `client` sont toujours présents, même vides :
    le validateur métier les exige à la racine, et leur absence serait un défaut
    de la source, non de sa traduction.
    """
    return {
        "report": _carried(metadata, REPORT_FIELDS),
        "client": _carried(metadata, CLIENT_FIELDS),
    }


def mission_source(mission: Path) -> dict[str, Any]:
    """Source contractuelle d'une mission, lue depuis son `metadata.yml`."""
    return to_source(load_metadata(mission))
