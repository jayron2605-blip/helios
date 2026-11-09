"""Noticias en vivo: las trae de fuentes publicas, las ordena y las conecta con el precio.

Reglas del modulo (son de producto, no de gusto):
  - Solo fuentes publicas y gratuitas: RSS de CoinDesk, Cointelegraph y Decrypt.
    CryptoPanic funciona ADICIONAL si el dueno pega su clave en bot/noticias.json
    (molde en noticias.EJEMPLO.json). Sin clave, el resto funciona igual.
  - Cada noticia guarda: titulo, fuente, hora real, moneda afectada (si se sabe),
    de que va en una linea en espanol, clasificacion buena/mala/neutra con motivo,
    enlace a la fuente, y el movimiento REAL del precio en la hora siguiente.
  - Nada se inventa: si no se puede clasificar seguro queda "sin clasificar".
    Si una fuente falla, se dice que fallo. Nunca se escribe una noticia de ejemplo
    que parezca real.
  - Se sacan duplicados, spam y viejas (+48 h). El servidor pide como mucho cada
    10 minutos, y deja guardadas las ultimas en bot/noticias_cache.json para que
    si se corta internet se sigan viendo.
  - Brio EMPUJA noticias a la app (POST /api/noticias/recibir). La direccion es
    solo Brio -> App: la app nunca le pide nada a Brio. Viven en su propio archivo
    bot/noticias_brio.json y se mezclan con las del RSS en la misma lista guardada.
"""
import hashlib, hmac, json, os, re, time
import datetime as dt
import email.utils as eutils
import difflib
import threading
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

RAIZ = os.path.dirname(os.path.abspath(__file__))
RUTA_CLAVES = os.path.join(RAIZ, "noticias.json")
RUTA_CACHE = os.path.join(RAIZ, "noticias_cache.json")
RUTA_BRIO = os.path.join(RAIZ, "noticias_brio.json")

FUENTES_RSS = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
}
CRYPTOPANIC = "https://cryptopanic.com/api/free/v1/posts/?auth_token={token}&public=true"

CADENCIA_SEG = 600           # el servidor pide noticias como mucho cada 10 minutos
MAX_EDAD_SEG = 48 * 3600     # nada mas viejo de 48 horas
MAX_POR_FUENTE = 25
MAX_TOTAL = 80
VENTANA_MEDIDA_MIN = 130     # hora del titulo 5 min + hora siguiente cerrada de verdad

# Brio manda noticias a la app (direccion Brio -> App, nunca al reves).
# Se guardan aparte porque traer() reconstruye la lista desde RSS en cada refresco:
# si vivieran solo en memoria o en el cache, se borrarian solas a los 10 minutos.
MAX_BRIO = 200               # cuantas guarda en disco como maximo
MAX_LOTE_BRIO = 50           # cuantas acepta en un solo POST
BRIO_SILENCIO_SEG = 2 * 3600  # mas de 2 h sin recibir => "Sin noticias nuevas importantes"
SENTIMIENTOS_BRIO = ("buena", "mala", "neutra")
IMPORTANCIAS_BRIO = ("alta", "media")
IGNORAR_SPAM = re.compile(r"giveaway|promo code|referral|sign ?up|subscribe|casino|"
                          r"bet now|free spins|sweepstake|play now|earn rewards",
                          re.IGNORECASE)

# monedas: (codigo, nombres que la delatan en el titulo). Solo las 6 del bot tienen velas
# propias; para el precio de referencia de las demas se usa BTC y el panel lo aclara.
MONEDAS = [
    ("BTC", ("bitcoin", "btc")),
    ("ETH", ("ethereum", "ether", "eth")),
    ("SOL", ("solana",)),
    ("BNB", ("bnb", "binance coin", "binance")),
    ("XRP", ("xrp", "ripple")),
    ("DOGE", ("dogecoin",)),
    ("ADA", ("cardano",)),
    ("LTC", ("litecoin",)),
    ("SHIB", ("shiba", "shib")),
    ("LINK", ("chainlink",)),
    ("DOT", ("polkadot",)),
    ("SUI", ("sui",)),
    ("AVAX", ("avalanche",)),
    ("APT", ("aptos",)),
    ("ARB", ("arbitrum",)),
    ("OP", ("optimism",)),
    ("PEPE", ("pepe",)),
    ("TRX", ("tron",)),
    ("XMR", ("monero",)),
    ("ZEC", ("zcash",)),
    ("UNI", ("uniswap",)),
    ("AAVE", ("aave",)),
    ("MATIC", ("polygon",)),
    ("WLD", ("worldcoin",)),
]

