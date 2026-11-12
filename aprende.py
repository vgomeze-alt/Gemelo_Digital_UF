# aprende.py
# Pestaña "Aprende y Evalúate" del Gemelo Digital UF:
#   1. Flashcards interactivas (se voltean con un clic)
#   2. Reto "¿Qué pasaría si...?" usando el modelo del simulador
#   3. Evaluación final calificada (0.0 - 5.0) con certificado en PDF y
#      registro en Google Sheets para que el profesor la verifique.

import hashlib
import io
import json
import random
import time
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# =============================================================================
# 1. FLASHCARDS
# =============================================================================

FLASHCARDS = [
    # (categoría, pregunta del frente, explicación del reverso)
    ("Conceptos",
     "¿Qué es la ultrafiltración y para qué se usa en esta práctica?",
     "Es una separación por membranas: el líquido se empuja con presión contra una "
     "membrana con poros muy finos. Las moléculas pequeñas la atraviesan y las grandes "
     "quedan retenidas.\n\nAquí se usa para concentrar las proteínas del lactosuero, que "
     "son grandes, separándolas del agua, la lactosa y las sales, que son pequeñas. El "
     "equipo fue diseñado para tratar agua y se adaptó para esta aplicación."),
    ("Conceptos",
     "¿Qué es el permeado y qué contiene?",
     "Es la corriente que SÍ atraviesa los poros de la membrana. Contiene agua, lactosa y "
     "sales minerales, porque son moléculas lo bastante pequeñas para pasar.\n\nSe retira "
     "continuamente hacia un tanque de recolección. Su caudal por unidad de área es el "
     "flux, la variable principal que sigue el gemelo digital."),
    ("Conceptos",
     "¿Qué es el rechazo (retenido) y por qué se recircula al tanque?",
     "Es la corriente que NO atraviesa la membrana: lleva las proteínas, que son "
     "demasiado grandes para los poros.\n\nSe devuelve al tanque de alimentación "
     "(operación en reciclo) para que la proteína no se quede pegada en la membrana. Como "
     "el agua sí sale por el permeado, en el tanque queda cada vez menos volumen con la "
     "misma proteína: por eso la concentración sube con el tiempo."),
    ("Conceptos",
     "¿Cuál es la diferencia entre flujo volumétrico y flux de permeado?",
     "El flujo volumétrico es cuánto volumen pasa por unidad de tiempo (por ejemplo, L/min). "
     "El flux es ese mismo flujo dividido entre el área de la membrana, en L/(m²·h).\n\n"
     "Se usa el flux porque permite comparar membranas de distinto tamaño: dice qué tan "
     "rápido filtra cada metro cuadrado. En este equipo el área es de 4.8 m²."),
    ("Conceptos",
     "¿Qué es el fouling (ensuciamiento) y cómo se nota en el equipo?",
     "Es una capa de proteínas y grasas que se va acumulando sobre la superficie de la "
     "membrana mientras se filtra el lactosuero.\n\nEsa capa es una resistencia extra al "
     "paso del líquido, así que:\n• el flux de permeado baja con el tiempo, y\n• las "
     "presiones en los manómetros suben.\nPor eso hay que limpiar la membrana al final."),
    ("Modelos",
     "¿Cómo predice el gemelo digital la concentración de proteína en el tanque?",
     "Con un balance de materia en el tanque:\n1/C(t) − 1/C₀ = −K·t\n\nC₀ es la "
     "concentración inicial, C(t) la concentración al tiempo t y K una constante que agrupa "
     "presión, viscosidad, resistencias y área. Supone que casi nada de proteína atraviesa "
     "la membrana.\n\nLo que baja de forma lineal es 1/C, así que C sube cada vez más "
     "rápido. K ≈ 0.00127 (g/L)⁻¹·min⁻¹ se ajustó con los datos R:28/72 (R² = 0.972)."),
    ("Modelos",
     "¿Qué dice el modelo de Hermia n = 0 (formación de torta) sobre el flux?",
     "Supone que la proteína forma una capa (torta) cada vez más gruesa sobre la membrana, "
     "y que esa capa es la que frena el paso del líquido:\nJ(t) = [1/J₀² + 2·Kc·t]^(−0.5)"
     "\n\nJ₀ es el flux inicial (≈ 19 L/m²·h) y Kc mide qué tan rápido crece la torta. Es el "
     "modelo recomendado entre 0 y 40 min porque es físicamente coherente y ajustó "
     "muy bien los datos (R² = 0.994)."),
    ("Modelos",
     "¿Qué dice el modelo exponencial y cuándo conviene usarlo?",
     "J(t) = J∞ + (J₀ − J∞)·e^(−k·t)\n\nEl flux arranca en J₀ y baja hasta estabilizarse en "
     "un valor mínimo J∞ ≈ 8.1 L/(m²·h); k indica qué tan rápido llega allí.\n\nConviene para "
     "proyectar tiempos largos: como tiene un piso físico (J∞), no predice flux absurdamente "
     "bajos. El modelo de torta, en cambio, sigue bajando sin límite."),
    ("Modelos",
     "¿Qué tan confiable es una simulación de más de 40 minutos?",
     "Los modelos se ajustaron con datos medidos entre 0 y 40 min. Más allá de eso el "
     "simulador calcula igual, pero es una extrapolación: una proyección orientativa, "
     "no un dato comprobado en laboratorio.\n\nSi vas a proyectar tiempos largos, usa el "
     "modelo exponencial, que se comporta de forma más realista."),
    ("Equipo",
     "¿Cuáles son los parámetros físicos principales del equipo y la práctica?",
     "• Volumen de operación: unos 80 L de lactosuero reconstituido en el tanque de "
     "alimentación.\n• Área de la membrana: 4.8 m², la que se usa para pasar de flujo a "
     "flux.\n• Densidad del lactosuero: 1.026 g/cm³, para convertir los pesos medidos en "
     "volumen."),
    ("Equipo",
     "¿Qué miden el FCV y el coeficiente de rechazo R?",
     "FCV (factor de concentración volumétrica): compara el volumen inicial con el "
     "volumen concentrado final. Dice cuánto se concentró el lote; en esta membrana suele "
     "estar alrededor de 1.5.\n\nCoeficiente de rechazo R: mide qué fracción de la proteína "
     "retiene la membrana, es decir, su selectividad. En operación óptima está entre 93 % y "
     "95 %."),
    ("Equipo",
     "¿Qué significa que el coeficiente de rechazo caiga de forma drástica?",
     "Que la membrana está dejando pasar proteína que antes retenía: perdió "
     "selectividad.\n\nLa causa más probable es una ruptura física de los poros, que puede "
     "ocurrir por presiones extremas o cambios bruscos de pH. Por eso las membranas son "
     "frágiles y hay que operarlas dentro de sus límites."),
    ("Procedimiento",
     "¿Cómo se prepara el lactosuero antes de la práctica?",
     "1. Llenar el tanque de alimentación con unos 80 L de agua.\n2. Pesar unos 5.21 kg "
     "de lactosuero en polvo y agregarlo.\n3. Encender la bomba de mezclado y apoyarse con "
     "una vara.\n4. Dejar hidratar la mezcla entre 5 y 10 min para que el polvo se disuelva "
     "bien antes de filtrar."),
    ("Procedimiento",
     "¿Cómo se arranca la ultrafiltración en el equipo?",
     "1. Verificar que todas las válvulas estén cerradas.\n2. Conectar el rechazo de vuelta "
     "al tanque de alimentación y el permeado al tanque de recolección.\n3. Abrir las "
     "válvulas 1 y 2 del panel.\n4. Ajustar la alimentación a unos 6 L/min en el rotámetro."
     "\n5. Abrir la válvula de permeado unas 2 vueltas."),
    ("Procedimiento",
     "¿Qué datos se toman durante la práctica y cada cuánto?",
     "Cada 8 minutos se registra:\n• el peso de permeado y de rechazo, para calcular "
     "caudales y flux;\n• la presión de entrada y la de membrana, que suben con el "
     "ensuciamiento;\n• los °Brix de alimentación, permeado y rechazo, para seguir el paso "
     "de azúcares.\nSe continúa hasta terminar el ensayo."),
    ("Procedimiento",
     "¿Para qué sirve la purga con agua y cómo se sabe que terminó?",
     "Sirve para limpiar las líneas de rechazo y de permeado, arrastrando los restos de "
     "producto.\n\nSe abre el paso por cada línea entre 5 y 10 min hasta que el agua sale "
     "clara. Luego se toma una muestra y se mide la conductividad: debe estar alrededor de "
     "30–33 µS/cm. También se mide el flux de agua pura."),
    ("Procedimiento",
     "¿Cómo se hace la limpieza química y cómo se comprueba que funcionó?",
     "Se recircula una solución de NaOH (soda cáustica) al 1 % p/v por el equipo, que "
     "disuelve la capa de proteína que causa el fouling.\n\nDespués se purga otra vez con "
     "agua, midiendo flux y conductividad. La limpieza funcionó cuando ambos vuelven a sus "
     "valores iniciales; si no, se repite."),
    ("Medición",
     "¿Qué técnicas de laboratorio se usan para medir azúcares y proteína?",
     "Azúcares (lactosa): grados Brix con un refractómetro. Es una medida cualitativa "
     "que muestra si la lactosa está pasando al permeado, como se espera.\n\nProteína: "
     "espectrofotometría, por ejemplo el método de Bradford. Da la concentración exacta "
     "de proteína en cada corriente y permite calcular el rechazo R."),
]

