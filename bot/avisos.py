"""Avisos al telefono. Solo lo importante.

La regla es simple: si te avisa de todo, no te avisa de nada. Este modulo manda
mensaje unicamente en cuatro casos:

  1. el estado del mercado cambia de nivel (calmo -> nervioso -> peligroso)
  2. aparece una senal fuerte (las cuatro lecturas de acuerdo) en un mercado
  3. pasa algo de seguridad (salta un freno o el bot cambia de modo)
  4. el resumen del dia, una sola vez

Ademas hay un freno de mano: nunca mas de un aviso comun cada 90 minutos.
Los de seguridad pasan siempre, porque dormirte un freno es peor que el ruido.

Sin telegram.json no intenta red: deja los mensajes en avisos_pendientes.txt.
"""
import json, os, time

RAIZ = os.path.dirname(os.path.abspath(__file__))
RUTA_CLAVES = os.path.join(RAIZ, "telegram.json")
RUTA_ESTADO = os.path.join(RAIZ, "avisos_estado.json")
RUTA_COLA = os.path.join(RAIZ, "avisos_pendientes.txt")
RUTA_PLANTILLA = os.path.join(RAIZ, "telegram.EJEMPLO.json")

MINUTOS_ENTRE_AVISOS = 90
HORAS_ENTRE_SENALES = 6
NIVELES = ["calmado", "normal", "nervioso", "peligroso"]


def hay_claves():
    return os.path.exists(RUTA_CLAVES)


def _leer(ruta, defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return defecto


def _guardar_estado(e):
    with open(RUTA_ESTADO, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=2)


def encolar(texto):
    with open(RUTA_COLA, "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M"), texto))


def _nivel(nombre):
    try:
        return NIVELES.index(nombre)
    except ValueError:
        return 1


def que_avisar(decision, asistente, estado_previo):
    """Devuelve lista de (clave, texto, es_urgente)."""
    ahora = time.time()
    avisos = []
    estado_mercado = (asistente or {}).get("estado")
    anterior = estado_previo.get("mercado_estado")

    # 1) cambio de estado del mercado
    if estado_mercado and anterior and estado_mercado != anterior:
        salto = abs(_nivel(estado_mercado) - _nivel(anterior))
        if salto >= 1:
            empeora = _nivel(estado_mercado) > _nivel(anterior)
            urgencia = estado_mercado == "peligroso"
            texto = "El mercado pasó de %s a %s. %s" % (
                anterior, estado_mercado,
                ("Ojo: " + "; ".join((asistente or {}).get("motivos", []))) if empeora
                else "Se calmó.")
            avisos.append(("estado:" + estado_mercado, texto, urgencia))

    # 2) senal fuerte por mercado (con enfriamiento por mercado)
    enfriamiento = estado_previo.get("senales", {})
    umbral = (decision or {}).get("umbral", 0.55)
    for m in (decision or {}).get("mercados", []):
        if m.get("prob_suba", 0) < umbral:
            continue
        ultimo = enfriamiento.get(m["simbolo"], 0)
        if ahora - ultimo < HORAS_ENTRE_SENALES * 3600:
            continue
        avisos.append(("senal:" + m["simbolo"],
                       "Señal en %s: el modelo ve %.0f %% de chance de subir y el precio está en %s."
                       % (m["simbolo"], m["prob_suba"] * 100, m["precio"]), False))
        enfriamiento[m["simbolo"]] = ahora
    estado_previo["senales"] = enfriamiento

    # 3) seguridad: pasa siempre
    if (decision or {}).get("freno"):
        avisos.append(("freno", "Se activó un freno: " + decision["freno"], True))
    modo = (decision or {}).get("modo")
    if modo and estado_previo.get("modo") and modo != estado_previo["modo"]:
        avisos.append(("modo:" + str(modo), "El bot cambió de modo: %s. %s"
                       % (modo, (decision or {}).get("ventaja", "")), modo == "REAL"))

    # 4) resumen del dia
    hoy = time.strftime("%Y-%m-%d")
    if estado_previo.get("digest") != hoy and time.localtime().tm_hour >= 9:
        avisos.append(("digest", resumen_del_dia(decision, asistente), False))
        estado_previo["digest"] = hoy

    if estado_mercado:
        if estado_mercado != anterior:
            estado_previo["mercado_desde"] = ahora
        estado_previo["mercado_estado"] = estado_mercado
    if modo:
        estado_previo["modo"] = modo
    return avisos


