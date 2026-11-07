# Helios — asistente para traders

Panel local que lee **22 fuentes públicas de datos** (sin cuenta, sin clave, sin costo) y le
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
bot/datos.py      descarga velas del repositorio público de Binance
bot/modelo.py     entrenamiento walk-forward (33 pliegues, reentrena cada mes)
bot/ejecutor.py   motor de órdenes: mismo código para backtest y prueba
bot/exchange.py   firmado HMAC de Binance + 6 frenos + candado de modo prueba fijo
bot/cerebro.py    circuito vivo: decide y se apaga solo si no hay ventaja demostrada
bot/avisos.py     avisos al teléfono por Telegram, sólo cuando cambia algo importante
bot/pruebas.py    29 pruebas del motor, de los frenos y del candado
bot/que_se_puede.py  test de qué es predecible y qué no
```

## El asistente

Lo primero que se ve en el panel. Cada vez que se actualiza responde tres cosas:

- **Estado del mercado**: calmado, normal, nervioso o peligroso, con los motivos concretos.
- **Qué está pasando**: dos o tres frases con precios, amplitud y el peor día de los últimos meses.
- **Cuánto podés perder si entrás ahora**: con una barra para poner tu capital. Calcula el corte
  natural según la agitación real, la pérdida en pesos y porcentaje, y cuántas veces de cada 100
  ese corte se tocó en los últimos 90 días.

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
flujo taker, operaciones), CoinGecko (mercados, sparklines, global, exchanges, tendencias),
DefiLlama (TVL por cadena y protocolo, stablecoins), mempool.space (comisiones, cola, potencia de
minado) y alternative.me (índice de miedo/codicia). Todas públicas y gratuitas.

`bot/datos/` (79 MB de velas) y `bot/resultados/` (modelos y curvas) están gitignoreados:
se regeneran con `Entrenar.bat`.

## Aviso

Nada de esto es asesoramiento financiero. El software no mueve dinero y su propia prueba dice que
las reglas que implementa pierden contra quedarse quieto.
