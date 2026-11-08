"""Cartera en papel para operar a mano (partes C1 a C4).

Plata falsa, precios reales. Es una cuenta aparte del bot S11 (esa vive en
posiciones.json y se mira en "El bot"). Aca el dueño prueba las ordenes
inteligentes: entrada a mercado o limite, stop-loss, take-profit (en partes)
y trailing stop. No mueve dinero real: exchange.SOLO_PRUEBA sigue en True.

Reusa el mismo Broker del backtest (ejecutor.py), asi que las ordenes se
resuelven con las mismas reglas duras: el stop antes que el objetivo en la
misma vela, comision y deslizamiento siempre descontados.

Los parametros de la orden vienen en fracciones (stop_loss=0.015 es 1,5 %).
El panel convierte los porcentajes que escribe el dueño antes de mandarlos.
"""
import json, math, os, time
from dataclasses import asdict

from ejecutor import Broker, Configuracion, Operacion

RAIZ = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(RAIZ, "cartera_manual.json")
CAPITAL_POR_MERCADO = 1000.0
SIMBOLOS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]

# parametros de orden elegibles; el resto usa el default del Broker
PARAMS_CFG = ("riesgo_por_operacion", "stop_loss", "take_profit", "trailing_stop")
# topes sanos para lo que escribe el dueño (fracciones). Evita ordenes absurdas.
TOPES = {"riesgo_por_operacion": (0.001, 0.10), "stop_loss": (0.001, 0.50),
         "take_profit": (0.001, 5.0), "trailing_stop": (0.0, 0.50)}


def _finito(v):
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def _clamp(v, lo, hi, default):
    if not _finito(v):
        return default
    return max(lo, min(hi, float(v)))


