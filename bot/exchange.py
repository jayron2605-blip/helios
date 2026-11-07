"""Cliente de exchange con frenos fisicos antes de tocar el mercado.

Nada de esto funciona sin un archivo claves.json al lado, que crea el dueno de
la cuenta. Mientras ese archivo no exista, o mientras exista el archivo
APAGADO, el bot NO manda ordenes: calcula, anota y muestra que hubiera hecho.

Los frenos se chequean aca, del lado del programa, antes de firmar nada:
  - tamano maximo por operacion (el monto se calcula con el precio real de la orden)
  - cantidad maxima de operaciones por dia
  - tope de perdida diaria (se actualiza con registrar_cierre() por cada operacion cerrada)
  - lista de mercados permitidos
  - interruptor de parada en el disco
"""
import hashlib, hmac, json, os, time, urllib.parse, urllib.error, urllib.request

RAIZ = os.path.abspath(os.path.dirname(__file__))
RUTA_CLAVES = os.path.join(RAIZ, "claves.json")
RUTA_APAGADO = os.path.join(RAIZ, "APAGADO")
RUTA_CONTADOR = os.path.join(RAIZ, "contador_dia.json")

PRODUCCION = "https://api.binance.com"
PRUEBAS = "https://testnet.binance.vision"

# CANDADO DE PRODUCTO. Helios es un asistente de prueba: no mueve dinero real nunca.
# Dejarlo en True es una decision del dueno del producto, no una configuracion.
# Con esto en True, comprar_mercado() y vender_mercado() se niegan siempre, aunque
# alguien cargue claves validas y apague el interruptor de simulacro.
SOLO_PRUEBA = True


class SinClaves(Exception):
    pass


class Freno(Exception):
    pass


class ModoSoloPrueba(Freno):
    pass


def hay_claves():
    return os.path.exists(RUTA_CLAVES)


def apachado():
    return os.path.exists(RUTA_APAGADO)


def cargar_config():
    if not hay_claves():
        raise SinClaves("Falta claves.json al lado de este programa. Sin eso el bot no opera.")
    with open(RUTA_CLAVES, encoding="utf-8") as f:
        c = json.load(f)
    for k in ("api_key", "api_secret"):
        if not c.get(k):
            raise SinClaves(f"claves.json no tiene {k}")
    c.setdefault("entorno", "pruebas")
    c.setdefault("solo_simulacro", True)
    c.setdefault("maximo_por_operacion_usd", 50)
    c.setdefault("maximo_operaciones_dia", 10)
    c.setdefault("tope_perdida_diaria_usd", 30)
    c.setdefault("mercados_permitidos", ["BTCUSDT", "ETHUSDT"])
    return c


