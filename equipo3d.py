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
                 "rechazo · VAL4 enjuague · VAL5 aire. Ciclos del laboratorio: "
                 "ultrafiltración y recirculación de NaOH = 1+2 · enjuague de la línea "
                 "de rechazo = 1+3 (se sigue con el conductímetro hasta 30–33 µS/cm) · "
                 "enjuague de la línea de permeado = 1+4."),
        "fuente": "P&ID (tabla VAL) · Manual (ciclos)",
    },
    "valvulaRoja": {
        "nombre": "Válvula reguladora roja V9 (retorno del rechazo)",
        "desc": ("Válvula manual de aguja de 9 vueltas en la tubería trasera de rechazo. "
                 "Durante la ultrafiltración es la ÚNICA que regula el rechazo que "
                 "regresa al tanque (la V3 permanece cerrada). Al abrirla (más vueltas) "
                 "el rechazo fluye libre, baja la presión en la membrana y sale menos "
                 "permeado; al cerrarla (menos vueltas) aumenta la restricción y la "
                 "presión transmembrana y se fuerza más líquido por los poros. Se opera "
                 "en la vuelta 2, contada desde totalmente cerrada, para equilibrar la "
                 "presión sin saturar el sistema."),
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
        "nombre": "Caneca externa (sobre báscula)",
        "desc": ("Balde externo sobre una báscula. Recibe la descarga de la manguera "
                 "delgada de permeado durante el enjuague de esa línea (V1+V4) tras la "
                 "limpieza química; ese líquido no se envía al drenaje y se desecha "
                 "luego en el punto indicado por el laboratorio."),
        "fuente": "Aclaración del laboratorio",
    },
    "drenaje": {
        "nombre": "Drenaje",
        "desc": ("Salida de la manguera gruesa de rechazo durante el barrido de esa "
                 "línea (V1+V3) o al vaciar el tanque."),
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
           "detalle": "Modo principal de trabajo: solo V1 y V2 abiertas (V3 cerrada). La mezcla pasa por el microfiltro y el rotámetro de entrada (~6 L/min) antes de la membrana. Sale por ABAJO del tanque hacia la bomba y el equipo. El rechazo (rojo, manguera gruesa) regresa por ARRIBA al mismo tanque en lazo cerrado, regulado únicamente por la válvula roja V9 (vuelta 2). El permeado (azul, manguera delgada) va al otro tanque, sobre su báscula."},
    "quim": {"etiqueta": "🧪 Recirculación de NaOH (V1+V2)", "valvulas": [1, 2],
             "detalle": "Cuando hay ensuciamiento severo por grasas y proteínas se prepara ~1 kg de soda cáustica en 80 L de agua (NaOH ≈ 1 %) en el tanque de alimentación y se recircula en modo V1+V2 para desintegrar la capa orgánica dentro del módulo. Activa 🔬 para ver cómo disuelve la torta. Después se alternan V1+V3 y V1+V4 con agua limpia para expulsar la soda saponificada y los residuos."},
    "lavR": {"etiqueta": "🚿 Lavado con agua: línea de rechazo (V1+V3)", "valvulas": [1, 3],
             "detalle": "Lavado preventivo: el agua de la planta barre la tubería de rechazo y sale por la manguera gruesa. Se usa antes del lactosuero para purgar la línea, o después de la corrida para arrastrar partículas grandes y azúcares. Se mide con el conductímetro hasta 30–33 µS/cm."},
    "lavP": {"etiqueta": "🚿 Enjuague línea de permeado (V1+V4) → caneca", "valvulas": [1, 4],
             "detalle": "Lavado preventivo de la línea delgada de permeado: el agua sale por la manguera delgada a la caneca externa sobre la báscula, para que no queden partículas que alteren las mediciones de volumen o masa."},
    "retro": {"etiqueta": "💨 Retrolavado + aire (V5)", "valvulas": [5],
              "detalle": "Agua del tanque azul (con NaOH agregado manualmente si es limpieza química), impulsada por la bomba de lavado en contraflujo, más aire comprimido: desprende la torta (cada 15–60 min, 30–60 s)."},
}


@st.cache_resource(show_spinner=False)
def _libs_three():
    three = (_AQUI / "static3d" / "three.min.js").read_text(encoding="utf-8")
    orbit = (_AQUI / "static3d" / "OrbitControls.js").read_text(encoding="utf-8")
    return three, orbit


