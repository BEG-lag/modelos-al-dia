"""Construye el sitio estático en ``docs/``: una sola página que funciona sin JavaScript.

``assets/app.js`` solo agrega filtros y orden a las tablas. La salida depende de los datos,
no de la hora de construcción.
"""

from __future__ import annotations

import json
import shutil
from html import escape
from importlib.resources import files
from pathlib import Path
from typing import Any

from . import __version__, curado, feeds
from . import vista as v
from .proveedores import POR_CLAVE, PROVEEDORES

REPO_URL = "https://github.com/BEG-lag/modelos-al-dia"
SITE_URL = "https://beg-lag.github.io/modelos-al-dia/"
ICONO = {"si": "●", "parcial": "◐", "no": "○", "brecha": "?"}
ESTADO_TXT = {"si": "Sí", "parcial": "Parcial", "no": "No", "brecha": "Sin dato"}
ORIGEN = {"api": "API", "blog": "Blog"}
ETIQUETA_TXT = {"ESTIMADO": "ESTIMADO", "SUPUESTO": "SUPUESTO", "BRECHA": "BRECHA DE DATO"}


def e(valor: Any) -> str:
    return escape("" if valor is None else str(valor), quote=True)


def _estado(valor: Any) -> str:
    if valor is True:
        return "si"
    if valor is False:
        return "no"
    return valor if valor in ICONO else "brecha"


def chip(prov: str) -> str:
    p = POR_CLAVE[prov]
    return f'<span class="chip" style="--c:{p.color}">{e(p.nombre)}</span>'


def etiqueta(valor: str | None) -> str:
    if not valor:
        return ""
    return f' <span class="tag tag-{e(valor.lower())}">[{e(ETIQUETA_TXT.get(valor, valor))}]</span>'


def fuente(url: str | None, texto: str = "fuente") -> str:
    if not url:
        return ""
    return f'<a class="src" href="{e(url)}" rel="noopener">{e(texto)}</a>'


def celda_estado(cap: dict[str, Any]) -> str:
    est = _estado(cap.get("estado"))
    detalle = cap.get("detalle") or ""
    titulo = f"{ESTADO_TXT[est]}. {detalle}".strip(". ")
    enlace = cap.get("fuente")
    icono = f'<span class="dot dot-{est}" aria-hidden="true">{ICONO[est]}</span>'
    texto = f'<span class="cap-txt">{e(detalle) or e(ESTADO_TXT[est])}</span>'
    contenido = f"{icono}{texto}{etiqueta(cap.get('etiqueta'))}"
    if enlace:
        contenido = f'<a href="{e(enlace)}" rel="noopener" title="{e(titulo)}">{contenido}</a>'
    return f'<td class="cap cap-{est}" data-estado="{est}">{contenido}</td>'


# ------------------------------------------------------------------------ secciones


def seccion(num: str, ancla: str, titulo: str, intro: str, cuerpo: str) -> str:
    return (
        f'<section id="{ancla}"><header class="sec"><span class="num">{num}</span>'
        f"<h2>{e(titulo)}</h2><p>{intro}</p></header>{cuerpo}</section>"
    )


