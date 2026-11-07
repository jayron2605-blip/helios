"""Registro de decisiones del bot, con el resultado escrito despues.

Cada vez que el cerebro mira el mercado se anade una linea. Y cuando esa decision
ya tiene 24 horas encima, el programa vuelve, mira que paso de verdad y lo escribe.
Eso es lo unico que separa un panel que opina de uno que se puede auditar.

Columnas: fecha, hora, mercado, precio, probabilidad, accion, motivo,
          estado_del_mercado, precio_24h_despues, resultado
"""
import csv, json, os, time

RAIZ = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(RAIZ, "decisiones.csv")
CABECERA = ["fecha", "hora", "mercado", "precio", "probabilidad", "accion", "motivo",
            "estado_del_mercado", "precio_24h_despues", "resultado"]
HORAS_CIERRE = 24


def _leer():
    if not os.path.exists(RUTA):
        return []
    with open(RUTA, newline="", encoding="utf-8") as f:
        filas = list(csv.reader(f))
    return filas[1:] if filas else []


def _momento(fila):
    try:
        return time.mktime(time.strptime(fila[0] + " " + fila[1], "%Y-%m-%d %H:%M:%S"))
    except Exception:
        return 0


def _escribir(filas):
    nuevo = not os.path.exists(RUTA)
    with open(RUTA, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CABECERA)
        w.writerows(filas)
    return nuevo


def cerrar_circulo(precios_ahora):
    """Vuelve sobre las decisiones de hace ~24 h y escribe que paso de verdad."""
    filas = _leer()
    cerradas = 0
    for fila in filas:
        if len(fila) < 10 or fila[9].strip():
            continue
        if fila[2] not in precios_ahora:
            continue
        edad_h = (time.time() - _momento(fila)) / 3600
        if edad_h < HORAS_CIERRE:
            continue
        try:
            antes = float(fila[3])
            despues = float(precios_ahora[fila[2]])
        except (ValueError, TypeError):
            fila[9] = "sin dato"
            continue
        mov = (despues / antes - 1) * 100
        fila[8] = "%.6g" % despues
        accion = fila[5]
        if accion.startswith("no opera") or accion == "quieto":
            veredicto = "no se hizo nada"
        elif mov > 0.5:
            veredicto = "acerto (subio %.1f %%)" % mov
        elif mov < -0.5:
            veredicto = "se equivoco (bajio %.1f %%)" % abs(mov)
        else:
            veredicto = "quedo plano (%.1f %%)" % mov
        fila[9] = veredicto
        cerradas += 1
    if cerradas:
        _escribir(filas)
    return cerradas


def registrar(decision, estado_asistente=None):
    """Escribe las decisiones de esta vuelta. Devuelve cuantas anadio."""
    ahora = time.localtime()
    fecha = time.strftime("%Y-%m-%d", ahora)
    hora = time.strftime("%H:%M:%S", ahora)
    estado_mercado = (estado_asistente or {}).get("estado", "")
    motivo = (decision or {}).get("ventaja", "")
    filas = _leer()
    viejas = {(f[0], f[2]) for f in filas if len(f) >= 3}
    agregadas = 0
    precios = {}
    for m in (decision or {}).get("mercados", []):
        clave = (fecha, m["simbolo"])
        if clave in viejas:
            precios[m["simbolo"]] = m["precio"]
            continue
        filas.append([fecha, hora, m["simbolo"], "%.6g" % m["precio"],
                      "%.3f" % m["prob_suba"], m.get("accion", ""), motivo,
                      estado_mercado, "", ""])
        precios[m["simbolo"]] = m["precio"]
        agregadas += 1
    if agregadas:
        _escribir(filas)
    cerradas = cerrar_circulo(precios)
    return agregadas, cerradas


def leer_limite(limite=200):
    filas = _leer()
    return {"cabecera": CABECERA, "filas": filas[-limite:][::-1], "total": len(filas)}


def resumen():
    """Cuantas decisiones se anotaron y de las cerradas, cuantas acertaron."""
    filas = _leer()
    cerradas = [f for f in filas if len(f) >= 10 and f[9].strip()]
    aciertas = sum(1 for f in cerradas if "acerto" in f[9])
    erroneas = sum(1 for f in cerradas if "equivoco" in f[9])
    planos = sum(1 for f in cerradas if "plano" in f[9])
    quietas = sum(1 for f in cerradas if "no se hizo nada" in f[9])
    return {"anotadas": len(filas), "con_resultado": len(cerradas),
            "acertaron": aciertas, "se_equivocaron": erroneas,
            "quedaron_planas": planos, "no_hizo_nada": quietas,
            "precision": round(aciertas / max(1, aciertas + erroneas + planos) * 100, 1)}


if __name__ == "__main__":
    print(json.dumps(resumen(), ensure_ascii=False, indent=2))
