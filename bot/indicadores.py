"""Indicadores técnicos calculados con la librería `ta` (D1).

MACD, Bollinger, ADX, VWAP, RSI y ATR sobre velas OHLCV públicas.
No usa claves ni opera: sólo lectura para el gráfico del panel.
"""
import math

import pandas as pd
import ta


def _df(velas):
    """Acepta lista de dicts {t,o,h,l,c,v} o DataFrame; devuelve DataFrame normalizado."""
    if isinstance(velas, pd.DataFrame):
        d = velas.copy()
        ren = {"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
        d = d.rename(columns={k: v for k, v in ren.items() if k in d.columns})
    else:
        d = pd.DataFrame(velas, columns=["t", "o", "h", "l", "c", "v"])
        d = d.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    for col in ("open", "high", "low", "close", "volume"):
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.dropna(subset=["close"]).reset_index(drop=True)
    return d


def _serie_a_lista(serie, timestamps):
    """Convierte una Serie a lista de {t, v} omitiendo NaN/inf."""
    out = []
    vals = serie.values if hasattr(serie, "values") else serie
    for i, v in enumerate(vals):
        if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            continue
        out.append({"t": int(timestamps[i]), "v": round(float(v), 8)})
    return out


def calcular(velas):
    """Calcula MACD(12,26,9), Bollinger(20,2), ADX(14), VWAP(14), RSI(14), ATR(14).

    velas: lista de dicts con t (segundos unix), o, h, l, c, v.
    Devuelve dict con macd{line,signal,hist}, bollinger{upper,middle,lower},
    adx{adx,di_plus,di_minus}, vwap[], rsi[], atr[]. Cada punto es {t, v}.
    """
    d = _df(velas)
    if len(d) < 2:
        return {"macd": {"line": [], "signal": [], "hist": []},
                "bollinger": {"upper": [], "middle": [], "lower": []},
                "adx": {"adx": [], "di_plus": [], "di_minus": []},
                "vwap": [], "rsi": [], "atr": []}

    ts = d["t"].astype(int).tolist() if "t" in d.columns else list(range(len(d)))
    c, h, l, v = d["close"], d["high"], d["low"], d["volume"]

    macd_ind = ta.trend.MACD(c, window_slow=26, window_fast=12, window_sign=9)
    bb = ta.volatility.BollingerBands(c, window=20, window_dev=2)
    # ta necesita al menos 28 velas para ADX y 14 para ATR. Un mercado
    # nuevo no debe impedir calcular los demás indicadores disponibles.
    adx_ind = ta.trend.ADXIndicator(h, l, c, window=14) if len(d) >= 28 else None
    vwap_ind = ta.volume.VolumeWeightedAveragePrice(h, l, c, v, window=14)
    rsi_ind = ta.momentum.RSIIndicator(c, window=14)
    atr_ind = ta.volatility.AverageTrueRange(h, l, c, window=14) if len(d) >= 14 else None

    return {
        "macd": {
            "line": _serie_a_lista(macd_ind.macd(), ts),
            "signal": _serie_a_lista(macd_ind.macd_signal(), ts),
            "hist": _serie_a_lista(macd_ind.macd_diff(), ts),
        },
        "bollinger": {
            "upper": _serie_a_lista(bb.bollinger_hband(), ts),
            "middle": _serie_a_lista(bb.bollinger_mavg(), ts),
            "lower": _serie_a_lista(bb.bollinger_lband(), ts),
        },
        "adx": {
            "adx": _serie_a_lista(adx_ind.adx().iloc[27:], ts[27:]) if adx_ind else [],
            "di_plus": _serie_a_lista(adx_ind.adx_pos().iloc[14:], ts[14:]) if adx_ind else [],
            "di_minus": _serie_a_lista(adx_ind.adx_neg().iloc[14:], ts[14:]) if adx_ind else [],
        },
        "vwap": _serie_a_lista(vwap_ind.volume_weighted_average_price(), ts),
        "rsi": _serie_a_lista(rsi_ind.rsi(), ts),
        "atr": _serie_a_lista(atr_ind.average_true_range().iloc[13:], ts[13:]) if atr_ind else [],
    }