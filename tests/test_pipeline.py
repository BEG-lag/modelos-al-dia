from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from modelos_al_dia import store
from modelos_al_dia.http import PoliteClient
from modelos_al_dia.pipeline import actualizar

from .conftest import ROOT


def _corre(root: Path, transporte, hoy=date(2026, 11, 23)):
    with PoliteClient(min_interval=0, retries=0, transport=transporte) as cliente:
        return actualizar(root, hoy, cliente=cliente)


def test_primera_corrida_y_segunda_sin_cambios(tmp_path, transporte):
    r1 = _corre(tmp_path, transporte)
    assert "models.dev" in r1.ok
    assert "anthropic-api" in r1.ok
    # Codex, Gemini CLI y los demás feeds no están grabados: fallan sin tumbar la corrida.
    assert any(k.startswith("github:") for k in r1.fallas)
    catalogo = store.lee(tmp_path, store.CATALOGO, {})
    assert catalogo["modelos"]
    assert store.lee(tmp_path, store.CAMBIOS, []) == []  # la primera corrida no inventa eventos
    novedades = store.lee(tmp_path, store.NOVEDADES, [])
    assert {n["fuente"] for n in novedades} >= {"openai-api", "anthropic-api", "xai-api"}
    assert any(n["fuente"] == "anthropic-blog" for n in novedades)

    antes = {p.name: p.read_text() for p in tmp_path.glob("*.json")}
    r2 = _corre(tmp_path, transporte)
    despues = {p.name: p.read_text() for p in tmp_path.glob("*.json")}
    assert antes == despues
    assert r2.cambios == []


def test_registra_cambios_de_precio(tmp_path, transporte):
    _corre(tmp_path, transporte)
    cat = store.lee(tmp_path, store.CATALOGO, {})
    for m in cat["modelos"]:
        if m["id"] == "claude-opus-5-5":
            m["precio_entrada"] = 99.0
    store.escribe(tmp_path, store.CATALOGO, cat)
    _corre(tmp_path, transporte, hoy=date(2026, 11, 24))
    cambios = store.lee(tmp_path, store.CAMBIOS, [])
    assert any(
        c["id"] == "claude-opus-5-5" and c["tipo"] == "precio_entrada" and c["antes"] == 99.0
        for c in cambios
    )


def test_conserva_catalogo_si_la_fuente_falla(tmp_path):
    import httpx

    shutil.copyfile(ROOT / "data" / "catalogo.json", tmp_path / "catalogo.json")
    original = (tmp_path / "catalogo.json").read_text()
    caido = httpx.MockTransport(lambda r: httpx.Response(503))
    reporte = _corre(tmp_path, caido)
    assert "models.dev" in reporte.fallas
    assert (tmp_path / "catalogo.json").read_text() == original
