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

## Rediseño v2 (2026-11-08) — qué cambió de verdad respecto a v1

La v1 solo cambió colores y espacios. La v2 es un rediseño completo, vista
por vista, siguiendo la referencia de teléfono que mandó la dueña (TradeAI /
AUREON / TradeAI Pro: azul marino oscuro, tarjetas muy redondas, botones
pastilla, números grandes). Sistema compartido nuevo al inicio del CSS
(`--bg:#070b16`, `--card:#121a2e`, `--r1:14px`, `--r2:22px`, `--r3:28px`,
`--pill:999px`, botones pastilla de 48px, sombras suaves). Trabajo hecho por
10 agentes en paralelo (uno por vista + menú), coordinados y unidos uno por
uno con commit, pruebas y captura después de cada vista. Solo `panel.html`.

| Vista | Qué cambió en v2 |
|---|---|
| Base | Tokens redondos compartidos; botones pastilla 48px (`.btn-verde` verde con texto oscuro, `.btn-rojo` rojo, primario azul con degradado); entradas 16px de radio; "Para qué sirve" como tarjeta redonda suave; asistente sin borde violeta duro; números grandes (estado 38px, KPIs 26px, precio 30px). |
| Panel | Estado 44px; "Pondría" y "El bot" como tarjetas redondas propias; los dos marcos como tarjetas separadas con anillo verde/azul al activar; KPIs 28px con etiqueta legible; precio del gráfico 34px; leyenda en pastillas; gauge y puntos más grandes; calor con celdas de 48px; comparador y seguimiento en cajas redondas; pie como tarjeta suave. Arreglo: "Para qué sirve" ahora se llena al arrancar en Panel (antes quedaba en "—" porque `irA` no se llamaba). |
| Gráfico | Tarjeta 28px; gráfico y RSI en cajas redondas con borde; precio 34px; intervalos 44px en teléfono con el activo en azul sólido y texto blanco; capas en pastillas que envuelven; leyenda EMA con colores legibles en claro y oscuro; cinta en contenedor redondo; estadísticas con números grandes. Corregido: los números de estadísticas salían todos violetas (la utilidad `.v` pisaba a `.g`/`.r`); ahora verde/rojo correctos. |
| El bot | Pastilla de estado con punto: APAGADO gris (antes amarillo), encendido verde, peligro rojo; números de papel 28px; frenos con valor grande y legible; PARAR rojo y Reanudar en pastilla a ancho completo en teléfono; tablas en contenedores redondos 22px con scroll lateral; botones CSV a ancho completo. |
| Cuaderno | Tarjeta redonda; botones pastilla a ancho completo en teléfono ("Anotar esta lectura" azul); tabla en caja redonda de 16px (desliza de lado). |
| On-chain | KPIs en 2 columnas en teléfono (22px, 30px en computadora); tarjetas 28px; pestañas en pastillas de 48px; medidor de miedo/codicia en caja redonda con número de 28px; celdas de calor con aire. |
| Laboratorio | Tarjetas 28px; títulos blancos 15px; selectores de 48px; deslizadores con pista redonda y pulgar azul de 24px con anillo blanco; valor en pastilla ("24 velas"); "Comparar las 5 estrategias" azul pastilla a ancho completo; métricas 20px; curva en caja redonda 22px; simulador a ancho completo en teléfono. |
| Ajustes | Títulos blancos 16px con punto de color; nota inicial en banner suave redondo; filas con aire (etiqueta 13px en negrita + punto, texto a la izquierda). |
| Noticias | Cabecera 28px y título 28px; filtros en pastillas que envuelven (Todas activa en cian); "Actualizar ahora" a ancho completo en teléfono; tarjetas de noticia con más aire (titular 15,5px); movimiento en pastilla verde/roja con fondo suave; pie como tarjeta redonda. |
| Cartera | Saldo 32px en tarjeta 28px; pastilla PLATA FALSA amarilla; "Colocar orden" verde pastilla a ancho completo; "Cerrar" rojo pastilla; tablas en cajas redondas 22px; buscador 48px y 16px; resultado del riesgo grande (19px); curva en caja redonda. |
| Menú | **En teléfono solo 5 botones abajo: Panel, Gráfico, Bot, Cartera, Más** (70×56px a 360px, con nombre). Las otras 5 vistas (Cuaderno, On-chain, Lab, Noticias, Ajustes) van en una hoja "Más" que se abre desde abajo (radio superior 28px, icono + nombre + frase corta, botón Cerrar azul pastilla). En computadora sigue el menú lateral completo con las 9 vistas. Teclas 1–9 siguen funcionando. |
| Tema claro | Verificado en Panel, Bot y Cartera a 360px: todo legible. Corregido: la tarjeta del asistente quedaba azul oscura en claro (degradado fijo `#1a2340`); ahora degradado claro. |

## Verificación v2 con navegador (Firefox headless, 2026-11-08)

- Pruebas después de cada vista y al final: `TODO OK` con **177**
  comprobaciones. CSS con llaves balanceadas (2 bloques `<style>`),
  sintaxis JS verificada con `node --check` después de cada unión.
- Ancho de página medido en las 10 partes: **1440px → 1440, 390px → 390,
  360px → 360**. Sin desborde horizontal de página en ninguna vista, ni en
  modo claro ni en oscuro. Capturas en `~/workspace/preview-helios-v2/`
  (`panel-360.png`, `grafico-360.png`, `bot-360.png`, `cartera-360.png`,
  `cuaderno-360.png`, `onchain-360.png`, `lab-360.png`, `ajustes-360.png`,
  `noticias-360.png`, `menu-360.png`, `menu-360-mas.png`, más las de 390px,
  las claras y las de 1440px; y un `panel-<vista>.html` por cada parte).
- Menú inferior medido a 360px: 5 botones de 70×56px, todos visibles, sin
  corte; la hoja Más se abre y se cierra (botón, fondo y tecla Escape).
- "Para qué sirve" en Panel: verificado llamando a `irA('panel')` a mano
  (rellena "Es la pantalla de siempre…"). En esta máquina la carga inicial
  sigue mostrando "—" porque el CDN bloqueado detiene el script en
  `montar()` antes de llegar al arranque; en la PC de la dueña, con
  internet, el script corre entero y se llena.
- Límite del entorno: en esta máquina la librería de gráficos por CDN
  (`LightweightCharts`) y las APIs de Binance/CoinGecko no cargaron, así que
  las capturas muestran el estado "Cargando…" y no velas ni precios reales.
  No es un error del panel: con internet en la PC del dueño los datos cargan
  como antes. Los gráficos con datos reales, las tablas con datos reales y
  los números grandes con valores reales (KPIs, saldo, P/L) se verificaron
  con datos de prueba inyectados en la página viva, no con el servidor real.

## Lo que NO se pudo probar en teléfono real

- No hay teléfono físico en esta máquina. La verificación en 360px y 390px se
  hizo con Firefox headless (Playwright) y con inspección del CSS, no con
  toque real ni en Chrome de un teléfono.
- No se recorrieron con toque real el buscador, los filtros, el comparador y
  el simulador: el código es el mismo que en computadora y los controles
  quedaron a 44px, pero el toque físico no se probó.
- Los colores de las celdas de On-chain (calor por cadena/protocolo) los pone
  el programa con colores en línea; no se cambiaron para no tocar lógica.
