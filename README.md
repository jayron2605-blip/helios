# Helios — asistente para traders

Panel local que lee **más de 25 fuentes públicas de datos** (sin cuenta, sin clave, sin costo) y le
explica al usuario, en palabras simples, **qué está pasando en el mercado, si está calmado o
peligroso, y cuánto podría perder si entrara ahora**.

No es un bot que prometa ganar dinero. Es un asistente que se queda apagado cuando su propia
prueba no le gana a no hacer nada, y que **no puede mover dinero real: está en modo prueba fijo**.

## Cómo se usa

Windows, sin instalar nada más que Python 3.12 o más nuevo (probado también en 3.14) y Node (el
gráfico usa una librería por CDN).

| Archivo | Qué hace |
|---|---|
| `Abrir panel.bat` | Levanta el servidor local y abre el terminal en el navegador |
| `Entrenar.bat` | Baja el histórico de velas y entrena el modelo con walk-forward |
| `Bot en papel.bat` | Cada 15 minutos mira el mercado, decide y anota |
| `Probar el motor.bat` | Corre las 177 pruebas del motor, de los frenos, del candado y de las noticias |

Teclas dentro del panel: `1`-`9` cambian de vista, `/` busca, `R` actualiza, `T` tema, `F` pantalla completa.

Los `.bat` ya no piden una versión fija: cada uno llama a `_python.bat`, que busca un Python que
sirva de verdad (primero `py -3.12`, después el launcher de Python, después cualquier
`Python3*` instalado en `%LOCALAPPDATA%`, y al final `python`/`python3`). En esta PC encuentra
3.14 solo. El `python` suelto de Windows suele ser un acceso roto a la Microsoft Store, por eso
se prueba al final y sólo si responde. Si no hay ninguno, el `.bat` avisa y no inventa una versión.

Igual todo se puede correr a mano desde la carpeta del proyecto, con el intérprete que tengas
(acá: `C:\Users\alina\AppData\Local\Programs\Python\Python314\python.exe`):

```
python servidor.py          # el panel en http://127.0.0.1:8765/
python bot/pruebas.py       # las 177 pruebas
python bot/datos.py         # baja o actualiza las velas locales
python bot/ventaja.py       # la búsqueda de ventaja (S0 a S12)
python bot/cerebro.py 24    # una decisión en papel y la registra
```

## Qué hay dentro

```
panel.html        panel de 9 vistas (sin framework)
servidor.py       proxy local con caché; agrega los endpoints /api/*
bot/asistente.py  traduce los números a palabras: estado, qué pasa y cuánto podés perder
bot/decisiones.py registro de decisiones, con el resultado escrito 24 h después
bot/ventaja.py    las trece estrategias probadas (S0-S12), mismos datos y mismos costos
bot/datos.py      descarga velas del repositorio público de Binance
bot/modelo.py     entrenamiento walk-forward (33 pliegues, reentrena cada mes)
bot/ejecutor.py   motor de órdenes: mismo código para backtest y prueba
bot/exchange.py   firmado HMAC de Binance + 6 frenos + candado de modo prueba fijo
bot/cerebro.py    circuito S11 en papel: decide, registra y avisa
bot/papel.py      cuenta automática S11; ensayo de 30 días pendiente de autorización
bot/cartera.py    cuenta manual en papel, órdenes inteligentes y valoración
bot/noticias.py   noticias en vivo con RSS, sin clave, conectadas con el precio
bot/avisos.py     avisos al teléfono por Telegram, sólo cuando cambia algo importante
bot/pruebas.py    177 pruebas del motor, de los frenos, del candado y de las noticias
bot/que_se_puede.py  test de qué es predecible y qué no
```

## Las 9 vistas

1. **Panel** — el asistente arriba y debajo precios, gráfico, internos, seguimiento con
   favoritos (★, guardados en tu PC) y un comparador de hasta tres monedas lado a lado.
