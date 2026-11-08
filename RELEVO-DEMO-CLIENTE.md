# Relevo exacto — Helios DEMO

Fecha del punto de pausa: **2026-11-08**.

**La demo NO está terminada.** El dueño pidió detener el trabajo en un punto verificable para que otro agente continúe. Se cerraron las conexiones parciales de indicadores, preferencias y lectura del cuaderno. No se inició una nueva etapa de producto.

## 1. Empezar aquí, sin perder cambios

- Carpeta real en esta Mac: `/Users/jairon/HeliosShare` (carpeta compartida por SMB con Windows).
- Ruta de Windows del proyecto: `\\192.168.100.32\HeliosShare`.
- Repositorio: `jayron2605-blip/helios`.
- Rama ACTUAL comprobada: **`demo-cliente`**.
- Base original comprobada: **`696dc34` — Juntar ui-mejora-interfaz a master: mejora de la interfaz**.
- **Después del punto de pausa, el dueño autorizó subir este relevo a GitHub en `demo-cliente`.** El código, este documento y las evidencias se incluyen en el commit del relevo. Consultar su identificador con `git log -1 --oneline -- RELEVO-DEMO-CLIENTE.md` y comprobar si existen cambios locales posteriores con `git status`. No se fusiona con master.
- La rama se creó desde `origin/master` después de fetch y de guardar el trabajo anterior. No volver a ejecutar ciegamente “pull en master y crear rama”: ese paso inicial ya fue resuelto preservando cambios.
- Existe `stash@{0}`: `On master: Trabajo local D1+D2 (ta+ccxt) antes de demo-cliente — NO perder`. Contiene trabajo previo que NO corresponde íntegramente a la demo. **No aplicar, borrar ni hacer pop:** reintroduciría D2, excluido hoy.
- No cambiar de rama, resetear, limpiar archivos, sobrescribir el árbol con GitHub ni reinstalar versiones a ciegas.

Comprobar primero (no modifica archivos):

```sh
git -C /Users/jairon/HeliosShare status --short
git -C /Users/jairon/HeliosShare branch --show-current
git -C /Users/jairon/HeliosShare log -1 --oneline
git -C /Users/jairon/HeliosShare stash list
```

`verificacion-relevo/resultado.json` contiene SHA-256 de los cuatro archivos de implementación al verificar este punto. Sirve para detectar si otro agente ya los cambió; no es un commit ni una copia de respaldo.

## 2. Reglas del dueño que siguen vigentes

- Sólo demo: **nada de dinero real, claves reales de exchange, órdenes reales, retiros o cobros**.
- Mantener `SOLO_PRUEBA = True` en `bot/exchange.py`. No tocar los frenos.
- Cartera manual: USD 1.000 ficticios por moneda utilizada. Bot S11: papel. No inventar P/L, ganancias, noticias o resultados.
- Banner global: **“Modo demo — dinero falso”**.
- Trabajar únicamente en `demo-cliente`. No fusionar con master. No crear commit/push sin autorización del dueño.
- Hoy: D1, F3/F4 y H. NO D2/ccxt multi-exchange, D5/AI-CryptoTrader, B3/ensayo de 30 días, E2/E4/publicación y claves Brio, G/cuentas o pagos.
- La existencia de código S11 y un botón Reanudar NO autoriza iniciar el ensayo de 30 días.
- Se autorizó acceso LAN para la demo, **no internet público**, túneles ni abrir puertos del router. Escuchar en `0.0.0.0` NO limita automáticamente a WiFi privada: escucha todas las interfaces IPv4.
- No leer/copiar secretos de `bot/noticias.json` ni claves de exchange. No incluir tokens, credenciales SMB, cuentas o resultados privados en el relevo/Git.
- Después de cada bloque de cambios: `python3 bot/pruebas.py`, mantener **177 OK / TODO OK**.
- Reinicio controlado del servidor: identificar proceso y usar Ctrl+C en su terminal; no matar todos los Python.

## 3. Archivos y estado exacto

### Implementación modificada

**`panel.html`**

