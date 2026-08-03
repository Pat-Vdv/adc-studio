"""Passe d'observation : source -> instantané (ADR-0014).

Elle appelle les API publiques et **ne décide rien**. Chaque champ de
l'instantané est la copie d'un fait produit ailleurs :

    contrats            table des fragments + profil
    écarts de contrat   la frontière d'entrée, via l'exception qu'elle lève
    défauts métier      le validateur
    résolution          `resolve`, fonction propriétaire de l'ordre
    composition         l'IR
    document            l'IR

Appeler `resolve` n'est pas une duplication : c'est la fonction qui **détient**
la décision (W2). Écrire ici `if component_id == ...` pour expliquer ce qu'elle
aurait décidé en serait une.

Cette passe n'écrit rien (W1). Elle ne rend aucun document : le rendu produirait
un fichier, et la carte qui relierait ses chapitres aux instances n'existe pas
encore — l'audit la range parmi les instrumentations à concevoir.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import adc_contracts
import adc_mission
from adc_engine import SourceContractError, compose_from_source, incident_profile
from adc_engine.validation import validate
from adc_profile import Profile, resolve

from .snapshot import (
    ComponentView,
    ContractView,
    DiagnosticView,
    DocumentView,
    MissionArtefact,
    MissionView,
    ResolvedBlock,
    WorkbenchSnapshot,
)

# Extensions dont le contenu est chargé dans l'instantané. Le critère est la
# nature du fichier, jamais son emplacement : décider par le répertoire
# obligerait à interpréter le vocabulaire d'atelier, dont le pont est le seul
# lecteur légitime (ADR-0011).
TEXT_SUFFIXES = frozenset({".md", ".txt"})

# Au-delà, le contenu n'est pas chargé et la taille dit pourquoi. Ce seuil est
# une politique d'observation — la consommation de l'outil — et non une règle
# métier : il appartient donc au Workbench.
TEXT_CONTENT_MAX_BYTES = 512 * 1024


def _diagnostics(raw: Any) -> tuple[DiagnosticView, ...]:
    """Diagnostics structurés, recopiés champ par champ."""
    return tuple(
        DiagnosticView(
            path=d.path,
            message=d.message,
            source=d.source,
            component=d.component,
            code=d.code,
        )
        for d in raw
    )


def _contracts(profile: Profile) -> tuple[ContractView, ...]:
    """Ce que la table des fragments et le profil déclarent, sans rien joindre.

    Le profil est indexé par identifiant de composant : un fragment dont la clé
    n'en est pas un — un fragment racine — n'y trouve aucune entrée, et sa
    cardinalité reste inconnue plutôt qu'inventée.
    """
    entries = {entry.component_id: entry for entry in profile.entries}
    views = []
    for key, fragment in adc_contracts.INCIDENT_REPORT_FRAGMENTS.items():
        entry = entries.get(key)
        views.append(
            ContractView(
                key=key,
                nature=fragment.nature,
                kind=fragment.kind,
                path=fragment.path,
                has_contract=adc_contracts.has_contract(key),
                instance_id=entry.instance_id if entry else None,
                minimum=entry.minimum if entry else None,
                maximum=entry.maximum if entry else None,
            )
        )
    return tuple(views)


def observe(source: Any, profile: Profile | None = None) -> WorkbenchSnapshot:
    """Instantané d'une source contractuelle.

    Une seule passe, et un instantané dans tous les cas : un contrat violé
    interrompt la composition, pas l'observation.
    """
    profile = profile or incident_profile()
    notes: list[str] = []

    document = None
    contract_diagnostics: tuple[DiagnosticView, ...] = ()
    try:
        composed = compose_from_source(source, profile)
    except SourceContractError as refused:
        # La frontière porte ses écarts : les relire ailleurs les recalculerait.
        contract_diagnostics = _diagnostics(refused.diagnostics)
        composed = None

    if composed is not None:
        document = DocumentView(
            id=composed.id,
            type=composed.type,
            title=composed.title,
            metadata=dict(composed.metadata),
        )
        source_diagnostics = _diagnostics(composed.source_diagnostics)
        composition_diagnostics = tuple(composed.diagnostics)
        components = tuple(
            ComponentView(
                component_id=instance.component_id,
                instance_id=instance.instance_id,
                payload=dict(instance.payload),
            )
            for instance in composed.components
        )
    else:
        # Le validateur métier ne dépend pas de la frontière : il conclut sur une
        # source que la composition a refusée.
        source_diagnostics = _diagnostics(validate(source))
        composition_diagnostics = ()
        components = ()

    if isinstance(source, dict):
        blocks, resolution_notes = resolve(source, profile)
        notes += resolution_notes
    else:
        blocks = ()
        notes.append("source non observable par la résolution : objet attendu à la racine")

    instances = {(c.component_id, c.instance_id) for c in components}
    resolution = tuple(
        ResolvedBlock(
            component_id=component_id,
            instance_id=instance_id,
            composed=(component_id, instance_id) in instances,
        )
        for component_id, instance_id in blocks
    )

    return WorkbenchSnapshot(
        source=source,
        profile_id=profile.id,
        contracts=_contracts(profile),
        contract_diagnostics=contract_diagnostics,
        source_diagnostics=source_diagnostics,
        composition_diagnostics=composition_diagnostics,
        resolution=resolution,
        components=components,
        document=document,
        observation_notes=tuple(notes),
    )


def _text(path: Path) -> str | None:
    """Contenu d'un fichier texte exploitable, ou rien.

    Un fichier illisible ne fait pas échouer l'observation : l'inventaire dit
    déjà qu'il existe, et c'est ce que le panneau doit montrer.
    """
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None


def _artefact(path: Path, mission: Path, roles: dict[str, str], consumed: Path) -> MissionArtefact:
    relative = path.relative_to(mission)
    directory = path.is_dir()
    loadable = (
        not directory
        and (path.suffix in TEXT_SUFFIXES or path == consumed)
        and path.stat().st_size <= TEXT_CONTENT_MAX_BYTES
    )
    return MissionArtefact(
        path=relative.as_posix(),
        kind="directory" if directory else "file",
        size=None if directory else path.stat().st_size,
        role=roles.get(relative.as_posix()),
        content=_text(path) if loadable else None,
        consumed=path == consumed,
    )


def _mission_view(mission: Path, metadata: dict[str, Any]) -> MissionView:
    """L'atelier inventorié, dans un ordre stable.

    Les rôles viennent de ce que la mission déclare, par le module qui en est
    propriétaire : les relire ici en ferait un second lecteur du vocabulaire
    d'atelier, libre de dériver du premier.
    """
    roles = {
        declared: role for role, declared in adc_mission.declared_directories(metadata).items()
    }
    consumed = adc_mission.metadata_path(mission)
    return MissionView(
        path=str(mission),
        artefacts=tuple(
            _artefact(path, mission, roles, consumed)
            for path in sorted(mission.rglob("*"), key=lambda p: p.as_posix())
        ),
    )


def observe_mission(mission: Path, profile: Profile | None = None) -> WorkbenchSnapshot:
    """Instantané d'une mission, traduite par son pont (ADR-0011).

    La source contractuelle n'est pas matérialisée : elle existe le temps de
    l'observation, comme le pont l'exige (R5).

    L'instantané qui en résulte porte le contenu du rapport d'un client : il a la
    sensibilité de la mission observée (ADR-0014, W6).
    """
    mission = Path(mission)
    metadata = adc_mission.load_metadata(mission)
    snapshot = observe(adc_mission.to_source(metadata), profile)
    return replace(snapshot, mission=_mission_view(mission, metadata))
