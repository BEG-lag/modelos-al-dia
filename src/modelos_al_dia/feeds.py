"""Feed Atom 1.0 de novedades. Determinista: ``<updated>`` es la fecha de la nota más nueva."""

from __future__ import annotations

from typing import Any
from xml.sax.saxutils import escape, quoteattr

from .proveedores import POR_CLAVE

SITE_URL = "https://beg-lag.github.io/modelos-al-dia/"
TAG = "tag:beg-lag.github.io,2026:modelos-al-dia/"
MAX_ENTRADAS = 150


def atom(novedades: list[dict[str, Any]]) -> str:
    entradas = novedades[:MAX_ENTRADAS]
    actualizado = f"{entradas[0]['fecha']}T12:00:00Z" if entradas else "2026-11-23T12:00:00Z"
    lineas = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="es-MX">',
        "  <title>modelos·al·día · novedades</title>",
        "  <subtitle>Notas de versión y anuncios oficiales de OpenAI, Anthropic, Google y xAI."
        "</subtitle>",
        f'  <link rel="self" type="application/atom+xml" href="{SITE_URL}feed.xml"/>',
        f'  <link rel="alternate" type="text/html" href="{SITE_URL}"/>',
        f"  <id>{SITE_URL}feed.xml</id>",
        f"  <updated>{actualizado}</updated>",
        "  <author><name>Benjamín Esponda García</name><uri>https://pivotek.mx</uri></author>",
        '  <generator uri="https://github.com/BEG-lag/modelos-al-dia">modelos-al-dia</generator>',
    ]
    for n in entradas:
        prov = POR_CLAVE[n["proveedor"]].nombre
        origen = "notas de la API" if n["origen"] == "api" else "blog"
        lineas += [
            "  <entry>",
            f"    <title>{escape(f'{prov}: {n["titulo"]}')}</title>",
            f'    <link rel="alternate" href={quoteattr(n["url"])}/>',
            f"    <id>{TAG}{escape(n['id'])}</id>",
            f"    <updated>{n['fecha']}T12:00:00Z</updated>",
            f"    <category term={quoteattr(n['proveedor'])} label={quoteattr(prov)}/>",
            f"    <summary>{escape(f'{prov}, {origen}.')}</summary>",
            "  </entry>",
        ]
    lineas.append("</feed>")
    return "\n".join(lineas) + "\n"
