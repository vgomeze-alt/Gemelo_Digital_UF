# analisis_datos.py
# Paso que cierra el ciclo del gemelo digital: lee la plantilla que sube un
# grupo, recalcula sus resultados con las MISMAS definiciones del modelo,
# ajusta sus propios parámetros (Hermia n=0 y balance por lotes) y los compara
# con el modelo de referencia (relación 28/72, válvula roja en la vuelta 2).

import io

import numpy as np
import pandas as pd
import streamlit as st

from plantilla_uf import TABLA_VALVULA


class ErrorPlantilla(Exception):
    """El archivo no es la plantilla del gemelo o le faltan datos clave."""


# ------------------------------------------------------------------ lectura
def _celda(wb, nombre):
    if nombre not in wb.defined_names:
        return None
    hoja, ref = next(wb.defined_names[nombre].destinations)
    return wb[hoja][ref.replace("$", "")].value


def _num(v):
    if v is None or (isinstance(v, str) and v.strip() in ("", "-", "—")):
        return np.nan
    if isinstance(v, str):
        v = v.replace(",", ".").strip()
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def leer_plantilla(contenido):
    """Lee la plantilla (bytes) y devuelve (info, DataFrame con datos medidos)."""
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(contenido), data_only=False)
    except Exception:
        raise ErrorPlantilla("No se pudo abrir el archivo como Excel (.xlsx).")
    if "tabla_datos" not in wb.defined_names:
        raise ErrorPlantilla(
            "Este archivo no es la plantilla actual del gemelo digital. Descarga la "
            "plantilla del paso 1, pasa tus datos a ella y vuelve a subirla.")

    info = {
        "vuelta": _num(_celda(wb, "vuelta_V9")),
        "area": _num(_celda(wb, "area_membrana")) or 4.8,
        "densidad": _num(_celda(wb, "densidad")) or 1.0208,
        "tara": _num(_celda(wb, "tara_tanque")),
        "m": _num(_celda(wb, "cal_m")),
        "b": _num(_celda(wb, "cal_b")),
        "temperatura": _num(_celda(wb, "temperatura")),
        "caudal": _num(_celda(wb, "caudal_alimentacion")),
    }
    if np.isnan(info["tara"]):
        info["tara"] = 8.3
    if np.isnan(info["b"]):
        info["b"] = 0.0

    hoja, ref = next(wb.defined_names["tabla_datos"].destinations)
    ws = wb[hoja]
    filas = list(ws[ref.replace("$", "")])[1:]          # sin encabezado
    datos = []
    for fila in filas:
        v = [_num(c.value) for c in fila[:9]]
        if not np.isnan(v[0]):
            datos.append(v)
    df = pd.DataFrame(datos, columns=["t", "m_perm", "m_tanque", "P_ent", "P_post",
                                      "brix_t", "brix_p", "abs_t", "abs_p"])
    if len(df) < 3:
        raise ErrorPlantilla("La tabla tiene menos de 3 tiempos con datos; se necesitan al menos 3.")
    return info, df.sort_values("t").reset_index(drop=True)


# ------------------------------------------------------------------ cálculos
def calcular(info, df):
    """Mismas definiciones que la plantilla y que el ajuste del modelo."""
    d = df.copy()
    d["V_perm"] = d["m_perm"] / info["densidad"]
    d["V_tanque"] = (d["m_tanque"] - info["tara"]) / info["densidad"]
    with np.errstate(divide="ignore", invalid="ignore"):
        d["J"] = np.where(d["t"] > 0, d["V_perm"] / (d["t"] / 60) / info["area"], np.nan)
    if not np.isnan(info["m"]):
        d["C_t"] = info["m"] * d["abs_t"] + info["b"]
        d["C_p"] = info["m"] * d["abs_p"] + info["b"]
        with np.errstate(divide="ignore", invalid="ignore"):
            d["R"] = (1 - d["C_p"] / d["C_t"]) * 100
    else:
        d["C_t"] = d["C_p"] = d["R"] = np.nan
    return d


