from __future__ import annotations

from datetime import date

import pytest

from modelos_al_dia import agentes, novedades

from .conftest import texto


def _validas(entradas):
    assert entradas
    for n in entradas:
        date.fromisoformat(n["fecha"])
        assert n["titulo"].strip()
        assert n["url"].startswith("https://")
    assert len({n["id"] for n in entradas}) == len(entradas)


def test_openai_api():
    entradas = novedades.lee_openai_api(texto("openai_changelog.md"))
    _validas(entradas)
    assert entradas[0]["fecha"] == "2026-11-19"
    assert "gpt-live-1.1" in entradas[0]["etiquetas"]
    assert any("gpt-6.2-astra" in n["etiquetas"] for n in entradas)


def test_anthropic_api():
    entradas = novedades.lee_anthropic_api(texto("claude_release_notes.md"))
    _validas(entradas)
    assert entradas[0]["fecha"] == "2026-11-23"
    assert "claude-opus-4-5" in entradas[0]["etiquetas"]


def test_google_api_usa_negritas_y_anclas():
    entradas = novedades.lee_google_api(texto("gemini_changelog.md"))
    _validas(entradas)
    assert entradas[0]["titulo"].startswith("Genie 4")
    assert entradas[0]["url"].endswith("#11-19-2026")


def test_xai_deduce_el_anio():
    entradas = novedades.lee_xai_api(texto("xai_release_notes.md"), date(2026, 11, 23))
    _validas(entradas)
    assert entradas[0]["fecha"] == "2026-11-01"
    assert entradas[0]["precision"] == "mes"
    fechas = [n["fecha"] for n in entradas]
    assert fechas == sorted(fechas, reverse=True)
    assert min(fechas) < "2026-01-01"  # el historial cruza al año anterior


def test_openai_blog_filtra_categorias():
    entradas = novedades.lee_openai_blog(texto("openai_news.xml"))
    _validas(entradas)
    assert all(set(n["etiquetas"]) & novedades.OPENAI_CATEGORIAS for n in entradas)


def test_google_blog():
    _validas(novedades.lee_google_blog(texto("gemini_blog.xml")))


def test_sitemap_y_titulo_de_anthropic():
    paginas = novedades.lee_anthropic_sitemap(texto("anthropic_sitemap.xml"))
    assert paginas
    assert all("/news/" in u for u, _ in paginas)
    titulo, fecha = novedades.titulo_de_pagina(texto("anthropic_news_page.html"))
    assert titulo == "Anthropic prices initial public offering"
    assert fecha == "2026-11-18"


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (
            "Use [GPT-6.2](https://x) for **demanding** coding tasks. More text.",
            "Use GPT-6.2 for demanding coding tasks.",
        ),
        ("Short. Then more.", "Short. Then more."),
    ],
)
def test_primera_frase(entrada, esperado):
    assert novedades._primera_frase(entrada) == esperado


def test_releases_de_github():
    versiones = agentes.lee_releases(texto("claude_code_releases.atom"))
    assert versiones
    assert versiones[0]["version"].startswith("v")
    assert agentes.mezcla(versiones[1:], versiones[:1]) == versiones
