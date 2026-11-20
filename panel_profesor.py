# panel_profesor.py
# Página "📊 Panel del profesor": análisis del curso con los datos que la app ya guarda
# en Google Sheets (registros, practicas, evaluaciones, pre_post).
#
# Acceso con la contraseña de profesores ([profesores] password en los Secrets). Si no
# está configurada, se acepta la de administrador ([admin] password).

import io
import json
import re

import numpy as np
import pandas as pd
import streamlit as st

NOTA_APROBATORIA = 3.0


# =============================================================================
# ACCESO
# =============================================================================

def _autenticar():
    if st.session_state.get("autenticado_profesor"):
        return True
    st.info("Esta página es solo para los profesores del laboratorio.")
    clave = st.text_input("Contraseña de profesores", type="password", key="clave_panel_prof")
    if st.button("Ingresar", key="btn_panel_prof"):
        validas = []
        for seccion in ("profesores", "admin"):
            try:
                validas.append(st.secrets[seccion]["password"])
            except Exception:
                pass
        if not validas:
            st.error("No hay contraseña configurada. Agrega una sección [profesores] con "
                     "'password' en los Secrets de Streamlit.")
        elif clave in validas:
            st.session_state.autenticado_profesor = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    return False


# =============================================================================
# UTILIDADES
# =============================================================================

def _leer(nombre, funcion):
    try:
        df = funcion()
        return (df if df is not None else pd.DataFrame()), None
    except Exception as e:
        return pd.DataFrame(), f"{nombre}: {e}"


def _fechas(df, col="fecha"):
    if df.empty or col not in df:
        return pd.Series(dtype="datetime64[ns]")
    return pd.to_datetime(df[col].astype(str).str.strip().str.lstrip("'"), errors="coerce")


def _filtrar_fecha(df, desde, hasta):
    if df.empty or "fecha" not in df:
        return df
    f = _fechas(df)
    return df[(f.dt.date >= desde) & (f.dt.date <= hasta) | f.isna()]


def _num(serie):
    return pd.to_numeric(serie, errors="coerce")


def _parse_temas(texto):
    """'Conceptos:2/2; Modelos:1/2' → {'Conceptos': (2, 2), 'Modelos': (1, 2)}"""
    salida = {}
    for parte in str(texto).split(";"):
        m = re.match(r"\s*([^:]+):\s*(\d+)\s*/\s*(\d+)", parte)
        if m:
            salida[m.group(1).strip()] = (int(m.group(2)), int(m.group(3)))
    return salida


def _alerta_base(texto):
    """'rechazo bajo (82 %)' → 'rechazo bajo'"""
    return re.sub(r"\s*\(.*?\)", "", texto).strip().capitalize()


def _banda_modelo(t, n=600, semilla=7):
    """Banda 5–95 % del flux de la vuelta 2 (Hermia n=0 con la incertidumbre de las réplicas)."""
    import simulacion_presion as sp
    rng = np.random.default_rng(semilla)
    pars = rng.multivariate_normal(sp.HERMIA_MEDIA, sp.HERMIA_COV, size=n)
    J0 = np.clip(pars[:, 0], 10, 35)[:, None]
    Kc = np.clip(pars[:, 1], 2e-5, None)[:, None]
    corr = np.clip(rng.normal(1, sp.CV_CORRIDAS, n), 0.5, 1.5)[:, None]
    J = (1 / J0 ** 2 + 2 * Kc * t[None, :]) ** -0.5 * corr
    return np.percentile(J, 5, axis=0), np.percentile(J, 50, axis=0), np.percentile(J, 95, axis=0)


def _tabla_practicas(df):
    filas = []
    for _, f in df.iterrows():
        try:
            d = json.loads(f.get("datos", ""))
        except Exception:
            d = {}
        try:
            vuelta = int(float(f.get("vuelta", "")))
        except Exception:
            vuelta = None
        filas.append({"Fecha": str(f.get("fecha", "")).lstrip("'"), "Grupo": f.get("nombre", ""),
                      "Vuelta": vuelta, "T (°C)": _num(pd.Series([f.get("temperatura")])).iloc[0],
                      "J0": d.get("J0"), "Kc": d.get("Kc"), "K": d.get("K"), "C0": d.get("C0"),
                      "Alertas": f.get("alertas", ""), "Estado": f.get("estado", ""),
                      "_t": d.get("t", []), "_J": d.get("J", [])})
    return pd.DataFrame(filas)


# =============================================================================
# SECCIONES
# =============================================================================

