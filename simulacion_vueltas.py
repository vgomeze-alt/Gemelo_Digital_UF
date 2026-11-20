# simulacion_vueltas.py
# Modo "Montecarlo por vueltas de la válvula roja (V9)".
#
# Solo usa los datos con lactosuero de la vuelta 2 (3 réplicas). No usa la
# caracterización con agua (Tabla 10) ni los ensayos de las vueltas 4 y 6.
#
# CADENA DEL MODELO
#   vuelta  →  apertura de la válvula  →  presión en el módulo  →  flux y concentración
#
# S1. La válvula roja está en la línea de RECHAZO, después de la membrana: al
#     abrirla (más vueltas) sale el rechazo con menos restricción y baja la
#     presión dentro del módulo; al cerrarla, la presión sube.
# S2. Característica de la válvula: Cv(v) = Cv_max·[r + (1 − r)·(v/9)^n]
#       r = Cv_min/Cv_max (fuga con la válvula cerrada), n = forma de la curva.
#       Ambos son inciertos → Montecarlo.
# S3. El caudal de rechazo es casi constante (la bomba da ~6 L/min y el permeado
#     es una fracción pequeña), así que la caída en la válvula escala como
#     ΔP ∝ (Q/Cv)²  →  ΔP(v) = ΔP_vuelta2 · [Cv(2)/Cv(v)]².
# S4. La presión no puede superar la que alcanza la bomba con la salida casi
#     cerrada (presión de cierre), incierta entre 3 y 5 bar.
# S5. Con la presión de cada vuelta, el flux sale del mismo modelo de Darcy con
#     torta compresible del modo "Presión y Montecarlo" (calibrado en la vuelta 2).
#
# El Montecarlo combina la incertidumbre del modelo (réplicas: J0, Kc, K,
# variación entre corridas, compresibilidad) con la de la válvula (r, n,
# presión de cierre). La vuelta 2 queda anclada a los datos; las demás son
# ESTIMACIONES cuya banda crece al alejarse de la vuelta 2.

import numpy as np
import pandas as pd
import streamlit as st

import simulacion_presion as sp

VUELTAS = np.arange(0, 10)
Q_ALIM = 6.0  # L/min, caudal de alimentación de la práctica (rotámetro)
# S6. El permeado no puede superar el caudal que entrega la bomba: se limita al
#     90 % de la alimentación (J_máx = 0.9·6 L/min·60 / 4.8 m² ≈ 67 L/m²·h).
J_CAP = 0.9 * Q_ALIM * 60 / 4.8


