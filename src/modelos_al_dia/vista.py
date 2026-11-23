"""Arma, a partir de ``data/``, lo que muestran la página y ``TABLAS.md``.

Todo sale de los archivos guardados; nada depende de la hora en que se construye.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from . import curado, store
from .proveedores import POR_CLAVE, PROVEEDORES

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_LARGOS = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]
CATEGORIAS_COMPARATIVA = [
    ("insignia", "Insignia"),
    ("razonamiento", "Razonamiento"),
    ("equilibrado", "Equilibrado"),
    ("rapido", "Rápido y barato"),
    ("codigo", "Código"),
    ("imagen", "Imagen"),
    ("video", "Video"),
    ("audio", "Voz y audio"),
    ("abierto", "Pesos abiertos"),
]
MODALIDADES = {
    "text": "texto",
    "image": "imagen",
    "pdf": "PDF",
    "audio": "audio",
    "video": "video",
    "texto": "texto",
    "imagen": "imagen",
}
TIPOS = {
    "texto": "Texto",
    "imagen": "Imagen",
    "video": "Video",
    "audio": "Audio",
    "embeddings": "Embeddings",
    "moderacion": "Moderación",
}
DIAS_NOVEDADES = 45


def norm(model_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (model_id or "").lower()).strip("-")


# ------------------------------------------------------------------------- formatos


def fecha_corta(iso: str | None, precision: str = "dia") -> str:
    if not iso:
        return "s/d"
    d = date.fromisoformat(iso[:10])
    if precision == "mes":
        return f"{MESES[d.month - 1]} {d.year}"
    return f"{d.day} {MESES[d.month - 1]} {d.year}"


def fecha_larga(iso: str) -> str:
    d = date.fromisoformat(iso[:10])
    return f"{d.day} de {MESES_LARGOS[d.month - 1]} de {d.year}"


def tokens(n: int | None) -> str:
    if not n:
        return "s/d"
    if n >= 1_000_000:
        valor = n / 1_000_000
        return f"{valor:.2f}".rstrip("0").rstrip(".") + "M"
    if n >= 1_000:
        return f"{round(n / 1000):d}K"
    return str(n)


def usd(valor: float | None) -> str:
    """Precio de plan mensual: $20, $4.99."""
    if valor is None:
        return "s/d"
    return f"${valor:,.0f}" if float(valor).is_integer() else f"${valor:,.2f}"


def precio(valor: float | None) -> str:
    if valor is None:
        return "s/d"
    if valor == 0:
        return "gratis"
    if valor < 0.1:
        return f"${valor:.3f}".rstrip("0")
    return f"${valor:,.2f}"


def modalidades(lista: list[str] | None) -> str:
    return ", ".join(MODALIDADES.get(m, m) for m in (lista or [])) or "s/d"


# ------------------------------------------------------------------------- modelo


def carga(root: Path) -> dict[str, Any]:
    cat = store.lee(root, store.CATALOGO, {"modelos": []})
    modelos = cat["modelos"]
    indice: dict[tuple[str, str], dict[str, Any]] = {}
    for m in modelos:
        indice[(m["proveedor"], norm(m["id"]))] = m
        for a in m.get("alias") or []:
            indice[(m["proveedor"], norm(a))] = m
    fichas = curado.proveedores(root)
    novedades = store.lee(root, store.NOVEDADES, [])
    cambios = store.lee(root, store.CAMBIOS, [])
    meta = store.lee(root, store.META, {})
    corte_base = max(
        [n["fecha"] for n in novedades] + [cat.get("actualizado") or "2026-01-01"],
    )
    return {
        "actualizado": corte_base,
        "meta": meta,
        "catalogo": modelos,
        "indice": indice,
        "fichas": fichas,
        "agentes": curado.agentes_codigo(root),
        "versiones": store.lee(root, store.AGENTES, {}),
        "novedades": novedades,
        "cambios": cambios,
    }


def enriquece(prov: str, m: dict[str, Any], indice: dict) -> dict[str, Any]:
    """Modelo de la ficha curada con los huecos llenados desde el catálogo automático."""
    auto = indice.get((prov, norm(m.get("id", ""))))
    salida = dict(m)
    salida["_auto"] = auto
    if auto:
        for curado_k, auto_k in (
            ("contexto_tokens", "contexto"),
            ("salida_max_tokens", "salida_max"),
            ("precio_entrada", "precio_entrada"),
            ("precio_salida", "precio_salida"),
            ("lanzamiento", "lanzamiento"),
        ):
            if salida.get(curado_k) in (None, "") and auto.get(auto_k) is not None:
                salida[curado_k] = auto[auto_k]
    return salida


def comparativa(datos: dict[str, Any]) -> list[dict[str, Any]]:
    """Filas por categoría; en cada una, el modelo vigente más reciente de cada proveedor."""
    filas = []
    for cat, etiqueta in CATEGORIAS_COMPARATIVA:
        celdas = {}
        for p in PROVEEDORES:
            ficha = datos["fichas"].get(p.clave) or {}
            candidatos = [
                m
                for m in ficha.get("modelos") or []
                if m.get("categoria") == cat and m.get("estado") in ("vigente", "preliminar")
            ]
            candidatos.sort(key=lambda m: str(m.get("lanzamiento") or ""), reverse=True)
            celdas[p.clave] = (
                enriquece(p.clave, candidatos[0], datos["indice"]) if candidatos else None
            )
        if any(celdas.values()):
            filas.append({"categoria": cat, "etiqueta": etiqueta, "celdas": celdas})
    return filas


def capacidades(datos: dict[str, Any]) -> list[dict[str, Any]]:
    filas = []
    for clave, etiqueta in curado.CAPACIDADES.items():
        celdas = {}
        for p in PROVEEDORES:
            caps = (datos["fichas"].get(p.clave) or {}).get("capacidades") or {}
            celdas[p.clave] = caps.get(clave) or {"estado": "brecha", "detalle": "Sin ficha"}
        filas.append({"clave": clave, "etiqueta": etiqueta, "celdas": celdas})
    return filas


def planes(datos: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {
        p.clave: ((datos["fichas"].get(p.clave) or {}).get("app") or {}).get("planes") or []
        for p in PROVEEDORES
    }


def agentes(datos: dict[str, Any]) -> list[dict[str, Any]]:
    productos = []
    for prod in datos["agentes"].get("productos") or []:
        versiones = datos["versiones"].get(prod.get("clave")) or []
        productos.append({**prod, "_version": versiones[0] if versiones else None})
    return productos


def novedades_recientes(datos: dict[str, Any], dias: int = DIAS_NOVEDADES) -> list[dict[str, Any]]:
    corte = (date.fromisoformat(datos["actualizado"]) - timedelta(days=dias)).isoformat()
    return [n for n in datos["novedades"] if n["fecha"] >= corte]


def resumen(datos: dict[str, Any]) -> list[dict[str, Any]]:
    """Tarjeta por proveedor: insignia, app, última novedad y conteo del catálogo."""
    salida = []
    for p in PROVEEDORES:
        ficha = datos["fichas"].get(p.clave) or {}
        insignias = [
            m
            for m in ficha.get("modelos") or []
            if m.get("categoria") == "insignia" and m.get("estado") == "vigente"
        ]
        insignias.sort(key=lambda m: str(m.get("lanzamiento") or ""), reverse=True)
        vigentes = [
            m for m in datos["catalogo"] if m["proveedor"] == p.clave and m["estado"] == "vigente"
        ]
        ultimo = max((m["lanzamiento"] or "" for m in vigentes), default="")
        nov = [n for n in datos["novedades"] if n["proveedor"] == p.clave][:3]
        precios = [
            pl.get("precio_usd_mes")
            for pl in (ficha.get("app") or {}).get("planes") or []
            if isinstance(pl.get("precio_usd_mes"), int | float)
        ]
        salida.append(
            {
                "proveedor": p,
                "ficha": ficha,
                "insignia": enriquece(p.clave, insignias[0], datos["indice"])
                if insignias
                else None,
                "vigentes": len(vigentes),
                "ultimo_lanzamiento": ultimo or None,
                "novedades": nov,
                "precio_min": min((x for x in precios if x > 0), default=None),
                "precio_max": max(precios, default=None),
            }
        )
    return salida


def nombre_proveedor(clave: str) -> str:
    return POR_CLAVE[clave].nombre if clave in POR_CLAVE else clave
