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
from datos import FEATURES, SIMBOLOS, leer_tabla

RAIZ = os.path.dirname(os.path.abspath(__file__))
H = 24


def base():
    d = leer_tabla().sort_values(["simbolo", "t"]).reset_index(drop=True)
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


def prueba_agitacion(d, modo):
    """Dos formas de pedirle lo mismo al modelo, y la respuesta no es la misma.

    modo="nivel": adivinar el numero de agitacion futuro.
    modo="razon": adivinar cuanto cambia contra la agitacion de hoy.
    La vara siempre es "suponer que sigue igual", que es lo que hace cualquiera sin modelo.
    """
    cols = FEATURES + ["agit_hoy"]
    rho, mejora = [], []
    for a, b in cortes(d):
        tren = d[(d["t"] < a) & tren_ok(d)]
        test = (d["t"] >= a) & (d["t"] <= b)
        if len(tren) < 20000 or test.sum() < 500:
            continue
        X_tren, X_test = tren[cols], d.loc[test, cols]
        if modo == "razon":
            y = np.log(tren["agit_futura"] / tren["agit_hoy"])
            m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.07, random_state=1)
            m.fit(X_tren, y)
            pred = d.loc[test, "agit_hoy"].to_numpy() * np.exp(m.predict(X_test))
        else:
            m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.07, random_state=1)
            m.fit(X_tren, tren["agit_futura"])
            pred = m.predict(X_test)
        real = d.loc[test, "agit_futura"]
        ingenuo = d.loc[test, "agit_hoy"]
        rho.append(float(spearmanr(pred, real).statistic))
        err_m = float(np.sqrt(np.mean((pred - real) ** 2)))
        err_i = float(np.sqrt(np.mean((ingenuo - real) ** 2)))
        mejora.append(1 - err_m / err_i)
    return float(np.mean(rho)), float(np.mean(mejora))


def tren_ok(d):
    return d["agit_futura"].notna() & d["agit_hoy"].notna()


if __name__ == "__main__":
    d = base()
    print("filas utiles:", len(d), "| horizonte:", H, "velas", flush=True)
    ac, ba = prueba_direccion(d)
    print(f"\nDIRECCION: el modelo acierta {ac*100:.2f} %. El truco de 'siempre decir mayoria' saca {ba*100:.2f} %.")
    print(f"           ventaja real: {(ac-ba)*100:+.2f} puntos")
    rho, me = prueba_agitacion(d, "nivel")
    print(f"\nAGITACION pidela como NIVEL  : correlacion de rango {rho:.3f}, "
          f"y contra 'sigue igual' {'gana' if me>0 else 'PIERDE'} por {abs(me)*100:.1f} %.")
    rho2, me2 = prueba_agitacion(d, "razon")
    print(f"AGITACION pidela como CAMBIO : correlacion de rango {rho2:.3f}, "
          f"y contra 'sigue igual' {'gana' if me2>0 else 'PIERDE'} por {abs(me2)*100:.1f} %.")
    print("           La conclusion cambia segun como se pregunte. Sirve para dimensionar")
    print("           el riesgo, no para prometer ganancias.")
    out = {"direccion_acierto": round(ac, 4), "direccion_base": round(ba, 4),
           "direccion_ventaja": round(ac - ba, 4),
           "agitacion_nivel_spearman": round(rho, 4), "agitacion_nivel_mejora": round(me, 4),
           "agitacion_cambio_spearman": round(rho2, 4), "agitacion_cambio_mejora": round(me2, 4),
           "respuesta_corta": ("la direccion no se puede predecir; la agitacion solo un poco, "
                              "y nada mas si se pide como cambio, no como nivel")}
    with open(os.path.join(RAIZ, "resultados", "que_se_puede_predecir.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nguardado en resultados/que_se_puede_predecir.json")