- Cuatro capas nuevas de `ta`: MACD, Bollinger, ADX y VWAP. Bollinger/VWAP sobre las velas; MACD/ADX en subgráficos. EMA y RSI existentes permanecen.
- `traerIndicadores()` usa `/api/indicadores`, con límite de espera de 15 segundos, mensaje terminal si falla y reintento al apagar/encender la capa. Conserva el aviso si el servidor calcula con datos antiguos (`stale`).
- Se invalidan respuestas antiguas al cambiar/recargar velas. Los huecos de calentamiento se representan como puntos sin valor, no como ceros: fechas de MACD/ADX/RSI alineadas con el gráfico principal.
- Si falla la carga de velas, se limpian gráficos en vez de conservar velas/indicadores de otro mercado.
- `opcionGrafico()` usa la paleta actual; MACD/ADX responden al cambio claro/oscuro.
- Banner global persistente agregado en HTML y CSS, fuera del contenido desplazable.
- Botones de cabecera y sliders propios a un mínimo de 44 px en teléfono. La atribución de TradingView se conserva.
- Ajustes tiene preferencias reales de tema y mostrar/ocultar “Para qué sirve”, guardadas en `localStorage` (`helios.pref`). **Se cerró lo que quedó a medias:** `salvarPref()` actualiza también el estado visual de los controles, incluso al usar cabecera/ayuda o recargar.
- Si falla totalmente Noticias sin datos guardados, dice “Sin noticias ahora, inténtalo luego”. Esto no equivale a haber auditado todos los fallos de RSS.
- `traerLog()` mapea por nombres de cabecera: ya no quita la fecha ni desplaza columnas/precio.

**`servidor.py`**

- Nuevo GET `/api/indicadores?simbolo=BTCUSDT&intervalo=1h`, lee 500 velas públicas Binance y llama a `bot/indicadores.py`. Respeta estado `ok`, `cache` o `stale:*` del origen.
- `leer_cuaderno()` tolera bytes NUL al leer, conserva CSV entrecomillado multilínea y descarta filas estructuralmente inválidas. **No repara ni reescribe el archivo del dueño.** Su cuaderno tenía 93 bytes NUL; no se afirma su causa.
- `HELIOS_HOST` permite elegir dirección; predeterminado sigue `127.0.0.1`. `ip_local()` imprime una IP candidata al abrir por LAN.
- **LAN NO está cerrada:** `_cartera_post()` sólo admite Origin loopback/localhost. Un navegador que abre por IP LAN recibe 403 al ordenar/cerrar. Verificado con un manejador aislado, sin ejecutar órdenes.
- Algunos comentarios anteriores dicen “sólo local”; no confundirlos con una garantía de aislamiento si se configura `0.0.0.0`.

### Archivos incorporados con el relevo

**`bot/indicadores.py`**: cálculo real usando `ta==0.11.0`. MACD(12,26,9), Bollinger(20,2), ADX(14), VWAP **móvil de 14 velas** (no VWAP reiniciado por sesión), RSI(14), ATR(14). RSI/ATR están disponibles en la API; el RSI visual existente sigue siendo el cálculo JS. Listas vacías/series cortas ya no hacen fallar ADX/ATR y se omite su calentamiento artificial.

**`requirements.txt`**: todas las versiones comprobadas con `importlib.metadata` en **esta Mac / Python 3.9.6**:

```text
ta==0.11.0
ccxt==4.5.64
numpy==2.0.2
pandas==2.3.3
scikit-learn==1.6.1
scipy==1.13.1
joblib==1.5.3
```

`ccxt` está listado por pedido del dueño, NO integrado en esta rama. Estos pines no certifican instalación ni compatibilidad en Python 3.14 de Windows. No instalar a ciegas ahí; verificar primero. El comentario del archivo sobre coincidencias con Windows es antecedente, no una comprobación nueva de Windows en este relevo.

**`verificar_relevo.py`**: comprobación reproducible, aislada, explicada abajo.

**`verificacion-relevo/`**: `resultado.json`, `regresiones.txt`, capturas `indicadores-360.png`, `indicadores-390.png`, `indicadores-1440.png`. Contiene evidencia de pruebas, no datos de cuentas del dueño.

**Este documento** y el aviso al inicio de `CONTINUAR-AQUI.md`: instrucciones de relevo. El resto de README/PLAN todavía requiere la entrega final solicitada.

## 4. Verificación realizada en este punto

Ejecutadas de nuevo, no sólo heredadas del chat:

- **177 comprobaciones OK / TODO OK** de `bot/pruebas.py`, sin modificar ese archivo ni los módulos de dinero/frenos.
- **79 comprobaciones del relevo** en `verificar_relevo.py`. La suite de 177 se contabiliza como un control dentro de esas 79; no son “256 pruebas independientes”.
- Sintaxis JS con `node --check`, compilación Python, llaves CSS balanceadas y `git diff --check`.
- Pines instalados coincidentes, indicadores con 0/1/2/13/14/26/27/28/100/500 velas de prueba, JSON sin NaN, casos CSV NUL/multilínea/truncado sin reescritura, API conserva `stale`.
- Chromium a 360×740, 390×844 y 1440×900: persistencia tras recarga, controles sincronizados, temas MACD/ADX, índices temporales alineados, columna fecha/mercado/precio del cuaderno y fallo 503 de indicadores sin carga infinita. Sin errores JS en ese recorrido.
- Las **500 velas BTCUSDT 1h sí se obtuvieron de Binance**. Se capturaron los indicadores y se inspeccionaron visualmente las capturas de 360 y 1440.
- Banner visible y ancho de página sin desborde en las 9 vistas en ese ensayo. **Las otras APIs estaban aisladas con datos nulos** para no alterar cuentas/secretos/archivos del dueño. Esto NO acredita las otras ocho vistas con datos reales ni todos sus controles.
- Toque **emulado** para abrir/cerrar Más a 360/390. No un teléfono físico.

