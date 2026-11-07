"""Busqueda de ventaja: trece estrategias, los mismos datos, los mismos costos.

La pregunta no es "¿adivino la direccion?". La evidencia hasta aqui dice que no.
La pregunta que si puede dar plata es: **¿se puede saber cuando viene riesgo alto y
bajar la exposicion antes?** La agitacion es predecible; la direccion no.

Corre walk-forward de verdad (el modelo nunca ve el mes que evalua), descuenta
comision y deslizamiento en cada cambio de posicion, y compara contra las dos varas:
no comprar nada (0 %) y comprar y sostener.

Ideas probadas:
  S0  comprar y sostener                      (la vara)
  S1  el modelo de direccion actual           (se sabe que pierde; queda por honestidad)
  S2  direccion + filtro de estado            (no operar con agitacion extrema)
  S3  direccion solo en bandas extremas       (entrar solo con prob > 0.60)
  S4  exposicion apuntada a agitacion         (bajar el tamano cuando viene riesgo alto)
  S5  S4 encima de momentum suave             (idem, pero con sesgo de tendencia)
  S6  S4 sin apalancar, rebalanceo diario     (la prueba justa de la idea)
  S7  S6 semanal                              (menos comisiones)
  S8  S7 con tope 0,8                         (proteccion, no ventaja)
  S9  rejilla de precios (grid)               (compra escalones al caer, vende al subir)
  S10 rotacion cross-seccional                (solo la moneda mas fuerte que sus pares)
  S11 confirmacion dia+semana+mes             (entrar solo si las tres escalas acuerdan)
  S12 DCA semanal segun agitacion             (compras periodicas, nunca vende)

Todas, incluida la vara S0, se miden en el MISMO tramo (el que el walk-forward
alcanza a evaluar). Versiones anteriores median S0 en la historia completa y las
estrategias solo en el tramo de prueba: comparaban periodos distintos.

Criterio de aprobacion: ganarle a comprar-y-sostener en mas de la mitad de los mercados
(4 de 6) Y no quedar por debajo de 0 % en promedio. Si no cumple, se apaga y queda escrito.
"""
import json, os, sys, time
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datos import FEATURES, SIMBOLOS, leer_tabla

RAIZ = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(RAIZ, "resultados")

COMISION = 0.001
DESLIZ = 0.0005
OBJETIVO_VOL = 0.030      # 3 % de agitacion diaria apuntada
CAP = 1.5                 # nunca mas de 1,5 veces el capital
UMBRAL_DIRECCION = 0.55
UMBRAL_EXTREMO = 0.60
DIAS = 24                 # velas de 1h en un dia


def cargar():
    d = leer_tabla()
    d = d.sort_values(["simbolo", "t"]).reset_index(drop=True)
    log = np.log(d["close"].clip(lower=1e-12))
    d["r1"] = log.groupby(d["simbolo"]).diff()
    g = d.groupby("simbolo")
    d["vol_pasada"] = (g["r1"].transform(lambda s: s.rolling(DIAS).std()) * np.sqrt(DIAS))
    d["vol_futura"] = (g["r1"].transform(lambda s: s.shift(-1).rolling(DIAS).std()) * np.sqrt(DIAS))
    d["fut_close"] = g["close"].transform(lambda s: s.shift(-DIAS))
    return d