# de que va la noticia, en una linea, segun lo que efectivamente dice el titulo.
# Si el tema lleva clase forzada, esa clasificacion gana a las palabras sueltas:
# un hackeo sigue siendo mala aunque la misma frase diga "surge".
TEMAS = [
    (r"hack|breach|exploit|drained|stolen|theft|phishing|scam|rug ?pull|robbed",
     "Habla de un robo, hackeo o estafa.", "mala",
     "los robos y las estafas asustan al mercado"),
    (r"law ?suit|sued|charged|indicted|fraud|criminal|prison|jail|seiz",
     "Habla de problemas legales o de justicia.", "mala",
     "las demandas y los cargos penales son señales malas"),
    (r"banned?\b|\bban\b|crack ?down|restrict|blocking access|cut off|shut ?down|delist",
     "Habla de prohibiciones, bloqueos o restricciones.", "mala",
     "las prohibiciones y los bloqueos cierran puertas al mercado"),
    (r"regulat|\bsec\b|cftc|compliance|guideline",
     "Habla de regulación de gobiernos o del mercado.", None, ""),
    (r"surge|soar|rally|skyrocket|all-?time high|\bath\b|record",
     "Habla de una subida fuerte del precio.", None, ""),
    (r"crash|plung|slump|dump|sink|slide|plummet|sell-?off|selloff|liquidat",
     "Habla de una caída fuerte del precio.", None, ""),
    (r"approv|green.?light|launch|roll ?out|goes? live|list(ed|ing)|adoption|partner",
     "Habla de algo que se aprobó, se lanzó o se integró.", None, ""),
    (r"\betf\b", "Habla de ETFs, los fondos que compran cripto en la bolsa.", None, ""),
    (r"inflation|\bfed\b|rate (cut|hike)|cpi|recession|tariff",
     "Habla de la economía grande: inflación, tasas o recesión.", None, ""),
    (r"upgrade|fork|mainnet|testnet|protocol|migration|vulnerab|\bbug\b",
     "Habla de mejoras técnicas o de la red.", None, ""),
    # "treasury" a secas es el departamento del gobierno, no una reserva acumulada:
    # sin contexto de compra el tema diria una mentira, asi que exige palabras de acumulacion
    (r"accumulat|\bholdings\b|treasur\w* (bought|holds?|added|buying)|reserve[sd]? (holdings|grew|added)|bought more|purchased",
     "Habla de compras grandes o de reservas que alguien acumula.", None, ""),
    (r"stablecoin|usdt|usdc|depeg|pegged",
     "Habla de stablecoins, las monedas atadas al dólar.", None, ""),
]

PALABRAS_BUENA = ("surge", "soar", "rally", "jump", "record", "all-time high", "approv",
                  "green light", "adoption", "adopt", "partner", "launch", "gains",
                  "rises", "rise", "beats", "exceeds", "inflow", "accumul", "milestone",
                  "boost", "uptick", "rebound", "upbeat", "positive")
PALABRAS_MALA = ("hack", "breach", "exploit", "stolen", "theft", "scam", "fraud",
                 "bankrupt", "liquidat", "crash", "plunge", "plummet", "slump", "dump",
                 "sinks", "slid", "slide", "falls", "fell", "tumble", "sued", "lawsuit",
                 "charged", "investigat", "fined", "penalty", "banned", "ban ",
                 "crackdown", "crack down", "sanction", "illegal", "ponzi",
                 "sell-off", "selloff", "worries", "fear", "bearish")

UMBRAL_MOVIMIENTO = 0.01      # 1 % en una hora = movimiento fuerte
MUNDO_REF = "BTCUSDT"

