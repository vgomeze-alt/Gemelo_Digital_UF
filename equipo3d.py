# equipo3d.py
# Pestaña "Equipo 3D": representación tridimensional interactiva del equipo de
# ultrafiltración MARTIN MTUF-PVC-4046 (Ref. laboratorio AI-UF-1-4).
#
# FUENTES de la información mostrada (cada tarjeta cita la suya):
#   [Manual]  Manual de operación del laboratorio (Multimedia/Documentacion).
#   [Tesis]   Documento de investigación: Tabla 7 (ficha de la membrana),
#             sección 2.3 (9 componentes) y ensayos preliminares.
#   [P&ID]    Diagrama P&ID del fabricante (RIELCO, 2024; Anexo M de la tesis):
#             VAL1 entrada, VAL2 permeado, VAL3 rechazo, VAL4 enjuague, VAL5 aire;
#             manómetros PI 1.01–1.05; colores de línea verde/azul/rojo.
#   [Fotos]   Fotografías del equipo en el laboratorio (AI-UF-1-4).
#   [Supuesto] Lo que NO está documentado: dimensiones y proporciones de las
#             piezas y el recorrido exacto de las tuberías (simplificado del P&ID).
#
# La geometría es esquemática-fiel: topología y componentes documentados,
# proporciones supuestas. Three.js (r128) va embebido para no depender de un CDN.

import json
from pathlib import Path

import numpy as np
import numpy as np
import streamlit as st
import streamlit.components.v1 as components

_AQUI = Path(__file__).parent