def s_resumen(datos: dict[str, Any]) -> str:
    tarjetas = []
    for r in v.resumen(datos):
        p = r["proveedor"]
        ficha = r["ficha"]
        ins = r["insignia"]
        if ins:
            insignia = (
                f'<p class="big">{e(ins.get("nombre"))}{etiqueta(ins.get("etiqueta"))}</p>'
                f'<p class="muted">{v.fecha_corta(ins.get("lanzamiento"))} · '
                f"{v.tokens(ins.get('contexto_tokens'))} de contexto · "
                f"{v.precio(ins.get('precio_entrada'))} / {v.precio(ins.get('precio_salida'))} por M tokens</p>"
            )
        else:
            insignia = '<p class="big">Sin ficha curada</p>'
        nov = "".join(
            f'<li><time datetime="{e(n["fecha"])}">{v.fecha_corta(n["fecha"], n["precision"])}</time> '
            f'<a href="{e(n["url"])}" rel="noopener">{e(n["titulo"])}</a></li>'
            for n in r["novedades"]
        )
        precio_app = ""
        if r["precio_max"] is not None:
            precio_app = (
                f"Gratis y de {v.usd(r['precio_min'])} a {v.usd(r['precio_max'])} al mes"
                if r["precio_min"]
                else "Gratis"
            )
        matriz = f" · parte de {e(ficha['matriz'])}" if ficha.get("matriz") else ""
        tarjetas.append(
            f'<article class="card" style="--c:{p.color}">'
            f'<header><h3>{e(p.producto)}</h3><span class="muted">{e(ficha.get("proveedor") or p.nombre)}{matriz}</span></header>'
            f'<p class="label">Modelo insignia</p>{insignia}'
            f'<dl class="mini"><div><dt>App</dt><dd>{e(precio_app) or "s/d"}</dd></div>'
            f"<div><dt>Modelos vigentes en la API</dt><dd>{r['vigentes']}</dd></div>"
            f"<div><dt>Último lanzamiento</dt><dd>{v.fecha_corta(r['ultimo_lanzamiento'])}</dd></div>"
            f"<div><dt>Ficha verificada</dt><dd>{v.fecha_corta(ficha.get('verificado'))}</dd></div></dl>"
            f'<p class="label">Lo último</p><ul class="news">{nov}</ul></article>'
        )
    return f'<div class="cards">{"".join(tarjetas)}</div>'


def _celda_modelo(m: dict[str, Any] | None) -> str:
    if not m:
        return '<td class="vacio">·</td>'
    partes = [
        f"<strong>{e(m.get('nombre') or m.get('id'))}</strong>{etiqueta(m.get('etiqueta'))}",
        f"<code>{e(m.get('id'))}</code>",
    ]
    datos = []
    if m.get("contexto_tokens"):
        datos.append(f"{v.tokens(m['contexto_tokens'])} ctx")
    if m.get("precio_entrada") is not None or m.get("precio_salida") is not None:
        datos.append(f"{v.precio(m.get('precio_entrada'))} / {v.precio(m.get('precio_salida'))}")
    if m.get("lanzamiento"):
        datos.append(v.fecha_corta(m["lanzamiento"]))
    if datos:
        partes.append(f'<span class="muted">{" · ".join(datos)}</span>')
    if m.get("notas"):
        partes.append(f'<span class="nota" title="{e(m["notas"])}">{e(m["notas"])}</span>')
    partes.append(fuente(m.get("fuente")))
    return f"<td>{'<br>'.join(p for p in partes if p)}</td>"


def s_comparativa(datos: dict[str, Any]) -> str:
    cab = "".join(f'<th scope="col">{chip(p.clave)}</th>' for p in PROVEEDORES)
    filas = "".join(
        f'<tr><th scope="row">{e(f["etiqueta"])}</th>'
        + "".join(_celda_modelo(f["celdas"][p.clave]) for p in PROVEEDORES)
        + "</tr>"
        for f in v.comparativa(datos)
    )
    return (
        '<div class="scroll"><table class="grid compare"><thead><tr><th scope="col">Categoría</th>'
        f"{cab}</tr></thead><tbody>{filas}</tbody></table></div>"
        '<p class="foot">Precios de API en USD por millón de tokens (entrada / salida), escalón base. '
        "ctx = ventana de contexto. Cada celda liga a su fuente.</p>"
    )


def s_capacidades(datos: dict[str, Any]) -> str:
    cab = "".join(f'<th scope="col">{chip(p.clave)}</th>' for p in PROVEEDORES)
    filas = "".join(
        f'<tr><th scope="row">{e(f["etiqueta"])}</th>'
        + "".join(celda_estado(f["celdas"][p.clave]) for p in PROVEEDORES)
        + "</tr>"
        for f in v.capacidades(datos)
    )
    leyenda = " ".join(
        f'<span><span class="dot dot-{k}">{ICONO[k]}</span> {ESTADO_TXT[k]}</span>' for k in ICONO
    )
    return (
        f'<p class="legend">{leyenda}</p>'
        '<div class="scroll"><table class="grid caps"><thead><tr><th scope="col">Capacidad</th>'
        f"{cab}</tr></thead><tbody>{filas}</tbody></table></div>"
    )


