# CONTINUAR AQUÍ — estado al cerrar la parte C

> **Relevo más reciente: 2026-11-08, rama `demo-cliente`.** Antes de usar este
> antecedente, leer [RELEVO-DEMO-CLIENTE.md](RELEVO-DEMO-CLIENTE.md): contiene el
> estado de la rama y su publicación autorizada, las pruebas del punto de pausa y los pendientes
> de la demo. No reiniciar D desde cero ni aplicar el stash de D1+D2.

Fecha: **2026-11-08**. Trabajar directamente en `\\192.168.100.32\HeliosShare`.
No copiar el proyecto ni depender de Y: (el mapeo falla; la ruta UNC funciona).

## Resumen y punto de partida

**El próximo agente empieza por D.** A está implementada; B tiene el circuito S11 implementado,
pero su ensayo de 30 días NO se inició ni está autorizado. **C queda terminada y verificada como
cartera manual en papel**, con los límites indicados abajo. E tiene trabajo previo aprovechable;
F sólo está verificada para Cartera; G y H siguen pendientes. No está terminado el prompt A–H.

Resultado final de esta revisión: **177 comprobaciones OK / TODO OK** (eran 149 antes del cierre
correctivo de C, y 90 al comenzar el plan final). Cartera probada en navegador a **1440, 360 y
390 px**, estos dos últimos en emulación móvil con toque; no en teléfono físico.

Quedan **cinco bloques D–H más la revisión global y el ensayo largo B3**. No es un porcentaje de
esfuerzo: cuentas, exchanges y publicación son trabajos de tamaño muy distinto y requieren
algunas decisiones del dueño. No se inició implementación de D en este cierre.

## Qué se hizo

### A — implementado

- Conectado `registrar_cierre()` a Broker mediante contador opcional; el papel S11 registra pérdidas
  para su freno diario sin contaminarlo con backtests. Pruebas RC y P5b.
- Exportaciones CSV de Laboratorio/scorecard, etiquetas de fuente/antigüedad y tema del Laboratorio.
- Ayuda y teclas actualizadas; hoy hay nueve vistas, sin eliminar las ocho anteriores.
- `_python.bat` busca un intérprete que funcione, incluido Python 3.14.
- La auditoría de TODOS los botones y textos sigue en H3; no confundir código agregado con haber
  vuelto a recorrer todas las vistas en este cierre.

### B — código S11 listo, prueba larga pendiente

- `bot/papel.py`: cuenta automática S11 (día+semana+mes), usando Broker y persistencia en
  `bot/posiciones.json`; conectada desde `bot/cerebro.py` y al registro de decisiones.
- Estado, motivo, antigüedad de cuenta y botón de apagado en la vista El bot; archivo `bot/APAGADO`.
- Pruebas P1–P8c pasan. S1 queda como comparación, no como estrategia activa del bot.
- **NO arrancar el ensayo ≥30 días sin autorización.** La antigüedad del archivo no acredita
  funcionamiento continuo. No se probaron de nuevo todos los controles de El bot en este cierre.
- `SOLO_PRUEBA=True` sigue fijo: NO hay operaciones reales ni autorización para habilitarlas.

### C — cerrada: órdenes y cartera manual en papel

- `bot/ejecutor.py`: mercado/límite, stop-loss y take-profit al entrar, objetivos parciales,
  trailing stop. Stop prioritario en velas ambiguas, comisiones/deslizamiento y contabilidad.
- `bot/cartera.py`: cuenta aparte de S11, USD 1.000 ficticios por moneda utilizada, seis monedas;
  saldos por moneda, efectivo/invertido, posiciones, P/L estimado neto de liquidación y curva.
- `servidor.py`: GET `/api/cartera`, POST `/api/cartera/orden` y `/api/cartera/cerrar`.
- `panel.html`: vista 9 Cartera, formularios, calculadora USD/pesos sin conversión, stop natural,
  historial buscable y CSV. Abiertas/pendientes/canceladas/ejecuciones visibles sin fingir ganancias.
- Persistencia en `bot/cartera_manual.json`, ignorada por Git. El cierre de revisión usó una cuenta
  temporal separada; no borró ni sobrescribió la cuenta guardada del dueño.

Correcciones finales respecto de la primera implementación de C:

- No resolver extremos de una vela todavía abierta, previos a una entrada o a un tick que ya movió
  el trailing. Marcas separadas para velas cerradas y cotización actual.