2. **Gráfico** — velas grandes con EMAs, volumen, RSI, abanico de escenarios y cinta de operaciones.
3. **El bot** — si está apagado o prendido y por qué, las trece ideas probadas y el registro de decisiones.
4. **Cuaderno** — la libreta de lecturas, exportable a Excel.
5. **On-chain** — capital bloqueado por red y protocolo, stablecoins, red de Bitcoin, exchanges,
   tendencias e historial de miedo y codicia de 90 días.
6. **Laboratorio** — reglas simples probadas contra velas reales, comparadas con no hacer nada, y
   el simulador **«¿Qué hubiera pasado si…?»**: moneda + fecha + capital, y compara
   comprar-y-sostener, DCA semanal y no comprar nada, con los rojos a la vista.
7. **Ajustes** — cómo se usa cada cosa y de dónde sale cada dato.
8. **Noticias** — lo que pasó, con hora, fuente, moneda y qué hizo el precio la hora siguiente.
9. **Cartera** — práctica manual: órdenes inteligentes, saldos por moneda, posiciones, curva,
   historial buscable/CSV y calculadora de riesgo.

Cada vista trae arriba una barra que dice, en español simple, para qué sirve.

## La interfaz (mejora de noviembre 2026, rama `ui-mejora-interfaz`)

Solo se cambió cómo se ve el panel (`panel.html`); la lógica, los números y
las funciones son los mismos. Detalle en `AUDITORIA-UI.md`.

- **Modo oscuro por defecto**, como una terminal profesional, y **modo claro
  que funciona de verdad** (fondos, tarjetas, texto y gráficos, no solo el fondo).
- **6 colores, siempre los mismos:** verde ganancia, rojo pérdida, amarillo
  solo avisos, azul botones principales, violeta solo asistente y noticias de
  Brio, cian acento. Miedo y codicia con su escala de 5 colores.
- **Panel primero:** qué está pasando, qué dice el asistente, cuánto lleva el
  bot en papel y las monedas favoritas, ordenados y sin amontonar.
- **En teléfono:** menú de abajo con icono y texto corto, botones de 44px,
  tablas que se mueven de lado con el dedo, buscador y formularios a 16px
  (sin zoom al tocar), gráficos completos a 360px y 390px.
- Estado del bot con punto de color **y** palabra (apagado, encendido, peligro).

### Cartera manual: qué hace y qué no

Cuenta independiente de S11, sin claves: USD 1.000 ficticios por cada moneda que uses. Permite
entrada a mercado o límite, stop-loss, dos objetivos desde el panel y trailing stop. El motor
admite hasta cuatro objetivos. Muestra comisiones, pérdidas y una estimación neta si cerraras ahora.
El historial incluye abiertas, pendientes, canceladas y ejecuciones; cancelar sin llenar no cobra
comisión ni genera una ganancia. Se guarda en `bot/cartera_manual.json`, fuera de Git.

Las órdenes se resuelven al consultar la cartera: manualmente o cada 90 segundos mientras su
vista está abierta. **No hay vigilancia continua ni órdenes alojadas en el exchange.** Se usan
cotizaciones públicas y hasta 120 velas horarias recientes; una desconexión larga puede dejar
períodos sin cubrir. Los extremos de una vela anteriores a la entrada o al último tick observado
no se reutilizan para disparar un stop retroactivo. Sin cotización reciente no se opera y se
identifica la valoración guardada. Un salto de precio puede superar la pérdida prevista al stop.

La calculadora trabaja en USD o pesos, sin convertir monedas. La curva suma el capital inicial de
cada moneda usada a toda la serie, para que agregar una moneda no parezca una ganancia.

Verificado el 2026-11-08: **177 comprobaciones, TODO OK**; Cartera en Chrome a 1440 px y emulación
móvil táctil a 360/390 px, incluidas órdenes, cancelaciones, filtros, CSV, errores de conexión y tema.
No equivale a auditar todas las vistas ni a probar un teléfono físico. Para continuar el proyecto,
leer `CONTINUAR-AQUI.md`: siguiente parte D; ensayo S11 de 30 días pendiente de autorización.