def s_planes(datos: dict[str, Any]) -> str:
    bloques = []
    for p in PROVEEDORES:
        ficha = datos["fichas"].get(p.clave) or {}
        app = ficha.get("app") or {}
        filas = "".join(
            f'<tr><th scope="row">{e(pl.get("nombre"))}{etiqueta(pl.get("etiqueta"))}</th>'
            f'<td class="num">{_precio_plan(pl.get("precio_usd_mes"))}</td>'
            f"<td>{e(pl.get('incluye'))} {fuente(pl.get('fuente'))}</td></tr>"
            for pl in app.get("planes") or []
        )
        enlace = (
            f'<a href="{e(app.get("url"))}" rel="noopener">{e(app.get("nombre") or p.producto)}</a>'
        )
        bloques.append(
            f'<div class="plan" style="--c:{p.color}"><h3>{enlace}</h3>'
            f'<table class="grid"><thead><tr><th scope="col">Plan</th><th scope="col">USD/mes</th>'
            f'<th scope="col">Qué incluye</th></tr></thead><tbody>{filas}</tbody></table></div>'
        )
    return f'<div class="plans">{"".join(bloques)}</div>'


def _precio_plan(valor: Any) -> str:
    if valor is None:
        return "s/d"
    if isinstance(valor, int | float):
        return "Gratis" if valor == 0 else f"${valor:,.2f}".replace(".00", "")
    return e(valor)


def s_agentes(datos: dict[str, Any]) -> str:
    productos = v.agentes(datos)
    if not productos:
        return '<p class="muted">Sin ficha de agentes de código.</p>'
    cab = "".join(
        f'<th scope="col"><span class="vert">{e(et)}</span></th>'
        for et in curado.CAPACIDADES_AGENTE.values()
    )
    filas = []
    for prod in productos:
        caps = prod.get("capacidades") or {}
        version = prod.get("_version")
        ver = (
            f'<br><a class="src" href="{e(version["url"])}" rel="noopener">{e(version["version"])}</a>'
            f' <span class="muted">{v.fecha_corta(version["fecha"])}</span>'
            if version
            else ""
        )
        superficies = ", ".join(prod.get("superficies") or [])
        modelos = ", ".join(prod.get("modelos") or [])
        abierto = _estado(prod.get("codigo_abierto"))
        multi = _estado(prod.get("multi_proveedor"))
        filas.append(
            f'<tr><th scope="row"><strong>{e(prod.get("nombre"))}</strong>{etiqueta(prod.get("etiqueta"))}'
            f'<br><span class="muted">{e(prod.get("empresa"))}</span>{ver}</th>'
            f'<td class="wide">{e(prod.get("tipo"))}<br><span class="muted">{e(superficies)}</span>'
            f'<br><span class="nota" title="{e(prod.get("fuerte_en"))}">{e(prod.get("fuerte_en"))}</span> {fuente(prod.get("fuente"))}</td>'
            f'<td class="wide">{e(modelos)}<br><span class="muted">Otros proveedores: {ESTADO_TXT[multi].lower()}'
            f" · código abierto: {ESTADO_TXT[abierto].lower()}</span></td>"
            f'<td class="wide">{e(prod.get("precio"))}</td>'
            + "".join(
                celda_estado({**(caps.get(k) or {"estado": "brecha"}), "detalle": ""}).replace(
                    '<span class="cap-txt">', '<span class="cap-txt sr">'
                )
                for k in curado.CAPACIDADES_AGENTE
            )
            + "</tr>"
        )
    return (
        '<div class="scroll"><table class="grid agents"><thead><tr><th scope="col">Producto</th>'
        '<th scope="col">Qué es</th><th scope="col">Modelos</th><th scope="col">Precio</th>'
        f"{cab}</tr></thead><tbody>{''.join(filas)}</tbody></table></div>"
        '<p class="foot">La versión más reciente de los agentes con código abierto (Claude Code, Codex, Gemini CLI, Grok Build, Cline y '
        "OpenCode) se lee a diario de sus releases en GitHub. El resto viene de la ficha curada.</p>"
    )