# Filtro de utilidad: los canales de cripto tambien publican de tecnologia general.
# Se queda lo que nombra algo de este mundo; lo demas se descarta y se cuenta,
# para que el panel pueda decir cuantas tiro fuera en vez de esconderlo.
VOCABULO_CRIPTO = re.compile(
    r"bitcoin|\bbtc\b|ethereum|\beth\b|crypto|blockchain|stablecoin|\bdefi\b|\bnft\b|"
    r"altcoin|solana|ripple|\bxrp\b|dogecoin|binance|coinbase|kraken|mexc|okx|bybit|"
    r"wallet|token|mining|miner|halving|satoshi|web3|airdrop|layer[- ]?[0-9]|"
    r"smart contract|on-?chain|memecoin|usdt|usdc|ledger|custody|self-?custody|"
    r"\bcoin\b|cripto|moneda digital|\betf\b|\bsec\b|\bcftc\b|market cap|capitalizacion|"
    r"tether|circle|ripple|cardano|polkadot|avalanche|chainlink|uniswap|aave",
    re.IGNORECASE)
MAPA_SIMBOLO = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "BNB": "BNBUSDT",
                "XRP": "XRPUSDT", "DOGE": "DOGEUSDT", "LTC": "LTCUSDT", "SHIB": "SHIBUSDT",
                "ADA": "ADAUSDT", "LINK": "LINKUSDT", "DOT": "DOTUSDT", "TRX": "TRXUSDT",
                "AVAX": "AVAXUSDT", "XMR": "XMRUSDT", "ZEC": "ZECUSDT", "AAVE": "AAVEUSDT",
                "UNI": "UNIUSDT", "MATIC": "MATICUSDT"}

_SEGURIDAD = threading.Lock()
CARGA = threading.Lock()
ESTADO = {"actualizado": 0, "noticias": [], "fuentes": {}, "_crudas": [], "_medidas": {}}


# ---------- utilidades puras ----------
def _traer(url, segundos=12):
    req = urllib.request.Request(url, headers={"User-Agent": "HeliosNoticias/1.0"})
    with urllib.request.urlopen(req, timeout=segundos) as r:
        return r.read()


def _id(link):
    return hashlib.sha1((link or "").encode("utf-8", "ignore")).hexdigest()[:12]


