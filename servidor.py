import json, csv, io, os, time, urllib.parse, urllib.request, webbrowser, threading, sys, socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# En una PC normal el panel sólo se ve en 127.0.0.1:8765. En un hosting real la
# plataforma asigna un puerto y espera que escuche en todas las interfaces, así
# que se toma PORT del entorno y, si existe, se escucha en 0.0.0.0.
EN_HOSTING = bool(os.environ.get("PORT"))
PUERTO = int(os.environ.get("PORT") or os.environ.get("HELIOS_PORT") or 8765)
# Por defecto el panel sólo se ve en esta PC (127.0.0.1). Para abrirlo desde un
# teléfono en la MISMA WiFi, arrancar con HELIOS_HOST=0.0.0.0 (sólo red local;
# nunca abrir el puerto 8765 en el router ni publicarlo a internet).
HOST = os.environ.get("HELIOS_HOST", "0.0.0.0" if EN_HOSTING else "127.0.0.1")
RAIZ = os.path.dirname(os.path.abspath(__file__))
RUTA_CUADERNO = os.path.join(RAIZ, "cuaderno.csv")
MAX_CUERPO_BRIO = 512 * 1024   # tope del POST de noticias: un lote de 50 noticias sobra

# Para poder usar los modulos del bot (asistente, noticias) como biblioteca
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot")))

BINANCE = "https://api.binance.com"
FUTUROS = "https://fapi.binance.com"
# api.binance.com responde 451 desde direcciones de EE.UU. (donde está, por
# ejemplo, el servidor de Virginia). Este espejo oficial de solo-datos-publicos
# sirve lo mismo y no bloquea: es el plan B automático de pedir().
ESPEJO = "https://data-api.binance.vision"
GECKO = "https://api.coingecko.com"
MIEDO = "https://api.alternative.me/fng/?limit=1"
LLAMA = "https://api.llama.fi"
LLAMA_ESTABLES = "https://stablecoins.llama.fi/stablecoins?includePrices=false"
RED = "https://mempool.space/api"
USER_AGENT = "HeliosPanel/0.1 (uso personal; sin clave de API)"

CACHE = {}
CACHE_SEG = {"mercados": 90, "velas": 45, "libro": 8, "extra": 15, "mundo": 300,
             "cinta": 10, "chispas": 120, "cadenas": 300, "protocolos": 21600,
             "estables": 3600, "tendencia": 300, "exchanges": 3600, "red": 60,
             "derivados": 900}
BLOQUEO = threading.Lock()


def pedir(url, clave, segundos):
    ahora = time.time()
    with BLOQUEO:
        guardado = CACHE.get(clave)
        if guardado and ahora - guardado[0] < segundos:
            return guardado[1], "cache"
    datos, estado = _traer_json(url)
    if datos is None and BINANCE in url:
        # Binance bloquea las direcciones de servidores de EE.UU. (error 451).
        # Su espejo público de datos NO bloquea y sirve exactamente lo mismo.
        # Se prueba siempre que el principal falle, aunque haya una copia vieja:
        # si no, en el hosting la copia vieja no se renovaría nunca.
        datos, estado = _traer_json(url.replace(BINANCE, ESPEJO))
        if datos is not None:
            estado = "espejo"
    if datos is None:
        with BLOQUEO:
            guardado = CACHE.get(clave)
        if guardado:
            return guardado[1], "viejo:" + tipo_de_error(estado)
        return None, estado
    with BLOQUEO:
        CACHE[clave] = (ahora, datos)
    return datos, estado


def tipo_de_error(estado):
    return estado.replace("error:", "") if estado else "desconocido"


def _traer_json(url):
    peticion = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(peticion, timeout=20) as respuesta:
            return json.loads(respuesta.read().decode("utf-8")), "ok"
    except Exception as error:
        return None, "error:" + type(error).__name__


ASISTENTE_CACHE = {}
ASISTENTE_SEG = 120
CAPITAL_ASISTENTE = 1000.0


