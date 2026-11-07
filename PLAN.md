# PLAN.md — plan de trabajo de Helios (noviembre 2026)

Escrito por el agente después de leer todo el código y correr las pruebas del motor
(`py -3.12 bot/pruebas.py` → **TODO OK**). Todo lo que sigue está verificado
leyendo el código, no es creencia.

**Re-verificado el 2026-11-07 a las 15:30 por el agente nuevo**, leyendo el repo completo
y corriendo las pruebas en otra máquina (Windows 11, Python 3.14, scikit-learn 1.9.1).
Resultado: **TODO OK, 81 pruebas** (49 del motor y de las noticias RSS + 32 nuevas de la
puerta de Brio; la prueba V corre en 3 tamaños).
Los números "24" y "39" que aparecían en el README estaban desactualizados.
Lo que este agente corrigió o confirmó está marcado en la sección 8.

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
Hoy: **81 pruebas, TODO OK** (contadas en la salida real, no en el documento).

### La parte C, en limpio (lo que está y lo que no)

| # | Idea | Estado real |
|---|---|---|
| 1 | Calculadora de riesgo por moneda | **hecha ahora**: sigue a la moneda que estás mirando, no solo a Bitcoin |
| 2 | Alertas que sí sirven | hechas (filtro de importancia + freno de 90 min) |
| 3 | Comparador de monedas | **no está** — queda pendiente |
| 4 | Historial de miedo y codicia 90 días | **hecho ahora** (vista On-chain, con datos reales) |
| 5 | Simulador "qué hubiera pasado si" | **no está** — queda pendiente |
| 6 | Lista de seguimiento personal (favoritos) | **no está** — queda pendiente |
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
   de 70,1 % a 58,6 % **en los 6 mercados**. Es protección, no ventaja: en un tramo que subió
   296 % de promedio, proteger costó 300 puntos de ganancia.

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

Pendientes reales de la parte C, por prioridad: **3 (comparador), 5 (simulador), 6 (favoritos)**,
y completar 9 y 10. El detalle de 8 es un arreglo de una línea.

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
| 1 | Leer todo + correr pruebas | **hecho** (49, TODO OK) |
| 2 | Este plan y corregir contradicciones | **hecho** |
| 3 | Verificar los "YA ARREGLADO" | **hecho** (uno resultó a medias) |
| 4 | Instalar `ta` + `ccxt` y Grid MIT | `ta` y `ccxt` instalados; Grid pendiente (va con S9) |
| 5 | `POST /api/noticias/recibir` + unir B1 y B2 | **hecho y probado** (ver 8.4) |
| 6 | Ventaja NUEVA, distinta a S1–S8 | siguiente |
| 7 | Comparador, simulador y favoritos | después |
| 8 | README con números reales + resumen | al cierre |

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
**solo aprueba si le gana a comprar-y-sostener en 4 de 6 mercados o más**. Si pierde, se
escribe igual en el README y en `ventaja.py`. El bot sigue apagado mientras tanto.

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