@st.cache_data(show_spinner=False)
def correr_vueltas(J_agua, C0, t_final, T, n_mc, semilla, n_med, r_med, p_cierre_med, s_med):
    rng = np.random.default_rng(semilla)
    R_M = sp.DP_REF / (sp.MU_AGUA_REF * sp._a_si(J_agua))
    t = np.linspace(0, t_final, 81)

    # ---- incertidumbre del modelo (vuelta 2)
    pars = rng.multivariate_normal(sp.HERMIA_MEDIA, sp.HERMIA_COV, size=n_mc)
    J0 = np.clip(pars[:, 0], 10, 35)[:, None]
    Kc = np.clip(pars[:, 1], 2e-5, None)[:, None]
    K = np.clip(rng.normal(sp.K_MEDIA, sp.K_SD, n_mc), 1e-4, None)[:, None]
    corrida = np.clip(rng.normal(1.0, sp.CV_CORRIDAS, n_mc), 0.5, 1.5)[:, None]
    s = np.clip(rng.normal(s_med, 0.1, n_mc), 0.0, 1.0)[:, None]
    T_mc = rng.normal(T, 1.0, n_mc)[:, None]

    # ---- incertidumbre de la válvula
    n = np.clip(rng.normal(n_med, 0.25, n_mc), 0.4, 2.5)[:, None]
    r = np.clip(rng.lognormal(np.log(r_med), 0.35, n_mc), 0.02, 0.4)[:, None]
    p_cierre = rng.uniform(p_cierre_med - 1.0, p_cierre_med + 1.0, n_mc)[:, None] * sp.BAR_A_PA

    def cv(v):
        return r + (1 - r) * (v / 9.0) ** n

    dP = sp.DP_REF * (cv(2.0) / cv(VUELTAS[None, :].astype(float))) ** 2      # (N, 10)
    dP = np.minimum(dP, p_cierre)
    dP[:, 2] = sp.DP_REF * (1 + rng.normal(0, 0.05, n_mc))                   # anclada a 11 psi

    J = np.empty((n_mc, len(VUELTAS), len(t)))
    C = np.empty_like(J)
    for k, v in enumerate(VUELTAS):
        Jk, Jref = sp._flux(t[None, :], dP[:, k:k + 1], T_mc, 1.0, s, J0, Kc, R_M)
        Jk = np.minimum(Jk * corrida, J_CAP)
        tau = np.concatenate((np.zeros((n_mc, 1)),
                              np.cumsum((Jk / (Jref * corrida))[:, 1:] * np.diff(t), axis=1)), axis=1)
        den = 1.0 / C0 - K * tau
        C[:, k, :] = np.where(den > 0, 1.0 / np.where(den > 0, den, 1.0), np.nan)
        J[:, k, :] = Jk
    Vp = np.concatenate((np.zeros(J.shape[:2] + (1,)),
                         np.cumsum((J[..., 1:] + J[..., :-1]) / 2 * 4.8 * np.diff(t) / 60, axis=-1)),
                        axis=-1)
    frac_perm = J * 4.8 / 60 / Q_ALIM * 100                                  # % del caudal
    return dict(t=t, dP=dP, J=J, C=C, Vp=Vp, frac=frac_perm)


def _pct(x, q, axis=0):
    return np.nanpercentile(x, q, axis=axis)


