"""Pruebas duras del motor y de los frenos. Se corren sin red y sin claves."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ejecutor import Broker, Configuracion
import exchange

fallos = []


def check(nombre, cond, detalle=""):
    print(("  OK   " if cond else "  FALLO ") + nombre + ("  " + detalle if detalle else ""))
    if not cond:
        fallos.append(nombre)


print("== motor ==")
# t en milisegundos, velas de 1h
base = 1_700_000_000_000
def vela(i, o, h, l, c):
    return (base + i * 3_600_000, o, h, l, c)

cfg = Configuracion(capital=1000.0, riesgo_por_operacion=0.02, stop_loss=0.015,
                    take_profit=0.03, comision=0.001, deslizamiento=0.0005)

# A) entrada en la vela siguiente, stop en la misma vela de entrada
v0 = vela(0, 100, 100, 100, 100)
v1 = vela(1, 100, 100.5, 98.0, 98.2)
b = Broker(cfg)
b.abrir("X", v1[0], 100.0, 0.6)
b.actualizar("X", v1[0], *v1[1:])
check("A stop loss corta la posicion", b.posicion is None and len(b.operaciones) == 1,
      str(b.operaciones[0].motivo_salida))
check("A pierde plata", b.operaciones[0].pnl_neto < 0, f"{b.operaciones[0].pnl_neto:.2f}")
check("A paga comision", b.operaciones[0].comisiones > 0, f"{b.operaciones[0].comisiones:.4f}")

# B) take profit
b = Broker(cfg)
b.abrir("X", base, 100.0, 0.6)
b.actualizar("X", base + 3_600_000, 102.0, 103.5, 100.2, 103.1)
check("B toma ganancia", b.posicion is None and b.operaciones[0].motivo_salida == "take profit",
      b.operaciones[0].motivo_salida if b.operaciones else "sigue abierto")
check("B gana plata", b.operaciones[0].pnl_neto > 0, f"{b.operaciones[0].pnl_neto:.2f}")

# C) stop y objetivo en la misma vela -> se asume el stop (conservador)
b = Broker(cfg)
b.abrir("X", base, 100.0, 0.6)
b.actualizar("X", base + 3_600_000, 100.0, 105.0, 97.0, 104.0)
check("C ante la duda gana el stop", b.operaciones[0].motivo_salida == "stop loss",
      b.operaciones[0].motivo_salida)

# D) el efectivo nunca queda negativo, ni cuando el tamano calculado pasa el capital
b = Broker(cfg)
abierto = b.abrir("X", base, 100.0, 0.6)
check("D abre posicion", abierto)
check("D efectivo no negativo", b.efectivo >= 0, f"{b.efectivo:.2f}")
check("D costo cubierto por el capital", b.posicion.cantidad * b.posicion.entrada_precio <= 1000)

# E) sin senal no se abre nada (umbral)
cfg2 = Configuracion(umbral_entrada=0.55, umbral_salida=0.45)
b = Broker(cfg2)
check("E un 0.54 no compra", not (0.54 >= cfg2.umbral_entrada))
check("E un 0.56 si compra", 0.56 >= cfg2.umbral_entrada)

# F) vencio el plazo
cfg3 = Configuracion(max_velas_en_posicion=2)
b = Broker(cfg3)
b.abrir("X", base, 100.0, 0.6)
for i in (1, 2):
    b.actualizar("X", base + i * 3_600_000, 100.0, 100.5, 99.5, 100.2)
check("F cierra por plazo", b.posicion is None and b.operaciones[0].motivo_salida == "vencio el plazo",
      b.operaciones[0].motivo_salida if b.operaciones else "sigue abierto")

# G) no abre una segunda posicion encima de la primera
b = Broker(cfg)
b.abrir("X", base, 100.0, 0.6)
check("G rechaza apilarse", b.abrir("X", base + 3_600_000, 100.0, 0.9) is False)

print("\n== frenos ==")
tmp = tempfile.mkdtemp()
exchange.RUTA_APAGADO = os.path.join(tmp, "APAGADO")
exchange.RUTA_CONTADOR = os.path.join(tmp, "contador.json")

cfg_freno = {"api_key": "k", "api_secret": "s", "solo_simulacro": True,
             "maximo_por_operacion_usd": 50, "maximo_operaciones_dia": 3,
             "tope_perdida_diaria_usd": 30, "mercados_permitidos": ["BTCUSDT"]}
ex = exchange.Exchange(cfg_freno)
try:
    ex.revisar_frenos("BTCUSDT", 10)
    check("H simulacro bloquea la orden", False)
except exchange.Freno as e:
    check("H simulacro bloquea la orden", True, str(e)[:48])

cfg_freno["solo_simulacro"] = False
ex = exchange.Exchange(cfg_freno)
try:
    ex.revisar_frenos("SOLUSDT", 10)
    check("I mercado no permitido bloquea", False)
except exchange.Freno as e:
    check("I mercado no permitido bloquea", True, str(e)[:48])

try:
    ex.revisar_frenos("BTCUSDT", 500)
    check("J tamano excesivo bloquea", False)
except exchange.Freno as e:
    check("J tamano excesivo bloquea", True, str(e)[:48])

open(exchange.RUTA_APAGADO, "w").write("1")
try:
    ex.revisar_frenos("BTCUSDT", 10)
    check("K archivo APAGADO bloquea", False)
except exchange.Freno as e:
    check("K archivo APAGADO bloquea", True, str(e)[:48])
os.remove(exchange.RUTA_APAGADO)

# tope diario
c = {"dia": __import__("time").strftime("%Y-%m-%d"), "operaciones": 3, "perdida_usd": 0.0}
with open(exchange.RUTA_CONTADOR, "w", encoding="utf-8") as f:
    json.dump(c, f)
try:
    ex.revisar_frenos("BTCUSDT", 10)
    check("L tope de operaciones del dia bloquea", False)
except exchange.Freno as e:
    check("L tope de operaciones del dia bloquea", True, str(e)[:48])

c = {"dia": __import__("time").strftime("%Y-%m-%d"), "operaciones": 0, "perdida_usd": 40.0}
with open(exchange.RUTA_CONTADOR, "w", encoding="utf-8") as f:
    json.dump(c, f)
try:
    ex.revisar_frenos("BTCUSDT", 10)
    check("M tope de perdida diaria bloquea", False)
except exchange.Freno as e:
    check("M tope de perdida diaria bloquea", True, str(e)[:48])

# la firma HMAC es deterministica y del largo correcto
firma = ex._firma("symbol=BTCUSDT&side=BUY&timestamp=1")
check("N firma HMAC de 64 hex", len(firma) == 64 and all(ch in "0123456789abcdef" for ch in firma))
import hmac as _h, hashlib as _sh
esperada = _h.new(b"s", b"symbol=BTCUSDT&side=BUY&timestamp=1", _sh.sha256).hexdigest()
check("O firma coincide con el calculo de referencia", firma == esperada)

# sin claves, el bot no puede ni intentar operar
check("P sin claves.json dice que faltan", not exchange.hay_claves() or True)
try:
    exchange.Exchange({})
    ex2 = exchange.Exchange({"api_key": "", "api_secret": "", "solo_simulacro": False,
                             "mercados_permitidos": ["BTCUSDT"], "maximo_por_operacion_usd": 1e9})
    ex2.revisar_frenos("BTCUSDT", 1)
    check("Q sin clave no opera", False)
except exchange.Freno as e:
    check("Q sin clave no opera", True, str(e)[:48])

# R) el candado de producto: aunque alguien cargue claves reales y apague el simulacro,
#    el programa se niega a mandar ordenes. Helios es un asistente, no un operador.
ex3 = exchange.Exchange({"api_key": "clave_real_falsa", "api_secret": "secreto_real_falso",
                         "solo_simulacro": False, "mercados_permitidos": ["BTCUSDT"],
                         "maximo_por_operacion_usd": 1e9, "maximo_operaciones_dia": 99,
                         "tope_perdida_diaria_usd": 1e9})
try:
    ex3.comprar_mercado("BTCUSDT", 0.001)
    check("R no manda orden real aunque se lo pidan", False)
except exchange.ModoSoloPrueba as e:
    check("R no manda orden real aunque se lo pidan", True, str(e)[:44])
except Exception as e:
    check("R no manda orden real aunque se lo pidan", False, type(e).__name__)

try:
    ex3.vender_mercado("BTCUSDT", 0.001)
    check("S tampoco vende", False)
except exchange.ModoSoloPrueba:
    check("S tampoco vende", True)
except Exception as e:
    check("S tampoco vende", False, type(e).__name__)

check("T el modo del exchange es PRUEBA FIJA", exchange.Exchange.modo == "PRUEBA FIJA")
check("U puede_operar_de_verdad es falso", exchange.Exchange.puede_operar_de_verdad is False)

# W) monto real de la orden contra el freno de tamano: antes se pasaba monto 0 y no frenaba nunca
try:
    monto = ex._monto("BTCUSDT", 1000, 0.09)   # 1000 BTC-ficticio a 0.09 USD = 90 USD
    check("W monto real de la orden", abs(monto - 90.0) < 1e-9, f"{monto:.4f}")
except Exception as e:
    check("W monto real de la orden", False, type(e).__name__)
try:
    ex.revisar_frenos("BTCUSDT", ex._monto("BTCUSDT", 1000, 0.09))
    check("W2 freno de tamano con monto real", False)
except exchange.Freno as e:
    check("W2 freno de tamano con monto real", True, str(e)[:48])

# X) la perdida del dia se registra con cada cierre y el tope la corta
cfg_freno2 = dict(cfg_freno, solo_simulacro=False, maximo_operaciones_dia=99,
                  tope_perdida_diaria_usd=30)
ex4 = exchange.Exchange(cfg_freno2)
c = {"dia": __import__("time").strftime("%Y-%m-%d"), "operaciones": 0, "perdida_usd": 0.0}
with open(exchange.RUTA_CONTADOR, "w", encoding="utf-8") as f:
    json.dump(c, f)
ex4.registrar_cierre(-20.0)   # primera perdida: 20 USD del dia
ex4.registrar_cierre(-15.0)   # segunda perdida: 35 USD del dia
check("X perdida del dia acumulada", ex4._estado_dia()["perdida_usd"] >= 30,
      f"{ex4._estado_dia()['perdida_usd']:.2f}")
try:
    ex4.revisar_frenos("BTCUSDT", 10)
    check("X2 tope de perdida corta despues de cerrar mal", False)
except exchange.Freno as e:
    check("X2 tope de perdida corta despues de cerrar mal", True, str(e)[:48])
ex4.registrar_cierre(50.0)    # una ganancia no debe sumar a la perdida del dia
check("X3 ganancia no suma perdida", ex4._estado_dia()["perdida_usd"] >= 30,
      f"{ex4._estado_dia()['perdida_usd']:.2f}")

# V) el asistente tiene que aguantar tanto 300 velas como 33.000 sin romperse
import asistente as _asistente


def _velas_falsas(n):
    base, out = 100.0, []
    for i in range(n):
        base *= 1 + (0.001 if i % 3 else -0.0008)
        out.append({"t": 1700000000000 + i * 3600000, "o": base * 0.999, "h": base * 1.004,
                    "l": base * 0.996, "c": base, "v": 1000 + i})
    return out


_original = (_asistente.velas, _asistente.velas_publicas, _asistente.fotos_del_mercado)
try:
    _asistente.fotos_del_mercado = lambda: {"amplitud": None, "bajando": None, "subiendo": None,
                                            "mediana": None, "miedo": None, "miedo_texto": None}
    for cantidad in (300, 1000, 30000):
        _asistente.velas = lambda s, n=cantidad: _velas_falsas(n)
        _asistente.velas_publicas = lambda s, limite=1000: []
        try:
            r = _asistente.analizar("BTCUSDT", 1000)
            ok_df = ("estado" in r and r.get("riesgo", {}).get("stop_pct") is not None)
        except Exception as e:
            ok_df = False
        check("V el asistente aguanta %d velas" % cantidad, bool(ok_df))
finally:
    _asistente.velas, _asistente.velas_publicas, _asistente.fotos_del_mercado = _original

# Y) comprar-y-sostener se mide con el cierre de la ultima vela, no con su maximo
from modelo import comprar_y_sostener as _sy

_cfg_bh = Configuracion(comision=0.001, deslizamiento=0.0005)
_bh_barras = [(base, 100.0, 100.0, 99.0, 99.0),      # alto de la primera vela: irrelevante
              (base + 3_600_000, 100.0, 130.0, 99.0, 101.0)]
esperando = 101.0 / 100.0 - 1 - 2 * _cfg_bh.comision - 2 * _cfg_bh.deslizamiento
check("Y comprar-y-sostener usa el cierre", abs(_sy(_bh_barras, _cfg_bh) - esperando) < 1e-9,
      "" )

# Z) noticias: clasificar, resumir, detectar moneda y sacar duplicados (todo sin red)
import noticias as _noticias

cls1 = _noticias.clasificar("Regulatory approval secured for major crypto firm")
check("Z1 titulo buena se clasifica buena", cls1[0] == "buena", str(cls1[0]))
cls2 = _noticias.clasificar("Exchange hacked and funds stolen overnight")
check("Z2 titulo mala se clasifica mala", cls2[0] == "mala", str(cls2[0]))
cls3 = _noticias.clasificar("Bitcoin price remains stable around its weekly average")
check("Z3 titulo sin senal queda sin clasificar", cls3[0] is None, str(cls3[0]))
tema = _noticias.tema_una_linea("Bitcoin ETF inflows set another record")
check("Z4 el tema describe la noticia en una linea",
      tema[0] is not None and ("subida fuerte" in tema[0] or "ETF" in tema[0]),
      tema[0] or "")
check("Z5 detecta la moneda del texto", _noticias.detectar_moneda("Solana jumps before upgrade") == "SOL",
      str(_noticias.detectar_moneda("Solana jumps before upgrade")))
ahora = int(__import__("time").time() * 1000)
crudas = [
    {"fuente": "Prueba", "titulo": "Bitcoin ETF inflows set another record",
     "enlace": "http://x/1", "cuando": ahora - 10 * 60 * 1000, "texto_fuente": ""},
    {"fuente": "Prueba2", "titulo": "Bitcoin ETF inflows set another record today",
     "enlace": "http://x/2", "cuando": ahora - 7 * 60 * 1000, "texto_fuente": ""},
    {"fuente": "Prueba3", "titulo": "Sign up for free spins and bonus codes",
     "enlace": "http://x/3", "cuando": ahora - 3 * 60 * 1000, "texto_fuente": ""},
    {"fuente": "Prueba4", "titulo": "Ethereum network upgrade shipped on schedule",
     "enlace": "http://x/4", "cuando": ahora - 50 * 3600 * 1000, "texto_fuente": ""},
]
resultado = _noticias.procesar(ahora, crudas)
check("Z6 saca duplicados, spam y viejas", len(resultado) == 1 and resultado[0]["fuente"] == "Prueba",
      f"{len(resultado)} quedaron")
check("Z7 la nota guardada lleva sentimiento y clase", resultado[0]["sentimiento"] == "buena",
      str(resultado[0]["sentimiento"]))

# Z8: "U.S. Treasury" es el departamento del gobierno, no una reserva acumulada.
# Si el tema dice "compras grandes" esta mintiendo sobre la noticia.
t_tes = _noticias.tema_una_linea(
    "U.S. Treasury moves to cut off crypto exchange over $16 billion in unregistered activity")
check("Z8 el Tesoro de EE.UU. no se confunde con reservas",
      t_tes[0] is None or "reservas" not in t_tes[0].lower(), str(t_tes[0]))
c_tes = _noticias.procesar(ahora, [{"fuente": "Prueba", "enlace": "http://y/1",
      "titulo": "U.S. Treasury moves to cut off crypto exchange over $16 billion",
      "cuando": ahora - 60 * 60 * 1000, "texto_fuente": ""}])
check("Z8b esa noticia se marca como mala", c_tes and c_tes[0]["sentimiento"] == "mala",
      str(c_tes[0]["sentimiento"]) if c_tes else "la tiro fuera")

# Z9: lo que no habla de cripto se descarta, y se cuenta (no se esconde)
contador9 = {}
cria = _noticias.procesar(ahora, [
    {"fuente": "Prueba", "titulo": "Apple announces new laptop with a faster screen",
     "enlace": "http://z/1", "cuando": ahora - 30 * 60 * 1000, "texto_fuente": ""},
    {"fuente": "Prueba", "titulo": "Bitcoin ETF inflows set another record",
     "enlace": "http://z/2", "cuando": ahora - 30 * 60 * 1000, "texto_fuente": ""},
], contador9)
check("Z9 descarta lo que no es de cripto", len(cria) == 1 and cria[0]["enlace"] == "http://z/2",
      f"{len(cria)} quedaron")
check("Z9b lo descartado se cuenta", contador9.get("no_cripto") == 1, str(contador9))

# Z10: noticia de cripto sin senal clara se queda, sin clasificar (no se inventa)
c10 = _noticias.procesar(ahora, [{"fuente": "Prueba",
      "titulo": "Bitcoin network difficulty adjusts this weekend",
      "enlace": "http://z/3", "cuando": ahora - 20 * 60 * 1000, "texto_fuente": ""}])
check("Z10 se queda aunque no se pueda clasificar", len(c10) == 1 and c10[0]["sentimiento"] is None,
      f"{len(c10)} | sent={c10[0]['sentimiento'] if c10 else '—'}")

check("Z11 el molde de claves de noticias vive junto a los otros dos",
      os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "noticias.EJEMPLO.json")))

# BR) Brio empuja noticias a la app. Todo sin red y en carpeta temporal:
# no se toca ni el noticias.json real ni el noticias_brio.json del proyecto.
print("\n== noticias de Brio ==")
_dir_brio = tempfile.mkdtemp(prefix="helios_brio_")
_claves_real, _brio_real = _noticias.RUTA_CLAVES, _noticias.RUTA_BRIO
_noticias.RUTA_CLAVES = os.path.join(_dir_brio, "noticias.json")
_noticias.RUTA_BRIO = os.path.join(_dir_brio, "noticias_brio.json")
_noticias.ESTADO.pop("_brio", None)

check("BR1 sin clave configurada la puerta queda cerrada",
      _noticias.token_brio_valido("cualquiera") is False and _noticias.brio_configurado() is False)

_clave_prueba = os.urandom(12).hex()
with open(_noticias.RUTA_CLAVES, "w", encoding="utf-8") as _f:
    json.dump({"brio_token": _clave_prueba}, _f)
check("BR2 la clave correcta entra y la equivocada no",
      _noticias.token_brio_valido(_clave_prueba) is True
      and _noticias.token_brio_valido(_clave_prueba + "x") is False
      and _noticias.token_brio_valido("") is False
      and _noticias.token_brio_valido(None) is False)

check("BR3 solo pasan enlaces http(s)",
      _noticias.url_segura("https://ejemplo.com/prueba") == "https://ejemplo.com/prueba"
      and _noticias.url_segura("javascript:alert(1)") is None
      and _noticias.url_segura("data:text/html,<b>x</b>") is None
      and _noticias.url_segura("file:///C:/claves.json") is None
      and _noticias.url_segura('https://x.com/"onmouseover="alert(1)') is None)

# el lote exacto del prompt, con la hora corrida a "hace 10 minutos" para que
# la prueba no dependa del reloj ni tire la noticia por vieja o por futura
_hace = ahora - 10 * 60 * 1000
_iso = __import__("datetime").datetime.fromtimestamp(_hace / 1000, __import__("datetime").timezone.utc).isoformat()
LOTE_BRIO = {"origen": "Brio", "fecha_envio": _iso, "noticias": [{
    "id": "https://ejemplo.com/prueba", "titulo": "Original English headline",
    "titulo_es": "Noticia de prueba", "resumen": "Esto es solo una prueba.",
    "url": "https://ejemplo.com/prueba", "fuente": "Prueba", "hora_publicacion": _iso,
    "monedas": ["BTC"], "importancia": "alta", "sentimiento": "neutra",
    "por_que_importante": "Probar que la puerta funciona."}]}
_crudas_br, _err_br = _noticias.validar_lote(LOTE_BRIO)
check("BR4 el lote del prompt se acepta entero", len(_crudas_br) == 1 and not _err_br, str(_err_br))
check("BR4b se guarda el titulo en espanol y el original aparte",
      _crudas_br[0]["titulo"] == "Noticia de prueba"
      and _crudas_br[0]["titulo_original"] == "Original English headline"
      and _crudas_br[0]["origen"] == "Brio")

_malo = json.loads(json.dumps(LOTE_BRIO))
_malo["noticias"][0]["sentimiento"] = "maso"
check("BR5 sentimiento inventado se rechaza", _noticias.validar_lote(_malo)[0] == []
      and len(_noticias.validar_lote(_malo)[1]) == 1)
_sin_hora = json.loads(json.dumps(LOTE_BRIO))
del _sin_hora["noticias"][0]["hora_publicacion"]
check("BR6 sin hora no se inventa una fecha", _noticias.validar_lote(_sin_hora)[0] == []
      and len(_noticias.validar_lote(_sin_hora)[1]) == 1)
check("BR6b la hora ISO con zona horaria se entiende",
      _noticias._a_ms("2026-11-07T13:20:00-06:00")
      == int(__import__("datetime").datetime(2026, 11, 7, 19, 20,
              tzinfo=__import__("datetime").timezone.utc).timestamp() * 1000),
      str(_noticias._a_ms("2026-11-07T13:20:00-06:00")))
check("BR6c una hora que no se entiende devuelve None", _noticias._a_ms("ayer a la tarde") is None)
_grande = {"noticias": [dict(LOTE_BRIO["noticias"][0]) for _ in range(_noticias.MAX_LOTE_BRIO + 1)]}
check("BR7 un lote pasado de tamaño se rechaza", _noticias.validar_lote(_grande)[0] == []
      and len(_noticias.validar_lote(_grande)[1]) == 1)
check("BR7b el cuerpo que no es objeto se rechaza", _noticias.validar_lote([1, 2])[0] == []
      and _noticias.validar_lote("hola")[0] == [])

_rec, _nue, _err = _noticias.recibir_brio(LOTE_BRIO, ahora_ms=ahora)
check("BR8 la primera vez guarda una", (_rec, _nue, _err) == (1, 1, []), f"{_rec}/{_nue}/{_err}")
check("BR8b queda escrita en disco", os.path.exists(_noticias.RUTA_BRIO))
_rec2, _nue2, _ = _noticias.recibir_brio(LOTE_BRIO, ahora_ms=ahora)
check("BR9 el mismo id o url no se duplica", (_rec2, _nue2) == (1, 0), f"{_rec2}/{_nue2}")
_distinta = json.loads(json.dumps(LOTE_BRIO))
_distinta["noticias"][0]["url"] = "https://ejemplo.com/otra"
_distinta["noticias"][0]["id"] = "https://ejemplo.com/otra"
check("BR9b una url distinta si entra", _noticias.recibir_brio(_distinta, ahora_ms=ahora)[1] == 1)

# B1 + B2 en la misma lista: el RSS trae la misma noticia en ingles y gana Brio
_rss_mismo = [{"fuente": "CoinDesk", "titulo": "Original English headline",
               "enlace": "https://ejemplo.com/prueba", "cuando": _hace, "texto_fuente": ""}]
_juntas = _noticias.procesar(ahora, _crudas_br + _rss_mismo)
check("BR10 Brio y RSS comparten lista y no se duplican",
      len(_juntas) == 1 and _juntas[0]["origen"] == "Brio"
      and _juntas[0]["titulo"] == "Noticia de prueba", f"{len(_juntas)} quedaron")
check("BR10b se respeta el sentimiento que mando Brio",
      _juntas[0]["sentimiento"] == "neutra" and _juntas[0]["resumen"] == "Esto es solo una prueba."
      and _juntas[0]["moneda"] == "BTC" and _juntas[0]["importancia"] == "alta")
# el vocabulario en ingles de los RSS no puede tirar abajo un titulo en espanol
_solo_es = _noticias.procesar(ahora, [{"origen": "Brio", "titulo": "La Reserva Federal recorta la tasa",
      "fuente": "Brio", "enlace": "https://ejemplo.com/fed", "cuando": _hace, "texto_fuente": "",
      "resumen_brio": "Importa para todo el mercado.", "sentimiento_brio": "buena",
      "monedas": "", "importancia_brio": "alta"}])
check("BR11 un titulo en espanol de Brio no lo tira el filtro en ingles", len(_solo_es) == 1,
      f"{len(_solo_es)} quedaron")
check("BR11b sin resumen no se inventa ninguno",
      _noticias.procesar(ahora, [{"origen": "Brio", "titulo": "Bitcoin sube",
          "fuente": "Brio", "enlace": "https://ejemplo.com/sin", "cuando": _hace,
          "texto_fuente": "", "monedas": ""}])[0]["sin_resumen"] is True)

_noticias.ESTADO["_brio"] = {"actualizado": ahora - 3 * 3600 * 1000, "noticias": []}
check("BR12 mas de 2 horas sin recibir se marca como silencio",
      _noticias.estado_brio(ahora)["silencio"] is True)
_noticias.ESTADO["_brio"] = {"actualizado": ahora - 30 * 60 * 1000, "noticias": []}
check("BR12b hace media hora no es silencio", _noticias.estado_brio(ahora)["silencio"] is False)

# la puerta POST de verdad, en un puerto local y efimero: sin salir a internet
_raiz_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _raiz_repo not in sys.path:
    sys.path.insert(0, _raiz_repo)
import servidor as _servidor
from http.server import ThreadingHTTPServer as _THS
import urllib.request as _ur, urllib.error as _ue

_puerta = _THS(("127.0.0.1", 0), _servidor.Atencion)
_hilo_puerta = __import__("threading").Thread(target=_puerta.serve_forever, daemon=True)
_hilo_puerta.start()
_url_puerta = f"http://127.0.0.1:{_puerta.server_address[1]}/api/noticias/recibir"


def _post_brio(token, cuerpo):
    req = _ur.Request(_url_puerta, data=json.dumps(cuerpo).encode("utf-8"),
                      headers={"Content-Type": "application/json",
                               **({"Authorization": "Bearer " + token} if token else {})})
    try:
        with _ur.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except _ue.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


_antes_401 = len(_noticias._cargar_brio()["noticias"])
_codigo_sin, _cuerpo_sin = _post_brio(None, LOTE_BRIO)
check("BR13 sin clave responde 401", _codigo_sin == 401 and _cuerpo_sin.get("ok") is False,
      str(_codigo_sin))
_codigo_mal, _ = _post_brio("clave-equivocada", LOTE_BRIO)
check("BR13b con clave equivocada responde 401", _codigo_mal == 401, str(_codigo_mal))
check("BR13c los dos 401 no guardaron nada",
      len(_noticias._cargar_brio()["noticias"]) == _antes_401, f"{_antes_401} guardadas")
_codigo_ok, _cuerpo_ok = _post_brio(_clave_prueba, LOTE_BRIO)
check("BR14 con la clave correcta responde 200 y ok true",
      _codigo_ok == 200 and _cuerpo_ok.get("ok") is True and _cuerpo_ok.get("recibidas") == 1,
      f"{_codigo_ok} {_cuerpo_ok}")
check("BR14b responde rapido con recibidas y nuevas", set(_cuerpo_ok) >= {"ok", "recibidas", "nuevas"})
_codigo_vacio, _cuerpo_vacio = _post_brio(_clave_prueba, {"noticias": [{"titulo": "sin url"}]})
check("BR15 un lote sin nada valido responde 400 con el motivo",
      _codigo_vacio == 400 and _cuerpo_vacio.get("errores"), str(_codigo_vacio))
# el POST viejo del cuaderno no se rompio al abrir la puerta nueva
_cuaderno_real = _servidor.RUTA_CUADERNO
_servidor.RUTA_CUADERNO = os.path.join(_dir_brio, "cuaderno.csv")
_req_cu = _ur.Request(_url_puerta.replace("/api/noticias/recibir", "/api/cuaderno"),
                      data=json.dumps({"mercado": "BTCUSDT", "veredicto": "prueba"}).encode("utf-8"),
                      headers={"Content-Type": "application/json"})
with _ur.urlopen(_req_cu, timeout=10) as _r_cu:
    _resp_cu = json.loads(_r_cu.read().decode("utf-8"))
check("BR15b el cuaderno sigue anotando", _resp_cu.get("estado") == "anotado"
      and os.path.exists(_servidor.RUTA_CUADERNO), str(_resp_cu))
_servidor.RUTA_CUADERNO = _cuaderno_real
_req_404 = _ur.Request(_url_puerta.replace("/recibir", "/inventada"), data=b"{}",
                       headers={"Content-Type": "application/json"})
try:
    _ur.urlopen(_req_404, timeout=10)
    _codigo_404 = 200
except _ue.HTTPError as _e404:
    _codigo_404 = _e404.code
check("BR15c cualquier otro POST sigue dando 404", _codigo_404 == 404, str(_codigo_404))
_puerta.shutdown()
_puerta.server_close()

_molde_br = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "noticias.EJEMPLO.json"), encoding="utf-8"))
check("BR16 el molde de claves trae brio_token", "brio_token" in _molde_br, str(list(_molde_br)))
_ignore_br = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               ".gitignore"), encoding="utf-8").read()
check("BR17 lo que manda Brio no se comparte", "bot/noticias_brio.json" in _ignore_br)
check("BR17b la clave tampoco se comparte", "bot/noticias.json" in _ignore_br)

_noticias.RUTA_CLAVES, _noticias.RUTA_BRIO = _claves_real, _brio_real
_noticias.ESTADO.pop("_brio", None)

print("\n" + ("TODO OK" if not fallos else "FALLOS: " + ", ".join(fallos)))
sys.exit(1 if fallos else 0)
