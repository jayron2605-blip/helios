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
    if isinstance(v, bool):
        return False
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError, OverflowError):
        return False


def _timestamp(v):
    if not _finito(v) or float(v) < 0 or not float(v).is_integer():
        raise ValueError("el momento debe ser un timestamp entero, finito y no negativo")
    return int(v) if isinstance(v, int) else int(float(v))


def _rechazar_constante_json(valor):
    raise ValueError(f"numero no finito en JSON: {valor}")


def _validar_orden(params):
    if not isinstance(params, dict):
        raise ValueError("los parametros de la orden deben ser un objeto")
    if params.get("tipo", "mercado") not in ("mercado", "limite"):
        raise ValueError("el tipo de orden debe ser mercado o limite")
    cfg_kw = {}
    for k in PARAMS_CFG:
        if k in params:
            lo, hi = TOPES[k]
            if not _finito(params[k]) or not lo <= float(params[k]) <= hi:
                raise ValueError(f"{k} debe ser un numero finito entre {lo} y {hi}")
            cfg_kw[k] = float(params[k])
    if "take_profits" in params:
        pares = params["take_profits"]
        if not isinstance(pares, (list, tuple)) or not 1 <= len(pares) <= 4:
            raise ValueError("take_profits debe contener entre 1 y 4 pares [fraccion, porcentaje]")
        tp = []
        for par in pares:
            if (not isinstance(par, (list, tuple)) or len(par) != 2
                    or not all(_finito(v) for v in par)):
                raise ValueError("cada take profit debe ser un par de numeros finitos")
            fraccion, pct = map(float, par)
            lo, hi = TOPES["take_profit"]
            if not 0.01 <= fraccion <= 1.0 or not lo <= pct <= hi:
                raise ValueError(f"take profit: fraccion entre 0.01 y 1; porcentaje entre {lo} y {hi}")
            if tp and pct <= tp[-1][1]:
                raise ValueError("los porcentajes de take profit deben ser estrictamente crecientes")
            tp.append((fraccion, pct))
        if not math.isclose(sum(fraccion for fraccion, _ in tp), 1.0, rel_tol=0, abs_tol=1e-9):
            raise ValueError("las fracciones de take profit deben sumar 1")
        cfg_kw["take_profits"] = tuple(tp)
    limite = None
    if "precio_limite" in params or params.get("tipo") == "limite":
        if not _finito(params.get("precio_limite")) or float(params["precio_limite"]) <= 0:
            raise ValueError("el precio limite debe ser un numero finito mayor que cero")
        if params.get("tipo") == "limite":
            limite = float(params["precio_limite"])
    return cfg_kw, limite


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
                g = json.load(f, parse_constant=_rechazar_constante_json)
        except (ValueError, UnicodeError) as exc:
            raise ValueError("cartera manual: JSON corrupto; no se reinicia el saldo") from exc
        if (not isinstance(g, dict) or not isinstance(g.get("mercados"), dict)
                or any(not isinstance(m, dict) for m in g["mercados"].values())):
            raise ValueError("cartera manual: estructura JSON invalida; no se reinicia el saldo")
        self.estado = g
        self.estado.setdefault("inicio", int(time.time() * 1000))
        self.estado.setdefault("capital_por_mercado", self.capital)

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

    def _guardar(self, sim, b, ultimo_ts, cfg=None, ultimo_precio=None, ultimo_precio_ts=None):
        previo = self.estado["mercados"].get(sim, {})
        # Una marca por evento: a igual timestamp gana el ultimo valor observado.
        puntos = {int(p["t"]): dict(p, t=int(p["t"])) for p in b.curva}
        b.curva = [puntos[t] for t in sorted(puntos)[-2000:]]
        precio_ts = previo.get("ultimo_precio_ts", 0)
        precio = previo.get("ultimo_precio")
        if ultimo_precio is not None and (ultimo_precio_ts is None or ultimo_precio_ts >= precio_ts):
            precio = float(ultimo_precio)
            if ultimo_precio_ts is not None:
                precio_ts = int(ultimo_precio_ts)
        self.estado["mercados"][sim] = {
            "efectivo": round(b.efectivo, 8),
            "posicion": asdict(b.posicion) if b.posicion else None,
            "operaciones": [asdict(o) for o in b.operaciones],
            "cancelaciones": previo.get("cancelaciones", []),
            "curva": list(b.curva),
            "ultimo_ts": int(ultimo_ts),
            "ultimo_precio": precio,
            "ultimo_precio_ts": precio_ts,
            "resumen": b.resumen(),
            "cfg": cfg if cfg is not None else previo.get("cfg", {}),
        }

    def _alimentar(self, b, sim, velas):
        cerradas = sorted((v for v in velas if v.get("cerrada", True)), key=lambda v: int(v["t"]))
        m = self.estado["mercados"].get(sim)
        # Al incorporar un mercado no simulamos operaciones ni curva anteriores.
        ultimo = int(m.get("ultimo_ts", 0)) if m is not None else (int(cerradas[-1]["t"]) if cerradas else 0)
        ultima_marca = max((int(p["t"]) for p in b.curva), default=0)
        for v in cerradas:
            ts = int(v["t"])
            if ts <= ultimo:
                continue
            ultimo = ts  # Solo avanza con velas cerradas, nunca con ticks.
            if ts < max(b.posicion.entrada_ts if b.posicion else 0, m.get("ultimo_precio_ts", 0) if m else 0):
                # No aplicar extremos anteriores a un stop ya movido por un tick.
                continue
            b.actualizar(sim, ts, float(v["o"]), float(v["h"]), float(v["l"]), float(v["c"]))
            if ts >= ultima_marca:
                b.marca(ts, float(v["c"]))
                ultima_marca = ts
        return ultimo

    def colocar_orden(self, sim, velas, params, momento=None):
        """Abre una posicion en papel; sin momento mantiene el reloj de las velas."""
        if sim not in SIMBOLOS:
            return False, "moneda no permitida"
        if not velas or not _finito(velas[-1].get("c")) or float(velas[-1]["c"]) <= 0:
            return False, "no hay precio valido para esa moneda"
        try:
            cfg_kw, limite = _validar_orden(params)
            ts = _timestamp(momento if momento is not None else velas[-1]["t"])
        except ValueError as exc:
            return False, str(exc)
        b = self._broker(sim)
        if b.posicion is not None:
            return False, "ya hay una posicion abierta en esa moneda"
        b.cfg = Configuracion(capital=self.capital, max_velas_en_posicion=720, **cfg_kw)
        precio = float(velas[-1]["c"])
        ultimo = self._alimentar(b, sim, velas)
        if not b.abrir(sim, ts, precio, 0.0, limite=limite):
            return False, "la orden no se pudo abrir (¿monto muy chico?)"
        b.marca(ts, precio)
        cfg_store = {k: v for k, v in cfg_kw.items() if k != "take_profits"}
        if "take_profits" in cfg_kw:
            cfg_store["take_profits"] = [list(x) for x in cfg_kw["take_profits"]]
        self._guardar(sim, b, ultimo, cfg_store, precio, ts)
        return True, {"simbolo": sim, "tipo": params.get("tipo", "mercado"),
                      "posicion": asdict(b.posicion)}

    def procesar(self, sim, velas, momento=None):
        """Resuelve velas cerradas y, con reloj real explicito, un unico tick nuevo."""
        ts = _timestamp(momento) if momento is not None else None
        if velas and (not _finito(velas[-1].get("c")) or float(velas[-1]["c"]) <= 0):
            raise ValueError("no hay precio valido para esa moneda")
        b = self._broker(sim)
        ultimo = self._alimentar(b, sim, velas)
        precio = precio_ts = None
        if velas:
            precio = float(velas[-1]["c"])
            ts = ts if ts is not None else _timestamp(velas[-1]["t"])
            m = self.estado["mercados"].get(sim, {})
            if momento is not None:
                if ts > m.get("ultimo_precio_ts", 0):
                    b.actualizar(sim, ts, precio, precio, precio, precio)
                    precio_ts = ts
                else:
                    # El mismo tick (o uno atrasado) no se vuelve a resolver.
                    precio = m.get("ultimo_precio", precio)
            else:
                precio_ts = ts
            if precio is not None and ts >= max((int(p["t"]) for p in b.curva), default=0):
                b.marca(ts, precio)
        self._guardar(sim, b, ultimo, ultimo_precio=precio, ultimo_precio_ts=precio_ts)
        return b

    def cerrar(self, sim, velas, momento=None):
        """Cierra a mano la posicion (o cancela una orden limite sin llenar)."""
        try:
            ts = _timestamp(momento if momento is not None else
                            (velas[-1]["t"] if velas else int(time.time() * 1000)))
        except ValueError as exc:
            return False, str(exc)
        if velas and (not _finito(velas[-1].get("c")) or float(velas[-1]["c"]) <= 0):
            return False, "no hay precio valido para cerrar"
        b = self._broker(sim)
        if b.posicion is None:
            return False, "no hay posicion para cerrar"
        m = self.estado["mercados"].get(sim, {})
        ultimo = m.get("ultimo_ts", 0)
        precio = float(velas[-1]["c"]) if velas else m.get("ultimo_precio")
        if not b.posicion.llena:
            cancelada = dict(asdict(b.posicion), salida_ts=ts, salida_precio=None,
                             comisiones=0.0, pnl_neto=None, pnl_bruto=None,
                             motivo_salida="cancelada sin ejecutar", estado="cancelada")
            b.posicion = None
            b.marca(ts, precio if precio is not None else 0.0)
            self._guardar(sim, b, ultimo, ultimo_precio=precio,
                          ultimo_precio_ts=ts if velas else None)
            self.estado["mercados"][sim]["cancelaciones"].append(cancelada)
            return True, {"cancelada": True}
        if not velas:
            return False, "no hay precio para cerrar"
        b = self.procesar(sim, velas, momento=momento)
        op = b.cerrar(ts, precio, "cerrada a mano") if b.posicion else b.operaciones[-1]
        b.marca(ts, precio)
        ultimo = self.estado["mercados"][sim]["ultimo_ts"]
        self._guardar(sim, b, ultimo, ultimo_precio=precio, ultimo_precio_ts=ts)
        return True, {"operacion": asdict(op)}

    def salvar(self):
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.estado, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.ruta)

    def _valoracion(self, sim, m, precios):
        precio = precios.get(sim)
        actualizado = _finito(precio) and float(precio) > 0
        if not actualizado:
            precio = m.get("ultimo_precio")
        precio = float(precio) if _finito(precio) and float(precio) > 0 else None
        estado_precio = "actual" if actualizado else ("guardado" if precio is not None else "sin_cotizacion")
        efectivo = float(m.get("efectivo", self.capital))
        pos = m.get("posicion")
        valor_pos = 0.0
        if pos and pos.get("llena", True):
            if precio is not None:
                valor_pos = pos["cantidad"] * precio
            elif m.get("curva"):
                # Compatibilidad con cuentas antiguas sin ultimo_precio: no inventar cotizacion.
                valor_pos = max(0.0, float(m["curva"][-1]["capital"]) - efectivo)
        return precio, actualizado, estado_precio, valor_pos, efectivo + valor_pos

    def resumen(self, precios=None):
        precios = precios or {}
        capital_total = pnl = 0.0
        ops = ganadoras = en_posicion = 0
        for sim, m in self.estado["mercados"].items():
            r = m.get("resumen", {})
            pos = m.get("posicion")
            llena = bool(pos and pos.get("llena", True))
            valor = self._valoracion(sim, m, precios)[-1]
            capital_total += valor
            pnl += valor - self.capital
            ops += int(r.get("operaciones", 0))
            ganadoras += int(r.get("ganadoras", 0))
            en_posicion += 1 if llena else 0
        inicio = self.estado.get("inicio")
        dias = round((time.time() * 1000 - inicio) / 86400000, 2) if inicio else 0.0
        base = self.capital * len(self.estado["mercados"])
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
        # Base constante: cada mercado usado aporta su saldo inicial desde el primer
        # punto, aunque su primera orden sea posterior. No se inventan marcas previas.
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
            precio, actualizado, estado_precio, valor_pos, valor = self._valoracion(sim, m, precios)
            cfg = self._cfg(m)
            pnl_vivo = None
            if pos and pos.get("llena", True) and precio is not None:
                salida_estimada = precio * (1 - cfg.deslizamiento)
                # Broker deja en la posicion la comision de entrada del remanente.
                pnl_vivo = ((salida_estimada - pos["entrada_precio"]) * pos["cantidad"]
                            - pos.get("comisiones", 0.0)
                            - salida_estimada * pos["cantidad"] * cfg.comision)
            mercados.append({"simbolo": sim, "efectivo": m.get("efectivo"),
                             "valor": round(valor, 2), "valor_posicion": round(valor_pos, 2),
                             "posicion": pos, "precio": precio, "cfg": asdict(cfg),
                             "precio_actualizado": actualizado, "estado_precio": estado_precio,
                             "ultimo_precio_ts": m.get("ultimo_precio_ts"),
                             "pnl_vivo": None if pnl_vivo is None else round(pnl_vivo, 2),
                             "resumen": m.get("resumen", {}), "ultimo_ts": m.get("ultimo_ts")})
            for o in m.get("operaciones", []):
                historial.append(dict(o, simbolo=sim, estado="ejecutada"))
            historial.extend(dict(o, simbolo=sim) for o in m.get("cancelaciones", []))
            if pos:
                llena = pos.get("llena", True)
                historial.append(dict(pos, simbolo=sim, estado="abierta" if llena else "pendiente",
                                      salida_precio=None, pnl_neto=None, pnl_bruto=None,
                                      comisiones=pos.get("comisiones", 0) if llena else 0,
                                      motivo_salida="posición abierta" if llena else "límite pendiente"))
        historial.sort(key=lambda o: o.get("salida_ts") or o.get("entrada_ts", 0), reverse=True)
        return {"inicio": self.estado.get("inicio"), "capital_por_mercado": self.capital,
                "resumen": self.resumen(precios), "mercados": mercados,
                "historial": historial, "curva": self._curva_agregada()}