COMPONENTES = {
    "tanqueAlimentacion": {
        "nombre": "Tanque de alimentación",
        "desc": ("Contiene el lactosuero reconstituido: capacidad total de 120–140 L y "
                 "volumen de operación de 80 L. El rechazo retorna aquí (operación en "
                 "reciclo) y la proteína se concentra con el tiempo. Tiene conexión "
                 "por abajo y por arriba: por la salida inferior la mezcla va a la "
                 "bomba y de ahí al equipo; por arriba recibe la manguera de retorno "
                 "del rechazo. Va sobre una báscula para seguir el peso. Para la "
                 "limpieza química se desocupa, se llena con agua y se agrega el NaOH "
                 "manualmente: no hay un tanque de lavado dedicado."),
        "fuente": "Manual (componentes 1 y 9) · If_11 · aclaración del laboratorio",
    },
    "bombaAlimentacion": {
        "nombre": "Bomba de alimentación (externa al equipo)",
        "desc": ("Bomba aparte del equipo, en el piso junto al tanque azul: impulsa el "
                 "lactosuero hacia el microfiltro y la membrana. Su velocidad define la "
                 "velocidad tangencial dentro de las fibras, clave para controlar el "
                 "ensuciamiento. El caudal se regula a ~6 L/min en el rotámetro de entrada."),
        "fuente": "Manual (componente 3) · If_11 · aclaración del laboratorio",
    },
    "microfiltro": {
        "nombre": "Cartucho de microfiltración (5 µm)",
        "desc": ("Filtro físico a la entrada de la línea de la membrana. Retiene "
                 "partículas e impurezas que taparían rápidamente los poros de la "
                 "membrana (pretratamiento del lactosuero)."),
        "fuente": "Manual (componente 4) · Tesis (cartuchos de 5 micras)",
    },
    "tableroControl": {
        "nombre": "Tablero de control",
        "desc": ("Panel eléctrico (220 VAC) con piloto verde de energía y selectores "
                 "MAN–0–AUTO: fila superior VÁLVULA 1–3; fila inferior VÁLVULA 4, "
                 "VÁLVULA 5, DOSIFICADORA y BOMBA. Los pilotos naranjas indican qué "
                 "está activo."),
        "fuente": "Fotos del equipo · Tesis (componente 1)",
    },
    "tableroHidraulico": {
        "nombre": "Tablero hidráulico (manómetros y rotámetros)",
        "desc": ("Manómetros PI 1.01–1.05: PRESIÓN ENTRADA, POST-FILTRO, PERMEADO, "
                 "RECHAZO y LAVADO. Rotámetros EWP de área variable (0.5–5 GPM / "
                 "2–18 LPM, se lee el tope del flotador): FLUJO ENTRADA, FLUJO PERMEADO "
                 "y FLUJO RECHAZO; los de permeado y rechazo fueron calibrados en la "
                 "investigación. Los 6 L/min de operación quedan hacia media escala."),
        "fuente": "P&ID (PI 1.01–1.05) · Fotos · Tesis (calibración)",
    },
    "membrana": {
        "nombre": "Membrana de ultrafiltración MARTIN MTUF-PVC-4046",
        "desc": ("Módulo Hollow Fiber de PVC autolimpiante · corte 100 kDa · área "
                 "4.8 m² · pH 2–13 · 5–45 °C · presión máx. de alimento 0.4 MPa (4 bar) "
                 "· flux de diseño 25–100 L/m²·h. Configuración inside-out: la "
                 "alimentación entra por el interior de cada fibra, el permeado "
                 "atraviesa la pared porosa y el rechazo sigue de largo. Formato 4046: "
                 "≈ Ø17 cm × 1.15 m según fichas de módulos UF-4046. Usa el botón "
                 "🔬 para ver el interior."),
        "fuente": "Tesis (Tabla 7; Fig. 4) · etiqueta del equipo · ficha UF-4046 (web)",
    },
    "valvulas": {
        "nombre": "Válvulas solenoides V1–V5",
        "desc": ("Según el P&ID del fabricante: VAL1 entrada · VAL2 permeado · VAL3 "
                 "rechazo · VAL4 enjuague · VAL5 aire. Ciclos del manual del "
                 "laboratorio: ultrafiltración = 1+2 · lavado de línea de rechazo = "
                 "1+3 · lavado de línea de permeado = 1+4."),
        "fuente": "P&ID (tabla VAL) · Manual (ciclos)",
    },
    "valvulaRoja": {
        "nombre": "Válvula reguladora roja (relación permeado/rechazo)",
        "desc": ("Válvula tipo mariposa en la parte trasera, con recorrido de 9 "
                 "vueltas. Fija la relación permeado/rechazo; la práctica se opera en "
                 "la vuelta 2 (posición estándar). Fue caracterizada vuelta a vuelta "
                 "en los ensayos preliminares."),
        "fuente": "Manual (componente 10) · Tesis (caracterización)",
    },
    "bombaLavado": {
        "nombre": "Bomba de lavado (del equipo)",
        "desc": ("Bomba propia del equipo, montada en la base (cabezal inoxidable y "
                 "motor negro, rotulada BOMBA LAVADO; botón BOMBA del tablero). Impulsa "
                 "el agua de los ciclos de lavado y retrolavado; la ficha recomienda "
                 "retrolavar cada 15–60 min durante 30–60 s."),
        "fuente": "Fotos del equipo · Tesis (componente 6 y Tabla 7)",
    },
    "inyeccionAire": {
        "nombre": "Sistema de inyección de aire",
        "desc": ("Unidad de mantenimiento conectada a aire comprimido (VAL5). Envía "
                 "aire a contracorriente para ayudar a desprender la capa de "
                 "ensuciamiento durante la limpieza."),
        "fuente": "Tesis (componente 9) · If_11 · P&ID",
    },
    "tanquePermeado": {
        "nombre": "Tanque de recolección de permeado",
        "desc": ("Recibe por arriba la manguera delgada del permeado (agua, lactosa y "
                 "sales) y tiene válvula inferior para desocuparlo. Va sobre una "
                 "báscula electrónica: su peso cada 8 min, con la densidad y el área "
                 "de membrana, da el flux J."),
        "fuente": "Manual (componentes 8 y 9) · fotos",
    },
    "canecaResiduos": {
        "nombre": "Caneca de residuos de la limpieza química",
        "desc": ("Recipiente aparte donde se recoge la solución de NaOH usada: el "
                 "químico no se envía al drenaje, se recoge aquí y luego se desecha "
                 "en el punto indicado por el laboratorio."),
        "fuente": "Aclaración del laboratorio",
    },
    "drenaje": {
        "nombre": "Drenaje",
        "desc": ("Salida al desagüe usada en los lavados y purgas CON AGUA. La "
                 "solución química usada no va aquí: se recoge en la caneca de "
                 "residuos."),
        "fuente": "P&ID · Manual (purgas) · aclaración del laboratorio",
    },
    "tomaAgua": {
        "nombre": "Toma de agua de red",
        "desc": ("Para los lavados, la manguera de entrada se desconecta del tanque de "
                 "alimentación y se conecta al agua de la planta."),
        "fuente": "Manual (procedimiento de lavado)",
    },
}

