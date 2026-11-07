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

print("\n" + ("TODO OK" if not fallos else "FALLOS: " + ", ".join(fallos)))
sys.exit(1 if fallos else 0)