def s_catalogo(datos: dict[str, Any]) -> str:
    filas = []
    for m in datos["catalogo"]:
        razon = "sí" if m["razonamiento"] else "no"
        clase = "" if m["estado"] == "vigente" else ' class="obsoleto"'
        alias = f' title="Alias: {e(", ".join(m["alias"]))}"' if m.get("alias") else ""
        filas.append(
            f'<tr{clase} data-prov="{e(m["proveedor"])}" data-tipo="{e(m["tipo"])}" data-estado="{e(m["estado"])}">'
            f"<td>{chip(m['proveedor'])}</td>"
            f"<td><strong>{e(m['nombre'])}</strong><br><code{alias}>{e(m['id'])}</code></td>"
            f"<td>{e(v.TIPOS.get(m['tipo'], m['tipo']))}</td>"
            f'<td data-v="{e(m["lanzamiento"] or "")}">{v.fecha_corta(m["lanzamiento"])}</td>'
            f'<td class="num" data-v="{m["contexto"] or 0}">{v.tokens(m["contexto"])}</td>'
            f'<td class="num" data-v="{m["salida_max"] or 0}">{v.tokens(m["salida_max"])}</td>'
            f'<td class="num" data-v="{m["precio_entrada"] if m["precio_entrada"] is not None else -1}">{v.precio(m["precio_entrada"])}</td>'
            f'<td class="num" data-v="{m["precio_salida"] if m["precio_salida"] is not None else -1}">{v.precio(m["precio_salida"])}</td>'
            f"<td>{e(v.modalidades(m['entrada']))} → {e(v.modalidades(m['salida']))}</td>"
            f"<td>{razon}</td>"
            f"<td>{'vigente' if m['estado'] == 'vigente' else 'obsoleto'}</td></tr>"
        )
    opciones_prov = "".join(
        f'<option value="{p.clave}">{e(p.nombre)}</option>' for p in PROVEEDORES
    )
    opciones_tipo = "".join(f'<option value="{k}">{e(t)}</option>' for k, t in v.TIPOS.items())
    controles = (
        '<form class="filters" data-table="catalogo" onsubmit="return false">'
        '<label>Buscar <input type="search" name="q" placeholder="gpt, opus, flash…"></label>'
        f'<label>Proveedor <select name="prov"><option value="">Todos</option>{opciones_prov}</select></label>'
        f'<label>Tipo <select name="tipo"><option value="">Todos</option>{opciones_tipo}</select></label>'
        '<label class="check"><input type="checkbox" name="obsoletos"> Incluir obsoletos</label>'
        '<output name="cuenta"></output></form>'
    )
    return (
        controles
        + '<div class="scroll tall"><table class="grid sortable" id="catalogo"><thead><tr>'
        '<th scope="col">Proveedor</th><th scope="col">Modelo</th><th scope="col">Tipo</th>'
        '<th scope="col" data-sort="v">Lanzamiento</th><th scope="col" data-sort="v">Contexto</th>'
        '<th scope="col" data-sort="v">Salida máx.</th><th scope="col" data-sort="v">$ entrada</th>'
        '<th scope="col" data-sort="v">$ salida</th><th scope="col">Modalidades</th>'
        '<th scope="col">Razona</th><th scope="col">Estado</th></tr></thead><tbody>'
        + "".join(filas)
        + "</tbody></table></div>"
        '<p class="foot">Fuente: <a href="https://models.dev">models.dev</a> (MIT) y la API pública de modelos de '
        '<a href="https://openrouter.ai/models">OpenRouter</a>, leídas a diario. Precios en USD por millón de tokens. '
        "Los datos de terceros pueden diferir del proveedor: ante duda, manda la página oficial de cada modelo.</p>"
    )


