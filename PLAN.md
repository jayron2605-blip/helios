# PLAN.md — plan de trabajo de Helios (noviembre 2026)

Escrito por el agente después de leer todo el código y correr las pruebas del motor
(`py -3.12 bot/pruebas.py` → **TODO OK**). Todo lo que sigue está verificado
leyendo el código, no es creencia.

**Re-verificado el 2026-11-07 a las 15:30 por el agente nuevo**, leyendo el repo completo
y corriendo las pruebas en otra máquina (Windows 11, Python 3.14, scikit-learn 1.9.1).
Resultado: **TODO OK, 90 pruebas** (49 del motor y de las noticias RSS + 32 de la puerta de
Brio + 9 del bloque VA de ventaja; la prueba V corre en 3 tamaños).
Los números "24" y "39" que aparecían en el README estaban desactualizados.
Lo que este agente corrigió o confirmó está marcado en la sección 8.

**Prompt FINAL recibido el 2026-11-07.** El dueño mandó un prompt nuevo que cambia el objetivo:
ya no agregar funciones sin parar, sino **terminar lo que falta, arreglar lo que está a medias y
probar todo una por una**. Ese prompt define las partes **A a H** (más amplias que las A–D de la
tanda anterior). Se arrancó por sus pasos 1 y 2: leída la carpeta completa en `Y:` y corrido
`python bot/pruebas.py` → **TODO OK, 90 pruebas** (90 líneas OK contadas en la salida real,
Python 3.14, scikit-learn 1.9.1). El plan final A–H está en la **sección 9**, la lista para probar
una por una en la **sección 10** y las decisiones del dueño en la **sección 11**. Las secciones
1 a 8 quedan como registro histórico verificado de la tanda anterior; donde el prompt final
corrige o amplía algo, se anota en la sección 9.

## 1. Qué encontré al leer el repositorio (por escrito, bug por bug)

1. **El bot no opera ni en papel en vivo.** `bot/cerebro.py` línea 80: `real = False` fijo,
   y nunca llama a `exchange.comprar_mercado()` ni `vender_mercado()`. El circuito `decide()`
   solo escribe probabilidades en `estado_cerebro.json`. → Se arregla en el punto 3 del plan.
2. **Comprar-y-sostener está bien medido en promedio pero usa el máximo.** `bot/modelo.py`
   línea 109: `c1 = barras[-1][2]` es el *high* de la última vela (índice 2), no el cierre
   (índice 4). Eso infla el retorno de "dejarlo quieto" en la última vela. → Corregido.
3. **El freno de tamaño por operación nunca salta.** `bot/exchange.py`: `revisar_frenos(simbolo, 0)`
   en `comprar_mercado()` y `vender_mercado()`: monto 0 jamás pasa `maximo_por_operacion_usd`. → Corregido.
4. **La pérdida del día nunca se registra.** El contador diario se crea y se lee, pero nada
   suma a `perdida_usd` cuando una operación cierra mal. → **A medias, corregido el 2026-11-07:**
   `registrar_cierre()` existe y acumula bien (`exchange.py:192-205`), y las pruebas X, X2 y X3
   pasan. Pero **solo lo llaman las pruebas**: `Broker.cerrar()` (`ejecutor.py:94-113`) no lo
   llama, ni `modelo.py`, ni `cerebro.py`. El docstring de `exchange.py:10` afirma que se
   actualiza "por cada operación cerrada" y hoy eso no ocurre fuera de los tests.
   Cablearlo es trabajo real pendiente de la parte A.3, no un "ya hecho".
5. **`SOLO_PRUEBA = True` se mantiene.** Es un candado a propósito: con este candado es
   imposible mandar una orden real aunque alguien cargue claves y apague el simulacro.
   No se toca durante todo este trabajo. Se quitará solo si Jairon lo aprueba por escrito
   después de ver una prueba en papel ganadora por lo menos 30 días.
6. **Alcances (no son bugs, son límites reales):** el asistente analiza una moneda
   (BTC por defecto), el bot mira 6, y el laboratorio solo funciona con las que tienen
   historial bajado (las mismas 6). Todos los endpoints del panel ya son `/api/...`
   y el panel solo muestra: apto para la futura app móvil.

## 2. El orden del trabajo

**Corrección importante:** la versión anterior de este plan marcaba los pasos 4 a 8 como
"hecho" cuando no lo estaban. El README no se había tocado, `cerebro.py` no registraba
decisiones y la tabla de la parte C prometía seis mejoras que no existían en el código.
Se corrigió leyendo el repo, no recordando. Estado real, verificado archivo por archivo:

| Paso | Qué es | Estado real |
|---|---|---|
| 1 | Leer todo + correr pruebas | hecho |
| 2 | Este plan | hecho |
| 3 | Corregir los 3 errores (comprar-y-sostener, monto del freno, pérdida diaria) | hecho y verificado |
| 4 | Noticias en vivo: módulo + `/api/noticias` + vista | **hecho ahora** (estaba a medias y sin guardar) |
| 5 | Buscar ventaja real con walk-forward | **hecho ahora**: 9 estrategias, ninguna aprueba (`bot/ventaja.py`) |
| 6 | Registro de decisiones en papel con su resultado | **hecho ahora** (`bot/decisiones.py`) |
| 7 | Mejoras de la parte C | **parcial**, ver tabla corregida abajo |
| 8 | README con los números reales | **hecho ahora** |

Después de cada cambio corro `py -3.12 bot/pruebas.py`. Si no sale TODO OK, no sigue nada.
Hoy: **90 pruebas, TODO OK** (contadas en la salida real, no en el documento).

### La parte C, en limpio (lo que está y lo que no)

