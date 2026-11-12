# simulacion_presion.py
# Modo "Presión y Montecarlo" de la pestaña Simulación.
#
# MODELO (Darcy + resistencias en serie, con torta compresible):
#
#   J(t, ΔP) = ΔP / { μ(T) · [ R_M·f_mem + R_f,ref(t) · (ΔP/ΔP_ref)^s ] }
#
#   - R_M: resistencia de la membrana limpia, calculada con el flux de agua
#     medido a la presión de referencia (R_M = ΔP_ref / (μ_agua · J_agua)).
#   - R_f,ref(t): resistencia de ensuciamiento a la presión de referencia,
#     obtenida del modelo de Hermia n=0 ajustado con R:28/72:
#         R_f,ref(t) = ΔP_ref / (μ_LD · J_Hermia(t)) − R_M
#     Así, a 11 psi, 20 °C y membrana limpia, el modelo reproduce EXACTAMENTE
#     la simulación base.
#   - s: compresibilidad de la torta (0 = incompresible → flux ∝ ΔP;
#     1 = totalmente compresible → el flux deja de crecer con la presión).
#     NO se midió: es un SUPUESTO de literatura para tortas de proteína.
#   - f_mem: factor de estado de la membrana (1 = limpia).
#   - μ(T): viscosidad del lactosuero corregida con la temperatura (misma
#     proporción que el agua, ecuación de Vogel).
#
#   Concentración: 1/C − 1/C0 = −K·τ, con τ(t) = ∫ J(t')/J_ref(t') dt'
#   ("tiempo equivalente"): si sale más permeado que en la referencia, la
#   proteína se concentra más rápido. A la presión de referencia τ = t.
#
# MONTECARLO: se repite la simulación N veces muestreando lo incierto:
#   - J0 y Kc: normal bivariada con la covarianza del ajuste de las 3 réplicas
#   - K: normal con la desviación entre réplicas
#   - s: alrededor del valor elegido (±0.1)
#   - ΔP real: ±5 % por fluctuaciones de bomba / lectura del manómetro
#   - T: ±1 °C;  R_M: ±5 % de variación entre membranas / estado

import numpy as np
import pandas as pd
import streamlit as st

PSI_A_PA = 6894.76
BAR_A_PA = 1.0e5

# --------------------------------------------------------------- DATOS BASE
DP_REF_PSI = 11.0                 # Hoja "Modelo": presión de entrada (manométrica)
DP_REF = DP_REF_PSI * PSI_A_PA    # Pa
MU_LD_REF = 0.00117               # Pa·s, lactosuero (Hoja "Modelo")
MU_AGUA_REF = 0.001               # Pa·s, agua (Hoja "Modelo")
T_REF = 20.0                      # °C, supuesto para las viscosidades de referencia
V_TANQUE = 80.0                   # L
P_MAX_PROVISIONAL_BAR = 2.0       # bar — PROVISIONAL: fichas técnicas de UF para agua
                                  # (rango típico 1–3 bar). Cambiar con la ficha real.

# Incertidumbre a partir de las 3 réplicas de R:28/72
HERMIA_MEDIA = np.array([19.0545, 1.33995e-4])            # J0 [L/m²h], Kc
HERMIA_COV = np.array([[3.57104788e+00, 2.79888831e-05],  # covarianza del ajuste
                       [2.79888831e-05, 3.03852765e-10]])
K_MEDIA, K_SD = 0.0012680, 1.29e-4                         # (g/L)^-1 min^-1

ESTADOS_MEMBRANA = {
    "Nueva / recién limpiada (R_M × 1.00)": 1.00,
    "Uso normal, limpieza incompleta (R_M × 1.15)": 1.15,
    "Envejecida o compactada (R_M × 1.40)": 1.40,
    "Más permeable que la de referencia (R_M × 0.80)": 0.80,
}


def _mu_agua(T):
    """Viscosidad del agua [Pa·s] (ecuación de Vogel), T en °C."""
    return 2.414e-5 * 10 ** (247.8 / (T + 273.15 - 140.0))


def _hermia(t, J0, Kc):
    return (1.0 / J0 ** 2 + 2.0 * Kc * t) ** -0.5


