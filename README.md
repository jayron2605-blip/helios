# Helios — asistente para traders

Panel local que lee **más de 25 fuentes públicas de datos** (sin cuenta, sin clave, sin costo) y le
explica al usuario, en palabras simples, **qué está pasando en el mercado, si está calmado o
peligroso, y cuánto podría perder si entrara ahora**.

No es un bot que prometa ganar dinero. Es un asistente que se queda apagado cuando su propia
prueba no le gana a no hacer nada, y que **no puede mover dinero real: está en modo prueba fijo**.

## Cómo se usa

Windows, sin instalar nada más que Python 3.12 y Node (el gráfico usa una librería por CDN).

| Archivo | Qué hace |
|---|---|
| `Abrir panel.bat` | Levanta el servidor local y abre el terminal en el navegador |
| `Entrenar.bat` | Baja el histórico de velas y entrena el modelo con walk-forward |
| `Bot en papel.bat` | Cada 15 minutos mira el mercado, decide y anota |
| `Probar el motor.bat` | Corre las 24 pruebas del motor y de los frenos |

Teclas dentro del panel: `1`-`7` cambian de vista, `/` busca, `R` actualiza, `T` tema, `F` pantalla completa.

## Qué hay dentro

```
panel.html        panel de 7 vistas (119 KB, sin framework)
servidor.py       proxy local con caché; agrega los endpoints /api/*
bot/asistente.py  traduce los números a palabras: estado, qué pasa y cuánto podés perder
bot/decisiones.py registro de decisiones, con el resultado escrito 24 h después
bot/ventaja.py    las nueve estrategias probadas, con los mismos datos y los mismos costos
bot/datos.py      descarga velas del repositorio público de Binance
bot/modelo.py     entrenamiento walk-forward (33 pliegues, reentrena cada mes)
bot/ejecutor.py   motor de órdenes: mismo código para backtest y prueba
bot/exchange.py   firmado HMAC de Binance + 6 frenos + candado de modo prueba fijo
bot/cerebro.py    circuito vivo: decide, registra y avisa; se apaga solo si no hay ventaja
bot/noticias.py   noticias en vivo con RSS, sin clave, conectadas con el precio
bot/avisos.py     avisos al teléfono por Telegram, sólo cuando cambia algo importante
bot/pruebas.py    39 pruebas del motor, de los frenos, del candado y de las noticias
bot/que_se_puede.py  test de qué es predecible y qué no
```

## Las 8 vistas

1. **Panel** — el asistente arriba y debajo precios, gráfico, internos y seguimiento.
2. **Gráfico** — velas grandes con EMAs, volumen, RSI, abanico de escenarios y cinta de operaciones.
3. **El bot** — si está apagado o prendido y por qué, las nueve ideas probadas y el registro de decisiones.
4. **Cuaderno** — la libreta de lecturas, exportable a Excel.
5. **On-chain** — capital bloqueado por red y protocolo, stablecoins, red de Bitcoin, exchanges,
   tendencias e historial de miedo y codicia de 90 días.
6. **Laboratorio** — reglas simples probadas contra 33.599 velas reales, comparadas con no hacer nada.
7. **Noticias** — lo que pasó, con hora, fuente, moneda y qué hizo el precio la hora siguiente.
8. **Ajustes** — cómo se usa cada cosa y de dónde sale cada dato.

Cada vista trae arriba una barra que dice, en español simple, para qué sirve.

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

En plata: **1.000 dólares puestos en cada uno de los 6 mercados (6.000 en total) terminaron en
71 dólares con el bot, y en 10.270 dólares dejándolos quietos.**

| | Resultado |
|---|---|
| Retorno del bot | **−98,8 %** |
| Retorno de comprar y sostener | **+71,2 %** |
| Mercados donde el bot le gana al silencio | **0 de 6** |
| Precisión direccional del modelo | 51,1 % |
| Precisión de adivinar siempre la mayoría | 52,8 % |

## Nueve formas de operar, la misma vara (noviembre 2026)

Después de ese primer resultado se probaron nueve maneras distintas, con los mismos datos,
el mismo tramo y los mismos costos (`bot/ventaja.py`). El tramo evaluado es un mercado que
subió muchísimo, así que la vara de comprar-y-sostener quedó en **+296 % de promedio**.

| Idea | Resultado | $6.000 → | Caída media | Gana en | ¿Aprueba? |
|---|---|---|---|---|---|
| S0 comprar y sostener | +296,0 % | $23.757 | 70,1 % | — (es la vara) | — |
| S1 modelo de dirección | −54,3 % | $2.743 | 67,7 % | 0/6 | no |
| S2 dirección + filtro de estado | −58,2 % | $2.508 | 69,1 % | 0/6 | no |
| S3 solo bandas extremas | −46,4 % | $3.217 | 61,9 % | 0/6 | no |
| S4 exposición por agitación (apalancada) | −38,8 % | $3.675 | 71,2 % | 0/6 | no |
| S5 agitación + sesgo de tendencia | −62,1 % | $2.277 | 75,3 % | 0/6 | no |
| S6 agitación, sin apalancar, diario | −17,4 % | $4.957 | 63,5 % | 0/6 | no |
| S7 agitación, sin apalancar, semanal | −12,4 % | $5.257 | 67,1 % | 0/6 | no |
| S8 agitación, tope 0,8, semanal | −4,1 % | $5.754 | 58,6 % | 0/6 | no |

**Ninguna aprueba.** El bot sigue apagado.

Lo que **sí** funcionó, y es lo único que mejoró en todos los mercados: bajar la exposición
cuando viene agitación alta. **S8 reduce la caída máxima de 70,1 % a 58,6 % en 6 de 6 mercados.**
Eso es protección, no ventaja: sirve para no quedar afuera en el peor día, no para ganar más.
En el tramo alcista que se probó, esa protección costó 300 puntos de ganancia.

### Dos cosas que se corrigieron en el camino, y que importan

1. **La agitación sí se puede predecir un poco, pero solo si se pide bien.** Pronosticar el
   *nivel* de agitación salía **15 % peor** que el tonto "supone que sigue igual". Pronosticar
   el *cambio* sale **3,2 % mejor**. El dato está en `resultados/ventaja.json` y la corrección
   es la razón por la que S6, S7 y S8 bajan la caída y S4 no.
2. **El comprar-y-sostener estaba medido con el máximo de la última vela** en lugar del cierre,
   y los costos de entrada y salida se cancelaban entre sí (quedaba como si no cobrara nada).
   Corregido en `bot/modelo.py` y `bot/ventaja.py`. Antes de correr nada se validó el simulador
   contra cinco casos de respuesta conocida, incluida la prueba de que no puede mirar el futuro.

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

## El registro de decisiones

`bot/decisiones.py` anota cada día qué dijo el programa —mercado, precio, probabilidad, acción,
motivo y estado del mercado— y **24 horas después vuelve y escribe qué pasó de verdad**.
El panel muestra esa cuenta: cuántas acertaron, cuántas fallaron y cuántas veces decidió
no hacer nada. Se descarga en `decisiones.csv` para abrir en Excel.

En el laboratorio, sobre 33.599 velas de BTC: **0 de 4 estrategias** (momentum, cruce de medias,
RSI, reversión) le ganan a comprar y sostener, que rinde +367,6 % en el período.

**Conclusión honesta:** con estas fuentes públicas y estas reglas, la dirección del precio no es
predecible. Lo que sí se puede construir es el registro auditable y el detector de humo. Por eso el
bot arranca **INHABILITADO**: lee su propio scorecard y se niega a mandar órdenes mientras no
demuestre ventaja.

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