| # | Idea | Estado real |
|---|---|---|
| 1 | Calculadora de riesgo por moneda | **hecha ahora**: sigue a la moneda que estás mirando, no solo a Bitcoin |
| 2 | Alertas que sí sirven | hechas (filtro de importancia + freno de 90 min) |
| 3 | Comparador de monedas | **hecho ahora** (panel, hasta 3 monedas lado a lado, commit 23542b1) |
| 4 | Historial de miedo y codicia 90 días | **hecho ahora** (vista On-chain, con datos reales) |
| 5 | Simulador "qué hubiera pasado si" | **hecho ahora** (laboratorio, comprar-y-sostener vs DCA vs nada, commit 23542b1) |
| 6 | Lista de seguimiento personal (favoritos) | **hecho ahora** (★ en la lista + filtro, en localStorage, commit 23542b1) |
| 7 | Explicación en una frase por pantalla | **hecho ahora**: barra "Para qué sirve" en las 8 vistas |
| 8 | Modo claro/oscuro y celular | estaba; se le sumó la barra nueva en responsive |
| 9 | Fuente y antigüedad de cada dato | estaba en noticias; **no está en todas las tarjetas** |
| 10 | Exportar a Excel | **hecho ahora** para decisiones; el cuaderno ya se podía bajar |

## 3. Las ideas para buscar ventaja (parte A), en este orden

1. **Tamaño por agitación**: predecir la agitación (que sí es predecible según `que_se_puede.py`)
   y escalar el tamaño de la operación según el riesgo real, en vez de usar un riesgo fijo del 2 %.
2. **Filtro de estado del mercado**: no operar cuando la agitación de la vela está en el
   extremo (atr_ratio muy alto o muy bajo) — los extremos son donde peor le fue al modelo.
3. **Varias escalas de tiempo**: features de retornos en 4h/día precalculados desde velas de 1h.
4. **Modelo alternativo**: RandomForest y una regresión sobre la magnitud (no la dirección).
5. **Tramo de probabilidad asimétrico**: entrar solo con probabilidad de banda extrema
   (> 0.6 / < 0.4), donde el modelo está más seguro que el 52.8 % de adivinar siempre lo mismo.

Regla de decisión: una idea solo sobrevive si en la prueba walk-forward (33 pliegues, misma
comisión de 0,1 % por lado, mismo deslizamiento) **le gana a comprar-y-sostener en la mayoría
de los 6 mercados** (mínimo 4 de 6). Con menos: se apaga, y queda escrito el por qué.

### Resultado real de esa búsqueda (noviembre 2026)

Se corrieron las 5 ideas más dos variantes de costo, contra el mismo tramo. **Ninguna
aprobó: 0 de 6 mercados en los nueve casos.** Los números completos están en
`bot/resultados/ventaja.json` y en el README.

Dos cosas que salieron del camino y valen más que la tabla:

1. **S4 estaba mal diseñada, no mal el pronóstico.** Con tope de exposición 1,5 (apalancarse)
   y rebalanceo diario, se pagaba **20,5 % del capital solo en comisiones** y la volatilidad
   del apalancamiento comía el resto. Al quitar el apalancamiento y rebalancear por semana,
   la misma idea pasó de −38,8 % a −4,1 %. La lección: antes de culpar al modelo, mirar el
   costo de la ejecución.
2. **Predecir la agitación funciona solo si se pide como cambio, no como nivel.** Pronosticar
   el nivel de agitación salía 15,2 % **peor** que el tonto "supone que sigue igual".
   Pronosticar la razón de cambio sale **3,2 % mejor**. Con esa versión, la caída máxima baja
   de 69,9 % a 58,6 % **en los 6 mercados**. Es protección, no ventaja. Ojo: el "+296 % y costó
   300 puntos" que decía acá antes salía de una vara inflada; al medir todas las estrategias en
   el mismo tramo, la vara real es −0,8 % y la protección de S8 cuesta apenas unos puntos
   (−4,1 % contra −0,8 %). Ver la corrección 3 de la sección 8.

También se corrigió un error de este plan: afirmaba que "sigue igual" era un baseline roto a
favor. Al programarlo bien, el baseline es fuerte y el modelo de nivel perdía contra él.

## 4. Fuentes de noticias que voy a usar (todas gratuitas)

| Fuente | Cómo | Clave |
|---|---|---|
| CoinDesk RSS | `https://www.coindesk.com/arc/outboundfeeds/rss/` (XML público) | no |
| Cointelegraph RSS | `https://cointelegraph.com/rss` (XML público) | no |
| Decrypt RSS | `https://decrypt.co/feed` (XML público) | no |
| CryptoPanic | API pública; con clave gratuita va mejor | **opcional**: `bot/noticias.json` (de `noticias.EJEMPLO.json`) |

- Sin clave: funcionan los RSS de arriba. Con clave: además CryptoPanic (con urgencias y votos).
- Caché de 10 minutos como máximo en el servidor (`/api/noticias`), y archivo
  `bot/noticias_cache.json` con las últimas, para que si se corta internet el panel
  diga "última actualización hace X minutos" y siga mostrando lo guardado.
- Cada noticia: título, fuente, hora real, moneda afectada si se sabe, resumen de una línea
  en español, clasificación buena/mala/neutra con motivo, enlace a la fuente y el movimiento
  real del precio en la hora siguiente (para no-confundir: lo marca cuando ya se puede medir).
- Nada se inventa: si una fuente falla, se dice que falló. Si no se puede clasificar seguro,
  queda **sin clasificar**.

## 5. Las 10 ideas nuevas propuestas (parte C) y cuáles implemento

**Corregida el 2026-11-07 por el agente nuevo.** Esta tabla decía "sí" en comparador,
favoritos y fuente/edad, contradiciendo la tabla honesta de la sección 2. Se verificó
archivo por archivo en `panel.html` (2.282 líneas) y `servidor.py`: **la sección 2 tenía
razón y esta tabla no.** Queda así, con la evidencia:

