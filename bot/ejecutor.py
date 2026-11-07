"""Motor de operaciones. Es el mismo codigo para el backtest, el papel y el real.

Reglas duras:
  - la senal se calcula al cierre de la vela t y se ejecuta contra la vela t+1,
    nunca contra la misma vela (eso es mirar el futuro).
  - si el stop y el objetivo caen en la misma vela, se asume el stop primero.
  - comision y deslizamiento se descuentan siempre, aunque la operacion gane.
"""
from dataclasses import dataclass, field, asdict
import csv, json, os, time

COMISION = 0.001      # 0,1 % por lado, spot Binance
DESLIZAMIENTO = 0.0005  # 0,05 % de castigo por ejecutar a mercado


@dataclass
class Configuracion:
    capital: float = 1000.0
    riesgo_por_operacion: float = 0.02   # fraction del capital arriesgada al stop
    stop_loss: float = 0.015             # 1,5 % debajo de la entrada
    take_profit: float = 0.030           # 3 % arriba de la entrada
    max_velas_en_posicion: int = 72      # 3 dias en velas de 1h; despues se cierra
    comision: float = COMISION
    deslizamiento: float = DESLIZAMIENTO
    umbral_entrada: float = 0.55
    umbral_salida: float = 0.45
    solo_largo: bool = True


@dataclass
class Operacion:
    simbolo: str = ""
    entrada_ts: int = 0
    entrada_precio: float = 0.0
    cantidad: float = 0.0
    stop: float = 0.0
    objetivo: float = 0.0
    salida_ts: int = 0
    salida_precio: float = 0.0
    motivo_salida: str = ""
    pnl_bruto: float = 0.0
    comisiones: float = 0.0
    pnl_neto: float = 0.0
    capital_final: float = 0.0
    prob_entrada: float = 0.0
    velas: int = 0


class Broker:
    """Simula la cuenta. Si despues se conecta el cliente real, cambia solo el envio de orden."""

    def __init__(self, cfg: Configuracion, registro="trades.csv", raiz=None, contador=None):
        self.cfg = cfg
        self.efectivo = cfg.capital
        self.posicion = None
        self.operaciones = []
        self.curva = []
        self.registro = registro
        self.raiz = raiz
        self.errores = []
        # contador del dia (un Exchange). Si se pasa, cada cierre en papel/prueba
        # registra su resultado para que el freno de perdida diaria sirva de algo.
        # El backtest historico no lo pasa: sus operaciones no son las de hoy.
        self.contador = contador

    # ---------- decision ----------
    def precio_entrada(self, precio_ref, comprar=True):
        castigo = precio_ref * self.cfg.deslizamiento
        return precio_ref + castigo if comprar else precio_ref - castigo

    def abrir(self, simbolo, ts, precio_ref, prob):
        if self.posicion is not None:
            return False
        c = self.cfg
        precio = self.precio_entrada(precio_ref, comprar=True)
        stop = precio * (1 - c.stop_loss)
        objetivo = precio * (1 + c.take_profit)
        arriesgado = self.efectivo * c.riesgo_por_operacion
        por_unidad = precio - stop
        if por_unidad <= 0:
            return False
        cantidad = arriesgado / por_unidad
        costo = cantidad * precio
        comision = costo * c.comision
        if costo + comision > self.efectivo:
            cantidad = self.efectivo / (precio * (1 + c.comision)) * 0.98
            costo = cantidad * precio
            comision = costo * c.comision
        if cantidad <= 0 or costo < 10:
            return False
        self.efectivo -= costo + comision
        self.posicion = Operacion(simbolo=simbolo, entrada_ts=ts, entrada_precio=precio,
                                  cantidad=cantidad, stop=stop, objetivo=objetivo,
                                  prob_entrada=prob,
                                  comisiones=comision)
        return True

    def cerrar(self, ts, precio_ref, motivo, comprar=False):
        p = self.posicion
        if p is None:
            return None
        precio = self.precio_entrada(precio_ref, comprar=False)
        bruto = (precio - p.entrada_precio) * p.cantidad
        venta = precio * p.cantidad
        com = venta * self.cfg.comision
        p.comisiones += com
        p.salida_ts = ts
        p.salida_precio = precio
        p.motivo_salida = motivo
        p.pnl_bruto = bruto
        p.pnl_neto = bruto - p.comisiones
        p.velas = 0
        self.efectivo += venta - com
        p.capital_final = self.efectivo
        self.operaciones.append(p)
        self.posicion = None
        if self.contador is not None:
            self.contador.registrar_cierre(p.pnl_neto)
        return p

    # ---------- avance ----------
    def actualizar(self, simbolo, ts, o, h, l, c):
        """Recibe la vela recien cerrada. Primero resuelve la posicion abierta contra ESA vela."""
        if self.posicion is not None and self.posicion.simbolo == simbolo:
            p = self.posicion
            if l <= p.stop:
                self.cerrar(ts, p.stop, "stop loss")
            elif h >= p.objetivo:
                self.cerrar(ts, p.objetivo, "take profit")
            elif ts - p.entrada_ts >= self.cfg.max_velas_en_posicion * 3600 * 1000:
                self.cerrar(ts, c, "vencio el plazo")
        return self.posicion

    def marca(self, ts, precio):
        valor = self.efectivo + (self.posicion.cantidad * precio if self.posicion else 0)
        self.curva.append({"t": ts, "capital": round(valor, 2),
                           "en_posicion": int(self.posicion is not None)})
        return valor

    # ---------- resumen ----------
    def resumen(self):
        ops = self.operaciones
        if not ops:
            return {"operaciones": 0}
        ganadas = [o for o in ops if o.pnl_neto > 0]
        perdidas = [o for o in ops if o.pnl_neto <= 0]
        capital = self.efectivo if not self.posicion else self.curva[-1]["capital"]
        curva = [x["capital"] for x in self.curva] or [self.cfg.capital]
        pico = curva[0]
        caida = 0.0
        for v in curva:
            pico = max(pico, v)
            caida = max(caida, (pico - v) / pico)
        return {
            "operaciones": len(ops),
            "ganadoras": len(ganadas),
            "perdedoras": len(perdidas),
            "tasa_acierto": round(len(ganadas) / len(ops), 4),
            "pnl_neto": round(capital - self.cfg.capital, 2),
            "retorno": round(capital / self.cfg.capital - 1, 4),
            "comisiones_pagadas": round(sum(o.comisiones for o in ops), 2),
            "ganancia_media": round(sum(o.pnl_neto for o in ganadas) / len(ganadas), 2) if ganadas else 0,
            "perdida_media": round(sum(o.pnl_neto for o in perdidas) / len(perdidas), 2) if perdidas else 0,
            "max_caida": round(caida, 4),
            "velas_en_posicion": round(sum(1 for x in self.curva if x["en_posicion"]) / max(1, len(self.curva)), 3),
        }

    def volcar_registro(self):
        if not self.operaciones:
            return None
        ruta = os.path.join(self.raiz, self.registro) if self.raiz else self.registro
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(asdict(self.operaciones[0]).keys()))
            w.writeheader()
            for o in self.operaciones:
                w.writerow(asdict(o))
        return ruta