class CarteraManual:
    """Una cuenta en papel por mercado, persistida en cartera_manual.json."""

    def __init__(self, ruta=RUTA, capital=CAPITAL_POR_MERCADO):
        self.ruta = ruta
        self.capital = capital
        self.estado = {"inicio": int(time.time() * 1000),
                       "capital_por_mercado": capital, "mercados": {}}
        self._cargar()

    def _cargar(self):
        if not os.path.exists(self.ruta):
            return
        try:
            with open(self.ruta, encoding="utf-8") as f:
                g = json.load(f)
        except Exception:
            return
        if isinstance(g, dict) and "mercados" in g:
            self.estado = g
            self.estado.setdefault("inicio", int(time.time() * 1000))
            self.estado.setdefault("capital_por_mercado", self.capital)
            self.estado.setdefault("mercados", {})

    def _cfg(self, m):
        d = m.get("cfg") or {}
        kw = {k: d[k] for k in PARAMS_CFG if k in d}
        if d.get("take_profits"):
            kw["take_profits"] = tuple(tuple(x) for x in d["take_profits"])
        return Configuracion(capital=self.capital, max_velas_en_posicion=720, **kw)

    def _broker(self, sim):
        m = self.estado["mercados"].get(sim, {})
        b = Broker(self._cfg(m))
        b.efectivo = float(m.get("efectivo", self.capital))
        b.posicion = Operacion(**m["posicion"]) if m.get("posicion") else None
        b.operaciones = [Operacion(**o) for o in m.get("operaciones", [])]
        b.curva = list(m.get("curva", []))
        return b

    def _guardar(self, sim, b, ultimo_ts, cfg=None):
        previo = self.estado["mercados"].get(sim, {})
        self.estado["mercados"][sim] = {
            "efectivo": round(b.efectivo, 8),
            "posicion": asdict(b.posicion) if b.posicion else None,
            "operaciones": [asdict(o) for o in b.operaciones],
            "curva": b.curva[-2000:],
            "ultimo_ts": int(ultimo_ts),
            "resumen": b.resumen(),
            "cfg": cfg if cfg is not None else previo.get("cfg", {}),
        }

    def _alimentar(self, b, sim, velas):
        m = self.estado["mercados"].get(sim)
        ultimo = int(m.get("ultimo_ts", 0)) if m else (int(velas[-2]["t"]) if len(velas) > 1 else 0)
        for v in velas:
            if int(v["t"]) > ultimo:
                b.actualizar(sim, int(v["t"]), float(v["o"]), float(v["h"]),
                             float(v["l"]), float(v["c"]))
                b.marca(int(v["t"]), float(v["c"]))
                ultimo = int(v["t"])
        return ultimo

    def colocar_orden(self, sim, velas, params):
        """Abre una posicion en papel. Devuelve (ok, detalle). params en fracciones."""
        if sim not in SIMBOLOS:
            return False, "moneda no permitida"
        if not velas:
            return False, "no hay precio para esa moneda"
        b = self._broker(sim)
        if b.posicion is not None:
            return False, "ya hay una posicion abierta en esa moneda"
        cfg_kw = {}
        for k in PARAMS_CFG:
            if k in params:
                lo, hi = TOPES[k]
                cfg_kw[k] = _clamp(params[k], lo, hi, getattr(Configuracion(), k))
        if params.get("take_profits"):
            tp = []
            for par in list(params["take_profits"])[:4]:
                if isinstance(par, (list, tuple)) and len(par) == 2 and _finito(par[0]) and _finito(par[1]):
                    tp.append((_clamp(par[0], 0.01, 1.0, 0.5), _clamp(par[1], 0.001, 5.0, 0.03)))
            if tp:
                cfg_kw["take_profits"] = tuple(tp)
        b.cfg = Configuracion(capital=self.capital, max_velas_en_posicion=720, **cfg_kw)
        ultima = velas[-1]
        ts, precio = int(ultima["t"]), float(ultima["c"])
        limite = None
        if params.get("tipo") == "limite":
            if not _finito(params.get("precio_limite")) or float(params["precio_limite"]) <= 0:
                return False, "falta el precio limite"
            limite = float(params["precio_limite"])
        self._alimentar(b, sim, velas)
        if not b.abrir(sim, ts, precio, 0.0, limite=limite):
            return False, "la orden no se pudo abrir (¿monto muy chico?)"
        b.marca(ts, precio)
        cfg_store = {k: v for k, v in cfg_kw.items() if k != "take_profits"}
        if "take_profits" in cfg_kw:
            cfg_store["take_profits"] = [list(x) for x in cfg_kw["take_profits"]]
        self._guardar(sim, b, ts, cfg_store)
        return True, {"simbolo": sim, "tipo": params.get("tipo", "mercado"),
                      "posicion": asdict(b.posicion)}

    def procesar(self, sim, velas):
        """Resuelve la posicion contra las velas nuevas (stop, objetivo, trailing, limite)."""
        b = self._broker(sim)
        ultimo = self._alimentar(b, sim, velas)
        if velas:
            b.marca(int(velas[-1]["t"]), float(velas[-1]["c"]))
            ultimo = max(ultimo, int(velas[-1]["t"]))
        self._guardar(sim, b, ultimo)
        return b

    def cerrar(self, sim, velas):
        """Cierra a mano la posicion (o cancela una orden limite sin llenar)."""
        b = self._broker(sim)
        if b.posicion is None:
            return False, "no hay posicion para cerrar"
        ts = int(velas[-1]["t"]) if velas else int(time.time() * 1000)
        if not b.posicion.llena:
            b.posicion = None
            self._guardar(sim, b, ts)
            return True, {"cancelada": True}
        if not velas:
            return False, "no hay precio para cerrar"
        op = b.cerrar(ts, float(velas[-1]["c"]), "cerrada a mano")
        b.marca(ts, float(velas[-1]["c"]))
        self._guardar(sim, b, ts)
        return True, {"operacion": asdict(op)}

    def salvar(self):
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.estado, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.ruta)

    def resumen(self, precios=None):
        precios = precios or {}
        capital_total = pnl = 0.0
        ops = ganadoras = en_posicion = 0
        for sim, m in self.estado["mercados"].items():
            r = m.get("resumen", {})
            pos = m.get("posicion")
            curva = m.get("curva", [])
            llena = bool(pos and pos.get("llena", True))
            if llena and _finito(precios.get(sim)):
                valor = float(m.get("efectivo", self.capital)) + pos["cantidad"] * float(precios[sim])
            elif curva:
                valor = curva[-1]["capital"]
            else:
                valor = float(m.get("efectivo", self.capital))
            capital_total += valor
            pnl += valor - self.capital
            ops += int(r.get("operaciones", 0))
            ganadoras += int(r.get("ganadoras", 0))
            en_posicion += 1 if llena else 0
        inicio = self.estado.get("inicio")
        dias = round((time.time() * 1000 - inicio) / 86400000, 2) if inicio else 0.0
        base = self.capital * max(1, len(self.estado["mercados"]))
        return {"inicio": inicio, "dias_en_papel": dias, "mercados": len(self.estado["mercados"]),
                "capital_inicial": round(base, 2), "capital_total": round(capital_total, 2),
                "pnl_neto": round(pnl, 2), "retorno": round(pnl / base, 4) if base else 0.0,
                "operaciones": ops, "ganadoras": ganadoras, "en_posicion": en_posicion}

    def _curva_agregada(self):
        mercados = self.estado["mercados"]
        tiempos = sorted({p["t"] for m in mercados.values() for p in m.get("curva", [])})
        if not tiempos:
            return []
        series = {sim: {p["t"]: p["capital"] for p in m.get("curva", [])}
                  for sim, m in mercados.items()}
        ult = {sim: self.capital for sim in mercados}
        salida = []
        for t in tiempos:
            total = 0.0
            for sim in mercados:
                if t in series[sim]:
                    ult[sim] = series[sim][t]
                total += ult[sim]
            salida.append({"t": t, "capital": round(total, 2)})
        return salida[-2000:]

    def detalle(self, precios=None):
        """Lo que necesita la vista Cartera: resumen, posiciones con P/L vivo,
        historial de ordenes y curva de capital. precios: {simbolo: precio_actual}."""
        precios = precios or {}
        mercados, historial = [], []
        for sim in SIMBOLOS:
            m = self.estado["mercados"].get(sim)
            if m is None:
                continue
            pos = m.get("posicion")
            precio = precios.get(sim)
            valor_pos, pnl_vivo = 0.0, None
            if pos and pos.get("llena", True) and _finito(precio):
                valor_pos = pos["cantidad"] * float(precio)
                pnl_vivo = (float(precio) - pos["entrada_precio"]) * pos["cantidad"]
            valor = float(m.get("efectivo", self.capital)) + valor_pos
            mercados.append({"simbolo": sim, "efectivo": m.get("efectivo"),
                             "valor": round(valor, 2), "posicion": pos, "precio": precio,
                             "pnl_vivo": None if pnl_vivo is None else round(pnl_vivo, 2),
                             "resumen": m.get("resumen", {}), "ultimo_ts": m.get("ultimo_ts")})
            for o in m.get("operaciones", []):
                h = dict(o)
                h["simbolo"] = sim
                historial.append(h)
        historial.sort(key=lambda o: o.get("salida_ts", 0), reverse=True)
        return {"inicio": self.estado.get("inicio"), "capital_por_mercado": self.capital,
                "resumen": self.resumen(precios), "mercados": mercados,
                "historial": historial[:500], "curva": self._curva_agregada()}