| # | Idea | Por qué sirve | Estado real verificado |
|---|---|---|---|
| 1 | Calculadora de riesgo en cada moneda | antes de comprar, cuánto perderías en pesos y en % | **sí** — `asistente.analizar(simbolo, capital)`, sigue a la moneda mirada |
| 2 | Alertas que sí sirven | solo cambios de estado, señales, frenos y resumen diario por Telegram | **sí** — `bot/avisos.py`, freno de 90 min |
| 3 | Comparador de monedas | ver 2-3 monedas juntas: quién sube, quién baja, quién está más agitado | **NO existe** — lo único parecido es `labCompararTodas()` (panel.html:2209), que compara 5 *estrategias* sobre un solo mercado, no monedas |
| 4 | Historial de miedo y codicia 90 días | una gráfica de 90 días pone en contexto el número de hoy | **sí** — `/api/miedo_hist` con `limit=90` (servidor.py:379) |
| 5 | Simulador "qué hubiera pasado si" | poner plata en una fecha y ver bot vs quieto | **NO existe** — no hay ningún `input type=date` en el panel; el Laboratorio usa todo el historial desde 2023 sin fecha elegible |
| 6 | Lista de seguimiento personal | marcar monedas favoritas y que queden arriba | **NO existe** — "Seguimiento" (panel.html:501) es solo el título de la tabla de mercados; `localStorage` guarda únicamente tema y última vista |
| 7 | Explicación en una frase por pantalla | cada vista se entiende sin preguntar | **sí** — barra `#paraque` con las 8 entradas de `PARA_QUE` (panel.html:873-882) |
| 8 | Modo claro/oscuro bien hecho | ya funcionaba; se completa en la vista nueva y gráficos | **sí, con un detalle** — `aplicarTema()` (panel.html:1718) re-tematiza `[grafico, big, rsiG]` pero deja fuera `lab.grafico` |
| 9 | Fuente y edad de cada dato | "Binance, hace 2 minutos": si un dato es viejo, se ve viejo | **parcial** — solo Noticias tiene `haceTxt()` por tarjeta; el resto muestra un chip global de caché y las fuentes sin antigüedad |
| 10 | Exportar la prueba y las decisiones a CSV | abrir en Excel el cuaderno, scorecards y decisiones del bot | **parcial** — cuaderno y decisiones sí (CSV); el botón de decisiones dice "Excel" pero baja CSV; Laboratorio y scorecard **no** se exportan |

**Cerrado el 2026-11-07 (commit 23542b1):** 3 (comparador), 5 (simulador) y 6 (favoritos) ya
están implementados y verificados en navegador; el detalle de 8 (`aplicarTema` dejaba fuera
`lab.grafico`) también quedó arreglado. Quedan pendientes 9 (fuente/edad en todas las tarjetas)
y 10 (exportar laboratorio y scorecard), que no eran obligatorios en esta tanda.

## 6. Lo que necesito de Jairon (decisiones, no trabajos)

1. **Telegram**: si quiere avisos al teléfono, crear el bot gratis con @BotFather y pegar
   token + chat en `bot/telegram.json` (el molde está en `telegram.EJEMPLO.json`).
2. **CryptoPanic** (opcional): crear la clave gratuita y pegarla en `bot/noticias.json`
   (molde en `noticias.EJEMPLO.json`). Sin clave, las noticias igual funcionan con RSS.
3. **Permisos**: no se necesita ninguna clave de exchange para nada de este trabajo.
   Dinero real: jamás sin su permiso escrito después de 30 días de prueba en papel ganadora.
4. **App móvil**: la lógica ya vive en `/api/...`; la app para App Store/Play Store
   (Flutter, como Mi Óptica Pro) puede usar los mismos endpoints cuando lo decidamos.

## 7. Los resultados honestos que quedan escritos

Quedan en el README y no se esconden: el bot pierde contra dejarlo quieto (−98,8 % vs
+71,2 % con los 6 mercados y $1.000 en cada uno). Las nuevas reglas de este plan también se
publican gane o pierda. El único detectable mejorable hoy es la **agitación**, y eso se usa
para dimensionar el riesgo, no para prometer ganancias.

## 8. Plan del agente nuevo (2026-11-07)

No reescribo lo de arriba: lo verifiqué y corregí donde mentía. Esto es lo que voy a hacer
y en qué orden, siguiendo el prompt unido.

### 8.1 Lo que verifiqué antes de tocar nada

- **Pruebas: 81, TODO OK.** No 39. Corridas con Python 3.14 y scikit-learn 1.9.1.
  Las 32 nuevas (BR1–BR17b) cubren la puerta de Brio, incluido un POST real contra un
  servidor local efímero: 401 sin clave, 401 con clave mala, 200 con la buena, 400 con
  lote inválido, 413 con cuerpo gigante, y el cuaderno y el 404 de siempre intactos.
- **Los tres "YA ARREGLADO":** dos confirmados (`comprar_y_sostener` usa `barras[-1][4]`;
  `comprar_mercado`/`vender_mercado` pasan el monto real a `revisar_frenos`). El tercero
  está **a medias**: `registrar_cierre()` existe pero nadie lo llama fuera de los tests.
- **`SOLO_PRUEBA = True` sigue puesto** y tiene cuatro capas independientes. No se toca.
- **Comparador, simulador y favoritos: no existen.** La tabla de la sección 2 era la honesta.
- **`cerebro.py` nunca opera**, ni en papel: importa `Broker` y `exchange` y no los usa.
  Solo escribe JSON y CSV. La parte A.3 sigue siendo trabajo real.

### 8.2 Dos obstáculos que necesito resolver o que el dueño decida

1. **El servidor escucha solo en `127.0.0.1`** (`servidor.py:419`). Brio está en internet y
   no puede alcanzar esta PC. Para que `POST /api/noticias/recibir` sirva de verdad hace
   falta una URL pública. Opciones: un túnel temporal (hay `pyngrok` instalado en esta
   máquina) o publicar el servidor cuando se haga la app. **No expongo nada a internet sin
   que el dueño lo apruebe.** Mientras tanto la puerta se construye y se prueba en local.