CICLOS = {
    "off": {"etiqueta": "⏹ Detenido", "valvulas": [], "detalle": "Equipo apagado. Haz clic en los componentes para conocerlos."},
    "uf": {"etiqueta": "🥛 Operación con lactosuero (V1+V2)", "valvulas": [1, 2],
           "detalle": "La mezcla sale por ABAJO del tanque hacia la bomba y el equipo. Por ARRIBA del tanque regresa el rechazo (rojo, manguera gruesa, con la proteína) y el permeado (azul, manguera delgada) va al otro tanque, sobre su báscula."},
    "lavR": {"etiqueta": "🚿 Lavado con agua: línea de rechazo (V1+V3)", "valvulas": [1, 3],
             "detalle": "Agua de red por la línea de rechazo hacia el DRENAJE, 5–10 min hasta que salga clara (~30–33 µS/cm)."},
    "lavP": {"etiqueta": "🚿 Lavado con agua: línea de permeado (V1+V4)", "valvulas": [1, 4],
             "detalle": "Agua de red por la línea de permeado hacia el DRENAJE, para limpiar el interior de las fibras."},
    "quim": {"etiqueta": "🧪 Limpieza química (NaOH) → caneca", "valvulas": [1, 3],
             "detalle": "El NaOH al 1 % se prepara manualmente en el tanque azul desocupado y se bombea con la MISMA bomba del lactosuero hacia la membrana; la solución usada se recoge en la CANECA de residuos (no va al drenaje) para desecharla en el punto indicado. Activa 🔬 para ver cómo disuelve la torta."},
    "retro": {"etiqueta": "💨 Retrolavado + aire (V5)", "valvulas": [5],
              "detalle": "Agua del tanque azul (con NaOH agregado manualmente si es limpieza química), impulsada por la bomba de lavado en contraflujo, más aire comprimido: desprende la torta (cada 15–60 min, 30–60 s)."},
}


@st.cache_resource(show_spinner=False)
def _libs_three():
    three = (_AQUI / "static3d" / "three.min.js").read_text(encoding="utf-8")
    orbit = (_AQUI / "static3d" / "OrbitControls.js").read_text(encoding="utf-8")
    return three, orbit


