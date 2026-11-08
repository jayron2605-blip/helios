"""Circuito vivo: mira la ultima vela cerrada, aplica S11 y opera en papel.

La regla que opera es S11 (confirmacion dia+semana+mes), la unica que aprobo la
prueba de ventaja. El modelo de direccion S1 se muestra solo como comparacion.
Las posiciones simuladas usan precios reales y persisten en posiciones.json.

Arranca SIEMPRE en papel y nunca mueve dinero real: exchange.SOLO_PRUEBA esta en
True como decision de producto, asi que no existe el camino a la orden real. Para
parar el papel alcanza el archivo APAGADO (o el boton de parada del panel).
"""
import json, os, sys, time
import numpy as np
import pandas as pd
from joblib import load

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datos import SIMBOLOS, INTERVALO, features, arma_tabla, DATOS, bajar_mes, meses
from papel import CarteraPapel, senal_s11
import exchange

RAIZ = os.path.dirname(os.path.abspath(__file__))
ESTADO = os.path.join(RAIZ, "estado_cerebro.json")
RUTA_POSICIONES = os.path.join(RAIZ, "posiciones.json")
ESTRATEGIA = "S11 confirmacion dia+semana+mes"


def actualizar_cache():
    """Trae las velas que faltan de este mes para cada simbolo."""
    mes_actual = time.strftime("%Y-%m")
    for s in SIMBOLOS:
        bajar_mes(s, mes_actual)


def _pct(v):
    if v is None:
        return "sin dato"
    s = ("%.1f" % abs(v * 100)).replace(".", ",")
    return ("+" if v >= 0 else "-") + s + " %"


def ventaja_demostrada(horizonte):
    """Lee el scorecard walk-forward. Devuelve (puede_operar, explicacion).

    Un bot que en la prueba histórica perdió contra "comprar y no tocar nada"
    no tiene permiso de operar plata. Esto no es una opinion: es el numero.
    """
    ruta = os.path.join(RAIZ, "resultados", f"scorecard_h{horizonte}.json")
    if not os.path.exists(ruta):
        return False, "todavía no hay prueba corrida"
    with open(ruta, encoding="utf-8") as f:
        s = json.load(f)
    detalle = s.get("detalle", {})
    ganadores = sum(1 for r in detalle.values()
                    if r.get("operaciones", 0) > 0 and r.get("retorno", 0) > r.get("comprar_y_sostener", 0))
    total = len(detalle)
    if ganadores == 0:
        return False, (f"en la prueba de {s.get('horizonte_velas')} velas perdió contra "
                       f"comprar-y-sostener en {total} de {total} mercados "
                       f"(el bot terminó en {_pct(s.get('retorno_promedio_bot'))} y quedarse quieto "
                       f"en {_pct(s.get('retorno_promedio_comprar_y_sostener'))})")
    if ganadores * 2 <= total:
        return False, f"gana apenas en {ganadores} de {total} mercados: no es una ventaja, es suerte"
    return True, f"gana en {ganadores} de {total} mercados"


def ventaja_s11():
    """Lee la prueba de ventaja (ventaja.json) y mira solo S11, la regla aprobada.

    Devuelve (puede_operar, explicacion, fila_s11). El modelo de direccion S1 se
    sigue mostrando como comparacion, pero el que habilita el papel es S11.
    """
    ruta = os.path.join(RAIZ, "resultados", "ventaja.json")
    if not os.path.exists(ruta):
        return False, "todavía no hay prueba de ventaja corrida (correr ventaja.py)", None
    with open(ruta, encoding="utf-8") as f:
        v = json.load(f)
    fila = next((x for x in v.get("estrategias", [])
                 if x.get("estrategia", "").startswith("S11")), None)
    if fila is None:
        return False, "la prueba de ventaja no incluye S11", None
    prom = (fila.get("retorno_promedio") or 0) * 100
    gana = fila.get("le_gana_al_benchmark_en", 0)
    total = len(fila.get("mercados", {}))
    if fila.get("aprueba"):
        return True, (f"S11 aprobó: {prom:+.1f} % promedio, le gana a comprar-y-sostener "
                      f"en {gana} de {total} mercados"), fila
    return False, (f"S11 no aprobó el corte ({prom:+.1f} % promedio, gana en {gana} de {total}): "
                   f"el bot se queda apagado"), fila