2. **Los `.bat` piden `py -3.12` y esta máquina tiene Python 3.14.** Los modelos
   `resultados/*.joblib` se entrenaron con otra versión de scikit-learn: pueden no cargar
   o dar aviso. Si hace falta reentrenar, se hace con `Entrenar.bat` y se vuelve a publicar
   el scorecard. No se inventa un resultado.

### 8.3 Orden de trabajo

| Paso | Qué | Estado |
|---|---|---|
| 1 | Leer todo + correr pruebas | **hecho** (90, TODO OK) |
| 2 | Este plan y corregir contradicciones | **hecho** |
| 3 | Verificar los "YA ARREGLADO" | **hecho** (uno resultó a medias) |
| 4 | Instalar `ta` + `ccxt` y Grid MIT | **hecho**: `ta`+`ccxt` instalados; Grid MIT reescrito como S9 con atribución |
| 5 | `POST /api/noticias/recibir` + unir B1 y B2 | **hecho y probado** (ver 8.4) |
| 6 | Ventaja NUEVA, distinta a S1–S8 | **hecho**: S9–S12 corridas; S11 aprueba (ver 8.5) |
| 7 | Comparador, simulador y favoritos | **hecho y verificado en navegador** (commit 23542b1) |
| 8 | README con números reales + resumen | **hecho** |

### 8.4 Cómo quedaron unidas B1 (RSS) y B2 (Brio) — hecho y probado

El problema real: `noticias.traer()` **reconstruye la lista entera** desde RSS en cada
refresco. Si las noticias de Brio se inyectaran solo en memoria o en el caché, se borrarían
solas a los 10 minutos.

Solución aplicada: Brio se guarda en su propio archivo persistente (`bot/noticias_brio.json`,
gitignoreado, escritura atómica). En cada `traer()` esas noticias se vuelven a leer y se mezclan
con las crudas del RSS **antes** de `procesar()`, así pasan por el mismo filtro de edad, spam y
duplicados, y reciben la misma medición de precio de la hora siguiente. Brio va primero en la
lista: si el RSS trae la misma noticia, gana la que ya vino leída y traducida. `procesar()`
respeta el título en español, el resumen y el sentimiento de Brio en vez de volver a deducirlos
del título en inglés, y no le aplica el filtro de vocabulario en inglés de los RSS. Dedup por
URL además del parecido de título que ya existe. De paso se corrigió que la medición de precio
ya hecha se perdiera en cada refresco: ahora se conserva entre reconstrucciones.

**La puerta:** `POST /api/noticias/recibir`, con `Authorization: Bearer <clave>`. Sin clave,
con clave equivocada o sin clave configurada responde **401 y no guarda nada**. Cuerpo máximo
512 KB (413), lote máximo 50 noticias, enlaces solo http(s) (un `javascript:` se rechaza),
sentimiento solo buena/mala/neutra, importancia solo alta/media, hora obligatoria (sin hora no
se inventa fecha). Responde `{"ok": true, "recibidas": N, "nuevas": M}`.

**URL que el dueño le tiene que dar a Brio:**

- En esta PC, hoy: `http://127.0.0.1:8765/api/noticias/recibir`
- Para Brio de verdad (está en internet): **todavía no existe una URL pública.** El servidor
  escucha solo en `127.0.0.1` a propósito. Hace falta que el dueño apruebe un túnel o publicar
  el servidor (ver 8.2 y 8.7). Hasta entonces la puerta está construida y probada en local.

**Probado de verdad, no de palabra:** se corrió el `curl` exacto del prompt contra el servidor
local → `200 {"ok": true, "recibidas": 1, "nuevas": 1}`; sin clave y con clave mala → `401`;
la noticia apareció arriba de `GET /api/noticias` mezclada con 52 de los RSS (95 crudas → 53);
se vio en el navegador con su etiqueta BRIO, su título en español y su moneda; un título con
`<img onerror=...>` se pintó como texto plano sin ejecutar nada; después **se borró la prueba**
y la lista quedó limpia. El botón "Actualizar ahora" del panel dice en su tooltip y en el pie
de la vista que **no llama a Brio**: sólo lee lo guardado o busca por RSS.

La clave de Brio va en `bot/noticias.json` (ya gitignoreado), campo `brio_token`, con su
molde en `noticias.EJEMPLO.json`. El agente ya creó una clave aleatoria ahí; no se escribió en
el código, ni en el repo, ni en el chat. Sin clave configurada la puerta responde 401 y no
guarda nada; el RSS sigue funcionando igual.

### 8.5 Ideas NUEVAS para buscar ventaja (no repiten S1–S8)

S1–S8 ya cubrieron: modelo de dirección, filtro de estado, bandas extremas, y dimensionar
por agitación (apalancado o no, diario o semanal, con o sin sesgo de tendencia). Ninguna
aprobó. Estas son mecanismos **distintos**, no variaciones de lo mismo:

1. **S9 — Grid por niveles.** Comprar abajo y vender arriba en una rejilla de precios, sin
   predecir dirección. Es el que pide la parte D y no se parece a nada de S1–S8.
2. **S10 — Rotación entre las 6 monedas.** En vez de decidir cada moneda por separado,
   ordenar las 6 por fuerza reciente y tener solo las 2 mejores. Usa la información
   cross-seccional que `datos.py` ya calcula y ninguna estrategia aprovechó.
3. **S11 — Confirmación en varias escalas.** Operar solo cuando 1h, 4h y día apuntan al
   mismo lado. Estaba propuesta en la sección 3 pero nunca se corrió.
4. **S12 — DCA con tamaño según agitación.** Compras periódicas, más grandes cuando la
   agitación prevista baja. Mecanismo de entrada distinto a todo lo anterior.
5. **S13 — Sentimiento de noticias.** Depende de que Brio mande historial; hasta que no
   haya suficientes noticias con precio medido, no se puede probar honestamente. Queda
   apuntada, no se simula con datos inventados.

