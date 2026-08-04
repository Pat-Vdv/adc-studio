"""Registre de localisation des fragments source (ADR-0010).

Où un fragment se lit dans une source, comment il se lit, et de quelle nature il
est. C'est un **fait structurel**, pas une règle : situer n'est pas valider.

Quatre couches le consomment — les contrats, la résolution, la composition et
l'observation — et aucune ne le possède. L'héberger chez l'une d'elles
obligerait les autres à en dépendre par un chemin qui ne dit pas ce qu'il
transporte : une couche qui a besoin de **situer** un fragment traverserait celle
qui le **valide**.

Module neutre au sens strict : il n'importe rien du dépôt. Il ne porte que ce
qu'ADR-0010 décrit, et rien de plus — tout ce qu'un annuaire général y
gagnerait appartiendrait à une autre couche.
"""
from __future__ import annotations

from dataclasses import dataclass

ROOT_PATH = "$"

# Comment un fragment se lit dans la source.
#
#   NODE       le noeud lui-même
#   COLLECTION la collection entière
#   OCCURRENCE chaque entrée de la collection, prise séparément
#   SOURCE     la source entière, dont le consommateur prélève plusieurs noeuds
NODE, COLLECTION, OCCURRENCE, SOURCE = "node", "collection", "occurrence", "source"

# Nature d'un fragment. Un composant catalogue porte un contrat ; un fragment
# racine est consommé sans avoir d'identité de bibliothèque, et n'est donc
# confronté à aucun schéma. Le déclarer ne lui accorde aucune couverture : cela
# nomme son consommateur, et laisse voir ce qui manque.
CATALOG_COMPONENT, ROOT_FRAGMENT = "catalog_component", "root_fragment"


@dataclass(frozen=True)
class Fragment:
    """Un fragment source : sa nature, comment le lire, et où."""

    nature: str
    kind: str
    path: str


# Table de la famille « rapport d'incident » (profil P-003). Elle appartient à
# une famille de rapports, pas à la bibliothèque : une autre famille nommerait
# les mêmes composants autrement. La clé est l'identifiant du composant pour un
# composant catalogue, le nom du noeud pour un fragment racine.
#
# Le nom du noeud ne se déduit pas de l'identifiant : C-007 lit `actions_taken`.
INCIDENT_REPORT_FRAGMENTS: dict[str, Fragment] = {
    "C-001-cover": Fragment(CATALOG_COMPONENT, SOURCE, ROOT_PATH),
    "C-002-identity-page": Fragment(CATALOG_COMPONENT, SOURCE, ROOT_PATH),
    "C-003-executive-summary": Fragment(CATALOG_COMPONENT, NODE, "executive_summary"),
    "C-004-finding": Fragment(CATALOG_COMPONENT, OCCURRENCE, "findings"),
    "C-005-recommendation": Fragment(CATALOG_COMPONENT, OCCURRENCE, "recommendations"),
    "C-006-risk": Fragment(CATALOG_COMPONENT, OCCURRENCE, "risks"),
    "C-007-decision": Fragment(CATALOG_COMPONENT, OCCURRENCE, "actions_taken"),
    "C-008-timeline": Fragment(CATALOG_COMPONENT, COLLECTION, "timeline"),
    "C-009-environment": Fragment(CATALOG_COMPONENT, NODE, "environment"),
    "C-010-evidence": Fragment(CATALOG_COMPONENT, OCCURRENCE, "evidence"),
    "C-011-incident-context": Fragment(CATALOG_COMPONENT, NODE, "incident_context"),
    "C-012-investigation": Fragment(CATALOG_COMPONENT, OCCURRENCE, "investigations"),
    "C-013-probable-cause": Fragment(CATALOG_COMPONENT, NODE, "probable_cause"),
    # Bloc `narrative` du profil : bâti par un builder, sans contrat.
    "conclusion": Fragment(ROOT_FRAGMENT, NODE, "conclusion"),
}