COLORES_CAT = {
    "Conceptos": "#2e86ab",
    "Modelos": "#c00000",
    "Equipo": "#1f4e78",
    "Procedimiento": "#38a169",
    "Medición": "#dd6b20",
}


def _html_flashcards():
    tarjetas = [{"cat": c, "f": f, "r": r, "color": COLORES_CAT[c]} for c, f, r in FLASHCARDS]
    return """
<style>
  * { box-sizing: border-box; font-family: "Source Sans Pro", Helvetica, Arial, sans-serif; }
  body { margin: 0; }
  .barra { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
  .chip { border:1px solid #cbd5e0; background:#fff; color:#2d3748; border-radius:16px;
          padding:4px 12px; font-size:13px; cursor:pointer; }
  .chip.activo { background:#1f4e78; color:#fff; border-color:#1f4e78; }
  .escena { perspective: 1200px; width:100%; height:340px; cursor:pointer; }
  .tarjeta { position:relative; width:100%; height:100%; transition: transform .6s;
             transform-style: preserve-3d; }
  .tarjeta.volteada { transform: rotateY(180deg); }
  .cara { position:absolute; inset:0; backface-visibility:hidden; border-radius:14px;
          padding:24px 32px; display:flex; flex-direction:column; justify-content:center;
          align-items:center; text-align:center; box-shadow: 0 4px 14px rgba(0,0,0,.12); }
  .frente { background:#fff; border-top:8px solid var(--c); }
  .frente .preg { font-size:23px; font-weight:600; color:#1a202c; line-height:1.35; max-width:620px; }
  .reverso { background:var(--c); color:#fff; transform: rotateY(180deg); }
  .reverso { justify-content:flex-start; align-items:stretch; padding:40px 32px 34px; }
  .reverso .resp { font-size:15.5px; line-height:1.5; white-space:pre-line; text-align:left;
                   overflow-y:auto; flex:1; }
  .etiqueta { position:absolute; top:12px; left:16px; font-size:12px; font-weight:700;
              letter-spacing:.05em; text-transform:uppercase; color:var(--c); }
  .reverso .etiqueta { color:rgba(255,255,255,.85); }
  .pista { position:absolute; bottom:10px; font-size:12px; color:#a0aec0; }
  .reverso .pista { color:rgba(255,255,255,.75); }
  .controles { display:flex; justify-content:space-between; align-items:center; margin-top:14px; gap:8px; }
  .btn { border:none; border-radius:8px; padding:9px 16px; font-size:14px; cursor:pointer;
         background:#edf2f7; color:#2d3748; }
  .btn:hover { background:#e2e8f0; }
  .btn.ok { background:#c6f6d5; color:#22543d; }
  .btn.rep { background:#fed7d7; color:#742a2a; }
  .progreso { height:6px; background:#edf2f7; border-radius:3px; margin-top:14px; overflow:hidden; }
  .progreso > div { height:100%; background:#38a169; transition: width .3s; }
  .estado { font-size:13px; color:#4a5568; margin-top:6px; text-align:center; }
</style>
<div class="barra" id="filtros"></div>
<div class="escena" onclick="voltear()">
  <div class="tarjeta" id="tarjeta">
    <div class="cara frente" id="frente"><span class="etiqueta" id="cat1"></span>
      <div class="preg" id="preg"></div><span class="pista">Haz clic para ver la respuesta</span></div>
    <div class="cara reverso" id="reverso"><span class="etiqueta" id="cat2"></span>
      <div class="resp" id="resp"></div><span class="pista">Haz clic para volver</span></div>
  </div>
</div>
<div class="controles">
  <button class="btn" onclick="mover(-1)">← Anterior</button>
  <button class="btn rep" onclick="marcar(false)">🔁 Repasar</button>
  <button class="btn ok" onclick="marcar(true)">✅ Me la sé</button>
  <button class="btn" onclick="barajar()">🔀 Barajar</button>
  <button class="btn" onclick="mover(1)">Siguiente →</button>
</div>
<div class="progreso"><div id="barra"></div></div>
<div class="estado" id="estado"></div>
<script>
const TODAS = """ + json.dumps(tarjetas, ensure_ascii=False) + """;
let filtro = "Todas", mazo = TODAS.slice(), i = 0;
const sabidas = new Set();
const cats = ["Todas", ...new Set(TODAS.map(t => t.cat))];
const cont = document.getElementById("filtros");
cats.forEach(c => {
  const b = document.createElement("button");
  b.className = "chip" + (c === filtro ? " activo" : ""); b.textContent = c;
  b.onclick = () => { filtro = c; document.querySelectorAll(".chip").forEach(x => x.classList.remove("activo"));
    b.classList.add("activo"); mazo = TODAS.filter(t => c === "Todas" || t.cat === c); i = 0; pintar(); };
  cont.appendChild(b);
});
function pintar() {
  const t = mazo[i];
  document.getElementById("tarjeta").classList.remove("volteada");
  document.getElementById("tarjeta").style.setProperty("--c", t.color);
  document.getElementById("frente").style.setProperty("--c", t.color);
  document.getElementById("reverso").style.setProperty("--c", t.color);
  document.getElementById("cat1").textContent = t.cat;
  document.getElementById("cat2").textContent = t.cat;
  document.getElementById("preg").textContent = t.f;
  setTimeout(() => { document.getElementById("resp").textContent = t.r; }, 150);
  const n = mazo.filter(x => sabidas.has(x.f)).length;
  document.getElementById("barra").style.width = (100 * n / mazo.length) + "%";
  document.getElementById("estado").textContent =
    `Tarjeta ${i + 1} de ${mazo.length} · Te sabes ${n} de ${mazo.length}` +
    (n === mazo.length ? " 🎉 ¡Dominaste este mazo!" : "");
}
function voltear() { document.getElementById("tarjeta").classList.toggle("volteada"); }
function mover(d) { i = (i + d + mazo.length) % mazo.length; pintar(); }
function marcar(ok) { const f = mazo[i].f; ok ? sabidas.add(f) : sabidas.delete(f); mover(1); }
function barajar() { for (let k = mazo.length - 1; k > 0; k--) { const j = Math.floor(Math.random() * (k + 1));
  [mazo[k], mazo[j]] = [mazo[j], mazo[k]]; } i = 0; pintar(); }
pintar();
</script>
"""