def asistente_actual(simbolo="BTCUSDT", capital=None):
    """Corre el asistente para el mercado que el panel esta mostrando.

    Antes solo sabia Bitcoin: si uno miraba Ethereum, el texto de "cuanto podes
    perder si entras ahora" hablaba de otra moneda. Cada mercado se calcula una
    vez cada 2 minutos, y el capital no cambia el analisis: solo la cuenta.
    """
    global CAPITAL_ASISTENTE
    if capital:
        try:
            CAPITAL_ASISTENTE = float(capital)
        except (TypeError, ValueError):
            pass
    clave = simbolo.upper()
    ahora = time.time()
    with BLOQUEO:
        guardado = ASISTENTE_CACHE.get(clave)
        if guardado and ahora - guardado[1] < ASISTENTE_SEG:
            return guardado[0]
    try:
        if "bot" not in sys.path:
            sys.path.insert(0, os.path.abspath(os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "bot")))
        import asistente
        datos = asistente.analizar(clave, CAPITAL_ASISTENTE)
        with open(os.path.join(RAIZ, "bot", "asistente_estado.json"), "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        with BLOQUEO:
            ASISTENTE_CACHE[clave] = (datos, ahora)
        return datos
    except Exception:
        guardado = leer_json(os.path.join(RAIZ, "bot", "asistente_estado.json"))
        with BLOQUEO:
            ASISTENTE_CACHE[clave] = (guardado, ahora)
        return guardado


def leer_csv_generico(ruta_relativa, limite=400):
    try:
        with open(ruta_relativa, newline="", encoding="utf-8") as archivo:
            filas = list(csv.reader(archivo))
    except FileNotFoundError:
        return None
    if not filas:
        return None
    return {"cabecera": filas[0], "filas": filas[1:][-limite:][::-1],
            "total": max(0, len(filas) - 1)}


def varios(peticiones):
    """Dispara varias lecturas publicas en paralelo. Si una falla, las otras siguen."""
    salida = {}

    def uno(clave, url, segundos):
        try:
            datos, estado = pedir(url, clave, segundos)
            salida[clave] = {"estado": estado, "datos": datos}
        except Exception as error:
            salida[clave] = {"estado": "error:" + type(error).__name__, "datos": None}

    hilos = [threading.Thread(target=uno, args=a) for a in peticiones]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=25)
    return salida


