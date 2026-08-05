"""Tests de la validation d'une source entière par les contrats de composants.

Le fichier voisin `test_component_contracts.py` prouve chaque contrat isolément.
Ici, deux choses seulement :

- la **table de localisation** — ce qu'elle couvre, et ce qu'elle laisse
  découvert, suivi explicitement plutôt qu'ignoré en silence ;
- la **localisation des écarts** — un écart doit se lire dans la source, pas
  dans le fragment, sans quoi il est inexploitable sur un rapport entier.
"""
from __future__ import annotations

import json

import pytest

import adc_contracts

FRAGMENTS = adc_contracts.INCIDENT_REPORT_FRAGMENTS

# Noeuds de la racine prélevés par les composants qui reçoivent la source
# entière : la table les désigne par `$`, jamais par leur nom.
_NODES_READ_FROM_SOURCE = ("report", "client")

# Noeuds de la source qui ne sont le fragment de personne : aucun builder ne
# les lit. Ni composants catalogue, ni fragments racine — les suivre à part
# évite de les confondre avec une couverture manquante (ADR-0010). La liste
# échoue dans les deux sens : un noeud qui trouve un consommateur doit la
# quitter, un noeud nouveau doit y entrer ou entrer dans la table.
SOURCE_NODES_CONSUMED_BY_NOBODY = ("annexes", "schema_version")


def _catalog_components() -> dict:
    return {k: f for k, f in FRAGMENTS.items() if f.nature == adc_contracts.CATALOG_COMPONENT}


def _root_fragments() -> dict:
    return {k: f for k, f in FRAGMENTS.items() if f.nature == adc_contracts.ROOT_FRAGMENT}


def _reference_source() -> dict:
    path = (
        adc_contracts.ROOT
        / "reference_reports"
        / "incident_report"
        / "data"
        / "sql_server_2014_incident.json"
    )
    return json.loads(path.read_text(encoding="utf-8-sig"))


# --- Table de localisation -------------------------------------------------


def test_every_component_of_the_library_is_located():
    # Un composant nouveau doit entrer dans la table, sans quoi son contrat ne
    # serait jamais confronté à une source réelle.
    assert set(_catalog_components()) == set(adc_contracts.component_ids())


def test_every_located_path_exists_in_the_reference_source():
    source = _reference_source()
    absent = [
        fragment.path
        for fragment in FRAGMENTS.values()
        if fragment.kind != adc_contracts.SOURCE and fragment.path not in source
    ]
    assert absent == [], "chemin sans contrepartie dans la source de référence"


def test_every_node_of_the_reference_source_is_located_or_tracked():
    """La table dit ce qui est couvert, donc aussi ce qui ne l'est pas.

    Ce test échoue dans les deux sens : un noeud qui trouve un consommateur
    sans entrer dans la table, comme un noeud nouveau que rien ne déclare.
    """
    located = {f.path for f in FRAGMENTS.values() if f.kind != adc_contracts.SOURCE}
    unclaimed = set(_reference_source()) - located - set(_NODES_READ_FROM_SOURCE)
    assert unclaimed == set(SOURCE_NODES_CONSUMED_BY_NOBODY)


def test_a_root_fragment_is_declared_without_being_covered():
    """Être dans la table n'accorde aucune couverture (ADR-0010).

    Les blocs `narrative` y nomment leur consommateur ; aucun schéma ne leur
    est opposé, et ce test échouera le jour où l'un d'eux gagnera un contrat —
    il faudra alors le déclarer composant catalogue, pas l'y laisser.
    """
    assert set(_root_fragments()) == {"conclusion"}
    for name in _root_fragments():
        assert not adc_contracts.has_contract(name)


def test_a_root_fragment_is_never_validated():
    source = _reference_source()
    source["conclusion"] = ["forme libre", 1, None]
    assert adc_contracts.report_diagnostics(source) == ()


def test_the_decision_component_does_not_read_the_node_its_name_suggests():
    # Le nom du noeud ne se déduit pas de l'identifiant du composant : c'est
    # pourquoi la localisation est une table et non une convention.
    decision = FRAGMENTS["C-007-decision"]
    assert (decision.kind, decision.path) == (adc_contracts.OCCURRENCE, "actions_taken")
    assert "decisions" not in _reference_source()


# --- Validation d'une source ----------------------------------------------


def test_the_reference_source_satisfies_every_contract():
    assert adc_contracts.validate_report(_reference_source()) == ()