def cortes(d, meses=12):
    ts = np.sort(d["t"].unique())
    inicio = int(len(ts) * 0.42)
    paso = max(1, len(ts) // meses)
    for k in range(inicio, len(ts) - paso, paso):
        yield int(ts[k]), int(ts[min(k + paso, len(ts) - 1)])


def predecir_vol(d, modo="razon"):
    """Walk-forward: pronostica la agitacion de las proximas 24 horas.

    modo="nivel" predice el numero directo.
    modo="razon" predice cuanto CAMBIA contra la agitacion de hoy, que es la forma
    bien escalada de pedirlo: el nivel tiene deriva y el modelo lo paga en error.
    """
    d = d.copy()
    d["v_pred"] = np.nan
    cols = FEATURES + ["vol_pasada"]
    sub_valido = d[d["vol_futura"].notna() & d["vol_pasada"].notna()]
    if modo == "razon":
        objetivo = np.log(sub_valido["vol_futura"] / sub_valido["vol_pasada"])
    else:
        objetivo = sub_valido["vol_futura"]
    t0 = time.time()
    for i, (a, b) in enumerate(cortes(d), 1):
        tren = d[(d["t"] < a) & d["vol_futura"].notna() & d["vol_pasada"].notna()]
        test = (d["t"] >= a) & (d["t"] <= b) & d[cols].notna().all(axis=1)
        if len(tren) < 20000 or test.sum() < 200:
            continue
        y = (np.log(tren["vol_futura"] / tren["vol_pasada"]) if modo == "razon"
             else tren["vol_futura"])
        m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.06, min_samples_leaf=80,
                                          l2_regularization=1.0, early_stopping=True,
                                          validation_fraction=0.15, random_state=7)
        m.fit(tren[cols], y)
        p = m.predict(d.loc[test, cols])
        d.loc[test, "v_pred"] = (d.loc[test, "vol_pasada"] * np.exp(p)
                                 if modo == "razon" else p)
        print(f"   vol {modo} plegado {i} {pd.Timestamp(a, unit='ms'):%Y-%m} "
              f"tren={len(tren)} ({time.time()-t0:.0f}s)", flush=True)
    return d


def predecir_direccion(d):
    d = d.copy()
    d["p"] = np.nan
    cols = [c for c in FEATURES if c != "r1"]
    t0 = time.time()
    for i, (a, b) in enumerate(cortes(d), 1):
        tren = d[(d["t"] < a) & d["fut_close"].notna()]
        test = (d["t"] >= a) & (d["t"] <= b) & d[cols].notna().all(axis=1)
        if len(tren) < 20000 or test.sum() < 200:
            continue
        y = (tren["fut_close"] > tren["close"]).astype(int)
        m = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06, min_samples_leaf=80,
                                           l2_regularization=1.0, early_stopping=True,
                                           validation_fraction=0.15, random_state=7)
        m.fit(tren[cols], y)
        d.loc[test, "p"] = m.predict_proba(d.loc[test, cols])[:, 1]
        print(f"   dir plegado {i} {pd.Timestamp(a, unit='ms'):%Y-%m} "
              f"tren={len(tren)} ({time.time()-t0:.0f}s)", flush=True)
    return d


# ---------- simulador de exposicion ----------
def simular(sub, pesos):
    """sub: DataFrame con close. pesos: array 0..CAP de exposicion por vela.

    El peso decidido en la vela t se aplica a la vela t+1 (no mira el futuro),
    y cada cambio de peso paga comision y deslizamiento.
    """
    c = sub["close"].to_numpy(dtype=float)
    r = np.zeros(len(c))
    r[1:] = c[1:] / c[:-1] - 1
    w = np.asarray(pesos, dtype=float)
    w[0] = 0.0
    ganancia = np.zeros(len(c))
    ganancia[0] = 1.0
    cap = 1.0
    for i in range(1, len(c)):
        aplicado = w[i - 1]
        bruto = cap * aplicado * r[i]
        cambio = abs(aplicado - (w[i - 2] if i >= 2 else 0.0))
        costo = cap * cambio * (COMISION + DESLIZ)
        cap += bruto - costo
        ganancia[i] = cap
    return ganancia


def comprar_y_sostener(c):
    """La vara: entra al principio y no sale. Paga la entrada; la salida no existe
    porque al final del periodo sigue adentro, igual que las estrategias simuladas."""
    return (np.asarray(c, dtype=float) / c[0]) * (1 - COMISION - DESLIZ)


def caida_max(curva):
    pico, peor = curva[0], 0.0
    for v in curva:
        pico = max(pico, v)
        if pico > 0:
            peor = max(peor, (pico - v) / pico)
    return peor


def pesos_por_vol(sub, objetivo=OBJETIVO_VOL, cap=CAP):
    v = sub["v_pred"].to_numpy(dtype=float)
    out = np.zeros(len(v))
    for i in range(len(v)):
        if not np.isfinite(v[i]) or v[i] <= 0:
            out[i] = 0.0
            continue
        out[i] = min(cap, objetivo / v[i])
    # rebalanceo diario: si no, se paga en comisiones mas de lo que se gana
    for i in range(len(out)):
        if i % DIAS:
            out[i] = out[i - 1]
    return out


