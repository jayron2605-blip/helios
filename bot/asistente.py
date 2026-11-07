"""El asistente: traduce numeros a palabras y calcula el golpe si entras ahora.

No predice. Hace tres cosas que si se pueden hacer con datos reales:
  1. decir si el mercado esta calmo o peligroso, y por que
  2. decir cuanto podrias perder si entraras ahora, en pesos y en porcentaje
  3. decir si la idea del bot le gana a quedarse quieto (leyendo su propia prueba)

Todo sale de las velas que ya estan en el disco y de dos fuentes publicas.
"""
import csv, json, os, statistics, time, urllib.request

RAIZ = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(RAIZ, "datos")
SALIDA = os.path.join(RAIZ, "asistente_estado.json")

SIMBOLOS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]
CAPITAL_POR_DEFECTO = 1000.0
RIESGO_POR_DEFECTO = 2.0


def velas(simbolo):
    ruta = os.path.join(DATOS, f"{simbolo}_1h.csv")
    if not os.path.exists(ruta):
        return []
    with open(ruta, newline="", encoding="utf-8") as f:
        filas = list(csv.reader(f))[1:]
    out = []
    for f in filas:
        if len(f) < 6:
            continue
        try:
            out.append({"t": int(float(f[0])), "o": float(f[1]), "h": float(f[2]),
                        "l": float(f[3]), "c": float(f[4]), "v": float(f[5])})
        except ValueError:
            continue
    return out


def atr(v, n=14):
    if len(v) < n + 1:
        return None
    trs = []
    for i in range(1, len(v)):
        a, b = v[i], v[i - 1]
        trs.append(max(a["h"] - a["l"], abs(a["h"] - b["c"]), abs(a["l"] - b["c"])))
    return sum(trs[-n:]) / n


def percentil(valor, muestra):
    if not muestra:
        return 50.0
    menores = sum(1 for x in muestra if x < valor)
    return menores / len(muestra) * 100


def cuantas_veces_se_toca(v, distancia_stop, velas_max=24, ventana=2160):
    """De las ultimas ~90 dias: si entrabas en cada vela con ese corte, cuantas veces te saco."""
    tramo = v[-ventana:] if len(v) > ventana else v
    tocadas = 0
    total = 0
    for i in range(len(tramo) - velas_max - 1):
        entrada = tramo[i]["c"]
        piso = entrada * (1 - distancia_stop)
        total += 1
        for j in range(i + 1, min(i + 1 + velas_max, len(tramo))):
            if tramo[j]["l"] <= piso:
                tocadas += 1
                break
    if not total:
        return None, 0
    return tocadas / total * 100, total


def pct_moveor(muestra, cuantil):
    if not muestra:
        return None
    orden = sorted(muestra)
    i = max(0, min(len(orden) - 1, int(round(cuantil * (len(orden) - 1)))))
    return orden[i]


def traer_json(url, segundos=120):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HeliosAsistente/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception:
        return None


def fotos_del_mercado():
    """Amplitud y miedo/codicia: las dos cosas que no estan en las velas locales."""
    datos = traer_json("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd"
                       "&order=market_cap_desc&per_page=250&page=1&sparkline=false"
                       "&price_change_percentage=24h")
    miedo = traer_json("https://api.alternative.me/fng/?limit=1")
    salida = {"amplitud": None, "bajando": None, "subiendo": None, "mediana": None,
              "miedo": None, "miedo_texto": None}
    if isinstance(datos, list):
        cambios = [c["price_change_percentage_24h_in_currency"]
                   for c in datos if c.get("price_change_percentage_24h_in_currency") is not None]
        if cambios:
            salida["mediana"] = round(statistics.median(cambios), 2)
            salida["subiendo"] = sum(1 for c in cambios if c > 0)
            salida["bajando"] = sum(1 for c in cambios if c < 0)
            salida["amplitud"] = len(cambios)
    if isinstance(miedo, dict) and miedo.get("data"):
        d = miedo["data"][0]
        salida["miedo"] = int(d["value"])
        salida["miedo_texto"] = d["value_classification"]
    return salida