- Varios movimientos de la misma hora quedan en la curva; no se pisan por usar la hora de la vela.
- Vender todos los objetivos alcanzados en una vela; descontar correctamente las comisiones.
- Una orden límite sin llenar no se puede vender para crear dinero; cancelarla queda registrada.
- Llenado y stop en la misma vela resueltos de forma conservadora; un salto bajo el stop no promete
  una venta al precio del stop. Cierre manual respeta stops/objetivos previos disponibles.
- Sin red se conserva la valoración guardada y se avisa; sin precio reciente no se ejecuta.
- Rechazo de entradas inválidas/no finitas sin modificar la cuenta; JSON corrupto no reinicia saldo.
- Acceso a la cuenta serializado entre peticiones HTTP; validación de origen y tipo JSON en POST.
- Actualizar y cambiar tema también actualiza la Cartera; gráfico con centavos, dimensiones correctas,
  tablas contenidas y botones de al menos 44 px; pie móvil sin texto superpuesto.

### Límites que NO deben ocultarse

- C es práctica manual, **no cartera real de exchange** ni parte del saldo de S11.
- Resuelve órdenes al consultar/actualizar la vista (cada 90 segundos mientras está abierta).
  **No hay vigilancia continua, órdenes alojadas en el exchange ni garantía de tocar cada precio.**
- Consulta hasta 120 velas horarias recientes. No cubre necesariamente una desconexión más larga;
  no reutiliza extremos anteriores a la entrada/último tick. No reconstruye un recorrido intravela.
- La curva agrega el capital inicial de todas las monedas usadas a toda la serie para que sumar
  otra moneda no se contabilice como ganancia. Mantiene las últimas 2.000 marcas por serie.
- Cada venta parcial figura como ejecución; abiertas muestran el remanente. En pendiente/cancelada,
  cantidad y precio son solicitados, no una compra ejecutada; resultado vacío y comisión cero.
- Pruebas de disparo de stops/objetivos/trailing usan datos controlados. El navegador usa precios
  públicos reales, pero no se esperó a que el mercado tocara esos niveles.

## Evidencia y cómo repetir

Suite, con el Python disponible en esta PC:

```sh
'C:/Users/alina/AppData/Local/Programs/Python/Python314/python.exe' '//192.168.100.32/HeliosShare/bot/pruebas.py'
```

Resultado verificado: **177 líneas OK y TODO OK**. Mantenerlas y sumar regresiones a cada cambio.
`python`/`python3` del PATH pueden ser accesos rotos de Microsoft Store.

Navegador Chrome a 1440×900 y emulación móvil táctil a 360×900/390×900:

- Crear mercado con dos objetivos y trailing; comprobar posición y saldo por moneda.
- Cerrar, ver resultado/comisión y curva; buscar coincidencia y búsqueda vacía.
- Descargar CSV y comprobar contenido, no sólo el aviso de descarga.
- Crear límite pendiente, cancelar y comprobar historial/CSV de cancelación.
- Actualizar cartera, simular pérdida de conexión y recuperar; cambiar tema.
- Validar calculadora en pesos y rechazar stop fuera de rango.
- Sin errores JavaScript; sin desborde horizontal de página, tablas desplazables y botones ≥44 px.
- HTTP de cartera: origen ajeno 403, tipo de contenido incorrecto 415 y cuerpo no objeto 400.