class Exchange:
    puede_operar_de_verdad = not SOLO_PRUEBA
    modo = "PRUEBA FIJA" if SOLO_PRUEBA else "REAL"

    def __init__(self, cfg=None):
        self.cfg = cfg or {}
        # aunque alguien pida produccion, siempre habla con el entorno de prueba
        base = PRUEBAS if SOLO_PRUEBA else (
            PRUEBAS if self.cfg.get("entorno", "pruebas") == "pruebas" else PRODUCCION)
        self.base = base
        self.clave = self.cfg.get("api_key", "")
        self.secreto = self.cfg.get("api_secret", "")
        self._desfase_ms = None
        self.bitacora = []

    # ---------- utilidades ----------
    def _anotar(self, tipo, dato):
        self.bitacora.append({"t": int(time.time() * 1000), "tipo": tipo,
                              "dato": str(dato)[:300]})

    def _firma(self, consulta):
        return hmac.new(self.secreto.encode(), consulta.encode(), hashlib.sha256).hexdigest()

    def _marca(self):
        if self._desfase_ms is None:
            self._desfase_ms = self._hora_servidor() - int(time.time() * 1000)
        return int(time.time() * 1000) + self._desfase_ms

    def _hora_servidor(self):
        with urllib.request.urlopen(PRODUCCION + "/api/v3/time", timeout=15) as r:
            return json.loads(r.read())["serverTime"]

    def _get(self, ruta, params=None, firmado=False):
        params = dict(params or {})
        if firmado:
            params.update({"timestamp": self._marca(), "recvWindow": 5000})
        qs = urllib.parse.urlencode(params)
        url = self.base + ruta + ("?" + qs if qs else "")
        req = urllib.request.Request(url, headers={
            "User-Agent": "HeliosBot/1.0",
            **({"X-MBX-APIKEY": self.clave} if firmado else {})})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "ignore")
            self._anotar("error_http", f"{e.code} {ruta} {cuerpo}")
            raise

    def _post(self, ruta, params):
        params = dict(params)
        params.update({"timestamp": self._marca(), "recvWindow": 5000})
        qs = urllib.parse.urlencode(params)
        req = urllib.request.Request(self.base + ruta + "?" + qs + "&signature=" + self._firma(qs),
                                     method="POST", headers={"User-Agent": "HeliosBot/1.0",
                                                             "X-MBX-APIKEY": self.clave})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "ignore")
            self._anotar("error_http", f"{e.code} {ruta} {cuerpo}")
            raise

    # ---------- lectura ----------
    def velas(self, simbolo, intervalo="1h", limite=500):
        url = (PRODUCCION + f"/api/v3/klines?symbol={simbolo}&interval={intervalo}&limit={limite}")
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.loads(r.read())

    def saldo(self):
        return self._get("/api/v3/account", {}, firmado=True)

    def precio_actual(self, simbolo):
        """Precio del ultimo trato, publico, sin clave. Sirve para saber el monto real de una orden."""
        with urllib.request.urlopen(
                PRODUCCION + f"/api/v3/ticker/price?symbol={simbolo}", timeout=15) as r:
            return float(json.loads(r.read())["price"])

    # ---------- frenos ----------
    def _estado_dia(self):
        hoy = time.strftime("%Y-%m-%d")
        try:
            with open(RUTA_CONTADOR, encoding="utf-8") as f:
                c = json.load(f)
        except Exception:
            c = {}
        if c.get("dia") != hoy:
            c = {"dia": hoy, "operaciones": 0, "perdida_usd": 0.0}
        return c

    def _salvar_dia(self, c):
        with open(RUTA_CONTADOR, "w", encoding="utf-8") as f:
            json.dump(c, f, ensure_ascii=False)

    def revisar_frenos(self, simbolo, monto_usd):
        if apachado():
            raise Freno("Hay un archivo APAGADO en la carpeta: el bot no manda ordenes.")
        if not self.clave:
            raise Freno("Sin claves: no se puede operar.")
        if self.cfg.get("solo_simulacro", True):
            raise Freno("Esta en modo simulacro. Para operar en serio hay que apagar ese interruptor a mano.")
        c = self._estado_dia()
        if simbolo not in self.cfg.get("mercados_permitidos", []):
            raise Freno(f"{simbolo} no esta en la lista de mercados permitidos.")
        if monto_usd > self.cfg.get("maximo_por_operacion_usd", 0):
            raise Freno(f"{monto_usd:.2f} USD pasa el maximo por operacion "
                        f"({self.cfg['maximo_por_operacion_usd']} USD).")
        if c["operaciones"] >= self.cfg.get("maximo_operaciones_dia", 0):
            raise Freno(f"Ya se hicieron {c['operaciones']} operaciones hoy; el tope es "
                        f"{self.cfg['maximo_operaciones_dia']}.")
        if c["perdida_usd"] >= self.cfg.get("tope_perdida_diaria_usd", 0):
            raise Freno(f"Se toco el tope de perdida diaria ({c['perdida_usd']:.2f} USD). Se paro.")
        return c

    def _monto(self, simbolo, cantidad, precio=None):
        """Monto real de la orden, en USD. Sin precio confiable no hay orden: freno por seguridad."""
        if precio is not None:
            return cantidad * float(precio)
        p = self.precio_actual(simbolo)
        if not p:
            raise Freno("No se pudo leer el precio del mercado: sin ese dato no se firma una orden.")
        return cantidad * p

    def registrar_cierre(self, pnl_usd):
        """Anota una operacion cerrada. Si perdio plata, suma al contador del dia.

        El freno de perdida diaria solo sirve de algo si la perdida se escribe.
        Devuelve el estado del dia (por si el executor quiere registrar el freno que salto).
        """
        c = self._estado_dia()
        perdida = -float(pnl_usd) if pnl_usd else 0.0
        if perdida > 0:
            c["perdida_usd"] = round(c.get("perdida_usd", 0.0) + perdida, 2)
        self._salvar_dia(c)
        self._anotar("cierre", f"pnl={pnl_usd:.2f} perdida_dia={c['perdida_usd']:.2f}"
                     if pnl_usd else "cierre sin pnl")
        return c

    # ---------- escritura ----------
    def comprar_mercado(self, simbolo, cantidad, precio=None):
        if SOLO_PRUEBA:
            raise ModoSoloPrueba("Helios está en modo prueba fijo: no manda órdenes reales, nunca.")
        monto = self._monto(simbolo, cantidad, precio)
        c = self.revisar_frenos(simbolo, monto)
        orden = self._post("/api/v3/order", {
            "symbol": simbolo, "side": "BUY", "type": "MARKET", "quantity": f"{cantidad:.8f}"})
        c["operaciones"] += 1
        self._salvar_dia(c)
        self._anotar("orden", json.dumps(orden)[:300])
        return orden

    def vender_mercado(self, simbolo, cantidad, precio=None):
        if SOLO_PRUEBA:
            raise ModoSoloPrueba("Helios está en modo prueba fijo: no manda órdenes reales, nunca.")
        monto = self._monto(simbolo, cantidad, precio)
        c = self.revisar_frenos(simbolo, monto)
        orden = self._post("/api/v3/order", {
            "symbol": simbolo, "side": "SELL", "type": "MARKET", "quantity": f"{cantidad:.8f}"})
        c["operaciones"] += 1
        self._salvar_dia(c)
        self._anotar("orden", json.dumps(orden)[:300])
        return orden


def crear_claves_plantilla():
    """Escribe el molde. No inventa claves: el usuario pega las suyas."""
    ruta = os.path.join(RAIZ, "claves.EJEMPLO.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({
            "api_key": "PEGA_AQUI_TU_CLAVE",
            "api_secret": "PEGA_AQUI_TU_SECRETO",
            "entorno": "pruebas",
            "solo_simulacro": True,
            "maximo_por_operacion_usd": 50,
            "maximo_operaciones_dia": 10,
            "tope_perdida_diaria_usd": 30,
            "mercados_permitidos": ["BTCUSDT", "ETHUSDT"],
        }, f, ensure_ascii=False, indent=2)
    return ruta