def _seccion_flashcards():
    st.markdown(
        "Repasa los conceptos clave del gemelo digital. **Haz clic en la tarjeta** para "
        "voltearla, marca las que ya te sabes y repite las demás hasta dominar el mazo."
    )
    components.html(_html_flashcards(), height=510)


# =============================================================================
# 2. RETO "¿QUÉ PASARÍA SI...?"
# =============================================================================

def _seccion_reto(PARAMS, modelo_C, modelo_J_torta, modelo_J_exp):
    st.markdown(
        "Primero **predice** qué crees que va a pasar y luego **comprueba** con el "
        "modelo del gemelo digital. Equivocarse aquí no cuenta para la nota: es para aprender."
    )

    retos = [
        {
            "clave": "reto_c0",
            "titulo": "1. Más proteína al inicio",
            "pregunta": (
                "Dos corridas de 40 min: una arranca con C₀ = 5 g/L y otra con C₀ = 10 g/L. "
                "¿Qué pasa con la **concentración de proteína en el tanque**?"
            ),
            "opciones": [
                "Las dos suben exactamente los mismos g/L",
                "La de C₀ = 10 g/L sube más g/L en el mismo tiempo",
                "La de C₀ = 10 g/L baja con el tiempo",
            ],
            "correcta": 1,
            "explicacion": (
                "Según 1/C − 1/C₀ = −K·t, lo que baja a ritmo constante es **1/C**, no C. "
                "Cuando C₀ es mayor, 1/C₀ es menor y la misma resta pesa más en "
                "proporción: la concentración crece más rápido en g/L."
            ),
            "grafica": lambda: pd.DataFrame(
                {"C₀ = 5 g/L": modelo_C(np.arange(0, 41, 2), 5.0),
                 "C₀ = 10 g/L": modelo_C(np.arange(0, 41, 2), 10.0)},
                index=pd.Index(np.arange(0, 41, 2), name="Tiempo (min)")),
            "ylabel": "C tanque (g/L)",
        },
        {
            "clave": "reto_largo",
            "titulo": "2. Una corrida muy larga",
            "pregunta": (
                "Si dejas la ultrafiltración corriendo **150 min** (mucho más que los 40 min "
                "medidos), ¿qué modelo de flux da una proyección más realista?"
            ),
            "opciones": [
                "Hermia n=0: el flux sigue bajando sin límite",
                "Exponencial: el flux se estabiliza cerca de un mínimo J∞",
                "Los dos dan exactamente lo mismo",
            ],
            "correcta": 1,
            "explicacion": (
                "El modelo de torta (Hermia n=0) sigue cayendo indefinidamente. El "
                f"exponencial tiende a un flux mínimo físico J∞ ≈ {PARAMS['Jinf_exp']:.1f} "
                "L/(m²·h). Por eso, fuera del rango medido, es el más confiable para "
                "proyectar."
            ),
            "grafica": lambda: pd.DataFrame(
                {"Hermia n=0 (torta)": modelo_J_torta(np.arange(0, 151, 5)),
                 "Exponencial": modelo_J_exp(np.arange(0, 151, 5))},
                index=pd.Index(np.arange(0, 151, 5), name="Tiempo (min)")),
            "ylabel": "J (L/m² h)",
        },
        {
            "clave": "reto_agua",
            "titulo": "3. Agua pura por una membrana limpia",
            "pregunta": (
                "Después de la limpieza química haces circular **agua pura**. "
                "¿Cómo se comporta el flux de permeado?"
            ),
            "opciones": [
                "Cae con el tiempo, igual que con lactosuero",
                "Sube sin parar",
                "Se mantiene constante en la línea base de la membrana",
            ],
            "correcta": 2,
            "explicacion": (
                "Sin proteína no hay torta ni ensuciamiento, así que el flux se queda "
                f"constante (≈ {PARAMS['J_agua']:.1f} L/(m²·h)). Con este flux se calcula la "
                "resistencia propia de la membrana, R_M."
            ),
            "grafica": lambda: pd.DataFrame(
                {"Agua (membrana limpia)": np.full(21, PARAMS["J_agua"]),
                 "Lactosuero (Hermia)": modelo_J_torta(np.arange(0, 41, 2))},
                index=pd.Index(np.arange(0, 41, 2), name="Tiempo (min)")),
            "ylabel": "J (L/m² h)",
        },
    ]

    for r in retos:
        with st.container(border=True):
            st.subheader(r["titulo"])
            eleccion = st.radio(r["pregunta"], r["opciones"], index=None, key=r["clave"])
            if st.button("Comprobar con el modelo", key=r["clave"] + "_btn",
                         disabled=eleccion is None):
                st.session_state[r["clave"] + "_ver"] = True
            if st.session_state.get(r["clave"] + "_ver") and eleccion is not None:
                if r["opciones"].index(eleccion) == r["correcta"]:
                    st.success("¡Bien predicho! " + r["explicacion"])
                else:
                    st.error(
                        f"No exactamente. La respuesta es: **{r['opciones'][r['correcta']]}**. "
                        + r["explicacion"]
                    )
                st.line_chart(r["grafica"](), y_label=r["ylabel"])


