"""Cartera en papel: posiciones simuladas con precios reales, guiadas por S11.

No mueve dinero real (exchange.SOLO_PRUEBA sigue en True). Usa el mismo Broker
del backtest y persiste el estado en posiciones.json para que sobreviva entre
vueltas del cerebro. La regla de entrada/salida es S11: estar dentro solo cuando
el dia (r24), la semana (r168) y el mes (r720) suben a la vez. Es una regla simple
de tendencia, no inteligencia artificial.

Encima de S11 el Broker aplica su stop-loss, take-profit y plazo como proteccion;
por eso el resultado en papel puede diferir del backtest de S11 puro.
"""
import json, math, os, time
from dataclasses import asdict

from ejecutor import Broker, Configuracion, Operacion

RAIZ = os.path.dirname(os.path.abspath(__file__))
RUTA_POSICIONES = os.path.join(RAIZ, "posiciones.json")
CAPITAL_POR_MERCADO = 1000.0


def _finito(v):
    try:
        return v is not None and math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def senal_s11(r24, r168, r720):
    """True si las tres escalas suben a la vez. Sin dato valido -> afuera (False)."""
    if not (_finito(r24) and _finito(r168) and _finito(r720)):
        return False
    return float(r24) > 0 and float(r168) > 0 and float(r720) > 0


class CarteraPapel:
    """Una cartera simulada por mercado, persistida en disco.

    contador: un Exchange opcional. Si se pasa, cada cierre registra su resultado
    en el freno de perdida del dia (registrar_cierre). El backtest no lo usa.
    """

    def __init__(self, ruta=RUTA_POSICIONES, capital=CAPITAL_POR_MERCADO,
                 contador=None, cfg=None):
        self.ruta = ruta
        self.capital = capital
        self.contador = contador
        # plazo largo (30 dias en velas de 1h): S11 es una regla de tendencia,
        # no conviene cortarla a los 3 dias. El stop y el objetivo siguen activos.
        self.cfg = cfg or Configuracion(capital=capital, max_velas_en_posicion=720)
        self.estado = {"inicio": int(time.time() * 1000),
                       "capital_por_mercado": capital, "mercados": {}}
        self._cargar()

    def _cargar(self):
        if not os.path.exists(self.ruta):
            return
        try:
            with open(self.ruta, encoding="utf-8") as f:
                guardado = json.load(f)
        except Exception:
            return
        if isinstance(guardado, dict) and "mercados" in guardado:
            self.estado = guardado
            self.estado.setdefault("inicio", int(time.time() * 1000))
            self.estado.setdefault("capital_por_mercado", self.capital)
            self.estado.setdefault("mercados", {})

    def _broker(self, simbolo):
        m = self.estado["mercados"].get(simbolo, {})
        b = Broker(self.cfg, contador=self.contador)
        b.efectivo = float(m.get("efectivo", self.capital))
        pos = m.get("posicion")
        b.posicion = Operacion(**pos) if pos else None
        b.operaciones = [Operacion(**o) for o in m.get("operaciones", [])]
        b.curva = list(m.get("curva", []))
        return b

    def _guardar(self, simbolo, b, ultimo_ts):
        self.estado["mercados"][simbolo] = {
            "efectivo": round(b.efectivo, 8),
            "posicion": asdict(b.posicion) if b.posicion else None,
            "operaciones": [asdict(o) for o in b.operaciones],
            "curva": b.curva[-2000:],
            "ultimo_ts": int(ultimo_ts),
            "resumen": b.resumen(),
        }

    def procesar(self, simbolo, velas, dentro, prob=0.0):
        """velas: lista ascendente de velas cerradas {t,o,h,l,c}. dentro: S11 al final.

        Alimenta las velas nuevas al Broker para resolver stop, objetivo y plazo;
        despues aplica S11 sobre la ultima vela cerrada. La primera vez arranca en
        la ultima vela (no simula historia previa al arranque). Devuelve (broker,
        accion) con accion en {comprar, vender, quieto}.
        """
        b = self._broker(simbolo)
        m = self.estado["mercados"].get(simbolo)
        if m is None:
            ultimo = int(velas[-2]["t"]) if len(velas) > 1 else 0
        else:
            ultimo = int(m.get("ultimo_ts", 0))
        pos_antes = b.posicion is not None
        ops_antes = len(b.operaciones)
        nuevas = [v for v in velas if int(v["t"]) > ultimo]
        for v in nuevas:
            b.actualizar(simbolo, int(v["t"]), float(v["o"]), float(v["h"]),
                         float(v["l"]), float(v["c"]))
            b.marca(int(v["t"]), float(v["c"]))
            ultimo = int(v["t"])
        if nuevas:
            ultima = nuevas[-1]
            ts, precio = int(ultima["t"]), float(ultima["c"])
            if dentro and b.posicion is None:
                b.abrir(simbolo, ts, precio, prob)
            elif not dentro and b.posicion is not None:
                b.cerrar(ts, precio, "S11: se perdio la confirmacion")
            # marcar de nuevo para que la curva refleje el estado tras la accion S11
            b.marca(ts, precio)
        pos_despues = b.posicion is not None
        if not pos_antes and pos_despues:
            accion = "comprar"
        elif pos_antes and not pos_despues:
            accion = "vender"
        elif len(b.operaciones) > ops_antes:
            accion = "vender"
        else:
            accion = "quieto"
        self._guardar(simbolo, b, ultimo)
        return b, accion

    def salvar(self):
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.estado, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.ruta)

    def resumen(self):
        """Agregado de la cartera: capital, P/L, operaciones, dias en papel."""
        mercados = self.estado["mercados"]
        capital_total = pnl = 0.0
        ops = ganadoras = en_posicion = 0
        for m in mercados.values():
            r = m.get("resumen", {})
            curva = m.get("curva", [])
            valor = curva[-1]["capital"] if curva else float(m.get("efectivo", self.capital))
            capital_total += valor
            pnl += valor - self.capital
            ops += int(r.get("operaciones", 0))
            ganadoras += int(r.get("ganadoras", 0))
            en_posicion += 1 if m.get("posicion") else 0
        inicio = self.estado.get("inicio")
        dias = round((time.time() * 1000 - inicio) / 86400000, 2) if inicio else 0.0
        base = self.capital * max(1, len(mercados))
        return {
            "inicio": inicio,
            "dias_en_papel": dias,
            "mercados": len(mercados),
            "capital_inicial": round(base, 2),
            "capital_total": round(capital_total, 2),
            "pnl_neto": round(pnl, 2),
            "retorno": round(pnl / base, 4) if base else 0.0,
            "operaciones": ops,
            "ganadoras": ganadoras,
            "en_posicion": en_posicion,
        }