def resumen_del_dia(decision, asistente):
    if not asistente:
        return "Resumen: todavía no hay análisis del asistente."
    r = asistente.get("riesgo", {})
    return ("Resumen del día. %s está en %s. %s Si entraras con %s, tu golpe máximo serían %s. "
            "El bot sigue apagado porque en la prueba con datos viejos no le gana a quedarse quieto."
            % (asistente.get("simbolo", "BTC").replace("USDT", ""),
               asistente.get("estado", "?"),
               (asistente.get("que_pasa") or [""])[0],
               _dolares(asistente.get("capital", 1000)), _dolares(r.get("perdida_usd", 0))))


def _dolares(v):
    return "$" + format(int(round(v or 0)), ",d").replace(",", ".")


def registrar(decision, asistente=None):
    """Decide que es importante, aplica el freno de mano y encola."""
    estado = _leer(RUTA_ESTADO, {})
    candidatos = que_avisar(decision, asistente, estado)

    ultimo = estado.get("ultimo_envio", 0)
    puede_comun = (time.time() - ultimo) >= MINUTOS_ENTRE_AVISOS * 60

    encolados, frenados = [], []
    for clave, texto, urgente in candidatos:
        if clave in estado.get("ya_avisado", {}) and not urgente:
            piso = HORAS_ENTRE_SENALES * 3600 if clave.startswith("senal") else 6 * 3600
            if time.time() - estado["ya_avisado"][clave] < piso:
                continue
        if not urgente and not puede_comun:
            frenados.append(clave)
            continue
        encolar(texto)
        encolados.append(texto)
        estado.setdefault("ya_avisado", {})[clave] = time.time()
        if not urgente:
            estado["ultimo_envio"] = time.time()
            puede_comun = False

    _guardar_estado(estado)
    return {"encolados": encolados, "frenados": frenados}


def enviar():
    if not hay_claves():
        return 0, ("Falta bot/telegram.json con el token del bot y el chat. "
                   "Los avisos quedan guardados en avisos_pendientes.txt.")
    cfg = _leer(RUTA_CLAVES, {})
    token, chat = cfg.get("token"), str(cfg.get("chat_id") or "")
    if not token or not chat:
        return 0, "telegram.json está incompleto: hacen falta token y chat_id."
    if not os.path.exists(RUTA_COLA):
        return 0, "no hay avisos pendientes."
    with open(RUTA_COLA, encoding="utf-8") as f:
        lineas = [l.strip() for l in f if l.strip()]
    if not lineas:
        return 0, "no hay avisos pendientes."

    import urllib.parse, urllib.request
    url = "https://api.telegram.org/bot%s/sendMessage" % token
    enviados, errores = 0, []
    for lote in [lineas[i:i + 8] for i in range(0, len(lineas), 8)]:
        cuerpo = urllib.parse.urlencode({"chat_id": chat, "text": "\n\n".join(lote),
                                         "disable_web_page_preview": "true"}).encode()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=cuerpo), timeout=20) as r:
                if json.loads(r.read()).get("ok"):
                    enviados += len(lote)
        except Exception as error:
            errores.append(type(error).__name__ + ": " + str(error)[:100])
    if enviados:
        with open(RUTA_COLA, "w", encoding="utf-8") as f:
            f.write("")
    return enviados, ("; ".join(errores) if errores else "ok")


def crear_plantilla():
    with open(RUTA_PLANTILLA, "w", encoding="utf-8") as f:
        json.dump({"token": "PEGA_AQUI_EL_TOKEN_DEL_BOT", "chat_id": 0},
                  f, ensure_ascii=False, indent=2)
    return RUTA_PLANTILLA


if __name__ == "__main__":
    import sys
    if "--probar" in sys.argv:
        a1 = {"estado": "calmado", "simbolo": "BTCUSDT", "capital": 1000,
              "que_pasa": ["BTC vale 77.000 dólares."], "riesgo": {"perdida_usd": 20}, "motivos": []}
        d1 = {"modo": "APAGADO", "umbral": 0.55, "ventaja": "no le gana",
              "mercados": [{"simbolo": "BTCUSDT", "prob_suba": 0.61, "precio": 77000},
                           {"simbolo": "ETHUSDT", "prob_suba": 0.42, "precio": 2300}]}
        print("1)", registrar(d1, a1))
        print("2) mismo dia, nada nuevo:", registrar(d1, a1))
        a2 = dict(a1, estado="peligroso", motivos=["la agitación está altísima"])
        print("3) el mercado empeora:", registrar(d1, a2))
        d2 = dict(d1, freno="se tocó el tope de pérdida diaria")
        print("4) salta un freno:", registrar(d2, a2))
        print("\ncola resultante:")
        print(open(RUTA_COLA, encoding="utf-8").read())
        print("envio:", enviar())
        sys.exit(0)
    n, porque = enviar()
    print("avisos mandados:", n, "|", porque)