def _a_si(J):          # L/(m²·h) → m/s
    return J / 3.6e6


def _de_si(J):         # m/s → L/(m²·h)
    return J * 3.6e6


def _flux(t, dP, T, f_mem, s, J0, Kc, R_M):
    """Flux de lactosuero [L/m²h]. Admite arreglos (N,1) para Montecarlo."""
    J_ref = _hermia(t, J0, Kc)
    R_f_ref = np.maximum(DP_REF / (MU_LD_REF * _a_si(J_ref)) - R_M, 0.0)
    mu = MU_LD_REF * _mu_agua(T) / _mu_agua(T_REF)
    J = dP / (mu * (R_M * f_mem + R_f_ref * (dP / DP_REF) ** s))
    return _de_si(J), J_ref


@st.cache_data(show_spinner=False)
def correr(J_agua, dP_psi, T, f_mem, s, C0, t_final, n_mc, semilla, p_max_bar):
    """Corre la simulación determinista y el Montecarlo. Devuelve un dict."""
    R_M = DP_REF / (MU_AGUA_REF * _a_si(J_agua))
    dP = dP_psi * PSI_A_PA
    t = np.linspace(0, t_final, 121)
    A = 4.8

    # ---- caso nominal (sin incertidumbre) y caso de referencia (11 psi)
    J_nom, J_ref_nom = _flux(t, dP, T, f_mem, s, *HERMIA_MEDIA, R_M)
    J_ref11, _ = _flux(t, DP_REF, T_REF, 1.0, s, *HERMIA_MEDIA, R_M)

    def conc(J, J_ref, K):
        tau = np.concatenate((np.zeros(J.shape[:-1] + (1,)),
                              np.cumsum((J / J_ref)[..., 1:] * np.diff(t), axis=-1)), axis=-1)
        den = 1.0 / C0 - K * tau
        return np.where(den > 0, 1.0 / np.where(den > 0, den, 1.0), np.nan)

    def vol(J):
        return np.concatenate((np.zeros(J.shape[:-1] + (1,)),
                               np.cumsum((J[..., 1:] + J[..., :-1]) / 2 * A * np.diff(t) / 60, axis=-1)),
                              axis=-1)

    C_nom = conc(J_nom, J_ref_nom, K_MEDIA)
    V_nom = vol(J_nom)

    # ---- Montecarlo
    rng = np.random.default_rng(semilla)
    pars = rng.multivariate_normal(HERMIA_MEDIA, HERMIA_COV, size=n_mc)
    J0 = np.clip(pars[:, 0], 10, 35)[:, None]
    Kc = np.clip(pars[:, 1], 2e-5, None)[:, None]
    K = np.clip(rng.normal(K_MEDIA, K_SD, n_mc), 1e-4, None)[:, None]
    s_mc = np.clip(rng.normal(s, 0.1, n_mc), 0.0, 1.0)[:, None]
    dP_mc = (dP * (1 + rng.normal(0, 0.05, n_mc)))[:, None]
    T_mc = rng.normal(T, 1.0, n_mc)[:, None]
    f_mc = (f_mem * (1 + rng.normal(0, 0.05, n_mc)))[:, None]

    J_mc, J_ref_mc = _flux(t[None, :], dP_mc, T_mc, f_mc, s_mc, J0, Kc, R_M)
    C_mc = conc(J_mc, J_ref_mc, K)
    V_mc = vol(J_mc)

    # ---- curva flux vs presión al tiempo final (con y sin incertidumbre)
    p_hi = max(1.3 * p_max_bar * BAR_A_PA, 1.2 * dP, 1.5 * DP_REF)
    dP_grid = np.linspace(0.05 * BAR_A_PA, p_hi, 60)
    J_grid_mc, _ = _flux(t_final, dP_grid[None, :], T_mc, f_mc, s_mc, J0, Kc, R_M)
    J_grid_nom, _ = _flux(t_final, dP_grid, T, f_mem, s, *HERMIA_MEDIA, R_M)
    mu_w = _mu_agua(T)
    J_agua_grid = _de_si(dP_grid / (mu_w * R_M * f_mem))

    return dict(t=t, J_nom=J_nom, J_ref11=J_ref11, C_nom=C_nom, V_nom=V_nom,
                J_mc=J_mc, C_mc=C_mc, V_mc=V_mc, dP_mc=dP_mc.ravel(),
                dP_grid=dP_grid, J_grid_mc=J_grid_mc, J_grid_nom=J_grid_nom,
                J_agua_grid=J_agua_grid, R_M=R_M)


