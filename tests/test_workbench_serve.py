"""Surface HTTP du Workbench : lecture seule, routes closes, boucle locale.

Ce que ces tests protègent n'est pas l'affichage — il se contrôle dans un
navigateur — mais les propriétés qu'un écran ne montre pas : qu'aucune route ne
lise un chemin arbitraire, qu'aucune méthode n'écrive, que rien ne sorte de la
machine, et qu'un instantané reste servi même quand la chaîne a refusé la source.
"""
from __future__ import annotations

import json
import threading
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from adc_workbench import observe, observe_mission
from adc_workbench.serve import ASSETS, JSON_ROUTE, LOOPBACK, UI, build_server

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "reference_reports" / "incident_report" / "data" / "sql_server_2014_incident.json"


def _source() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8-sig"))


class _Running:
    """Serveur démarré sur un port libre, arrêté à la sortie du bloc."""

    def __init__(self, snapshot):
        self.server = build_server(snapshot, port=0)
        self.host, self.port = self.server.server_address[:2]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def url(self, route: str) -> str:
        return f"http://{self.host}:{self.port}{route}"

    def get(self, route: str):
        with urlopen(self.url(route), timeout=5) as response:
            return response.status, response.headers, response.read()

    def request(self, route: str, method: str):
        with urlopen(Request(self.url(route), method=method, data=b""), timeout=5) as response:
            return response.status


@pytest.fixture
def running():
    with _Running(observe(_source())) as server:
        yield server


# --- Les routes servies ----------------------------------------------------


def test_the_page_is_served(running):
    status, headers, body = running.get("/")
    assert status == 200
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert b"<!doctype html>" in body.lower()


@pytest.mark.parametrize("route", sorted(ASSETS))
def test_every_declared_asset_is_served(running, route):
    status, _, body = running.get(route)
    assert status == 200
    assert body


def test_the_snapshot_is_served_as_json(running):
    status, headers, body = running.get(JSON_ROUTE)
    assert status == 200
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    snapshot = json.loads(body)
    assert snapshot["document"]["id"] == "ADC-SOC01-2026-SQL2014-001"
    assert snapshot["resolution"], "les occurrences résolues doivent être transportées"


def test_the_served_snapshot_keeps_the_resolution_order(running):
    snapshot = json.loads(running.get(JSON_ROUTE)[2])
    served = [block["component_id"] for block in snapshot["resolution"]]
    observed = [block.component_id for block in observe(_source()).resolution]
    assert served == observed


# --- Aucune lecture arbitraire --------------------------------------------

TRAVERSALS = (
    "/../adc_workbench/serve.py",
    "/../../etc/passwd",
    "/%2e%2e/%2e%2e/etc/passwd",
    "/app.js/../../serve.py",
    "/ui/index.html",
    "/index.html",
    "/../README.md",
    "/snapshot.json/../serve.py",
    "//etc/passwd",
    "/.git/config",
)


@pytest.mark.parametrize("route", TRAVERSALS)
def test_no_route_reads_an_arbitrary_path(running, route):
    """Les routes sont une table close : l'inconnu est refusé, jamais cherché.

    Aucun chemin venu du navigateur n'est joint à un répertoire — la traversée
    n'est donc pas filtrée, elle est inconcevable.
    """
    with pytest.raises(HTTPError) as refused:
        running.get(route)
    assert refused.value.code == 404


def test_the_server_joins_no_request_path_to_a_directory():
    # La propriété ci-dessus tient par construction : le code ne compose jamais
    # un chemin avec ce que le navigateur envoie.
    code = (ROOT / "adc_workbench" / "serve.py").read_text(encoding="utf-8")
    assert "self.path)" not in code.replace("urlsplit(self.path)", "")


# --- Aucune écriture -------------------------------------------------------


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_no_method_writes(running, method):
    with pytest.raises(HTTPError) as refused:
        running.request("/", method)
    assert refused.value.code == 405


# --- Rien ne sort de la machine -------------------------------------------


def test_the_server_listens_on_loopback_only(running):
    assert running.host == LOOPBACK


@pytest.mark.parametrize("name", sorted(asset[0] for asset in ASSETS.values()))
def test_no_asset_loads_anything_external(name):
    """Aucun CDN, aucune police distante, aucune télémétrie."""
    code = (UI / name).read_text(encoding="utf-8")
    for external in ("http://", "https://", "//cdn", "fonts.googleapis", "unpkg", "jsdelivr"):
        assert external not in code, f"{name} : ressource externe ({external})"


def test_the_page_only_references_served_routes():
    parsed = _Links()
    parsed.feed((UI / "index.html").read_text(encoding="utf-8"))
    assert parsed.links, "la page doit référencer ses ressources"
    for link in parsed.links:
        assert link in ASSETS, f"ressource non servie : {link}"


def test_the_server_logs_nothing(capfd, running):
    # Un journal serait une seconde copie de ce qui est observé (W6).
    running.get(JSON_ROUTE)
    captured = capfd.readouterr()
    assert captured.err == ""
    assert captured.out == ""


# --- Structure de la page --------------------------------------------------


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "link" and attributes.get("rel") == "stylesheet":
            self.links.append(attributes.get("href"))
        if tag == "script" and attributes.get("src"):
            self.links.append(attributes["src"])


class _Panels(HTMLParser):
    """Sections de panneau et conteneurs de corps, relevés structurellement."""

    def __init__(self):
        super().__init__()
        self.panels: list[str] = []
        self.bodies: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        identifier = attributes.get("id") or ""
        if tag == "section" and "panel" in (attributes.get("class") or ""):
            self.panels.append(identifier)
        if attributes.get("class") == "panel-body":
            self.bodies.append(identifier)


def test_the_page_declares_the_four_panels(running):
    parsed = _Panels()
    parsed.feed(running.get("/")[2].decode("utf-8"))
    assert parsed.panels == [
        "panel-mission",
        "panel-source",
        "panel-diagnostics",
        "panel-components",
    ]
    assert parsed.bodies == [
        "body-mission",
        "body-source",
        "body-diagnostics",
        "body-components",
    ]


# --- Les cas que l'écran doit encore afficher ------------------------------


def test_a_refused_source_is_still_served():
    source = _source()
    source["findings"][0]["severity"] = "urgent"
    with _Running(observe(source)) as server:
        snapshot = json.loads(server.get(JSON_ROUTE)[2])
    assert snapshot["document"] is None
    assert snapshot["contract_diagnostics"], "l'écran doit pouvoir dire pourquoi"
    assert snapshot["resolution"], "la résolution reste observable"


def test_an_incomplete_mission_is_still_served(tmp_path):
    (tmp_path / "metadata.yml").write_text('titre: "Mission nue"\n', encoding="utf-8")
    with _Running(observe_mission(tmp_path)) as server:
        snapshot = json.loads(server.get(JSON_ROUTE)[2])
    assert snapshot["mission"]["artefacts"]
    assert snapshot["source_diagnostics"], "les sections à rédiger restent visibles"


def test_hostile_content_survives_the_round_trip_as_text(tmp_path):
    """Le contenu observé n'est jamais interprété comme du balisage.

    Il traverse le JSON tel quel ; la page le pose ensuite par `textContent`, ce
    qu'un verrou d'architecture vérifie de son côté.
    """
    hostile = '<script>alert("xss")</script>'
    (tmp_path / "metadata.yml").write_text(f"titre: '{hostile}'\n", encoding="utf-8")
    with _Running(observe_mission(tmp_path)) as server:
        status, headers, body = server.get(JSON_ROUTE)
    assert status == 200
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert json.loads(body)["source"]["report"]["title"] == hostile