def _seccion_practicas(tp, reg):
    import matplotlib.pyplot as plt

    if tp.empty:
        st.write("Todavía no hay prácticas con datos para analizar.")
        return pd.DataFrame()

    # ---- flux de cada grupo frente al modelo (vuelta 2)
    st.markdown("##### Flux de cada grupo frente al modelo (vuelta 2)")
    t = np.linspace(0, 40, 81)
    lo, me, hi = _banda_modelo(t)
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.fill_between(t, lo, hi, color="#1f4e78", alpha=0.15, label="Modelo (banda 5–95 %)")
    ax.plot(t, me, color="#1f4e78", lw=2, label="Modelo (mediana)")
    dentro = []
    paleta = plt.cm.tab10.colors
    k = 0
    for i, r in tp.iterrows():
        tt = np.array([x if x is not None else np.nan for x in r["_t"]], dtype=float)
        JJ = np.array([x if x is not None else np.nan for x in r["_J"]], dtype=float)
        ok = np.isfinite(tt) & np.isfinite(JJ) & (tt > 0)
        if r["Vuelta"] != 2 or ok.sum() == 0:
            dentro.append(None)
            continue
        lo_i, hi_i = np.interp(tt[ok], t, lo), np.interp(tt[ok], t, hi)
        frac = float(np.mean((JJ[ok] >= lo_i) & (JJ[ok] <= hi_i)))
        dentro.append(frac)
        ax.plot(tt[ok], JJ[ok], "o-", color=paleta[k % 10], ms=4, lw=1.2,
                label=f"{r['Grupo']} ({r['Fecha'][:10]})")
        k += 1
    ax.set_xlabel("Tiempo (min)")
    ax.set_ylabel("Flux J (L/m²·h)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7.5, loc="upper right", ncol=2)
    fig.tight_layout()
    if k:
        st.pyplot(fig)
    else:
        st.caption("Aún no hay prácticas de la vuelta 2 con datos de flux para comparar.")
    plt.close(fig)
    tp = tp.copy()
    tp["Dentro de la banda"] = [("—" if d is None else ("✅ sí" if d >= 0.5 else "⚠️ no"))
                                for d in dentro]
    fuera = tp[tp["Dentro de la banda"] == "⚠️ no"]
    if not fuera.empty:
        st.warning("Prácticas de la vuelta 2 con la mayoría de puntos fuera de la banda del modelo "
                   "(revisar medición o condiciones): " +
                   ", ".join(f"{g} ({f[:10]})" for g, f in zip(fuera["Grupo"], fuera["Fecha"])))

    vista = tp.drop(columns=["_t", "_J"]).round({"T (°C)": 1, "J0": 2, "C0": 2})
    vista["Kc"] = vista["Kc"].map(lambda x: f"{x:.2e}" if isinstance(x, (int, float)) and np.isfinite(x) else "")
    vista["K"] = vista["K"].map(lambda x: f"{x:.5f}" if isinstance(x, (int, float)) and np.isfinite(x) else "")
    st.dataframe(vista, hide_index=True, width="stretch")

    c1, c2 = st.columns(2)
    # ---- alertas más comunes
    with c1:
        st.markdown("##### Alertas más comunes")
        todas = []
        for a in tp["Alertas"].astype(str):
            if a.strip().lower() in ("", "nan", "ninguna"):
                continue
            todas += [_alerta_base(x) for x in a.split(";") if x.strip()]
        if todas:
            cuenta = pd.Series(todas).value_counts()
            fig, ax = plt.subplots(figsize=(4.6, 0.5 + 0.45 * len(cuenta)))
            ax.barh(cuenta.index[::-1], cuenta.values[::-1], color="#e76f51")
            ax.set_xlabel("Número de prácticas")
            ax.grid(alpha=0.3, axis="x")
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.success("Ninguna práctica ha tenido alertas graves.")
        sin = int((tp["Alertas"].astype(str).str.strip().str.lower().isin(["", "nan", "ninguna"])).sum())
        st.caption(f"{sin} de {len(tp)} prácticas sin alertas.")
    # ---- prácticas por vuelta
    with c2:
        st.markdown("##### Prácticas por vuelta de la V9")
        pv = tp.dropna(subset=["Vuelta"]).groupby(["Vuelta", "Estado"]).size().unstack(fill_value=0)
        if not pv.empty:
            fig, ax = plt.subplots(figsize=(4.6, 3))
            colores = {"Aprobado": "#2a9d8f", "Pendiente": "#e9c46a", "Rechazado": "#e76f51",
                       "Excluida": "#b0b7c3"}
            abajo = np.zeros(len(pv))
            for est in pv.columns:
                ax.bar(pv.index.astype(int).astype(str), pv[est], bottom=abajo,
                       color=colores.get(est, "#888"), label=est)
                abajo += pv[est].values
            ax.set_xlabel("Vuelta")
            ax.set_ylabel("Prácticas")
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3, axis="y")
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
            otras = [int(v) for v in pv.index if int(v) != 2]
            st.caption("Prácticas en otras vueltas calibran la válvula roja del simulador." +
                       ("" if otras else " Aún no hay ninguna: programar alguna en la vuelta 4 o 6 "
                                         "ayudaría a validar las estimaciones."))
    return tp


