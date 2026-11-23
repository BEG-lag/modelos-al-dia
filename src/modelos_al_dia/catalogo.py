"""Catálogo técnico de modelos, armado con dos fuentes abiertas que no piden llave de API.

* models.dev (https://models.dev/api.json, base abierta con licencia MIT): fechas de lanzamiento,
  límites de contexto y salida, precios por millón de tokens, modalidades y si el modelo está
  marcado como obsoleto.
* OpenRouter (https://openrouter.ai/api/v1/models): sirve para confirmar qué modelos se pueden
  usar hoy y para sumar los que models.dev todavía no registra.

El resultado es una lista de registros planos, ordenada y determinista: si las fuentes no
cambian, el archivo ``data/catalogo.json`` tampoco.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from .proveedores import PROVEEDORES

MODELSDEV_URL = "https://models.dev/api.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/models"

# Ids que solo apuntan a otro modelo ("el más reciente de la familia").
ALIAS_RE = re.compile(r"(-latest|-preview-latest)$")
# Instantánea con fecha de otro id: claude-sonnet-4-5-20250929, gpt-4o-2024-05-13.
FECHA_RE = re.compile(r"-(20\d{6}|20\d{2}-\d{2}-\d{2}|\d{4})$")
# Sufijos de nombre que no cambian el modelo: "Claude Sonnet 4.5 (latest)".
NOMBRE_RE = re.compile(r"\s*\((latest|snapshot)\)\s*$", re.I)
# Variantes de OpenRouter que no son modelos distintos.
OR_VARIANTES = (":batch", ":free", ":extended", ":thinking", ":online", ":nitro", ":floor")


def _norm(model_id: str) -> str:
    """Clave para emparejar ids entre fuentes: claude-opus-5.5 == claude-opus-5-5."""
    return re.sub(r"[^a-z0-9]+", "-", model_id.lower()).strip("-")


def _precio(valor: Any) -> float | None:
    if valor is None or valor == "":
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return round(numero, 4) if numero >= 0 else None


def _tipo(model_id: str, familia: str, salida: list[str]) -> str:
    texto = f"{model_id} {familia}".lower()
    if "embed" in texto:
        return "embeddings"
    if "video" in salida:
        return "video"
    if "image" in salida:
        return "imagen"
    if "audio" in salida or any(k in texto for k in ("tts", "transcribe", "whisper", "voice")):
        return "audio"
    if "moderation" in texto:
        return "moderacion"
    return "texto"


def _desde_modelsdev(clave: str, modelo: dict[str, Any]) -> dict[str, Any]:
    modalidades = modelo.get("modalities") or {}
    entrada = sorted(modalidades.get("input") or [])
    salida = sorted(modalidades.get("output") or [])
    limite = modelo.get("limit") or {}
    costo = modelo.get("cost") or {}
    familia = modelo.get("family") or ""
    return {
        "proveedor": clave,
        "id": modelo["id"],
        "nombre": modelo.get("name") or modelo["id"],
        "familia": familia,
        "tipo": _tipo(modelo["id"], familia, salida),
        "estado": "obsoleto" if modelo.get("status") == "deprecated" else "vigente",
        "lanzamiento": modelo.get("release_date") or None,
        "conocimiento": modelo.get("knowledge") or None,
        "contexto": limite.get("context") or None,
        "salida_max": limite.get("output") or None,
        "precio_entrada": _precio(costo.get("input")),
        "precio_salida": _precio(costo.get("output")),
        "precio_cache": _precio(costo.get("cache_read")),
        "entrada": entrada,
        "salida": salida,
        "razonamiento": bool(modelo.get("reasoning")),
        "herramientas": bool(modelo.get("tool_call")),
        "pesos_abiertos": bool(modelo.get("open_weights")),
        "alias": [],
        "openrouter": None,
        "fuente": "models.dev",
    }


def _desde_openrouter(clave: str, modelo: dict[str, Any]) -> dict[str, Any]:
    arq = modelo.get("architecture") or {}
    entrada = sorted(m.replace("file", "pdf") for m in arq.get("input_modalities") or [])
    salida = sorted(arq.get("output_modalities") or [])
    precios = modelo.get("pricing") or {}
    por_millon = {
        k: (None if (p := _precio(precios.get(k))) is None else round(p * 1_000_000, 4))
        for k in ("prompt", "completion", "input_cache_read")
    }
    model_id = modelo["id"].split("/", 1)[1]
    nombre = modelo.get("name") or model_id
    nombre = nombre.split(": ", 1)[1] if ": " in nombre else nombre
    creado = modelo.get("created")
    lanzamiento = (
        datetime.fromtimestamp(creado, UTC).date().isoformat() if isinstance(creado, int) else None
    )
    params = set(modelo.get("supported_parameters") or [])
    return {
        "proveedor": clave,
        "id": model_id,
        "nombre": nombre,
        "familia": "",
        "tipo": _tipo(model_id, "", salida),
        "estado": "vigente",
        "lanzamiento": lanzamiento,
        "conocimiento": modelo.get("knowledge_cutoff") or None,
        "contexto": modelo.get("context_length") or None,
        "salida_max": (modelo.get("top_provider") or {}).get("max_completion_tokens") or None,
        "precio_entrada": por_millon["prompt"],
        "precio_salida": por_millon["completion"],
        "precio_cache": por_millon["input_cache_read"],
        "entrada": entrada,
        "salida": salida,
        "razonamiento": "reasoning" in params,
        "herramientas": "tools" in params,
        "pesos_abiertos": bool(modelo.get("hugging_face_id")),
        "alias": [],
        "openrouter": modelo["id"],
        "fuente": "openrouter",
    }


def construir(modelsdev: dict[str, Any], openrouter: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Une las dos fuentes en una lista ordenada de modelos de los cuatro proveedores."""
    registros: list[dict[str, Any]] = []
    for prov in PROVEEDORES:
        bloque = (modelsdev.get(prov.modelsdev) or {}).get("models") or {}
        crudos = [_desde_modelsdev(prov.clave, m) for m in bloque.values() if m.get("id")]

        # Fuera los alias "-latest" y las instantáneas con fecha que repiten el mismo nombre:
        # se queda el id más corto y los demás se anotan como alias.
        por_id = {r["id"]: r for r in crudos}

        def grupo(r: dict[str, Any], por_id: dict[str, dict[str, Any]] = por_id) -> str:
            base = FECHA_RE.sub("", r["id"])
            canonico = por_id.get(base, r) if base != r["id"] else r
            return NOMBRE_RE.sub("", canonico["nombre"]).strip().lower()

        por_nombre: dict[str, list[dict[str, Any]]] = {}
        for r in crudos:
            if not ALIAS_RE.search(r["id"]):
                por_nombre.setdefault(grupo(r), []).append(r)
        elegidos: list[dict[str, Any]] = []
        for grupo in por_nombre.values():
            grupo.sort(key=lambda r: (len(r["id"]), r["id"]))
            principal = grupo[0]
            principal["alias"] = sorted(r["id"] for r in grupo[1:])
            elegidos.append(principal)

        indice = {}
        for r in elegidos:
            indice[_norm(r["id"])] = r
            for a in r["alias"]:
                indice[_norm(a)] = r

        for m in (openrouter or {}).get("data") or []:
            mid = m.get("id") or ""
            if not mid.startswith(prov.openrouter + "/") or mid.endswith(OR_VARIANTES):
                continue
            if ":" in mid:
                continue
            clave_norm = _norm(mid.split("/", 1)[1])
            if clave_norm in indice:
                indice[clave_norm]["openrouter"] = mid
            elif not ALIAS_RE.search(mid):
                nuevo = _desde_openrouter(prov.clave, m)
                indice[clave_norm] = nuevo
                elegidos.append(nuevo)
        registros.extend(elegidos)

    registros.sort(
        key=lambda r: (r["proveedor"], -_orden_fecha(r["lanzamiento"]), r["id"]),
    )
    return registros


