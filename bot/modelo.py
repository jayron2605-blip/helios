"""Entrenamiento y evaluacion con walk-forward.

Walk-forward quiere decir: el modelo nunca ve el futuro. Se entrena con todo lo
que paso antes de T y se prueba con el mes que sigue, despues se corre T un mes
y se repite. Es la unica forma de que el numero que sale se parezca al que vas a
ver en vivo.
"""
import json, os, sys, time
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from joblib import dump

from ejecutor import Broker, Configuracion
from datos import SIMBOLOS, FEATURES

RAIZ = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(RAIZ, "datos")
SALIDA = os.path.join(RAIZ, "resultados")

REENTRENAR_MESES = 1
CALIENTE_MESES = 12


def carga_tabla(horizonte):
    d = pd.read_pickle(os.path.join(DATOS, "tabla.pkl")).sort_values(["simbolo", "t"]).reset_index(drop=True)
    d["futuro"] = d.groupby("simbolo")["close"].shift(-horizonte)
    d["etiqueta_h"] = (np.log(d["futuro"].clip(lower=1e-12))
                       - np.log(d["close"].clip(lower=1e-12)))
    d["y"] = (d["etiqueta_h"] > 0).astype(int)
    d.loc[d["futuro"].isna(), "y"] = np.nan
    return d


def folds(d, horizonte):
    t0 = d["t"].min()
    tmax = d["t"].max()
    inicio_test = pd.Timestamp(t0, unit="ms") + pd.DateOffset(months=CALIENTE_MESES)
    cortes = pd.date_range(inicio_test, pd.Timestamp(tmax, unit="ms"), freq="MS")
    for k in range(len(cortes) - 1):
        a = int(cortes[k].timestamp() * 1000)
        b = int(cortes[k + 1].timestamp() * 1000) - 1
        yield a, b


def entrenar_y_probar(d, horizonte, verbose=True):
    d = d.dropna(subset=["y"]).copy()
    d["p"] = np.nan
    cortes = list(folds(d, horizonte))
    t0 = time.time()
    for i, (a, b) in enumerate(cortes, 1):
        tren = d[d["t"] < a]
        test = (d["t"] >= a) & (d["t"] <= b)
        if len(tren) < 5000 or test.sum() == 0:
            continue
        modelo = HistGradientBoostingClassifier(
            max_iter=220, learning_rate=0.06, max_leaf_nodes=31,
            min_samples_leaf=60, l2_regularization=1.0, early_stopping=True,
            validation_fraction=0.15, random_state=42)
        modelo.fit(tren[FEATURES], tren["y"].astype(int))
        d.loc[test, "p"] = modelo.predict_proba(d.loc[test, FEATURES])[:, 1]
        if verbose and (i % 3 == 0 or i == len(cortes)):
            print(f"   plegado {i}/{len(cortes)}  {pd.Timestamp(a,unit='ms'):%Y-%m}  "
                  f"tren={len(tren)}  ({time.time()-t0:.0f}s)", flush=True)
    ultimo = d[d["p"].notna()]["t"].max()
    modelo_final = HistGradientBoostingClassifier(
        max_iter=220, learning_rate=0.06, max_leaf_nodes=31,
        min_samples_leaf=60, l2_regularization=1.0, early_stopping=True,
        validation_fraction=0.15, random_state=42)
    sub = d[d["t"] <= ultimo]
    modelo_final.fit(sub[FEATURES], sub["y"].astype(int))
    os.makedirs(SALIDA, exist_ok=True)
    dump(modelo_final, os.path.join(SALIDA, f"modelo_h{horizonte}.joblib"))
    with open(os.path.join(SALIDA, "features.json"), "w", encoding="utf-8") as f:
        json.dump(FEATURES, f, ensure_ascii=False)
    return d


def backtest_simbolo(barras, probs, cfg, simbolo):
    broker = Broker(cfg, registro=f"trades_{simbolo}.csv", raiz=SALIDA)
    pend = None
    n = len(barras)
    for i in range(n - 1):
        ts, o, h, l, c = barras[i]
        if pend == "cerrar" and broker.posicion:
            broker.cerrar(ts, o, "salida por senal")
        elif pend == "abrir" and not broker.posicion:
            broker.abrir(simbolo, ts, o, probs[i])
        pend = None
        broker.actualizar(simbolo, ts, o, h, l, c)
        broker.marca(ts, c)
        p = probs[i]
        if not broker.posicion and p >= cfg.umbral_entrada:
            pend = "abrir"
        elif broker.posicion and p <= cfg.umbral_salida:
            pend = "cerrar"
    if broker.posicion:
        ts, o, h, l, c = barras[-1]
        broker.cerrar(ts, c, "fin del testeo")
        broker.marca(ts, c)
    broker.volcar_registro()
    return broker