def _banda(ax, x, Y, color, etiqueta):
    p5, p50, p95 = np.nanpercentile(Y, [5, 50, 95], axis=0)
    ax.fill_between(x, p5, p95, color=color, alpha=0.18, label=f"{etiqueta}: banda 90 %")
    ax.plot(x, p50, color=color, lw=2, label=f"{etiqueta}: mediana")
    return p5, p50, p95


def pagina_presion(PARAMS):
    import matplotlib.pyplot as plt

    st.markdown(
        "Explora qué pasa si cambias la **presión transmembrana**, el **estado de la membrana** "
        "o la **temperatura**. Con el **Montecarlo**, la simulación se repite cientos de veces "
        "variando lo que es incierto, y en vez de una sola curva verás una **banda de "
        "resultados probables**."
    )
    st.warning(
        "🧪 **Modo exploratorio.** Los datos experimentales se tomaron a **una sola presión "
        f"({DP_REF_PSI:g} psi ≈ {DP_REF / BAR_A_PA:.2f} bar)**. El efecto de la presión se calcula "
        "con la ley de Darcy y una compresibilidad de la torta tomada de literatura: es una "
        "**extrapolación teórica**, útil para entender tendencias, no un dato validado."
    )

    col_in, col_out = st.columns([1, 2])
    with col_in:
        st.subheader("Condiciones de operación")
        dP_psi = st.slider("Presión transmembrana, ΔP (psi)", 2.0, 45.0, DP_REF_PSI, 0.5,
                           help=f"Referencia de los datos experimentales: {DP_REF_PSI:g} psi.")
        st.caption(f"= {dP_psi * PSI_A_PA / BAR_A_PA:.2f} bar")
        p_max_bar = st.number_input(
            "Presión máxima de la membrana (bar)", 0.5, 10.0, P_MAX_PROVISIONAL_BAR, 0.1,
            help="Valor PROVISIONAL tomado de fichas técnicas de membranas de UF para agua "
                 "(rango típico 1–3 bar). Cámbialo cuando tengas la ficha técnica del equipo.")
        st.caption(f"= {p_max_bar * BAR_A_PA / PSI_A_PA:.0f} psi · ⚠️ valor provisional, pendiente "
                   f"de confirmar con la ficha técnica")
        estado = st.selectbox("Estado de la membrana", list(ESTADOS_MEMBRANA),
                              help="Cambia la resistencia propia de la membrana, R_M.")
        f_mem = ESTADOS_MEMBRANA[estado]
        T = st.slider("Temperatura del lactosuero (°C)", 10.0, 40.0, T_REF, 0.5,
                      help="La temperatura cambia la viscosidad: más caliente → menos viscoso → más flux.")
        C0 = st.number_input("Concentración inicial de proteína, C₀ (g/L)", 1.0, 30.0,
                             float(PARAMS["C0_valido"]), 0.1)
        t_final = st.slider("Tiempo de proceso (min)", 10, 120, 40, 5)

        st.subheader("Montecarlo")
        n_mc = st.select_slider("Número de simulaciones", [100, 200, 300, 500, 1000], 300)
        with st.expander("Opciones avanzadas"):
            s = st.slider("Compresibilidad de la torta, s", 0.0, 1.0, 0.7, 0.05,
                          help="0 = la torta no se comprime (el flux sube en proporción a la presión). "
                               "1 = se comprime totalmente (subir la presión ya no aumenta el flux). "
                               "Para tortas de proteína se reportan valores intermedios a altos. "
                               "No se midió en el laboratorio.")
            semilla = st.number_input("Semilla aleatoria", 0, 99999, 2026, 1,
                                      help="Con la misma semilla se obtienen los mismos resultados.")
        simular = st.button("Simular con presión 🎲", type="primary", width="stretch")

    if not simular and "sim_presion" not in st.session_state:
        with col_out:
            st.info("Elige las condiciones y presiona **Simular con presión 🎲**.")
        _explicacion()
        return

    entradas = (float(PARAMS["J_agua"]), dP_psi, T, f_mem, s, C0, t_final, n_mc, int(semilla), p_max_bar)
    if simular:
        st.session_state.sim_presion = entradas
    entradas = st.session_state.sim_presion
    _, dP_psi, T, f_mem, s, C0, t_final, n_mc, semilla, p_max_bar = entradas
    r = correr(*entradas)

    dP = dP_psi * PSI_A_PA
    p_max = p_max_bar * BAR_A_PA
    t = r["t"]
    Jf = r["J_mc"][:, -1]
    Vf = r["V_mc"][:, -1]
    Cf = r["C_mc"][:, -1]

    with col_out:
        st.subheader("Resultados")

        # ----------------------------------------------------------- avisos
        if dP > p_max:
            st.error(
                f"🚫 **Supera la presión máxima ({p_max_bar:.1f} bar ≈ {p_max / PSI_A_PA:.0f} psi).** "
                "En el equipo real esto puede **compactar la membrana** (su resistencia sube de forma "
                "permanente) o **romper fibras o poros**: el coeficiente de rechazo caería y la "
                "proteína pasaría al permeado. **No se debe operar así.** La simulación se muestra "
                "solo para ver la tendencia.")
        elif dP > 0.8 * p_max:
            st.warning(f"⚠️ **Cerca de la presión máxima** ({dP / p_max:.0%} del límite). Deja margen: "
                       "las fluctuaciones de la bomba pueden superarlo por momentos.")
        prob_exc = float(np.mean(r["dP_mc"] > p_max))
        if 0.01 <= prob_exc and dP <= p_max:
            st.warning(f"⚠️ Con las fluctuaciones normales de presión (±5 %), en **{prob_exc:.0%}** de "
                       "las simulaciones se supera la presión máxima.")
        if not 0.5 * DP_REF <= dP <= 1.5 * DP_REF:
            st.info(f"ℹ️ **Lejos de la presión medida** ({DP_REF_PSI:g} psi). Cuanto más te alejas, más "
                    "depende el resultado del supuesto de compresibilidad: la banda de incertidumbre "
                    "se ensancha.")
        prob_vacio = float(np.mean(Vf > V_TANQUE))
        if prob_vacio > 0.05:
            st.warning(f"⚠️ **El tanque se vaciaría** en el {prob_vacio:.0%} de las simulaciones "
                       f"(más de {V_TANQUE:.0f} L de permeado). En la realidad la operación se "
                       "detendría antes.")
        prob_div = float(np.mean(~np.isfinite(Cf)))
        if prob_div > 0.05:
            st.error(f"🚫 En el {prob_div:.0%} de las simulaciones la concentración «explota» "
                     "(C → ∞) antes del final: el modelo de concentración deja de ser válido. "
                     "Reduce el tiempo, la presión o C₀.")

        # ---------------------------------------------------------- métricas
        p5, p50, p95 = np.nanpercentile(Jf, [5, 50, 95])
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Flux a {t_final} min (L/m²·h)", f"{p50:.2f}", help=f"Banda 90 %: {p5:.2f} – {p95:.2f}")
        c1.caption(f"90 %: {p5:.2f} – {p95:.2f}")
        v5, v50, v95 = np.nanpercentile(Vf, [5, 50, 95])
        c2.metric("Permeado total (L)", f"{v50:.1f}")
        c2.caption(f"90 %: {v5:.1f} – {v95:.1f}")
        if np.isfinite(Cf).mean() > 0.5:
            k5, k50, k95 = np.nanpercentile(Cf, [5, 50, 95])
            c3.metric("C final (g/L)", f"{k50:.2f}")
            c3.caption(f"90 %: {k5:.2f} – {k95:.2f}")
        else:
            c3.metric("C final (g/L)", "— (C → ∞)")

        # -------------------------------------------------------- interpretación
        J_ref_fin = r["J_ref11"][-1]
        cambio_J = r["J_nom"][-1] / J_ref_fin - 1
        cambio_P = dP / DP_REF - 1
        mu_rel = _mu_agua(T) / _mu_agua(T_REF) - 1
        lineas = []
        if abs(cambio_P) > 0.02:
            lineas.append(
                f"La presión está un **{cambio_P:+.0%}** respecto a la referencia, pero el flux final "
                f"cambia solo **{cambio_J:+.0%}**. " +
                ("No crece en la misma proporción porque, al empujar más fuerte, la capa de proteína "
                 "se compacta y opone más resistencia (torta compresible)." if cambio_P > 0 else
                 "Con menos presión la torta queda menos compacta, así que el flux baja menos de lo "
                 "que bajó la presión."))
        if f_mem != 1.0:
            lineas.append(
                f"La membrana tiene una resistencia propia **{f_mem - 1:+.0%}** respecto a la limpia: "
                + ("filtra más lento desde el inicio. El efecto se nota sobre todo en los primeros "
                   "minutos; después domina la resistencia de la torta." if f_mem > 1 else
                   "filtra más rápido al inicio, pero la torta termina dominando igual."))
        if abs(T - T_REF) >= 1:
            lineas.append(
                f"A {T:g} °C la viscosidad es **{mu_rel:+.0%}** respecto a 20 °C, y el flux cambia en "
                "sentido contrario: " + ("más frío → más viscoso → menos flux." if T < T_REF else
                                         "más caliente → menos viscoso → más flux (sin pasar del "
                                         "límite de temperatura de la membrana ni dañar la proteína)."))
        if not lineas:
            lineas.append("Estas son las condiciones de referencia del laboratorio: la mediana coincide "
                          "con la simulación base y la banda muestra la variabilidad entre réplicas.")
        st.markdown("**¿Qué está pasando?**\n\n" + "\n\n".join(f"- {l}" for l in lineas))

        # ----------------------------------------------------------- gráficas
        fig, ax = plt.subplots(figsize=(7, 3.8))
        _banda(ax, t, r["J_mc"], "#c00000", f"{dP_psi:g} psi")
        ax.plot(t, r["J_ref11"], "k--", lw=1.2, label=f"Referencia {DP_REF_PSI:g} psi (datos)")
        if t_final > 40:
            ax.axvspan(40, t_final, color="orange", alpha=0.06)
        ax.set_xlabel("Tiempo (min)"); ax.set_ylabel("J (L/m² h)")
        ax.set_title("Flux de permeado con incertidumbre (Montecarlo)")
        ax.grid(alpha=0.3); ax.legend(fontsize=8)
        fig.tight_layout(); st.pyplot(fig); plt.close(fig)

        fig, ax = plt.subplots(figsize=(7, 3.8))
        x_bar = r["dP_grid"] / BAR_A_PA
        p5g, p50g, p95g = np.nanpercentile(r["J_grid_mc"], [5, 50, 95], axis=0)
        ax.fill_between(x_bar, p5g, p95g, color="#c00000", alpha=0.18, label="Lactosuero: banda 90 %")
        ax.plot(x_bar, p50g, color="#c00000", lw=2, label=f"Lactosuero a {t_final} min")
        ax.plot(x_bar, r["J_agua_grid"], color="#2e86ab", lw=1.5, ls="-.", label="Agua pura (sin torta)")
        ax.axvspan(p_max / BAR_A_PA, x_bar[-1], color="red", alpha=0.08)
        ax.axvline(p_max / BAR_A_PA, color="red", lw=1.5, label=f"Presión máx. ({p_max_bar:.1f} bar, provisional)")
        ax.axvline(DP_REF / BAR_A_PA, color="k", ls="--", lw=1, label=f"Medido ({DP_REF_PSI:g} psi)")
        ax.axvline(dP / BAR_A_PA, color="#1f4e78", ls=":", lw=2, label="Tu presión")
        ax.set_ylim(0, max(np.nanmax(p95g), 1) * 1.4)
        ax.set_xlabel("Presión transmembrana (bar)"); ax.set_ylabel("J (L/m² h)")
        ax.set_title("¿Cuánto flux gano subiendo la presión?")
        ax.grid(alpha=0.3); ax.legend(fontsize=7, loc="upper left")
        fig.tight_layout(); st.pyplot(fig); plt.close(fig)
        st.caption("Con agua pura el flux sube en línea recta con la presión. Con lactosuero la curva "
                   "se aplana: la torta se compacta y llega un punto en que subir la presión casi no "
                   "aumenta el flux, pero sí acerca la membrana a su límite y la ensucia más.")

        if np.isfinite(r["C_mc"]).mean() > 0.5:
            fig, ax = plt.subplots(figsize=(7, 3.4))
            _banda(ax, t, r["C_mc"], "#1f4e78", f"{dP_psi:g} psi")
            ax.set_ylim(0, min(np.nanpercentile(r["C_mc"], 99) * 1.15, 5 * C0))
            ax.set_xlabel("Tiempo (min)"); ax.set_ylabel("C tanque (g/L)")
            ax.set_title("Concentración de proteína en el tanque")
            ax.grid(alpha=0.3); ax.legend(fontsize=8)
            fig.tight_layout(); st.pyplot(fig); plt.close(fig)

        fig, ax = plt.subplots(figsize=(7, 2.8))
        ax.hist(Jf[np.isfinite(Jf)], bins=30, color="#c00000", alpha=0.7)
        ax.axvline(p50, color="k", lw=1.5)
        ax.set_xlabel(f"Flux a {t_final} min (L/m² h)"); ax.set_ylabel("Nº de simulaciones")
        ax.set_title(f"Distribución de {n_mc} simulaciones")
        ax.grid(alpha=0.3)
        fig.tight_layout(); st.pyplot(fig); plt.close(fig)

        df = pd.DataFrame({
            "t (min)": t,
            "J mediana (L/m2 h)": np.nanpercentile(r["J_mc"], 50, axis=0),
            "J P5": np.nanpercentile(r["J_mc"], 5, axis=0),
            "J P95": np.nanpercentile(r["J_mc"], 95, axis=0),
            "C mediana (g/L)": np.nanpercentile(r["C_mc"], 50, axis=0),
            "Vol. permeado mediana (L)": np.nanpercentile(r["V_mc"], 50, axis=0),
        })
        st.download_button("📥 Descargar resultados (CSV)", df.to_csv(index=False).encode("utf-8"),
                           file_name=f"simulacion_presion_{dP_psi:g}psi.csv", mime="text/csv",
                           width="stretch")
    _explicacion()


