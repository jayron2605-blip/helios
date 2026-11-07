import json, csv, os, time, urllib.parse, urllib.request, webbrowser, threading, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PUERTO = 8765
RUTA_CUADERNO = "cuaderno.csv"

# Para poder usar los modulos del bot (asistente, noticias) como biblioteca
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot")))

BINANCE = "https://api.binance.com"
FUTUROS = "https://fapi.binance.com"
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
    peticion = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(peticion, timeout=20) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except Exception as error:
        with BLOQUEO:
            guardado = CACHE.get(clave)
        if guardado:
            return guardado[1], "stale:" + type(error).__name__
        return None, "error:" + type(error).__name__
    with BLOQUEO:
        CACHE[clave] = (ahora, datos)
    return datos, "ok"


ASISTENTE_CACHE = {"momento": 0, "datos": None}
ASISTENTE_SEG = 120


def asistente_actual():
    """Corre el asistente como mucho cada 2 minutos. Si falla, sirve el ultimo guardado."""
    ahora = time.time()
    with BLOQUEO:
        if ASISTENTE_CACHE["datos"] and ahora - ASISTENTE_CACHE["momento"] < ASISTENTE_SEG:
            return ASISTENTE_CACHE["datos"]
    try:
        if "bot" not in sys.path:
            sys.path.insert(0, "bot")
        import asistente
        datos = asistente.analizar()
        with open(os.path.join("bot", "asistente_estado.json"), "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        with BLOQUEO:
            ASISTENTE_CACHE["datos"] = datos
            ASISTENTE_CACHE["momento"] = ahora
        return datos
    except Exception:
        guardado = leer_json("bot/asistente_estado.json")
        with BLOQUEO:
            ASISTENTE_CACHE["datos"] = guardado
            ASISTENTE_CACHE["momento"] = ahora
        return guardado


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
        with open(RUTA_CUADERNO, newline="", encoding="utf-8") as archivo:
            filas = list(csv.reader(archivo))
    except FileNotFoundError:
        return []
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
    """Lee el historial que ya bajo el bot. No toca la red: 33.000 velas locales."""
    clave = simbolo + intervalo
    with BLOQUEO:
        if clave in HISTORIAL_EN_MEMORIA:
            return HISTORIAL_EN_MEMORIA[clave]
    ruta = os.path.join("bot", "datos", f"{simbolo}_{intervalo}.csv")
    if not os.path.exists(ruta):
        return None
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
                with open("panel.html", "rb") as archivo:
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
            datos, estado = pedir(url, "velas:" + simbolo + intervalo, CACHE_SEG["velas"])
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
            return self._json({"estado": "ok", "datos": asistente_actual()})

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
            return self._json({"estado": "ok", "datos": leer_json("bot/estado_cerebro.json")})

        if ruta.path == "/api/puntaje":
            h = (parametros.get("horizonte") or ["24"])[0]
            h = h if h in ("1", "24") else "24"
            return self._json({"estado": "ok",
                               "datos": leer_json(f"bot/resultados/scorecard_h{h}.json")})

        if ruta.path == "/api/cuaderno":
            return self._json({"estado": "ok", "datos": leer_cuaderno()})

        if ruta.path == "/api/noticias":
            import noticias
            refrescar = (parametros.get("refrescar") or [""])[0] == "1"
            return self._json({"estado": "ok", "datos": noticias.traer(force=refrescar)})

        return self._json({"estado": "no_existe"}, 404)

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != "/api/cuaderno":
            return self._json({"estado": "no_existe"}, 404)
        largo = int(self.headers.get("Content-Length") or 0)
        try:
            cuerpo = json.loads(self.rfile.read(largo).decode("utf-8"))
            fila = [str(cuerpo.get(k, ""))[:64] for k in
                    ("fecha", "hora", "mercado", "precio", "tendencia", "agitacion",
                     "fuerza", "rango24h", "coincidencias", "escenarios", "veredicto")]
        except Exception:
            return self._json({"estado": "cuerpo_invalido"}, 400)
        anotar(fila)
        return self._json({"estado": "anotado"})


def calentar_noticias():
    """Deja las noticias cargadas antes del primer pedido del panel."""
    try:
        import noticias
        noticias.traer()
    except Exception:
        pass


def main():
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Atencion)
    direccion = f"http://127.0.0.1:{PUERTO}/"
    print("Helios panel andando en", direccion)
    print("Cuaderno en:", RUTA_CUADERNO, "(se abre con el Bloc de notas)")
    print("Ctrl+C o cerrar esta ventana para parar.")
    threading.Thread(target=calentar_noticias, daemon=True).start()
    threading.Timer(1.2, lambda: webbrowser.open(direccion)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