# =============================================================================
# 3. EVALUACIÓN FINAL
# =============================================================================

# Banco de preguntas de selección múltiple: (pregunta, correcta, [distractores], pestaña de origen)
BANCO = [
    ("¿Qué compone principalmente la corriente de permeado?",
     "Agua, lactosa y sales minerales",
     ["Proteínas y grasas", "Solo proteínas concentradas", "Solución de NaOH"], "Información General"),
    ("En esta práctica, ¿qué se hace con la corriente de rechazo?",
     "Se recircula al tanque de alimentación, donde la proteína se va concentrando",
     ["Se desecha al desagüe", "Se mezcla con el permeado", "Se envía directo al tanque de NaOH"],
     "Información General"),
    ("¿Qué efecto tiene el fouling (ensuciamiento) sobre la operación?",
     "El flux de permeado disminuye y las presiones en los manómetros aumentan",
     ["El flux de permeado aumenta", "La concentración de proteína en el tanque disminuye",
      "No tiene ningún efecto medible"], "Información General"),
    ("¿Cuál es la diferencia entre flujo volumétrico y flux de permeado?",
     "El flux es el flujo volumétrico dividido por el área de membrana",
     ["Son exactamente lo mismo", "El flux es la masa de proteína retenida",
      "El flux se mide en g/L"], "Información General"),
    ("¿Qué modelo de flux se recomienda dentro del rango medido (0–40 min)?",
     "Hermia n = 0 (formación de torta)",
     ["Bloqueo completo (Hermia n = 2)", "Ley de Fick", "Modelo lineal"], "Guía de Usuario"),
    ("¿Por qué el modelo exponencial es más confiable para proyectar tiempos largos?",
     "Porque tiende a un flux mínimo físico J∞",
     ["Porque tiene el R² más alto", "Porque no depende del tiempo",
      "Porque fue el único modelo evaluado"], "Simulación / Guía de Usuario"),
    ("¿Qué ecuación describe la concentración de proteína en el tanque?",
     "1/C(t) − 1/C₀ = −K·t",
     ["C(t) = C₀ − K·t", "C(t) = C₀·e^(K·t)", "C(t) = K·t²"], "Guía de Usuario"),
    ("¿Qué supuesto principal se usa en el balance por lotes del tanque?",
     "Que la cantidad de proteína que atraviesa la membrana tiende a cero",
     ["Que el flux es constante", "Que el volumen del tanque no cambia",
      "Que no hay recirculación del rechazo"], "Guía de Usuario"),
    ("¿Cuál es el área de transferencia de la membrana del equipo?",
     "4.8 m²", ["0.48 m²", "48 m²", "1.026 m²"], "Información General"),
    ("¿Cuál es el volumen de operación estándar en el tanque de alimentación?",
     "Unos 80 L", ["Unos 8 L", "Unos 800 L", "Unos 5.2 L"], "Información General"),
    ("En operación óptima, ¿en qué rango está el coeficiente de rechazo R?",
     "Entre 93 % y 95 %", ["Entre 50 % y 60 %", "Entre 10 % y 20 %", "Exactamente 100 %"],
     "Información General"),
    ("¿Qué indicaría una caída drástica del coeficiente de rechazo?",
     "Una posible ruptura física en los poros de la membrana",
     ["Que la membrana quedó más limpia", "Que aumentó la concentración de proteína",
      "Que la bomba se apagó"], "Información General"),
    ("¿Qué solución se usa para la limpieza química de la membrana?",
     "NaOH al 1 % p/v", ["HCl concentrado", "Etanol al 70 %", "Agua destilada caliente"],
     "Documentación"),
    ("¿Qué se mide para verificar que el agua de purga es adecuada?",
     "La conductividad (~30–33 µS/cm)", ["Los °Brix", "La absorbancia a 595 nm", "El pH con papel indicador"],
     "Documentación"),
    ("¿A qué flujo de alimentación se ajusta el rotámetro al iniciar?",
     "Aproximadamente 6 L/min", ["Aproximadamente 60 L/min", "Aproximadamente 0.6 L/min",
                                 "Aproximadamente 26 L/min"], "Documentación"),
    ("¿Cada cuánto se toman datos durante la práctica?",
     "Cada 8 minutos", ["Cada 30 segundos", "Cada hora", "Solo al inicio y al final"],
     "Documentación"),
    ("¿Qué técnica se usa para determinar el contenido de proteína?",
     "Espectrofotometría (método de Bradford)",
     ["Refractometría (°Brix)", "Conductimetría", "Titulación con NaOH"], "Información General"),
    ("¿Para qué se miden los °Brix en las corrientes?",
     "Para seguir de forma cualitativa el paso de azúcares (lactosa)",
     ["Para medir la proteína exacta", "Para medir la presión de membrana",
      "Para verificar la conductividad"], "Información General"),
    ("Si haces circular agua por una membrana recién usada con lactosuero (sin limpieza química), ¿qué esperas?",
     "El flux arranca bajo y se recupera poco a poco",
     ["El flux es igual al de la membrana limpia desde el inicio", "El flux cae a cero",
      "El flux sube por encima del de agua limpia"], "Simulación"),
    ("¿Cómo se debe interpretar una simulación con t > 40 min?",
     "Como una extrapolación orientativa, no como un dato verificado",
     ["Como un dato experimental validado", "No se puede simular, la app lo bloquea",
      "Como un error del modelo"], "Simulación"),
    ("¿Cuánto lactosuero en polvo se agrega al tanque para preparar la alimentación?",
     "Unos 5.21 kg", ["Unos 52 kg", "Unos 0.5 kg", "Unos 80 kg"], "Documentación"),
    ("¿Cuál es una razón para usar un gemelo digital en esta práctica?",
     "El tiempo limitado de laboratorio, el costo de la materia prima y la fragilidad de las membranas",
     ["Reemplazar por completo la práctica presencial", "Evitar aprender los modelos matemáticos",
      "Porque el equipo real no existe"], "Información General"),
]

