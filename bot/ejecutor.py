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
    # C1 ordenes inteligentes. Por defecto apagadas: el papel de S11 usa stop+objetivo
    # simples. trailing_stop: fraccion bajo el maximo (0.02 = 2%); 0 = apagado.
    # take_profits: tupla de (fraccion, pct) para vender en partes; el ultimo vende lo
    # que quede. Vacio = un solo objetivo (take_profit).
    trailing_stop: float = 0.0
    take_profits: tuple = ()


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
    # C1 ordenes inteligentes. Con valor por defecto para que las posiciones viejas
    # guardadas en posiciones.json se reconstruyan sin estos campos.
    cantidad_inicial: float = 0.0     # cantidad al abrir; para repartir la comision de entrada
    stop_inicial: float = 0.0         # stop al abrir; si el actual es mayor, hubo trailing
    tp_pendientes: list = field(default_factory=list)  # [[precio, cantidad_o_None, motivo], ...]
    es_limite: bool = False           # True si es orden limite pendiente de llenar
    precio_limite: float = 0.0        # precio al que se llena la orden limite
    llena: bool = True                # False mientras la orden limite no se ha llenado


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

    def abrir(self, simbolo, ts, precio_ref, prob, limite=None):
        """Abre una posicion. limite=None: compra a mercado (como siempre).
        limite=precio: deja una orden limite pendiente; no se descuenta el efectivo
        hasta que el precio baje al limite y se llene (ver actualizar)."""
        if self.posicion is not None:
            return False
        c = self.cfg
        es_limite = limite is not None
        precio = float(limite) if es_limite else self.precio_entrada(precio_ref, comprar=True)
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
        # take profits en partes: cada (fraccion, pct) vende una porcion; el ultimo
        # vende lo que quede. Vacio = un solo objetivo (take_profit), como siempre.
        tp = []
        if c.take_profits:
            n = len(c.take_profits)
            for i, (frac, pct) in enumerate(c.take_profits):
                precio_tp = precio * (1 + pct)
                q = None if i == n - 1 else cantidad * frac
                tp.append([precio_tp, q, "take profit %d" % (i + 1)])
            objetivo = tp[-1][0]
        if es_limite:
            # orden pendiente: el efectivo se descuenta recien cuando se llene
            self.posicion = Operacion(simbolo=simbolo, entrada_ts=ts, entrada_precio=precio,
                                      cantidad=cantidad, cantidad_inicial=cantidad,
                                      stop=stop, stop_inicial=stop, objetivo=objetivo,
                                      prob_entrada=prob, comisiones=comision, tp_pendientes=tp,
                                      es_limite=True, precio_limite=precio, llena=False)
            return True
        self.efectivo -= costo + comision
        self.posicion = Operacion(simbolo=simbolo, entrada_ts=ts, entrada_precio=precio,
                                  cantidad=cantidad, cantidad_inicial=cantidad,
                                  stop=stop, stop_inicial=stop, objetivo=objetivo,
                                  prob_entrada=prob, comisiones=comision, tp_pendientes=tp)
        return True

    def _llenar_limite(self, ts, p):
        """La orden limite pendiente se llena: recien ahora se descuenta el efectivo."""
        costo = p.cantidad * p.entrada_precio
        comision = costo * self.cfg.comision
        if costo + comision > self.efectivo:
            self.posicion = None   # no alcanza el efectivo: la orden se cancela
            return
        self.efectivo -= costo + comision
        p.entrada_ts = ts
        p.comisiones = comision
        p.llena = True

    def _vender_parcial(self, ts, precio_ref, q, motivo):
        """Vende una parte de la posicion (take profit parcial). q=None vende lo que queda.
        La comision de entrada se reparte en proporcion a la cantidad vendida."""
        p = self.posicion
        if p is None:
            return None
        if q is None or q >= p.cantidad - 1e-9:
            q = p.cantidad
        cant_antes = p.cantidad
        precio = self.precio_entrada(precio_ref, comprar=False)
        bruto = (precio - p.entrada_precio) * q
        venta = precio * q
        com_salida = venta * self.cfg.comision
        com_entrada = p.comisiones * (q / cant_antes) if cant_antes > 0 else 0.0
        neto = bruto - com_salida - com_entrada
        self.efectivo += venta - com_salida
        parte = Operacion(simbolo=p.simbolo, entrada_ts=p.entrada_ts, entrada_precio=p.entrada_precio,
                          cantidad=q, stop=p.stop, objetivo=p.objetivo,
                          salida_ts=ts, salida_precio=precio, motivo_salida=motivo,
                          pnl_bruto=bruto, comisiones=com_salida + com_entrada, pnl_neto=neto,
                          capital_final=self.efectivo, prob_entrada=p.prob_entrada)
        self.operaciones.append(parte)
        p.comisiones -= com_entrada
        p.cantidad -= q
        if self.contador is not None:
            self.contador.registrar_cierre(neto)
        if p.cantidad <= 1e-9:
            self.posicion = None
        return parte

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
            # orden limite pendiente: se llena si el precio bajo al limite. Recien
            # llenada, no se resuelve en la misma vela (evita mirar el futuro).
            if not p.llena:
                if l <= p.precio_limite:
                    self._llenar_limite(ts, p)
                return self.posicion
            if l <= p.stop:
                motivo = "trailing stop" if (self.cfg.trailing_stop > 0 and p.stop > p.stop_inicial) else "stop loss"
                self.cerrar(ts, p.stop, motivo)
            elif p.tp_pendientes and h >= p.tp_pendientes[0][0]:
                precio_tp, q, motivo = p.tp_pendientes.pop(0)
                self._vender_parcial(ts, precio_tp, q, motivo)
                if self.posicion is not None and self.posicion.tp_pendientes:
                    self.posicion.objetivo = self.posicion.tp_pendientes[0][0]
            elif h >= p.objetivo:
                self.cerrar(ts, p.objetivo, "take profit")
            elif ts - p.entrada_ts >= self.cfg.max_velas_en_posicion * 3600 * 1000:
                self.cerrar(ts, c, "vencio el plazo")
            # trailing stop: sube el stop al cierre de esta vela, rige para la siguiente
            if (self.posicion is not None and self.posicion.simbolo == simbolo
                    and self.posicion.llena and self.cfg.trailing_stop > 0):
                nuevo = h * (1 - self.cfg.trailing_stop)
                if nuevo > self.posicion.stop:
                    self.posicion.stop = nuevo
        return self.posicion

    def marca(self, ts, precio):
        # una orden limite sin llenar todavia no es plata invertida: no cuenta en el capital
        pos = self.posicion if (self.posicion is not None and self.posicion.llena) else None
        valor = self.efectivo + (pos.cantidad * precio if pos else 0)
        self.curva.append({"t": ts, "capital": round(valor, 2),
                           "en_posicion": int(pos is not None)})
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
