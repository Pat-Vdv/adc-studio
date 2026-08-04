"""Serveur local du Workbench : lecture seule, boucle locale, routes fermées.

Trois propriétés sont tenues par construction plutôt que par vigilance :

- **aucune lecture arbitraire** — les routes sont une table close. Aucun chemin
  venu du navigateur n'est joint à un répertoire, donc aucune traversée n'est
  concevable, échappée ou non ;
- **aucune écriture** — seule la méthode GET est servie ; tout le reste est
  refusé sans être interprété ;
- **aucune sortie externe** — l'écoute est sur la boucle locale, et la page ne
  charge que des ressources servies ici.

Le journal ne reproduit rien de ce qui est observé (ADR-0014, W6) : les requêtes
ne portent que des noms de routes fixes, et elles ne sont pas journalisées.

Le serveur observe **une** mission, fournie au lancement. Le navigateur n'en
reçoit jamais un chemin exploitable pour en demander un autre : il n'existe
aucune route qui prenne un chemin en paramètre.
"""
from __future__ import annotations

import argparse
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .observation import observe_mission
from .serialize import to_json
from .snapshot import WorkbenchSnapshot

UI = Path(__file__).resolve().parent / "ui"

LOOPBACK = "127.0.0.1"

JSON_ROUTE = "/snapshot.json"

# Table close : une route inconnue n'est pas cherchée sur le disque, elle est
# refusée. C'est ce qui rend la traversée de chemin impossible par construction.
ASSETS: dict[str, tuple[str, str]] = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


class WorkbenchHandler(BaseHTTPRequestHandler):
    """Sert un instantané et les ressources de la page. Rien d'autre."""

    snapshot: WorkbenchSnapshot

    protocol_version = "HTTP/1.1"
    server_version = "ADCWorkbench"
    sys_version = ""

    def log_message(self, format: str, *args: object) -> None:
        """Silence délibéré : un journal est une seconde copie de ce qu'on lit."""

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # La page ne charge aucune ressource externe : on l'interdit aussi côté
        # navigateur, pour que l'absence de réseau soit tenue et pas seulement
        # constatée.
        self.send_header("Content-Security-Policy", "default-src 'self'; base-uri 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _refuse(self, status: int) -> None:
        self._send(b"", "text/plain; charset=utf-8", status)

    def do_GET(self) -> None:  # noqa: N802 — nom imposé par la bibliothèque
        route = urlsplit(self.path).path
        if route == JSON_ROUTE:
            self._send(to_json(self.snapshot).encode("utf-8"), "application/json; charset=utf-8")
            return
        asset = ASSETS.get(route)
        if asset is None:
            self._refuse(404)
            return
        name, content_type = asset
        self._send((UI / name).read_bytes(), content_type)

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def _method_not_allowed(self) -> None:
        self._refuse(405)

    do_POST = do_PUT = do_DELETE = do_PATCH = _method_not_allowed  # noqa: N815


def build_server(snapshot: WorkbenchSnapshot, port: int = 0) -> ThreadingHTTPServer:
    """Serveur prêt à écouter, lié à la boucle locale.

    Le port 0 laisse le système en choisir un libre : c'est ce dont les tests ont
    besoin, et cela évite qu'un port fixe soit un prérequis d'exécution.
    """
    handler = type("BoundWorkbenchHandler", (WorkbenchHandler,), {"snapshot": snapshot})
    return ThreadingHTTPServer((LOOPBACK, port), handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Workbench ADC Studio (lecture seule).")
    parser.add_argument("mission", type=Path, help="Dossier de la mission à observer")
    parser.add_argument("--port", type=int, default=8017)
    arguments = parser.parse_args(argv)

    try:
        snapshot = observe_mission(arguments.mission)
    except (FileNotFoundError, ValueError) as refused:
        print(f"MISSION ILLISIBLE : {refused}", file=sys.stderr)
        return 1

    server = build_server(snapshot, arguments.port)
    host, port = server.server_address[:2]
    print(f"Workbench : http://{host}:{port}  (lecture seule, Ctrl+C pour arrêter)")
    print(f"Mission observée : {arguments.mission}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
