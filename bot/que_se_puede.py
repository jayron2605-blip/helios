"""Dos preguntas separadas, porque tienen respuestas distintas:

  1. Se puede predecir la DIRECCION?  (lo que todos venden)
  2. Se puede predecir la AGITACION?   (lo que si es predecible, y sirve para arriesgar bien)
"""
import json, os, sys
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datos import FEATURES, SIMBOLOS

RAIZ = os.path.dirname(os.path.abspath(__file__))
H = 24


def base():
    d = pd.read_pickle(os.path.join(RAIZ, "datos", "tabla.pkl")).sort_values(["simbolo", "t"]).reset_index(drop=True)
    d["futuro"] = d.groupby("simbolo")["close"].shift(-H)
    d["y"] = (np.log(d["futuro"].clip(lower=1e-12)) - np.log(d["close"].clip(lower=1e-12)) > 0).astype(int)
    # agitacion futura: rango real de las proximas H velas, normalizado por el precio
    r = d.groupby("simbolo")["high"].shift(-1).rolling(1).max()
    d["max_f"] = d.groupby("simbolo")["high"].transform(lambda s: s.shift(-1).rolling(H).max())
    d["min_f"] = d.groupby("simbolo")["low"].transform(lambda s: s.shift(-1).rolling(H).min())
    d["agit_futura"] = (d["max_f"] - d["min_f"]) / d["close"]
    d["agit_hoy"] = d.groupby("simbolo")["high"].transform(lambda s: s.rolling(H).max()).values
    d["agit_hoy"] = (d["agit_hoy"] - d.groupby("simbolo")["low"].transform(lambda s: s.rolling(H).min()).values) / d["close"]
    d = d.dropna(subset=["y", "agit_futura", "agit_hoy"])
    return d


def cortes(d, n=8):
    ts = np.sort(d["t"].unique())
    inicio = int(len(ts) * 0.55)
    bordes = np.linspace(inicio, len(ts) - 1, n + 1).astype(int)
    for k in range(n):
        a, b = ts[bordes[k]], ts[bordes[k + 1]]
        yield a, b


def prueba_direccion(d):
    aciertos, bases = [], []
    for a, b in cortes(d):
        tren = d[d["t"] < a]
        test = d[(d["t"] >= a) & (d["t"] <= b)]
        if len(tren) < 20000 or len(test) < 500:
            continue
        m = HistGradientBoostingClassifier(max_iter=180, learning_rate=0.07, random_state=1)
        m.fit(tren[FEATURES], tren["y"])
        p = (m.predict_proba(test[FEATURES])[:, 1] > 0.5).astype(int)
        aciertos.append((p == test["y"].to_numpy()).mean())
        bases.append(max(test["y"].mean(), 1 - test["y"].mean()))
    return float(np.mean(aciertos)), float(np.mean(bases))


def prueba_agitacion(d):
    rho, mejora = [], []
    for a, b in cortes(d):
        tren = d[d["t"] < a]
        test = d[(d["t"] >= a) & (d["t"] <= b)]
        if len(tren) < 20000 or len(test) < 500:
            continue
        m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.07, random_state=1)
        m.fit(tren[FEATURES], tren["agit_futura"])
        pred = m.predict(test[FEATURES])
        r = spearmanr(pred, test["agit_futura"]).statistic
        rho.append(r)
        err_modelo = float(np.sqrt(np.mean((pred - test["agit_futura"]) ** 2)))
        err_ingenuo = float(np.sqrt(np.mean((test["agit_hoy"] - test["agit_futura"]) ** 2)))
        mejora.append(1 - err_modelo / err_ingenuo)
    return float(np.mean(rho)), float(np.mean(mejora))


if __name__ == "__main__":
    d = base()
    print("filas utiles:", len(d), "| horizonte:", H, "velas", flush=True)
    ac, ba = prueba_direccion(d)
    print(f"\nDIRECCION: el modelo acierta {ac*100:.2f} %. El truco de 'siempre decir mayoria' saca {ba*100:.2f} %.")
    print(f"           ventaja real: {(ac-ba)*100:+.2f} puntos")
    rho, me = prueba_agitacion(d)
    print(f"\nAGITACION: correlacion de rango (Spearman) con lo que va a pasar: {rho:.3f}")
    print(f"           mejora el error de 'suponer que sigue igual' en {me*100:.1f} %.")
    out = {"direccion_acierto": round(ac, 4), "direccion_base": round(ba, 4),
           "direccion_ventaja": round(ac - ba, 4),
           "agitacion_spearman": round(rho, 4), "agitacion_mejora_error": round(me, 4)}
    with open(os.path.join(RAIZ, "resultados", "que_se_puede_predecir.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nguardado en resultados/que_se_puede_predecir.json")
