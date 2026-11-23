"""Revisa los datos del repositorio tal como están: fichas curadas, catálogo y sitio."""

from __future__ import annotations

import json

import pytest

from modelos_al_dia import curado, store
from modelos_al_dia.site import construir_sitio
from modelos_al_dia.tablas import generar

from .conftest import ROOT

DATA = ROOT / "data"


def test_fichas_curadas_validas():
    assert curado.valida(DATA) == []


def test_no_se_lee_como_booleano(tmp_path):
    (tmp_path / "curado").mkdir()
    (tmp_path / "curado" / "agentes-codigo.yaml").write_text(
        "productos:\n  - clave: x\n    codigo_abierto: no\n", encoding="utf-8"
    )
    assert curado.agentes_codigo(tmp_path)["productos"][0]["codigo_abierto"] == "no"


def test_cuatro_fichas_y_agentes():
    fichas = curado.proveedores(DATA)
    assert set(fichas) == {"openai", "anthropic", "google", "xai"}
    claves = {p["clave"] for p in curado.agentes_codigo(DATA)["productos"]}
    assert {"claude-code", "codex", "antigravity"} <= claves


def test_catalogo_guardado():
    cat = store.lee(DATA, store.CATALOGO, {})
    ids = [(m["proveedor"], m["id"]) for m in cat["modelos"]]
    assert len(ids) == len(set(ids))
    for m in cat["modelos"]:
        assert m["estado"] in {"vigente", "obsoleto"}
        for campo in ("precio_entrada", "precio_salida"):
            assert m[campo] is None or m[campo] >= 0


@pytest.fixture(scope="module")
def sitio(tmp_path_factory):
    salida = tmp_path_factory.mktemp("docs")
    construir_sitio(DATA, salida)
    return salida


def test_sitio_completo(sitio):
    html = (sitio / "index.html").read_text(encoding="utf-8")
    for ancla in (
        "resumen",
        "comparativa",
        "capacidades",
        "planes",
        "agentes",
        "catalogo",
        "novedades",
    ):
        assert f'id="{ancla}"' in html
    assert "Claude Code" in html
    assert "Antigravity" in html
    assert (sitio / "feed.xml").exists()
    json.loads((sitio / "data" / "curado.json").read_text(encoding="utf-8"))


def test_sin_guion_largo_en_lo_que_escribimos(sitio):
    """Las fichas y las plantillas no usan guion largo (los títulos de terceros sí pueden)."""
    for ruta in (DATA / "curado").glob("*.yaml"):
        assert "\u2014" not in ruta.read_text(encoding="utf-8"), ruta.name
    for ruta in (ROOT / "src" / "modelos_al_dia").rglob("*.*"):
        if ruta.suffix in {".py", ".css", ".js"}:
            assert "\u2014" not in ruta.read_text(encoding="utf-8"), ruta.name


def test_sitio_determinista(sitio, tmp_path):
    construir_sitio(DATA, tmp_path)
    assert (tmp_path / "index.html").read_text() == (sitio / "index.html").read_text()


def test_tablas_md():
    texto = generar(DATA)
    assert texto.startswith("<!-- Archivo generado")
    assert "## 5. Agentes de código" in texto