def _explicacion():
    with st.expander("📘 Fundamento del modelo y supuestos"):
        st.markdown(rf"""
**Ley de Darcy con resistencias en serie**

$$J = \frac{{\Delta P}}{{\mu\,\left(R_M + R_f\right)}}$$

- $R_M$: resistencia de la membrana limpia, obtenida del flux de agua pura a {DP_REF_PSI:g} psi.
- $R_f(t)$: resistencia del ensuciamiento (torta de proteína), obtenida del modelo de Hermia
  ajustado con R:28/72. A la presión de referencia el modelo reproduce exactamente la simulación base.

**Efecto de la presión: torta compresible**

$$R_f(t,\Delta P) = R_{{f,ref}}(t)\,\left(\frac{{\Delta P}}{{\Delta P_{{ref}}}}\right)^{{s}}$$

Con $s = 0$, el flux crece en proporción a la presión; con $s = 1$, el flux se estanca (flux límite).
**$s$ no se midió**: es un supuesto. Para calibrarlo basta con hacer 2 o 3 corridas cortas a otras
presiones.

**Montecarlo**: en cada simulación se toman al azar
- $J_0$ y $K_c$ según la incertidumbre del ajuste de las **3 réplicas**;
- $K$ según la variación entre réplicas (±10 %);
- la compresibilidad (±0.1), la presión real (±5 %), la temperatura (±1 °C) y la resistencia de la
  membrana (±5 %).

La banda sombreada contiene el 90 % de los resultados.

**Presión máxima**: {P_MAX_PROVISIONAL_BAR:.1f} bar por defecto. Es un valor **provisional** tomado de
fichas técnicas de membranas de ultrafiltración para agua (rango típico de 1 a 3 bar), porque no se
tiene la ficha del equipo.

**Limitaciones**: no se modela que una torta más gruesa (por más flux) crezca más rápido, ni la
pérdida de rechazo por encima de la presión máxima; tampoco el efecto de la velocidad de flujo
cruzado.
""")
