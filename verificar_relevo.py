"""Verificación del punto de relevo; NO es la auditoría completa de la demo.

Ejecutar desde la carpeta del proyecto: python3 verificar_relevo.py
Necesita las dependencias de requirements.txt, Node y Playwright con Chromium.
Consulta 500 velas públicas reales, pero aísla los demás datos/operaciones.
No ejecuta cerebro, ni escribe en el cuaderno o las cuentas del dueño.
El servidor de prueba usa loopback y un puerto efímero; se cierra al terminar.
"""
import csv
import hashlib
import importlib.metadata as metadata
import io
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import urllib.request

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "bot"))
import indicadores
import servidor
from playwright.sync_api import sync_playwright

OUT = ROOT / "verificacion-relevo"
OUT.mkdir(exist_ok=True)
resultados = []


def comprobar(nombre, condicion):
    assert condicion, nombre
    resultados.append(nombre)
    print("OK", nombre, flush=True)


def velas_de(klines):
    return [dict(t=int(k[0]) // 1000, o=float(k[1]), h=float(k[2]),
                 l=float(k[3]), c=float(k[4]), v=float(k[5])) for k in klines]


def main():
    html = (ROOT / "panel.html").read_text(encoding="utf-8")
    for js in re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S):
        r = subprocess.run(["node", "--check"], input=js, text=True, capture_output=True)
        comprobar("Sintaxis JavaScript", r.returncode == 0)
    for i, css in enumerate(re.findall(r'<style[^>]*>(.*?)</style>', html, re.S)):
        comprobar(f"Llaves CSS bloque {i}", css.count("{") == css.count("}"))
    for nombre in ("servidor.py", "bot/indicadores.py"):
        compile((ROOT / nombre).read_text(encoding="utf-8"), nombre, "exec")
    comprobar("Sintaxis Python", True)
    for linea in (ROOT / "requirements.txt").read_text().splitlines():
        if "==" in linea and not linea.startswith("#"):
            nombre, pin = linea.split("==")
            comprobar(f"Versión instalada {nombre}=={pin}", metadata.version(nombre) == pin)

    for n in (0, 1, 2, 13, 14, 26, 27, 28, 100, 500):
        datos = [dict(t=1700000000 + i * 3600, o=100 + i / 10,
                      h=102 + i / 10, l=98 + i / 10,
                      c=100 + i / 10 + math.sin(i), v=10 + i) for i in range(n)]
        calc = indicadores.calcular(datos)
        json.dumps(calc, allow_nan=False)
        comprobar(f"Indicadores con {n} velas sintéticas (no ganancias)", True)

    prueba = subprocess.run([sys.executable, "bot/pruebas.py"], cwd=ROOT,
                            capture_output=True, text=True)
    cantidad = sum(x.strip().startswith("OK ") for x in prueba.stdout.splitlines())
    (OUT / "regresiones.txt").write_text(prueba.stdout + prueba.stderr, encoding="utf-8")
    comprobar("177 regresiones / TODO OK", prueba.returncode == 0 and cantidad == 177
              and "TODO OK" in prueba.stdout)
    comprobar("Candado SOLO_PRUEBA intacto", bool(re.search(
        r'^SOLO_PRUEBA\s*=\s*True', (ROOT / "bot/exchange.py").read_text(), re.M)))

    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=500"
    with urllib.request.urlopen(url, timeout=25) as respuesta:
        klines = json.load(respuesta)
    comprobar("500 velas públicas Binance, sin sustituir por inventadas", len(klines) == 500)
    vs = velas_de(klines)
    cab = ["fecha", "hora", "mercado", "precio", "tendencia", "agitacion",
           "fuerza", "rango24h", "coincidencias", "escenarios", "veredicto"]
    fila = ["2026-11-08", "12:00:00", "BTC/USDT", "100", "texto\nmultilínea",
            "calmada", "neutral", "medio", "1/4", "20/40", "no operar"]
    buffer = io.StringIO(newline="")
    csv.writer(buffer).writerows([cab, fila])
    pedir_original, ruta_original = servidor.pedir, servidor.RUTA_CUADERNO
    estado_fuente = ["ok"]
    # Sólo sustituye el transporte dentro del servidor de prueba. Las velas
    # fueron obtenidas realmente arriba y el endpoint de indicadores es el real.
    servidor.pedir = lambda *a, **k: (klines, estado_fuente[0])

    class PruebaHTTP(servidor.Atencion):
        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/":
                contenido = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(contenido)
            elif path in ("/api/indicadores", "/api/cuaderno"):
                super().do_GET()
            else:
                # Aislamiento explícito: no tocar Cartera, noticias/secretos,
                # asistente persistido ni bot. No acredita estas vistas.
                self._json({"estado": "aislado_para_prueba", "datos": None})

        def do_POST(self):
            self._json({"estado": "escrituras_deshabilitadas_en_prueba"}, 405)

        def log_message(self, *args):
            pass

    try:
        with tempfile.TemporaryDirectory(prefix="helios-relevo-") as temporal:
            archivo = Path(temporal) / "cuaderno.csv"
            original = buffer.getvalue().encode("utf-8") + b"\x00\x00" + b'"fila incompleta'
            archivo.write_bytes(original)
            servidor.RUTA_CUADERNO = str(archivo)
            lectura = servidor.leer_cuaderno()
            comprobar("Cuaderno: NUL, multilínea y fila truncada", lectura["filas"] == [fila])
            comprobar("Cuaderno: lector no reescribe archivo", archivo.read_bytes() == original)
            srv = servidor.ThreadingHTTPServer(("127.0.0.1", 0), PruebaHTTP)
            hilo = threading.Thread(target=srv.serve_forever, daemon=True)
            hilo.start()
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            try:
                estado_fuente[0] = "stale:prueba"
                with urllib.request.urlopen(base + "/api/indicadores") as r:
                    comprobar("API conserva estado stale", json.load(r)["estado"] == "stale:prueba")
                estado_fuente[0] = "ok"
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    try:
                        for ancho, alto in ((360, 740), (390, 844), (1440, 900)):
                            ctx = browser.new_context(viewport={"width": ancho, "height": alto},
                                                      has_touch=ancho < 900, is_mobile=ancho < 900)
                            page = ctx.new_page()
                            errores = []
                            page.on("pageerror", lambda e: errores.append(str(e)))
                            page.goto(base, wait_until="load")
                            page.wait_for_function("typeof PREF !== 'undefined' && typeof grafico !== 'undefined'")
                            page.evaluate("""velas => {
                              estado.velas=velas; estado.escenarios=null;
                              irA('ajustes'); document.querySelector('#ajTema [data-tema=claro]').click();
                              document.querySelector('#ajParaque [data-pq=hide]').click();
                            }""", vs)
                            page.reload(wait_until="load")
                            comprobar(f"{ancho}px preferencias guardadas y activas", page.evaluate("""() =>
                              PREF.tema==='claro' && PREF.paraqueOculto &&
                              document.querySelector('#ajTema [data-tema=claro]').classList.contains('on') &&
                              document.querySelector('#ajParaque [data-pq=hide]').classList.contains('on')"""))
                            page.evaluate("document.getElementById('btnTema').click(); document.getElementById('btnAyuda').click()")
                            comprobar(f"{ancho}px controles cabecera sincronizados", page.evaluate("""() =>
                              document.querySelector('#ajTema [data-tema=oscuro]').classList.contains('on') &&
                              document.querySelector('#ajParaque [data-pq=show]').classList.contains('on')"""))
                            page.evaluate("""velas => {
                              estado.velas=velas; estado.escenarios=null; irA('grafico');
                              ['macd','boll','adx','vwap'].forEach(c=>{capas[c]=true});
                              return traerIndicadores();
                            }""", vs)
                            comprobar(f"{ancho}px MACD/ADX alineados por fecha", page.evaluate("""() => {
                              // data() omite los whitespace; validar el índice temporal real.
                              const t=estado.velas[400].t;
                              const indice=g=>g.timeScale().coordinateToLogical(g.timeScale().timeToCoordinate(t));
                              return macdLinea.data().length===475 && adxLinea.data().length===473 &&
                                Math.abs(indice(big)-indice(macdG))<0.01 &&
                                Math.abs(indice(big)-indice(adxG))<0.01 &&
                                Math.abs(indice(big)-400)<0.01;
                            }"""))
                            page.evaluate("document.querySelector('#ajTema [data-tema=claro]').click()")
                            comprobar(f"{ancho}px tema de subgráficos", page.evaluate("""() =>
                              macdG.options().layout.background.color==='#ffffff' &&
                              adxG.options().layout.background.color==='#ffffff'"""))
                            page.evaluate("document.getElementById('chartMacd').scrollIntoView()")
                            page.screenshot(path=str(OUT / f"indicadores-{ancho}.png"))
                            for vista in ("panel", "grafico", "bot", "cuaderno", "onchain", "lab", "noticias", "cartera", "ajustes"):
                                page.evaluate("v=>irA(v)", vista)
                                comprobar(f"{ancho}px {vista}: banner y ancho (datos restantes aislados)", page.evaluate("""() => {
                                  const r=document.querySelector('.demoBanner').getBoundingClientRect();
                                  return r.top>=0 && r.bottom<=innerHeight && r.width<=innerWidth &&
                                    document.documentElement.scrollWidth<=innerWidth;
                                }"""))
                            page.evaluate("traerLog()")
                            page.wait_for_function("document.querySelector('#log tr td')?.textContent==='2026-11-08'")
                            comprobar(f"{ancho}px cuaderno columnas alineadas", page.evaluate("""() =>
                              document.querySelectorAll('#log tr td')[2].textContent==='BTC/USDT' &&
                              document.querySelectorAll('#log tr td')[3].textContent==='100.0000'"""))
                            if ancho < 900:
                                page.locator('.rail button[data-v="mas"]').tap()
                                comprobar(f"{ancho}px toque emulado abre Más", page.locator('#masFondo').evaluate("e=>e.classList.contains('abierta')"))
                                page.locator('#masCerrar').tap()
                                comprobar(f"{ancho}px toque emulado cierra Más", not page.locator('#masFondo').evaluate("e=>e.classList.contains('abierta')"))
                            page.evaluate("irA('grafico')")
                            page.route("**/api/indicadores*", lambda r: r.fulfill(status=503, body="no disponible"))
                            page.evaluate("traerIndicadores()")
                            comprobar(f"{ancho}px error indicador termina carga", page.evaluate("""() =>
                              estadoIndicadores===null && document.getElementById('gNota').textContent.includes('no disponibles')"""))
                            comprobar(f"{ancho}px sin errores JavaScript", not errores)
                            ctx.close()
                    finally:
                        browser.close()
            finally:
                srv.shutdown()
                srv.server_close()
                hilo.join(timeout=5)
    finally:
        servidor.pedir, servidor.RUTA_CUADERNO = pedir_original, ruta_original
    informe = {"alcance": "Relevo local: NO teléfono físico ni auditoría funcional completa",
               "datos_reales": "500 velas Binance BTCUSDT 1h; otras APIs aisladas",
               "comprobaciones": resultados,
               "sha256_codigo": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
                                  for f in ("panel.html", "servidor.py", "bot/indicadores.py", "requirements.txt")}}
    (OUT / "resultado.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    print("RELEVO VERIFICADO", len(resultados), "comprobaciones; esto NO cierra la demo")


if __name__ == "__main__":
    main()