def comprar_y_sostener(barras, cfg):
    if len(barras) < 2:
        return 0.0
    o0 = barras[0][1]
    c1 = barras[-1][2]
    bruto = c1 / o0 - 1
    return bruto - 2 * cfg.comision - 2 * cfg.deslizamiento


def correr(horizonte, umbral=0.55):
    d = carga_tabla(horizonte)
    print(f"== horizonte {horizonte} velas ==  filas={len(d)}  "
          f"baselines sube={d['y'].mean():.3f}", flush=True)
    d = entrenar_y_probar(d, horizonte)
    eval_d = d[d["p"].notna()]
    print(f"   fila con prediccion: {len(eval_d)}", flush=True)

    cfg = Configuracion(umbral_entrada=umbral, umbral_salida=1 - umbral,
                        max_velas_en_posicion=max(24, horizonte * 2))
    resumen, curvas = {}, []
    for s in SIMBOLOS:
        sub = eval_d[eval_d["simbolo"] == s].sort_values("t")
        if len(sub) < 500:
            continue
        barras = list(zip(sub["t"].astype("int64"), sub["open"].astype(float),
                          sub["high"].astype(float), sub["low"].astype(float),
                          sub["close"].astype(float)))
        probs = sub["p"].astype(float).to_numpy()
        broker = backtest_simbolo(barras, probs, cfg, s)
        r = broker.resumen()
        r["comprar_y_sostener"] = round(comprar_y_sostener(barras, cfg), 4)
        aciertos = ((probs > 0.5).astype(int) == sub["y"].astype(int).to_numpy()).mean()
        r["precision_modelo"] = round(float(aciertos), 4)
        resumen[s] = r
        for x in broker.curva:
            curvas.append({"t": x["t"], "simbolo": s, "capital": x["capital"]})
        print(f"   {s:9s} op={r.get('operaciones',0):5d}  acierto={r.get('tasa_acierto',0):.3f}  "
              f"retorno={r.get('retorno',0)*100:+7.2f}%  vs buy&hold {r['comprar_y_sostener']*100:+7.2f}%  "
              f"caida={r.get('max_caida',0)*100:5.1f}%  com={r.get('comisiones_pagadas',0):.0f}", flush=True)

    # agregado: capital repartido en partes iguales
    total_ops = sum(r.get("operaciones", 0) for r in resumen.values())
    rets = [r["retorno"] for r in resumen.values() if r.get("operaciones", 0) > 0]
    bh = [r["comprar_y_sostener"] for r in resumen.values()]
    scorecard = {
        "horizonte_velas": horizonte,
        "umbral": umbral,
        "simbolos": SIMBOLOS,
        "comision_por_lado": cfg.comision,
        "deslizamiento": cfg.deslizamiento,
        "riesgo_por_operacion": cfg.riesgo_por_operacion,
        "stop_loss": cfg.stop_loss,
        "take_profit": cfg.take_profit,
        "operaciones_totales": total_ops,
        "retorno_promedio_bot": round(float(np.mean(rets)), 4) if rets else None,
        "retorno_promedio_comprar_y_sostener": round(float(np.mean(bh)), 4) if bh else None,
        "simbolos_que_le_ganan_al_silencioso": int(sum(1 for r in resumen.values()
                                                       if r.get("operaciones", 0) > 0
                                                       and r["retorno"] > r["comprar_y_sostener"])),
        "detalle": resumen,
    }
    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, f"scorecard_h{horizonte}.json"), "w", encoding="utf-8") as f:
        json.dump(scorecard, f, ensure_ascii=False, indent=2)
    pd.DataFrame(curvas).to_csv(os.path.join(SALIDA, f"curva_h{horizonte}.csv"), index=False)
    print(f"\n   TOTAL: {total_ops} operaciones | bot {scorecard['retorno_promedio_bot']} "
          f"| comprar-y-sostener {scorecard['retorno_promedio_comprar_y_sostener']} "
          f"| le gana al silencio en {scorecard['simbolos_que_le_ganan_al_silencioso']}/{len(resumen)}",
          flush=True)
    return scorecard


if __name__ == "__main__":
    h = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    umbral = float(sys.argv[2]) if len(sys.argv) > 2 else 0.55
    correr(h, umbral)
