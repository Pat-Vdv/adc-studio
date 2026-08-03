"""Preuve navigateur de la navigation croisée (P4).

Une capture d'écran statique ne prouve rien d'une interaction : ces tests
exercent de vrais clics dans Chromium et vérifient **l'état exact du DOM** après
chacun — quel élément porte la sélection primaire, lesquels portent la mise en
évidence liée, et surtout qu'aucun autre ne les porte.

Les assertions négatives comptent autant que les positives : lorsque
l'instantané ne connaît pas une relation, l'interface ne doit rien allumer
ailleurs.

Exécution :

    .venv/bin/python -m pytest tests/test_workbench_browser.py

Le navigateur du système est réutilisé (`CHROMIUM`) : aucun second navigateur
n'est téléchargé. Les tests sont ignorés si Playwright ou ce navigateur manquent.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from adc_workbench import observe, observe_mission
from adc_workbench.serve import build_server

sync_playwright = pytest.importorskip("playwright.sync_api", reason="playwright absent").sync_playwright

CHROMIUM = Path("/usr/bin/chromium-browser")
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "reference_reports" / "incident_report" / "data" / "sql_server_2014_incident.json"

pytestmark = pytest.mark.skipif(not CHROMIUM.exists(), reason="chromium du système absent")

PRIMARY = ".selected"
LINKED = ".linked"


def _source() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8-sig"))


def _refused() -> dict:
    source = _source()
    source["findings"][0]["severity"] = "urgent"
    return source


class _Served:
    def __init__(self, snapshot):
        self.server = build_server(snapshot, port=0)
        self.host, self.port = self.server.server_address[:2]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return f"http://{self.host}:{self.port}/"

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(executable_path=str(CHROMIUM))
        yield instance
        instance.close()


def _open(browser, snapshot, width=1366, height=768):
    """Page chargée et rendue, prête à être cliquée."""
    served = _Served(snapshot)
    url = served.__enter__()
    page = browser.new_page(viewport={"width": width, "height": height})
    page.goto(url)
    page.wait_for_selector("body[data-ready]")
    return served, page


def _state(page) -> tuple[list[str], list[str]]:
    """(sélection primaire, mises en évidence liées), identifiées lisiblement."""
    def describe(selector):
        return page.eval_on_selector_all(
            selector,
            """nodes => nodes.map(n => {
                 const panel = n.closest('.panel');
                 const key = n.dataset.component || n.dataset.path || n.dataset.artefact
                             || (n.dataset.unstructured !== undefined ? 'unstructured' : '?');
                 return (panel ? panel.id : 'hors-panneau') + '|' + key;
               })""",
        )

    return describe(PRIMARY), describe(LINKED)


# --- A. Composant -> nœud source ------------------------------------------


def test_clicking_a_component_highlights_its_source_node(browser):
    served, page = _open(browser, observe(_source()))
    try:
        page.click("#body-components .row:has-text('C-004-finding')")
        primary, linked = _state(page)
        assert primary == ["panel-components|C-004-finding"]
        # Le contrat désigne un nœud : c'est la seule extrémité disponible.
        assert linked == ["panel-source|$.findings"]
        assert page.inner_text("#selected-path") == "$.findings"
    finally:
        page.close()
        served.__exit__()


def test_a_component_selection_reveals_its_payload(browser):
    served, page = _open(browser, observe(_source()))
    try:
        row = "#body-components .row:has-text('C-001-cover')"
        assert page.is_hidden(f"{row} pre")
        page.click(row)
        assert page.is_visible(f"{row} pre")
    finally:
        page.close()
        served.__exit__()


def test_a_cross_selection_scrolls_the_panel_not_the_page(browser):
    served, page = _open(browser, observe(_source()))
    try:
        before = page.evaluate("document.querySelector('#body-source').scrollTop")
        # Un composant dont le nœud est loin dans l'arbre de la source.
        page.click("#body-components .row:has-text('C-010-evidence')")
        after = page.evaluate("document.querySelector('#body-source').scrollTop")
        assert after > before, "le panneau Source doit avoir défilé"
        # La page, elle, ne bouge jamais.
        assert page.evaluate("window.scrollY") == 0
        assert page.evaluate("document.documentElement.scrollHeight <= window.innerHeight")
    finally:
        page.close()
        served.__exit__()


# --- B. Diagnostic de contrat ---------------------------------------------


def test_a_contract_diagnostic_links_its_component_and_its_node(browser):
    served, page = _open(browser, observe(_refused()))
    try:
        page.click("#body-diagnostics .row[data-code], #body-diagnostics .row[data-diagnostic]")
        primary, linked = _state(page)
        assert primary == ["panel-diagnostics|C-004-finding"]
        assert "panel-components|C-004-finding" in linked
        assert "panel-source|$.findings[0].severity" in linked
        assert page.inner_text("#selected-path") == "$.findings[0].severity"
    finally:
        page.close()
        served.__exit__()


# --- C. Diagnostic métier : un chemin, jamais un composant -----------------


def test_a_business_diagnostic_links_a_node_but_never_a_component(browser):
    source = _source()
    source["findings"][0]["evidence_ids"] = ["evidence-404"]
    served, page = _open(browser, observe(source))
    try:
        page.click("#body-diagnostics .row[data-path*='evidence_ids']")
        primary, linked = _state(page)
        assert len(primary) == 1
        assert primary[0].startswith("panel-diagnostics|")
        # L'assertion qui compte : aucun composant n'est allumé.
        assert not [node for node in linked if node.startswith("panel-components|")]
        assert linked == ["panel-source|$.findings[0].evidence_ids[0]"]
    finally:
        page.close()
        served.__exit__()


# --- D. Diagnostic de composition : aucune extrémité ----------------------


def test_an_unstructured_diagnostic_links_nothing(browser):
    source = _source()
    del source["conclusion"]
    served, page = _open(browser, observe(source))
    try:
        page.click("#body-diagnostics .row[data-unstructured]")
        primary, linked = _state(page)
        assert primary == ["panel-diagnostics|unstructured"]
        assert linked == [], "une chaîne libre n'a aucune extrémité à rejoindre"
    finally:
        page.close()
        served.__exit__()


# --- E. Nœud source --------------------------------------------------------


def test_clicking_a_source_node_shows_its_canonical_path(browser):
    served, page = _open(browser, observe(_source()))
    try:
        page.click("#body-source [data-path='$.report.title']")
        primary, linked = _state(page)
        assert primary == ["panel-source|$.report.title"]
        assert page.inner_text("#selected-path") == "$.report.title"
        # Aucun contrat ne désigne ce nœud précis : rien n'est inventé.
        assert linked == []
    finally:
        page.close()
        served.__exit__()


def test_a_source_node_named_by_a_contract_links_back_to_it(browser):
    served, page = _open(browser, observe(_source()))
    try:
        page.click("#body-source [data-path='$.findings']")
        primary, linked = _state(page)
        assert primary == ["panel-source|$.findings"]
        assert linked == ["panel-components|C-004-finding"]
    finally:
        page.close()
        served.__exit__()


# --- F. Artefact de mission ------------------------------------------------


def test_clicking_a_mission_file_previews_it_and_links_nothing(browser, tmp_path):
    (tmp_path / "travail").mkdir()
    (tmp_path / "metadata.yml").write_text('titre: "Mission"\n', encoding="utf-8")
    (tmp_path / "travail" / "brouillon.md").write_text("# Brouillon\n\nContenu.\n", encoding="utf-8")
    served, page = _open(browser, observe_mission(tmp_path))
    try:
        row = "#body-mission .row[data-artefact='travail/brouillon.md']"
        assert page.is_hidden(f"{row} pre")
        page.click(row)
        primary, linked = _state(page)
        assert primary == ["panel-mission|travail/brouillon.md"]
        assert page.is_visible(f"{row} pre")
        # Mission et Source ne sont pas reliées : l'instantané l'ignore.
        assert linked == []
    finally:
        page.close()
        served.__exit__()


# --- G. Un second clic ne laisse aucun résidu ------------------------------


def test_a_second_selection_erases_every_trace_of_the_first(browser):
    served, page = _open(browser, observe(_source()))
    try:
        page.click("#body-components .row:has-text('C-004-finding')")
        first_primary, first_linked = _state(page)
        assert first_primary and first_linked

        page.click("#body-components .row:has-text('C-010-evidence')")
        primary, linked = _state(page)
        assert primary == ["panel-components|C-010-evidence"]
        assert linked == ["panel-source|$.evidence"]
        # Aucune trace de la première sélection, ni primaire ni liée.
        assert first_primary[0] not in primary
        assert first_linked[0] not in linked
        assert page.eval_on_selector_all(f"{PRIMARY}", "n => n.length") == 1
    finally:
        page.close()
        served.__exit__()


def test_a_selection_across_families_replaces_the_previous_one(browser):
    served, page = _open(browser, observe(_source()))
    try:
        page.click("#body-components .row:has-text('C-004-finding')")
        page.click("#body-source [data-path='$.report.title']")
        primary, linked = _state(page)
        assert primary == ["panel-source|$.report.title"]
        assert linked == []
        assert page.eval_on_selector_all("#body-components .selected", "n => n.length") == 0
    finally:
        page.close()
        served.__exit__()


# --- Le payload rouvert ne reste pas ouvert -------------------------------


def test_a_preview_closes_when_the_selection_moves(browser):
    served, page = _open(browser, observe(_source()))
    try:
        first = "#body-components .row:has-text('C-001-cover')"
        page.click(first)
        assert page.is_visible(f"{first} pre")
        page.click("#body-components .row:has-text('C-010-evidence')")
        assert page.is_hidden(f"{first} pre")
    finally:
        page.close()
        served.__exit__()