def _seccion_evaluacion(ev):
    import matplotlib.pyplot as plt

    if ev.empty:
        st.write("Todavía no hay evaluaciones finales registradas.")
        return
    notas = _num(ev["nota"]).dropna()
    c1, c2, c3 = st.columns(3)
    c1.metric("Evaluaciones", len(ev))
    c2.metric("Nota promedio", f"{notas.mean():.2f}" if len(notas) else "—")
    c3.metric("Aprobados", f"{100 * (notas >= NOTA_APROBATORIA).mean():.0f} %" if len(notas) else "—")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Distribución de notas")
        fig, ax = plt.subplots(figsize=(4.6, 3))
        ax.hist(notas, bins=np.arange(0, 5.51, 0.5), color="#2a9d8f", edgecolor="white")
        ax.axvline(NOTA_APROBATORIA, color="#e76f51", lw=2, label=f"Aprueba ({NOTA_APROBATORIA})")
        ax.set_xlabel("Nota")
        ax.set_ylabel("Estudiantes")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3, axis="y")
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
    with col2:
        st.markdown("##### Aciertos por tema")
        acum = {}
        if "temas" in ev:
            for txt in ev["temas"].dropna():
                for tema, (a, n) in _parse_temas(txt).items():
                    s = acum.setdefault(tema, [0, 0])
                    s[0] += a
                    s[1] += n
        if acum:
            temas = sorted(acum, key=lambda k: acum[k][0] / acum[k][1])
            pct = [100 * acum[k][0] / acum[k][1] for k in temas]
            fig, ax = plt.subplots(figsize=(4.6, 3))
            ax.barh(temas, pct, color=["#e76f51" if p < 60 else "#2a9d8f" for p in pct])
            ax.set_xlim(0, 100)
            ax.set_xlabel("Aciertos (%)")
            ax.grid(alpha=0.3, axis="x")
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
            flojos = [k for k, p in zip(temas, pct) if p < 60]
            if flojos:
                st.caption("Temas con menos del 60 % de aciertos: " + ", ".join(flojos) +
                           ". Conviene reforzarlos en clase.")
        else:
            st.caption("El detalle por tema se guarda desde esta versión: aparecerá con las "
                       "próximas evaluaciones (requiere el Apps Script actualizado).")

    codigo = st.text_input("Verificar un código de constancia", key="panel_codigo").strip().upper()
    if codigo:
        hallado = ev[ev["codigo"].astype(str).str.upper().str.strip("'") == codigo]
        if hallado.empty:
            st.error("Ese código no aparece en el registro.")
        else:
            st.success("Código válido ✅")
            st.dataframe(hallado, hide_index=True, width="stretch")
    with st.expander("Ver todas las evaluaciones"):
        st.dataframe(ev.sort_values("fecha", ascending=False), hide_index=True, width="stretch")


def _excel(hojas):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for nombre, df in hojas.items():
            (df if not df.empty else pd.DataFrame({"(sin datos)": []})).to_excel(
                w, sheet_name=nombre[:31], index=False)
    return buf.getvalue()


# =============================================================================
# PÁGINA
# =============================================================================