## El asistente

Lo primero que se ve en el panel. **Se mueve con la moneda que estés mirando**: si abrís
Ethereum, el asistente habla de Ethereum, no de Bitcoin. Responde tres cosas:

- **Estado del mercado**: calmado, normal, nervioso o peligroso, con los motivos concretos.
- **Qué está pasando**: frases con precios, amplitud del mercado y el peor día de los últimos meses.
- **Cuánto podés perder si entrás ahora**: con una barra para poner tu capital. Calcula el corte
  natural según la agitación real de ESA moneda, la pérdida en pesos y porcentaje, y cuántas veces
  de cada 100 ese corte se tocó en los últimos 90 días.

Los avisos por Telegram se mandan **sólo** cuando el estado del mercado cambia de nivel, cuando
aparece una señal fuerte, cuando salta un freno, o en el resumen diario. Nunca más de uno cada
90 minutos; los de seguridad pasan siempre.

## Los resultados, sin suavizar

Prueba sobre **201.594 velas reales de 1 hora** (6 mercados, 2023-01 a 2026-10), con validación
walk-forward — el modelo nunca ve el mes que se evalúa — y comisión del 0,1 % por lado descontada.
Este primer cuadro es el scorecard del modelo de dirección sobre **toda** la historia; el cuadro
de las trece estrategias más abajo usa sólo el tramo que el walk-forward alcanza a evaluar, por
eso su vara de comprar-y-sostener es distinta (−0,8 %).

En plata: **1.000 dólares puestos en cada uno de los 6 mercados (6.000 en total) terminaron en
71 dólares con el bot, y en 10.270 dólares dejándolos quietos.**

| | Resultado |
|---|---|
| Retorno del bot | **−98,8 %** |
| Retorno de comprar y sostener | **+71,2 %** |
| Mercados donde el bot le gana al silencio | **0 de 6** |
| Precisión direccional del modelo | 51,1 % |
| Precisión de adivinar siempre la mayoría | 52,8 % |

## Trece formas de operar, la misma vara (noviembre 2026)

Después de ese primer resultado se probaron trece maneras distintas (S0 a S12), con los mismos
datos, el mismo tramo y los mismos costos (`bot/ventaja.py`). **Todas, incluida la vara S0, corren
en el mismo tramo**: el que el walk-forward alcanza a evaluar (desde 2024-08). En ese tramo
comprar-y-sostener rindió **−0,8 % de promedio**, no el +296 % que salía antes cuando la vara
usaba toda la historia y las estrategias sólo el pedazo de prueba.

| Idea | Resultado | $6.000 → | Caída media | Gana en | ¿Aprueba? |
|---|---|---|---|---|---|
| S0 comprar y sostener | −0,8 % | $5.953 | 69,9 % | — (es la vara) | — |
| S1 modelo de dirección | −54,3 % | $2.743 | 67,7 % | 1/6 | no |
| S2 dirección + filtro de estado | −58,2 % | $2.508 | 69,1 % | 1/6 | no |
| S3 solo bandas extremas | −46,4 % | $3.217 | 61,9 % | 1/6 | no |
| S4 exposición por agitación (apalancada) | −38,8 % | $3.675 | 71,2 % | 0/6 | no |
| S5 agitación + sesgo de tendencia | −62,1 % | $2.277 | 75,3 % | 0/6 | no |
| S6 agitación, sin apalancar, diario | −17,4 % | $4.957 | 63,5 % | 3/6 | no |
| S7 agitación, sin apalancar, semanal | −12,4 % | $5.257 | 67,1 % | 4/6 | no |
| S8 agitación, tope 0,8, semanal | −4,1 % | $5.754 | 58,6 % | 5/6 | no |
| S9 rejilla de precios (grid) | −29,3 % | $4.240 | 55,8 % | 2/6 | no |
| S10 rotación: la más fuerte que sus pares | −19,7 % | $4.816 | 60,6 % | 2/6 | no |
| S11 confirmación día+semana+mes | **+69,2 %** | **$10.152** | **27,6 %** | **4/6** | **sí** |
| S12 DCA semanal según agitación | −1,4 % | $5.917 | 69,9 % | 4/6 | no |

