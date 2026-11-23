"""Versiones publicadas de los agentes de código con repositorio abierto en GitHub.

Se leen los feeds Atom de *releases* (públicos, sin llave). Los productos sin repositorio
público (Antigravity, Cursor, Windsurf...) se describen en la ficha curada.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

REPOS: dict[str, str] = {
    "claude-code": "anthropics/claude-code",
    "codex": "openai/codex",
    "gemini-cli": "google-gemini/gemini-cli",
    "grok-build": "xai-org/grok-build",
    "cline": "cline/cline",
    "opencode": "anomalyco/opencode",
}
ATOM = {"a": "http://www.w3.org/2005/Atom"}
MAX_VERSIONES = 30
PRERELEASE_RE = re.compile(r"(alpha|beta|nightly|preview|rc)", re.I)


def feed_url(repo: str) -> str:
    return f"https://github.com/{repo}/releases.atom"


def lee_releases(texto: str) -> list[dict[str, Any]]:
    """Versiones estables, de la más reciente a la más antigua."""
    raiz = ET.fromstring(texto.strip().encode())
    salida = []
    for entry in raiz.findall("a:entry", ATOM):
        titulo = (entry.findtext("a:title", namespaces=ATOM) or "").strip()
        fecha = (entry.findtext("a:updated", namespaces=ATOM) or "")[:10]
        enlace = entry.find("a:link", ATOM)
        url = enlace.get("href") if enlace is not None else None
        version = url.rsplit("/", 1)[-1] if url else titulo
        if not fecha or PRERELEASE_RE.search(version) or PRERELEASE_RE.search(titulo):
            continue
        salida.append({"version": version, "fecha": fecha, "url": url})
    salida.sort(key=lambda v: (v["fecha"], v["version"]), reverse=True)
    return salida[:MAX_VERSIONES]


def mezcla(previas: list[dict[str, Any]], nuevas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Une el historial guardado con lo recién leído (el feed solo trae las últimas)."""
    por_version = {v["version"]: v for v in previas}
    por_version.update({v["version"]: v for v in nuevas})
    todas = sorted(por_version.values(), key=lambda v: (v["fecha"], v["version"]), reverse=True)
    return todas[:MAX_VERSIONES]