def test_an_error_is_located_in_the_source_not_in_the_fragment():
    source = _reference_source()
    source["findings"][0]["severity"] = "urgent"
    errors = adc_contracts.validate_report(source)
    assert errors == (
        f"C-004-finding: $.findings[0].severity: {errors[0].split(': ', 2)[2]}",
    )
    assert "urgent" in errors[0]


def test_each_occurrence_is_validated_separately():
    source = _reference_source()
    source["evidence"].append({"id": "", "kind": ""})
    paths = [error.split(": ")[1] for error in adc_contracts.validate_report(source)]
    index = len(source["evidence"]) - 1
    assert paths == [f"$.evidence[{index}].id", f"$.evidence[{index}].kind"]


def test_an_error_on_a_node_carries_the_node_path():
    source = _reference_source()
    source["environment"]["cpu_logical_count"] = 40.5
    errors = adc_contracts.validate_report(source)
    assert len(errors) == 1
    assert errors[0].startswith("C-009-environment: $.environment.cpu_logical_count: ")


def test_an_error_on_the_root_keeps_the_root_path():
    source = _reference_source()
    source["report"]["title"] = 42
    errors = adc_contracts.validate_report(source)
    # Deux contrats lisent ce champ, deux contrats sont violés : le rapporter
    # une seule fois masquerait l'un des deux (ADR-0010).
    assert [error.split(": ")[0] for error in errors] == ["C-001-cover", "C-002-identity-page"]
    assert all(error.split(": ")[1] == "$.report.title" for error in errors)


def test_an_absent_node_produces_no_error():
    # Présence et cardinalité relèvent du profil et du validateur de rapport :
    # un schéma de composant ne dit rien de sa propre présence.
    source = _reference_source()
    del source["timeline"]
    del source["risks"]
    assert adc_contracts.validate_report(source) == ()


def test_a_malformed_collection_is_left_to_the_report_validator():
    # Une collection d'occurrences qui n'est pas une liste ne peut pas être
    # parcourue : aucun contrat d'occurrence ne peut l'adresser.
    source = _reference_source()
    source["findings"] = {"finding-001": {}}
    assert adc_contracts.validate_report(source) == ()


def test_a_source_that_is_not_an_object_is_refused_by_the_root_contracts():
    errors = adc_contracts.validate_report(["pas une source"])
    assert [error.split(": ")[0] for error in errors] == ["C-001-cover", "C-002-identity-page"]
    assert all(error.split(": ")[1] == "$" for error in errors)


def test_an_empty_table_validates_nothing():
    assert adc_contracts.validate_report(_reference_source(), fragments={}) == ()


# --- Support commun aux deux validations -----------------------------------


def test_a_schema_diagnostic_names_its_contract_and_its_keyword():
    source = _reference_source()
    source["findings"][0]["severity"] = "urgent"
    diagnostics = adc_contracts.report_diagnostics(source)
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert (diagnostic.source, diagnostic.component) == ("schema", "C-004-finding")
    assert diagnostic.path == "$.findings[0].severity"
    # Le code est le mot-clé du schéma, repris tel quel : le traduire
    # inventerait un vocabulaire que rien n'atteste.
    assert diagnostic.code == "enum"


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("severity", "urgent", "enum"),
        ("title", 42, "type"),
        ("evidence_ids", "evidence-001", "type"),
        ("inconnu", "x", "additionalProperties"),
    ],
)
def test_the_keyword_that_rejected_the_value_is_the_code(field, value, code):
    source = _reference_source()
    source["findings"][0][field] = value
    assert [d.code for d in adc_contracts.report_diagnostics(source)] == [code]


def test_a_missing_required_field_is_coded_required():
    source = _reference_source()
    del source["findings"][0]["title"]
    assert [d.code for d in adc_contracts.report_diagnostics(source)] == ["required"]


def test_the_textual_form_is_the_rendering_of_the_diagnostics():
    source = _reference_source()
    source["findings"][0]["severity"] = "urgent"
    assert adc_contracts.validate_report(source) == tuple(
        str(diagnostic) for diagnostic in adc_contracts.report_diagnostics(source)
    )


# --- Préfixe de localisation ----------------------------------------------


def test_a_fragment_validated_alone_keeps_local_paths():
    errors = adc_contracts.validate_fragment(
        "C-009-environment", {"cpu_logical_count": 16.5}
    )
    assert errors[0].startswith("C-009-environment: $.cpu_logical_count: ")