def pagina_vueltas(PARAMS):
    import matplotlib.pyplot as plt

    st.markdown(
        "¿Qué pasaría si giras la **válvula roja trasera** a otra vuelta? Esta simulación parte "
        "**solo de los datos con lactosuero de la vuelta 2** (3 réplicas) y estima las demás "
        "vueltas con un modelo físico de la válvula y cientos de simulaciones (Montecarlo)."
    )
    st.warning(
        "🧪 **Solo la vuelta 2 tiene datos experimentales.** Las demás vueltas son "
        "**estimaciones** basadas en supuestos físicos (ver abajo): sirven para entender "
        "tendencias y riesgos, no como datos validados. La banda de incertidumbre crece al "
        "alejarse de la vuelta 2."
    )

    col_in, col_out = st.columns([1, 2.2])
    with col_in:
        st.subheader("Condiciones")
        vuelta_sel = st.slider("Vuelta a explorar en detalle", 0, 9, 4)
        C0 = st.number_input("Concentración inicial C₀ (g/L)", 1.0, 30.0, float(PARAMS["C0_valido"]), 0.1)
        t_final = st.slider("Tiempo de proceso (min)", 10, 60, 40, 5)
        T = st.slider("Temperatura (°C)", 10.0, 40.0, 20.0, 0.5)
        n_mc = st.select_slider("Número de simulaciones", [200, 300, 500, 1000], 300)
        with st.expander("Supuestos de la válvula (avanzado)"):
            n_med = st.slider("Forma de la curva de la válvula, n", 0.5, 2.0, 1.0, 0.1,
                              help="n < 1: abre rápido al principio · n = 1: lineal · "
                                   "n > 1: abre lento al principio (igual porcentaje).")
            r_med = st.slider("Paso con la válvula cerrada, Cv_min/Cv_max", 0.03, 0.30, 0.10, 0.01,
                              help="Qué tanto deja pasar la válvula en la vuelta 0.")
            p_cierre = st.slider("Presión de cierre de la bomba (bar)", 2.5, 6.0, 4.0, 0.25,
                                 help="Presión máxima que alcanza la bomba con la salida casi cerrada.")
            s_med = st.slider("Compresibilidad de la torta, s", 0.0, 1.0, 0.7, 0.05)
            semilla = st.number_input("Semilla aleatoria", 0, 99999, 2026, 1)
        simular = st.button("Simular todas las vueltas 🎲", type="primary", width="stretch")

    if not simular and "sim_vueltas" not in st.session_state:
        with col_out:
            st.info("Ajusta las condiciones y presiona **Simular todas las vueltas 🎲**.")
        _explicacion()
        return
    entradas = (float(PARAMS["J_agua"]), C0, t_final, T, n_mc, int(semilla),
                n_med, r_med, p_cierre, s_med)
    if simular:
        st.session_state.sim_vueltas = entradas
    entradas = st.session_state.sim_vueltas
    r = correr_vueltas(*entradas)
    t, J, C, dP, frac, Vp = r["t"], r["J"], r["C"], r["dP"], r["frac"], r["Vp"]
    pmax = sp.P_MAX_FICHA_BAR

    dP_bar = dP / sp.BAR_A_PA
    Jf = J[:, :, -1]
    Cf = C[:, :, -1]
    prob_sobre = (dP_bar > pmax).mean(axis=0)

    with col_out:
        st.subheader("Resultados por vuelta")
        peligrosas = [int(v) for v in VUELTAS if prob_sobre[v] > 0.05]
        vacias = [int(v) for v in VUELTAS if (Vp[:, v, -1] > sp.V_TANQUE).mean() > 0.5]
        if vacias:
            st.warning(f"⚠️ En las vueltas {', '.join(map(str, vacias))} saldría más permeado que los "
                       f"{sp.V_TANQUE:.0f} L del tanque antes de los {entradas[2]} min: el tanque se vaciaría "
                       "y la concentración calculada deja de ser real.")
        if peligrosas:
            st.error(f"🚫 **Riesgo de superar la presión máxima de la membrana ({pmax:.0f} bar)** en las "
                     f"vueltas {', '.join(map(str, peligrosas))}: con la válvula muy cerrada la presión "
                     "del módulo sube hacia la presión de cierre de la bomba. No se recomienda operar ahí.")
        p50 = _pct(Jf, 50)
        mejor = int(np.nanargmax(np.where(prob_sobre <= 0.05, p50, -np.inf)))
        st.success(f"✅ Dentro del límite de presión, el mayor flux estimado está en la **vuelta {mejor}** "
                   f"(~{p50[mejor]:.1f} L/m²·h a {entradas[2]} min). La vuelta 2 (datos) da "
                   f"~{p50[2]:.1f} L/m²·h.")

        colores = ["#2e7d32" if v == 2 else "#e08a00" for v in VUELTAS]

        fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
        ax = axs[0]
        lo, me, hi = _pct(dP_bar, 5), _pct(dP_bar, 50), _pct(dP_bar, 95)
        ax.fill_between(VUELTAS, lo, hi, color="#1f4e78", alpha=0.18)
        ax.plot(VUELTAS, me, color="#1f4e78", lw=2)
        ax.scatter(VUELTAS, me, c=colores, zorder=5, s=45)
        ax.axhline(pmax, color="red", lw=1.5); ax.text(9, pmax, " máx.", color="red", va="bottom", ha="right", fontsize=8)
        ax.set_xlabel("Vuelta de la válvula roja"); ax.set_ylabel("Presión en el módulo (bar)")
        ax.set_title("¿Qué presión genera cada vuelta?"); ax.set_xticks(VUELTAS); ax.grid(alpha=0.3)
        ax = axs[1]
        lo, me, hi = _pct(Jf, 5), _pct(Jf, 50), _pct(Jf, 95)
        ax.fill_between(VUELTAS, lo, hi, color="#c00000", alpha=0.18)
        ax.plot(VUELTAS, me, color="#c00000", lw=2)
        ax.scatter(VUELTAS, me, c=colores, zorder=5, s=45)
        ax.set_xlabel("Vuelta de la válvula roja"); ax.set_ylabel(f"Flux a {entradas[2]} min (L/m² h)")
        ax.set_title("Flux final según la vuelta"); ax.set_xticks(VUELTAS); ax.grid(alpha=0.3)
        fig.tight_layout(); st.pyplot(fig); plt.close(fig)
        st.caption("🟢 vuelta 2: datos experimentales · 🟠 demás vueltas: estimaciones. "
                   "Bandas: 90 % de las simulaciones.")

        fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
        ax = axs[0]
        f0 = frac[:, :, 1]
        ax.fill_between(VUELTAS, _pct(f0, 5), _pct(f0, 95), color="#2e86ab", alpha=0.18)
        ax.plot(VUELTAS, _pct(f0, 50), color="#2e86ab", lw=2, label="Al inicio")
        ax.plot(VUELTAS, _pct(frac[:, :, -1], 50), color="#2e86ab", lw=2, ls="--", label=f"A los {entradas[2]} min")
        ax.scatter(VUELTAS, _pct(f0, 50), c=colores, zorder=5, s=45)
        ax.set_xlabel("Vuelta de la válvula roja"); ax.set_ylabel("% del caudal que sale como permeado")
        ax.set_title("Relación permeado/rechazo simulada"); ax.set_xticks(VUELTAS); ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
        ax = axs[1]
        ok = np.isfinite(Cf).mean(axis=0) > 0.5
        ax.fill_between(VUELTAS[ok], _pct(Cf[:, ok], 5), _pct(Cf[:, ok], 95), color="#082e52", alpha=0.18)
        ax.plot(VUELTAS[ok], _pct(Cf[:, ok], 50), color="#082e52", lw=2)
        ax.scatter(VUELTAS[ok], _pct(Cf[:, ok], 50), c=[colores[i] for i in np.where(ok)[0]], zorder=5, s=45)
        ax.axhline(C0, color="gray", ls=":", lw=1)
        ax.set_xlabel("Vuelta de la válvula roja"); ax.set_ylabel(f"C tanque a {entradas[2]} min (g/L)")
        ax.set_title("¿Cuánto se concentra la proteína?"); ax.set_xticks(VUELTAS); ax.grid(alpha=0.3)
        fig.tight_layout(); st.pyplot(fig); plt.close(fig)

        # ---- detalle de la vuelta elegida frente a la vuelta 2
        v = vuelta_sel
        st.markdown(f"#### Vuelta {v} frente a la vuelta 2 (datos)")
        c1, c2, c3 = st.columns(3)
        c1.metric("Presión estimada (bar)", f"{_pct(dP_bar[:, v], 50):.2f}",
                  f"{_pct(dP_bar[:, v], 50) - _pct(dP_bar[:, 2], 50):+.2f} vs. vuelta 2")
        c2.metric(f"Flux a {entradas[2]} min (L/m²·h)", f"{_pct(Jf[:, v], 50):.1f}",
                  f"{(_pct(Jf[:, v], 50) / _pct(Jf[:, 2], 50) - 1):+.0%}")
        c2.caption(f"90 %: {_pct(Jf[:, v], 5):.1f} – {_pct(Jf[:, v], 95):.1f}")
        c3.metric("Permeado al inicio (% del caudal)", f"{_pct(frac[:, v, 1], 50):.0f} %")
        if prob_sobre[v] > 0.05:
            st.error(f"En el {prob_sobre[v]:.0%} de las simulaciones la vuelta {v} supera los {pmax:.0f} bar.")

        fig, ax = plt.subplots(figsize=(10, 3.4))
        for k, col, nom in ((2, "#2e7d32", "Vuelta 2 (datos)"), (v, "#e08a00", f"Vuelta {v} (estimada)")):
            ax.fill_between(t, _pct(J[:, k, :], 5), _pct(J[:, k, :], 95), color=col, alpha=0.15)
            ax.plot(t, _pct(J[:, k, :], 50), color=col, lw=2, label=nom)
        ax.set_xlabel("Tiempo (min)"); ax.set_ylabel("J (L/m² h)"); ax.grid(alpha=0.3); ax.legend(fontsize=9)
        ax.set_title("Flux en el tiempo")
        fig.tight_layout(); st.pyplot(fig); plt.close(fig)

        tabla = pd.DataFrame({
            "Vuelta": VUELTAS,
            "Origen": ["Datos (3 réplicas)" if x == 2 else "Estimada" for x in VUELTAS],
            "Presión (bar)": _pct(dP_bar, 50).round(2),
            f"Flux {entradas[2]} min (L/m²·h)": _pct(Jf, 50).round(1),
            "Flux P5–P95": [f"{a:.1f}–{b:.1f}" for a, b in zip(_pct(Jf, 5), _pct(Jf, 95))],
            "% permeado (inicio)": _pct(frac[:, :, 1], 50).round(0),
            f"C {entradas[2]} min (g/L)": _pct(Cf, 50).round(2),
            "P(supera presión máx.)": [f"{x:.0%}" for x in prob_sobre],
        })
        st.dataframe(tabla, hide_index=True, width="stretch")
        st.download_button("📥 Descargar tabla (CSV)", tabla.to_csv(index=False).encode("utf-8"),
                           file_name="montecarlo_vueltas.csv", mime="text/csv")
    _explicacion()


