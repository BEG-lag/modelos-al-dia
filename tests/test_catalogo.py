from __future__ import annotations

from modelos_al_dia import catalogo

from .conftest import datos_json


def _construido():
    return catalogo.construir(datos_json("modelsdev.json"), datos_json("openrouter.json"))


def test_solo_los_cuatro_proveedores():
    modelos = _construido()
    assert {m["proveedor"] for m in modelos} == {"openai", "anthropic", "google", "xai"}
    assert not any("inkling" in m["id"] for m in modelos)


def test_quita_alias_latest_y_agrupa_instantaneas():
    modelos = {m["id"]: m for m in _construido()}
    assert "gemini-flash-latest" not in modelos
    assert "claude-sonnet-4-5-20250929" not in modelos
    assert modelos["claude-sonnet-4-5"]["alias"] == ["claude-sonnet-4-5-20250929"]


def test_empareja_ids_con_punto_y_guion():
    modelos = {m["id"]: m for m in _construido()}
    assert modelos["claude-opus-5-5"]["openrouter"] == "anthropic/claude-opus-5.5"
    assert modelos["grok-4.7"]["openrouter"] == "x-ai/grok-4.7"


def test_suma_modelos_que_solo_estan_en_openrouter():
    modelos = {m["id"]: m for m in _construido()}
    oss = modelos["gpt-oss-120b"]
    assert oss["fuente"] == "openrouter"
    assert oss["pesos_abiertos"] is True
    assert "gpt-6.2-astra:batch" not in modelos


def test_campos_y_tipos():
    modelos = {m["id"]: m for m in _construido()}
    fable = modelos["claude-fable-5-2"]
    assert fable["precio_entrada"] == 8
    assert fable["precio_salida"] == 40
    assert fable["contexto"] == 1_000_000
    assert fable["tipo"] == "texto"
    assert modelos["grok-imagine-video-1.5"]["tipo"] == "video"
    assert modelos["text-embedding-3-large"]["tipo"] == "embeddings"
    assert modelos["gemini-3.1-flash-image"]["estado"] == "obsoleto"


def test_orden_estable():
    assert _construido() == _construido()


def test_comparar_detecta_nuevo_retirado_y_precio():
    antes = _construido()
    despues = [dict(m) for m in antes if m["id"] != "grok-4.6"]
    for m in despues:
        if m["id"] == "claude-opus-5-5":
            m["precio_entrada"] = 3.0
    despues.append({**antes[0], "id": "modelo-nuevo", "nombre": "Modelo nuevo"})
    eventos = catalogo.comparar(antes, despues, "2026-11-24")
    tipos = {(e["id"], e["tipo"]) for e in eventos}
    assert ("modelo-nuevo", "nuevo") in tipos
    assert ("grok-4.6", "retirado") in tipos
    assert ("claude-opus-5-5", "precio_entrada") in tipos
    assert all(e["fecha"] == "2026-11-24" for e in eventos)