N_SELECCION = 10   # preguntas de selección múltiple por intento
NOTA_APROBATORIA = 3.0


def _generar_examen(PARAMS, modelo_C, modelo_J_torta):
    """Arma un examen aleatorio (preguntas y opciones barajadas)."""
    rng = random.Random()
    preguntas = []
    for preg, correcta, distractores, origen in rng.sample(BANCO, N_SELECCION):
        opciones = [correcta] + list(distractores)
        rng.shuffle(opciones)
        preguntas.append({"tipo": "opcion", "texto": preg, "opciones": opciones,
                          "correcta": correcta, "origen": origen})

    # Preguntas numéricas con datos aleatorios (se pueden resolver con la pestaña Simulación)
    C0 = round(rng.uniform(6.0, 9.0), 1)
    t1 = rng.choice([16, 24, 32, 40])
    C_t = float(modelo_C(t1, C0))
    preguntas.append({
        "tipo": "numero", "unidad": "g/L", "origen": "Simulación",
        "texto": (f"Una corrida de lactosuero arranca con C₀ = {C0} g/L. Según el modelo del "
                  f"gemelo digital, ¿cuál es la concentración de proteína en el tanque a los "
                  f"{t1} min? (Puedes usar la pestaña Simulación.)"),
        "correcta": C_t,
    })
    t2 = rng.choice([10, 20, 30, 40])
    J_t = float(modelo_J_torta(t2))
    preguntas.append({
        "tipo": "numero", "unidad": "L/(m²·h)", "origen": "Simulación",
        "texto": (f"Con el modelo de Hermia n = 0 (formación de torta), ¿cuál es el flux de "
                  f"permeado a los {t2} min? (Puedes usar la pestaña Simulación.)"),
        "correcta": J_t,
    })
    return preguntas


