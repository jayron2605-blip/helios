# Auditoría de interfaz — Helios (rama `ui-mejora-interfaz`)

Fecha: **2026-11-08**. Solo interfaz (`panel.html`). No se tocó `bot/`, ni
`servidor.py`, ni ningún número, cálculo o decisión. Pruebas después de cada
cambio: `TODO OK` con **177** comprobaciones.

## Lo que ya estaba bien (no se inventó un problema donde no lo había)

- Sistema de tokens CSS al inicio (`--bg`, `--card`, `--up #0ecb81`, `--dn #f6465d`).
- Tema claro en `body[data-tema="claro"]` que cambia fondos, texto y verdes/rojos.
- 9 vistas, barra "Para qué sirve" en todas, base responsive (viewport, menú
  abajo en teléfono, tarjetas en una columna a menos de 900px, tablas que
  colapsan a menos de 1320px y 1100px).
- Cartera ya tenía botones de 44px y tablas contenidas (verificado 2026-11-08).
- Noticias ya tenían tarjeta por noticia, sentimiento con palabra (BUENA / MALA /
  NEUTRA) y movimiento de precio con palabra. Miedo y codicia ya mostraba el
  número y la palabra (por ejemplo, "Miedo extremo").

## Lo que estaba mal y se arregló

| # | Problema | Arreglo |
|---|----------|---------|
| 1 | No había botón principal: todos los botones eran iguales, grises. | `.btn-primario` azul (`#2f7fff`) en Colocar orden, Calcular y Actualizar ahora. Secundario con borde. Peligro rojo solo para parar el bot. |
| 2 | Botones de ~27px de alto fuera de Cartera: chicos para el dedo. | Base 40px en computadora, 44px en teléfono; también `.tf`, `.seg`, `.tabs` y buscador (36px). |
| 3 | Menú de abajo solo con iconos, sin texto; a menos de 600px se movía de lado. | Etiqueta corta bajo cada icono (Panel, Gráfico, Bot, Cuaderno, On-chain, Lab, Cartera, Noticias, Ajustes); 9 botones repartidos, vista activa con color y marca. |
| 4 | Tablas anchas se apretaban en teléfono (Cuaderno 11 columnas, historial 9). | `min-width` en tablas dentro de `.scrolly`/`.vlist` y en comparador, laboratorio y simulador: se mueven de lado con el dedo sin romper la vista. |
| 5 | Modo claro a medias: bordes `#131b24` duros, fondo de selección `#0d2430` oscuro, línea mediana blanca invisible sobre fondo blanco. | Bordes y selección con variables; mediana gris `#8a97a8`, visible en los dos temas. |
| 6 | Líneas cian `#00d1ff` (EMA 50, RSI, laboratorio, dispersión) casi invisibles sobre fondo blanco. | Cian de gráficos `#0a87a8`, se lee en oscuro y en claro. La leyenda EMA 50 usa el mismo color. |
| 7 | Rosa `#ff2d78` en la marca: un séptimo color fuera del sistema. | Marca en azul; quedan 6 colores principales. |
| 8 | La etiqueta BRIO era verde, igual que "noticia buena": se confundía con el sentimiento. | Pastilla violeta propia para Brio. El violeta queda solo para el asistente y Brio. |
| 9 | Estado del bot: solo color y palabra, sin punto. | Punto de color junto a la palabra en `#botModo` (gris apagado, verde encendido, rojo peligro, según la clase que ya ponía el programa). |
| 10 | Miedo y codicia con solo 3 colores (rojo, amarillo, verde). | Escala de 5: rojo extremo, naranja miedo, amarillo neutro, verde claro codicia, verde fuerte codicia extrema. |
| 11 | Altura del gráfico grande fija en línea (`440px`): no se podía bajar en teléfono. | Altura en CSS: 440px en computadora, 320px en teléfono. |
| 12 | Los dos botones grandes de "Cómo leemos / Cómo lo venden" se apretaban en teléfono. | En columna en teléfono, uno debajo del otro. |
| 13 | Textos de formularios a 12–13px en teléfono: el teléfono hace zoom al tocarlos. | En teléfono, entradas y listas a 16px y 44px de alto. |
| 14 | Estrella de favoritos de 26px: difícil de tocar. | Zona de toque de 36px mínimo. |
| 15 | El asistente no se distinguía de las demás tarjetas. | Borde violeta a la izquierda y título en violeta. |
| 16 | Barra "Para qué sirve" con texto cian chico, poca jerarquía. | Etiqueta azul en forma de pastilla, texto a 13px, fondo de tarjeta. |
| 17 | Menú de abajo a 360px: el botón Ajustes quedaba fuera de la pantalla (el menú se movía de lado) y "Noticias" se cortaba. Causa: cada botón medía 44px fijos y la rejilla no podía achicarse. | Botones repartidos que se achican (38px a 360px, 41px a 390px) y rejilla con `minmax(0,1fr)`: las 9 vistas entran sin mover el menú. |
| 18 | El `$1.000` del asistente se cortaba a 360px ("$1.0…"). Causa: la rejilla del asistente no podía achicarse por el deslizador. | Rejillas del asistente, de las tarjetas y del laboratorio con `minmax(0,1fr)` y `min-width:0`: el capital se ve entero a 360px y a 390px. |

## Sistema de color final (6 principales)

Verde ganancia `#0ecb81`, rojo pérdida `#f6465d`, amarillo avisos `#f0b90b`,
azul botones `#2f7fff`, violeta especial `#8b5cf6`, cian acento `#00d1ff`.
Naranja `#f5820b` solo en la escala de miedo/codicia. Documentado al inicio
del CSS de `panel.html`.

## Verificación con navegador (Firefox headless, 2026-11-08)

- Servidor local: HTTP 200, panel nuevo servido (200.948 bytes).
- Ancho de página medido en las 9 vistas: **1440px → 1440, 390px → 390,
  360px → 360**. Sin desborde horizontal de página en ninguna vista ni en
  modo claro.
- Menú inferior medido: 9 botones de 38px a 360px y de 41px a 390px, todos
  visibles; capital del asistente `$1.000` completo a 360px (borde derecho
  329px) y a 390px (359px).
- Contraste calculado (WCAG): texto/fondo oscuro 16,75:1, texto/fondo claro
  15,93:1, verde claro 5,38:1, botón azul con texto blanco 4,77:1 en oscuro
  y 6,65:1 en claro. CSS con llaves balanceadas, HTML sin errores de
  etiquetas, sintaxis JS verificada con `node --check`.
- Límite del entorno: en esta máquina la librería de gráficos por CDN
  (`LightweightCharts`) y las APIs de Binance/CoinGecko no cargaron, así que
  las capturas muestran el estado "Cargando…" y no velas ni precios reales.
  No es un error del panel: con internet en la PC del dueño los datos cargan
  como antes. Los gráficos con datos reales no se pudieron ver acá.

## Lo que NO se pudo probar en teléfono real

- No hay teléfono físico en esta máquina. La verificación en 360px y 390px se
  hizo con Firefox headless (Playwright) y con inspección del CSS, no con
  toque real ni en Chrome de un teléfono.
- No se recorrieron con toque real el buscador, los filtros, el comparador y
  el simulador: el código es el mismo que en computadora y los controles
  quedaron a 44px, pero el toque físico no se probó.
- Los colores de las celdas de On-chain (calor por cadena/protocolo) los pone
  el programa con colores en línea; no se cambiaron para no tocar lógica.