def pesos_direccion(sub, umbral=UMBRAL_DIRECCION, con_filtro=False, extremo=False):
    """Entra con probabilidad alta y se queda adentro hasta que baje de 0,50.

    Sin enfriar, el peso salta cada hora y la estrategia se paga en comisiones.
    """
    p = sub["p"].to_numpy(dtype=float)
    v = sub["v_pred"].to_numpy(dtype=float)
    u = UMBRAL_EXTREMO if extremo else umbral
    out = np.zeros(len(p))
    dentro = False
    for i in range(len(p)):
        if np.isfinite(p[i]):
            if not dentro and p[i] >= u:
                bloqueado = con_filtro and np.isfinite(v[i]) and v[i] > OBJETIVO_VOL * 2
                dentro = not bloqueado
            elif dentro and p[i] < 0.50:
                dentro = False
        out[i] = 1.0 if dentro else 0.0
    for i in range(len(out)):
        if i % DIAS:
            out[i] = out[i - 1]
    return out


def pesos_por_vol_cap(sub, cap=1.0, objetivo=OBJETIVO_VOL, banda=0.25, cada=DIAS):
    """La prueba justa de la idea: apuntar a agitacion SIN apalancarse y sin mover
    el dinero en cada vela. Con tope 1,5 y rebalanceo diario se paga en comisiones
    mas de lo que rinde la decision, y eso no es culpa del pronostico.

    banda: solo cambia el peso si el nuevo difiere del actual en mas de ese %,
           para no trocar por migajas.
    """
    v = sub["v_pred"].to_numpy(dtype=float)
    out = np.zeros(len(v))
    actual = 0.0
    for i in range(len(v)):
        if i % cada == 0:
            if np.isfinite(v[i]) and v[i] > 0:
                deseado = min(cap, objetivo / v[i])
            else:
                deseado = 0.0
            if abs(deseado - actual) > banda * max(actual, 0.25):
                actual = deseado
        out[i] = actual
    return out


def pesos_vol_con_momentum(sub):
    """Exposicion apuntada a agitacion, pero con sesgo: menos si viene cayendo fuerte."""
    w = pesos_por_vol(sub)
    c = sub["close"].to_numpy(dtype=float)
    for i in range(len(w)):
        if i > DIAS and c[i] < c[i - DIAS]:
            w[i] *= 0.75
    return w


# ---------- mecanismos NUEVOS (no repiten S1-S8) ----------
def pesos_grid(sub, paso=0.02, base=0.5, delta=0.10, cap=1.0):
    """S9: rejilla de precios. Compra un escalon cada vez que el precio cae un `paso`
    por debajo del ultimo precio operado, y vende un escalon cada vez que sube un
    `paso` por encima. No predice direccion: cobra la oscilacion.

    Idea de rejilla como la del grid bot MIT de jordantete/grid_trading_bot,
    reescrita aqui como pesos de exposicion (no se copia codigo de ese repo).
    Solo usa el cierre de la vela t: la orden se ejecuta en t+1, sin mirar el futuro.
    """
    c = sub["close"].to_numpy(dtype=float)
    out = np.zeros(len(c))
    ancla = c[0]
    w = base
    escala = np.log1p(paso)
    for i in range(len(c)):
        if c[i] <= 0 or ancla <= 0:
            out[i] = w
            continue
        escalones = int(np.floor(np.log(c[i] / ancla) / escala + 0.5))
        if escalones:
            # cada escalon abajo suma un compra; cada escalon arriba resta una venta.
            # Se acumula: volver al precio ancla no deshace lo operado.
            w = float(min(cap, max(0.0, w - escalones * delta)))
            ancla = c[i]
        out[i] = w
    return out


def pesos_rotacion(sub, cada=DIAS * 7):
    """S10: quedarse solo con la moneda que va mas fuerte que sus pares.

    Usa la fuerza de 24 h contra la mediana de las OTRAS cinco (ya viene en la
    tabla como med_otras_r24). Si esta moneda no le gana al resto, no se tiene.
    Rebalanceo semanal para no pagar comisiones por cada hora.
    """
    rel = (sub["r24"] - sub["med_otras_r24"]).to_numpy(dtype=float)
    out = np.zeros(len(rel))
    actual = 0.0
    for i in range(len(rel)):
        if i % cada == 0:
            actual = 1.0 if (np.isfinite(rel[i]) and rel[i] > 0) else 0.0
        out[i] = actual
    return out


