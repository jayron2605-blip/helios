# ENTREGA-DEMO.md — Helios demo para el cliente

Fecha: **2026-11-08**. Rama: `demo-cliente` (base `696dc34`, relevo `ab8d3ed` + este trabajo).
Leer junto con `RELEVO-DEMO-CLIENTE.md` (punto de pausa) y `README.md` (guía de uso y LAN).

**La demo sirve para enseñar, no para prometer.** Este documento dice qué quedó funcional,
qué queda pendiente para después de la inversión y qué NO se debe decir al cliente.

## 1. Qué se verificó en esta tanda (sin exagerar)

- `python bot/pruebas.py`: **177 OK / TODO OK** (Windows, Python 3.14), después de cada bloque.
- **F4 (21 comprobaciones aisladas):** servidor de prueba con cuenta/APAGADO/cuaderno
  temporales; POST de cuaderno, bot y cartera por **IP LAN real** aceptados con Origin local;
  Origin ajeno y Host de dominio ajeno (DNS rebinding) → 403 sin escribir; Brio sin clave → 401;
  archivos del dueño intactos (comparación de mtime/tamaño).
- **H (72 comprobaciones, Chromium emulado 360/390/1440 + contexto sin CDN):** mercados/velas/
  on-chain/lab con datos públicos reales; cuaderno con filas con comas/quotes/multilínea;
  CSV exportado con escape correcto; Anotar anuncia éxito **sólo** tras confirmar HTTP y avisa
  si falla; favoritos y comparador; estado del bot real; cartera UI coloca y cierra orden en
  papel con cuenta temporal; sin CDN el panel vive, explica y el Lab calcula números;
  noticias con estados vacíos honestos según fuentes.
- **RSS reales:** `noticias.traer(force=True)` con caché temporal: CoinDesk ok (25),
  Cointelegraph ok (30), Decrypt ok (39); títulos/enlaces reales; horas de publicación parseadas.
- Sintaxis JS (`node --check`) y llaves CSS balanceadas tras los cambios.

**Lo que NO es esta verificación:** no es un teléfono físico (F3 sigue pendiente, necesita al
dueño); no es `verificar_relevo.py` (79) corrido en Windows: sus pines de `requirements.txt`
son de Mac/Python 3.9.6 y esta PC tiene 3.14 con otras versiones; esa suite debe correrse en la
Mac del dueño. No se instalaron paquetes a ciegas ni se falsearon pines.

## 2. Qué quedó funcional (por vista)

1. **Panel:** asistente que habla de la moneda mirada, precios reales, favoritos ★ locales,
   comparador de tres monedas, "Sólo favoritos".
2. **Gráfico:** velas Binance reales; EMAs, RSI, MACD, Bollinger, ADX, VWAP (ta real);
   escenarios; intervalos en una fila a 360/390; Comprar/Vender ahora dicen que abren la
   Cartera de práctica (antes parecían órdenes reales).
3. **El bot:** estado con punto+palabra, PARAR/Reanudar (archivo APAGADO), scorecard honesto
   de S11 y del modelo que perdió. Ensayo de 30 días **no iniciado**.
4. **Cuaderno:** lectura tolerante a NUL sin reescribir el archivo del dueño; Anotar con
   confirmación real; export CSV con escape completo.
5. **On-chain:** TVL por cadena/protocolo, stablecoins, red Bitcoin, exchanges, tendencia,
   miedo/codicia; números públicos reales.
6. **Laboratorio:** backtest contra velas locales y simulador "qué hubiera pasado"; funciona
   incluso sin CDN (números sí, curva no, y lo dice).
7. **Noticias:** RSS reales con fuente/hora/enlace y precio de la hora siguiente; puerta Brio
   con clave (sin clave 401); estados vacíos no mienten sobre las fuentes.
8. **Cartera:** USD 1.000 ficticios por moneda; mercado/límite, stop, objetivos, trailing;
   P/L, curva, historial con canceladas, CSV, calculadora USD/MXN sin falsa conversión;
   POST protegidos por origen local (loopback o LAN del propio equipo).
9. **Ajustes:** tema y "Para qué sirve" persistidos por navegador+origen (teléfono y PC no
   comparten preferencias); ayuda en español simple.

Global: banner **"Modo demo — dinero falso"** visible; timeout universal de 20 s en los
pedidos del navegador; sin CDN de gráficos el panel no muere; `SOLO_PRUEBA = True` intacto.

## 3. Pendiente (para después de la inversión, o con decisión del dueño)

- **F3 teléfono físico:** recorrido de las 9 vistas con toque real, registrando dispositivo,
  navegador y tamaño. Bloqueante para dar la demo por lista. Necesita al dueño.
- **`verificar_relevo.py` (79)** en la Mac (pines/Playwright de allá).
- **H1 reporte unificado** (P/L + operaciones + peor caída): NO agregado; hay exportaciones
  por vista. Queda explícito, no se fingió.
- **D2** multi-exchange ccxt, **D5** AI-CryptoTrader, **B3** ensayo 30 días, **E2/E4** internet
  y URL/clave Brio, **G** cuentas/planes/pagos, **Telegram** del canal: todo excluido hoy por
  decisión del dueño; cada uno requiere su autorización explícita.
- Firewall de Windows para LAN: sólo red privada y sólo si el dueño lo autoriza; no se tocó.

## 4. Qué NO prometer al cliente

- Ganancias ni rendimientos futuros: S11 es ventaja **histórica** medida (4/6 mercados,
  +69,2 % promedio en el tramo probado), con posible sesgo de selección (1 de 13 ideas pasó).
- Operación continua u órdenes alojadas en un exchange: la cartera se resuelve al consultar.
- Dinero real, retiros, cuentas o pagos: no existen en la demo; `SOLO_PRUEBA=True` es producto.
- Pruebas en teléfono físico que no se hicieron, publicación en internet, ni Brio conectado
  sin URL pública.
- Preferencias compartidas entre dispositivos: `localStorage` es por navegador+origen.

## 5. Cómo abrir la demo

- **PC:** `Abrir panel.bat` → http://127.0.0.1:8765/.
- **Teléfono (misma WiFi):** `Abrir panel LAN.bat` en la PC que corre el servidor; abrir la
  URL `http://<IP-de-esa-PC>:8765/` que imprime la terminal. Misma WiFi; firewall sólo red
  privada si el dueño autoriza; nunca router/túneles/internet. Detalle y seguridad en README.
- Parar: cerrar la ventana (Ctrl+C), no matar todos los Python.

## 6. Decisiones del dueño (respondidas el 2026-11-08)

1. **Commit y push en `demo-cliente`: AUTORIZADO.** Se commitea y se sube esta rama; master
   y el stash de D1+D2 no se tocan.
2. **Recorrido con teléfono físico (F3): el dueño lo hace hoy**, en la misma WiFi, con el
   servidor LAN prendido. Hasta que lo reporte, F3 sigue marcado FALTA/PARCIAL, no HECHO.
3. **`verificar_relevo.py` (79): queda pendiente, se corre en la Mac.** El script exige las
   versiones exactas de `requirements.txt` (instaladas en la Mac, no en esta PC Windows) y
   Playwright de Python con Chromium (acá no está). No se instalan versiones a ciegas ni se
   falsea el resultado. Comando en la Mac: `python3 verificar_relevo.py` desde la carpeta
   compartida (`/Users/jairon/HeliosShare`).
4. **Firewall sólo red privada: AUTORIZADO** si Windows lo pide al abrir el servidor LAN.
   Nada de router, túneles ni internet público.