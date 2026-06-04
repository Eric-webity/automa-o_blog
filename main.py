"""
GEO Extractor — interface NiceGUI (Content Studio).

Execução: python main.py
"""

from __future__ import annotations

import logging
import os
import socket
import sys

from dotenv import load_dotenv
from nicegui import ui

from api import register_api_routes
from config.paths import DATA_DIR, OUTPUT_DIR
from config.production import resolve_storage_secret
from db import init_db
from ui.pages import register_pages
from ui.state import create_app_config

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
init_db()
register_api_routes()
config = create_app_config()
register_pages(config)


def _is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """Testa bind real (connect_ex falha no Windows com portas ocupadas)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _find_available_port(start: int = 8080, attempts: int = 50) -> int:
    """Encontra porta livre para o servidor NiceGUI."""
    forced = os.getenv("GEO_PORT")
    candidates: list[int] = []
    if forced:
        candidates.append(int(forced))
    candidates.extend(range(start, start + attempts))
    seen: set[int] = set()
    for port in candidates:
        if port in seen:
            continue
        seen.add(port)
        if _is_port_available(port):
            return port
    raise SystemExit(
        f"Nenhuma porta livre entre {start} e {start + attempts - 1}. "
        "Feche instâncias antigas do GEO Extractor ou defina GEO_PORT no .env."
    )


if __name__ in {"__main__", "__mp_main__"}:
    port = _find_available_port()
    logger.info("GEO Extractor: http://localhost:%s", port)
    print(f"GEO Extractor: http://localhost:{port}")
    ui.run(
        title="GEO Extractor",
        port=port,
        reload=False,
        show=True,
        storage_secret=resolve_storage_secret(),
    )