Misma vara para todas: walk-forward, comisión 0,1 % por lado, mismo deslizamiento, y
**solo aprueba si le gana a comprar-y-sostener en más de la mitad de los mercados y no queda
en rojo**. Si pierde, se escribe igual en el README y en `ventaja.py`.

**Resultado corrido de verdad (commit aeedd48):** S9 grid −29,3 % (2/6), S10 rotación −19,7 %
(2/6), S11 confirmación día+semana+mes **+69,2 % (4/6, aprueba)**, S12 DCA −1,4 % (4/6 pero en
rojo, no aprueba). S11 baja la caída máxima de 69,9 % a 27,6 % en los 6; mediana por mercado
+31,6 %, mejor XRP +225,5 %, peor BNB +3,3 %. Es una regla de tendencia, no IA. El bot sigue en
papel y `SOLO_PRUEBA=True`: falta la prueba en papel en vivo ~30 días y el visto bueno del dueño.

**Corrección 3 (importante):** antes S0 (la vara) usaba toda la historia y las estrategias solo
el tramo de prueba, así que la vara salía +296 % y todo parecía perder contra ella. Ahora todas
corren en el mismo tramo (desde 2024-08) y la vara real es −0,8 %. Sin esto la comparación era
mentira. S13 (sentimiento de noticias) sigue apuntada, no se simuló con datos inventados.

### 8.6 Código abierto que voy a usar (parte D)

- **`ta`** (MIT) y **`ccxt`** (MIT): se instalan, no se copian. `ta` reemplaza el RSI y ATR
  hechos a mano y suma MACD, Bollinger, ADX, VWAP. `ccxt` abre la puerta a más exchanges.
- **Grid de `jordantete/grid_trading_bot`** (MIT): se adapta una pieza pequeña a
  `ejecutor.py`, dejando el nombre del autor. No se pega el repo entero.
- **No se copia** Freqtrade ni OctoBot (GPL) ni backtesting.py (AGPL): solo se estudian
  sus ideas de riesgo y salida, y se reescriben.
- Antes de vender, revisar el LICENSE exacto de la versión instalada.

### 8.7 Lo que necesito del dueño (decisiones, no trabajos)

1. **URL pública para Brio.** Decidir entre túnel temporal o esperar a publicar. Sin eso,
   la puerta funciona pero Brio no puede llamarla.
2. **Clave secreta de Brio.** Ya hay una creada en `bot/noticias.json` (campo `brio_token`).
   El dueño la copia de ese archivo y se la da a Brio por canal seguro, junto con la URL
   pública cuando exista. No va en el código, ni en el repo, ni en el chat. Si prefiere otra,
   la reemplaza en ese mismo archivo y la puerta la toma al instante.
3. **Telegram y CryptoPanic** siguen siendo opcionales, como en la sección 6.
4. **Dinero real: no.** `SOLO_PRUEBA` queda en True todo este trabajo.
5. **Probar S11 en papel en vivo ~30 días.** Ya ganó la prueba histórica; el siguiente paso del
   plan (A.4) es correrla en papel, sin plata real, y mostrar el resultado en el panel antes de
   cualquier decisión de dinero. Es un proceso de 30 días: necesita el visto bueno del dueño
   para arrancar, no se salta ni se simula con datos inventados.
6. **Python de los `.bat`.** Los `.bat` llaman a `py -3.12`; en esta PC el intérprete es 3.14 y
   `py` no está en el PATH. Decidir si se ajustan los `.bat` a la versión instalada o se corre
   a mano (el README ya explica los comandos sueltos).

## 9. Plan FINAL — partes A a H (prompt final, 2026-11-07)

Este es el plan final, en el orden exacto que pide el prompt. **No se programa nada nuevo fuera
de esta lista**: las ideas que se ocurran van a `IDEAS-FUTURAS.md`, no se codean. Cada función se
da por terminada solo si funciona de verdad, con datos reales, en computadora y en teléfono, y con
su prueba pasando. **Actualizado el 2026-11-08 al cerrar C.** Las secciones 1–8 son antecedentes
históricos; el estado vigente está en 9–11 y `CONTINUAR-AQUI.md`. Se distingue código implementado,
pruebas automatizadas y verificación de navegador; una categoría no sustituye a la otra.

### Pasos 1 y 2 (este trabajo) — HECHO
- Leída la carpeta completa en `Y:` y corrido `python bot/pruebas.py` → **TODO OK, 90 pruebas**.
- Este PLAN actualizado sin reescribirlo: se marca lo hecho, se corrige lo que estaba mal y se
  agrega el plan final A–H (sección 9), la lista de prueba (sección 10) y las decisiones (sección 11).

### A. Arreglar lo que está a medias — código implementado
- **A1 → HECHO.** `Broker` registra cada cierre mediante el contador opcional; el papel S11 lo
  usa y el backtest no contamina el contador del día. Pruebas RC y P5b pasan.
- **A2 → IMPLEMENTADO; auditoría global pendiente en H3.** Ayuda 1–9, tema del Laboratorio,
  CSV de Laboratorio/scorecard y etiquetas de fuente/edad agregados en `fe5f63b`.
  No se considera probada aquí toda la interfaz: el cierre del 2026-11-08 se limita a Cartera.
- **A3 → HECHO.** `_python.bat` encuentra un intérprete utilizable, incluido Python 3.14;
  ya no se depende exclusivamente de `py -3.12`. Se conservan comandos manuales en README.
- **A4 → HECHO.** Suite del 2026-11-08: **177 comprobaciones OK, TODO OK** (base inicial: 90).

### B. El bot de verdad — código implementado; ensayo largo pendiente
- **B1/B2 → HECHO EN CÓDIGO Y PRUEBAS.** `cerebro.py` usa `CarteraPapel` de `papel.py`, Broker,
  S11 (día+semana+mes) y el registro de decisiones. S1 queda como comparación. Pruebas P pasan.