def s_novedades(datos: dict[str, Any]) -> str:
    recientes = v.novedades_recientes(datos)
    items = "".join(
        f'<li data-prov="{e(n["proveedor"])}" data-origen="{e(n["origen"])}">'
        f'<time datetime="{e(n["fecha"])}">{v.fecha_corta(n["fecha"], n["precision"])}</time>'
        f'{chip(n["proveedor"])}<span class="origen">{ORIGEN.get(n["origen"], n["origen"])}</span>'
        f'<a href="{e(n["url"])}" rel="noopener">{e(n["titulo"])}</a></li>'
        for n in recientes
    )
    opciones = "".join(f'<option value="{p.clave}">{e(p.nombre)}</option>' for p in PROVEEDORES)
    controles = (
        '<form class="filters" data-list="novedades" onsubmit="return false">'
        f'<label>Proveedor <select name="prov"><option value="">Todos</option>{opciones}</select></label>'
        '<label>Origen <select name="origen"><option value="">Todo</option>'
        '<option value="api">Notas de la API</option><option value="blog">Blog y producto</option></select></label>'
        '<output name="cuenta"></output></form>'
    )
    return (
        controles + f'<ol class="timeline" id="novedades">{items}</ol>'
        f'<p class="foot">Últimos {v.DIAS_NOVEDADES} días. Títulos tal como los publica cada fuente oficial, sin resúmenes '
        'con IA. Historial completo en <a href="data/novedades.json">novedades.json</a> y en el '
        '<a href="feed.xml">feed Atom</a>.</p>'
    )


def s_cambios(datos: dict[str, Any]) -> str:
    cambios = datos["cambios"][:80]
    if not cambios:
        return (
            '<p class="muted">El registro de cambios empieza con la primera corrida diaria: a partir de '
            f"{v.fecha_larga(datos['actualizado'])} aquí aparecerá cada modelo nuevo, retirado o con cambio "
            "de precio o de contexto.</p>"
        )
    nombres = {
        "nuevo": "Nuevo",
        "retirado": "Ya no aparece",
        "precio_entrada": "Precio de entrada",
        "precio_salida": "Precio de salida",
        "contexto": "Contexto",
        "salida_max": "Salida máxima",
        "estado": "Estado",
    }

    def fmt(campo: str, valor: Any) -> str:
        if valor is None:
            return "·"
        if campo.startswith("precio"):
            return v.precio(valor)
        if campo in ("contexto", "salida_max"):
            return v.tokens(valor)
        return str(valor)

    filas = "".join(
        f"<tr><td>{v.fecha_corta(c['fecha'])}</td><td>{chip(c['proveedor'])}</td>"
        f"<td><code>{e(c['id'])}</code></td><td>{e(nombres.get(c['tipo'], c['tipo']))}</td>"
        f"<td>{e(fmt(c['tipo'], c['antes']))} → {e(fmt(c['tipo'], c['despues']))}</td></tr>"
        for c in cambios
    )
    return (
        '<div class="scroll"><table class="grid"><thead><tr><th scope="col">Fecha</th><th scope="col">Proveedor</th>'
        '<th scope="col">Modelo</th><th scope="col">Cambio</th><th scope="col">Antes → después</th></tr></thead>'
        f"<tbody>{filas}</tbody></table></div>"
    )


def s_pendientes(datos: dict[str, Any]) -> str:
    bloques = []
    for p in PROVEEDORES:
        pend = (datos["fichas"].get(p.clave) or {}).get("pendientes") or []
        if pend:
            bloques.append(
                f"<h3>{chip(p.clave)}</h3><ul>"
                + "".join(f"<li>{e(x)}</li>" for x in pend)
                + "</ul>"
            )
    pend_ag = datos["agentes"].get("pendientes") or []
    if pend_ag:
        bloques.append(
            "<h3>Agentes de código</h3><ul>"
            + "".join(f"<li>{e(x)}</li>" for x in pend_ag)
            + "</ul>"
        )
    return f"<details><summary>Ver {sum(b.count('<li>') for b in bloques)} dudas abiertas</summary>{''.join(bloques)}</details>"