**S11 es la única que aprueba** el corte (ganarle a la vara en más de la mitad de los mercados y
no quedar en rojo): +69,2 % de promedio, 4 de 6 mercados, y baja la caída máxima de 69,9 % a
27,6 % en los 6. Es una regla simple de tendencia —estar dentro sólo cuando el día, la semana y
el mes vienen subiendo a la vez—, **no es inteligencia artificial**.

Para no engañarse con el promedio: la mediana por mercado es +31,6 %; el mejor mercado (XRP)
rindió +225,5 % y el peor (BNB) +3,3 %. En BTC, SOL y BNB gana apenas unos puntos. Son pocos
pliegues (unos dos años): es una ventaja medida, no una garantía. **El bot sigue en papel y
`SOLO_PRUEBA` en True**: lo que sigue es probar S11 en papel en vivo unos 30 días antes de que el
dueño decida nada con plata real.

Las otras doce no aprueban. Lo que sí mejoró en todos los mercados fue bajar la exposición
cuando viene agitación alta (S8 baja la caída de 69,9 % a 58,6 % en 6 de 6): eso es protección,
no ventaja.

### Tres cosas que se corrigieron en el camino, y que importan

1. **La agitación sí se puede predecir un poco, pero solo si se pide bien.** Pronosticar el
   *nivel* salía peor que el tonto "supone que sigue igual"; pronosticar el *cambio* sale
   **3,2 % mejor**. El dato está en `resultados/ventaja.json`.
2. **El comprar-y-sostener estaba medido con el máximo de la última vela** en lugar del cierre,
   y los costos de entrada y salida se cancelaban entre sí. Corregido en `bot/modelo.py` y
   `bot/ventaja.py`, con pruebas de que el simulador no puede mirar el futuro.
3. **La vara y las estrategias no corrían en el mismo tramo.** S0 usaba toda la historia y las
   estrategias sólo el tramo de prueba, así que la vara quedaba inflada (+296 %). Ahora todas
   corren en el mismo tramo y la vara real de ese tramo es −0,8 %. Sin esta corrección, cualquier
   comparación habría sido mentira.

## Noticias en vivo

Vista aparte, con las fuentes públicas que funcionan sin clave: RSS de **CoinDesk**,
**Cointelegraph** y **Decrypt**. Con una clave gratuita opcional de CryptoPanic se suma esa
fuente (molde en `bot/noticias.EJEMPLO.json`; el archivo real está en `.gitignore`).

Cada noticia muestra título, medio, hora real, la moneda que afecta si el texto la nombra,
una línea en español de qué va, y **qué hizo el precio en la hora siguiente**, medido con velas
cerradas de Binance. Si la hora todavía no cerró, se vuelve a intentar más tarde; nunca se
inventa el número.

El filtro es transparente: el panel dice cuántas llegaron, cuántas quedaron y por qué se
descartaron (viejas de más de 48 h, que no hablaban de cripto, repetidas, publicidad).
Los resúmenes solo afirman lo que el título dice: "U.S. Treasury moves to cut off a crypto
exchange" es una restricción, no una compra de reservas.

### Brio empuja; la app nunca le pide

La dirección es **sólo Brio → app**. Brio manda un lote JSON a `POST /api/noticias/recibir` con
la cabecera `Authorization: Bearer <clave>`. La app guarda lo que llega y lo mezcla con los RSS
en una sola lista, sin duplicados. Respuesta: `{"ok":true,"recibidas":N,"nuevas":M}`. Sin clave,
con clave equivocada o sin clave configurada, responde **401 y no guarda nada**.