- **B3 → FALTA / PENDIENTE DE AUTORIZACIÓN.** No se inició el ensayo en vivo de ≥30 días.
  No se reemplaza por datos inventados ni por las pruebas unitarias.
- **B4 → IMPLEMENTADO.** Botón de parada y archivo `bot/APAGADO` para S11. `SOLO_PRUEBA=True`
  sigue fijo; ninguna orden real. Las claves las crea el dueño y nunca se comparten.
- **B5 → IMPLEMENTADO.** Estado, motivo y días de la cuenta en papel. La antigüedad de una cuenta
  no demuestra 30 días de funcionamiento continuo. Revalidar la vista El bot en la auditoría global.
- **B6 → HECHO como criterio.** S11 es una regla de tendencia, no IA.

### C. Órdenes inteligentes y cartera → HECHO en papel (2026-11-08)
- **C1:** entrada a mercado/límite, stop y objetivo al entrar, objetivos parciales y trailing.
  Stop prioritario en velas ambiguas; saltos de precio no garantizan el precio del stop.
  Comisiones/deslizamiento descontados; objetivos simultáneos y cierres anteriores respetados.
- **C2:** vista 9 sin quitar las anteriores; saldo total y por moneda, efectivo/invertido,
  posiciones, P/L estimado neto de cierre y curva con varios movimientos por hora.
  Sin red conserva la última valoración y avisa; no opera con cotizaciones vencidas.
- **C3:** historial de abiertas, pendientes, canceladas y ejecuciones cerradas; fecha, moneda,
  precio, cantidad, comisión, motivo y resultado; búsqueda y CSV descargado y comprobado.
  Cancelar una pendiente no genera dinero, comisiones ni una operación ganada/perdida.
- **C4:** calculadora en USD o pesos sin conversión de divisas, validación de entrada y stop natural.
- **Verificación:** Chrome a 1440 px y emulación móvil táctil a 360/390 px; órdenes, cierre,
  cancelación, filtros, CSV, actualización, pérdida/recuperación de conexión, tema, sin errores JS.
  Botones de Cartera de al menos 44 px y tablas con desplazamiento horizontal contenido.
  Disparos de stops/objetivos/trailing cubiertos con datos controlados en pruebas, no se esperó
  a que el mercado real tocara esos niveles. Cuenta temporal aislada, sin alterar la cuenta del dueño.
- **Alcance:** cuenta manual independiente de S11, USD 1.000 ficticios por moneda usada.
  Resuelve al consultar/actualizar la vista (cada 90 s mientras está abierta), no vigilancia continua
  ni órdenes alojadas en un exchange. Revisa hasta 120 velas horarias disponibles y los ticks
  observados; no reconstruye extremos anteriores a la entrada/último tick ni garantiza cubrir
  desconexiones más largas. Todo esto sigue siendo práctica, no ejecución real.

### D. Código abierto y más exchanges → PARCIAL
- **D1 Usar `ta` de verdad → FALTA.** `ta` 0.11.0 instalado pero **sin importar** en el código
  (verificado: ningún `import ta`). RSI/ATR siguen a mano. Falta MACD, Bollinger, ADX, VWAP en el
  gráfico y `requirements.txt` con las versiones exactas.
- **D2 Usar `ccxt` de verdad → FALTA.** `ccxt` 4.5.92 instalado pero **sin importar**. `exchange.py`
  habla con Binance a mano (HMAC). Falta Binance/Bybit/OKX/Kraken con la misma forma y selector en
  Ajustes. Las claves siguen siendo solo para operar, nunca para retirar.
- **D3 Grid S9 MIT atribuido → HECHO.** Reescrito en `ventaja.py`, atribuido a
  `jordantete/grid_trading_bot` (MIT). Pruebas VA1–VA3 pasan. No se copió el repo entero.
- **D4 No copiar GPL/AGPL → HECHO como regla.** Freqtrade/OctoBot/backtesting.py solo se estudian y
  se reescriben. Antes de vender, revisar el LICENSE exacto de la versión instalada.
- **D5 AI-CryptoTrader (Apache-2.0) solo en prueba → FALTA.** No se usa todavía; si se prueba, solo
  si gana a comprar-y-sostener en walk-forward, sin encender dinero real. Si no gana, se escribe y se apaga.

### E. Noticias y Brio → PARCIAL
- **E1 Puerta de Brio existe → HECHO.** No se recrea. `POST /api/noticias/recibir`, pruebas
  BR1–BR17b (32) pasan, curl real probado (200/401/400/413).
- **E2 Servidor en internet → FALTA / DECISIÓN DEL DUEÑO.** Escucha solo en `127.0.0.1`
  (`servidor.py`). No se expone sin permiso. Opciones por escrito: túnel temporal, red local, o
  servidor en internet, cada una con su riesgo (sección 11, decisión 1). No elige el agente solo.
- **E3 Clave de Brio → HECHO (ubicación).** Está en `bot/noticias.json` (gitignoreado), campo
  `brio_token`, molde en `noticias.EJEMPLO.json`. El dueño la copia y la da a Brio por canal seguro.
  No va en el código, ni en el repo, ni en el chat.
- **E4 URL + clave para Brio → FALTA.** Depende de E2. Hasta que haya URL pública, Brio no puede
  llamar; la puerta está construida y probada en local.
- **E5 Botón "Actualizar ahora" no llama a Brio → HECHO.** Solo lee lo guardado o busca por RSS;
  escrito en el panel (tooltip y pie de vista) y en el README.

### F. Web responsive para teléfono → PARCIAL
- **F1 Base responsive → HECHO (no se borra).** Viewport, menú abajo en teléfono, tarjetas a una
  columna bajo 900px, tablas que colapsan bajo 1320px y 1100px. Falta completarla.
