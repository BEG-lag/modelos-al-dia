"""Los cuatro proveedores que sigue el proyecto y cómo se llaman en cada fuente."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Proveedor:
    clave: str
    nombre: str
    producto: str  # la app de consumo
    modelsdev: str  # clave en https://models.dev/api.json
    openrouter: str  # prefijo en https://openrouter.ai/api/v1/models
    color: str  # acento en la página


PROVEEDORES: tuple[Proveedor, ...] = (
    Proveedor("openai", "OpenAI", "ChatGPT", "openai", "openai", "#10a37f"),
    Proveedor("anthropic", "Anthropic", "Claude", "anthropic", "anthropic", "#d97757"),
    Proveedor("google", "Google", "Gemini", "google", "google", "#4285f4"),
    Proveedor("xai", "xAI", "Grok", "xai", "x-ai", "#a3a3a3"),
)

POR_CLAVE = {p.clave: p for p in PROVEEDORES}
CLAVES = tuple(p.clave for p in PROVEEDORES)
