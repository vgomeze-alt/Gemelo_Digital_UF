# test_pre_post.py
# Test de entrada (antes de la práctica) y test de salida (después) del Gemelo Digital UF.
#
# - Son las MISMAS 10 preguntas en los dos momentos (cambia solo el orden), para poder
#   comparar y medir cuánto se aprendió con la práctica y el gemelo digital.
# - El test de entrada no muestra nota ni respuestas (para no "enseñar" el test).
# - El test de salida muestra la nota, la comparación con la entrada y las correcciones.
# - Los dos se emparejan por el correo del estudiante.
# - El profesor ve el resumen (incluida la ganancia normalizada de Hake) en el panel
#   de administrador de "Sube tus Datos".
#
# Para cambiar una pregunta basta con editar PREGUNTAS. Si se cambian, conviene hacerlo
# entre semestres para no mezclar resultados de preguntas distintas.

import random
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

COLUMNAS_PREPOST = ["fecha", "tipo", "nombre", "correo", "grupo",
                    "correctas", "total", "porcentaje", "respuestas"]

# (id, tema, pregunta, respuesta correcta, [distractores])
PREGUNTAS = [
    ("P1", "Conceptos",
     "¿Por qué la concentración de proteína en el tanque aumenta con el tiempo?",
     "Porque el agua sale por el permeado y la proteína retenida vuelve al tanque",
     ["Porque se agrega más lactosuero en polvo durante la práctica",
      "Porque la proteína se forma por reacción química en el tanque",
      "Porque el permeado se devuelve al tanque"]),
    ("P2", "Conceptos",
     "¿Qué efecto tiene el ensuciamiento (fouling) sobre la operación?",
     "El flux de permeado disminuye y las presiones en los manómetros aumentan",
     ["El flux de permeado aumenta",
      "La concentración de proteína en el tanque disminuye",
      "No tiene ningún efecto medible"]),
    ("P3", "Modelos",
     "¿Qué mecanismo físico representa el modelo de Hermia n = 0?",
     "La formación de una capa (torta) de proteína sobre la membrana",
     ["El bloqueo de cada poro por una sola partícula",
      "La evaporación del agua",
      "La disolución de la membrana"]),
    ("P4", "Modelos",
     "En el balance por lotes del tanque, ¿qué variable cambia de forma lineal con el tiempo?",
     "1/C, el inverso de la concentración",
     ["La concentración C", "El flux J", "El área de membrana"]),
    ("P5", "Equipo",
     "¿Con qué se regula cuánto sale por permeado y cuánto por rechazo durante la práctica?",
     "Con las vueltas de la válvula roja de la línea de rechazo (V9)",
     ["Con la válvula 3 del tablero",
      "Con la temperatura del lactosuero",
      "Con la cantidad de lactosuero en polvo"]),
    ("P6", "Equipo",
     "¿Qué mide el coeficiente de rechazo R?",
     "La selectividad de la membrana: qué fracción de proteína retiene",
     ["La presión de entrada", "El volumen del tanque", "La conductividad del agua"]),
    ("P7", "Procedimiento",
     "¿Qué válvulas del panel se abren para la ultrafiltración de lactosuero?",
     "Solo las válvulas 1 y 2",
     ["Las válvulas 1, 2 y 3", "Las válvulas 3 y 4", "Todas a la vez"]),
    ("P8", "Procedimiento",
     "¿Cómo se comprueba que la limpieza química con NaOH funcionó?",
     "La conductividad y el flux de agua vuelven a sus valores iniciales",
     ["El permeado sale de color amarillo",
      "La presión se vuelve cero",
      "El tanque de alimentación queda lleno"]),
    ("P9", "Medición",
     "¿Para qué se mide el flux de agua pura al inicio y al final?",
     "Para conocer la resistencia propia de la membrana y verificar la limpieza",
     ["Para medir la proteína en el permeado",
      "Para calcular la densidad del lactosuero",
      "No tiene ninguna utilidad"]),
    ("P10", "Simulación",
     "¿Cómo se debe interpretar una simulación con t > 40 min?",
     "Como una extrapolación orientativa, no como un dato verificado",
     ["Como un dato experimental validado",
      "No se puede simular, la app lo bloquea",
      "Como un error del modelo"]),
]
IDS = [p[0] for p in PREGUNTAS]
TOTAL = len(PREGUNTAS)
NOMBRE_TIPO = {"entrada": "Test de entrada", "salida": "Test de salida"}


