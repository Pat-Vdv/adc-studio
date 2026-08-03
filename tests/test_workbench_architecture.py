"""Ce qu'ADR-0014 interdit au Workbench, rendu exécutable.

Un outil d'observation dérive vers une seconde implémentation du moteur par
petites commodités : une validation « juste pour vérifier », un nom de nœud codé
en dur « le temps de brancher l'écran », un libellé français « pour que ce soit
lisible ». Chacune est indolore ; leur somme est une couche métier que rien ne
gouverne.

Ces tests sont écrits sur le modèle de
`test_the_contracts_are_consumed_at_the_boundary_only` : ils lisent les sources
du paquet et refusent ce qu'un invariant interdit. Ils passent dès leur écriture
— ce sont des verrous, pas des constats de défaut.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import adc_contracts
import adc_mission

WORKBENCH = Path(__file__).resolve().parents[1] / "adc_workbench"
SOURCES = sorted(WORKBENCH.glob("*.py"))


def _code(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_workbench_has_sources_to_inspect():
    # Sans quoi tous les tests ci-dessous passeraient sur le vide.
    assert SOURCES, "aucune source de Workbench trouvée"


# --- W1 : lecture seule ----------------------------------------------------

WRITES = (
    "write_text",
    "write_bytes",
    "mkdir",
    "makedirs",
    "unlink",
    "rmtree",
    "os.remove",
    "shutil.copy",
)


@pytest.mark.parametrize("call", WRITES)
def test_the_workbench_writes_nothing(call):
    """Aucune écriture, pas même incidente (W1).

    La persistance d'un instantané est une décision de commande explicite, pas
    un effet de bord d'une passe d'observation.
    """
    for path in SOURCES:
        assert call not in _code(path), f"{path.name} : écriture interdite ({call})"


def test_the_workbench_opens_no_file_for_writing():
    for path in SOURCES:
        code = _code(path)
        assert '"w"' not in code and "'w'" not in code, f"{path.name} : ouverture en écriture"


# --- W2 : propriétaire unique ---------------------------------------------


def test_the_workbench_validates_nothing_itself():
    """La validation d'un schéma appartient à la frontière (ADR-0009, I9)."""
    for path in SOURCES:
        code = _code(path)
        assert "jsonschema" not in code, f"{path.name} : validateur de schéma"
        assert "Draft202012Validator" not in code


def test_the_workbench_reads_no_contract_from_disk():
    # Les contrats se lisent par `adc_contracts`, seul propriétaire de leur
    # localisation et de leur chargement.
    for path in SOURCES:
        code = _code(path)
        assert "schema.json" not in code, f"{path.name} : lecture directe d'un contrat"
        assert "components/" not in code
        assert "COMPONENTS_DIR" not in code


def test_the_workbench_parses_no_profile():
    # L'ordre et les cardinalités viennent de `adc_profile`, jamais d'une
    # relecture du YAML.
    for path in SOURCES:
        code = _code(path)
        assert "yaml" not in code, f"{path.name} : relecture d'un profil"
        assert ".yaml" not in code


@pytest.mark.parametrize(
    "node",
    sorted(
        {
            fragment.path
            for fragment in adc_contracts.INCIDENT_REPORT_FRAGMENTS.values()
            if fragment.kind != adc_contracts.SOURCE
        }
    ),
)
def test_the_workbench_hardcodes_no_source_node(node):
    """La correspondance nœud <-> composant est déclarée une fois (ADR-0012, G2).

    Elle appartient à la table des fragments. Un nom de nœud écrit en dur ici
    serait une seconde déclaration du même fait, muette le jour où la première
    change.

    Le test est dérivé de la table elle-même : un nœud nouveau entre
    automatiquement dans le périmètre interdit.
    """
    for path in SOURCES:
        code = _code(path)
        assert f'"{node}"' not in code, f"{path.name} : nœud codé en dur ({node})"
        assert f"'{node}'" not in code


@pytest.mark.parametrize(
    "key",
    sorted(
        {*adc_mission.REPORT_FIELDS, *adc_mission.CLIENT_FIELDS, adc_mission.DIRECTORIES_FIELD}
    ),
)
def test_the_workbench_interprets_no_workshop_vocabulary(key):
    """Le pont est le seul lecteur du vocabulaire d'atelier (ADR-0011).

    Le panneau Mission montre le fichier brut ; il ne lit pas `titre` pour en
    déduire quoi que ce soit. Un second lecteur de ce vocabulaire dériverait du
    premier sans que rien ne le dise — et la correspondance « atelier ->
    canonique » cesserait d'avoir un propriétaire unique.

    La liste interdite est dérivée du pont lui-même : une clé nouvelle y entre
    seule.
    """
    for path in SOURCES:
        code = _code(path)
        assert f'"{key}"' not in code, f"{path.name} : vocabulaire d'atelier ({key})"
        assert f"'{key}'" not in code


# --- W3 : pas de reconstruction -------------------------------------------


def test_the_workbench_parses_no_diagnostic_message():
    """Les diagnostics de composition sont des chaînes libres.

    Les découper pour en tirer un code, un chemin ou une identité recréerait une
    structure que le moteur ne produit pas — et cette structure serait fausse le
    jour où un message change de forme.
    """
    for path in SOURCES:
        code = _code(path)
        for reconstruction in (".split(", ".partition(", "re.match", "re.search", "startswith("):
            assert reconstruction not in code, f"{path.name} : analyse de message ({reconstruction})"


def test_the_workbench_imports_no_presentation_vocabulary():
    # Traduire une valeur canonique appartient au renderer (ADR-0009, I5).
    for path in SOURCES:
        code = _code(path)
        assert "render_docx" not in code, f"{path.name} : vocabulaire de présentation"
        assert "_enum_label" not in code
        assert "_ENUM_VOCABULARIES" not in code


def test_the_workbench_declares_no_severity():
    # Aucune couche n'en produit : l'inventer serait la dérive qu'ADR-0010
    # interdit, et que `status`, `level` et `result` ont déjà évitée.
    for path in SOURCES:
        assert "severity" not in _code(path), f"{path.name} : gravité inventée"