def anotar(fila):
    nuevo = not __import__("os").path.exists(RUTA_CUADERNO)
    with open(RUTA_CUADERNO, "a", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        if nuevo:
            escritor.writerow([
                "fecha", "hora", "mercado", "precio", "tendencia", "agitacion",
                "fuerza", "rango24h", "coincidencias", "escenarios", "veredicto",
            ])
        escritor.writerow(fila)


def leer_cuaderno(limite=400):
    try:
        with open(RUTA_CUADERNO, "rb") as archivo:
            crudo = archivo.read()
    except FileNotFoundError:
        return []
    # Se toleran NUL al leer, sin reescribir el archivo. csv.reader debe
    # recibir el flujo completo para conservar campos entrecomillados multilínea.
    texto = crudo.replace(b"\x00", b"").decode("utf-8", errors="replace")
    filas = []
    lector = csv.reader(io.StringIO(texto, newline=""), strict=True)
    while True:
        try:
            fila = next(lector)
        except StopIteration:
            break
        except csv.Error:
            continue
        if fila and (not filas or len(fila) == len(filas[0])):
            filas.append(fila)
    if not filas:
        return []
    cabecera, cuerpo = filas[0], filas[1:]
    return {"cabecera": cabecera, "filas": cuerpo[-limite:][::-1]}


def leer_json(ruta_relativa):
    """Lee un producto del bot si existe. Si todavia no esta, devuelve None y el panel lo dice."""
    try:
        with open(ruta_relativa, encoding="utf-8") as archivo:
            return json.load(archivo)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


HISTORIAL_EN_MEMORIA = {}


def velas_locales(simbolo, intervalo):
    """Historial para el Laboratorio.

    Si el bot ya bajó las velas (33.000 en el disco), las usa: es instantáneo.
    En un hosting no están, así que se piden las últimas mil al exchange público.
    El panel no cambia: recibe las mismas columnas, sólo menos historia.
    """
    clave = simbolo + intervalo
    with BLOQUEO:
        if clave in HISTORIAL_EN_MEMORIA:
            return HISTORIAL_EN_MEMORIA[clave]
    ruta = os.path.join(RAIZ, "bot", "datos", f"{simbolo}_{intervalo}.csv")
    if not os.path.exists(ruta):
        return _velas_del_exchange(simbolo, intervalo, 1000)
    with open(ruta, newline="", encoding="utf-8") as archivo:
        filas = list(csv.reader(archivo))[1:]
    t, o, h, l, c, v = [], [], [], [], [], []
    for f in filas:
        if len(f) < 6:
            continue
        t.append(int(float(f[0])))
        o.append(float(f[1])); h.append(float(f[2]))
        l.append(float(f[3])); c.append(float(f[4])); v.append(float(f[5]))
    paquete = {"t": t, "open": o, "high": h, "low": l, "close": c, "volumen": v}
    with BLOQUEO:
        HISTORIAL_EN_MEMORIA[clave] = paquete
    return paquete


def _velas_del_exchange(simbolo, intervalo, limite=1000):
    """Plan B sin disco: pide velas públicas al exchange. Nunca claves."""
    clave = simbolo + intervalo + ":web"
    with BLOQUEO:
        guardado = HISTORIAL_EN_MEMORIA.get(clave)
        if guardado:
            return guardado[1]
    try:
        if not simbolo.replace("USDT", "").isalnum() or intervalo not in {
                "15m", "30m", "1h", "4h", "1d", "1w"}:
            return None
        url = (f"{BINANCE}/api/v3/klines?symbol={simbolo}"
               f"&interval={intervalo}&limit={int(limite)}")
        datos, _estado = pedir(url, "historial:" + clave, 60)
        if not isinstance(datos, list) or not datos:
            return None
        paquete = {"t": [int(k[0]) for k in datos],
                   "open": [float(k[1]) for k in datos],
                   "high": [float(k[2]) for k in datos],
                   "low": [float(k[3]) for k in datos],
                   "close": [float(k[4]) for k in datos],
                   "volumen": [float(k[5]) for k in datos],
                   "origen": "exchange"}
        with BLOQUEO:
            HISTORIAL_EN_MEMORIA[clave] = (time.time(), paquete)
        return paquete
    except Exception:
        return None


def recortar_protocolos(datos):
    if not isinstance(datos, list):
        return None
    orden = sorted(datos, key=lambda p: p.get("tvl") or 0, reverse=True)[:40]
    return [{"nombre": p.get("name"), "cadena": p.get("category"),
             "tvl": p.get("tvl"), "cambio1d": p.get("change_1d"),
             "sitio": (p.get("url") or "")[:60]} for p in orden]


def recortar_estables(datos):
    if not isinstance(datos, dict):
        return None
    filas = datos.get("peggedAssets") or []
    orden = sorted(filas, key=lambda s: (s.get("circulating") or {}).get("peggedUSD") or 0,
                   reverse=True)[:14]
    return [{"nombre": s.get("name"), "simbolo": s.get("symbol"),
             "circulando": (s.get("circulating") or {}).get("peggedUSD"),
             "mecanismo": s.get("pegMechanism"), "precio": s.get("price")} for s in orden]


BLOQUEO_CARTERA = threading.Lock()


def cartera_velas(sim):
    url = f"{BINANCE}/api/v3/klines?symbol={sim}&interval=1h&limit=120"
    datos, estado = pedir(url, "cartera:velas:" + sim, 10)
    if estado not in ("ok", "cache") or not isinstance(datos, list) or not datos:
        return []
    ahora = int(time.time() * 1000)
    try:
        salida = [{"t": int(k[0]), "o": float(k[1]), "h": float(k[2]),
                   "l": float(k[3]), "c": float(k[4]), "cerrada": int(k[6]) < ahora}
                  for k in datos]
        if int(datos[-1][6]) < ahora - 120000:
            return []
        import math
        if any(not math.isfinite(v[k]) or v[k] <= 0 for v in salida for k in ("o", "h", "l", "c")):
            return []
        return salida
    except (TypeError, ValueError, IndexError, KeyError):
        return []


def cartera_actual():
    import cartera
    with BLOQUEO_CARTERA:
        c = cartera.CarteraManual()
        precios, sin_precio = {}, []
        for sim, m in list(c.estado["mercados"].items()):
            if m.get("posicion") is not None:
                velas = cartera_velas(sim)
                if velas:
                    c.procesar(sim, velas, momento=int(time.time() * 1000))
                    precios[sim] = velas[-1]["c"]
                else:
                    sin_precio.append(sim)
        c.salvar()
        detalle = c.detalle(precios)
        detalle["sin_precio"] = sin_precio
        return detalle


class Atencion(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, objeto, codigo=200):
        cuerpo = json.dumps(objeto, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        ruta = urllib.parse.urlparse(self.path)
        parametros = urllib.parse.parse_qs(ruta.query)

        if ruta.path in ("/", "/panel", "/panel.html"):
            try:
                with open(os.path.join(RAIZ, "panel.html"), "rb") as archivo:
                    cuerpo = archivo.read()
            except FileNotFoundError:
                cuerpo = "<h1>Falta panel.html al lado de servidor.py</h1>".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
            return

        if ruta.path == "/api/mercados":
            url = (GECKO + "/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc"
                   "&per_page=250&page=1&sparkline=false&price_change_percentage=24h,7d")
            datos, estado = pedir(url, "mercados", CACHE_SEG["mercados"])
            return self._json({"estado": estado, "datos": datos})

        if ruta.path == "/api/velas":
            simbolo = (parametros.get("simbolo") or ["BTCUSDT"])[0].upper()
            intervalo = (parametros.get("intervalo") or ["1h"])[0]
            limite = min(int((parametros.get("limite") or ["400"])[0]), 1000)
            if not (simbolo.replace("USDT", "").isalnum() and intervalo in
                    {"15m", "30m", "1h", "4h", "1d", "1w"}):
                return self._json({"estado": "rechazado", "datos": None}, 400)
            url = f"{BINANCE}/api/v3/klines?symbol={simbolo}&interval={intervalo}&limit={limite}"
            # el limite va en la clave: si no, un pedido de 5 velas deja cacheado
            # un grafico de 5 y el de 500 sale vacio durante 45 segundos
            datos, estado = pedir(url, "velas:" + simbolo + intervalo + ":" + str(limite),
                                  CACHE_SEG["velas"])
            return self._json({"estado": estado, "datos": datos})

        if ruta.path == "/api/libro":
            simbolo = (parametros.get("simbolo") or ["BTCUSDT"])[0].upper()
            if not simbolo.replace("USDT", "").isalnum():
                return self._json({"estado": "rechazado", "datos": None}, 400)
            url = f"{BINANCE}/api/v3/depth?symbol={simbolo}&limit=20"
            datos, estado = pedir(url, "libro:" + simbolo, CACHE_SEG["libro"])
            return self._json({"estado": estado, "datos": datos})

        if ruta.path == "/api/extra":
            simbolo = (parametros.get("simbolo") or ["BTCUSDT"])[0].upper()
            if not simbolo.replace("USDT", "").isalnum():
                return self._json({"estado": "rechazado", "datos": None}, 400)
            paquete = varios([
                ("ticker", f"{BINANCE}/api/v3/ticker/24hr?symbol={simbolo}", CACHE_SEG["extra"]),
                ("funding", f"{FUTUROS}/fapi/v1/premiumIndex?symbol={simbolo}", CACHE_SEG["extra"]),
                ("interes", f"{FUTUROS}/fapi/v1/openInterest?symbol={simbolo}", CACHE_SEG["extra"]),
                ("largo_corto", f"{FUTUROS}/futures/data/globalLongShortAccountRatio?symbol={simbolo}&period=1h&limit=48", CACHE_SEG["extra"]),
                ("flujo", f"{FUTUROS}/futures/data/takerlongshortRatio?symbol={simbolo}&period=1h&limit=48", CACHE_SEG["extra"]),
                ("operaciones", f"{BINANCE}/api/v3/aggTrades?symbol={simbolo}&limit=45", 3),
            ])
            return self._json({"estado": "ok", "datos": paquete})

        if ruta.path == "/api/mundo":
            paquete = varios([
                ("global", GECKO + "/api/v3/global", CACHE_SEG["mundo"]),
                ("miedo", MIEDO, CACHE_SEG["mundo"]),
            ])
            return self._json({"estado": "ok", "datos": paquete})

        if ruta.path == "/api/asistente":
            sim = (parametros.get("simbolo") or ["BTCUSDT"])[0].upper()
            cap = (parametros.get("capital") or [""])[0]
            if not sim.replace("USDT", "").isalnum():
                return self._json({"estado": "rechazado", "datos": None}, 400)
            return self._json({"estado": "ok", "datos": asistente_actual(sim, cap)})

        if ruta.path == "/api/cinta":
            url = (GECKO + "/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc"
                   "&per_page=40&page=1&sparkline=false&price_change_percentage=1h,24h,7d")
            datos, estado = pedir(url, "cinta", CACHE_SEG["cinta"])
            return self._json({"estado": estado, "datos": datos})

        if ruta.path == "/api/chispas":
            url = (GECKO + "/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc"
                   "&per_page=60&page=1&sparkline=true&price_change_percentage=1h,24h,7d")
            datos, estado = pedir(url, "chispas", CACHE_SEG["chispas"])
            return self._json({"estado": estado, "datos": datos})

        if ruta.path == "/api/cadenas":
            datos, estado = pedir(LLAMA + "/v2/chains", "cadenas", CACHE_SEG["cadenas"])
            if isinstance(datos, list):
                datos = sorted(datos, key=lambda c: c.get("tvl") or 0, reverse=True)[:16]
            return self._json({"estado": estado, "datos": datos})

        if ruta.path == "/api/protocolos":
            datos, estado = pedir(LLAMA + "/protocols", "protocolos", CACHE_SEG["protocolos"])
            return self._json({"estado": estado, "datos": recortar_protocolos(datos)})

        if ruta.path == "/api/estables":
            datos, estado = pedir(LLAMA_ESTABLES, "estables", CACHE_SEG["estables"])
            return self._json({"estado": estado, "datos": recortar_estables(datos)})

        if ruta.path == "/api/tendencia":
            datos, estado = pedir(GECKO + "/api/v3/search/trending", "tendencia", CACHE_SEG["tendencia"])
            if isinstance(datos, dict):
                datos = [{"nombre": c["item"].get("name"), "simbolo": c["item"].get("symbol"),
                          "puesto": n + 1,
                          "rango": c["item"].get("market_cap_rank"),
                          "precio": (c["item"].get("data") or {}).get("price"),
                          "capital": (c["item"].get("data") or {}).get("market_cap"),
                          "var24h": ((c["item"].get("data") or {}).get("price_change_percentage_24h") or {}).get("usd")}
                         for n, c in enumerate((datos.get("coins") or [])[:12])]
            return self._json({"estado": estado, "datos": datos})

        if ruta.path == "/api/exchanges":
            datos, estado = pedir(GECKO + "/api/v3/exchanges?per_page=15&page=1",
                                  "exchanges", CACHE_SEG["exchanges"])
            if isinstance(datos, list):
                datos = sorted(datos, key=lambda e: (e.get("trade_volume_24h_btc") or 0),
                               reverse=True)[:15]
            return self._json({"estado": estado, "datos": datos})

        if ruta.path == "/api/red":
            paquete = varios([
                ("comisiones", RED + "/v1/fees/recommended", CACHE_SEG["red"]),
                ("cola", RED + "/mempool", CACHE_SEG["red"]),
                ("potencia", RED + "/v1/mining/hashrate/3d", CACHE_SEG["red"]),
            ])
            return self._json({"estado": "ok", "datos": paquete})

        if ruta.path == "/api/derivados":
            simbolo = (parametros.get("simbolo") or ["BTCUSDT"])[0].upper()
            if not simbolo.replace("USDT", "").isalnum():
                return self._json({"estado": "rechazado", "datos": None}, 400)
            paquete = varios([
                ("interes_historico", f"{FUTUROS}/futures/data/openInterestHist?symbol={simbolo}&period=1d&limit=30", CACHE_SEG["derivados"]),
                ("grandes", f"{FUTUROS}/futures/data/topLongShortPositionRatio?symbol={simbolo}&period=1d&limit=30", CACHE_SEG["derivados"]),
            ])
            return self._json({"estado": "ok", "datos": paquete})

        if ruta.path == "/api/indicadores":
            simbolo = (parametros.get("simbolo") or ["BTCUSDT"])[0].upper()
            intervalo = (parametros.get("intervalo") or ["1h"])[0]
            if not (simbolo.replace("USDT", "").isalnum() and intervalo in
                    {"15m", "30m", "1h", "4h", "1d", "1w"}):
                return self._json({"estado": "rechazado", "datos": None}, 400)
            url = f"{BINANCE}/api/v3/klines?symbol={simbolo}&interval={intervalo}&limit=500"
            datos, estado = pedir(url, "velas:" + simbolo + intervalo + ":500",
                                  CACHE_SEG["velas"])
            if not isinstance(datos, list) or not datos:
                return self._json({"estado": estado, "datos": None})
            try:
                import indicadores
                velas = [{"t": int(k[0]) // 1000, "o": float(k[1]), "h": float(k[2]),
                          "l": float(k[3]), "c": float(k[4]), "v": float(k[5])} for k in datos]
                return self._json({"estado": estado, "datos": indicadores.calcular(velas)})
            except Exception as error:
                return self._json({"estado": "error:" + type(error).__name__, "datos": None})

        if ruta.path == "/api/historial":
            simbolo = (parametros.get("simbolo") or ["BTCUSDT"])[0].upper()
            intervalo = (parametros.get("intervalo") or ["1h"])[0]
            if not (simbolo.replace("USDT", "").isalnum()
                    and intervalo in {"15m", "30m", "1h", "4h", "1d", "1w"}):
                return self._json({"estado": "rechazado", "datos": None}, 400)
            datos = velas_locales(simbolo, intervalo)
            if datos is None:
                return self._json({"estado": "no_descargado", "datos": None})
            return self._json({"estado": "ok", "datos": datos})

        if ruta.path == "/api/cerebro":
            return self._json({"estado": "ok", "datos": leer_json(os.path.join(RAIZ, "bot", "estado_cerebro.json"))})

        if ruta.path == "/api/cartera":
            try:
                return self._json({"estado": "ok", "datos": cartera_actual()})
            except Exception as error:
                return self._json({"estado": "error:" + type(error).__name__, "datos": None})

        if ruta.path == "/api/puntaje":
            h = (parametros.get("horizonte") or ["24"])[0]
            h = h if h in ("1", "24") else "24"
            return self._json({"estado": "ok",
                               "datos": leer_json(os.path.join(RAIZ, "bot", "resultados", f"scorecard_h{h}.json"))})

        if ruta.path == "/api/cuaderno":
            return self._json({"estado": "ok", "datos": leer_cuaderno()})

        if ruta.path == "/api/ventaja":
            return self._json({"estado": "ok",
                               "datos": leer_json(os.path.join(RAIZ, "bot", "resultados", "ventaja.json"))})

        if ruta.path == "/api/decisiones":
            return self._json({"estado": "ok",
                               "datos": leer_csv_generico(os.path.join(RAIZ, "bot", "decisiones.csv"))})

        if ruta.path == "/api/miedo_hist":
            datos, estado = pedir("https://api.alternative.me/fng/?limit=90",
                                  "miedo_hist", CACHE_SEG["mundo"])
            if isinstance(datos, dict):
                datos = [{"valor": int(d["value"]), "texto": d["value_classification"],
                          "dia": int(d["timestamp"])} for d in (datos.get("data") or [])]
            return self._json({"estado": estado, "datos": datos})

        if ruta.path == "/api/noticias":
            import noticias
            refrescar = (parametros.get("refrescar") or [""])[0] == "1"
            return self._json({"estado": "ok", "datos": noticias.traer(force=refrescar)})

        return self._json({"estado": "no_existe"}, 404)

    def do_POST(self):
        camino = urllib.parse.urlparse(self.path).path
        if camino == "/api/noticias/recibir":
            return self._recibir_brio()
        if camino == "/api/bot/apagar":
            if self._post_rechazado():
                return
            return self._bot_interruptor(True)
        if camino == "/api/bot/prender":
            if self._post_rechazado():
                return
            return self._bot_interruptor(False)
        if camino in ("/api/cartera/orden", "/api/cartera/cerrar"):
            return self._cartera_post(camino)
        if camino != "/api/cuaderno":
            return self._json({"estado": "no_existe"}, 404)
        if self._post_rechazado():
            return
        if self.headers.get_content_type() != "application/json":
            return self._json({"estado": "se_requiere_json"}, 415)
        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            largo = -1
        if largo < 0 or largo > 64 * 1024:
            return self._json({"estado": "cuerpo_grande"}, 413)
        try:
            cuerpo = json.loads(self.rfile.read(largo).decode("utf-8"))
            fila = [str(cuerpo.get(k, ""))[:64] for k in
                    ("fecha", "hora", "mercado", "precio", "tendencia", "agitacion",
                     "fuerza", "rango24h", "coincidencias", "escenarios", "veredicto")]
        except Exception:
            return self._json({"estado": "cuerpo_invalido"}, 400)
        anotar(fila)
        return self._json({"estado": "anotado"})

    def _recibir_brio(self):
        """Puerta de entrada de Brio. Direccion Brio -> App: aca solo se recibe.

        Sin clave, con clave equivocada o sin clave configurada en bot/noticias.json
        responde 401 y no guarda nada. El boton "Actualizar noticias" del panel
        nunca pasa por aca: ese boton lee lo guardado o busca por RSS.
        """
        import noticias
        cabecera = self.headers.get("Authorization") or ""
        token = cabecera[7:].strip() if cabecera[:7].lower() == "bearer " else ""
        if not noticias.token_brio_valido(token):
            return self._json({"ok": False, "estado": "no_autorizado",
                               "detalle": "Falta la clave o no coincide. No se guardó nada."}, 401)
        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            largo = -1
        if largo < 0 or largo > MAX_CUERPO_BRIO:
            return self._json({"ok": False, "estado": "cuerpo_grande",
                               "detalle": f"El máximo es {MAX_CUERPO_BRIO} bytes."}, 413)
        try:
            cuerpo = json.loads(self.rfile.read(largo).decode("utf-8"))
        except Exception:
            return self._json({"ok": False, "estado": "cuerpo_invalido"}, 400)
        recibidas, nuevas, errores = noticias.recibir_brio(cuerpo)
        if not recibidas and errores:
            return self._json({"ok": False, "estado": "nada_valido",
                               "recibidas": 0, "nuevas": 0, "errores": errores}, 400)
        salida = {"ok": True, "recibidas": recibidas, "nuevas": nuevas}
        if errores:
            salida["errores"] = errores
        return self._json(salida)

    def _post_rechazado(self):
        """Freno de origen para los POST del panel (Brio no pasa por acá: usa clave).

        El Host tiene que ser loopback o un nombre/IP de este equipo: un dominio
        ajeno apuntado a nuestra IP (DNS rebinding) queda rechazado. Si el
        navegador manda Origin, debe ser exactamente el http://Host:puerto con el
        que abrió el panel; una página de otro sitio no puede ordenar, cerrar,
        anotar ni tocar el bot. Sin Origin (curl, scripts de prueba) se deja pasar
        porque el Host ya es local y un navegador ajeno siempre manda Origin.
        """
        host = self.headers.get("Host") or ""
        nombre = urllib.parse.urlsplit("http://" + host).hostname or ""
        if nombre not in hosts_locales():
            self._json({"estado": "host_rechazado"}, 403)
            return True
        origen = self.headers.get("Origin")
        if origen and origen != "http://" + host:
            self._json({"estado": "origen_rechazado"}, 403)
            return True
        return False

    def _bot_interruptor(self, apagar):
        """Boton de parada del panel: escribe o borra el archivo APAGADO que el
        bot ya chequea (exchange.apachado). Es solo papel: SOLO_PRUEBA sigue en
        True, asi que prender nunca habilita dinero real. El POST pasa por el
        freno de origen local (_post_rechazado).
        """
        import exchange
        ruta = exchange.RUTA_APAGADO
        if apagar:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("Parado desde el panel el %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
            return self._json({"estado": "ok", "apagado": True})
        if os.path.exists(ruta):
            os.remove(ruta)
        return self._json({"estado": "ok", "apagado": False})

    def _cartera_post(self, camino):
        """Ordenes en papel (C1). POST del panel local o LAN, plata falsa, precios reales.
        Valida origen, moneda y cuerpo; nunca toca dinero real (SOLO_PRUEBA sigue True)."""
        import cartera
        if self._post_rechazado():
            return
        if self.headers.get_content_type() != "application/json":
            return self._json({"estado": "se_requiere_json"}, 415)
        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            largo = -1
        if largo < 0 or largo > 64 * 1024:
            return self._json({"estado": "cuerpo_grande"}, 413)
        try:
            cuerpo = json.loads(self.rfile.read(largo).decode("utf-8"))
        except Exception:
            return self._json({"estado": "cuerpo_invalido"}, 400)
        if not isinstance(cuerpo, dict):
            return self._json({"estado": "cuerpo_invalido"}, 400)
        sim = str(cuerpo.get("simbolo") or "").upper()
        if sim not in cartera.SIMBOLOS:
            return self._json({"estado": "rechazado", "detalle": "moneda no permitida"}, 400)
        try:
            with BLOQUEO_CARTERA:
                c = cartera.CarteraManual()
                pos = c.estado["mercados"].get(sim, {}).get("posicion")
                cancelar = camino == "/api/cartera/cerrar" and pos and not pos.get("llena", True)
                velas = [] if cancelar else cartera_velas(sim)
                if not velas and not cancelar:
                    return self._json({"estado": "error", "detalle": "No hay cotización reciente; no se cambió la cuenta."}, 502)
                momento = int(time.time() * 1000)
                if camino == "/api/cartera/orden":
                    ok, det = c.colocar_orden(sim, velas, cuerpo, momento=momento)
                else:
                    ok, det = c.cerrar(sim, velas, momento=momento)
                if not ok:
                    return self._json({"estado": "rechazado", "detalle": det}, 400)
                c.salvar()
        except (ValueError, OSError):
            return self._json({"estado": "error", "detalle": "No se pudo leer o guardar la cuenta. Revisá el archivo antes de reintentar."}, 500)
        return self._json({"estado": "ok", "detalle": det})


def calentar_noticias():
    """Deja las noticias cargadas antes del primer pedido del panel."""
    try:
        import noticias
        noticias.traer()
    except Exception:
        pass


def ip_local():
    """IPv4 de la red local sin enviar tráfico: el connect UDP sólo elige ruta."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))   # no manda ningún paquete
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return "127.0.0.1"


def hosts_locales():
    """Nombres e IP con los que este equipo puede servir el panel (loopback y LAN).

    Se recalcula en cada POST porque la IP puede cambiar al reconectar la WiFi.
    Sólo entran direcciones del propio equipo; un Host de dominio ajeno no entra.
    """
    nombres = {"127.0.0.1", "localhost", "::1"}
    try:
        equipo = socket.gethostname()
        nombres.add(equipo.lower())
        for _, _, _, _, direccion in socket.getaddrinfo(equipo, None):
            nombres.add(direccion[0].lower())
    except OSError:
        pass
    nombres.add(ip_local().lower())
    if HOST not in ("0.0.0.0", "::", ""):
        nombres.add(HOST.lower())
    return nombres


def main():
    servidor = ThreadingHTTPServer((HOST, PUERTO), Atencion)
    direccion = f"http://127.0.0.1:{PUERTO}/"
    print("Helios panel andando en", direccion)
    if HOST not in ("127.0.0.1", "localhost"):
        print("Para el teléfono en la misma WiFi:", f"http://{ip_local()}:{PUERTO}/")
        print("(sólo red local; no abrir el puerto en el router ni publicarlo)")
    print("Cuaderno en:", RUTA_CUADERNO, "(se abre con el Bloc de notas)")
    print("Ctrl+C o cerrar esta ventana para parar.")
    threading.Thread(target=calentar_noticias, daemon=True).start()
    if not EN_HOSTING:
        # en un hosting no hay navegador que abrir, y abrirlo rompe el arranque
        threading.Timer(1.2, lambda: webbrowser.open(direccion)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