### Rectificación importante de afirmaciones anteriores

El chat llegó a decir “F3/F4 done” y “phone can open”. Era excesivo: se habían hecho emulación y peticiones a la IP LAN **desde la propia Mac**, no acceso de otro dispositivo ni prueba física. F3/F4 se devolvió a pendiente. El reporte anterior `/tmp/helios-f3/report.json` también marcaba `mas_abre:false` por un selector de prueba incorrecto; la prueba nueva usa `#masFondo.abierta` y pasa. No tomar las capturas viejas como cierre global.

### Repetir la verificación

Desde la carpeta del proyecto:

```sh
python3 bot/pruebas.py
python3 verificar_relevo.py
```

La segunda requiere Node, las dependencias del proyecto y Playwright/Chromium. En esta Mac están instalados. En otra máquina, verificar antes; si faltan, instalar únicamente para pruebas cuando esté permitido:

```sh
python3 -m pip install playwright
python3 -m playwright install chromium-headless-shell
```

No añadir Playwright a las dependencias funcionales de la app sin necesidad. El script consulta Binance/CDN; si no hay internet o cambian versiones, debe fallar con honestidad. No reemplazar datos reales por inventados para forzar un OK.

El script levanta un servidor en **127.0.0.1 y puerto efímero**, deshabilita POST y las APIs ajenas a lo probado, usa un CSV temporal y lo cierra todo al terminar. No llama a `servidor.main()`, no abre el bot y no opera la cuenta real del dueño, ni siquiera en papel.

## 5. Estado del servidor al entregar

- **No hay servidor escuchando en el puerto 8765** al comprobar este relevo. No depender de antiguos PID 2889/4123/4685/4878 del chat.
- No se dejó servidor de pruebas ni navegador de pruebas ejecutándose.
- El bind predeterminado sigue siendo loopback. No se publica nada al cerrar.
- PC Windows: `Abrir panel.bat`, URL `http://127.0.0.1:8765/`. No se ejecutó el .bat de Windows desde esta Mac.
- Mac: abrir terminal en `/Users/jairon/HeliosShare`, ejecutar `python3 servidor.py`; Ctrl+C para detener. Importa el directorio de trabajo: todavía hay rutas relativas para archivos del proyecto.
- La IP de la Mac usada antes fue `192.168.100.9`; es un antecedente, no una dirección garantizada después de reconectar. La PC Windows compartía por `192.168.100.32`. La dirección del teléfono debe ser la **máquina que realmente ejecuta servidor.py**, no necesariamente la que comparte los archivos.
- No relanzar LAN para demostrar órdenes hasta resolver el punto siguiente y revisar origen/red. La lectura por IP LAN sí se había comprobado desde la propia Mac; no representa una prueba de firewall desde el teléfono.

## 6. Siguiente trabajo exacto — todavía NO hecho

### Paso inmediato: cerrar F4 sin abrir de más

1. Revisar `servidor.py`: `HOST`, `main()`, `_cartera_post()` y las rutas POST de bot/cuaderno/Brio.
2. Corregir el rechazo de Origin LAN **sin desactivar la validación ni aceptar cualquier origen/Host**. Definir los orígenes locales esperados y probar rechazos ajenos. No asumir que bind `0.0.0.0` equivale a red privada.
3. Probar lectura y POST de Cartera en la misma LAN con cuenta temporal, y revisar protección coherente de los otros POST. Brio conserva su autenticación; no crear clave ni URL pública.
4. Preparar instrucciones/arranque LAN para PC, elegir IP correcta, WiFi común y firewall sólo en red privada si el dueño lo autoriza. No crear excepciones amplias ni tocar el router.

### Después: F3 físico (bloqueante para dar por lista la demo)

- Necesita un teléfono físico disponible y participación del dueño si el agente no puede manejarlo. No sustituirlo por emulación ni marcar completado por una captura.
- Recorrer las 9 vistas, toque real, datos reales, tamaños 360/390 CSS cuando el dispositivo lo permita. Registrar dispositivo, navegador, tamaño y qué se probó de verdad.
- Verificar buscador, favoritos, comparador, desplazamiento de tablas/gráficos, intervalos, menú Más, temas y formularios. No limitarse a medir `document.scrollWidth`.