def _es_correcta(p, respuesta):
    if respuesta is None:
        return False
    if p["tipo"] == "opcion":
        return respuesta == p["correcta"]
    return abs(respuesta - p["correcta"]) <= 0.03 * abs(p["correcta"])  # tolerancia ±3 %


def _codigo_verificacion(nombre, correo, nota, fecha, secreto):
    base = f"{nombre.strip().lower()}|{correo.strip().lower()}|{nota:.1f}|{fecha}|{secreto}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:8].upper()


def _certificado_pdf(datos):
    """Genera un certificado de una página en PDF (solo con matplotlib)."""
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    fig = plt.figure(figsize=(11.69, 8.27))  # A4 horizontal
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0.03, 0.04), 0.94, 0.92, fill=False, lw=3, ec="#1f4e78"))
    ax.add_patch(plt.Rectangle((0.045, 0.055), 0.91, 0.89, fill=False, lw=1, ec="#1f4e78"))

    try:
        logo = plt.imread("Multimedia/Imagenes/logo_unal_color.webp")
        fig.add_axes([0.38, 0.78, 0.24, 0.12]).imshow(logo)
        fig.axes[-1].axis("off")
    except Exception:
        pass

    aprobado = datos["nota"] >= NOTA_APROBATORIA
    color = "#276749" if aprobado else "#9b2c2c"
    ax.text(0.5, 0.71, "CONSTANCIA DE EVALUACIÓN", ha="center", fontsize=26,
            weight="bold", color="#1f4e78")
    ax.text(0.5, 0.655, "Gemelo Digital — Membrana de Ultrafiltración de Lactosuero",
            ha="center", fontsize=14, color="#4a5568")
    ax.text(0.5, 0.58, "Se deja constancia de que", ha="center", fontsize=13, color="#2d3748")
    ax.text(0.5, 0.52, datos["nombre"], ha="center", fontsize=24, weight="bold", color="#1a202c")
    ax.text(0.5, 0.475, f"{datos['correo']}   ·   Grupo: {datos['grupo']}", ha="center",
            fontsize=12, color="#4a5568")
    ax.text(0.5, 0.41, "presentó la evaluación final de la pestaña «Aprende y Evalúate» y obtuvo:",
            ha="center", fontsize=13, color="#2d3748")
    ax.text(0.5, 0.31, f"{datos['nota']:.1f} / 5.0", ha="center", fontsize=44, weight="bold",
            color=color)
    ax.text(0.5, 0.245,
            f"{datos['correctas']} de {datos['total']} respuestas correctas  ·  "
            f"{'APROBADO' if aprobado else 'NO APROBADO'}",
            ha="center", fontsize=13, color=color, weight="bold")
    ax.text(0.5, 0.15,
            f"Fecha: {datos['fecha']}   ·   Tiempo empleado: {datos['tiempo_min']} min",
            ha="center", fontsize=11, color="#4a5568")
    ax.text(0.5, 0.105, f"Código de verificación: {datos['codigo']}", ha="center",
            fontsize=13, weight="bold", family="monospace", color="#1f4e78")
    ax.text(0.5, 0.075,
            "El profesor puede comprobar este código en el registro de evaluaciones del gemelo digital.",
            ha="center", fontsize=9, color="#718096")

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        pdf.savefig(fig)
    plt.close(fig)
    return buf.getvalue()