# ---------------------------------------------------------------------------- página


def pagina(datos: dict[str, Any]) -> str:
    meta = datos["meta"]
    actualizado = datos["actualizado"]
    nav = [
        ("resumen", "Resumen"),
        ("comparativa", "Comparativa"),
        ("capacidades", "Capacidades"),
        ("planes", "Apps y planes"),
        ("agentes", "Agentes de código"),
        ("catalogo", "Catálogo API"),
        ("novedades", "Novedades"),
        ("cambios", "Cambios"),
    ]
    menu = "".join(f'<a href="#{a}">{t}</a>' for a, t in nav)
    secciones = [
        seccion(
            "01",
            "resumen",
            "Resumen",
            "Lo esencial de cada uno: su modelo insignia, cuánto cuesta la app y lo último que anunció.",
            s_resumen(datos),
        ),
        seccion(
            "02",
            "comparativa",
            "Comparativa por categoría",
            "El modelo vigente más reciente de cada proveedor en cada categoría, de la ficha curada.",
            s_comparativa(datos),
        ),
        seccion(
            "03",
            "capacidades",
            "Qué puede hacer cada uno",
            "Capacidades de la app y de la plataforma. Pasa el cursor o toca una celda para ver el detalle y su fuente.",
            s_capacidades(datos),
        ),
        seccion(
            "04",
            "planes",
            "Apps y planes",
            "Precio mensual en USD de los planes de consumo y de equipo, como los publica cada empresa.",
            s_planes(datos),
        ),
        seccion(
            "05",
            "agentes",
            "Agentes de código",
            "Claude Code, Codex, Antigravity y compañía: dónde corren, qué modelos usan y qué pueden hacer.",
            s_agentes(datos),
        ),
        seccion(
            "06",
            "catalogo",
            "Catálogo de modelos de la API",
            f"{meta.get('vigentes', 0)} modelos vigentes (de {meta.get('modelos', 0)} registrados), actualizado a diario de forma automática.",
            s_catalogo(datos),
        ),
        seccion(
            "07",
            "novedades",
            "Novedades oficiales",
            "Notas de versión de las cuatro APIs y anuncios de producto, con liga a la fuente.",
            s_novedades(datos),
        ),
        seccion(
            "08",
            "cambios",
            "Cambios en el catálogo",
            "Modelos nuevos, retirados y cambios de precio o de contexto detectados entre una corrida y otra.",
            s_cambios(datos),
        ),
    ]
    return f"""<!doctype html>
<html lang="es-MX">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>modelos·al·día · ChatGPT, Claude, Gemini y Grok, comparados</title>
<meta name="description" content="Los modelos de OpenAI, Anthropic, Google y xAI al día: comparativa, capacidades, planes, agentes de código y novedades oficiales, cada dato con su fuente.">
<link rel="alternate" type="application/atom+xml" title="modelos·al·día" href="feed.xml">
<link rel="stylesheet" href="assets/style.css?v={__version__}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%230b0d12'/%3E%3Ccircle cx='10' cy='11' r='4' fill='%2310a37f'/%3E%3Ccircle cx='22' cy='11' r='4' fill='%23d97757'/%3E%3Ccircle cx='10' cy='22' r='4' fill='%234285f4'/%3E%3Ccircle cx='22' cy='22' r='4' fill='%23a3a3a3'/%3E%3C/svg%3E">
</head>
<body>
<header class="top">
  <div class="wrap">
    <p class="brand">modelos<span>·</span>al<span>·</span>día<a class="pvk" href="https://pivotek.mx" title="PIVOTEK"><picture class="pvk-logo"><source media="(prefers-color-scheme: light)" srcset="assets/pivotek-logotipo-naranja-placa.svg" width="105" height="43"><img src="assets/pivotek-logotipo-naranja.svg" alt="PIVOTEK" width="90" height="34"></picture><picture class="pvk-iso"><source media="(prefers-color-scheme: light)" srcset="assets/pivotek-isotipo-naranja-placa.svg" width="23" height="24"><img src="assets/pivotek-isotipo-naranja.svg" alt="PIVOTEK" width="21" height="24"></picture></a></p>
    <h1>ChatGPT, Claude, Gemini y Grok, comparados y al día</h1>
    <p class="lede">Modelos, precios, capacidades, planes y agentes de código de OpenAI, Anthropic, Google y xAI.
    Cada dato liga a su fuente; lo que no está confirmado lleva su etiqueta.</p>
    <p class="stamp">Datos al <time datetime="{e(actualizado)}">{v.fecha_larga(actualizado)}</time> ·
    {meta.get("vigentes", 0)} modelos vigentes · {meta.get("novedades", 0)} novedades registradas ·
    <a href="feed.xml">feed</a> · <a href="{REPO_URL}">GitHub</a></p>
    <nav aria-label="Secciones">{menu}</nav>
  </div>
</header>
<main class="wrap">
{"".join(secciones)}
<section id="metodo"><header class="sec"><span class="num">09</span><h2>Fuentes y método</h2></header>
<ul class="method">
<li><strong>Automático, a diario:</strong> catálogo técnico desde models.dev y OpenRouter; notas de versión de las APIs
de OpenAI, Anthropic (Claude Platform), Google (Gemini API) y xAI; blogs de OpenAI, Anthropic y Google (Gemini); versiones
de los agentes de código abiertos en GitHub.</li>
<li><strong>Curado, con revisión humana:</strong> modelos destacados, capacidades, planes y agentes de código viven en
<a href="{REPO_URL}/tree/main/data/curado">data/curado</a>. Una rutina semanal propone cambios en un pull request y nada
se publica sin aprobación.</li>
<li><strong>Etiquetas:</strong> [ESTIMADO] cifra aproximada; [SUPUESTO] premisa no confirmada; [BRECHA DE DATO]
información que falta.</li>
<li>Los títulos de las novedades se muestran en el idioma original de la fuente. No hay resúmenes generados con IA.</li>
</ul>
{s_pendientes(datos)}
</section>
</main>
<footer class="wrap foot-page">
<p>Proyecto independiente, sin relación con OpenAI, Anthropic, Google ni xAI/SpaceX. Las marcas son de sus dueños.
La información puede cambiar sin aviso: verifica en la fuente oficial antes de decidir una compra o una integración.</p>
<p>Código MIT · datos propios CC0 · <a href="{REPO_URL}">{REPO_URL.removeprefix("https://")}</a> · v{__version__}</p>
</footer>
<script src="assets/app.js?v={__version__}" defer></script>
</body>
</html>
"""


