"""Descarga velas públicas de Binance y arma la tabla de features.

No usa ninguna clave: el repositorio histórico es público.
"""
import csv, codecs, io, os, sys, time, zipfile, urllib.request
import numpy as np
import pandas as pd

RAIZ = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(RAIZ, "datos")
BASE = "https://data.binance.vision/data/spot/monthly/klines"
COLS = ["t","open","high","low","close","volumen","tcierre","cotizacion",
        "operaciones","compra_base","compra_cotizada","ignorado"]

SIMBOLOS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","DOGEUSDT"]
INTERVALO = "1h"
DESDE = (2023, 1)
HASTA = (2026, 10)


def meses():
    y, m = DESDE
    fy, fm = HASTA
    while (y, m) <= (fy, fm):
        yield f"{y}-{m:02d}"
        m += 1
        if m == 13:
            y, m = y + 1, 1


def bajar_mes(simbolo, anio_mes, reintentos=4):
    ruta = os.path.join(DATOS, f"{simbolo}_{INTERVALO}.csv")
    url = f"{BASE}/{simbolo}/{INTERVALO}/{simbolo}-{INTERVALO}-{anio_mes}.zip"
    for intento in range(reintentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "HeliosBot/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                crudo = r.read()
            with zipfile.ZipFile(io.BytesIO(crudo)) as z:
                with z.open(z.namelist()[0]) as raw:
                    filas = list(csv.reader(codecs.iterdecode(raw, "utf-8")))
            tabla = pd.DataFrame(filas, columns=COLS)
            for c in COLS[1:]:
                tabla[c] = pd.to_numeric(tabla[c], errors="coerce")
            tabla["t"] = pd.to_numeric(tabla["t"], errors="coerce").astype("int64")
            # Binance publica en microsegundos los archivos desde 2025-01
            tabla.loc[tabla["t"] > 10**14, "t"] //= 1000
            tabla = tabla.dropna(subset=["close"])
            if os.path.exists(ruta):
                viejo = pd.read_csv(ruta)
                tabla = pd.concat([viejo, tabla], ignore_index=True)
            tabla = (tabla.drop_duplicates(subset="t").sort_values("t").reset_index(drop=True))
            tabla.to_csv(ruta, index=False)
            return len(filas)
        except Exception as e:
            if tipo_red(f"{type(e).__name__}: {e}") == 404:
                return -1
            time.sleep(1.5 * (intento + 1))
    return 0


def tipo_red(msg):
    return 404 if "404" in msg else 0


def ya_descargado(simbolo):
    ruta = os.path.join(DATOS, f"{simbolo}_{INTERVALO}.csv")
    if not os.path.exists(ruta):
        return set()
    t = pd.read_csv(ruta, usecols=["t"])["t"]
    return {pd.Timestamp(int(x), unit="ms").strftime("%Y-%m") for x in t}


def features(simbolo):
    """Todo lo de la fila t usa sólo información cerrada hasta t. La etiqueta mira t+1."""
    ruta = os.path.join(DATOS, f"{simbolo}_{INTERVALO}.csv")
    d = pd.read_csv(ruta).sort_values("t").reset_index(drop=True)
    c = d["close"]
    log = np.log(c.clip(lower=1e-12))

    d["r1"] = log.diff()
    for n in (4, 24, 72, 168, 720):
        d[f"r{n}"] = log.diff(n)

    delta = log.diff()
    sube = delta.clip(lower=0).rolling(14).mean()
    baja = (-delta.clip(upper=0)).rolling(14).mean()
    d["rsi"] = 100 - 100 / (1 + sube / baja.replace(0, np.nan))

    tr = pd.concat([d["high"] - d["low"],
                    (d["high"] - c.shift()).abs(),
                    (d["low"] - c.shift()).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(14).mean()
    d["atr_ratio"] = d["atr"] / d["atr"].rolling(168).mean()
    d["cuerpo"] = (tr / c.replace(0, np.nan)).rolling(14).mean()

    for n in (20, 50, 200):
        d[f"dist_sma{n}"] = c / c.rolling(n).mean() - 1
    d["max_168"] = d["high"].rolling(168).max()
    d["min_168"] = d["low"].rolling(168).min()
    d["pos_rango"] = (c - d["min_168"]) / (d["max_168"] - d["min_168"]).replace(0, np.nan)

    v = d["cotizacion"]
    d["vol_z"] = (v - v.rolling(48).mean()) / v.rolling(48).std().replace(0, np.nan)
    d["flujo"] = (d["compra_cotizada"] / v.replace(0, np.nan)) - 0.5

    hora = (pd.to_datetime(d["t"], unit="ms", utc=True).dt.hour)
    d["hora_s"] = np.sin(2 * np.pi * hora / 24)
    d["hora_c"] = np.cos(2 * np.pi * hora / 24)
    d["finde"] = (pd.to_datetime(d["t"], unit="ms", utc=True).dt.day_of_week >= 5).astype(int)

    d["etiqueta_ret"] = log.shift(-1) - log
    d["sube"] = (d["etiqueta_ret"] > 0).astype(int)
    d["simbolo"] = simbolo
    return d.drop(columns=["max_168", "min_168"])


FEATURES = ["r1","r4","r24","r72","r168","r720","rsi","atr_ratio","cuerpo",
            "dist_sma20","dist_sma50","dist_sma200","pos_rango","vol_z","flujo",
            "hora_s","hora_c","finde","med_otras_r1","med_otras_r24","disp_pares"]


def arma_tabla():
    tablas = [features(s) for s in SIMBOLOS]
    d = pd.concat(tablas, ignore_index=True)
    piv = d.pivot_table(index="t", columns="simbolo", values="r1", aggfunc="first")
    med = piv.median(axis=1)
    disp = piv.std(axis=1)
    piv24 = d.pivot_table(index="t", columns="simbolo", values="r24", aggfunc="first")
    d = d.merge(pd.DataFrame({"med_otras_r1": med, "disp_pares": disp,
                              "med_otras_r24": piv24.median(axis=1)}).rename_axis("t").reset_index(),
                on="t", how="left")
    # la mediana del propio simbolo no debe contaminar la lectura del resto
    for i, s in enumerate(SIMBOLOS):
        m = d["simbolo"] == s
        otras = [p for j, p in enumerate(SIMBOLOS) if j != i]
        sub = d.loc[m, "t"]
        d.loc[m, "med_otras_r1"] = sub.map(piv[otras].median(axis=1))
        d.loc[m, "med_otras_r24"] = sub.map(piv24[otras].median(axis=1))
    d = d.sort_values(["simbolo", "t"]).reset_index(drop=True)
    d.to_pickle(os.path.join(DATOS, "tabla.pkl"))
    return d


if __name__ == "__main__":
    os.makedirs(DATOS, exist_ok=True)
    total = 0
    for s in SIMBOLOS:
        listos = ya_descargado(s)
        pendientes = [m for m in meses() if m not in listos]
        print(f"{s}: {len(listos)} meses en cache, {len(pendientes)} por bajar", flush=True)
        for k, m in enumerate(pendientes, 1):
            n = bajar_mes(s, m)
            if n == -1:
                print(f"   {m} no existe todavia", flush=True)
            total += max(n, 0)
            if k % 12 == 0 or k == len(pendientes):
                print(f"   {s} {m}  [{k}/{len(pendientes)}]", flush=True)
    print("velas descargadas:", total, flush=True)
    d = arma_tabla()
    print("tabla final:", d.shape, "| filas con etiqueta:", int(d["sube"].notna().sum()), flush=True)
