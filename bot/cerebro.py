"""Circuito vivo: mira la ultima vela cerrada, pregunta al modelo y decide.

Arranca SIEMPRE en papel. Para pasar a dinero real hacen falta dos cosas
escritas a mano por el dueno de la cuenta: el archivo claves.json y apagar el
interruptor solo_simulacro. Con una de las dos falta, sigue en papel.
"""
import json, os, sys, time
import numpy as np
import pandas as pd
from joblib import load

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datos import SIMBOLOS, INTERVALO, features, arma_tabla, DATOS, bajar_mes, meses
from ejecutor import Broker, Configuracion
import exchange

RAIZ = os.path.dirname(os.path.abspath(__file__))
ESTADO = os.path.join(RAIZ, "estado_cerebro.json")
RUTA_POSICIONES = os.path.join(RAIZ, "posiciones.json")


def actualizar_cache():
    """Trae las velas que faltan de este mes para cada simbolo."""
    mes_actual = time.strftime("%Y-%m")
    for s in SIMBOLOS:
        bajar_mes(s, mes_actual)


def ventaja_demostrada(horizonte):
    """Lee el scorecard walk-forward. Devuelve (puede_operar, explicacion).

    Un bot que en la prueba histórica perdió contra "comprar y no tocar nada"
    no tiene permiso de operar plata. Esto no es una opinion: es el numero.
    """
    ruta = os.path.join(RAIZ, "resultados", f"scorecard_h{horizonte}.json")
    if not os.path.exists(ruta):
        return False, "todavia no hay prueba walk-forward corrida"
    with open(ruta, encoding="utf-8") as f:
        s = json.load(f)
    detalle = s.get("detalle", {})
    ganadores = sum(1 for r in detalle.values()
                    if r.get("operaciones", 0) > 0 and r.get("retorno", 0) > r.get("comprar_y_sostener", 0))
    total = len(detalle)
    if ganadores == 0:
        return False, (f"en la prueba de {s.get('horizonte_velas')} velas el bot perdio contra "
                       f"comprar-y-sostener en {total} de {total} mercados "
                       f"(bot {s.get('retorno_promedio_bot')}, comprar-y-sostener "
                       f"{s.get('retorno_promedio_comprar_y_sostener')})")
    if ganadores * 2 <= total:
        return False, f"gana apenas en {ganadores} de {total} mercados: no es una ventaja, es suerte"
    return True, f"gana en {ganadores} de {total} mercados"


def decide(horizonte=24, umbral=0.55):
    d = arma_tabla()
    ruta_modelo = os.path.join(RAIZ, "resultados", f"modelo_h{horizonte}.joblib")
    if not os.path.exists(ruta_modelo):
        raise SystemExit("Falta el modelo entrenado. Correr modelo.py primero.")
    modelo = load(ruta_modelo)
    with open(os.path.join(RAIZ, "resultados", "features.json"), encoding="utf-8") as f:
        cols = json.load(f)

    cfg = Configuracion(umbral_entrada=umbral, umbral_salida=1 - umbral,
                        max_velas_en_posicion=max(24, horizonte * 2))
    posiciones = {}
    if os.path.exists(RUTA_POSICIONES):
        with open(RUTA_POSICIONES, encoding="utf-8") as f:
            posiciones = json.load(f)

    x = exchange.cargar_config() if exchange.hay_claves() else {}
    puede, por_que = ventaja_demostrada(horizonte)
    real = bool(x) and not x.get("solo_simulacro", True) and not exchange.apachado() and puede
    en_papel_activo = bool(x) and puede
    ex = exchange.Exchange(x) if x else None

    if not puede:
        modo = "INHABILITADO"
    elif real:
        modo = "REAL"
    elif en_papel_activo:
        modo = "PAPEL"
    else:
        modo = "PAPEL"

    salida = {"momento": int(time.time() * 1000), "horizonte": horizonte,
              "umbral": umbral, "modo": modo, "ventaja": por_que,
              "permite_operar": puede,
              "mercados": [], "freno": None}

    for s in SIMBOLOS:
        sub = d[d["simbolo"] == s].sort_values("t")
        if len(sub) < 300:
            continue
        ultima = sub.iloc[-1]
        p = float(modelo.predict_proba(sub[cols].tail(1))[0, 1])
        accion = "comprar" if p >= umbral else ("vender" if p <= 1 - umbral else "quieto")
        if not puede:
            accion = "no opera: sin ventaja demostrada"
        fila = {"simbolo": s, "precio": round(float(ultima["close"]), 6),
                "prob_suba": round(p, 4), "accion": accion,
                "vela": pd.Timestamp(int(ultima["t"]), unit="ms", tz="UTC").isoformat(),
                "lecturas": {c: (None if pd.isna(ultima[c]) else round(float(ultima[c]), 5))
                             for c in ("r24", "rsi", "atr_ratio", "pos_rango", "dist_sma200")}}
        pos = posiciones.get(s)
        if pos:
            fila["posicion_abierta"] = pos
        salida["mercados"].append(fila)

    if real:
        try:
            ex.saldo()
        except Exception as e:
            salida["freno"] = f"el exchange rechazo: {type(e).__name__}"
    with open(ESTADO, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    try:
        import avisos
        nuevos = avisos.registrar(salida)
        n, porque = avisos.enviar()
        salida["avisos"] = {"nuevos": nuevos, "mandados": n, "por_que": porque}
        with open(ESTADO, "w", encoding="utf-8") as f:
            json.dump(salida, f, ensure_ascii=False, indent=2)
    except Exception as error:
        salida["avisos"] = {"error": type(error).__name__}
    return salida


if __name__ == "__main__":
    h = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    if "--bajar" in sys.argv:
        actualizar_cache()
    r = decide(h)
    print("modo:", r["modo"])
    for m in r["mercados"]:
        print(f"  {m['simbolo']:9s} {m['precio']:>12}  p={m['prob_suba']:.3f}  -> {m['accion']}")