def analizar(simbolo="BTCUSDT", capital=CAPITAL_POR_DEFECTO, riesgo=RIESGO_POR_DEFECTO):
    v = velas(simbolo)
    if len(v) < 500:
        return {"error": "no hay velas suficientes para %s" % simbolo}

    precio = v[-1]["c"]
    a = atr(v) or precio * 0.005
    agitacion = a / precio  # movimiento tipico de una hora

    # donde esta la agitacion de hoy contra los ultimos 90 dias
    hist = []
    paso = max(1, len(v) // 400)
    for i in range(14, len(v), paso):
        tramo = v[max(0, i - 15):i]
        if len(tramo) < 15:
            continue
        aa = atr(tramo)
        if aa:
            hist.append(aa / tramo[-1]["c"])
    nivel_agitacion = percentil(agitacion, hist)

    cambio24 = (precio / v[-25]["c"] - 1) * 100 if len(v) > 25 else None
    cambio7d = (precio / v[-169]["c"] - 1) * 100 if len(v) > 169 else None
    rango24 = (max(x["h"] for x in v[-24:]) - min(x["l"] for x in v[-24:])) / precio * 100
    caidas = []
    for i in range(24, min(len(v), 24 * 90)):
        caidas.append((v[-i]["c"] / v[-i - 24]["c"] - 1) * 100)
    peor24 = min(caidas) if caidas else None

    # deriva tipica en 24 horas: cuanto suele hundirse el precio desde que entras
    derivas = []
    for i in range(max(0, len(v) - 24 * 90), len(v) - 25):
        entrada = v[i]["c"]
        minimo = min(v[j]["l"] for j in range(i + 1, i + 25))
        derivas.append((entrada - minimo) / entrada)
    deriva = statistics.median(derivas) if derivas else agitacion * 4

    # el corte se pone un poco mas alla de lo que suele hundirse en un dia normal
    stop = deriva * 1.5
    tocado, muestras = cuantas_veces_se_toca(v, stop)
    riesgo_usd = capital * riesgo / 100
    tamano = riesgo_usd / stop if stop > 0 else 0

    foto = fotos_del_mercado()

    # ---- clasificacion en palabras ----
    puntos = 0
    motivos = []
    if nivel_agitacion >= 75:
        puntos += 2
        motivos.append("la agitacion esta por encima del %d %% de los ultimos 90 dias" % int(nivel_agitacion))
    elif nivel_agitacion >= 50:
        puntos += 1
        motivos.append("la agitacion esta en la mitad alta de los ultimos 90 dias")
    if foto.get("bajando") and foto.get("amplitud"):
        prop = foto["bajando"] / foto["amplitud"] * 100
        if prop >= 70:
            puntos += 2
            motivos.append("%d de cada 10 monedas estan cayendo" % int(round(prop / 10)))
        elif prop >= 55:
            puntos += 1
            motivos.append("mas de la mitad de las monedas estan cayendo")
    if tocado is not None and tocado >= 65:
        puntos += 1
        motivos.append("un corte prudente se toco %d de cada 100 veces en los ultimos 90 dias" % int(round(tocado)))
    if cambio24 is not None and abs(cambio24) >= 6:
        puntos += 1
        motivos.append("el precio se movio %.1f %% en un dia" % cambio24)

    if puntos >= 5:
        estado, color = "peligroso", "rojo"
    elif puntos >= 3:
        estado, color = "nervioso", "amarillo"
    elif puntos <= 1:
        estado, color = "calmado", "verde"
    else:
        estado, color = "normal", "gris"

    # ---- veredicto del bot, en plata ----
    veredicto = {"apagado": True, "motivo": "todavia no hay prueba corriendo",
                 "bot_desde_1000": None, "quieto_desde_1000": None, "mercados": None,
                 "texto": ""}
    ruta_score = os.path.join(RAIZ, "resultados", "scorecard_h24.json")
    if os.path.exists(ruta_score):
        with open(ruta_score, encoding="utf-8") as f:
            s = json.load(f)
        det = s.get("detalle") or {}
        if det:
            gana = sum(1 for r in det.values()
                       if r.get("operaciones", 0) > 0
                       and r.get("retorno", 0) > r.get("comprar_y_sostener", 0))
            invertido = 1000 * len(det)
            bot_total = sum(1000 * (1 + r.get("retorno", 0)) for r in det.values())
            quieto_total = sum(1000 * (1 + r.get("comprar_y_sostener", 0)) for r in det.values())
            apagado = gana == 0
            veredicto.update({
                "apagado": apagado,
                "motivo": "le gano a comprar-y-sostener en %d de %d mercados" % (gana, len(det)),
                "invertido": invertido,
                "bot_total": round(bot_total),
                "quieto_total": round(quieto_total),
                "mercados": len(det),
                "gana_en": gana,
                "operaciones": s.get("operaciones_totales"),
            })
            if apagado:
                veredicto["texto"] = (
                    "Probé la idea con velas viejas de casi tres años en %d mercados, entrenando sólo "
                    "con datos anteriores a cada mes que evaluaba, y descontando la comisión que cobra "
                    "el exchange. Puse 1.000 dólares en cada uno (%s en total): el bot terminó con %s "
                    "y dejando la plata quieta habrías tenido %s. No le gana a quedarse quieto en "
                    "ninguno de los %d. Por eso está apagado."
                    % (len(det), _dolares(invertido), _dolares(bot_total),
                       _dolares(quieto_total), len(det)))
            else:
                veredicto["texto"] = (
                    "La idea le gana a quedarse quieto en %d de %d mercados. Igual sigue en modo "
                    "prueba: ganar con datos viejos no asegura nada con datos nuevos." % (gana, len(det)))

    # ---- frases ----
    que_pasa = []
    if cambio24 is not None:
        que_pasa.append("%s vale hoy %s dólares, %s %s %% en el último día y %s %s %% en la semana."
                        % (simbolo.replace("USDT", ""), _num(precio, 2),
                           "subió" if cambio24 >= 0 else "bajó", _num(abs(cambio24), 1),
                           "subió" if (cambio7d or 0) >= 0 else "bajó", _num(abs(cambio7d or 0), 1)))
    if foto.get("mediana") is not None:
        planos = foto["amplitud"] - foto["subiendo"] - foto["bajando"]
        que_pasa.append("De %d monedas, %d están subiendo, %d bajando y %d sin moverse."
                        % (foto["amplitud"], foto["subiendo"], foto["bajando"], planos))
    que_pasa.append("En las últimas 24 horas el precio se movió dentro de una franja del %s %%."
                    % _num(rango24, 1))
    if peor24 is not None:
        que_pasa.append("El peor día de los últimos tres meses fue de %s %%." % _num(peor24, 1))

    riesgo_texto = (
        "Si compraras ahora con %s y te saliera mal, el corte natural está %s %% abajo del precio. "
        "Ahí perderías %s, o sea %s %% de lo que pusiste. En los últimos 90 días, un corte así se "
        "tocó %d de cada 100 veces antes de que pasara un día."
        % (_dolares(capital), _num(stop * 100, 1), _dolares(riesgo_usd), _num(riesgo, 1),
           int(round(tocado or 0))))

    return {
        "momento": int(time.time() * 1000),
        "simbolo": simbolo,
        "capital": capital,
        "precio": round(precio, 6),
        "estado": estado,
        "color": color,
        "motivos": motivos,
        "que_pasa": que_pasa,
        "riesgo": {
            "texto": riesgo_texto,
            "stop_pct": round(stop * 100, 2),
            "perdida_usd": round(riesgo_usd, 2),
            "perdida_pct": riesgo,
            "tamano_usd": round(tamano, 2),
            "veces_tocado": None if tocado is None else round(tocado, 1),
            "muestras": muestras,
            "peor_dia_pct": None if peor24 is None else round(peor24, 2),
        },
        "agitacion": {
            "tipica_1h_pct": round(agitacion * 100, 3),
            "percentil_90d": round(nivel_agitacion, 0),
            "rango_24h_pct": round(rango24, 2),
            "cambio_24h_pct": None if cambio24 is None else round(cambio24, 2),
            "cambio_7d_pct": None if cambio7d is None else round(cambio7d, 2),
        },
        "mercado": foto,
        "bot": veredicto,
        "modo": "PRUEBA",
        "nunca_dinero_real": True,
    }


def _dolares(v):
    return "$" + format(int(round(v)), ",d").replace(",", ".")


def _num(v, dec=2):
    s = format(float(v), ",.%df" % dec)
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


if __name__ == "__main__":
    import sys
    sim = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    cap = float(sys.argv[2]) if len(sys.argv) > 2 else CAPITAL_POR_DEFECTO
    r = analizar(sim, cap)
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
    print("ESTADO:", r["estado"].upper())
    print("motivos:", "; ".join(r["motivos"]) or "ninguno")
    print()
    for f in r["que_pasa"]:
        print(" -", f)
    print()
    print("RIESGO:", r["riesgo"]["texto"])
    print()
    print("BOT:", r["bot"]["texto"])
    print("guardado en", SALIDA)
