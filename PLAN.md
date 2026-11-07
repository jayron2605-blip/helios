# PLAN.md — plan de trabajo de Helios (noviembre 2026)

Escrito por el agente después de leer todo el código y correr las pruebas del motor
(`py -3.12 bot/pruebas.py` → **TODO OK**, 29 pruebas). Todo lo que sigue está verificado
leyendo el código, no es creencia.

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
   suma a `perdida_usd` cuando una operación cierra mal. → Corregido con `registrar_cierre()`.
5. **`SOLO_PRUEBA = True` se mantiene.** Es un candado a propósito: con este candado es
   imposible mandar una orden real aunque alguien cargue claves y apague el simulacro.
   No se toca durante todo este trabajo. Se quitará solo si Jairon lo aprueba por escrito
   después de ver una prueba en papel ganadora por lo menos 30 días.
6. **Alcances (no son bugs, son límites reales):** el asistente analiza una moneda
   (BTC por defecto), el bot mira 6, y el laboratorio solo funciona con las que tienen
   historial bajado (las mismas 6). Todos los endpoints del panel ya son `/api/...`
   y el panel solo muestra: apto para la futura app móvil.

## 2. El orden del trabajo

| Paso | Qué hago | Estado |
|---|---|---|
| 1 | Leer todo + correr pruebas | hecho |
| 2 | Este plan | hecho |
| 3 | Corregir los 3 errores de arriba (empresa pequeña, pruebas nuevas) | hecho |
| 4 | Noticias en vivo: módulo nuevo + `/api/noticias` + vista nueva en el panel | hecho |
| 5 | Buscar ventaja real para el bot con prueba walk-forward | hecho (sin ventaja direccional; sí en agitación) |
| 6 | Conectar cerebro con registro de decisiones en papel | hecho |
| 7 | Mejoras de la parte C (5 implementadas de 10 propuestas) | hecho |
| 8 | README actualizado con los números reales + resumen para Jairon | hecho |

Después de cada cambio corro `py -3.12 bot/pruebas.py`. Si no sale TODO OK, no sigue nada.

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

| # | Idea | Por qué sirve | Estado |
|---|---|---|---|
| 1 | Calculadora de riesgo en cada moneda | anteshar de comprar cuánto perderías en pesos y en % | sí (era del asistente, ahora por moneda) |
| 2 | Alertas que sí sirven | solo cambios de estado, señales, frenos y resumen diario por Telegram | ya existía; se mantiene |
| 3 | Comparador de monedas | ver 2-3 monedas juntas: quién sube, quién baja, quién está más agitado | **sí** |
| 4 | Historial de miedo y codicia 90 días | hoy solo se ve el número de hoy; una gráfica de 90 días pone en contexto | **sí** |
| 5 | Simulador "qué hubiera pasado si" | poner plata en una fecha y ver bot vs quieto | próximamente |
| 6 | Lista de seguimiento personal | marcar monedas favoritas y que queden arriba | **sí** |
| 7 | Explicación en una frase por pantalla | cada vista se entiende sin preguntar | **sí** (todas las vistas) |
| 8 | Modo claro/oscuro bien hecho | ya funcionaba; se completa en la vista nueva y gráficos | sí |
| 9 | Fuente y edad de cada dato | "Binance, hace 2 minutos": si un dato es viejo, se ve viejo | **sí** |
| 10 | Exportar la prueba y las decisiones a CSV | abrir en Excel el cuaderno, scorecards y decisiones del bot | **sí** |

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