def _r2(y, yhat):
    ss_res = np.sum((y - yhat) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    return 1 - ss_res / ss_tot if ss_tot > 0 else np.nan


def ajustar(d):
    """Ajusta Hermia n=0 (1/J² = 1/J0² + 2·Kc·t) y el balance (1/C − 1/C0 = −K·t)."""
    res = {}
    m = d["J"].notna() & (d["t"] > 0) & (d["J"] > 0)
    if m.sum() >= 3:
        t, J = d.loc[m, "t"].values, d.loc[m, "J"].values
        pend, inter = np.polyfit(t, 1 / J ** 2, 1)
        if inter > 0 and pend > 0:
            J0, Kc = inter ** -0.5, pend / 2
            res.update(J0=J0, Kc=Kc, R2_J=_r2(J, (1 / J0 ** 2 + 2 * Kc * t) ** -0.5))
    mc = d["C_t"].notna() & (d["C_t"] > 0)
    if mc.sum() >= 3 and (d.loc[mc, "t"] == 0).any():
        C0 = float(d.loc[mc & (d["t"] == 0), "C_t"].iloc[0])
        t, C = d.loc[mc, "t"].values, d.loc[mc, "C_t"].values
        y = 1 / C0 - 1 / C
        if np.sum(t ** 2) > 0:
            K = np.sum(t * y) / np.sum(t ** 2)
            if K > 0:
                res.update(C0=C0, K=K)
                with np.errstate(divide="ignore", invalid="ignore"):
                    Chat = 1 / (1 / C0 - K * t)
                res["R2_C"] = _r2(C, Chat)
    return res


def diagnostico(info, d, aj, PARAMS, modelo_J_torta):
    """Mensajes de interpretación para el grupo: (nivel, texto)."""
    msj = []
    v = info["vuelta"]
    if np.isnan(v) or int(v) not in TABLA_VALVULA:
        msj.append(("warning", "No se indicó la vuelta de la válvula roja: la comparación supone "
                               "la práctica estándar (vuelta 2, relación 28/72)."))
    elif int(v) != 2:
        p, r = TABLA_VALVULA[int(v)]
        msj.append(("info", f"Trabajaste en la vuelta {int(v)} (relación {p}/{r}) y el modelo de "
                            "referencia es de la vuelta 2 (28/72). Con menos permeado por vuelta es "
                            "esperable un flux distinto: compara tendencias, no valores exactos."))
    m = d["J"].notna()
    if m.sum():
        tf = float(d.loc[m, "t"].iloc[-1])
        Jf = float(d.loc[m, "J"].iloc[-1])
        Jref = float(modelo_J_torta(tf))
        dif = Jf / Jref - 1
        if dif < -0.15:
            msj.append(("warning", f"A los {tf:g} min tu flux ({Jf:.1f} L/m²·h) está un {abs(dif):.0%} "
                                   f"por debajo del modelo ({Jref:.1f}). Posibles causas: membrana con "
                                   "ensuciamiento previo (limpieza incompleta), otra vuelta de la válvula, "
                                   "menor caudal de alimentación o error de lectura en la báscula."))
        elif dif > 0.15:
            msj.append(("info", f"A los {tf:g} min tu flux ({Jf:.1f} L/m²·h) está un {dif:.0%} por encima "
                                f"del modelo ({Jref:.1f}): la membrana estaba más limpia o la temperatura "
                                "era mayor. Revisa también que el peso de permeado sea el acumulado."))
        else:
            msj.append(("success", f"Tu flux final ({Jf:.1f} L/m²·h a {tf:g} min) coincide con el modelo "
                                   f"del gemelo digital ({Jref:.1f}) dentro de ±15 %."))
        if (np.diff(d.loc[d["t"] > 0, "V_perm"].dropna()) < 0).any():
            msj.append(("error", "El volumen de permeado disminuye en algún tiempo: el peso de permeado "
                                 "debe ser ACUMULADO (lo que marca la báscula desde el inicio)."))
    if "Kc" in aj:
        rel = aj["Kc"] / PARAMS["Kc_torta"]
        if rel > 1.3:
            msj.append(("warning", f"Tu torta creció {rel:.1f} veces más rápido que en la referencia "
                                   f"(Kc = {aj['Kc']:.2e}): más ensuciamiento. Revisa la limpieza previa y "
                                   "el microfiltro."))
    R = d["R"].dropna()
    if len(R):
        if R.mean() < 90:
            msj.append(("error", f"Coeficiente de rechazo promedio de {R.mean():.0f} %, por debajo del rango "
                                 "normal (93–95 %): la membrana deja pasar proteína. Posible daño de las "
                                 "fibras o error en la calibración de absorbancia. Avísale al profesor."))
        else:
            msj.append(("success", f"Coeficiente de rechazo promedio de {R.mean():.0f} %: la membrana retiene "
                                   "la proteína como se espera (93–95 % en operación normal)."))
    P = d["P_ent"].dropna()
    if len(P) and P.max() > 58:
        msj.append(("error", f"La presión de entrada llegó a {P.max():.0f} psi, por encima de la presión "
                             "máxima de la membrana (4 bar ≈ 58 psi)."))
    if np.isnan(info["m"]):
        msj.append(("info", "Sin pendiente de calibración no se calculan concentraciones ni rechazo: "
                            "escríbela en la plantilla para obtener el análisis completo."))
    return msj


def alertas_graves(d):
    """Condiciones que impiden usar la práctica para actualizar el modelo."""
    al = []
    if (np.diff(d.loc[d["t"] > 0, "V_perm"].dropna()) < 0).any():
        al.append("peso de permeado no acumulado")
    R = d["R"].dropna()
    if len(R) and R.mean() < 90:
        al.append(f"rechazo bajo ({R.mean():.0f} %)")
    P = d["P_ent"].dropna()
    if len(P) and P.max() > 58:
        al.append(f"presión sobre el máximo ({P.max():.0f} psi)")
    if d["J"].notna().sum() < 3:
        al.append("menos de 3 puntos de flux")
    return al


# ------------------------------------------------------------------ interfaz
def mostrar_analisis(contenido, PARAMS, modelo_J_torta, modelo_C):
    import matplotlib.pyplot as plt

    try:
        info, df = leer_plantilla(contenido)
    except ErrorPlantilla as e:
        st.error(f"📄 {e}")
        return None

    d = calcular(info, df)
    aj = ajustar(d)

    st.markdown("#### 🔍 Así se ven tus datos frente al gemelo digital")
    st.caption("Revisa este análisis antes de enviar: si algo no cuadra, corrige el Excel y vuelve a subirlo.")

    for nivel, texto in diagnostico(info, d, aj, PARAMS, modelo_J_torta):
        getattr(st, nivel)(texto)

    c1, c2, c3, c4 = st.columns(4)
    if "J0" in aj:
        c1.metric("J₀ ajustado (L/m²·h)", f"{aj['J0']:.1f}", f"{aj['J0'] - PARAMS['J0_torta']:+.1f} vs. modelo")
        c2.metric("R² flux (Hermia n=0)", f"{aj['R2_J']:.3f}")
    if "K" in aj:
        c3.metric("K ajustado ((g/L)⁻¹·min⁻¹)", f"{aj['K']:.5f}",
                  f"{(aj['K'] / PARAMS['K'] - 1):+.0%} vs. modelo")
        c4.metric("R² concentración", f"{aj['R2_C']:.3f}")

    t_fino = np.linspace(0, max(40.0, float(d["t"].max())), 120)
    col1, col2 = st.columns(2)
    with col1:
        fig, ax = plt.subplots(figsize=(5.2, 3.6))
        ax.plot(t_fino[1:], modelo_J_torta(t_fino[1:]), "k--", lw=1.4, label="Modelo de referencia (vuelta 2)")
        if "J0" in aj:
            ax.plot(t_fino[1:], (1 / aj["J0"] ** 2 + 2 * aj["Kc"] * t_fino[1:]) ** -0.5,
                    color="#c00000", lw=2, label="Ajuste con tus datos")
        ax.scatter(d["t"], d["J"], s=45, color="#c00000", zorder=5, label="Tus datos")
        ax.set_xlabel("Tiempo (min)"); ax.set_ylabel("J (L/m² h)"); ax.set_title("Flux de permeado")
        ax.grid(alpha=0.3); ax.legend(fontsize=8)
        fig.tight_layout(); st.pyplot(fig); plt.close(fig)
    with col2:
        if d["C_t"].notna().sum() >= 2:
            C0 = aj.get("C0", float(PARAMS["C0_valido"]))
            fig, ax = plt.subplots(figsize=(5.2, 3.6))
            ax.plot(t_fino, modelo_C(t_fino, C0), "k--", lw=1.4, label="Modelo de referencia")
            if "K" in aj:
                with np.errstate(divide="ignore", invalid="ignore"):
                    ax.plot(t_fino, 1 / (1 / C0 - aj["K"] * t_fino), color="#1f4e78", lw=2,
                            label="Ajuste con tus datos")
            ax.scatter(d["t"], d["C_t"], s=45, color="#1f4e78", zorder=5, label="Tus datos")
            ax.set_xlabel("Tiempo (min)"); ax.set_ylabel("C tanque (g/L)")
            ax.set_title("Proteína en el tanque"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
            fig.tight_layout(); st.pyplot(fig); plt.close(fig)
        else:
            st.info("Agrega las absorbancias y la calibración para ver la concentración.")

    with st.expander("📋 Tabla calculada"):
        tabla = d[["t", "V_perm", "J", "V_tanque", "C_t", "C_p", "R", "P_ent", "P_post"]].rename(columns={
            "t": "t (min)", "V_perm": "V permeado (L)", "J": "J (L/m²·h)", "V_tanque": "V tanque (L)",
            "C_t": "C tanque (g/L)", "C_p": "C permeado (g/L)", "R": "Rechazo (%)",
            "P_ent": "P entrada (psi)", "P_post": "P post-filtro (psi)"})
        st.dataframe(tabla.round(3), hide_index=True, width="stretch")

    resumen = []
    if "J0" in aj:
        resumen.append(f"J0={aj['J0']:.2f}; Kc={aj['Kc']:.3e}; R2_J={aj['R2_J']:.3f}")
    if "K" in aj:
        resumen.append(f"K={aj['K']:.5f}; C0={aj['C0']:.2f}; R2_C={aj['R2_C']:.3f}")
    if d["R"].notna().any():
        resumen.append(f"Rechazo={d['R'].mean():.1f}%")
    from modelo_actualizado import resumen_para_guardar
    alertas = alertas_graves(d)
    datos_json, alertas_txt = resumen_para_guardar(d, aj, alertas)
    if alertas:
        st.caption("ℹ️ Por las alertas marcadas en rojo, esta práctica se registrará pero no se "
                   "usará para actualizar el modelo del gemelo digital.")
    else:
        st.caption("🧠 Si el profesor aprueba esta práctica, sus datos ayudarán a actualizar el "
                   "modelo del gemelo digital.")
    return {"vuelta": info["vuelta"], "resumen": " | ".join(resumen),
            "temperatura": info["temperatura"], "datos": datos_json, "alertas": alertas_txt}