def _seccion_evaluacion(PARAMS, modelo_C, modelo_J_torta, guardar_evaluacion):
    ev = st.session_state.setdefault("evaluacion", {"estado": "inicio"})

    # ---------------------------------------------------------------- INICIO
    if ev["estado"] == "inicio":
        st.markdown(
            f"Pon a prueba lo que aprendiste en **todas** las pestañas del gemelo digital. "
            f"La evaluación tiene **{N_SELECCION} preguntas de selección múltiple** y "
            f"**2 preguntas numéricas** que puedes resolver con el simulador. Las preguntas "
            f"cambian en cada intento.\n\n"
            f"Al terminar recibes tu nota (0.0 a 5.0, se aprueba con {NOTA_APROBATORIA}) y una "
            f"**constancia en PDF** con un código de verificación para mostrarle a tu profesor."
        )
        with st.form("form_inicio_eval"):
            nombre = st.text_input("Nombre completo")
            correo = st.text_input("Correo institucional")
            grupo = st.text_input("Grupo / subgrupo de laboratorio")
            empezar = st.form_submit_button("Comenzar evaluación", type="primary")
        if empezar:
            if not nombre.strip() or "@" not in correo or not grupo.strip():
                st.warning("Completa tu nombre, un correo válido y tu grupo para comenzar.")
            else:
                ev.update(estado="examen", nombre=nombre.strip(), correo=correo.strip(),
                          grupo=grupo.strip(), inicio=time.time(),
                          preguntas=_generar_examen(PARAMS, modelo_C, modelo_J_torta))
                st.rerun()
        return

    # ---------------------------------------------------------------- EXAMEN
    if ev["estado"] == "examen":
        st.info(f"Evaluación de **{ev['nombre']}** · Responde todas las preguntas y presiona "
                f"**Enviar evaluación**. No podrás cambiar tus respuestas después de enviar.")
        with st.form("form_examen"):
            respuestas = []
            for k, p in enumerate(ev["preguntas"], start=1):
                st.markdown(f"**{k}. {p['texto']}**")
                if p["tipo"] == "opcion":
                    respuestas.append(st.radio("Respuesta", p["opciones"], index=None,
                                               key=f"ev_p{k}", label_visibility="collapsed"))
                else:
                    respuestas.append(st.number_input(f"Respuesta en {p['unidad']}", value=None,
                                                      step=0.01, format="%.2f", key=f"ev_p{k}"))
                st.write("")
            enviar = st.form_submit_button("Enviar evaluación", type="primary")
        if enviar:
            faltan = [k for k, r in enumerate(respuestas, start=1) if r is None]
            if faltan:
                st.warning("Te faltan por responder las preguntas: " + ", ".join(map(str, faltan)))
                return
            correctas = sum(_es_correcta(p, r) for p, r in zip(ev["preguntas"], respuestas))
            total = len(ev["preguntas"])
            nota = round(5.0 * correctas / total, 1)
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
            try:
                secreto = st.secrets["gsheets"]["token"]
            except Exception:
                secreto = "gemelo-uf"
            resultado = {
                "fecha": fecha, "nombre": ev["nombre"], "correo": ev["correo"],
                "grupo": ev["grupo"], "nota": nota, "correctas": correctas, "total": total,
                "tiempo_min": max(1, round((time.time() - ev["inicio"]) / 60)),
                "codigo": _codigo_verificacion(ev["nombre"], ev["correo"], nota, fecha, secreto),
            }
            try:
                guardar_evaluacion(resultado)
                resultado["guardado"] = True
            except Exception as e:
                resultado["guardado"] = False
                resultado["error_guardado"] = str(e)
            ev.update(estado="resultado", respuestas=respuestas, resultado=resultado)
            st.rerun()
        return

    # ------------------------------------------------------------- RESULTADO
    res = ev["resultado"]
    aprobado = res["nota"] >= NOTA_APROBATORIA
    col1, col2, col3 = st.columns(3)
    col1.metric("Nota", f"{res['nota']:.1f} / 5.0")
    col2.metric("Respuestas correctas", f"{res['correctas']} de {res['total']}")
    col3.metric("Código de verificación", res["codigo"])
    if aprobado:
        st.success("🎉 ¡Aprobaste la evaluación! Descarga tu constancia y preséntala a tu profesor.")
        if res["nota"] >= 4.5:
            st.balloons()
    else:
        st.error("No alcanzaste la nota aprobatoria. Repasa las pestañas y las flashcards, "
                 "y vuelve a intentarlo.")
    if not res.get("guardado"):
        st.caption(f"⚠️ No se pudo registrar el resultado en la hoja de evaluaciones "
                   f"({res.get('error_guardado')}). Guarda tu constancia en PDF.")

    st.download_button("📄 Descargar constancia (PDF)", data=_certificado_pdf(res),
                       file_name=f"Constancia_GemeloUF_{res['codigo']}.pdf",
                       mime="application/pdf", type="primary")

    with st.expander("Ver retroalimentación pregunta por pregunta"):
        for k, (p, r) in enumerate(zip(ev["preguntas"], ev["respuestas"]), start=1):
            ok = _es_correcta(p, r)
            if p["tipo"] == "opcion":
                tu = r
                bien = p["correcta"]
            else:
                tu = f"{r:.2f} {p['unidad']}"
                bien = f"{p['correcta']:.2f} {p['unidad']} (se acepta ±3 %)"
            st.markdown(f"{'✅' if ok else '❌'} **{k}. {p['texto']}**  \n"
                        f"Tu respuesta: {tu}" + ("" if ok else f"  \nRespuesta correcta: **{bien}**")
                        + f"  \n_Repasa: pestaña {p['origen']}_")

    if st.button("🔁 Hacer un nuevo intento"):
        st.session_state.evaluacion = {"estado": "inicio"}
        st.rerun()