def _html_escena(j_ratio, j_curva, c_curva):
    three, orbit = _libs_three()
    plantilla = (_AQUI / "static3d" / "escena.js").read_text(encoding="utf-8")
    escena = (plantilla
              .replace("__COMPONENTES__", json.dumps(COMPONENTES, ensure_ascii=False))
              .replace("__CICLOS__", json.dumps(CICLOS, ensure_ascii=False))
              .replace("__JRATIO__", json.dumps(list(j_ratio)))
              .replace("__JCURVE__", json.dumps(list(j_curva)))
              .replace("__CCURVE__", json.dumps(list(c_curva))))
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  html,body {{ margin:0; padding:0; overflow:hidden; font-family:"Source Sans Pro",Helvetica,Arial,sans-serif; }}
  #c {{ width:100%; height:100%; display:block; cursor:grab; }}
  .panelbtns {{ position:absolute; top:10px; left:10px; display:flex; flex-direction:column; gap:6px; z-index:5; }}
  .panelbtns button {{ border:1px solid #cbd5e0; background:#fff; color:#213547; border-radius:8px;
      padding:7px 12px; font-size:13.5px; cursor:pointer; text-align:left; box-shadow:0 1px 4px rgba(0,0,0,.12); }}
  .panelbtns button.act {{ background:#082e52; color:#fff; border-color:#082e52; }}
  #detalleCiclo {{ position:absolute; left:10px; bottom:10px; max-width:46%; background:rgba(255,255,255,.93);
      border-radius:10px; padding:9px 13px; font-size:13.5px; color:#213547; box-shadow:0 1px 6px rgba(0,0,0,.15); }}
  #tarjeta {{ position:absolute; top:10px; right:10px; width:310px; background:#fff; border-radius:12px;
      box-shadow:0 4px 16px rgba(0,0,0,.22); padding:14px 16px; display:none; z-index:6; }}
  #tarjeta h3 {{ margin:0 0 6px; font-size:16.5px; color:#082e52; }}
  #tarjeta p {{ margin:0 0 8px; font-size:13.5px; line-height:1.45; color:#213547; }}
  #tarjeta .fuente {{ font-size:11.5px; color:#586c7c; border-top:1px solid #e2e8f0; padding-top:6px; }}
  #tarjeta .cerrar {{ position:absolute; top:6px; right:10px; border:none; background:none; font-size:17px;
      cursor:pointer; color:#586c7c; }}
  #leyenda {{ position:absolute; right:10px; bottom:10px; background:rgba(255,255,255,.93); border-radius:10px;
      padding:8px 12px; font-size:12px; color:#213547; box-shadow:0 1px 6px rgba(0,0,0,.15); }}
  #leyenda span {{ display:inline-block; width:18px; height:4px; border-radius:2px; margin:0 5px 2px 10px; }}
  #hint {{ position:absolute; top:10px; left:50%; transform:translateX(-50%); background:rgba(8,46,82,.85);
      color:#fff; border-radius:16px; padding:5px 14px; font-size:12.5px; z-index:4; }}
  #foul {{ position:absolute; left:10px; bottom:74px; background:rgba(255,255,255,.93); border-radius:10px;
      padding:7px 12px; font-size:12.5px; color:#213547; box-shadow:0 1px 6px rgba(0,0,0,.15); display:none; }}
</style></head><body>
<canvas id="c"></canvas>
<div class="panelbtns" id="botones"></div>
<div id="foul">Minuto de la práctica: <b id="minv">0</b><br>
  <input type="range" id="min" min="0" max="40" value="0" step="1" style="width:170px">
  <div style="font-size:11px;color:#586c7c">El permeado se frena según el modelo de Hermia<br>y la membrana se tiñe por el ensuciamiento</div></div>
<div id="detalleCiclo"></div>
<div id="panelInterior" style="display:none;position:absolute;right:10px;top:10px;width:335px;
  background:rgba(255,255,255,.96);border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.22);
  padding:12px 14px;z-index:5;font-size:13px;color:#213547">
  <h3 id="faseT" style="margin:0 0 5px;font-size:15.5px;color:#082e52"></h3>
  <p id="faseD" style="margin:0 0 7px;line-height:1.4"></p>
  <div id="lectura" style="background:#eef4fa;border-radius:8px;padding:5px 9px;margin-bottom:7px;font-size:12.5px"></div>
  <div id="zonaGraficas"><canvas id="gf" width="307" height="195"></canvas></div>
  <div style="font-size:11.5px;color:#586c7c;margin:4px 0 2px">Torta de proteína depositada</div>
  <div style="height:8px;background:#edf2f7;border-radius:4px;overflow:hidden;margin-bottom:8px">
    <div id="barraTorta" style="height:100%;width:0%;background:linear-gradient(90deg,#e0b56b,#8a5a22)"></div></div>
  <div id="ctrlTiempo" style="display:flex;gap:8px;align-items:center">
    <button id="btnPlay" style="border:none;border-radius:8px;padding:7px 10px;background:#082e52;color:#fff;
      font-size:12.5px;cursor:pointer;white-space:nowrap">▶ Reproducir 0–40 min</button>
    <input type="range" id="minInt" min="0" max="40" value="0" step="1" style="flex:1">
  </div>
