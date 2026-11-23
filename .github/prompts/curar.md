# Curaduría semanal de las fichas

Eres quien mantiene al día las fichas curadas de `data/curado/`: `openai.yaml`, `anthropic.yaml`,
`google.yaml`, `xai.yaml` y `agentes-codigo.yaml`. El formato está en `data/curado/_ejemplo.yaml` y lo
valida `uv run --frozen modelos-al-dia check`.

## Qué revisar

1. Lee `data/novedades.json` (entradas de los últimos 10 días) y `data/cambios.json` (cambios del
   catálogo de los últimos 10 días). Son las pistas de qué pudo cambiar: modelos nuevos, precios,
   retiros, planes, capacidades de las apps y agentes de código.
2. Lee la sección `pendientes` de cada ficha: intenta resolver las dudas abiertas.
3. Verifica cada cambio en la fuente oficial (sitio, documentación, página de precios o notas de
   versión del proveedor) con WebSearch y WebFetch. Si solo hay fuentes secundarias, márcalo con
   `etiqueta: SUPUESTO`.

## Cómo editar

- Cambia solo lo que confirmaste. No reescribas lo que sigue igual.
- Cada dato nuevo o cambiado lleva `fuente` (URL). Actualiza `verificado` de la ficha a la fecha de hoy
  solo si revisaste esa ficha completa.
- Usa las etiquetas: `ESTIMADO` (cifra aproximada), `SUPUESTO` (premisa no confirmada) y `BRECHA`
  (dato que falta). Nunca inventes un dato sin marcarlo.
- Un modelo que el proveedor retira pasa a `estado: retirado` (no lo borres). Un modelo nuevo se agrega
  con la categoría que le corresponda.
- Agrega a `hitos` los lanzamientos de la semana, con fecha y fuente.
- Español mexicano. Prohibido el guion largo (U+2014): usa comas, dos puntos o paréntesis.
- Entrecomilla las URLs dentro de mapas en línea (`{estado: si, detalle: "...", fuente: "https://..."}`).

## Al terminar

1. Corre `uv run --frozen modelos-al-dia check` hasta que diga `OK`.
2. Escribe `.github/prompts/ultimo-resumen.md` con el cuerpo del pull request: una lista breve de qué
   cambió en cada ficha y por qué, con la liga a la fuente, y una sección "Por revisar" con lo que
   quedó como SUPUESTO o BRECHA. Si no hubo cambios, escribe "Sin cambios esta semana." y no edites
   ninguna ficha.
3. No hagas commit ni push: el workflow abre el pull request.