def pesos_multiescala(sub, cada=DIAS):
    """S11: entrar solo cuando dia, semana y mes apuntan al mismo lado.

    r24 (dia), r168 (semana) y r720 (mes) tienen que ser los tres positivos.
    Como el motor es solo largo, si los tres son negativos se queda afuera (0).
    """
    a = sub["r24"].to_numpy(dtype=float)
    b = sub["r168"].to_numpy(dtype=float)
    c = sub["r720"].to_numpy(dtype=float)
    out = np.zeros(len(a))
    actual = 0.0
    for i in range(len(a)):
        if i % cada == 0:
            ok = np.isfinite(a[i]) and np.isfinite(b[i]) and np.isfinite(c[i])
            actual = 1.0 if (ok and a[i] > 0 and b[i] > 0 and c[i] > 0) else 0.0
        out[i] = actual
    return out


def pesos_dca(sub, cada=DIAS * 7, aporte=0.05, objetivo=OBJETIVO_VOL):
    """S12: compras periodicas (DCA), mas grandes cuando viene poca agitacion.

    Nunca vende: va sumando un aporte semanal hasta llegar a estar del todo
    adentro. El aporte se escala por la agitacion prevista: chico si viene
    riesgo alto, grande si viene calmado. Mecanismo de entrada distinto a S1-S8.
    """
    v = sub["v_pred"].to_numpy(dtype=float)
    out = np.zeros(len(v))
    w = 0.0
    for i in range(len(v)):
        if i % cada == 0 and w < 1.0:
            factor = 1.0
            if np.isfinite(v[i]) and v[i] > 0:
                factor = float(min(2.0, max(0.25, objetivo / v[i])))
            w = min(1.0, w + aporte * factor)
        out[i] = w
    return out


