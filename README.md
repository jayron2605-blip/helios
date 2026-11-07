# Helios — terminal de mercado y laboratorio de estrategias

Panel local que lee **22 fuentes públicas de datos** (sin cuenta, sin clave, sin costo) y un
motor de operaciones que decide, ejecuta en papel y lleva la contabilidad de cada decisión.

No es un bot que promete ganar. Es un sistema que **se niega a operar una estrategia que no le
gana a no hacer nada**, y que muestra los números rojos en la pantalla principal.

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
panel.html        terminal de 7 vistas (112 KB, sin framework)
servidor.py       proxy local con caché; agrega los endpoints /api/*
bot/datos.py      descarga velas del repositorio público de Binance
bot/modelo.py     entrenamiento walk-forward (33 pliegues, reentrena cada mes)
bot/ejecutor.py   motor de órdenes: mismo código para backtest, papel y real
bot/exchange.py   firmado HMAC de Binance + 6 frenos físicos
bot/cerebro.py    circuito vivo: decide y se inhibe si no hay ventaja demostrada
bot/avisos.py     avisos al teléfono por Telegram
bot/pruebas.py    24 pruebas del motor y de los frenos
bot/que_se_puede.py  test de qué es predecible y qué no
```

## Los resultados, sin suavizar

Prueba sobre **201.594 velas reales de 1 hora** (6 mercados, 2023-01 a 2026-10), con validación
walk-forward — el modelo nunca ve el mes que se evalúa — y comisión del 0,1 % por lado descontada.

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

## Frenos

El motor se detiene antes de firmar cualquier orden si falta una de estas condiciones:

1. No existe `bot/claves.json` (copiá `bot/claves.EJEMPLO.json` y pegá tus claves).
2. `solo_simulacro` sigue en `true`.
3. Existe un archivo `bot/APAGADO`.
4. El mercado no está en `mercados_permitidos`.
5. Se superó `maximo_por_operacion_usd` o `maximo_operaciones_dia`.
6. Se tocó `tope_perdida_diaria_usd`.
7. El walk-forward no demostró ventaja.

Ninguna clave va en el código: se leen de archivos locales que están en `.gitignore`.

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