def decide(horizonte=24, umbral=0.55):
    d = arma_tabla()
    # El modelo de direccion S1 se carga solo como comparacion: la que opera es S11.
    ruta_modelo = os.path.join(RAIZ, "resultados", f"modelo_h{horizonte}.joblib")
    modelo, cols = None, []
    if os.path.exists(ruta_modelo):
        modelo = load(ruta_modelo)
        with open(os.path.join(RAIZ, "resultados", "features.json"), encoding="utf-8") as f:
            cols = json.load(f)

    puede, por_que, fila_s11 = ventaja_s11()
    apagado = exchange.apachado()
    # Helios nunca opera dinero real: exchange.SOLO_PRUEBA lo hace imposible.
    # El papel se habilita solo si S11 aprobo y no esta el archivo APAGADO.
    opera = puede and not apagado
    modo = "PRUEBA" if opera else "APAGADO"
    if apagado:
        por_que = "hay un archivo APAGADO en la carpeta: el bot está parado a propósito"

    # contador del dia: cada cierre en papel registra su P/L en el freno de perdida diaria
    contador = exchange.Exchange({})
    cartera = CarteraPapel(ruta=RUTA_POSICIONES, contador=contador)

    salida = {"momento": int(time.time() * 1000), "horizonte": horizonte,
              "umbral": umbral, "modo": modo, "ventaja": por_que,
              "estrategia": ESTRATEGIA, "s11": fila_s11,
              "permite_operar": puede, "apagado": apagado,
              "nunca_dinero_real": True, "mercados": [], "freno": None}

    for s in SIMBOLOS:
        sub = d[d["simbolo"] == s].sort_values("t")
        if len(sub) < 300:
            continue
        ultima = sub.iloc[-1]
        precio = float(ultima["close"])
        # S1 como comparacion (si hay modelo entrenado); no decide la operacion
        p = float(modelo.predict_proba(sub[cols].tail(1))[0, 1]) if modelo is not None else 0.5
        r24, r168, r720 = ultima.get("r24"), ultima.get("r168"), ultima.get("r720")
        dentro = senal_s11(r24, r168, r720)
        velas = [{"t": int(v.t), "o": float(v.open), "h": float(v.high),
                  "l": float(v.low), "c": float(v.close)}
                 for v in sub.tail(800).itertuples()]
        # si esta apagado o S11 no aprobo, no se abre nada y se cierra lo que hubiera
        b, accion = cartera.procesar(s, velas, dentro and opera, prob=p)
        if not opera:
            accion_txt = "no opera: está apagado"
        else:
            accion_txt = {"comprar": "comprar (papel)", "vender": "vender (papel)",
                          "quieto": "quieto (papel)"}[accion]
        pos = b.posicion
        fila = {"simbolo": s, "precio": round(precio, 6),
                "prob_suba": round(p, 4), "accion": accion_txt,
                "vela": pd.Timestamp(int(ultima["t"]), unit="ms", tz="UTC").isoformat(),
                "s11": {"dentro": bool(dentro),
                        "r24": None if pd.isna(r24) else round(float(r24), 5),
                        "r168": None if pd.isna(r168) else round(float(r168), 5),
                        "r720": None if pd.isna(r720) else round(float(r720), 5)},
                "lecturas": {c: (None if pd.isna(ultima[c]) else round(float(ultima[c]), 5))
                             for c in ("r24", "rsi", "atr_ratio", "pos_rango", "dist_sma200")},
                "papel": {"efectivo": round(b.efectivo, 2),
                          "en_posicion": pos is not None, "resumen": b.resumen()}}
        if pos:
            fila["posicion_abierta"] = {"cantidad": round(pos.cantidad, 8),
                                        "entrada_precio": pos.entrada_precio,
                                        "stop": pos.stop, "objetivo": pos.objetivo,
                                        "entrada_ts": pos.entrada_ts}
        salida["mercados"].append(fila)

    cartera.salvar()
    salida["papel"] = cartera.resumen()

    # el asistente: las palabras y el riesgo, para los avisos y para el registro
    asis = None
    try:
        import asistente
        asis = asistente.analizar(os.environ.get("HELIOS_SIMBOLO", "BTCUSDT"))
        salida["asistente"] = {"estado": asis.get("estado"),
                               "motivos": asis.get("motivos"),
                               "riesgo": asis.get("riesgo", {}).get("texto")}
    except Exception as error:
        salida["asistente"] = {"error": type(error).__name__}

    # registro de decisiones, con el resultado escrito 24 horas despues
    try:
        import decisiones
        nuevas, cerradas = decisiones.registrar(salida, asis)
        salida["decisiones"] = {"nuevas": nuevas, "cerradas": cerradas,
                                "resumen": decisiones.resumen()}
    except Exception as error:
        salida["decisiones"] = {"error": type(error).__name__ + ": " + str(error)[:100]}

    try:
        import avisos
        r = avisos.registrar(salida, asis)
        n, porque = avisos.enviar()
        salida["avisos"] = {"encolados": r["encolados"], "frenados": r["frenados"],
                            "mandados": n, "por_que": porque}
    except Exception as error:
        salida["avisos"] = {"error": type(error).__name__}

    with open(ESTADO, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    return salida


if __name__ == "__main__":
    h = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    if "--bajar" in sys.argv:
        actualizar_cache()
    r = decide(h)
    print("modo:", r["modo"], "| estrategia:", r.get("estrategia"))
    print("ventaja:", r["ventaja"])
    for m in r["mercados"]:
        s11 = m.get("s11", {})
        print(f"  {m['simbolo']:9s} {m['precio']:>12}  S11 dentro={s11.get('dentro')}  -> {m['accion']}")
    p = r.get("papel", {})
    if p:
        print(f"papel: {p.get('dias_en_papel')} dias | P/L {p.get('pnl_neto')} USD "
              f"| capital {p.get('capital_total')} | ops {p.get('operaciones')} "
              f"| en posicion {p.get('en_posicion')}/{p.get('mercados')}")
