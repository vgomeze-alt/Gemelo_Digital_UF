# modelo_actualizado.py
# El gemelo digital aprende de las prácticas que el profesor aprueba.
#
# Cada práctica aprobada (y sin alertas graves) aporta:
#   1. Si es de la VUELTA 2: una corrida más para los parámetros del modelo
#      base. J0, Kc y K pasan a ser el promedio por corrida de la tesis
#      (3 réplicas) + las prácticas aprobadas; su dispersión entre corridas
#      alimenta la incertidumbre del Montecarlo.
#   2. Si es de OTRA VUELTA y trae la presión de entrada: un punto para
#      calibrar la curva de la válvula roja. La calibración es bayesiana: el
#      supuesto inicial (prior) se combina con las presiones medidas y el
#      Montecarlo sortea desde la curva ya corregida (posterior). Sin datos,
#      el resultado es exactamente el supuesto inicial.
#
# Las prácticas con alertas graves (rechazo < 90 %, presión > 4 bar, peso de
# permeado no acumulado) se guardan pero NO entran al modelo.

import json

import numpy as np
import pandas as pd

# ---- referencia: tesis, vuelta 2 (3 réplicas)
TESIS = {"J0": 19.0545, "Kc": 1.33995e-4, "K": 0.0012680, "n_corridas": 3, "P_psi": 11.0}

# Supuestos iniciales de la válvula (los mismos del modo de vueltas)
PRIOR_N = (1.0, 0.25)          # media, desviación
PRIOR_LOG_R = (np.log(0.10), 0.35)
SIGMA_LOG_P = 0.12             # error de lectura del manómetro (~12 %)
GRID_R = np.exp(np.linspace(np.log(0.02), np.log(0.4), 70))
GRID_N = np.linspace(0.4, 2.5, 70)


def practicas_validas(df):
    """Lista de prácticas aprobadas y sin alertas graves, con sus datos decodificados."""
    if df is None or df.empty:
        return []
    salida = []
    for _, f in df.iterrows():
        if str(f.get("estado", "")).strip() != "Aprobado":
            continue
        if str(f.get("alertas", "")).strip() not in ("", "nan", "ninguna"):
            continue
        try:
            datos = json.loads(f["datos"])
            vuelta = int(float(f["vuelta"]))
        except Exception:
            continue
        salida.append({"fecha": f.get("fecha", ""), "nombre": f.get("nombre", ""),
                       "vuelta": vuelta, **datos})
    return salida


def parametros_base(practicas):
    """J0, Kc, K promediados por corrida: tesis (3) + prácticas de la vuelta 2."""
    v2 = [p for p in practicas if p["vuelta"] == 2 and p.get("J0") and p.get("Kc")]
    if not v2:
        return dict(TESIS, n_practicas=0)
    n = TESIS["n_corridas"]
    J0 = (TESIS["J0"] * n + sum(p["J0"] for p in v2)) / (n + len(v2))
    Kc = (TESIS["Kc"] * n + sum(p["Kc"] for p in v2)) / (n + len(v2))
    conK = [p["K"] for p in v2 if p.get("K")]
    K = (TESIS["K"] * n + sum(conK)) / (n + len(conK))
    return {"J0": J0, "Kc": Kc, "K": K, "n_corridas": n + len(v2), "n_practicas": len(v2),
            "P_psi": TESIS["P_psi"]}


def puntos_valvula(practicas):
    """(vuelta, presión media en psi, flux final, t final) de cada práctica con presión."""
    pts = []
    for p in practicas:
        P = [x for x in p.get("P_ent", []) if x is not None and np.isfinite(x)]
        if not P:
            continue
        J = [(t, j) for t, j in zip(p.get("t", []), p.get("J", [])) if j is not None and np.isfinite(j)]
        tf, Jf = (J[-1] if J else (np.nan, np.nan))
        pts.append((p["vuelta"], float(np.mean(P)), float(Jf), float(tf)))
    return pts


def posterior_valvula(pts, P_ref_psi=11.0):
    """Pesos de la curva de la válvula en la malla (r, n) dados los puntos medidos.

    Modelo: P(v) = P_ref·[Cv(2)/Cv(v)]², Cv(v) = r + (1 − r)(v/9)^n.
    Las prácticas de la vuelta 2 actualizan la presión de anclaje."""
    R, N = np.meshgrid(GRID_R, GRID_N, indexing="ij")
    logp = (-0.5 * ((np.log(R) - PRIOR_LOG_R[0]) / PRIOR_LOG_R[1]) ** 2
            - 0.5 * ((N - PRIOR_N[0]) / PRIOR_N[1]) ** 2)
    P2 = [P for v, P, _, _ in pts if v == 2]
    P_ancla = (P_ref_psi * 3 + sum(P2)) / (3 + len(P2))
    otras = [(v, P) for v, P, _, _ in pts if v != 2]
    for v, P in otras:
        cv = lambda x: R + (1 - R) * (x / 9.0) ** N
        Pm = P_ancla * (cv(2.0) / cv(float(v))) ** 2
        logp += -0.5 * ((np.log(Pm) - np.log(P)) / SIGMA_LOG_P) ** 2
    w = np.exp(logp - logp.max())
    w /= w.sum()
    return w, P_ancla, len(otras)


def muestrear_valvula(rng, n_mc, pts):
    """Sortea (r, n) desde la posterior; sin datos equivale a sortear del prior."""
    w, P_ancla, n_otras = posterior_valvula(pts)
    idx = rng.choice(w.size, size=n_mc, p=w.ravel())
    i, j = np.unravel_index(idx, w.shape)
    r = GRID_R[i] * np.exp(rng.uniform(-0.02, 0.02, n_mc))        # suaviza la malla
    n = GRID_N[j] + rng.uniform(-0.015, 0.015, n_mc)
    return r[:, None], n[:, None], P_ancla, n_otras


def resumen_para_guardar(d, aj, alertas):
    """Lo que se guarda de cada práctica (JSON compacto) para alimentar el modelo."""
    def lst(col):
        return [None if not np.isfinite(x) else round(float(x), 4) for x in d[col].values]
    datos = {"t": lst("t"), "J": lst("J"), "C": lst("C_t"), "P_ent": lst("P_ent")}
    for k in ("J0", "Kc", "K", "C0"):
        if k in aj:
            datos[k] = float(aj[k])
    return json.dumps(datos, separators=(",", ":")), ("; ".join(alertas) if alertas else "ninguna")


def tabla_practicas(df):
    """Vista resumida para el panel del profesor."""
    if df is None or df.empty:
        return pd.DataFrame()
    filas = []
    for idx, f in df.iterrows():
        try:
            d = json.loads(f["datos"])
        except Exception:
            d = {}
        filas.append({"_idx": idx, "Fecha": f.get("fecha", ""), "Grupo": f.get("nombre", ""),
                      "Vuelta": f.get("vuelta", ""), "J0": round(d.get("J0", np.nan), 2),
                      "K": round(d.get("K", np.nan), 5) if d.get("K") else np.nan,
                      "Alertas": f.get("alertas", ""), "Estado": f.get("estado", "")})
    return pd.DataFrame(filas)