- **La URL que el dueño le tiene que dar a Brio:** `http://127.0.0.1:8765/api/noticias/recibir`
  si Brio corre en esta misma PC. Si Brio corre en otra PC (como ahora), esa dirección no le
  sirve: haría falta publicar el servidor (un túnel o abrirlo a la red local), y **eso todavía
  no está hecho ni aprobado**. El servidor hoy escucha sólo en `127.0.0.1`, así que desde otra
  máquina Brio aún no puede empujar.
- **La clave** vive en `bot/noticias.json` (campo `brio_token`), un archivo en `.gitignore` que
  crea el dueño; el molde está en `bot/noticias.EJEMPLO.json`. No se escribe en el código ni se
  manda por chat.
- **El botón "Actualizar ahora" del panel NO llama a Brio.** Sólo vuelve a leer lo que Brio ya
  mandó y guardó, o hace que la app busque sola por los RSS. Brio no es un servidor y no está
  prendido las 24 horas, por eso la app nunca le pide nada.
- Si Brio no mandó nada en más de 2 horas, el panel dice "Sin noticias nuevas importantes" en
  vez de inventar actividad.

## El registro de decisiones

`bot/decisiones.py` anota cada día qué dijo el programa —mercado, precio, probabilidad, acción,
motivo y estado del mercado— y **24 horas después vuelve y escribe qué pasó de verdad**.
El panel muestra esa cuenta: cuántas acertaron, cuántas fallaron y cuántas veces decidió
no hacer nada. Se descarga en `decisiones.csv` para abrir en Excel.

En el laboratorio, sobre 33.599 velas de BTC: **0 de 4 estrategias** (momentum, cruce de medias,
RSI, reversión) le ganan a comprar y sostener, que rinde +367,6 % en el período.

**Conclusión honesta:** con estas fuentes públicas, adivinar la dirección del precio no funciona
(S1 a S3 pierden). Lo que sí apareció fue una regla de tendencia en tres plazos (S11) que le gana
a la vara en la prueba histórica; y lo que siempre se puede construir es el registro auditable y
el detector de humo. Aun con S11 aprobada, el bot arranca **INHABILITADO para plata real**: lee su
propio scorecard, sigue en papel y `SOLO_PRUEBA` en True. El camino que falta es probar S11 en
papel en vivo unos 30 días y que el dueño lo apruebe por escrito; nada de eso se salta.

## Modo prueba fijo

Helios **no puede mover dinero real**. No es una opción que esté apagada: no existe el camino.

`bot/exchange.py` tiene `SOLO_PRUEBA = True` como decisión de producto. Con eso:

- `comprar_mercado()` y `vender_mercado()` lanzan `ModoSoloPrueba` siempre, aunque alguien cargue
  claves válidas y apague el interruptor de simulacro.
- El cliente habla únicamente con el entorno de prueba del exchange.
- La interfaz lo dice en el panel y en la vista del bot.

Encima de eso quedan los frenos de siempre: falta de claves, archivo `bot/APAGADO`, mercados
permitidos, tope por operación, tope de operaciones diarias, tope de pérdida diaria y la
condición de ventaja demostrada. Están cubiertos por las pruebas R a U.

## Datos y fuentes

Binance spot y Binance Futuros (velas, libro, funding, interés abierto, ratio largo/corto,
flujo taker, operaciones, interés abierto histórico y traders grandes), CoinGecko (mercados,
sparklines, global, exchanges, tendencias), DefiLlama (TVL por cadena y protocolo, stablecoins),
mempool.space (comisiones, cola, potencia de minado), alternative.me (miedo y codicia de hoy y
de 90 días) y los RSS públicos de CoinDesk, Cointelegraph y Decrypt. Todas públicas y gratuitas.

`bot/datos/` (79 MB de velas) y `bot/resultados/` (modelos y curvas) están gitignoreados:
se regeneran con `Entrenar.bat`.

## Aviso

Nada de esto es asesoramiento financiero. El software no mueve dinero y su propia prueba dice que
las reglas que implementa pierden contra quedarse quieto.