def construir_sitio(root: Path, salida: Path) -> str:
    datos = v.carga(root)
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "index.html").write_text(pagina(datos), encoding="utf-8")
    activos = salida / "assets"
    activos.mkdir(exist_ok=True)
    estatico = files("modelos_al_dia") / "static"
    for nombre in (
        "style.css",
        "app.js",
        "pivotek-logotipo-naranja.svg",
        "pivotek-isotipo-naranja.svg",
        "pivotek-logotipo-naranja-placa.svg",
        "pivotek-isotipo-naranja-placa.svg",
    ):
        (activos / nombre).write_text(
            (estatico / nombre).read_text(encoding="utf-8"), encoding="utf-8"
        )
    # Copia de los datos para descargarlos desde la página.
    destino = salida / "data"
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir()
    for nombre in ("catalogo.json", "novedades.json", "cambios.json", "agentes.json", "meta.json"):
        origen = root / nombre
        if origen.exists():
            shutil.copyfile(origen, destino / nombre)
    (destino / "curado.json").write_text(
        json.dumps(
            {"proveedores": datos["fichas"], "agentes_codigo": datos["agentes"]},
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (salida / "feed.xml").write_text(feeds.atom(datos["novedades"]), encoding="utf-8")
    (salida / ".nojekyll").write_text("", encoding="utf-8")
    return f"{len(datos['catalogo'])} modelos, {len(datos['novedades'])} novedades"
