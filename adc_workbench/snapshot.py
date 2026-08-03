"""Modèle de l'instantané d'observation (ADR-0014, W4).

L'instantané est **le seul état** qu'une interface consommera. Elle n'en recalcule
rien : ce qu'il ne porte pas n'est pas affichable, et c'est délibéré — une
interface qui recevrait la source brute pourrait toujours en tirer ses propres
conclusions, donc redevenir une couche métier.

Deux règles se lisent directement dans ces structures :

- **rien n'est déduit** — chaque champ est la copie d'un fait produit par sa
  couche propriétaire (W2) ;
- **ce qui n'est pas structuré le reste** — les diagnostics de composition sont
  aujourd'hui des chaînes libres, et l'instantané les porte telles quelles plutôt
  que de les analyser (W3). Leur absence de structure est ainsi visible au lieu
  d'être masquée par une interprétation.

Aucune gravité n'apparaît ici : aucune couche n'en déclare, et l'inventer
reproduirait la dérive qu'ADR-0010 interdit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DiagnosticView:
    """Un diagnostic structuré, tel que sa couche propriétaire l'a produit.

    Copie fidèle de `ValidationDiagnostic` : aucun champ n'est ajouté, aucun
    message n'est réécrit. `component` n'est renseigné que lorsqu'un contrat
    nommé est violé — un écart métier porte sur la source, pas sur un composant.
    """

    path: str
    message: str
    source: str
    component: str | None
    code: str


@dataclass(frozen=True)
class ContractView:
    """Ce que la table des fragments et le profil disent d'un fragment source.

    `minimum` et `maximum` restent à `None` lorsque le profil ne peut pas être
    relié à ce fragment. C'est le cas des fragments racine : la table les indexe
    par nom de nœud, le profil par marqueur de bloc, et **rien ne relie les deux
    clés**. Fabriquer ce lien ici l'inventerait (W2) ; le laisser vide le rend
    visible.
    """

    key: str
    nature: str
    kind: str
    path: str
    has_contract: bool
    instance_id: str | None = None
    minimum: int | None = None
    maximum: int | None = None


@dataclass(frozen=True)
class ResolvedBlock:
    """Une occurrence telle que la résolution l'a produite, dans son ordre.

    `composed` dit seulement si une instance de cette identité figure dans l'IR.
    Il ne dit **pas pourquoi** elle n'y figure pas : cette raison est portée par
    un diagnostic de composition, aujourd'hui non structuré. L'inférer ici serait
    reconstituer une décision du moteur (W3).
    """

    component_id: str
    instance_id: str
    composed: bool


@dataclass(frozen=True)
class ComponentView:
    """Une instance de l'IR, payload compris.

    Le payload est repris tel quel, dans son vocabulaire canonique. Aucune valeur
    n'est traduite : le français appartient au renderer (ADR-0009, I5).
    """

    component_id: str
    instance_id: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class DocumentView:
    """L'en-tête de l'IR, sans ses composants ni ses diagnostics.

    Les uns et les autres sont portés à part par l'instantané : les regrouper
    ici obligerait une interface à choisir laquelle des deux vues fait autorité.
    """

    id: str
    type: str
    title: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class MissionArtefact:
    """Un artefact d'atelier, inventorié — et parfois lu.

    Trois notions distinctes, qu'il ne faut pas confondre :

    - l'**inventaire** — chemin, nature, taille — dit ce qui existe ;
    - le **contenu** n'est chargé que pour ce qu'une observation peut exploiter :
      il reste `None` partout ailleurs. Une capture ou un livrable n'entre pas
      dans l'instantané au motif qu'il existe ;
    - le **rôle** vient de ce que la mission déclare d'elle-même. Il n'est porté
      que par les répertoires qu'elle nomme : rien ne déclare qu'un rôle se
      propage à ce qu'ils contiennent, et l'y propager serait une heuristique.

    `consumed` dit qu'un producteur a réellement lu cet artefact pour produire
    l'instantané. C'est un fait, pas une intention : il répond à « qu'est-ce qui
    a participé à cette observation ? », sans rien dire de ce qui pourrait y
    participer un jour.
    """

    path: str
    kind: str
    size: int | None = None
    role: str | None = None
    content: str | None = None
    consumed: bool = False


@dataclass(frozen=True)
class MissionView:
    """L'atelier tel qu'il se présente sur le disque, au moment de l'observation.

    Cette vue montre le fichier de métadonnées **brut**. Elle n'en interprète
    aucun champ : la seule lecture qui fasse autorité sur ce vocabulaire est
    celle du pont, et son résultat est la source canonique de l'instantané.
    """

    path: str
    artefacts: tuple[MissionArtefact, ...] = ()


@dataclass(frozen=True)
class WorkbenchSnapshot:
    """État observé d'une source, à un instant, par une passe unique.

    `document` est `None` lorsqu'un contrat est violé : la chaîne s'arrête à la
    frontière et rien n'est composé (ADR-0009, I9). L'instantané existe malgré
    tout — c'est même le cas où il sert le plus.
    """

    source: Any
    profile_id: str
    contracts: tuple[ContractView, ...] = ()
    contract_diagnostics: tuple[DiagnosticView, ...] = ()
    source_diagnostics: tuple[DiagnosticView, ...] = ()
    # Chaînes libres, volontairement non analysées (W3).
    composition_diagnostics: tuple[str, ...] = ()
    resolution: tuple[ResolvedBlock, ...] = ()
    components: tuple[ComponentView, ...] = ()
    document: DocumentView | None = None
    mission: MissionView | None = None
    # Ce que la passe n'a pas pu observer, et pourquoi.
    observation_notes: tuple[str, ...] = field(default_factory=tuple)
