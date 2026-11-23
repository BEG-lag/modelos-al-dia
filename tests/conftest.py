"""Fixtures compartidos. Todo corre sin red, con respuestas reales grabadas el 2026-11-23
(recortadas). ``anthropic_news_page.html`` es una página mínima con la misma forma que las notas
de anthropic.com."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).parent.parent

RUTAS = {
    "https://models.dev/api.json": "modelsdev.json",
    "https://openrouter.ai/api/v1/models": "openrouter.json",
    "https://developers.openai.com/api/docs/changelog.md": "openai_changelog.md",
    "https://openai.com/news/rss.xml": "openai_news.xml",
    "https://docs.claude.com/en/release-notes/overview.md": "claude_release_notes.md",
    "https://www.anthropic.com/sitemap.xml": "anthropic_sitemap.xml",
    "https://ai.google.dev/gemini-api/docs/changelog.md.txt": "gemini_changelog.md",
    "https://blog.google/products/gemini/rss/": "gemini_blog.xml",
    "https://docs.x.ai/docs/release-notes.md": "xai_release_notes.md",
    "https://github.com/anthropics/claude-code/releases.atom": "claude_code_releases.atom",
}


def texto(nombre: str) -> str:
    return (FIXTURES / nombre).read_text(encoding="utf-8")


def datos_json(nombre: str) -> dict:
    return json.loads(texto(nombre))


def manejador(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url in RUTAS:
        return httpx.Response(200, text=texto(RUTAS[url]))
    if url.startswith("https://www.anthropic.com/news/"):
        return httpx.Response(200, text=texto("anthropic_news_page.html"))
    return httpx.Response(404, text="no grabado")


@pytest.fixture
def transporte() -> httpx.MockTransport:
    return httpx.MockTransport(manejador)