def _panel_profesor(cargar_evaluaciones):
    with st.expander("👩‍🏫 Para el profesor: ver resultados de las evaluaciones"):
        if not st.session_state.get("autenticado_admin"):
            clave = st.text_input("Contraseña de administrador", type="password", key="clave_admin_eval")
            if st.button("Ingresar", key="btn_admin_eval"):
                try:
                    correcta = st.secrets["admin"]["password"]
                except Exception:
                    st.error("No se ha configurado la contraseña de administrador en los Secrets.")
                    return
                if clave == correcta:
                    st.session_state.autenticado_admin = True
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")
            return
        try:
            df = cargar_evaluaciones()
        except Exception as e:
            st.error(f"No se pudieron cargar las evaluaciones: {e}")
            return
        if df.empty:
            st.write("Todavía no hay evaluaciones registradas.")
            return
        codigo = st.text_input("Verificar un código de constancia", key="buscar_codigo").strip().upper()
        if codigo:
            hallado = df[df["codigo"].astype(str).str.upper() == codigo]
            if hallado.empty:
                st.error("Ese código no aparece en el registro.")
            else:
                st.success("Código válido ✅")
                st.dataframe(hallado, hide_index=True, width="stretch")
        st.dataframe(df.sort_values("fecha", ascending=False), hide_index=True, width="stretch")
        st.download_button("📥 Descargar todas las evaluaciones (CSV)",
                           data=df.to_csv(index=False).encode("utf-8"),
                           file_name="evaluaciones_gemelo_uf.csv", mime="text/csv")


# =============================================================================
# PÁGINA
# =============================================================================

def pagina_aprende(PARAMS, modelo_C, modelo_J_torta, modelo_J_exp,
                   guardar_evaluacion, cargar_evaluaciones):
    st.write("# Aprende y Evalúate")
    st.markdown(
        "Repasa con las flashcards, pon a prueba tu intuición con el modelo y, cuando te "
        "sientas listo, presenta la evaluación final."
    )
    tab1, tab2, tab3 = st.tabs(["🃏 Flashcards", "🧪 ¿Qué pasaría si...?", "📝 Evaluación final"])
    with tab1:
        _seccion_flashcards()
    with tab2:
        _seccion_reto(PARAMS, modelo_C, modelo_J_torta, modelo_J_exp)
    with tab3:
        _seccion_evaluacion(PARAMS, modelo_C, modelo_J_torta, guardar_evaluacion)
        st.divider()
        _panel_profesor(cargar_evaluaciones)