Herramientas de verificación temporales, fuera del repositorio:
`C:\Users\alina\AppData\Local\Temp\helios-browser-check\` contiene `verificar.cjs`,
`servidor_prueba.py`, capturas `cartera-*.png`/`historial-final-*.png` y CSV descargados.
El driver `playwright-core` está instalado sólo allí; usa Chrome del sistema. El servidor de prueba
usa el código compartido, puerto local 8766, cuenta temporal y cuaderno deshabilitado para pruebas.
No confundir sus operaciones ficticias con resultados del dueño ni publicar esos resultados como tales.

El servidor normal en 8765 puede seguir con código anterior: **reiniciarlo de forma controlada para
cargar los cambios**, identificando el proceso y usando Ctrl+C en su terminal, no matando todos los
Python. Sigue escuchando sólo en `127.0.0.1`. No abrir LAN, túnel o internet sin permiso.

## Qué falta, en orden

### D — siguiente trabajo

1. Usar `ta` realmente y mostrar MACD, Bollinger, ADX y VWAP en el gráfico; hoy RSI/ATR se calculan
   a mano y las librerías están instaladas pero sin integrar. Añadir `requirements.txt` exacto.
2. Integrar `ccxt` para Binance/Bybit/OKX/Kraken con la misma interfaz y selector en Ajustes,
   manteniendo frenos y modo prueba fijo. No pedir claves reales para las pruebas.
3. Grid S9 ya existe, reescrito y atribuido a `jordantete/grid_trading_bot` (MIT); no recrearlo.
4. No copiar GPL/AGPL. Revisar las licencias exactas antes de vender; no asumirlas por el nombre.
5. AI-CryptoTrader sólo en pruebas y si supera comprar-y-sostener en walk-forward. No está probado;
   no afirmar rendimiento ni aprobación sin medirlo.

Versiones instaladas observadas: `ta==0.11.0`, `ccxt==4.5.92`, `numpy==2.4.1`, `pandas==2.3.3`,
`scikit-learn==1.9.1`, `scipy==1.18.1`, `joblib==1.6.0`. Verificar antes de fijar dependencias.

### E — Brio/noticias

La puerta POST `/api/noticias/recibir` ya existe, con autenticación y pruebas BR; no recrearla.
Falta decidir cómo hacerla accesible a Brio y entregar URL/clave por canal seguro. Hoy sólo local.
La clave está en `bot/noticias.json`, campo `brio_token`, ignorado por Git: **no leerla al chat ni
subirla al repo**. Actualizar ahora sólo lee lo guardado/RSS, NO llama a Brio.

### F — teléfono/web

Conservar la base responsive. Cartera ya está probada en 360/390; falta revisar las otras ocho vistas,
favoritos, comparador, simulador y filtros con toque. Acceso desde teléfono físico depende de la
autorización de red. Documentar acceso local/internet únicamente según la opción aprobada.

### G — demo, cuentas, pago y ayuda

La práctica manual sin claves no sustituye un modo demo completo ni cuentas de cliente. Falta
separación por usuario, plan gratis/pago aprobado y ayuda con capturas reales. No fingir cobros.

### H — reportes, registro y revisión general

Faltan reporte mensual (P/L, operaciones, ganadas, caída y comparación con comprar-y-sostener), CSV
(y PDF si es viable), registro general de órdenes/frenos/errores y auditoría completa de pantallas.
El historial C no sustituye ese registro general ni el reporte mensual.

### Cierre global

Recorrer cada ítem de PLAN sección 10, computadora y emulación móvil, mantener TODO OK,
actualizar README/PLAN con evidencia real y recién entonces resumir el proyecto completo.

## Git y entrega

Rama `master`; remoto `https://github.com/jayron2605-blip/helios.git`.
Seis commits locales previos a este cierre correctivo:

```text
1365d92 Parte C2-C4: cartera en papel a mano con precios reales
8472655 Parte C1: ordenes inteligentes en el motor (papel y prueba)
ead0325 Parte B: el bot en papel opera S11 con precios reales y se puede parar
fe5f63b Parte A: terminar lo que estaba a medias (panel y .bat)
f22550b A1: cablear registrar_cierre en Broker.cerrar con contador opcional
138a2fd PLAN: plan final A-H del prompt nuevo y lista de prueba marcada
```

Las correcciones finales y estos documentos se entregan en un commit local adicional; consultar
`git log` y `git status` para el identificador y estado actual. **No se hizo push en este cierre.**
El intento anterior quedó esperando autenticación de GitHub; el dueño eligió **seguir y subir al
final**. No reintentar autenticación ni cambiar credenciales por iniciativa propia.

```sh
git -C '//192.168.100.32/HeliosShare' -c safe.directory='%(prefix)///192.168.100.32/HeliosShare/' status --short --branch
```

No modificar configuración global/local de Git. No incluir estados, claves, cuentas temporales,
modelos o capturas de prueba en commits. Trabajar con cambios pequeños y mensajes en español.

## Decisiones y restricciones del dueño

- Ensayo S11 ≥30 días: autorización pendiente; no iniciarlo automáticamente.
- Dinero real: nunca sin aprobación escrita; **NO quitar `SOLO_PRUEBA=True`**.
- URL/red: elegir entre túnel temporal (exposición temporal/URL variable), LAN (sólo la red, no Brio
  externo) o servidor en internet (estable, costos y seguridad). No elegir ni exponer sin permiso.
- Claves: sólo las crea/entrega el dueño por canal seguro, nunca código, repo ni chat.
- Planes y precios: pendiente de decisión; no programar cobros ficticios.
- Python de los .bat ya resuelto con detección: no dejarlo como bloqueo pendiente.
- Firewall: hubo permiso específico para deshabilitar únicamente
  `codex_sandbox_offline_block_outbound`; no se tocaron reglas de loopback. No ampliar ese permiso.
- No agregar funciones fuera de A–H, no borrar vistas, no esconder pérdidas ni inventar resultados.
