"""Corrida programada: catálogo, novedades oficiales y versiones de agentes de código.

Una fuente que falla se salta y se conserva lo guardado; la corrida solo falla si fallan todas.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from . import agentes, catalogo, novedades, store
from .http import FetchError, PoliteClient

log = logging.getLogger(__name__)

# Historial de novedades que se guarda.
DESDE = "2025-01-01"
# Notas nuevas de anthropic.com que se abren por corrida para leer su título.
ANTHROPIC_MAX_PAGINAS = 25
ANTHROPIC_VENTANA_DIAS = 120
# Si el catálogo nuevo trae menos de esta fracción de modelos, se toma como falla de la fuente.
UMBRAL_CATALOGO = 0.6


@dataclass
class Reporte:
    ok: list[str] = field(default_factory=list)
    fallas: dict[str, str] = field(default_factory=dict)
    cambios: list[str] = field(default_factory=list)


def _json(cliente: PoliteClient, url: str) -> Any:
    return cliente.get_ok(url, accept="application/json").json()


def _texto(cliente: PoliteClient, url: str) -> str:
    return cliente.get_ok(url).text


def actualizar(root: Path, hoy: date, *, cliente: PoliteClient | None = None) -> Reporte:
    reporte = Reporte()
    propio = cliente is None
    cliente = cliente or PoliteClient()
    try:
        _catalogo(cliente, root, hoy, reporte)
        _novedades(cliente, root, hoy, reporte)
        _agentes(cliente, root, reporte)
    finally:
        if propio:
            cliente.close()
    _meta(root, reporte)
    return reporte


# ------------------------------------------------------------------------- catálogo


def _catalogo(cliente: PoliteClient, root: Path, hoy: date, reporte: Reporte) -> None:
    try:
        modelsdev = _json(cliente, catalogo.MODELSDEV_URL)
        reporte.ok.append("models.dev")
    except (FetchError, ValueError) as exc:
        reporte.fallas["models.dev"] = str(exc)
        return
    try:
        openrouter = _json(cliente, catalogo.OPENROUTER_URL)
        reporte.ok.append("openrouter")
    except (FetchError, ValueError) as exc:
        reporte.fallas["openrouter"] = str(exc)
        openrouter = None

    previo = store.lee(root, store.CATALOGO, {"modelos": []})
    nuevos = catalogo.construir(modelsdev, openrouter)
    antes = previo.get("modelos") or []
    if antes and len(nuevos) < UMBRAL_CATALOGO * len(antes):
        reporte.fallas["catalogo"] = (
            f"el catálogo nuevo trae {len(nuevos)} modelos contra {len(antes)};"
            " se conserva el guardado"
        )
        return
    if openrouter is None:
        # Sin OpenRouter no se sabe qué modelos solo existen ahí: se conservan los guardados.
        ids = {(r["proveedor"], r["id"]) for r in nuevos}
        nuevos += [
            r for r in antes if r["fuente"] == "openrouter" and (r["proveedor"], r["id"]) not in ids
        ]
        nuevos.sort(
            key=lambda r: (r["proveedor"], -catalogo._orden_fecha(r["lanzamiento"]), r["id"])
        )

    eventos = catalogo.comparar(antes, nuevos, hoy.isoformat()) if antes else []
    if antes == nuevos:
        return
    fecha = hoy.isoformat() if antes else (previo.get("actualizado") or hoy.isoformat())
    store.escribe(root, store.CATALOGO, {"actualizado": fecha, "modelos": nuevos})
    reporte.cambios.append(f"catálogo ({len(nuevos)} modelos, {len(eventos)} eventos)")
    if eventos:
        historial = store.lee(root, store.CAMBIOS, [])
        store.escribe(root, store.CAMBIOS, eventos + historial)


# ------------------------------------------------------------------------ novedades


def _novedades(cliente: PoliteClient, root: Path, hoy: date, reporte: Reporte) -> None:
    guardadas: list[dict[str, Any]] = store.lee(root, store.NOVEDADES, [])
    por_id = {n["id"]: n for n in guardadas}
    lectores = {
        "openai-api": novedades.lee_openai_api,
        "openai-blog": novedades.lee_openai_blog,
        "anthropic-api": novedades.lee_anthropic_api,
        "google-api": novedades.lee_google_api,
        "google-blog": novedades.lee_google_blog,
        "xai-api": lambda t: novedades.lee_xai_api(t, hoy),
    }
    for clave, lector in lectores.items():
        fuente = novedades.POR_CLAVE[clave]
        try:
            entradas = lector(_texto(cliente, fuente.url))
        except (FetchError, ValueError, SyntaxError) as exc:
            reporte.fallas[clave] = str(exc)
            continue
        if not entradas:
            reporte.fallas[clave] = "la fuente respondió pero no se reconoció ninguna nota"
            continue
        reporte.ok.append(clave)
        for e in entradas:
            if e["fecha"] >= DESDE:
                por_id.setdefault(e["id"], e)

    _anthropic_blog(cliente, root, hoy, por_id, reporte)

    todas = sorted(por_id.values(), key=lambda n: (n["fecha"], n["fuente"], n["id"]), reverse=True)
    if store.escribe(root, store.NOVEDADES, todas):
        reporte.cambios.append(f"novedades ({len(todas) - len(guardadas):+d})")


def _anthropic_blog(
    cliente: PoliteClient,
    root: Path,
    hoy: date,
    por_id: dict[str, dict[str, Any]],
    reporte: Reporte,
) -> None:
    fuente = novedades.POR_CLAVE["anthropic-blog"]
    try:
        paginas = novedades.lee_anthropic_sitemap(_texto(cliente, fuente.url))
    except (FetchError, SyntaxError) as exc:
        reporte.fallas[fuente.clave] = str(exc)
        return
    reporte.ok.append(fuente.clave)
    vistos: dict[str, str] = store.lee(root, store.VISTOS, {})
    corte = (hoy - timedelta(days=ANTHROPIC_VENTANA_DIAS)).isoformat()
    pendientes = sorted(
        (p for p in paginas if p[1] >= corte and p[0] not in vistos),
        key=lambda p: p[1],
        reverse=True,
    )[:ANTHROPIC_MAX_PAGINAS]
    for url, lastmod in pendientes:
        try:
            titulo, publicado = novedades.titulo_de_pagina(_texto(cliente, url))
        except FetchError as exc:
            log.warning("no se pudo leer %s: %s", url, exc)
            continue
        fecha = publicado or lastmod
        vistos[url] = fecha
        if fecha < DESDE:
            continue
        e = novedades._entrada(fuente, fecha, titulo or novedades.titulo_desde_slug(url), url=url)
        por_id.setdefault(e["id"], e)
    store.escribe(root, store.VISTOS, dict(sorted(vistos.items())))


# -------------------------------------------------------------------------- agentes


def _agentes(cliente: PoliteClient, root: Path, reporte: Reporte) -> None:
    guardado: dict[str, list[dict[str, Any]]] = store.lee(root, store.AGENTES, {})
    for clave, repo in agentes.REPOS.items():
        try:
            nuevas = agentes.lee_releases(_texto(cliente, agentes.feed_url(repo)))
        except (FetchError, SyntaxError) as exc:
            reporte.fallas[f"github:{repo}"] = str(exc)
            continue
        reporte.ok.append(f"github:{repo}")
        guardado[clave] = agentes.mezcla(guardado.get(clave, []), nuevas)
    if store.escribe(root, store.AGENTES, guardado):
        reporte.cambios.append("versiones de agentes de código")


def _meta(root: Path, reporte: Reporte) -> None:
    cat = store.lee(root, store.CATALOGO, {"modelos": []})
    nov = store.lee(root, store.NOVEDADES, [])
    cambios = store.lee(root, store.CAMBIOS, [])
    meta = {
        "modelos": len(cat["modelos"]),
        "vigentes": sum(1 for m in cat["modelos"] if m["estado"] == "vigente"),
        "novedades": len(nov),
        "ultima_novedad": nov[0]["fecha"] if nov else None,
        "ultimo_cambio": cambios[0]["fecha"] if cambios else cat.get("actualizado"),
    }
    store.escribe(root, store.META, meta)