def test_a_root_error_takes_the_prefix_without_trailing_separator():
    # Champs requis manquants : les écarts portent sur le fragment lui-même,
    # dont le chemin est le préfixe nu — ni « $.findings[3]$ », ni
    # « $.findings[3]. ».
    errors = adc_contracts.validate_fragment(
        "C-004-finding", {"id": "finding-001"}, at="$.findings[3]"
    )
    assert errors, "un constat réduit à son identifiant viole son contrat"
    assert all(error.split(": ")[1] == "$.findings[3]" for error in errors)


def test_only_the_boundary_consumes_a_validation_api():
    """Un builder n'appelle jamais un schéma (ADR-0009, I9).

    Le verrou précédent interdisait au moteur de **mentionner** `adc_contracts`.
    C'était un proxy grossier : il confondait valider et situer, et interdisait
    donc à la composition de lire une localisation dont elle a légitimement
    besoin. Depuis qu'un registre neutre porte la localisation (ADR-0010), le
    verrou peut viser ce qu'il visait vraiment — la validation.
    """
    engine = adc_contracts.ROOT / "tools" / "python" / "adc_engine"
    apis = (
        "report_diagnostics",
        "validate_report",
        "validate_fragment",
        "fragment_diagnostics",
        "validation_diagnostics",
        "validation_errors",
        "example_errors",
        "load_schema",
    )
    consumers = {
        path.name
        for path in engine.glob("*.py")
        if any(api in path.read_text(encoding="utf-8") for api in apis)
    }
    assert consumers == {"entry.py"}, "une validation est consommée hors de la frontière"


@pytest.mark.parametrize(
    "node",
    sorted({f.path for f in FRAGMENTS.values() if f.kind != adc_contracts.SOURCE}),
)
def test_no_builder_reselects_its_own_fragment(node):
    """La résolution sélectionne, la composition transforme (ADR-0012, G2).

    Un builder qui nommerait son nœud le sélectionnerait une seconde fois, et
    redéclarerait un fait que le registre possède. Ces dix-huit lectures ont
    existé ; elles ne doivent pas revenir.

    Le verrou vise la **sélection dans la source**, non le nom : `conclusion`
    désigne aussi un volet du résumé exécutif et une occurrence nommée, et
    interdire le mot produirait des faux positifs sans rien protéger de plus.

    La liste interdite est dérivée du registre : un nœud nouveau y entre seul.
    """
    compose = (
        adc_contracts.ROOT / "tools" / "python" / "adc_engine" / "compose.py"
    ).read_text(encoding="utf-8")
    for selection in (f'data.get("{node}"', f'data["{node}"]', f"data.get('{node}'"):
        assert selection not in compose, f"nœud resélectionné par la composition : {node}"


def test_no_builder_receives_the_whole_source():
    """La résolution tend au builder son fragment, jamais la source entière.

    Recevoir la source, c'est pouvoir y chercher — donc pouvoir resélectionner.
    Le contrat d'entrée rend la duplication impossible plutôt qu'interdite.
    """
    import ast

    compose = adc_contracts.ROOT / "tools" / "python" / "adc_engine" / "compose.py"
    tree = ast.parse(compose.read_text(encoding="utf-8"))
    builders = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("_build_")
    ]
    assert builders, "aucun builder trouvé"
    for builder in builders:
        first = builder.args.args[0].arg
        assert first == "fragment", f"{builder.name} reçoit « {first} » au lieu du fragment"


def test_the_registry_key_exceptions_are_bounded_by_the_deferred_status():
    """Le résidu du statut différé ne doit pas survivre à sa cause (ADR-0013, D2).

    Un bloc du profil est situé par l'identifiant de son composant. Un fragment
    racine échappe à cette clé — le registre l'indexe par nom de nœud, le profil
    par marqueur de bloc, et rien ne relie les deux. Il n'en reste qu'un.

    Ce test lie l'exception à sa cause : le jour où le dernier fragment racine
    est contractualisé, la table doit se vider. Sans lui, elle survivrait en
    silence à la décision qui la justifiait.
    """
    import adc_fragments

    roots = {key for key, f in FRAGMENTS.items() if f.nature == adc_contracts.ROOT_FRAGMENT}
    assert set(adc_fragments.BLOCK_REGISTRY_KEYS.values()) == roots
    assert len(adc_fragments.BLOCK_REGISTRY_KEYS) == len(roots)