- **F2 Arreglar lo que se ve mal en teléfono → HECHO EN CÓDIGO (2026-11-08, rama
  `ui-mejora-interfaz`).** Tablas con scroll lateral y ancho mínimo, botones de
  40px en computadora y 44px en teléfono, menú abajo con texto corto, gráficos
  completos a 360/390px (altura en CSS, no fija), buscador y formularios a 16px
  sin zoom, estrella de favoritos con zona de toque de 36px. Falta la prueba
  con toque en teléfono físico (ver F3).
- **F2b Sistema de colores y letras → HECHO (2026-11-08, misma rama).** 6 colores
  documentados al inicio del CSS; modo claro completado (bordes, selección,
  línea mediana y líneas cian visibles en los dos temas); botón principal azul,
  peligro rojo solo para parar el bot; pastilla violeta para Brio; estado del
  bot con punto y palabra; miedo/codicia con 5 colores. Solo `panel.html`;
  sin tocar `bot/`, `servidor.py` ni ningún número. Pruebas: TODO OK, 177.
- **F2c Rediseño v2 → HECHO EN CÓDIGO (2026-11-08, misma rama, 10 agentes
  en paralelo, uno por vista + menú).** Tarjetas 22–28px, botones pastilla de
  48px, números grandes, menú de teléfono con solo 5 botones + hoja Más,
  "Para qué sirve" lleno al arrancar en Panel, tema claro verificado en
  Panel/Bot/Cartera. Solo `panel.html`; sin tocar `bot/`, `servidor.py` ni
  ningún número. Pruebas después de cada vista: TODO OK, 177. Capturas
  360/390/1440px en `~/workspace/preview-helios-v2/`. Falta la prueba con
  datos reales y toque en teléfono físico (ver F3).
- **F3 Probar en 360px y 390px → PARCIAL.** Cartera y su navegación probadas el 2026-11-08
  en emulación móvil de Chrome con toque; no fue un teléfono físico. La mejora de
  interfaz se verificó con servidor local (200), sintaxis JS y pruebas 177 TODO OK;
  las capturas en 360/390px con Chromium headless quedan registradas en el reporte
  de la rama; si no salieron, se marca FALTA, no HECHO. Falta auditar las otras vistas
  con toque real.
- **F4 Abrir desde el teléfono por web → FALTA.** Depende de E2. Dejar por escrito cómo abrirlo en
  la misma red y cómo desde internet cuando esté publicado.

### G. Cuentas, demo y pago → FALTA (todo)
G1 modo demo con plata falsa, sin claves ni pago. G2 cuentas por cliente (hoy Helios es para una sola
persona en una PC; para vender es obligatorio). G3 plan gratis/pago por escrito, sin programar un cobro
que no funciona. G4 ayuda en español simple con video o capturas reales del panel, sin números
inventados. Si no se puede todo en esta tanda, se deja por escrito qué queda y por qué, no se finge.

### H. Reportes y que no haya errores → FALTA
H1 reporte por mes (ganancia/pérdida, operaciones, cuántas ganó, peor caída, vs comprar-y-sostener) en
CSV y PDF si se puede. H2 registro de todo (cada orden, cada freno que salta, cada error) con fecha y
hora, legible sin abrir el código. H3 sin errores: pruebas después de cada cambio, en computadora y en
teléfono, sin botones muertos ni pantallas vacías.

### Orden de ejecución (del prompt, sin saltarse nada)
1. Leer + pruebas → **HECHO**. 2. Este PLAN → **HECHO**. 3. Parte A. 4. Parte B (papel con S11; los
30 días solo si el dueño autoriza). 5. Parte C. 6. Parte D. 7. Partes E y F. 8. Partes G y H.
9. Probar una por una con la lista de la sección 10, en computadora y en teléfono. 10. Actualizar
README y PLAN con los números reales y entregar el resumen al dueño.

## 10. Lista para probar una por una (copiada del prompt final)

Marcada con **HECHO** o **FALTA**, con fecha y lo que se vio. No se marca HECHO lo que no se probó
en el navegador (o, si es de API/backtest, con pruebas/curl). Revisión de C: **2026-11-08**;
las comprobaciones anteriores conservan su fecha y la auditoría global aún falta.

**Bot y papel:**
- **HECHO EN PRUEBAS / FALTA ENSAYO LARGO** — S11 abre/cierra y persiste usando Broker (P1–P8c, 2026-11-08). No inició el ensayo de ≥30 días con precios en vivo.
- **FALTA VALIDACIÓN EN VIVO** — Registro de decisiones conectado; resultado real a 24 h y ensayo continuo pendientes, no se inventan resultados.
- **HECHO EN PAPEL** — Stop y take-profit al entrar. Orden configurada en navegador y disparos en pruebas A–C, P5, CM9 y CF (2026-11-08); resolución al actualizar, no continua.
- **HECHO EN PRUEBAS** — Freno de pérdida diaria conectado a S11: X/X2/X3, RC1–RC3 y P5b (2026-11-08). No confundir con la cuenta manual independiente.
- **FALTA REVALIDACIÓN GLOBAL** — Botón de apagado y archivo APAGADO implementados para S11; el archivo bloquea en pruebas K. No se probó otra vez el botón en este cierre de C.
- **FALTA REVALIDACIÓN GLOBAL** — Estado, motivo y días implementados en El bot; P7b pasa (2026-11-08). Antigüedad de cuenta no prueba funcionamiento continuo.

**Órdenes y cartera (2026-11-08):**
- **HECHO** — Límite: creación y cancelación en navegador; llenado al precio en pruebas L y CM6.
- **HECHO** — Stop y objetivo juntos: configurados en navegador y resolución probada en motor; stop primero en vela ambigua.
- **HECHO** — Trailing: configuración visible en navegador; sube, no baja y cierra en pruebas T y CF19/CF20.
- **HECHO** — Venta en partes: dos objetivos al crear en navegador; ventas y comisiones verificadas en TP/TPS/CM7/CF1–CF2, incluso misma vela.
- **HECHO** — Saldo total/por moneda, posiciones, P/L vivo neto estimado, curva y calculadora; navegador a 1440/360/390 px. Sin conexión avisa y se recupera.
- **HECHO** — Historial buscable con abiertas/pendientes/canceladas/ejecutadas, comisión y motivo; CSV descargado y contenido comprobado en los tres tamaños.
- Los disparos de precio usan datos controlados en pruebas; no se esperó una señal del mercado en vivo. Las pruebas de interfaz usan cotizaciones públicas reales y dinero ficticio aislado.