def _html_escena(j_ratio, j_curva, c_curva, vueltas_json="null"):
    three, orbit = _libs_three()
    plantilla = (_AQUI / "static3d" / "escena.js").read_text(encoding="utf-8")
    escena = (plantilla
              .replace("__COMPONENTES__", json.dumps(COMPONENTES, ensure_ascii=False))
              .replace("__CICLOS__", json.dumps(CICLOS, ensure_ascii=False))
              .replace("__JRATIO__", json.dumps(list(j_ratio)))
              .replace("__JCURVE__", json.dumps(list(j_curva)))
              .replace("__CCURVE__", json.dumps(list(c_curva)))
              .replace("__VUELTAS__", vueltas_json))
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
  #foul {{ position:absolute; left:10px; top:318px; background:rgba(255,255,255,.93); border-radius:10px;
      padding:7px 12px; font-size:12.5px; color:#213547; box-shadow:0 1px 6px rgba(0,0,0,.15); display:none; }}
  #panelPractica {{ display:none; position:absolute; top:10px; right:10px; width:350px; max-height:625px;
      overflow-y:auto; background:rgba(255,255,255,.97); border-radius:12px; box-shadow:0 4px 16px rgba(0,0,0,.22);
      padding:11px 14px; z-index:7; font-size:13px; color:#213547; }}
  #panelPractica h3 {{ margin:0 0 6px; font-size:15.5px; color:#082e52; }}
  #panelPractica select {{ width:100%; padding:4px; font-size:13px; margin-bottom:6px; }}
  #prPasos {{ margin:4px 0 8px; padding-left:18px; }}
  #prPasos li {{ margin-bottom:3px; color:#8795a1; }}
  #prPasos li.ok {{ color:#2f855a; }}
  #prPasos li.cur {{ color:#082e52; font-weight:600; }}
  .prfila {{ display:flex; gap:5px; align-items:center; margin:4px 0; flex-wrap:wrap; }}
  .prfila button {{ border:1px solid #cbd5e0; background:#fff; border-radius:7px; padding:5px 9px; cursor:pointer; font-size:12.5px; }}
  .prfila button.act {{ background:#ff9500; color:#fff; border-color:#e08200; }}
  #prComprobar {{ background:#082e52 !important; color:#fff; border-color:#082e52 !important; }}
  #prMsg.mal {{ background:#fff5f5; border-left:4px solid #e53e3e; padding:5px 8px; margin-top:6px; }}
  #prMsg.bien {{ background:#f0fff4; border-left:4px solid #38a169; padding:5px 8px; margin-top:6px; }}
  #prMsg ul {{ margin:3px 0 0; padding-left:16px; }}
  #prPeligro {{ display:none; background:#fffaf0; border-left:4px solid #dd6b20; padding:5px 8px; margin:6px 0; }}
  #prCond {{ display:none; background:#ebf8ff; border-radius:8px; padding:5px 9px; margin:6px 0; }}
  #prFin {{ display:none; background:#f0fff4; border-radius:8px; padding:7px 9px; margin-top:6px; }}
  #lecV9 {{ display:none; position:absolute; left:362px; top:44px; width:400px; max-width:calc(100% - 740px); min-width:260px;
      background:rgba(255,255,255,.95); border-radius:10px; padding:7px 12px; font-size:12.5px; color:#213547;
      box-shadow:0 1px 6px rgba(0,0,0,.18); border-left:5px solid #1f4e78; z-index:4; }}
  #lecV9.peligro {{ border-left-color:#e53e3e; background:#fff5f5; }}
  #lecV9 .etq {{ font-size:10.5px; border-radius:8px; padding:1px 6px; margin-left:4px; }}
  #lecV9 .dato {{ background:#c6f6d5; color:#22543d; }}
  #lecV9 .est {{ background:#feebc8; color:#7b341e; }}
  #lecV9 .rango {{ color:#718096; font-size:11px; }}
  #ctrlV9 {{ display:none; gap:6px; align-items:center; margin-top:6px; }}
  #ctrlV9 button {{ border:1px solid #cbd5e0; background:#fff; border-radius:6px; padding:2px 9px; cursor:pointer; }}
</style></head><body>
<canvas id="c"></canvas>
<div class="panelbtns" id="botones"></div>
<div id="foul">Minuto de la práctica: <b id="minv">0</b><br>
  <input type="range" id="min" min="0" max="40" value="0" step="1" style="width:170px">
  <div style="font-size:11px;color:#586c7c">El permeado se frena según el modelo de Hermia<br>y la membrana se tiñe por el ensuciamiento</div>
</div>
<div id="lecV9"><div id="lecV9txt"></div>
  <div id="ctrlV9">Gira la válvula roja V9: <button id="v9m">− cerrar</button> vuelta <b id="v9Libre">2</b>
    <button id="v9p">abrir +</button></div></div>
<div id="detalleCiclo"></div>
<div id="panelPractica">
  <h3>🎮 Modo práctica</h3>
  <select id="prProc"></select>
  <ol id="prPasos"></ol>
  <div id="prTab">
    <b>Tablero</b>
    <div class="prfila">Válvulas:
      <button data-v="1">V1</button><button data-v="2">V2</button><button data-v="3">V3</button>
      <button data-v="4">V4</button><button data-v="5">V5</button></div>
    <div class="prfila"><button id="prBomba">BOMBA: apagada</button></div>
    <div class="prfila">Válvula roja V9: <button id="prV9m">−</button> vuelta <b id="prV9">9</b>
      <button id="prV9p">+</button> <span style="font-size:11px;color:#586c7c">(0 = cerrada · 9 = abierta)</span></div>
    <div class="prfila">Rotámetro de entrada: <button id="prCm">−</button> <b id="prCau">0.0</b> L/min
      <button id="prCp">+</button></div>
    <div class="prfila">Entrada conectada a:
      <select id="prFuente" style="width:auto;margin:0"><option value="tanque">Tanque de alimentación</option>
        <option value="red">Toma de agua de red</option></select></div>
    <div class="prfila">Contenido del tanque:
      <select id="prCont" style="width:auto;margin:0"><option value="agua">Agua</option>
        <option value="lactosuero">Lactosuero preparado</option><option value="naoh">NaOH 1 %</option></select></div>
  </div>
  <div id="prCond">🔌 Conductímetro: <b id="prCondV">850</b> µS/cm · minuto simulado <b id="prCondM">0.0</b>
    <div style="font-size:11px;color:#586c7c">Objetivo: 30–33 µS/cm</div></div>
  <div id="prPeligro"></div>
  <div class="prfila"><button id="prComprobar">✔ Comprobar paso</button><button id="prReiniciar">↺ Reiniciar</button></div>
  <div id="prMsg"></div>
  <div id="prFin"></div>
</div>
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
  <h3 id="tN"></h3><p id="tD"></p></div>
<div id="leyenda"><b>Líneas (colores del P&ID)</b><br>
  Entrada<span style="background:#1fa23a"></span> Permeado<span style="background:#1565d8"></span><br>
  Rechazo<span style="background:#d8342c"></span> Lavado<span style="background:#18b8c4"></span>
  Aire<span style="background:#f08c1a"></span></div>
<script>{three}</script>
<script>{orbit}</script>
<script>{escena}</script>
</body></html>"""


@st.cache_data(show_spinner=False)
def _tabla_vueltas(J_agua, C0, pts, base):
    """Resumen por vuelta del modelo de la válvula roja (mismo Montecarlo del simulador
    'Vueltas de la válvula roja', con sus supuestos por defecto)."""
    import simulacion_presion as sp
    from simulacion_vueltas import VUELTAS, correr_vueltas
    r = correr_vueltas(J_agua, C0, 40, 20.0, 300, 2026, 1.0, 0.10, 4.0, 0.7, pts=pts, base=base)
    P = r["dP"] / sp.PSI_A_PA
    J0 = r["J"][:, :, 0]
    con_datos = {2} | {int(v) for v, *_ in pts}
    filas = []
    for k, v in enumerate(VUELTAS):
        filas.append({
            "P": float(np.nanmedian(P[:, k])),
            "Plo": float(np.nanpercentile(P[:, k], 5)),
            "Phi": float(np.nanpercentile(P[:, k], 95)),
            "J0": float(np.nanmedian(J0[:, k])),
            "Qp": float(np.nanmedian(J0[:, k])) * 4.8 / 60,
            "prob": float((r["dP"][:, k] / sp.BAR_A_PA > sp.P_MAX_FICHA_BAR).mean()),
            "datos": int(v) in con_datos,
        })
    return json.dumps(filas)


def pagina_equipo3d(PARAMS, modelo_J_torta, modelo_C, cargar_practicas=None):
    st.write("# Equipo 3D")
    st.markdown(
        "Recorre el equipo real de ultrafiltración **MARTIN MTUF-PVC-4046** (AI-UF-1-4): "
        "rota, acércate, haz **clic en cada componente** para ver qué es y qué hace, y "
        "activa un **ciclo de operación** para ver el recorrido del fluido con los "
        "colores del P&ID del fabricante."
    )
    st.info("🎮 **Nuevo: Modo práctica.** Pulsa el botón dentro de la escena, elige un "
            "procedimiento (operación, enjuagues o limpieza con NaOH) y opera el tablero paso "
            "a paso: la página te dice si lo hiciste bien y por qué. Practícalo antes de ir "
            "al laboratorio.")
    # Velocidad relativa del permeado según Hermia (conecta el 3D con el modelo del gemelo)
    t = np.arange(0, 41, 1.0)
    J = modelo_J_torta(t)
    j_ratio = (J / float(J[0])).round(4).tolist()
    j_curva = J.round(2).tolist()
    c_curva = modelo_C(t, float(PARAMS["C0_valido"])).round(2).tolist()
    try:
        from modelo_actualizado import parametros_base, practicas_validas, puntos_valvula
        practicas = practicas_validas(cargar_practicas()) if cargar_practicas else []
        base = parametros_base(practicas)
        vueltas_json = _tabla_vueltas(float(PARAMS["J_agua"]), float(PARAMS["C0_valido"]),
                                      tuple(puntos_valvula(practicas)),
                                      (base["J0"], base["Kc"], base["K"]) if base["n_practicas"] else None)
    except Exception:
        vueltas_json = "null"
    components.html(_html_escena(tuple(j_ratio), tuple(j_curva), tuple(c_curva), vueltas_json),
                    height=660, scrolling=False)
    st.caption("🔧 Con el ciclo de operación con lactosuero activo, cambia la vuelta de la válvula roja "
               "V9 (abajo a la izquierda o en el modo práctica): el manómetro de entrada, los "
               "rotámetros y el chorro de permeado responden con el modelo del simulador. La vuelta 2 "
               "es dato experimental; las demás son estimaciones (ver Simulación → Vueltas de la "
               "válvula roja).")