### H: auditoría funcional pendiente

- Panel: asistente, bot, favoritos y comparador con datos reales; revisar fallos de fuentes.
- Gráfico: D1 tiene el punto comprobado descrito arriba. Falta auditoría completa de controles/escenarios/intervalos y uso físico. Comprar y Vender **ambos sólo navegan a Cartera**, no ejecutan acciones diferenciadas; aclarar o conectar el recorrido demo sin dinero real. Los botones de intervalos aún requieren validar la exigencia de una fila en móvil.
- El bot: probar PARAR/Reanudar, estado con punto+palabra, frenos, historial y P/L; usan el archivo APAGADO. No confundir quitar APAGADO con que exista un proceso del bot corriendo. No iniciar el ensayo de 30 días ni inventar historial para llenar la pantalla.
- Cuaderno: lectura/arreglo de columnas sí probado con CSV temporal. Falta probar Anotar y exportar realmente; `anotar(true)` aún anuncia éxito antes de confirmar HTTP y el CSV se arma con `join(',')` sin escape completo. No afirmar que ya se auditó el guardado por navegador.
- On-chain y Laboratorio: validar todas las APIs, números reales, comparación y simulador, y estados sin datos; marcar “próximamente” lo no disponible en vez de fingir resultados.
- Noticias: comprobar respuestas RSS reales CoinDesk/Cointelegraph, fuentes/horas/enlaces. Se cambió sólo el mensaje de fallo total sin caché. Hay otros estados vacíos que todavía pueden decir que las fuentes responden sin comprobarlo. Brio se deja sin publicación ni nueva clave.
- Cartera: volver a probar mercado/límite/cancelación/cierre, P/L, curva, CSV, calculadora USD/MXN sin falsa conversión y fallos de conexión, con cuenta temporal. En LAN está bloqueada por el Origin descrito arriba.
- Ajustes: tema/ayuda ya cerrados y persistencia verificada en un mismo origen. `localStorage` pertenece a navegador+origen: teléfono y PC NO comparten preferencias automáticamente. Si falla el almacenamiento, el código aún silencia el error; no prometer persistencia en ese entorno.
- Estados globales: `pedir()` general todavía no tiene timeout universal y el arranque depende del CDN de gráficos. Revisar pantallas vacías, guiones sin explicación y “Cargando…” ante caída real de red. El límite de 15 segundos agregado es de indicadores, no de toda la app.
- Reporte unificado CSV P/L + operaciones + peor caída: **NO agregado**. Existen exportaciones previas por vista; decidir si alcanza hoy o dejarlo explícito para después.

### Entrega final para reunión, aún pendiente

Actualizar README/PLAN con guía PC y teléfono realmente probada, estado funcional/pendiente y guion de 2 minutos:

1. Panel: “Lee datos públicos y explica el estado del mercado; no predice ganancias”.
2. Gráfico: “Estas son velas reales e indicadores; las acciones son de práctica”.
3. Cartera: “El dinero es ficticio; se registran comisiones, ganancias y pérdidas”.
4. El bot: “S11 es una regla con ventaja histórica medida, no garantía futura; sigue en papel”.

No prometer ganancias, operación continua, pruebas físicas que no se hicieron, publicación ni conexión real de exchanges/pagos. La inversión futura tampoco autoriza por sí sola retirar el candado: requiere otra decisión explícita.

## 7. Prompt breve para el próximo agente

> Continuá Helios DEMO leyendo primero RELEVO-DEMO-CLIENTE.md. El árbol /Users/jairon/HeliosShare ya está en demo-cliente, creado desde 696dc34, con el relevo autorizado para GitHub: comprobá el commit y cualquier cambio local posterior antes de actuar. NO vuelvas a master, no hagas pull/reset/clean a ciegas ni apliques stash@{0}. Hay 177 regresiones OK y 79 comprobaciones aisladas del relevo; no es demo terminada. D1, preferencias y lectura del cuaderno tienen un punto probado. Empezá por F4: Cartera por Origin LAN da 403; resolvelo conservando seguridad/orígenes locales, sin publicar a internet. Después F3 teléfono físico y H auditoría completa de 9 vistas con datos reales. Respetá SOLO_PRUEBA=True, no toques secretos/cuentas reales, no inicies ensayo de 30 días ni D2/D5/E2/E4/G. Comprobá el servidor: al relevo no había nada escuchando en 8765. Repetí las pruebas y actualizá README/PLAN con acceso PC/teléfono y guion de demo antes de dar por terminado. No afirmes pruebas ni funciones que no verificaste.
