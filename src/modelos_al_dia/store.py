"""Lectura y escritura de ``data/``. JSON ordenado y estable: sin cambios, sin diff."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path("data")

CATALOGO = "catalogo.json"
CAMBIOS = "cambios.json"
NOVEDADES = "novedades.json"
AGENTES = "agentes.json"
VISTOS = "vistos.json"
META = "meta.json"


def lee(root: Path, nombre: str, defecto: Any) -> Any:
    ruta = root / nombre
    if not ruta.exists():
        return defecto
    return json.loads(ruta.read_text(encoding="utf-8"))


def escribe(root: Path, nombre: str, datos: Any) -> bool:
    """Escribe solo si el contenido cambió. Devuelve True si hubo cambio."""
    ruta = root / nombre
    texto = json.dumps(datos, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if ruta.exists() and ruta.read_text(encoding="utf-8") == texto:
        return False
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")
    return True