def _orden(tipo):
    """Orden fijo de preguntas y opciones para cada tipo (distinto entre entrada y salida)."""
    rng = random.Random(f"gemelo-uf-{tipo}")
    preguntas = list(PREGUNTAS)
    rng.shuffle(preguntas)
    salida = []
    for pid, tema, preg, correcta, distr in preguntas:
        opciones = [correcta] + list(distr)
        rng.shuffle(opciones)
        salida.append((pid, tema, preg, correcta, opciones))
    return salida


def calificar(respuestas):
    """respuestas: {id: opción elegida}. Devuelve (correctas, {id: 0/1})."""
    correctas = {p[0]: p[3] for p in PREGUNTAS}
    detalle = {pid: int(respuestas.get(pid) == correctas[pid]) for pid in IDS}
    return sum(detalle.values()), detalle


def _ultimo(df, correo, tipo):
    if df is None or df.empty:
        return None
    sub = df[(df["tipo"] == tipo) &
             (df["correo"].astype(str).str.strip().str.lower() == correo.strip().lower())]
    if sub.empty:
        return None
    return sub.sort_values("fecha").iloc[-1]


# =============================================================================
# FORMULARIO DEL ESTUDIANTE
# =============================================================================

def seccion_test(tipo, guardar, cargar, prefijo):
    """Muestra el test ('entrada' o 'salida'). prefijo evita choques de claves
    cuando el mismo test aparece en dos páginas."""
    clave_res = f"prepost_resultado_{prefijo}_{tipo}"
    if tipo == "entrada":
        st.markdown(
            f"**{TOTAL} preguntas · unos 5 minutos · opcional.** Respóndelo **antes** de la "
            "práctica con lo que sabes ahora, sin repasar: no cuenta para la nota. Al final de "
            "la práctica presentas el **test de salida** (las mismas preguntas) y ves cuánto "
            "aprendiste.")
    else:
        st.markdown(
            f"**{TOTAL} preguntas · unos 5 minutos · opcional.** Son las mismas preguntas del "
            "test de entrada en otro orden. Usa **el mismo correo** para poder comparar tus "
            "resultados.")

    res = st.session_state.get(clave_res)
    if res:
        _mostrar_resultado(tipo, res, cargar)
        if st.button("Presentar de nuevo", key=f"prepost_otra_{prefijo}_{tipo}"):
            st.session_state.pop(clave_res, None)
            st.rerun()
        return

    with st.form(f"form_prepost_{prefijo}_{tipo}"):
        c1, c2, c3 = st.columns([2, 2, 1])
        nombre = c1.text_input("Nombre completo", key=f"pp_nom_{prefijo}_{tipo}")
        correo = c2.text_input("Correo institucional", key=f"pp_cor_{prefijo}_{tipo}")
        grupo = c3.text_input("Grupo", key=f"pp_gru_{prefijo}_{tipo}")
        respuestas = {}
        for i, (pid, tema, preg, correcta, opciones) in enumerate(_orden(tipo), start=1):
            respuestas[pid] = st.radio(f"**{i}.** {preg}", opciones, index=None,
                                       key=f"pp_{prefijo}_{tipo}_{pid}")
        enviar = st.form_submit_button(f"Enviar {NOMBRE_TIPO[tipo].lower()}", type="primary")

    if enviar:
        faltan = [i for i, (pid, *_r) in enumerate(_orden(tipo), start=1) if respuestas[pid] is None]
        if not nombre.strip() or "@" not in correo:
            st.error("Escribe tu nombre y un correo válido (sirve para emparejar entrada y salida).")
            return
        if faltan:
            st.error("Te faltan las preguntas: " + ", ".join(map(str, faltan)) +
                     ". Si no sabes, elige la que te parezca más probable.")
            return
        n_ok, detalle = calificar(respuestas)
        fila = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tipo": tipo,
            "nombre": nombre.strip(),
            "correo": correo.strip().lower(),
            "grupo": grupo.strip(),
            "correctas": n_ok,
            "total": TOTAL,
            "porcentaje": round(100 * n_ok / TOTAL, 1),
            # Prefijo "R" para que Google Sheets no lo convierta en número (perdería los ceros)
            "respuestas": "R" + "".join(str(detalle[p]) for p in IDS),
        }
        error = None
        try:
            guardar(fila)
        except Exception as e:
            error = str(e)
        st.session_state[clave_res] = {"fila": fila, "elegidas": respuestas, "error": error}
        st.rerun()