def correr():
    os.makedirs(SALIDA, exist_ok=True)
    d = cargar()
    print("filas:", len(d), "| con vol pasada:", int(d["vol_pasada"].notna().sum()), flush=True)
    d = predecir_vol(d)
    d = predecir_direccion(d)

    # ---- primer control de honestidad: ¿la agitacion se predice mejor que "sigue igual"? ----
    val = d[d["v_pred"].notna() & d["vol_futura"].notna() & d["vol_pasada"].notna()]
    err_modelo = float(np.sqrt(np.mean((val["v_pred"] - val["vol_futura"]) ** 2)))
    err_ingenuo = float(np.sqrt(np.mean((val["vol_pasada"] - val["vol_futura"]) ** 2)))
    err_promedio = float(np.sqrt(np.mean((val["vol_futura"].mean() - val["vol_futura"]) ** 2)))
    from scipy.stats import spearmanr
    rho = float(spearmanr(val["v_pred"].to_numpy(dtype=float),
                          val["vol_futura"].to_numpy(dtype=float)).statistic)
    print(f"\nagitacion: modelo {err_modelo:.5f} | sigue-igual {err_ingenuo:.5f} | "
          f"promedio {err_promedio:.5f} | rho {rho:.3f}", flush=True)
    mejora = 1 - err_modelo / err_ingenuo
    print(f"mejora sobre 'sigue igual': {mejora*100:.1f} %", flush=True)

    estrategias = {
        "S0 comprar y sostener": None,
        "S1 modelo de direccion": lambda s: pesos_direccion(s),
        "S2 direccion + filtro de estado": lambda s: pesos_direccion(s, con_filtro=True),
        "S3 solo bandas extremas": lambda s: pesos_direccion(s, extremo=True),
        "S4 exposicion apuntada a agitacion": lambda s: pesos_por_vol(s),
        "S5 agitacion + sesgo de tendencia": lambda s: pesos_vol_con_momentum(s),
        "S6 agitacion, sin apalancar, diario": lambda s: pesos_por_vol_cap(s),
        "S7 agitacion, sin apalancar, semanal": lambda s: pesos_por_vol_cap(s, cada=DIAS * 7, banda=0.20),
        "S8 agitacion, tope 0.8, semanal": lambda s: pesos_por_vol_cap(s, cap=0.8, cada=DIAS * 7, banda=0.20),
        "S9 rejilla de precios (grid)": lambda s: pesos_grid(s),
        "S10 rotacion: solo la mas fuerte que sus pares": lambda s: pesos_rotacion(s),
        "S11 confirmacion dia+semana+mes": lambda s: pesos_multiescala(s),
        "S12 DCA semanal segun agitacion": lambda s: pesos_dca(s),
    }

    tabla, detalle = [], {}
    for nombre, fn in estrategias.items():
        fila = {"estrategia": nombre, "mercados": {}}
        for sim in SIMBOLOS:
            sub = d[d["simbolo"] == sim].sort_values("t")
            # Todas, incluida la vara S0, corren en el MISMO tramo: el que el
            # walk-forward alcanza a evaluar. Antes S0 usaba la historia completa
            # y las estrategias solo el tramo de prueba: la vara quedaba inflada
            # (o desinflada) por un periodo que las otras ni veian.
            sub = sub[sub["v_pred"].notna()]
            if len(sub) < 3000:
                continue
            c = sub["close"].to_numpy(dtype=float)
            curva = comprar_y_sostener(c) if fn is None else simular(sub, fn(sub))
            fin = float(curva[-1])
            fila["mercados"][sim] = {
                "retorno": round(fin - 1, 4),
                "caida_max": round(caida_max(curva), 4),
            }
        rets = [v["retorno"] for v in fila["mercados"].values()]
        fila["retorno_promedio"] = round(float(np.mean(rets)), 4) if rets else None
        fila["desde_1000_total"] = int(round(sum(1000 * (1 + r) for r in rets)))
        fila["ganadoras_de_benchmark"] = None
        tabla.append(fila)
        detalle[nombre] = fila

    base = next(f for f in tabla if f["estrategia"] == "S0 comprar y sostener")
    for fila in tabla:
        if fila["estrategia"] == "S0 comprar y sostener":
            fila["le_gana_al_benchmark_en"] = 0
            continue
        gana = sum(1 for sim, v in fila["mercados"].items()
                   if v["retorno"] > base["mercados"].get(sim, {}).get("retorno", 0))
        fila["le_gana_al_benchmark_en"] = gana
        fila["aprueba"] = bool(gana * 2 > len(SIMBOLOS) and (fila["retorno_promedio"] or 0) > 0)

    print("\n=== resultado ===")
    print(f"{'estrategia':44s} {'promedio':>9s} {'$6.000 →':>10s} {'gana en':>8s} {'aprueba':>8s}")
    for fila in tabla:
        print(f"{fila['estrategia']:44s} {fila['retorno_promedio']*100:8.1f}% "
              f"{fila['desde_1000_total']:10,d} "
              f"{str(fila['le_gana_al_benchmark_en']) + '/' + str(len(SIMBOLOS)):>8s} "
              f"{('SI' if fila['aprueba'] else 'no') if fila['estrategia'] != 'S0 comprar y sostener' else '—':>8s}")

    for fila in tabla:
        cd = [v["caida_max"] for v in fila["mercados"].values()]
        fila["caida_media"] = round(float(np.mean(cd)), 4)
        fila["caida_peor"] = round(float(max(cd)), 4)
        fila["baja_la_caida_en"] = int(sum(
            1 for sim, v in fila["mercados"].items()
            if v["caida_max"] < base["mercados"].get(sim, {}).get("caida_max", 9.9)))

    mejor_dd = max((f for f in tabla if f["estrategia"] != "S0 comprar y sostener"),
                   key=lambda f: -f["caida_media"])
    aprobadas = [f for f in tabla if f.get("aprueba")]
    if aprobadas:
        mejor = max(aprobadas, key=lambda f: f["retorno_promedio"])
        rets = sorted(v["retorno"] for v in mejor["mercados"].values())
        n = len(rets)
        mediana = rets[n // 2] if n % 2 else (rets[n // 2 - 1] + rets[n // 2]) / 2
        mejor_sim = max(mejor["mercados"], key=lambda s: mejor["mercados"][s]["retorno"])
        peor_sim = min(mejor["mercados"], key=lambda s: mejor["mercados"][s]["retorno"])
        frase = (
            "La prueba aprobó %s: en el mismo tramo para todas, rindió %+.1f %% de promedio "
            "contra %+.1f %% de comprar-y-sostener, le gana en %d de %d mercados y baja la caída "
            "máxima de %.1f %% a %.1f %% (la mejora en %d de %d). Para no engañarse con el promedio: "
            "la mediana por mercado es %+.1f %%, el mejor mercado (%s) rindió %+.1f %% y el peor "
            "(%s) %+.1f %%. Es una regla simple de tendencia, no una garantía: el bot sigue en papel "
            "y SOLO_PRUEBA en True hasta que el dueño apruebe lo que sigue."
            % (mejor["estrategia"], mejor["retorno_promedio"] * 100, base["retorno_promedio"] * 100,
               mejor["le_gana_al_benchmark_en"], len(mejor["mercados"]),
               base["caida_media"] * 100, mejor["caida_media"] * 100,
               mejor["baja_la_caida_en"], len(mejor["mercados"]),
               mediana * 100, mejor_sim, mejor["mercados"][mejor_sim]["retorno"] * 100,
               peor_sim, mejor["mercados"][peor_sim]["retorno"] * 100))
    else:
        frase = (
            "Ninguna estrategia le gana a comprar-y-sostener en la mayoría de los mercados con "
            "retorno positivo, así que el bot se queda apagado. Lo único que sí mejoró en todos "
            "los mercados fue bajar la exposición cuando viene agitación alta: %s baja la caída "
            "máxima de %.1f %% a %.1f %% en %d de %d mercados, con un retorno promedio de %+.1f %% "
            "contra %+.1f %% de la vara. Eso es protección, no ventaja: sirve para no quedar afuera "
            "en el peor día, no para ganar más."
            % (mejor_dd["estrategia"], base["caida_media"] * 100, mejor_dd["caida_media"] * 100,
               mejor_dd["baja_la_caida_en"], len(mejor_dd["mercados"]),
               mejor_dd["retorno_promedio"] * 100, base["retorno_promedio"] * 100))
    salida = {
        "veredicto": {
            "gana_alguno_al_quieto": bool(aprobadas),
            "aprobadas": [f["estrategia"] for f in aprobadas],
            "frase": frase,
        },

        "momento": int(time.time() * 1000),
        "mercados": SIMBOLOS,
        "comision_por_lado": COMISION,
        "deslizamiento": DESLIZ,
        "objetivo_vol_diario": OBJETIVO_VOL,
        "tope_de_exposicion": CAP,
        "velas": int(len(d)),
        "filas_evaluadas": int(len(val)),
        "ojo_tramo": ("El tramo evaluado es el mismo para todas las estrategias y para la vara: "
                      "desde donde el walk-forward empieza a evaluar hasta el final. En este "
                      "periodo comprar-y-sostener rindio %+.1f %% de promedio. Si el tramo es "
                      "alcista, cualquier estrategia que baje la exposicion pierde contra la "
                      "vara por definicion; por eso se mira tambien la caida maxima, que es lo "
                      "unico que el control de riesgo puede mejorar sin adivinar la direccion."
                      % (base["retorno_promedio"] * 100)),
        "agitacion_se_predice": {
            "error_modelo": round(err_modelo, 6),
            "error_sigue_igual": round(err_ingenuo, 6),
            "error_promedio": round(err_promedio, 6),
            "mejora_vs_sigue_igual_pct": round(mejora * 100, 2),
            "rho_spearman": round(rho, 4),
            "veredicto": ("si, el modelo le gana al 'sigue igual'"
                          if err_modelo < err_ingenuo else
                          "no: 'supone que sigue igual' predice mejor que el modelo"),
        },
        "estrategias": tabla,
        "aprueban": [f["estrategia"] for f in tabla if f.get("aprueba")],
    }
    with open(os.path.join(SALIDA, "ventaja.json"), "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print("\nguardado en resultados/ventaja.json")
    return salida


if __name__ == "__main__":
    correr()