def pagina_panel(cargar_registros, cargar_practicas, cargar_evaluaciones, cargar_prepost):
    st.write("# 📊 Panel del profesor")
    if not _autenticar():
        return
    if st.button("Cerrar sesión", key="btn_panel_salir"):
        st.session_state.autenticado_profesor = False
        st.rerun()

    errores = []
    reg, e1 = _leer("registros", cargar_registros)
    pra, e2 = _leer("practicas", cargar_practicas)
    ev, e3 = _leer("evaluaciones", cargar_evaluaciones)
    pp, e4 = _leer("pre_post", cargar_prepost)
    errores = [e for e in (e1, e2, e3, e4) if e]
    if errores:
        st.warning("Algunas pestañas del Google Sheet no se pudieron leer (si son nuevas, actualiza "
                   "el Apps Script y publícalo como 'Nueva versión'):\n\n- " + "\n- ".join(errores))

    # ---- filtros
    todas = pd.concat([_fechas(d) for d in (reg, pra, ev, pp) if not d.empty] or
                      [pd.Series(dtype="datetime64[ns]")]).dropna()
    hoy = pd.Timestamp.today().date()
    f_min = todas.min().date() if len(todas) else hoy
    f_max = max(todas.max().date(), hoy) if len(todas) else hoy
    c1, c2 = st.columns([2, 2])
    rango = c1.date_input("Periodo", value=(f_min, f_max), min_value=f_min, max_value=f_max,
                          key="panel_rango", format="DD/MM/YYYY")
    desde, hasta = (rango if isinstance(rango, (list, tuple)) and len(rango) == 2 else (f_min, f_max))
    grupos = sorted({str(g).strip() for d in (ev, pp) if not d.empty and "grupo" in d
                     for g in d["grupo"] if str(g).strip() and str(g) != "nan"})
    sel = c2.multiselect("Grupos (evaluación y tests)", grupos, key="panel_grupos",
                         placeholder="Todos")
    reg, pra, ev, pp = (_filtrar_fecha(d, desde, hasta) for d in (reg, pra, ev, pp))
    if sel:
        ev = ev[ev["grupo"].astype(str).str.strip().isin(sel)] if not ev.empty else ev
        pp = pp[pp["grupo"].astype(str).str.strip().isin(sel)] if not pp.empty else pp

    # ---- tarjetas
    from modelo_actualizado import practicas_validas
    from test_pre_post import emparejar
    est = reg["estado"].astype(str).value_counts() if not reg.empty else pd.Series(dtype=int)
    notas = _num(ev["nota"]).dropna() if not ev.empty else pd.Series(dtype=float)
    pares = emparejar(pp).dropna(subset=["Entrada (%)", "Salida (%)"]) if not pp.empty else pd.DataFrame()
    g = np.nan
    if not pares.empty and pares["Entrada (%)"].mean() < 100:
        g = ((pares["Salida (%)"].mean() - pares["Entrada (%)"].mean()) /
             (100 - pares["Entrada (%)"].mean()))
    n_modelo = len(practicas_validas(pra)) if not pra.empty else 0
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Prácticas subidas", len(reg),
              help=f"Aprobadas {est.get('Aprobado', 0)} · Pendientes {est.get('Pendiente', 0)} · "
                   f"Rechazadas {est.get('Rechazado', 0)}")
    k1.caption(f"✅ {est.get('Aprobado', 0)} · ⏳ {est.get('Pendiente', 0)} · ❌ {est.get('Rechazado', 0)}")
    k2.metric("Evaluación final", f"{notas.mean():.2f}" if len(notas) else "—",
              help="Nota promedio (0–5)")
    k2.caption(f"{len(notas)} estudiante(s) · "
               f"{(100 * (notas >= NOTA_APROBATORIA).mean()):.0f} % aprueba" if len(notas) else "sin datos")
    k3.metric("Ganancia entrada → salida", "—" if np.isnan(g) else f"{g:.2f}",
              help="Ganancia normalizada de Hake: <0.3 baja · 0.3–0.7 media · >0.7 alta")
    k3.caption(f"{len(pares)} estudiante(s) con ambos tests")
    k4.metric("Prácticas en el modelo", n_modelo,
              help="Aprobadas y sin alertas graves: actualizan el simulador.")
    k4.caption("de " + str(len(pra)) + " con datos")

    t1, t2, t3, t4 = st.tabs(["🧪 Prácticas de laboratorio", "📋 Test de entrada y salida",
                              "📝 Evaluación final", "📥 Descargar"])
    with t1:
        tp = _seccion_practicas(_tabla_practicas(pra) if not pra.empty else pd.DataFrame(), reg)
    with t2:
        from test_pre_post import panel_profesor as panel_prepost
        panel_prepost(lambda: pp)
    with t3:
        _seccion_evaluacion(ev)
    with t4:
        st.markdown("Descarga todo lo del periodo y grupos seleccionados en un solo Excel "
                    "(una hoja por tipo de dato).")
        tp_x = tp.drop(columns=[c for c in ("_t", "_J") if c in tp]) if isinstance(tp, pd.DataFrame) else pd.DataFrame()
        pp_x = emparejar(pp).drop(columns=["_resp_pre", "_resp_post"], errors="ignore") if not pp.empty else pd.DataFrame()
        resumen = pd.DataFrame({
            "Indicador": ["Periodo", "Prácticas subidas", "Aprobadas", "Pendientes", "Rechazadas",
                          "Prácticas en el modelo", "Evaluaciones", "Nota promedio", "% aprobados",
                          "Estudiantes con test entrada y salida", "Ganancia normalizada g"],
            "Valor": [f"{desde} a {hasta}", len(reg), est.get("Aprobado", 0), est.get("Pendiente", 0),
                      est.get("Rechazado", 0), n_modelo, len(notas),
                      round(notas.mean(), 2) if len(notas) else "",
                      round(100 * (notas >= NOTA_APROBATORIA).mean(), 1) if len(notas) else "",
                      len(pares), "" if np.isnan(g) else round(g, 2)]})
        st.download_button("📥 Descargar Excel del curso",
                           data=_excel({"Resumen": resumen, "Registros": reg, "Practicas": tp_x,
                                        "Evaluaciones": ev, "Entrada_salida": pp_x}),
                           file_name=f"panel_gemelo_uf_{desde}_{hasta}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           type="primary")