def _mostrar_resultado(tipo, res, cargar):
    fila = res["fila"]
    if res.get("error"):
        st.warning("Tus respuestas no se pudieron guardar en el registro del profesor "
                   f"({res['error']}). Avísale al profesor.")
    if tipo == "entrada":
        st.success(f"✅ ¡Listo, {fila['nombre'].split()[0]}! Tu test de entrada quedó guardado. "
                   "Ahora haz la práctica y, al terminar, presenta el **test de salida** "
                   "(está aquí en Aprende y Evalúate y al final de **Sube tus Datos**).")
        return

    try:
        previo = _ultimo(cargar(), fila["correo"], "entrada")
    except Exception:
        previo = None
    c1, c2, c3 = st.columns(3)
    c2.metric("Test de salida", f"{fila['correctas']}/{TOTAL}")
    if previo is not None:
        pre = int(float(previo["correctas"]))
        c1.metric("Test de entrada", f"{pre}/{TOTAL}")
        c3.metric("Mejora", f"{fila['correctas'] - pre:+d} preguntas",
                  delta=f"{100 * (fila['correctas'] - pre) / TOTAL:+.0f} %")
    else:
        c1.metric("Test de entrada", "—")
        st.caption("No encontramos un test de entrada con ese correo, así que no se puede "
                   "calcular tu mejora.")

    st.markdown("##### Revisión de respuestas")
    for i, (pid, tema, preg, correcta, _ops) in enumerate(_orden(tipo), start=1):
        elegida = res["elegidas"].get(pid)
        if elegida == correcta:
            st.markdown(f"✅ **{i}.** {preg}  \n  {correcta}")
        else:
            st.markdown(f"❌ **{i}.** {preg}  \n  Elegiste: {elegida}  \n  "
                        f"**Correcta:** {correcta}")


# =============================================================================
# PANEL DEL PROFESOR
# =============================================================================

def emparejar(df):
    """Una fila por estudiante (correo) con su último test de entrada y de salida."""
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["correo"] = df["correo"].astype(str).str.strip().str.lower()
    df["correctas"] = pd.to_numeric(df["correctas"], errors="coerce")
    df = df.sort_values("fecha")
    ult = df.groupby(["correo", "tipo"]).tail(1)
    pre = ult[ult["tipo"] == "entrada"].set_index("correo")
    post = ult[ult["tipo"] == "salida"].set_index("correo")
    correos = sorted(set(pre.index) | set(post.index))
    filas = []
    for c in correos:
        p = pre.loc[c] if c in pre.index else None
        q = post.loc[c] if c in post.index else None
        ref = q if q is not None else p
        e = 100 * p["correctas"] / TOTAL if p is not None else np.nan
        s = 100 * q["correctas"] / TOTAL if q is not None else np.nan
        g = (s - e) / (100 - e) if (p is not None and q is not None and e < 100) else np.nan
        filas.append({"Nombre": ref["nombre"], "Correo": c, "Grupo": ref["grupo"],
                      "Entrada (%)": e, "Salida (%)": s, "Mejora (puntos)": s - e,
                      "Ganancia g": g,
                      "_resp_pre": p["respuestas"] if p is not None else "",
                      "_resp_post": q["respuestas"] if q is not None else ""})
    return pd.DataFrame(filas)


def _aciertos_por_pregunta(cadenas):
    limpias = ["".join(ch for ch in str(c) if ch in "01") for c in cadenas]
    m = [[int(ch) for ch in c] for c in limpias if len(c) == TOTAL]
    if not m:
        return np.full(TOTAL, np.nan)
    return 100 * np.mean(m, axis=0)