def _explicacion():
    with st.expander("📘 ¿Cómo se estiman las vueltas sin datos? Supuestos del modelo"):
        st.markdown(r"""
**Datos usados:** solo la operación con lactosuero de la **vuelta 2** (3 réplicas, 11 psi). No se
usan la caracterización con agua ni los ensayos de otras vueltas.

**Cadena del modelo:** vuelta → apertura de la válvula → presión en el módulo → flux y concentración.

1. **La válvula roja está en la línea de rechazo, después de la membrana.** Al abrirla (más vueltas)
   el rechazo sale con menos restricción y **baja la presión** del módulo; al cerrarla, sube.
2. **Curva de la válvula:** $C_v(v) = C_{v,máx}\,[\,r + (1-r)\,(v/9)^n\,]$, donde $r$ es lo que deja
   pasar cerrada y $n$ la forma de la curva. Ninguno se midió: el Montecarlo los varía.
3. **Caudal de rechazo casi constante** (la bomba da ~6 L/min y el permeado es una fracción pequeña),
   por lo que la caída de presión en la válvula escala como $\Delta P \propto (Q/C_v)^2$:
   $$\Delta P(v) = \Delta P_{vuelta\,2}\left[\frac{C_v(2)}{C_v(v)}\right]^2$$
4. **La presión no puede pasar de la presión de cierre de la bomba** (supuesta entre 3 y 5 bar), y el
   **permeado no puede superar el caudal que entrega la bomba** (se limita al 90 % de los 6 L/min).
5. Con la presión de cada vuelta, el **flux** sale del modelo de Darcy con torta compresible
   (calibrado en la vuelta 2), y la **concentración** del balance por lotes.

**Montecarlo:** en cada simulación se sortean $J_0$, $K_c$, $K$ (réplicas), la variación entre corridas,
la compresibilidad de la torta, la temperatura, y los parámetros de la válvula ($r$, $n$, presión de
cierre). La vuelta 2 queda anclada a 11 psi; por eso su banda es la más estrecha.

**Cómo validarlo:** una corrida corta (10–15 min) en 2 o 3 vueltas distintas, anotando la presión de
entrada y el peso de permeado, basta para calibrar la curva de la válvula y convertir estas
estimaciones en datos.
""")