</div>
<div id="hint">Arrastra para rotar · rueda para acercar · clic en un componente</div>
<div id="tarjeta"><button class="cerrar" onclick="document.getElementById('tarjeta').style.display='none'">✕</button>
  <h3 id="tN"></h3><p id="tD"></p><div class="fuente" id="tF"></div></div>
<div id="leyenda"><b>Líneas (colores del P&ID)</b><br>
  Entrada<span style="background:#1fa23a"></span> Permeado<span style="background:#1565d8"></span><br>
  Rechazo<span style="background:#d8342c"></span> Lavado<span style="background:#18b8c4"></span>
  Aire<span style="background:#f08c1a"></span></div>
<script>{three}</script>
<script>{orbit}</script>
<script>{escena}</script>
</body></html>"""


def pagina_equipo3d(PARAMS, modelo_J_torta, modelo_C):
    st.write("# Equipo 3D")
    st.markdown(
        "Recorre el equipo real de ultrafiltración **MARTIN MTUF-PVC-4046** (AI-UF-1-4): "
        "rota, acércate, haz **clic en cada componente** para ver qué es y qué hace, y "
        "activa un **ciclo de operación** para ver el recorrido del fluido con los "
        "colores del P&ID del fabricante."
    )
    # Velocidad relativa del permeado según Hermia (conecta el 3D con el modelo del gemelo)
    t = np.arange(0, 41, 1.0)
    J = modelo_J_torta(t)
    j_ratio = (J / float(J[0])).round(4).tolist()
    j_curva = J.round(2).tolist()
    c_curva = modelo_C(t, float(PARAMS["C0_valido"])).round(2).tolist()
    components.html(_html_escena(tuple(j_ratio), tuple(j_curva), tuple(c_curva)),
                    height=660, scrolling=False)
    st.caption(
        "Modelo esquemático: los componentes, las válvulas, los ciclos y la ficha técnica "
        "están documentados (manual, tesis y P&ID de RIELCO); las dimensiones, proporciones "
        "y el recorrido exacto de las tuberías son supuestos de representación."
    )
    with st.expander("📘 Fuentes y correspondencia de válvulas"):
        st.markdown(
            "- **Manual del laboratorio:** componentes 1–10, ciclos por válvulas "
            "(UF = 1+2, lavado rechazo = 1+3, lavado permeado = 1+4), válvula roja en vuelta 2.\n"
            "- **Tesis (Tabla 7 y sección 2.3):** ficha de la membrana (PVC Hollow Fiber, "
            "100 kDa, 4.8 m², presión máx. 0.4 MPa) y los 9 subsistemas del equipo.\n"
            "- **P&ID del fabricante (RIELCO, Anexo M):** VAL1 entrada · VAL2 permeado · "
            "VAL3 rechazo · VAL4 enjuague · VAL5 aire; manómetros PI 1.01–1.05. El P&ID "
            "está dibujado para producción de agua ultrapura, por lo que el destino de las "
            "salidas difiere del uso con lactosuero (aquí el rechazo se recircula al tanque).\n"
            "- **Nota:** la guía If_11 numera las válvulas manuales del tablero del 1 al 9 "
            "(la 9 es la reguladora roja); el panel eléctrico rotula V1–V5. En esta escena "
            "se usan los ciclos del manual con la numeración V1–V5 del panel.\n"
            "- **Operación real del laboratorio** (aclaración del equipo de trabajo): no hay "
            "tanque de lavado ni tanque de químico dedicados; la limpieza se hace desocupando "
            "los tanques azules, llenándolos con agua y agregando el NaOH manualmente. La "
            "bomba del equipo (BOMBA LAVADO, en la base) es distinta de la bomba de "
            "alimentación, que es externa.\n"
            "- **Interior de la membrana:** módulo *inside-out* (ficha de módulos UF-4046 y "
            "Fig. 4 de la tesis): alimentación por el lumen de las fibras, permeado a través "
            "de la pared, concentrado de largo; el botón 🔬 lo muestra animado."
        )