def panel_profesor(cargar):
    import matplotlib.pyplot as plt

    st.markdown("#### 📋 Test de entrada y salida")
    st.caption("Mismas 10 preguntas antes y después de la práctica, emparejadas por correo. "
               "La ganancia normalizada de Hake, g = (salida − entrada)/(100 − entrada), indica "
               "qué fracción de lo que no sabían aprendieron: g < 0.3 baja, 0.3–0.7 media, "
               "> 0.7 alta.")
    try:
        df = cargar()
    except Exception as e:
        st.warning("No se pudieron leer los tests. Si acabas de activar esta función, actualiza "
                   f"el Apps Script con la pestaña 'pre_post' y publícalo como 'Nueva versión'. ({e})")
        return
    tabla = emparejar(df)
    if tabla.empty:
        st.write("Todavía nadie ha presentado el test de entrada o de salida.")
        return

    grupos = ["Todos"] + sorted(g for g in tabla["Grupo"].astype(str).unique() if g.strip())
    sel = st.selectbox("Grupo", grupos, key="prepost_grupo")
    if sel != "Todos":
        tabla = tabla[tabla["Grupo"].astype(str) == sel]
    pares = tabla.dropna(subset=["Entrada (%)", "Salida (%)"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tests de entrada", int(tabla["Entrada (%)"].notna().sum()))
    c2.metric("Tests de salida", int(tabla["Salida (%)"].notna().sum()))
    if pares.empty:
        c3.metric("Entrada → salida", "—")
        c4.metric("Ganancia g del curso", "—")
        st.info("Aún no hay estudiantes con los dos tests (entrada y salida con el mismo correo).")
    else:
        m_pre, m_post = pares["Entrada (%)"].mean(), pares["Salida (%)"].mean()
        g_curso = (m_post - m_pre) / (100 - m_pre) if m_pre < 100 else np.nan
        c3.metric("Entrada → salida", f"{m_pre:.0f} % → {m_post:.0f} %",
                  delta=f"{m_post - m_pre:+.0f} puntos")
        c4.metric("Ganancia g del curso", "—" if np.isnan(g_curso) else f"{g_curso:.2f}",
                  help=f"Con {len(pares)} estudiante(s) que presentaron los dos tests.")

        # Gráfica 1: antes vs después por estudiante
        fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
        for _, r in pares.iterrows():
            color = "#2a9d8f" if r["Salida (%)"] >= r["Entrada (%)"] else "#e76f51"
            axs[0].plot([0, 1], [r["Entrada (%)"], r["Salida (%)"]], "-o", color=color, alpha=0.6)
        axs[0].plot([0, 1], [m_pre, m_post], "-o", color="black", lw=3, label="Promedio")
        axs[0].set_xticks([0, 1], ["Entrada", "Salida"])
        axs[0].set_ylim(-5, 105)
        axs[0].set_ylabel("Aciertos (%)")
        axs[0].set_title("Cada línea es un estudiante")
        axs[0].legend(loc="lower right")
        axs[0].grid(alpha=0.3)

        # Gráfica 2: aciertos por pregunta
        a_pre = _aciertos_por_pregunta(pares["_resp_pre"])
        a_post = _aciertos_por_pregunta(pares["_resp_post"])
        x = np.arange(TOTAL)
        axs[1].bar(x - 0.2, a_pre, 0.4, label="Entrada", color="#b0b7c3")
        axs[1].bar(x + 0.2, a_post, 0.4, label="Salida", color="#2a9d8f")
        axs[1].set_xticks(x, IDS)
        axs[1].set_ylim(0, 105)
        axs[1].set_ylabel("Estudiantes que aciertan (%)")
        axs[1].set_title("Aciertos por pregunta")
        axs[1].legend()
        axs[1].grid(alpha=0.3, axis="y")
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        detalle = pd.DataFrame({
            "Pregunta": IDS, "Tema": [p[1] for p in PREGUNTAS],
            "Texto": [p[2] for p in PREGUNTAS],
            "Entrada (%)": np.round(a_pre, 0), "Salida (%)": np.round(a_post, 0),
            "Cambio (puntos)": np.round(a_post - a_pre, 0)})
        flojas = detalle[detalle["Salida (%)"] < 60]
        if not flojas.empty:
            st.warning("Preguntas que menos del 60 % acierta después de la práctica (conviene "
                       "reforzarlas en clase): " + ", ".join(
                           f"{r.Pregunta} ({r.Tema})" for r in flojas.itertuples()))
        with st.expander("Ver detalle por pregunta"):
            st.dataframe(detalle, hide_index=True, width="stretch")

    vista = tabla.drop(columns=["_resp_pre", "_resp_post"]).round(
        {"Entrada (%)": 0, "Salida (%)": 0, "Mejora (puntos)": 0, "Ganancia g": 2})
    st.dataframe(vista, hide_index=True, width="stretch")
    st.download_button("📥 Descargar resultados entrada/salida (CSV)",
                       data=vista.to_csv(index=False).encode("utf-8"),
                       file_name="test_entrada_salida_gemelo_uf.csv", mime="text/csv",
                       key="prepost_csv")