def _normaliza(t):
    t = (t or "").lower()
    t = re.sub(r"[^a-z0-9áééíóúñü ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _parecido(a, b):
    return difflib.SequenceMatcher(None, _normaliza(a), _normaliza(b)).ratio()


def _texto_de(item, etiqueta):
    for hijo in item:
        tag = hijo.tag.split("}")[-1]
        if tag == etiqueta:
            if (hijo.text or "").strip():
                return hijo.text.strip()
            if hijo.get("href"):
                return hijo.get("href").strip()
    return ""


def _cuando_de(item):
    for hijo in item:
        tag = hijo.tag.split("}")[-1]
        if tag not in ("pubDate", "published", "updated") or not (hijo.text or "").strip():
            continue
        texto = hijo.text.strip()
        try:
            return int(eutils.parsedate_to_datetime(texto).timestamp() * 1000)
        except Exception:
            pass
        try:
            return int(dt.datetime.fromisoformat(texto.replace("Z", "+00:00")).timestamp() * 1000)
        except Exception:
            continue
    return None


# ---------- leer fuentes ----------
def _leer_rss(nombre, url):
    """Devuelve noticias crudas de un canal RSS publico. Si el canal cae, avisa afuera."""
    datos = _traer(url)
    raiz = ET.fromstring(datos)
    salida = []
    for item in raiz.iter():
        if item.tag.split("}")[-1] not in ("item", "entry"):
            continue
        titulo = _texto_de(item, "title")
        enlace = _texto_de(item, "link") or _texto_de(item, "id")
        momento = _cuando_de(item)
        if not titulo or len(titulo) < 15 or not enlace or momento is None:
            continue
        resumen = _texto_de(item, "description") or _texto_de(item, "summary")
        resumen = re.sub(r"<[^>]+>", " ", resumen or "")
        salida.append({"fuente": nombre, "titulo": titulo, "enlace": enlace,
                       "cuando": momento, "texto_fuente": resumen[:400]})
    return salida


def _leer_cryptopanic(cfg):
    """Fuente adicional OPCIONAL con clave del dueno. Sin clave devuelve lista vacia."""
    if not (cfg or {}).get("cryptopanic_token"):
        return []
    datos = json.loads(_traer(CRYPTOPANIC.format(token=cfg["cryptopanic_token"])))
    salida = []
    for p in (datos.get("results") or [])[:MAX_POR_FUENTE]:
        publicado = (p.get("published_at") or "")
        cuando = None
        try:
            cuando = int(dt.datetime.fromisoformat(
                publicado.replace("Z", "+00:00")).timestamp() * 1000)
        except ValueError:
            pass
        if cuando is None:
            continue
        salida.append({"fuente": "CryptoPanic", "titulo": p.get("title") or "",
                       "enlace": p.get("url") or "", "cuando": cuando, "texto_fuente": "",
                       "monedas": ",".join(c.get("code", "") for c in (p.get("currencies") or []))})
    return salida


# ---------- clasificar y resumir (funciones puras, probadas) ----------
def detectar_moneda(texto):
    """Primera moneda que el texto nombra de verdad. None si no hay certeza."""
    t = " " + _normaliza(texto) + " "
    for codigo, claves in MONEDAS:
        for clave in claves:
            if re.search(r"\b" + re.escape(clave) + r"\b", t):
                return codigo
    return None


def tema_una_linea(titulo, texto_fuente=""):
    """Una linea en espanol con de que va la noticia, si el titulo realmente lo dice."""
    t = _normaliza(titulo)
    for patron, linea, clase, motivo in TEMAS:
        if re.search(patron, t):
            return linea, clase, motivo
    return None, None, None


def clasificar(titulo):
    """(clase, motivo) con lo que pasa en el titulo. Sin senal clara NO decide."""
    t = " " + _normaliza(titulo) + " "
    hay_buena = any(re.search(r"\b" + re.escape(p.split()[0]), t) or p in t for p in PALABRAS_BUENA)
    hay_mala = any(re.search(r"\b" + re.escape(p.split()[0]), t) or p in t for p in PALABRAS_MALA)
    if hay_buena and not hay_mala:
        return "buena", "habla de algo que suele empujar el precio para arriba"
    if hay_mala and not hay_buena:
        return "mala", "habla de daño, ventas o prohibición"
    if hay_buena and hay_mala:
        return "neutra", "mezcla señales buenas y malas: mejor leerla completa"
    return None, "no se puede clasificar solo por el título"


def es_de_cripto(texto):
    """True si el texto nombra algo de este mercado. Se cuenta, no se esconde."""
    return bool(VOCABULO_CRIPTO.search(texto or "")) or detectar_moneda(texto) is not None


def procesar(ahora_ms, crudas, contador=None):
    """Toma las noticias crudas: corta spam, viejas y duplicados; clasifica; ordena.

    Las de Brio llegan ya leidas: se respeta su titulo en espanol, su resumen y su
    sentimiento en vez de volver a adivinarlos desde el titulo en ingles. Van
    primero en la lista, asi que si el RSS trae la misma noticia gana la de Brio.
    """
    limpiadas, vistas, enlaces = [], [], set()
    for n in crudas:
        titulo = (n.get("titulo") or "").strip()
        cuando = n.get("cuando")
        if not titulo or cuando is None:
            continue
        if cuando > ahora_ms + 5 * 60 * 1000 or ahora_ms - cuando > MAX_EDAD_SEG * 1000:
            if contador is not None:
                contador["viejas"] = contador.get("viejas", 0) + 1
            continue
        de_brio = n.get("origen") == "Brio"
        if IGNORAR_SPAM.search(_normaliza(titulo)):
            if contador is not None:
                contador["spam"] = contador.get("spam", 0) + 1
            continue
        # Brio ya filtro por importancia y escribe en espanol: el vocabulario en
        # ingles de los RSS tiraria abajo noticias suyas que si sirven.
        if not de_brio and not es_de_cripto(titulo + " " + (n.get("texto_fuente") or "")[:220]):
            if contador is not None:
                contador["no_cripto"] = contador.get("no_cripto", 0) + 1
            continue
        enlace = (n.get("enlace") or "").strip()
        if (enlace and enlace in enlaces) or any(_parecido(v, titulo) >= 0.72 for v in vistas):
            if contador is not None:
                contador["repetidas"] = contador.get("repetidas", 0) + 1
            continue
        vistas.append(titulo)
        if enlace:
            enlaces.add(enlace)
        texto = n.get("texto_fuente") or ""
        if de_brio:
            clase = n.get("sentimiento_brio")
            motivo = n.get("por_que_brio") or "Brio la marcó como importante para el mercado."
            linea = n.get("resumen_brio")
            sin_linea = not linea
        else:
            linea, clase_tema, motivo_tema = tema_una_linea(titulo)
            if clase_tema:
                clase, motivo = clase_tema, motivo_tema
            else:
                clase, motivo = clasificar(titulo)
            sin_linea = linea is None
        monedas_cripto = (n.get("monedas") or "").strip() or None
        fila = {
            "id": _id(enlace or titulo),
            "titulo": titulo,
            "fuente": n.get("fuente"),
            "enlace": enlace or None,
            "cuando": int(cuando),
            "moneda": monedas_cripto or detectar_moneda(titulo + " " + texto[:200]),
            "resumen": linea or ("Brio no mandó resumen: abrí la noticia original para leerla."
                                 if de_brio else
                                 "No pude intuir de qué va: abrí la noticia para leerla."),
            "sin_resumen": sin_linea,
            "sentimiento": clase if clase in ("buena", "mala", "neutra") else None,
            "por_que": motivo,
            "origen": "Brio" if de_brio else "RSS",
            "precio": None,
        }
        if de_brio:
            fila["titulo_original"] = n.get("titulo_original")
            fila["importancia"] = n.get("importancia_brio")
        limpiadas.append(fila)
    return sorted(limpiadas, key=lambda x: x["cuando"], reverse=True)[:MAX_TOTAL]


# ---------- el movimiento REAL del precio despues de la noticia ----------
# api.binance.com responde 451 desde direcciones de EE.UU. El espejo publico
# de Binance sirve las mismas velas y no bloquea: plan B si el primero falla.
BINANCE_URL = "https://api.binance.com"
BINANCE_ESPEJO = "https://data-api.binance.vision"


def _velas_de_hora(simbolo, momento_ms, ahora_ms):
    bucket = int(momento_ms // 3600000) * 3600000
    ruta = (f"/api/v3/klines?symbol={simbolo}"
            f"&interval=1h&startTime={bucket}&limit=2")
    velas = None
    for base in (BINANCE_URL, BINANCE_ESPEJO):
        try:
            velas = json.loads(_traer(base + ruta, 10))
            break
        except Exception:
            continue
    if velas is None:
        return None
    if (not isinstance(velas, list) or len(velas) < 2
            or int(velas[0][0]) != bucket
            or int(velas[1][0]) != bucket + 3600000
            or int(velas[1][6]) > ahora_ms - 60000):
        return None  # hueco en los datos o la hora todavia no cerro: se mide otro dia
    return float(velas[0][4]), float(velas[1][4])


def medir_precios(ahora_ms):
    """Marca como se movio el precio en la hora siguiente a cada noticia vieja.

    Una vez medida, no se vuelve a medir (queda en el cache). Si no hay velas
    cerradas todavia, queda 'no_medido' con su razon: nunca se inventa.
    """
    con_medida = 0
    with _SEGURIDAD:
        pendientes = [n for n in ESTADO.get("noticias", [])
                      if n.get("precio") is None
                      and ahora_ms - n["cuando"] >= VENTANA_MEDIDA_MIN * 60 * 1000
                      and n["id"] not in ESTADO["_medidas"]][:6]
    for n in pendientes:
        n["precio"] = {"estado": "midiendo", "moneda": "—"}
        simbolo = MAPA_SIMBOLO.get(n["moneda"])
        etiqueta = n["moneda"] if simbolo else "BTC (referencia)"
        par = _velas_de_hora(simbolo or MUNDO_REF, n["cuando"], ahora_ms)
        if par is None:
            # se vuelve a intentar en la proxima pasada: la hora todavia no cerro
            n["precio"] = {"estado": "no_medido", "moneda": etiqueta,
                           "por_que": "la hora siguiente todavía no cerró o Binance no respondió"}
        else:
            base, luego = par
            mov = luego / base - 1
            if mov >= UMBRAL_MOVIMIENTO:
                estado = "coincidió con una subida fuerte"
            elif mov <= -UMBRAL_MOVIMIENTO:
                estado = "coincidió con una caída fuerte"
            else:
                estado = "movimiento pequeño"
            n["precio"] = {"estado": estado, "moneda": etiqueta,
                           "movimiento_pct": round(mov * 100, 2)}
            ESTADO["_medidas"][n["id"]] = True
            con_medida += 1
    return con_medida


# ---------- guardado y carga ----------
def _salvar_cache():
    try:
        with _SEGURIDAD:
            datos = {"actualizado": ESTADO.get("actualizado", 0),
                     "fuentes": dict(ESTADO.get("fuentes", {})),
                     "noticias": ESTADO.get("noticias", [])[:MAX_TOTAL]}
        with open(RUTA_CACHE, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False)
    except Exception:
        pass


def _cargar_cache():
    try:
        with open(RUTA_CACHE, encoding="utf-8") as f:
            datos = json.load(f)
        ESTADO["noticias"] = datos.get("noticias", [])
        ESTADO["fuentes"] = datos.get("fuentes", {})
        ESTADO["actualizado"] = datos.get("actualizado", 0)
        for n in ESTADO["noticias"]:
            if n.get("precio") and n["precio"].get("estado") != "midiendo":
                ESTADO["_medidas"].setdefault(n["id"], True)
    except (FileNotFoundError, json.JSONDecodeError):
        pass


def _cargar_config():
    try:
        with open(RUTA_CLAVES, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# ---------- Brio empuja noticias a la app (Brio -> App, nunca al reves) ----------
def _clave_brio():
    # En Render el disco es efimero: la clave vive en la variable de entorno
    # BRIO_TOKEN. En la PC del dueno puede seguir viviendo en noticias.json.
    entorno = str(os.environ.get("BRIO_TOKEN") or "").strip()
    if entorno:
        return entorno
    return str((_cargar_config() or {}).get("brio_token") or "").strip()


def brio_configurado():
    """True si hay clave de Brio, ya sea en el entorno o en bot/noticias.json."""
    return bool(_clave_brio())


def token_brio_valido(token):
    """Sin clave configurada no entra nada: la puerta queda cerrada, no abierta."""
    esperado = _clave_brio()
    if not esperado or not token:
        return False
    return hmac.compare_digest(esperado.encode("utf-8"), str(token).encode("utf-8"))


def url_segura(texto):
    """Solo http(s) y sin caracteres que rompan el HTML. None si no sirve.

    El panel abre este enlace con window.open(): un javascript: o un data: aca
    seria codigo ejecutandose en la maquina del dueno.
    """
    if not isinstance(texto, str):
        return None
    t = texto.strip()
    if not t or len(t) > 600 or re.search(r"[\s\"'<>\\]", t):
        return None
    partes = urllib.parse.urlsplit(t)
    if partes.scheme not in ("http", "https") or not partes.netloc:
        return None
    return t


def _a_ms(valor):
    """Hora ISO8601, RFC2822 o epoch -> milisegundos. None si no se entiende: no se inventa."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        if valor > 1e12:
            return int(valor)
        if valor > 1e9:
            return int(valor * 1000)
        return None
    if not isinstance(valor, str) or not valor.strip():
        return None
    texto = valor.strip()
    try:
        momento = dt.datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        try:
            return int(eutils.parsedate_to_datetime(texto).timestamp() * 1000)
        except Exception:
            return None
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=dt.timezone.utc)
    return int(momento.timestamp() * 1000)


def _texto_corto(valor, tope):
    return valor.strip()[:tope] if isinstance(valor, str) else ""


def validar_lote(payload):
    """(crudas, errores) de lo que mando Brio. Lo que no se puede leer se rechaza con motivo."""
    if not isinstance(payload, dict):
        return [], ["el cuerpo tiene que ser un objeto JSON"]
    lista = payload.get("noticias")
    if not isinstance(lista, list):
        return [], ["falta la lista 'noticias']"]
    if len(lista) > MAX_LOTE_BRIO:
        return [], [f"el lote trae {len(lista)} noticias y el maximo es {MAX_LOTE_BRIO}"]
    crudas, errores = [], []
    for i, p in enumerate(lista):
        donde = f"noticias[{i}]"
        if not isinstance(p, dict):
            errores.append(donde + ": no es un objeto")
            continue
        enlace = url_segura(p.get("url"))
        if not enlace:
            errores.append(donde + ": 'url' falta o no es http(s)")
            continue
        cuando = _a_ms(p.get("hora_publicacion"))
        if cuando is None:
            errores.append(donde + ": 'hora_publicacion' no se entiende")
            continue
        original = _texto_corto(p.get("titulo"), 300)
        espanol = _texto_corto(p.get("titulo_es"), 300)
        if not (original or espanol):
            errores.append(donde + ": falta 'titulo' o 'titulo_es'")
            continue
        sentimiento = _texto_corto(p.get("sentimiento"), 20).lower()
        if sentimiento and sentimiento not in SENTIMIENTOS_BRIO:
            errores.append(donde + ": 'sentimiento' tiene que ser buena, mala o neutra")
            continue
        importancia = _texto_corto(p.get("importancia"), 20).lower()
        if importancia and importancia not in IMPORTANCIAS_BRIO:
            errores.append(donde + ": 'importancia' tiene que ser alta o media")
            continue
        monedas = p.get("monedas")
        if monedas is not None and not isinstance(monedas, list):
            errores.append(donde + ": 'monedas' tiene que ser una lista")
            continue
        codigos = ",".join(_texto_corto(c, 12).upper() for c in (monedas or [])
                           if isinstance(c, str) and c.strip())[:200]
        crudas.append({
            "origen": "Brio",
            "titulo": espanol or original,
            "titulo_original": original or None,
            "fuente": _texto_corto(p.get("fuente"), 60) or "Brio",
            "enlace": enlace,
            "id_brio": _texto_corto(p.get("id"), 600) or enlace,
            "cuando": cuando,
            "texto_fuente": "",
            "monedas": codigos,
            "resumen_brio": (_texto_corto(p.get("resumen"), 400)
                             or _texto_corto(p.get("por_que_importante"), 400) or None),
            "sentimiento_brio": sentimiento or None,
            "por_que_brio": _texto_corto(p.get("por_que_importante"), 300) or None,
            "importancia_brio": importancia or None,
        })
    return crudas, errores


def _cargar_brio():
    try:
        with open(RUTA_BRIO, encoding="utf-8") as f:
            datos = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"actualizado": 0, "noticias": []}
    if not isinstance(datos, dict):
        return {"actualizado": 0, "noticias": []}
    noticias = [n for n in (datos.get("noticias") or []) if isinstance(n, dict)]
    return {"actualizado": int(datos.get("actualizado") or 0), "noticias": noticias}


def _salvar_brio(datos):
    """Atomico: si se corta la luz a mitad de escritura no queda el archivo roto."""
    temporal = RUTA_BRIO + ".tmp"
    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    os.replace(temporal, RUTA_BRIO)


def recibir_brio(payload, ahora_ms=None):
    """Guarda lo que empujo Brio. Devuelve (recibidas, nuevas, errores).

    Se guarda aparte del cache de RSS porque traer() reconstruye esa lista entera
    en cada refresco: ahi las de Brio se borrarian solas a los 10 minutos.
    """
    crudas, errores = validar_lote(payload)
    ahora_ms = int(time.time() * 1000) if ahora_ms is None else int(ahora_ms)
    with _SEGURIDAD:
        datos = _cargar_brio()
        viejas = datos["noticias"]
        conocidas = set()
        for n in viejas:
            conocidas.add(n.get("enlace"))
            conocidas.add(n.get("id_brio"))
        nuevas = []
        for n in crudas:
            if n["enlace"] in conocidas or n["id_brio"] in conocidas:
                continue
            conocidas.add(n["enlace"])
            conocidas.add(n["id_brio"])
            nuevas.append(n)
        if nuevas:
            juntas = nuevas + viejas
            juntas.sort(key=lambda x: x.get("cuando") or 0, reverse=True)
            datos = {"actualizado": ahora_ms, "noticias": juntas[:MAX_BRIO]}
            _salvar_brio(datos)
        ESTADO["_brio"] = datos
    return len(crudas), len(nuevas), errores


def estado_brio(ahora_ms=None):
    """Lo que el panel necesita para decir si Brio mando algo y cuando."""
    ahora_ms = int(time.time() * 1000) if ahora_ms is None else int(ahora_ms)
    with _SEGURIDAD:
        datos = ESTADO.get("_brio")
        if datos is None:
            datos = _cargar_brio()
            ESTADO["_brio"] = datos
    ultimo = datos.get("actualizado") or 0
    guardadas = len(datos.get("noticias") or [])
    return {"configurado": brio_configurado(),
            "actualizado": ultimo,
            "guardadas": guardadas,
            "silencio": bool(ultimo) and (ahora_ms - ultimo) > BRIO_SILENCIO_SEG * 1000}


# ---------- para el servidor (/api/noticias) ----------
def traer(force=False):
    """Trae lo mejor que tenga. Internet cada 10 minutos como maximo (o con force=True).

    Si todas las fuentes fallan, sirve lo guardado y el panel mostra que es viejo.
    """
    ahora_ms = int(time.time() * 1000)
    fresco = (ahora_ms - ESTADO.get("actualizado", 0)) < CADENCIA_SEG * 1000
    if (not fresco or force) and CARGA.acquire(blocking=False):
        try:
            crudas, fuentes = [], {}

            def bajar(nombre, trabajo):
                try:
                    items = trabajo()
                    crudas.extend(items)
                    fuentes[nombre] = f"ok ({len(items)} noticias)"
                except Exception as e:
                    fuentes[nombre] = "error: " + type(e).__name__

            hilos = [threading.Thread(target=bajar, args=(nombre, (lambda u=nombre: _leer_rss(u, FUENTES_RSS[u]))))
                     for nombre in FUENTES_RSS]
            cfg = _cargar_config()
            if cfg.get("cryptopanic_token"):
                hilos.append(threading.Thread(target=bajar, args=("CryptoPanic", lambda: _leer_cryptopanic(cfg))))
            for h in hilos:
                h.start()
            for h in hilos:
                h.join(timeout=15)
            contador = {}
            with _SEGURIDAD:
                brio = _cargar_brio()
                ESTADO["_brio"] = brio
                # Brio primero: si el RSS trae la misma noticia, gana la que ya
                # vino leida y traducida en vez de la que hay que adivinar.
                crudas = list(brio["noticias"]) + crudas
                fuentes["Brio"] = (f"ok ({len(brio['noticias'])} guardadas)" if brio["noticias"]
                                   else ("esperando el primer envío" if brio_configurado()
                                         else "sin clave configurada"))
                anteriores = {n["id"]: n.get("precio") for n in ESTADO.get("noticias", [])}
                ESTADO["_crudas"] = crudas
                ESTADO["fuentes"] = fuentes
                ESTADO["noticias"] = procesar(ahora_ms, crudas, contador)
                for n in ESTADO["noticias"]:
                    previo = anteriores.get(n["id"])
                    if previo and previo.get("estado") not in (None, "midiendo"):
                        n["precio"] = previo
                ESTADO["descartes"] = contador
                ESTADO["actualizado"] = ahora_ms
            _salvar_cache()
        finally:
            CARGA.release()
    medir_precios(ahora_ms)
    _salvar_cache()
    brio = estado_brio(ahora_ms)
    with _SEGURIDAD:
        return {"actualizado": ESTADO.get("actualizado", 0),
                "fuentes": dict(ESTADO.get("fuentes", {})),
                "recibidas": len(ESTADO.get("_crudas", [])),
                "descartes": dict(ESTADO.get("descartes", {})),
                "brio": brio,
                "noticias": ESTADO.get("noticias", [])[:MAX_TOTAL]}


_cargar_cache()