def _orden_fecha(iso: str | None) -> int:
    if not iso:
        return 0
    try:
        return int(iso[:10].replace("-", "").ljust(8, "0"))
    except ValueError:
        return 0


# --------------------------------------------------------------- cambios entre dos días

CAMPOS_VIGILADOS = ("precio_entrada", "precio_salida", "contexto", "salida_max", "estado")


def comparar(
    antes: list[dict[str, Any]], despues: list[dict[str, Any]], fecha: str
) -> list[dict[str, Any]]:
    """Eventos entre dos versiones del catálogo: nuevo, retirado y cambios de campos clave."""
    viejo = {(r["proveedor"], r["id"]): r for r in antes}
    nuevo = {(r["proveedor"], r["id"]): r for r in despues}
    eventos: list[dict[str, Any]] = []
    for clave in sorted(nuevo.keys() - viejo.keys()):
        r = nuevo[clave]
        eventos.append(_evento(fecha, r, "nuevo", None, r["nombre"]))
    for clave in sorted(viejo.keys() - nuevo.keys()):
        r = viejo[clave]
        eventos.append(_evento(fecha, r, "retirado", r["nombre"], None))
    for clave in sorted(viejo.keys() & nuevo.keys()):
        a, d = viejo[clave], nuevo[clave]
        for campo in CAMPOS_VIGILADOS:
            if a.get(campo) != d.get(campo) and d.get(campo) is not None:
                eventos.append(_evento(fecha, d, campo, a.get(campo), d.get(campo)))
    return eventos


def _evento(fecha: str, r: dict[str, Any], tipo: str, antes: Any, despues: Any) -> dict[str, Any]:
    return {
        "fecha": fecha,
        "proveedor": r["proveedor"],
        "id": r["id"],
        "nombre": r["nombre"],
        "tipo": tipo,
        "antes": antes,
        "despues": despues,
    }
