"""Novedades oficiales: notas de versión de cada API y blogs de producto.

Cada lector recibe el texto ya descargado y devuelve entradas planas. No hay resúmenes hechos
con IA: el título es la primera frase de la nota oficial, en el idioma en que se publicó, y cada
entrada lleva la liga a su fuente.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from typing import Any

MESES_EN = {
    m: i
    for i, m in enumerate(
        [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ],
        start=1,
    )
}
MESES_CORTOS = {k[:3]: v for k, v in MESES_EN.items()}


@dataclass(frozen=True)
class Fuente:
    clave: str
    proveedor: str
    origen: str  # api | blog
    nombre: str
    url: str  # lo que se descarga
    pagina: str  # lo que ve la persona


FUENTES: tuple[Fuente, ...] = (
    Fuente(
        "openai-api",
        "openai",
        "api",
        "Changelog de la API de OpenAI",
        "https://developers.openai.com/api/docs/changelog.md",
        "https://developers.openai.com/api/docs/changelog",
    ),
    Fuente(
        "openai-blog",
        "openai",
        "blog",
        "OpenAI News",
        "https://openai.com/news/rss.xml",
        "https://openai.com/news",
    ),
    Fuente(
        "anthropic-api",
        "anthropic",
        "api",
        "Notas de versión de Claude Platform",
        "https://docs.claude.com/en/release-notes/overview.md",
        "https://platform.claude.com/docs/en/release-notes/overview",
    ),
    Fuente(
        "anthropic-blog",
        "anthropic",
        "blog",
        "Anthropic News",
        "https://www.anthropic.com/sitemap.xml",
        "https://www.anthropic.com/news",
    ),
    Fuente(
        "google-api",
        "google",
        "api",
        "Notas de versión de la API de Gemini",
        "https://ai.google.dev/gemini-api/docs/changelog.md.txt",
        "https://ai.google.dev/gemini-api/docs/changelog",
    ),
    Fuente(
        "google-blog",
        "google",
        "blog",
        "Blog de Google: Gemini",
        "https://blog.google/products/gemini/rss/",
        "https://blog.google/products/gemini/",
    ),
    Fuente(
        "xai-api",
        "xai",
        "api",
        "Notas de versión de la API de xAI",
        "https://docs.x.ai/docs/release-notes.md",
        "https://docs.x.ai/docs/release-notes",
    ),
)
POR_CLAVE = {f.clave: f for f in FUENTES}

# Del blog de OpenAI solo interesan anuncios de producto y de modelos.
OPENAI_CATEGORIAS = {"Product", "Release", "API", "ChatGPT", "Codex"}

LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
MARCAS_RE = re.compile(r"[*_`]+")
TITULO_MAX = 220


def _limpia(texto: str) -> str:
    texto = LINK_RE.sub(r"\1", texto)
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = MARCAS_RE.sub("", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _primera_frase(texto: str) -> str:
    texto = _limpia(texto)
    corte = re.search(r"(?<=[.!?])\s+(?=[A-Z\[`(])", texto)
    if corte and corte.start() >= 25:
        texto = texto[: corte.start()]
    if len(texto) > TITULO_MAX:
        texto = texto[: TITULO_MAX - 1].rsplit(" ", 1)[0] + "…"
    return texto


def _id(fuente: str, fecha: str, titulo: str) -> str:
    huella = hashlib.sha1(f"{fuente}|{fecha}|{titulo}".encode()).hexdigest()[:12]
    return f"{fuente}-{huella}"


def _entrada(
    fuente: Fuente,
    fecha: str,
    titulo: str,
    *,
    url: str | None = None,
    precision: str = "dia",
    etiquetas: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": _id(fuente.clave, fecha, titulo),
        "proveedor": fuente.proveedor,
        "origen": fuente.origen,
        "fuente": fuente.clave,
        "fecha": fecha,
        "precision": precision,
        "titulo": titulo,
        "url": url or fuente.pagina,
        "etiquetas": sorted(set(etiquetas or [])),
    }


MODELO_RE = re.compile(
    r"`((?:gpt|o\d|claude|gemini|gemma|veo|imagen|grok|sora|genie|nano-banana|lyria|codex)"
    r"[a-z0-9.\-]*)`",
    re.I,
)


def _modelos_mencionados(texto: str) -> list[str]:
    return sorted({m.lower() for m in MODELO_RE.findall(texto)})[:6]


# ------------------------------------------------------------------ notas de versión (md)


def lee_openai_api(texto: str, fuente: Fuente = POR_CLAVE["openai-api"]) -> list[dict[str, Any]]:
    """Formato: '## November, 2026' > '### Nov 19' > línea de etiquetas > párrafos."""
    entradas: list[dict[str, Any]] = []
    anio = mes = None
    bloques = re.split(r"^(#{2,3} .+)$", texto, flags=re.M)
    encabezado = ""
    for parte in bloques:
        if parte.startswith("## "):
            m = re.match(r"## (\w+),? (\d{4})", parte)
            if m and m.group(1).lower() in MESES_EN:
                mes, anio = MESES_EN[m.group(1).lower()], int(m.group(2))
            continue
        if parte.startswith("### "):
            encabezado = parte[4:].strip()
            continue
        if not encabezado or anio is None:
            continue
        m = re.match(r"([A-Za-z]{3})\w* (\d{1,2})", encabezado)
        encabezado = ""
        if not m or m.group(1).lower() not in MESES_CORTOS:
            continue
        dia = date(anio, MESES_CORTOS[m.group(1).lower()], int(m.group(2)))
        if mes and dia.month > mes:  # una nota de diciembre bajo enero: año anterior
            dia = dia.replace(year=anio - 1)
        lineas = [ln.strip() for ln in parte.strip().splitlines() if ln.strip()]
        etiquetas: list[str] = []
        if lineas and ("·" in lineas[0] or lineas[0].startswith(("Feature", "Update"))):
            etiquetas = [
                t.split(":", 1)[1].strip()
                for t in lineas.pop(0).split("·")
                if t.strip().startswith("Model:")
            ]
        cuerpo = " ".join(lineas)
        if not cuerpo:
            continue
        titulo = _primera_frase(cuerpo)
        entradas.append(_entrada(fuente, dia.isoformat(), titulo, etiquetas=etiquetas or None))
    return entradas


def lee_anthropic_api(
    texto: str, fuente: Fuente = POR_CLAVE["anthropic-api"]
) -> list[dict[str, Any]]:
    """Formato: '### November 23, 2026' seguido de viñetas '* ...'."""
    entradas: list[dict[str, Any]] = []
    partes = re.split(r"^### (\w+ \d{1,2}, \d{4})\s*$", texto, flags=re.M)
    for i in range(1, len(partes) - 1, 2):
        try:
            dia = datetime.strptime(partes[i], "%B %d, %Y").date()
        except ValueError:
            continue
        for vineta in re.split(r"^\* ", partes[i + 1], flags=re.M)[1:]:
            vineta = vineta.strip()
            if not vineta:
                continue
            entradas.append(
                _entrada(
                    fuente,
                    dia.isoformat(),
                    _primera_frase(vineta),
                    etiquetas=_modelos_mencionados(vineta),
                )
            )
    return entradas


def lee_google_api(texto: str, fuente: Fuente = POR_CLAVE["google-api"]) -> list[dict[str, Any]]:
    """Formato: '## November 19, 2026  {% id="11-19-2026" %}' y viñetas '*   **Título**: ...'."""
    entradas: list[dict[str, Any]] = []
    partes = re.split(
        r'^## (\w+ \d{1,2}, \d{4})\s*(?:\{% id="([^"]+)" %\})?\s*$', texto, flags=re.M
    )
    for i in range(1, len(partes) - 2, 3):
        try:
            dia = datetime.strptime(partes[i], "%B %d, %Y").date()
        except ValueError:
            continue
        ancla = partes[i + 1] or ""
        for vineta in re.split(r"^\*\s+", partes[i + 2], flags=re.M)[1:]:
            vineta = vineta.strip()
            if not vineta:
                continue
            negrita = re.match(r"\*\*(.+?)\*\*", vineta)
            titulo = _limpia(negrita.group(1)).rstrip(":") if negrita else _primera_frase(vineta)
            url = f"{fuente.pagina}#{ancla}" if ancla else None
            entradas.append(
                _entrada(
                    fuente,
                    dia.isoformat(),
                    titulo,
                    url=url,
                    etiquetas=_modelos_mencionados(vineta),
                )
            )
    return entradas


def lee_xai_api(
    texto: str, hoy: date, fuente: Fuente = POR_CLAVE["xai-api"]
) -> list[dict[str, Any]]:
    """Formato: '## November' (año en curso) o '## December 2025' > '### Título'. Fecha por mes.

    El año se deduce recorriendo los meses de arriba hacia abajo desde el mes actual: cuando el
    mes sube en lugar de bajar, cambió el año.
    """
    entradas: list[dict[str, Any]] = []
    anio, ultimo_mes = hoy.year, None
    mes = None
    titulo = None
    for linea in texto.splitlines():
        m_mes = re.match(r"^## (\w+)(?: (\d{4}))?\s*$", linea)
        if m_mes and m_mes.group(1).lower() in MESES_EN:
            mes = MESES_EN[m_mes.group(1).lower()]
            if m_mes.group(2):  # los meses de años pasados traen el año
                anio = int(m_mes.group(2))
            elif mes > (hoy.month if ultimo_mes is None else ultimo_mes):
                anio -= 1
            ultimo_mes = mes
            continue
        m_tit = re.match(r"^### (.+)$", linea)
        if m_tit and mes:
            titulo = _limpia(m_tit.group(1))
            fecha = date(anio, mes, 1).isoformat()
            entradas.append(
                _entrada(
                    fuente,
                    fecha,
                    titulo,
                    precision="mes",
                    etiquetas=_modelos_mencionados(m_tit.group(1)),
                )
            )
    return entradas


# ------------------------------------------------------------------------------ blogs


def _rss_items(texto: str) -> list[ET.Element]:
    raiz = ET.fromstring(texto.strip().encode())
    return raiz.findall("./channel/item")


def _fecha_rss(valor: str | None) -> str | None:
    if not valor:
        return None
    try:
        return parsedate_to_datetime(valor).date().isoformat()
    except (TypeError, ValueError):
        return None


def lee_openai_blog(texto: str, fuente: Fuente = POR_CLAVE["openai-blog"]) -> list[dict[str, Any]]:
    entradas = []
    for item in _rss_items(texto):
        categorias = {(c.text or "").strip() for c in item.findall("category")}
        if not categorias & OPENAI_CATEGORIAS:
            continue
        fecha = _fecha_rss(item.findtext("pubDate"))
        titulo = _limpia(item.findtext("title") or "")
        if fecha and titulo:
            entradas.append(
                _entrada(
                    fuente, fecha, titulo, url=item.findtext("link"), etiquetas=list(categorias)
                )
            )
    return entradas


def lee_google_blog(texto: str, fuente: Fuente = POR_CLAVE["google-blog"]) -> list[dict[str, Any]]:
    entradas = []
    for item in _rss_items(texto):
        fecha = _fecha_rss(item.findtext("pubDate"))
        titulo = _limpia(item.findtext("title") or "")
        if fecha and titulo:
            entradas.append(_entrada(fuente, fecha, titulo, url=item.findtext("link")))
    return entradas


SITEMAP_NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def lee_anthropic_sitemap(texto: str) -> list[tuple[str, str]]:
    """(url, lastmod) de cada página de /news/ del sitemap de anthropic.com."""
    raiz = ET.fromstring(texto.encode())
    salida = []
    for url in raiz.findall("s:url", SITEMAP_NS):
        loc = (url.findtext("s:loc", namespaces=SITEMAP_NS) or "").strip()
        mod = (url.findtext("s:lastmod", namespaces=SITEMAP_NS) or "").strip()
        if "/news/" in loc and mod:
            salida.append((loc, mod[:10]))
    return salida


TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
META_FECHA_RE = re.compile(
    r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})|'
    r'property="article:published_time"\s+content="(\d{4}-\d{2}-\d{2})',
)


def titulo_de_pagina(html: str) -> tuple[str | None, str | None]:
    """Título y fecha de publicación (si la página la declara) de una nota de anthropic.com."""
    import html as html_mod

    m = TITLE_RE.search(html)
    titulo = None
    if m:
        titulo = html_mod.unescape(_limpia(m.group(1)))
        previo = None
        while previo != titulo:  # "Nota | Anthropic \\ Anthropic"
            previo = titulo
            titulo = re.sub(r"\s*[\\|·-]\s*Anthropic\s*$", "", titulo).strip()
        titulo = titulo or None
    f = META_FECHA_RE.search(html)
    fecha = (f.group(1) or f.group(2)) if f else None
    return titulo, fecha


def titulo_desde_slug(url: str) -> str:
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    return slug.replace("-", " ").strip().capitalize()
