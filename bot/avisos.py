"""Avisos al telefono. Todo el cable esta listo; falta un solo dato: el token del bot.

Funciona asi:
  - cerebro.py llama a registrar() despues de cada decision
  - si la decision de un mercado CAMBIA, o si salta un freno, se guarda el mensaje
  - enviar() los manda por Telegram cuando existe telegram.json con token y chat_id

Sin telegram.json no intenta nada de red: deja los avisos en el disco y avisa
que falta. No hay secreto escrito en el codigo.
"""
import json, os, time, urllib.parse, urllib.request

RAIZ = os.path.dirname(os.path.abspath(__file__))
RUTA_CLAVES = os.path.join(RAIZ, "telegram.json")
RUTA_ESTADO = os.path.join(RAIZ, "avisos_estado.json")
RUTA_COLA = os.path.join(RAIZ, "avisos_pendientes.txt")
RUTA_PLANTILLA = os.path.join(RAIZ, "telegram.EJEMPLO.json")


def hay_claves():
    return os.path.exists(RUTA_CLAVES)


def ultimo_estado():
    try:
        with open(RUTA_ESTADO, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def salvar_estado(e):
    with open(RUTA_ESTADO, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=2)


def encolar(texto):
    with open(RUTA_COLA, "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), texto))


def registrar(decision):
    """Compara con la ultima decision guardada y encola lo que cambio."""
    viejo = ultimo_estado()
    nuevos = {}
    avisos = []
    for m in decision.get("mercados", []):
        clave = m["simbolo"]
        banda = "compra" if m["prob_suba"] >= decision["umbral"] else (
                "venta" if m["prob_suba"] <= 1 - decision["umbral"] else "neutral")
        nuevos[clave] = banda
        antes = viejo.get(clave)
        if antes and antes != banda:
            avisos.append("%s paso de %s a %s (prob %.2f, precio %s)"
                          % (clave, antes, banda, m["prob_suba"], m["precio"]))
        nuevos[clave + "_prob"] = round(m["prob_suba"], 3)
    if decision.get("modo") != viejo.get("_modo"):
        avisos.append("el modo del bot paso a %s" % decision.get("modo"))
        nuevos["_modo"] = decision.get("modo")
    if decision.get("freno"):
        avisos.append("FRENO ACTIVO: %s" % decision["freno"])
    if viejo and not viejo.get("_arranque"):
        nuevos["_arranque"] = 1
    if not viejo:
        nuevos["_arranque"] = 1
        avisos.append("bot prendido en modo %s (%s)"
                      % (decision.get("modo"), decision.get("ventaja", "sin prueba")))
    salvar_estado(nuevos)
    for a in avisos:
        encolar(a)
    return avisos


def enviar():
    """Manda la cola por Telegram. Devuelve (cuantos, explicacion)."""
    if not hay_claves():
        return 0, ("Falta %s con el token del bot y el chat. "
                   "Los avisos quedan en %s hasta entonces."
                   % (os.path.basename(RUTA_CLAVES), os.path.basename(RUTA_COLA)))
    with open(RUTA_CLAVES, encoding="utf-8") as f:
        cfg = json.load(f)
    token, chat = cfg.get("token"), str(cfg.get("chat_id") or "")
    if not token or not chat:
        return 0, "telegram.json esta incompleto: hace falta token y chat_id."
    if not os.path.exists(RUTA_COLA):
        return 0, "no hay avisos pendientes."
    with open(RUTA_COLA, encoding="utf-8") as f:
        lineas = [l.strip() for l in f if l.strip()]
    if not lineas:
        return 0, "no hay avisos pendientes."
    url = "https://api.telegram.org/bot%s/sendMessage" % token
    enviados, errores = 0, []
    for lote in [lineas[i:i + 10] for i in range(0, len(lineas), 10)]:
        texto = "\n".join(lote)
        cuerpo = urllib.parse.urlencode({"chat_id": chat, "text": texto,
                                         "disable_web_page_preview": "true"}).encode()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=cuerpo), timeout=20) as r:
                respuesta = json.loads(r.read())
            if respuesta.get("ok"):
                enviados += len(lote)
            else:
                errores.append(str(respuesta.get("description"))[:120])
        except Exception as error:
            errores.append(type(error).__name__ + ": " + str(error)[:120])
    if enviados:
        with open(RUTA_COLA, "w", encoding="utf-8") as f:
            f.write("")
    return enviados, ("; ".join(errores) if errores else "ok")


def crear_plantilla():
    with open(RUTA_PLANTILLA, "w", encoding="utf-8") as f:
        json.dump({"token": "PEGA_AQUI_EL_TOKEN_DEL_BOT",
                   "chat_id": 0}, f, ensure_ascii=False, indent=2)
    return RUTA_PLANTILLA


if __name__ == "__main__":
    import sys
    if "--probar" in sys.argv:
        falso = {"modo": "PAPEL", "umbral": 0.55, "horizonte": 24,
                 "ventaja": "prueba", "freno": None,
                 "mercados": [{"simbolo": "BTCUSDT", "prob_suba": 0.61, "precio": 75000},
                              {"simbolo": "ETHUSDT", "prob_suba": 0.44, "precio": 2300}]}
        print("encolado:", registrar(falso))
        print("segunda pasada (deberia avisar el cambio):")
        falso["mercados"][0]["prob_suba"] = 0.40
        print("encolado:", registrar(falso))
        print("enviar():", enviar())
        sys.exit(0)
    n, porque = enviar()
    print("avisos mandados:", n, "|", porque)