**Exchanges e indicadores:**
- **FALTA** — Cambiar de exchange entre Binance, Bybit, OKX y Kraken funciona. (D2; `ccxt` instalado pero sin usar.)
- **FALTA** — MACD, Bollinger, ADX y VWAP se ven en el gráfico. (D1; `ta` instalado pero sin usar.)
- **HECHO** — Grid S9 funciona en la prueba. (2026-11-07: pruebas VA1–VA3 en `TODO OK` y S9 en `ventaja.py`; es backtest, no requiere navegador.)

**Noticias y Brio:**
- **HECHO** — Noticias por RSS se ven, con fuente, hora y precio de la hora siguiente. (2026-11-07: vista 8 con `haceTxt()` por noticia `panel.html:1587`; verificado en navegador en la tanda anterior y pruebas RSS.)
- **HECHO** — `POST /api/noticias/recibir` responde 200 con clave y 401 sin clave. (2026-11-07: pruebas BR13/BR13b/BR14 → 401/401/200, y curl real; es API, no navegador.)
- **HECHO** — Una noticia de Brio aparece arriba, en la misma lista que las de RSS, sin duplicarse. (2026-11-07: prueba BR10 y verificado en navegador con etiqueta BRIO arriba, mezclada con RSS, sin duplicados.)
- **HECHO** — Si pasan más de 2 horas sin Brio, dice "Sin noticias nuevas importantes". (2026-11-07: prueba BR12 y el texto existe en `panel.html:1521`.)
- **HECHO** — El botón "Actualizar ahora" no llama a Brio. (2026-11-07: verificado en código, tooltip y pie de vista; solo lee lo guardado o busca RSS.)

**Teléfono y web:**
- **HECHO EN CÓDIGO / FALTA TOQUE REAL** — Panel en teléfono a 360px: Cartera probada en emulación táctil Chrome el 2026-11-08, sin desborde de página y botones ≥44 px; la mejora de interfaz 2026-11-08 (rama `ui-mejora-interfaz`) deja tablas con scroll, botones a 44px y gráficos con altura móvil en todas las vistas, pero no se probó con toque en teléfono físico (F3).
- **HECHO EN CÓDIGO / FALTA TOQUE REAL** — Panel en teléfono a 390px: lo mismo que a 360px (F3).
- **HECHO EN CÓDIGO / FALTA TOQUE REAL** — Menú abajo funciona, favoritos, comparador y simulador funcionan con toque. (Favoritos/comparador/simulador verificados en navegador de escritorio el 2026-11-07, commit 23542b1; menú abajo ahora con texto corto y botones de 52px en la mejora 2026-11-08; NO probados con toque en teléfono; F2/F3.)
- **FALTA** — Se puede abrir desde el teléfono por web, no solo desde la PC. (F4; depende de E2, servidor solo en `127.0.0.1`.)

**Cuentas y demo:**
- **FALTA** — Entrar con cuenta, ver solo lo mío. (G2; hoy es single-user.)
- **FALTA** — Modo demo con plata falsa funciona sin claves. (G1.)
- **FALTA (parcial)** — Ayuda en español simple, con capturas reales. (La vista Ajustes tiene ayuda en español `panel.html:1810`; falta video/capturas reales; G4.)

**Reportes y sin errores:**
- **FALTA** — Reporte por mes, con ganancia, operaciones y peor caída, y se baja en CSV. (H1.)
- **HECHO** — `python bot/pruebas.py` sale `TODO OK`, con más de 90 pruebas. (2026-11-08: **177 comprobaciones OK**, contadas en la salida; base original de este plan: 90.)
- **FALTA (parcial)** — No hay botones muertos, ni pantallas vacías, ni números inventados. (Revisión parcial hecha; falta auditoría completa de botones y prueba en teléfono; H3.)

## 11. Lo que el dueño tiene que decidir — no lo decide el agente solo

1. **URL pública para Brio y para la web.** ¿Túnel temporal, red local o servidor en internet? Sin
   su permiso no se expone el servidor. Riesgos en una frase: *túnel* = rápido y temporal, pero la
   URL cambia y queda expuesta mientras dure; *red local* = solo dispositivos de la misma red, no
   sirve para Brio en internet; *servidor en internet* = estable y alcanzable, pero cuesta y hay que
   asegurarlo bien.
2. **Clave de Brio.** Está en `bot/noticias.json` en local (campo `brio_token`). Él la copia y se la
   da a Brio por canal seguro, junto con la URL cuando exista. No va en el código ni en el chat.
3. **Arrancar la prueba en papel de S11 por 30 días.** Cuando lo autorice. Sin eso, B3 queda pendiente.
4. **Dinero real.** Solo con su aprobación por escrito, después de la prueba en papel. Nunca antes.
   `SOLO_PRUEBA=True` se mantiene todo este trabajo.
5. **Python de los `.bat`: resuelto en A.** `_python.bat` detecta un intérprete válido, incluido 3.14.
   Sigue disponible la ejecución manual documentada; ya no bloquea el trabajo.
6. **Cuentas y pago.** ¿Qué plan es gratis y qué plan es de pago, y cuánto cuesta? (G3, por escrito.)
7. **GitHub.** Decisión ya tomada: seguir y subir al final. La autenticación quedó pendiente;
   no reintentar el push en este cierre parcial de C.

Si una de estas decisiones no está, ese trabajo queda marcado como pendiente, no se inventa.
