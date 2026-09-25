import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import io
import smtplib
from email.message import EmailMessage
from datetime import datetime

# =============================================================================
# GEMELO DIGITAL - MEMBRANA DE ULTRAFILTRACIÓN (Lactosuero, relación R:28/72)
# Basado en el archivo original "AppBeta.py" (Banco de Intercambiadores de
# Calor - BIC). Se conservó la misma estructura y el mismo estilo visual,
# adaptando el contenido al proyecto de la membrana.
#
# Referencia de diseño / inspiración: https://gemelodigitalbic.streamlit.app/
#
# NOTA: Todo lo marcado como "POR COMPLETAR" o "POR DEFINIR" es contenido que
# aún no se tiene (imágenes, videos, PDFs, textos institucionales, etc.) y
# debe reemplazarse antes de publicar la app.
# =============================================================================


### FORMATO PARA VISUALIZACIÓN DE LA PÁGINA
st.markdown("""
    <style>
    /* Fondo principal de la interfaz */
    .css-1v3fvcr {
        background-color: #3c3cb9; /* Azul */
        color: black; /* Texto negro */
    }

    /* Botones de la barra lateral */
    [data-testid="stSidebar"] .stButton > button {
        background-color: #1C1C1C; /* Negro */
        color: white; /* Texto blanco */
        border-radius: 5px; /* Bordes redondeados */
        border: 1px solid white; /* Borde blanco */
        font-size: 16px; /* Tamaño del texto */
        margin: 10px 0; /* Espaciado entre botones */
    }

    /* Hover de los botones */
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #4682B4; /* Azul acero claro */
        color: white; /* Texto blanco */
        border: 1px solid #1E90FF; /* Borde azul brillante */
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    /* Hover de todos los botones */
    .stButton > button:hover {
        background-color: #4682B4; /* Azul acero claro */
        color: white; /* Texto blanco */
        border: 1px solid #1E90FF; /* Borde azul brillante */
    }
    </style>
""", unsafe_allow_html=True)


st.set_page_config(layout="wide", page_title="Gemelo Digital - Membrana UF")

if "pagina" not in st.session_state:
    st.session_state.pagina = "inicio"


# =============================================================================
# PARÁMETROS DEL MODELO (ajustados con los datos experimentales R 28/72)
# Ver archivo Excel "modelo_membrana_R2872.xlsx", hojas "Transporte",
# "Fouling" y "Modelo_Final" para el detalle completo de cada ajuste.
# =============================================================================

PARAMS = {
    # Modelo de balance por lotes (mecanístico, PDF): 1/C(t) - 1/C0 = -K*t
    "K": 0.0012680,          # (g/L)^-1 * min^-1  -- ajuste excluyendo punto atípico t=8 min

    # Modelo de fouling recomendado: Hermia n=0 (formación de torta)
    # J(t) = [1/J0^2 + 2*Kc*t]^-0.5
    "J0_torta": 19.0545,     # L/(m2 h)
    "Kc_torta": 0.000133995, # unidades consistentes con t en min, J en L/m2h

    # Modelo alternativo (respaldo): exponencial empírico
    # J(t) = Jinf + (J0 - Jinf) * exp(-k*t)
    "J0_exp": 18.77758,      # L/(m2 h)
    "Jinf_exp": 8.12218,     # L/(m2 h)
    "k_exp": 0.0666969,      # 1/min

    # Flux de agua pura (limpieza / línea base de resistencia de membrana, sin proteína)
    # Ver Hoja "Modelo": R_M se calculó justamente con este flux de agua medido.
    "J_agua": 23.117,        # L/(m2 h) -- flux de agua experimental, ΔP y membrana de referencia

    # NOTA: k_enjuague es una estimación ILUSTRATIVA, no ajustada con datos
    # experimentales (no contamos con una curva medida de recuperación de flux
    # durante un enjuague sin limpieza química). Se incluye solo para que la
    # simulación muestre una tendencia físicamente razonable; no debe tratarse
    # como un valor validado.
    "k_enjuague_estimado": 0.08,   # 1/min, supuesto ilustrativo

    # Área de membrana (dato de equipo, Hoja "Modelo")
    "A_M": 4.8,               # m2

    # Rango experimental validado
    "t_min_valido": 0,
    "t_max_valido": 40,       # min
    "C0_valido": 7.395,       # g/L (valor experimental de referencia)
}


def modelo_C(t, C0, K=PARAMS["K"]):
    """Concentración de proteína en el tanque C(t), balance por lotes."""
    t = np.asarray(t, dtype=float)
    inv_C0 = 1.0 / C0
    denom = inv_C0 - K * t
    denom = np.where(denom <= 0, np.nan, denom)  # evita división por valores no físicos
    return 1.0 / denom


def modelo_J_torta(t, J0=PARAMS["J0_torta"], Kc=PARAMS["Kc_torta"]):
    """Flux de permeado J(t), modelo de Hermia n=0 (formación de torta)."""
    t = np.asarray(t, dtype=float)
    return (1.0 / J0**2 + 2.0 * Kc * t) ** -0.5


def modelo_J_exp(t, J0=PARAMS["J0_exp"], Jinf=PARAMS["Jinf_exp"], k=PARAMS["k_exp"]):
    """Flux de permeado J(t), modelo exponencial empírico (alternativa)."""
    t = np.asarray(t, dtype=float)
    return Jinf + (J0 - Jinf) * np.exp(-k * t)


def modelo_J_agua(t, J_agua=PARAMS["J_agua"]):
    """Flux de agua pura J(t), membrana LIMPIA (tras limpieza química completa).
    Sin proteína no hay formación de torta ni polarización por concentración
    medibles en nuestros datos: el flux se mantiene prácticamente constante en
    el tiempo (ver PDF de fundamentación, sección de resistencia irreversible
    ≈ 0 — el flux de agua retorna a su valor inicial tras cada limpieza)."""
    t = np.asarray(t, dtype=float)
    return np.full_like(t, float(J_agua))


def modelo_J_enjuague(t, J_inicio, J_agua=PARAMS["J_agua"], k=PARAMS["k_enjuague_estimado"]):
    """Flux de agua J(t) cuando se pasa agua INMEDIATAMENTE después del
    lactosuero, sin limpieza química (la torta sigue físicamente presente).

    ADVERTENCIA: esta curva es una aproximación ILUSTRATIVA (recuperación
    exponencial desde el flux final del lactosuero hacia el flux de agua
    limpia). No está ajustada con datos experimentales -- no contamos con una
    medición de la curva de recuperación de flux durante un enjuague sin
    limpieza química. Úsala solo como referencia cualitativa de la tendencia
    esperada, no como una predicción validada.
    """
    t = np.asarray(t, dtype=float)
    return J_agua - (J_agua - J_inicio) * np.exp(-k * t)


# =============================================================================
# REGISTRO DE CARGAS (para poder Aprobar / Rechazar después)
# =============================================================================
# Se guarda en un archivo CSV local (registros_carga.csv). Mientras la app no
# se reinicie o se vuelva a desplegar, este archivo persiste entre sesiones.
# Si necesitas que sobreviva incluso a reinicios del servidor, más adelante se
# puede migrar a una base de datos o a Google Sheets, pero para empezar esto
# es suficiente.

REGISTRO_PATH = "registros_carga.csv"
COLUMNAS_REGISTRO = ["nombre", "correo", "tipo_practica", "archivo", "tamano_kb", "fecha", "estado", "observaciones"]


def cargar_registros():
    """Devuelve el DataFrame con todos los registros de cargas (o uno vacío)."""
    try:
        return pd.read_csv(REGISTRO_PATH)
    except FileNotFoundError:
        return pd.DataFrame(columns=COLUMNAS_REGISTRO)


def guardar_nuevo_registro(nombre, correo, tipo_practica, archivo_nombre, tamano_bytes, observaciones=""):
    """Agrega una fila nueva con estado 'Pendiente' y guarda el archivo."""
    df = cargar_registros()
    nueva_fila = {
        "nombre": nombre,
        "correo": correo,
        "tipo_practica": tipo_practica,
        "archivo": archivo_nombre,
        "tamano_kb": round(tamano_bytes / 1024, 1),
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "estado": "Pendiente",
        "observaciones": observaciones,
    }
    df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
    df.to_csv(REGISTRO_PATH, index=False)


def actualizar_estado_registro(indice, nuevo_estado):
    """Cambia el estado ('Aprobado' / 'Rechazado') de la fila con ese índice."""
    df = cargar_registros()
    df.loc[indice, "estado"] = nuevo_estado
    df.to_csv(REGISTRO_PATH, index=False)


# =============================================================================
# NOTIFICACIÓN POR CORREO AL SUBIR DATOS
# =============================================================================
# Requiere configurar credenciales en .streamlit/secrets.toml (NO subir este
# archivo a un repositorio público). Ejemplo de contenido:
#
# [email]
# remitente = "tu_correo_gmail@gmail.com"
# password  = "xxxx xxxx xxxx xxxx"   # App Password de Gmail, no la clave normal
# destinatario = "correo_que_recibe_las_alertas@dominio.com"
# smtp_server = "smtp.gmail.com"
# smtp_port = 587
#
# [admin]
# password = "la_clave_que_tú_quieras"
#
# Con Gmail, no funciona la contraseña normal de la cuenta: hay que activar
# verificación en 2 pasos y generar una "Contraseña de aplicación" en
# https://myaccount.google.com/apppasswords

def enviar_notificacion_carga(nombre_usuario, tipo_practica, nombre_archivo,
                               tamano_bytes, adjuntar_archivo=None, observaciones=""):
    """Envía un correo notificando que alguien subió datos al Gemelo Digital.
    Devuelve (True, None) si se envió, o (False, mensaje_error) si falló.
    """
    try:
        cfg = st.secrets["email"]
    except Exception:
        return False, (
            "No se encontraron las credenciales de correo en st.secrets "
            "(sección [email]). Configúralas en .streamlit/secrets.toml."
        )

    msg = EmailMessage()
    msg["Subject"] = f"[Gemelo Digital UF] Nueva carga de datos - {nombre_usuario}"
    msg["From"] = cfg["remitente"]
    msg["To"] = cfg["destinatario"]

    cuerpo = (
        f"Se registró una nueva carga de datos en el Gemelo Digital de la "
        f"Membrana de Ultrafiltración.\n\n"
        f"Usuario / responsable: {nombre_usuario}\n"
        f"Tipo de práctica: {tipo_practica}\n"
        f"Archivo: {nombre_archivo}\n"
        f"Tamaño: {tamano_bytes / 1024:.1f} KB\n"
        f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Observaciones / anomalías reportadas: "
        f"{observaciones if observaciones.strip() else '(sin observaciones)'}\n"
    )
    msg.set_content(cuerpo)

    if adjuntar_archivo is not None:
        adjuntar_archivo.seek(0)
        datos_bin = adjuntar_archivo.read()
        msg.add_attachment(
            datos_bin,
            maintype="application",
            subtype="octet-stream",
            filename=nombre_archivo,
        )

    try:
        with smtplib.SMTP(cfg["smtp_server"], int(cfg["smtp_port"])) as server:
            server.starttls()
            server.login(cfg["remitente"], cfg["password"])
            server.send_message(msg)
        return True, None
    except Exception as e:
        return False, str(e)


def enviar_notificacion_decision(correo_destino, nombre_usuario, tipo_practica, decision):
    """Envía un correo a quien subió los datos avisando que fue Aprobado o Rechazado.
    Devuelve (True, None) si se envió, o (False, mensaje_error) si falló.
    """
    try:
        cfg = st.secrets["email"]
    except Exception:
        return False, (
            "No se encontraron las credenciales de correo en st.secrets "
            "(sección [email])."
        )

    if decision == "Aprobado":
        asunto = "✅ Tu práctica fue APROBADA"
        cuerpo = (
            f"Hola {nombre_usuario},\n\n"
            f"Tu registro de la práctica '{tipo_practica}' en el Gemelo Digital "
            f"de la Membrana de Ultrafiltración fue APROBADO: se confirmó que la "
            f"práctica sí se realizó y los datos quedaron validados.\n\n"
            f"Gracias por tu carga."
        )
    else:
        asunto = "❌ Tu práctica fue RECHAZADA"
        cuerpo = (
            f"Hola {nombre_usuario},\n\n"
            f"Tu registro de la práctica '{tipo_practica}' en el Gemelo Digital "
            f"de la Membrana de Ultrafiltración fue RECHAZADO: no se pudo "
            f"confirmar que la práctica se haya realizado como se indicó.\n\n"
            f"Si crees que esto es un error, contacta a la persona encargada del equipo."
        )

    msg = EmailMessage()
    msg["Subject"] = f"[Gemelo Digital UF] {asunto}"
    msg["From"] = cfg["remitente"]
    msg["To"] = correo_destino
    msg.set_content(cuerpo)

    try:
        with smtplib.SMTP(cfg["smtp_server"], int(cfg["smtp_port"])) as server:
            server.starttls()
            server.login(cfg["remitente"], cfg["password"])
            server.send_message(msg)
        return True, None
    except Exception as e:
        return False, str(e)

def generar_plantilla_excel():
    """Genera en memoria (sin tocar el disco) el Excel de plantilla que las
    personas descargan, llenan y vuelven a subir en 'Sube tus Datos'.
    Devuelve un BytesIO listo para st.download_button.
    """
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.comments import Comment
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()

    AMARILLO = PatternFill("solid", fgColor="FFF2CC")
    GRIS = PatternFill("solid", fgColor="F2F2F2")
    AZUL = PatternFill("solid", fgColor="1F4E78")
    BLANCO_BOLD = Font(bold=True, color="FFFFFF", size=11)
    BOLD = Font(bold=True, size=11)
    NOTA = Font(italic=True, size=9, color="808080")
    thin = Side(style="thin", color="BFBFBF")
    BORDE = Border(left=thin, right=thin, top=thin, bottom=thin)

    # ================= HOJA 1: INSTRUCCIONES =================
    ws0 = wb.active
    ws0.title = "Instrucciones"
    ws0.sheet_view.showGridLines = False
    ws0["B2"] = "PLANTILLA DE CARGA DE DATOS — GEMELO DIGITAL MEMBRANA DE ULTRAFILTRACIÓN"
    ws0["B2"].font = Font(bold=True, size=14, color="1F4E78")
    ws0["B4"] = "Cómo usar esta plantilla"
    ws0["B4"].font = BOLD
    instrucciones = [
        "1. Ve a la hoja 'Datos_Practica'.",
        "2. Llena SOLO las celdas de color AMARILLO — son las únicas que debes escribir.",
        "3. Las celdas de color GRIS tienen fórmulas que se calculan solas (Volumen, Flux, "
        "Concentración, etc.) — no las edites ni escribas sobre ellas.",
        "4. Completa el bloque de identificación (integrantes, fecha, profesor, relación de "
        "rechazo) antes de la tabla de datos.",
        "5. Guarda el archivo con tu nombre o el del grupo (ej. Datos_Grupo3_R2872.xlsx) y "
        "súbelo en la pestaña 'Sube tus Datos' del Gemelo Digital.",
    ]
    r = 5
    for linea in instrucciones:
        ws0.cell(row=r, column=2, value=linea).alignment = Alignment(wrap_text=True)
        ws0.merge_cells(f"B{r}:H{r}")
        r += 1
    r += 1
    ws0.cell(row=r, column=2, value="Código de colores").font = BOLD
    r += 1
    ws0.cell(row=r, column=2, value="Escribir aquí (dato experimental)").fill = AMARILLO
    ws0.cell(row=r, column=2).border = BORDE
    r += 1
    ws0.cell(row=r, column=2, value="No tocar (fórmula automática)").fill = GRIS
    ws0.cell(row=r, column=2).border = BORDE
    ws0.column_dimensions["B"].width = 46

    # ================= HOJA 2: DATOS_PRACTICA =================
    ws = wb.create_sheet("Datos_Practica")
    ws.sheet_view.showGridLines = False

    ws["B2"] = "DATOS DE LA PRÁCTICA — ULTRAFILTRACIÓN DE LACTOSUERO"
    ws["B2"].font = Font(bold=True, size=14, color="1F4E78")

    campos_id = [
        ("Integrante 1", ""),
        ("Integrante 2", ""),
        ("Integrante 3", ""),
        ("Correo de contacto del grupo", ""),
        ("Fecha de la práctica", ""),
        ("Profesor a cargo", "Mario Andrés Noriega Valencia"),
        ("Relación de rechazo utilizada (ej. R:28/72)", ""),
        ("Área de membrana, A_M (m2)", 4.8),
        ("Densidad del lactosuero (kg/L)", 1.026),
        ("Factor de calibración (pendiente de la curva Absorbancia vs. Concentración)", ""),
    ]
    r = 4
    for etiqueta, valor_default in campos_id:
        ws.cell(row=r, column=2, value=etiqueta).font = BOLD
        ws.merge_cells(f"B{r}:D{r}")
        c = ws.cell(row=r, column=5, value=valor_default)
        c.fill = AMARILLO
        c.border = BORDE
        ws.merge_cells(f"E{r}:F{r}")
        r += 1

    ws.cell(row=r+1, column=2,
            value="Factor de calibración: si tu curva es Concentración = m×Absorbancia + b, "
                  "escribe aquí la pendiente 'm'. Pregunta a tu profesor si no la tienes.").font = NOTA
    ws.merge_cells(f"B{r+1}:H{r+1}")
    ws.cell(row=r+1, column=2).alignment = Alignment(wrap_text=True)

    fila_factor_calibracion = 13  # Área en fila 11, Densidad en fila 12, Factor en fila 13
    fila_area = 11
    fila_densidad = 12

    r_tabla_header = r + 3
    encabezados = [
        "Tiempo (min)", "Masa Permeado (kg)", "Masa Rechazo (kg)",
        "Absorbancia Permeado (u.a.)", "Absorbancia Rechazo (u.a.)", "Absorbancia Tanque (u.a.)",
        "Volumen Permeado (L)", "Flujo Volumétrico Q (L/min)", "Flux J (L/m2·h)",
        "Concentración Tanque (g/L)",
    ]
    for j, h in enumerate(encabezados):
        c = ws.cell(row=r_tabla_header, column=2+j, value=h)
        c.fill = AZUL
        c.font = BLANCO_BOLD
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDE

    tiempos = [0, 8, 16, 24, 32, 40]
    r0 = r_tabla_header + 1
    for i, t in enumerate(tiempos):
        rr = r0 + i
        ws.cell(row=rr, column=2, value=t).fill = AMARILLO
        for col in (3, 4, 5, 6, 7):
            ws.cell(row=rr, column=col, value=None).fill = AMARILLO

        ws.cell(row=rr, column=8,
                value=f"=IF(C{rr}=\"\",\"\",C{rr}/$E${fila_densidad})").fill = GRIS
        ws.cell(row=rr, column=9,
                value=f"=IF(OR(H{rr}=\"\",B{rr}=0),\"\",H{rr}/B{rr})").fill = GRIS
        ws.cell(row=rr, column=10,
                value=f"=IF(I{rr}=\"\",\"\",I{rr}*60/$E${fila_area})").fill = GRIS
        ws.cell(row=rr, column=11,
                value=f"=IF(G{rr}=\"\",\"\",G{rr}*$E${fila_factor_calibracion})").fill = GRIS

        for col in range(2, 12):
            ws.cell(row=rr, column=col).border = BORDE

    ws.cell(row=r0, column=3).comment = Comment(
        "Masa acumulada de permeado recolectada hasta este tiempo, en kilogramos.", "Gemelo Digital UF")
    ws.cell(row=r0, column=4).comment = Comment(
        "Masa acumulada de rechazo (retenido) hasta este tiempo, en kilogramos.", "Gemelo Digital UF")
    ws.cell(row=r0, column=5).comment = Comment(
        "Lectura de absorbancia UV del permeado (adimensional, unidades arbitrarias).", "Gemelo Digital UF")
    ws.cell(row=r0, column=8).comment = Comment(
        "Se calcula solo: Volumen = Masa Permeado / Densidad del lactosuero.", "Gemelo Digital UF")
    ws.cell(row=r0, column=10).comment = Comment(
        "Se calcula solo: Flux = Q(L/min) * 60 / Área de membrana (m2). Esta es la variable "
        "clave para comparar con el modelo del Gemelo Digital.", "Gemelo Digital UF")

    ws.column_dimensions["B"].width = 14
    for col in "CDEFGHIJK":
        ws.column_dimensions[col].width = 16
    ws.freeze_panes = f"B{r0}"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

# =============================================================================
# PÁGINAS
# =============================================================================

def inicio():
    st.write("# Bienvenido al Gemelo Digital de la Membrana de Ultrafiltración")
    st.text(
        "Un gemelo digital del proceso de ultrafiltración de lactosuero (membrana, "
        "relación de rechazo), desarrollado a partir de datos experimentales "
        "para aprender, enseñar y explorar el comportamiento del proceso sin necesidad "
        "de operar el equipo real."
    )
    st.write("## Instructivo del Gemelo Digital")
    st.video("https://youtu.be/78Ob75mh4x8")


def informacion_general():
    st.write("# Información General")
    st.write("### Entender la membrana antes de entender el gemelo digital")

    st.write(
        "A continuación se presentan fotografías del equipo real de laboratorio, "
        "señalando sus componentes principales: el tanque de alimentación, la línea "
        "de ingreso de fluido, la unidad de microfiltración, el panel de válvulas y "
        "manómetros, y la sección de salida de la membrana con la división de "
        "corrientes de permeado y rechazo."
    )

    col_img1, col_img2, col_img3 = st.columns(3)

    with col_img1:
        st.image(
            "Multimedia/Imagenes/pfd_alimentacion.png",
            caption="Vista del equipo en sección de alimentación",
            width="stretch",
        )

    with col_img2:
        st.image(
            "Multimedia/Imagenes/pfd_panel_valvulas.png",
            caption="Vista del equipo, panel de válvulas y manómetros",
            width="stretch",
        )

    with col_img3:
        st.image(
            "Multimedia/Imagenes/pfd_salida_membrana.png",
            caption="Vista del equipo, sección de salida de la membrana",
            width="stretch",
        )

    if "infogen" not in st.session_state:
        st.session_state.infogen = "basico"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Lo básico", width="stretch"):
            st.session_state.infogen = "basico"

    with col2:
        if st.button("Nuestra solución", width="stretch"):
            st.session_state.infogen = "solucion"

    with col3:
        if st.button("Funcionamiento", width="stretch"):
            st.session_state.infogen = "funcionamiento"

    with col4:
        if st.button("¿Qué ganas tú?", width="stretch"):
            st.session_state.infogen = "ganas"

    if st.session_state.infogen == "basico":
        st.markdown(
            """
            <p style='text-align: justify;'>
            La ultrafiltración (UF) es una tecnología avanzada de separación por membranas
            que permite la concentración selectiva de macromoléculas. Aunque el equipo del
            laboratorio fue diseñado originalmente para el tratamiento de agua, se ha
            adaptado en este proyecto para la concentración de proteínas de lactosuero, una
            operación de alto valor para la industria alimentaria y de suplementos
            alimenticios.
            </p>
            """,
            unsafe_allow_html=True)

        st.header("Corrientes de proceso y reciclo")
        st.markdown(
            """
            <p style='text-align: justify;'>
            El sistema opera dividiendo la alimentación en dos corrientes principales
            dentro del módulo de filtración:
            </p>
            <p style='text-align: justify;'>
            <b>El Permeado:</b> corriente compuesta por agua, lactosa y sales minerales que
            atraviesan los poros de la membrana. Esta corriente se retira de manera continua
            hacia un tanque de recolección.
            </p>
            <p style='text-align: justify;'>
            <b>El Rechazo (o Retenido):</b> corriente que contiene las proteínas de mayor
            tamaño que no consiguen atravesar los poros de la membrana. Esta línea se
            recircula constantemente de vuelta al tanque de alimentación (operación en
            reciclo). De este modo, las proteínas no quedan retenidas permanentemente en la
            membrana, sino que se van concentrando progresivamente en el tanque de
            alimentación principal.
            </p>
            """,
            unsafe_allow_html=True)

        st.image(
            "Multimedia/Imagenes/diagrama_flujo_vs_flux.png",
            caption="Comparación de Flujo Volumétrico y Flux de Permeado en Filtración por Membrana",
            width="stretch",
        )

        st.header("El fenómeno del fouling (ensuciamiento)")
        st.markdown(
            """
            <p style='text-align: justify;'>
            Durante la operación con lactosuero, las grasas y proteínas forman una capa
            acumulada sobre la superficie de la membrana (conocida como biofilm o
            ensuciamiento). Este fenómeno físico genera una resistencia que causa que el
            flux de permeado disminuya drásticamente con el tiempo y que las presiones
            internas del sistema se incrementen en los manómetros.
            </p>
            """,
            unsafe_allow_html=True)

    if st.session_state.infogen == "solucion":
        st.header("¿Por qué se construyó este gemelo digital?")
        st.markdown(
            """
            <p style='text-align: justify;'>
            Llevar a cabo esta práctica en la planta piloto real presenta desafíos
            importantes: el tiempo limitado de laboratorio (típicamente entre 3 y 4 horas),
            los costos de la materia prima y la fragilidad de las membranas, que pueden
            perder selectividad ante cambios descontrolados de pH o presiones extremas.
            </p>
            <p style='text-align: justify;'>
            El Gemelo Digital soluciona esto al ofrecer un entorno virtual interactivo
            basado en datos reales de laboratorio obtenidos bajo la tutoría técnica del
            Profesor Mario.
            </p>
            """,
            unsafe_allow_html=True)

        st.subheader("Parámetros físicos del simulador")
        st.markdown(
            """
            <p style='text-align: justify;'>
            El modelo matemático que gobierna el comportamiento del gemelo digital está
            alimentado con las variables reales del laboratorio:
            </p>
            <ul>
            <li><b>Volumen de operación estándar:</b> 80 litros de lactosuero reconstituido
            en el tanque de alimentación.</li>
            <li><b>Densidad del fluido:</b> 1.026 g/cm³ (valor de densidad del lactosuero
            empleado para transformar pesos en volumen real).</li>
            <li><b>Área de transferencia:</b> 4.8 m² correspondientes al diseño físico de la
            membrana instalada.</li>
            </ul>
            """,
            unsafe_allow_html=True)

        st.subheader("Indicadores de desempeño calculados")
        st.markdown(
            """
            <p style='text-align: justify;'>
            El gemelo digital evalúa la eficiencia de la separación calculando en tiempo
            real:
            </p>
            <ol>
            <li><b>Factor de Concentración Volumétrica (FCV):</b> indicador del volumen
            concentrado final respecto al inicial, el cual suele rondar un valor de 1.5
            debido a la naturaleza de esta membrana de ultrafiltración adaptada.</li>
            <li><b>Coeficiente de Rechazo (R):</b> mide la selectividad de la membrana. En
            operación óptima de laboratorio se mantiene entre un 93% y 95%. Una caída
            drástica en este indicador en el gemelo digital simularía una ruptura física en
            el poro de la membrana.</li>
            </ol>
            """,
            unsafe_allow_html=True)
        st.caption(
            "Nota: estos valores de referencia (volumen, densidad, FCV y rechazo) "
            "corresponden a la descripción general del equipo y la práctica de "
            "laboratorio. Los parámetros que efectivamente usa el modelo matemático "
            "de la pestaña \"Simulación\" (K, J0, Kc, C0≈7.4 g/L) se ajustaron con "
            "los datos experimentales R:28/72 — ver la pestaña \"Guía de Usuario\" "
            "para el detalle. Si hay una relación directa entre unos y otros, se "
            "puede documentar aquí más adelante."
        )

    if st.session_state.infogen == "funcionamiento":
        st.markdown(
            """
            <p style='text-align: justify;'>
            El gemelo digital se compone de tres dimensiones interactivas que conectan la
            simulación con la práctica real de laboratorio:
            </p>
            """,
            unsafe_allow_html=True)

        st.markdown(
            """
            <p style='text-align: justify;'>
            <b>VER (El Tablero de Control):</b> el usuario interactúa con una réplica
            digital de los controles del equipo real (incluyendo el monitoreo de los
            manómetros de presión y el rotámetro de flujo).
            </p>
            """,
            unsafe_allow_html=True)

        st.markdown(
            """
            <p style='text-align: justify;'>
            <b>SIMULAR (Operación y Limpieza):</b> permite experimentar ciclos completos de
            ultrafiltración, así como simular las fases indispensables de lavado preventivo
            con agua (monitoreado virtualmente mediante la conductividad del sistema para
            verificar su limpieza) y los procesos de restauración química de la membrana
            mediante soluciones de soda cáustica para remover el fouling acumulado.
            </p>
            """,
            unsafe_allow_html=True)

        st.image(
            "Multimedia/Imagenes/historial_flux_curva_limpieza.png",
            caption="Historial de flux (tiempo vs. flux de permeado): curva de "
                    "decaimiento durante la concentración de lactosuero y "
                    "recuperación del flux tras la limpieza química",
            width="stretch",
        )

        st.markdown(
            """
            <p style='text-align: justify;'>
            <b>CONECTAR (Métodos de Medición del Laboratorio):</b> el gemelo digital ayuda
            a relacionar las variables del proceso con las técnicas analíticas reales que se
            usan en planta, tales como el análisis cualitativo del paso de azúcares mediante
            Grados Brix (refractometría) y la determinación exacta del contenido de
            proteínas a través de espectrofotometría convencional (como el Método de
            Bradford).
            </p>
            """,
            unsafe_allow_html=True)

    if st.session_state.infogen == "ganas":
        st.markdown(
            """
            <p style='text-align: justify;'>
            El valor del gemelo digital cambia según quién lo utilice, pero en todos los
            casos busca reducir la distancia entre el conocimiento teórico y el
            comportamiento real del proceso de ultrafiltración.
            </p>
            """,
            unsafe_allow_html=True)

        st.subheader("Para los estudiantes")
        st.markdown(
            """
            <p style='text-align: justify;'>
            Acceso a un simulador de respuesta inmediata que condensa una práctica física
            de varias horas en una experiencia ágil. Permite experimentar con límites
            operativos, fallas simuladas y limpiezas en un entorno interactivo y
            completamente seguro.
            </p>
            """,
            unsafe_allow_html=True)

        st.subheader("Para los profesores")
        st.markdown(
            """
            <p style='text-align: justify;'>
            Una herramienta interactiva de visualización de datos de flujo para ilustrar
            fenómenos complejos como la colmatación de membranas, la teoría de
            transferencia de masa y la hidráulica de tuberías industriales.
            </p>
            """,
            unsafe_allow_html=True)

        st.subheader("Referencias bibliográficas mencionadas")
        st.markdown(
            """
            <p style='text-align: justify;'>
            El modelo y fundamentos físicos de permeabilidad y flujo de membranas
            utilizados en esta plataforma se rigen bajo la literatura de referencia global
            en el área:
            </p>
            <ol>
            <li>Baker, R. W. (2012). <i>Membrane technology and applications</i> (3rd ed.). John Wiley &amp; Sons.</li>
            <li>Grand View Research. (2022). <i>Membrane separation technology market size, share &amp; trends analysis report 2022–2030</i>. Grand View Research.</li>
            <li>Cheryan, M. (1998). <i>Ultrafiltration and microfiltration handbook</i> (2nd ed.). CRC Press.</li>
            <li>Meng, F., Chae, S. R., Drews, A., Kraume, M., Shin, H. S., &amp; Yang, F. (2017). Recent advances in membrane bioreactors. <i>Bioresource Technology, 122</i>, 27–36. <a href="https://doi.org/10.1016/j.biortech.2012.07.006" target="_blank">https://doi.org/10.1016/j.biortech.2012.07.006</a></li>
            <li>Hermia, J. (1982). Constant pressure blocking filtration laws. <i>Transactions of the Institution of Chemical Engineers, 60</i>, 183–187.</li>
            <li>Field, R. W., Wu, D., Howell, J. A., &amp; Gupta, B. B. (1995). Critical flux concept for microfiltration fouling. <i>Journal of Membrane Science, 100</i>(3), 259–272. <a href="https://doi.org/10.1016/0376-7388(94)00265-Z" target="_blank">https://doi.org/10.1016/0376-7388(94)00265-Z</a></li>
            <li>Grieves, M. (2014). <i>Digital twin: Manufacturing excellence through virtual factory replication</i>. White Paper. Florida Institute of Technology.</li>
            <li>Liao, Y., Deschamps, F., Loures, E. F. R., &amp; Ramos, L. F. P. (2017). Past, present and future of Industry 4.0. <i>International Journal of Production Research, 55</i>(12), 3609–3629. <a href="https://doi.org/10.1080/00207543.2017.1303864" target="_blank">https://doi.org/10.1080/00207543.2017.1303864</a></li>
            <li>Tao, F., Zhang, H., Liu, A., &amp; Nee, A. Y. C. (2019). Digital twin in industry: State-of-the-art. <i>IEEE Transactions on Industrial Informatics, 15</i>(4), 2405–2415. <a href="https://doi.org/10.1109/TII.2018.2873186" target="_blank">https://doi.org/10.1109/TII.2018.2873186</a></li>
            <li>Rebecchi, S., Bruni, G., &amp; Pagliani, M. (2022). Digital twin of a reverse osmosis plant. <i>Desalination, 532</i>, 115764. <a href="https://doi.org/10.1016/j.desal.2022.115764" target="_blank">https://doi.org/10.1016/j.desal.2022.115764</a></li>
            <li>Xiong, H., Liu, C., Zhang, W., &amp; Chen, S. (2022). Hybrid model for ultrafiltration membrane fouling prediction. <i>Journal of Membrane Science, 641</i>, 119914. <a href="https://doi.org/10.1016/j.memsci.2021.119914" target="_blank">https://doi.org/10.1016/j.memsci.2021.119914</a></li>
            <li>Jones, D., Snider, C., Nassehi, A., Yon, J., &amp; Hicks, B. (2020). Characterising the digital twin: A systematic literature review. <i>CIRP Journal of Manufacturing Science and Technology, 29</i>, 36–52.</li>
            <li>Rasheed, A., San, O., &amp; Kvamsdal, T. (2020). Digital twin: Values, challenges and enablers from a modeling perspective. <i>IEEE Access, 8</i>, 21980–22012.</li>
            <li>Vincent Vela, M. C., Álvarez Blanco, S., Lora García, J., &amp; Bergantiños Rodríguez, E. (2008). Fouling dynamics modelling in the ultrafiltration of PEGs. <i>Desalination, 222</i>, 451–456.</li>
            <li>Bacchin, P., Si-Hassen, D., Starov, V., Clifton, M. J., &amp; Aimar, P. (2002). A unifying model for concentration polarization, gel-layer formation and particle deposition in cross-flow membrane filtration. <i>Chemical Engineering Science, 57</i>, 77–91.</li>
            <li>Corbatón-Báguena, M. J., Álvarez-Blanco, S., &amp; Vincent-Vela, M. C. (2018). Evaluation of fouling resistances during the ultrafiltration of whey model solutions. <i>Journal of Cleaner Production, 172</i>, 358–367.</li>
            <li>Rinaldoni, A. N., Tarazaga, C. C., Campderrós, M. E., &amp; Pérez Padilla, A. (2009). Assessing performance of skim milk ultrafiltration by using technical parameters. <i>Journal of Food Engineering, 92</i>, 226–232.</li>
            <li>Niu, C., Li, X., Dai, R., &amp; Wang, Z. (2022). Artificial intelligence-incorporated membrane fouling prediction for membrane-based processes in the past 20 years: A critical review. <i>Water Research, 216</i>, 118299.</li>
            <li>Kovacs, D. J., Li, Z., Baetz, B. W., et al. (2022). Membrane fouling prediction and uncertainty analysis using machine learning. <i>Journal of Membrane Science, 660</i>, 120817.</li>
            <li>Fortunato, L., Lamprea, A. F., &amp; Leiknes, T. (2020). Evaluation of membrane fouling using online monitoring tools under non-steady state conditions in a membrane bioreactor treating municipal wastewater. <i>Journal of Membrane Science, 612</i>, 118396. <a href="https://doi.org/10.1016/j.memsci.2020.118396" target="_blank">https://doi.org/10.1016/j.memsci.2020.118396</a></li>
            <li>Lu, R., Boo, C., Gao, D., Esfahani, M. R., Lee, G., Elimelech, M., &amp; Bhattacharya, S. (2023). Digital twin-assisted real-time fouling diagnosis and control in membrane-based water treatment. <i>Environmental Science &amp; Technology, 57</i>(12), 4875–4886. <a href="https://doi.org/10.1021/acs.est.2c07382" target="_blank">https://doi.org/10.1021/acs.est.2c07382</a></li>
            <li>Hoyer, M., Galier, S., &amp; Balmann, H. R. (2021). Ultrafiltration of complex mixtures: Impact of operating conditions on fouling mechanisms and membrane resistance. <i>Separation and Purification Technology, 275</i>, 119181. <a href="https://doi.org/10.1016/j.seppur.2021.119181" target="_blank">https://doi.org/10.1016/j.seppur.2021.119181</a></li>
            <li>Meng, S., Winters, H., Liu, Y., &amp; Han, J. (2022). Critical flux and fouling mechanism in ultrafiltration of protein solutions under varying transmembrane pressure. <i>Journal of Membrane Science, 643</i>, 120031. <a href="https://doi.org/10.1016/j.memsci.2021.120031" target="_blank">https://doi.org/10.1016/j.memsci.2021.120031</a></li>
            </ol>
            """,
            unsafe_allow_html=True)

    st.write("### ¿Le interesa lo que estamos construyendo?")
    st.markdown(
        """
        <p style='text-align: justify;'>
        Lo que se desarrolló es una herramienta sencilla de usar, pero sólida en su fundamento: se
        apoya en relaciones físicas y estadísticas consistentes (balance de materia, modelos de
        Hermia, criterios de selección de modelos), se estructura de forma modular en Python y
        está pensada para alojarse en una página web de acceso libre.
        </p>
        """,
        unsafe_allow_html=True)
    st.markdown(
        """
        <p style='text-align: justify;'><b>Dirección del proyecto</b></p>
        <p style='text-align: justify;'>
        Mario Andrés Noriega Valencia<br>
        Profesor Asociado<br>
        Coordinador de Laboratorios de la Facultad de Ingeniería<br>
        Departamento de Ingeniería Química y Ambiental<br>
        Universidad Nacional de Colombia – Sede Bogotá<br>
        E-mail: <a href="mailto:manoriegava@unal.edu.co">manoriegava@unal.edu.co</a>
        </p>
        <p style='text-align: justify;'><b>Desarrollo</b></p>
        <p style='text-align: justify;'>
        Valery Alejandra Gómez Estupiñán<br>
        Estudiante de Ingeniería Química<br>
        Universidad Nacional de Colombia – Sede Bogotá<br>
        E-mail: <a href="mailto:vgomeze@unal.edu.co">vgomeze@unal.edu.co</a>
        </p>
        """,
        unsafe_allow_html=True)


def simulacion():
    st.write("# Simulación")
    st.markdown(
        "Modelo del proceso de ultrafiltración ajustado con datos experimentales "
        "**R:28/72**. Elige qué fluido se hace circular por la membrana, define "
        "las condiciones de operación y observa los resultados."
    )

    st.divider()

    col_in, col_out = st.columns([1, 2])

    with col_in:
        st.subheader("Fluido a circular por la membrana")

        fluido = st.radio(
            "Selecciona el experimento",
            options=[
                "Lactosuero — proceso de concentración de proteína",
                "Agua — limpieza / línea base de resistencia (sin proteína)",
            ],
            help=(
                "Lactosuero: simula el proceso real de ultrafiltración, con caída "
                "de flux por ensuciamiento y concentración creciente de proteína. "
                "Agua: simula la corrida de agua pura que se usa para medir la "
                "resistencia propia de la membrana (R_M); al no haber proteína, "
                "no hay formación de torta ni concentración que calcular."
            ),
        )
        es_agua = fluido.startswith("Agua")

        st.subheader("Condiciones de operación")

        if es_agua:
            estado_membrana = st.radio(
                "Estado de la membrana al iniciar la circulación de agua",
                options=[
                    "Limpia — tras limpieza química completa (línea base)",
                    "Recién usada con lactosuero — enjuague, sin limpieza química",
                ],
                help=(
                    "Limpia: el flux de agua se mantiene constante en el valor "
                    "de línea base (ver PDF: el ensuciamiento se consideró "
                    "reversible tras limpieza). Recién usada: la torta de "
                    "proteína sigue físicamente presente, así que el flux "
                    "arranca bajo y se recupera con el tiempo a medida que el "
                    "enjuague la va arrastrando."
                ),
            )
            es_enjuague = estado_membrana.startswith("Recién usada")

            if es_enjuague:
                st.warning(
                    "⚠️ No contamos con datos experimentales de la curva de "
                    "recuperación de flux durante un enjuague sin limpieza "
                    "química. La curva que se muestra es una **aproximación "
                    "ilustrativa** (recuperación exponencial hacia el flux de "
                    "agua limpia), no una predicción validada — trátala solo "
                    "como tendencia cualitativa esperada."
                )
                J_inicio_enjuague = st.number_input(
                    "Flux justo antes de cambiar a agua (L/m2 h) — el último "
                    "flux del lactosuero",
                    min_value=0.1, max_value=float(PARAMS["J_agua"]),
                    value=float(PARAMS["Jinf_exp"]), step=0.1,
                )
            else:
                J_inicio_enjuague = None

            st.info(
                "💧 Con agua pura no hay proteína que retener ni que "
                "concentrar: no aplican el modelo de concentración C(t) ni "
                "los modelos de ensuciamiento (Hermia/exponencial) usados "
                "para lactosuero."
            )
            C0 = None
            modelo_flux = None
        else:
            C0 = st.number_input(
                "Concentración inicial de proteína en el tanque, C0 (g/L)",
                min_value=0.1, max_value=100.0,
                value=float(PARAMS["C0_valido"]), step=0.1,
            )

        t_final = st.number_input(
            "Tiempo total de proceso a simular, t_final (min)",
            min_value=1, max_value=300,
            value=int(PARAMS["t_max_valido"]), step=1,
        )

        dt = st.number_input(
            "Paso de tiempo para la tabla de resultados, Δt (min)",
            min_value=1, max_value=30, value=2, step=1,
        )

        if not es_agua:
            modelo_flux = st.radio(
                "Modelo de flux de permeado a utilizar",
                options=["Hermia n=0 (formación de torta) — recomendado dentro del rango medido (0-40 min)",
                         "Exponencial empírico — recomendado para proyectar tiempos largos"],
            )

            fuera_rango = (t_final > PARAMS["t_max_valido"]) or (
                abs(C0 - PARAMS["C0_valido"]) / PARAMS["C0_valido"] > 0.30)

            if fuera_rango:
                st.info(
                    "ℹ️ Estás proyectando fuera del rango medido en laboratorio "
                    f"(t = 0–{PARAMS['t_max_valido']} min, C0 ≈ {PARAMS['C0_valido']} g/L). "
                    "El modelo **sí calcula el resultado igualmente** — esto es una "
                    "extrapolación, así que trátala como una proyección orientativa, no "
                    "como un dato verificado experimentalmente. Para proyectar tiempos "
                    "largos, el modelo **exponencial** es más confiable porque tiene un "
                    "flux mínimo físico (J∞); el modelo de torta puede seguir bajando "
                    "de forma poco realista si te alejas mucho del rango medido."
                )

        simular = st.button("Simular", width="stretch")

    if simular:
        t = np.arange(0, t_final + dt, dt)

        if es_agua:
            if es_enjuague:
                J_t = modelo_J_enjuague(t, J_inicio_enjuague)
            else:
                J_t = modelo_J_agua(t)
            C_t = None
        else:
            C_t = modelo_C(t, C0)
            if modelo_flux.startswith("Hermia"):
                J_t = modelo_J_torta(t)
            else:
                J_t = modelo_J_exp(t)

        Vp_t = np.concatenate(([0], np.cumsum(
            ((J_t[:-1] + J_t[1:]) / 2) * PARAMS["A_M"] * (np.diff(t) / 60)
        )))  # integración trapezoidal simple, J en L/m2h -> t en h

        if es_agua:
            col_j = "J agua — enjuague (L/m2 h)" if es_enjuague else "J agua — limpia (L/m2 h)"
            df = pd.DataFrame({
                "t (min)": t,
                col_j: J_t,
                "Vol. permeado acumulado (L)": Vp_t,
            })
        else:
            df = pd.DataFrame({
                "t (min)": t,
                "C tanque (g/L)": C_t,
                "J permeado (L/m2 h)": J_t,
                "Vol. permeado acumulado (L)": Vp_t,
            })

        with col_out:
            st.subheader("Resultados de la simulación")

            if not es_agua:
                fig1, ax1 = plt.subplots()
                ax1.plot(t, C_t, marker="o", color="#1f4e78")
                if t_final > PARAMS["t_max_valido"]:
                    ax1.axvspan(PARAMS["t_max_valido"], t_final, color="orange", alpha=0.08)
                    ax1.axvline(PARAMS["t_max_valido"], color="orange", linestyle="--", linewidth=1)
                    ax1.text(PARAMS["t_max_valido"], ax1.get_ylim()[1]*0.98, " proyección →",
                              color="darkorange", fontsize=8, va="top")
                ax1.set_xlabel("Tiempo (min)")
                ax1.set_ylabel("C tanque (g/L)")
                ax1.set_title("Concentración de proteína en el tanque")
                ax1.grid(alpha=0.3)
                st.pyplot(fig1)

            fig2, ax2 = plt.subplots()
            color_flux = "#2e86ab" if es_agua else "#c00000"
            ax2.plot(t, J_t, marker="o", color=color_flux)
            if es_agua:
                ax2.set_ylim(0, max(PARAMS["J_agua"], max(J_t)) * 1.15)
            if (not es_agua) and t_final > PARAMS["t_max_valido"]:
                ax2.axvspan(PARAMS["t_max_valido"], t_final, color="orange", alpha=0.08)
                ax2.axvline(PARAMS["t_max_valido"], color="orange", linestyle="--", linewidth=1)
                ax2.text(PARAMS["t_max_valido"], ax2.get_ylim()[1]*0.98, " proyección →",
                          color="darkorange", fontsize=8, va="top")
            ax2.set_xlabel("Tiempo (min)")
            ax2.set_ylabel("J (L/m2 h)")
            if es_agua:
                titulo_flux = ("Flux de agua — recuperación por enjuague (estimación ilustrativa)"
                                if es_enjuague else "Flux de agua (membrana limpia, sin ensuciamiento)")
            else:
                titulo_flux = "Flux de permeado"
            ax2.set_title(titulo_flux)
            ax2.grid(alpha=0.3)
            st.pyplot(fig2)

            st.subheader("Resumen")
            if es_agua:
                colr1, colr2, colr3 = st.columns(3)
                if es_enjuague:
                    colr1.metric("J inicial (L/m2 h)", f"{J_t[0]:.2f}")
                    colr2.metric("J final (L/m2 h)", f"{J_t[-1]:.2f}")
                    colr3.metric("Volumen permeado total (L)", f"{Vp_t[-1]:.1f}")
                    st.caption(
                        "Curva ilustrativa, no ajustada a datos experimentales "
                        "(ver advertencia arriba). Con limpieza química, en "
                        "cambio, el flux se comporta como una línea base "
                        "constante — pruébalo eligiendo 'Limpia' arriba."
                    )
                else:
                    colr1.metric("J de agua (L/m2 h)", f"{J_t[0]:.2f}")
                    colr2.metric("Volumen permeado total (L)", f"{Vp_t[-1]:.1f}")
                    colr3.metric("Resistencia de membrana, R_M", "1.09×10¹³ m⁻¹")
                    st.caption(
                        "El flux de agua se mantiene constante porque, según "
                        "nuestros datos, tras una limpieza química el "
                        "ensuciamiento es reversible — este es justamente el "
                        "flux que se usó para calcular la resistencia "
                        "intrínseca de la membrana (R_M) en la Hoja \"Modelo\" "
                        "del Excel."
                    )
            else:
                colr1, colr2, colr3, colr4 = st.columns(4)
                colr1.metric("C final (g/L)", f"{C_t[-1]:.2f}")
                colr2.metric("Factor Cf/C0", f"{C_t[-1]/C0:.2f}")
                colr3.metric("J final (L/m2 h)", f"{J_t[-1]:.2f}")
                colr4.metric("J promedio (L/m2 h)", f"{np.mean(J_t):.2f}")

            st.subheader("Tabla de resultados")
            st.dataframe(df, width="stretch")

            csv = df.to_csv(index=False).encode("utf-8")
            if es_agua:
                nombre_archivo = "simulacion_agua_enjuague.csv" if es_enjuague else "simulacion_agua_limpia.csv"
            else:
                nombre_archivo = "simulacion_lactosuero.csv"
            st.download_button(
                "📥 Descargar resultados (CSV)", data=csv,
                file_name=nombre_archivo, mime="text/csv",
                width="stretch",
            )
    else:
        with col_out:
            st.info("Define el fluido y las condiciones de operación, y presiona "
                    "**Simular** para ver los resultados.")


def documentacion():
    import os
    import glob
    st.write("# Documentación")

    # Carpeta del manual (PDF)
    CARPETA_DOCS = r"C:\Users\valer\Downloads\UF\Multimedia\Documentacion"
    # Carpeta de los diagramas de flujo (imágenes)
    CARPETA_IMAGENES = r"C:\Users\valer\Downloads\UF\Multimedia\Imagenes"

    # El manual se busca por su nombre base, sin depender de la extensión exacta.
    # Esto evita problemas cuando Windows oculta la extensión o el nombre termina
    # en un punto (p. ej. "Manual_Ultrafiltracion_Lactosuero..pdf").
    NOMBRE_BASE_MANUAL = "Manual_Ultrafiltracion_Lactosuero"

    NOMBRES_DIAGRAMAS = [
        "diagrama_flujo_1.png",
        "diagrama_flujo_2.png",
        "diagrama_flujo_3.png",
    ]

    def buscar_manual():
        """Devuelve la ruta del manual buscándolo por nombre base en la carpeta."""
        if not os.path.isdir(CARPETA_DOCS):
            return None
        patron = os.path.join(CARPETA_DOCS, NOMBRE_BASE_MANUAL + "*")
        coincidencias = glob.glob(patron)
        return coincidencias[0] if coincidencias else None

    if "doc_actual" not in st.session_state:
        st.session_state.doc_actual = None

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Manual de Operación", width="stretch"):
            st.session_state.doc_actual = "manual"

    with col2:
        if st.button("Diagramas de Flujo", width="stretch"):
            st.session_state.doc_actual = "diagramas"

    if st.session_state.doc_actual is None:
        st.info(
            "📄 Aquí encontrarás la documentación técnica del equipo de "
            "ultrafiltración: el **Manual de Operación** (PDF descargable con "
            "el procedimiento paso a paso) y los **Diagramas de Flujo** del "
            "proceso (preparación del lactosuero, purga/limpieza de líneas y "
            "procedimiento de la práctica). Elige una de las dos opciones de "
            "arriba para verla."
        )

    elif st.session_state.doc_actual == "manual":
        ruta_manual = buscar_manual()
        if ruta_manual:
            with open(ruta_manual, "rb") as f:
                pdf_bytes = f.read()
            try:
                st.pdf(pdf_bytes)
            except Exception:
                st.info(
                    "El visor de PDF integrado no está disponible en esta "
                    "instalación. Puedes descargar el manual con el botón de "
                    "abajo. (Para verlo aquí mismo, instala el componente con: "
                    "pip install \"streamlit[pdf]\")"
                )
            nombre_descarga = os.path.basename(ruta_manual)
            if not nombre_descarga.lower().endswith(".pdf"):
                nombre_descarga = NOMBRE_BASE_MANUAL + ".pdf"
            st.download_button(
                label="📥 Descargar Manual (PDF)",
                data=pdf_bytes,
                file_name=nombre_descarga,
                mime="application/pdf",
                width="stretch"
            )
        else:
            st.warning(
                f"No se encontró ningún archivo que empiece por "
                f"'{NOMBRE_BASE_MANUAL}' en la carpeta:\n\n{CARPETA_DOCS}"
            )
            if os.path.isdir(CARPETA_DOCS):
                st.caption("Archivos que sí hay en esa carpeta:")
                st.code("\n".join(os.listdir(CARPETA_DOCS)) or "(carpeta vacía)")
            else:
                st.caption("La carpeta indicada no existe o no es accesible.")

    elif st.session_state.doc_actual == "diagramas":

        st.subheader("Diagramas de flujo del proceso")

        ancho_img = st.slider("Tamaño de las imágenes (px)", 300, 1000, 600, 50)

        faltantes = []

        NOMBRES_CAPTIONS = [
            "Diagrama de preparación del lactosuero",
            "Diagrama del proceso de purga y limpieza de las líneas de rechazo y permeado",
            "Diagrama de procedimiento de la práctica."
        ]

        for i, nombre in enumerate(NOMBRES_DIAGRAMAS):
            ruta = os.path.join(CARPETA_IMAGENES, nombre)

            if os.path.exists(ruta):
                st.image(
                    ruta,
                    caption=NOMBRES_CAPTIONS[i],
                    width=ancho_img
                )
            else:
                faltantes.append(nombre)

        if faltantes:
            st.warning("No se encontraron estas imágenes en "
                    f"{CARPETA_IMAGENES}:\n\n- " + "\n- ".join(faltantes))

            if os.path.isdir(CARPETA_IMAGENES):
                st.caption("Archivos que sí hay en esa carpeta:")
                st.code("\n".join(os.listdir(CARPETA_IMAGENES)) or "(carpeta vacía)")
            else:
                st.caption("La carpeta de imágenes no existe o no es accesible.")

def guia_usuario():
    st.write("# Guía de Usuario")
    st.write("## Características y guía de operación del proceso")
    st.video("https://youtu.be/Zs4_z36NaH8")

    st.divider()

    st.subheader("Fundamento teórico de la simulación")

    st.markdown(r"""
    ### Modelo de concentración en el tanque (balance por lotes)

    La simulación de la variable de estado $C(t)$ se basa en un balance de materia
    integrado sobre el tanque de alimentación, asumiendo que la cantidad de proteína
    que atraviesa la membrana tiende a cero (rechazo casi total).

    Partiendo de la Ley de Darcy y de la definición de concentración, se obtiene:

    $$
    \frac{1}{C(t)} - \frac{1}{C_0} = -K \cdot t
    $$

    donde:

    - $C(t)$: concentración de proteína en el tanque en el tiempo $t$ [g/L]
    - $C_0$: concentración inicial de proteína [g/L]
    - $K$: constante cinética del balance, agrupa presión, viscosidad, resistencias
      de la membrana y área efectiva [L/g·min]
    - $t$: tiempo de proceso [min]

    $K$ se estimó por regresión lineal (mínimos cuadrados) sobre los datos
    experimentales R:28/72, excluyendo un punto identificado como atípico
    (t = 8 min), obteniendo:

    $$
    K \approx 0.00127 \ \text{(g/L)}^{-1}\text{min}^{-1} \qquad R^2 = 0.972
    $$
    """)

    st.markdown(r"""
    ### Modelo de flux de permeado (ensuciamiento / fouling)

    El flux de permeado $J(t)$ se modeló utilizando los modelos clásicos de Hermia
    para ensuciamiento de membranas. Se evaluaron los cuatro mecanismos (bloqueo
    completo, bloqueo estándar, bloqueo intermedio y formación de torta), además de
    un modelo empírico exponencial y una ley potencial.

    **Modelo recomendado — Hermia n = 0 (formación de torta):**

    $$
    J(t) = \left[\frac{1}{J_0^{2}} + 2 K_c \cdot t \right]^{-0.5}
    $$

    Se seleccionó por representar un mecanismo físicamente coherente con la
    formación de una capa de proteína sobre la membrana (torta/gel), con buen
    ajuste estadístico ($R^2 = 0.994$) y comportamiento extrapolable razonable.

    **Modelo alternativo — Exponencial empírico:**

    $$
    J(t) = J_\infty + (J_0 - J_\infty)\, e^{-k \cdot t}
    $$

    con interpretación directa: $J_0$ el flux inicial, $J_\infty$ el flux al que se
    estabiliza el sistema, y $k$ la velocidad con que ocurre esa caída.

    Todos los parámetros se estimaron por regresión no lineal (mínimos cuadrados)
    sobre los 5 puntos experimentales de flux disponibles (t = 8 a 40 min).
    """)

    st.markdown(r"""
    ### Por qué no se usó el modelo de mejor ajuste estadístico

    Un modelo de tipo ley potencial ($J = a\cdot t^{-b}$) obtuvo el mejor ajuste
    estadístico ($R^2 = 0.999$), pero se descartó como base del gemelo digital por
    no tener un límite físico razonable ($J\to\infty$ cuando $t\to 0$, y $J\to 0$
    cuando $t\to\infty$), lo que lo hace poco confiable para extrapolar fuera del
    rango experimental medido.
    """)

    st.markdown(r"""
    ### Limitaciones del modelo actual

    - Ajustado con un único nivel de presión transmembranal; no se puede separar
      de forma independiente la polarización por concentración del ensuciamiento.
    - No se dispone de mediciones directas de resistencia de membrana en función
      del tiempo (solo estimable indirectamente a partir del flux).

   
    """)


def datos():
    st.write("# Sube tus Datos")
    st.markdown(
        "Si cuentas con datos experimentales propios de ultrafiltración (otra "
        "relación de rechazo, otra membrana u otras condiciones), puedes usarlos "
        "para complementar o recalibrar el modelo."
    )

    practica = st.selectbox(
        "Seleccione el tipo de datos con el cual va a alimentar el Gemelo Digital:",
        [
            "Ultrafiltración - Relación de rechazo R:28/72",
            "Ultrafiltración - Otra configuración (POR DEFINIR)",
        ]
    )

    ejemplo = pd.DataFrame({
        "Tiempo (min)": [0, 8, 16, 24, 32, 40, "..."],
        "Masa de Permeado (kg)": [0, "...", "...", "...", "...", "...", "..."],
        "Masa de Rechazo (kg)": [0, "...", "...", "...", "...", "...", "..."],
        "Absorbancia Permeado (u.a.)": ["-", "...", "...", "...", "...", "...", "..."],
        "Absorbancia Rechazo (u.a.)": ["-", "...", "...", "...", "...", "...", "..."],
        "Absorbancia Tanque (u.a.)": ["...", "...", "...", "...", "...", "...", "..."],
    })

    st.write("### Ejemplo del formato esperado")
    st.table(ejemplo)
    st.caption(
        "Formato basado en la estructura de la Hoja 1 ('R 28-72') del archivo Excel "
        "del modelo. Se recomiendan al menos 3 réplicas por variable y por tiempo."
    )

    st.subheader("1. Descarga la plantilla")
    st.markdown(
        "Descarga este Excel, complétalo (integrantes del grupo, fecha, profesor a "
        "cargo y los datos medidos) y luego súbelo en el paso 2. Las celdas amarillas "
        "son las únicas que debes llenar; las grises ya traen las fórmulas de Volumen, "
        "Flujo, Flux y Concentración calculadas automáticamente."
    )
    plantilla_bytes = generar_plantilla_excel()
    st.download_button(
        "📥 Descargar plantilla de Excel",
        data=plantilla_bytes,
        file_name="Plantilla_Carga_Datos_UF.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )

    st.subheader("2. Sube tu archivo ya completado")

    st.markdown(
        "**Identifícate antes de subir el archivo.** Esto permite llevar control "
        "de quién realiza ensayos en el equipo y recibir una alerta por correo "
        "cada vez que se suben datos nuevos."
    )

    # "form_datos_version" se usa como sufijo de las keys de los campos del
    # formulario. Al incrementarlo después de un envío exitoso y volver a
    # correr la página (st.rerun), Streamlit crea widgets nuevos (vacíos) en
    # vez de reutilizar los que tenían texto/archivo cargado. Así el
    # formulario queda limpio (nombre, correo, archivo y observaciones)
    # después de presionar "Subir reporte final".
    if "form_datos_version" not in st.session_state:
        st.session_state.form_datos_version = 0
    v = st.session_state.form_datos_version

    nombre_usuario = st.text_input(
        "Nombre completo de quien realiza la carga",
        placeholder="Ej: Alejandra Jimenez ",
        key=f"nombre_usuario_{v}"
    )
    correo_usuario = st.text_input(
        "Correo electrónico (para avisarte si tu práctica es aprobada o rechazada)",
        placeholder="Ej: alejandra.jimenez@unal.edu.co",
        key=f"correo_usuario_{v}"
    )

    archivo = st.file_uploader(
        "Sube un archivo CSV o Excel con tus datos",
        type=["csv", "xlsx"],
        key=f"archivo_{v}"
    )

    observaciones = st.text_area(
        "Observaciones o anomalías detectadas durante la práctica",
        placeholder="Ej: A los 24 min se observó una caída brusca de presión, "
                    "el rotámetro marcó valores inestables, se cambió el filtro...",
        key=f"observaciones_{v}"
    )

    st.caption(
        "Los datos NO se suben ni se envían hasta que presiones el botón "
        "'Subir reporte final'."
    )
    enviar = st.button("📤 Subir reporte final", key=f"btn_subir_{v}")

    if enviar:
        if not nombre_usuario.strip():
            st.warning("Por favor ingresa tu nombre antes de subir el reporte final.")
        elif not correo_usuario.strip() or "@" not in correo_usuario:
            st.warning("Por favor ingresa un correo electrónico válido antes de subir el reporte final.")
        elif archivo is None:
            st.warning("Por favor selecciona un archivo antes de subir el reporte final.")
        else:
            st.success("Archivo recibido. POR COMPLETAR: lógica de lectura, validación y "
                       "re-ajuste automático de los parámetros del modelo con estos datos.")

            guardar_nuevo_registro(
                nombre=nombre_usuario.strip(),
                correo=correo_usuario.strip(),
                tipo_practica=practica,
                archivo_nombre=archivo.name,
                tamano_bytes=archivo.size,
                observaciones=observaciones.strip(),
            )

            enviado, error = enviar_notificacion_carga(
                nombre_usuario=nombre_usuario.strip(),
                tipo_practica=practica,
                nombre_archivo=archivo.name,
                tamano_bytes=archivo.size,
                adjuntar_archivo=archivo,
                observaciones=observaciones.strip(),
            )
            if enviado:
                st.info(f"Se notificó por correo la carga realizada por **{nombre_usuario}**. "
                        f"Queda pendiente de aprobación (ver abajo).")
            else:
                st.caption(f"No se pudo enviar la notificación por correo: {error}")

            # Reinicia el formulario: nombre, correo, archivo y observaciones
            # quedan vacíos de nuevo.
            st.session_state.form_datos_version += 1
            st.rerun()

    # =========================================================================
    # HISTORIAL PÚBLICO (visible para cualquiera, sin contraseña)
    # =========================================================================
    st.divider()
    st.subheader("📋 Historial de prácticas registradas")
    st.caption("Consulta pública: quién registró datos y si ya fue aprobado o rechazado.")

    df_historial = cargar_registros()
    if df_historial.empty:
        st.write("Todavía no hay ninguna práctica registrada.")
    else:
        vista = df_historial[["nombre", "tipo_practica", "fecha", "estado"]].sort_values(
            "fecha", ascending=False
        )
        st.dataframe(vista, width="stretch", hide_index=True)

    # =========================================================================
    # PANEL DE APROBACIÓN (protegido con contraseña)
    # =========================================================================
    st.divider()

    if "autenticado_admin" not in st.session_state:
        st.session_state.autenticado_admin = False

    if not st.session_state.autenticado_admin:
        with st.expander("🔒 Ingresar como administrador para aprobar/rechazar prácticas"):
            clave = st.text_input("Contraseña de administrador", type="password", key="clave_admin_datos")
            if st.button("Ingresar", key="btn_ingresar_admin_datos"):
                try:
                    clave_correcta = st.secrets["admin"]["password"]
                except Exception:
                    st.error(
                        "No se ha configurado la contraseña de administrador. "
                        "Agrega una sección [admin] con 'password' en secrets.toml."
                    )
                else:
                    if clave == clave_correcta:
                        st.session_state.autenticado_admin = True
                        st.rerun()
                    else:
                        st.error("Contraseña incorrecta.")
    else:
        st.subheader("✅ Panel de aprobación")

        if st.button("Cerrar sesión de administrador", key="btn_cerrar_admin_datos"):
            st.session_state.autenticado_admin = False
            st.rerun()

        df_pend = cargar_registros()
        pendientes = df_pend[df_pend["estado"] == "Pendiente"]

        if pendientes.empty:
            st.write("No hay prácticas pendientes por revisar en este momento.")
        else:
            for indice, fila in pendientes.iterrows():
                with st.container(border=True):
                    col_info, col_aprobar, col_rechazar = st.columns([4, 1, 1])
                    with col_info:
                        obs = fila.get("observaciones", "")
                        obs = "" if pd.isna(obs) else str(obs)
                        st.markdown(
                            f"**{fila['nombre']}** — {fila['tipo_practica']}  \n"
                            f"Archivo: `{fila['archivo']}` ({fila['tamano_kb']} KB)  \n"
                            f"Fecha: {fila['fecha']}  \n"
                            f"Observaciones: {obs if obs.strip() else '_(sin observaciones)_'}"
                        )
                    with col_aprobar:
                        if st.button("✅ Aprobar", key=f"aprobar_{indice}"):
                            actualizar_estado_registro(indice, "Aprobado")
                            enviado, error = enviar_notificacion_decision(
                                correo_destino=fila["correo"],
                                nombre_usuario=fila["nombre"],
                                tipo_practica=fila["tipo_practica"],
                                decision="Aprobado",
                            )
                            if not enviado:
                                st.caption(f"(No se pudo avisar por correo: {error})")
                            st.rerun()
                    with col_rechazar:
                        if st.button("❌ Rechazar", key=f"rechazar_{indice}"):
                            actualizar_estado_registro(indice, "Rechazado")
                            enviado, error = enviar_notificacion_decision(
                                correo_destino=fila["correo"],
                                nombre_usuario=fila["nombre"],
                                tipo_practica=fila["tipo_practica"],
                                decision="Rechazado",
                            )
                            if not enviado:
                                st.caption(f"(No se pudo avisar por correo: {error})")
                            st.rerun()


def encuesta():
    st.write("# Encuesta de Percepción")

    st.markdown(
        "Esta encuesta busca conocer tu opinión sobre la página web, el contenido técnico, "
        "el video de operación y la simulación interactiva desarrollados como herramienta "
        "pedagógica de apoyo para los laboratorios del **Departamento de Ingeniería Química y Ambiental** "
        "(Universidad Nacional de Colombia, Sede Bogotá).\n\n"
        "Tus respuestas son completamente **anónimas** y completarla te tomará aproximadamente **5 a 7 minutos**."
    )

    st.info(
        "📌 **¿Cuándo puedes usar esta herramienta y cómo responder la encuesta?**\n\n"
        "• **Para familiarizarte con el equipo:** Este Gemelo Digital es ideal para utilizarlo **antes de la práctica presencial**, "
        "permitiéndote conocer el equipo real de nuestra planta piloto y sus variables de operación.\n\n"
        "• **Si ya realizaste la práctica de laboratorio sin haber usado previamente esta herramienta:** "
        "¡No hay problema! Tómate unos minutos para explorar la plataforma web, revisar los diagramas y probar la "
        "simulación ahora, y responde la encuesta pensando en qué tanto te habría servido como apoyo en su momento."
    )

    # Reemplaza la URL con el enlace de tu Google Form embebido
    url_google_form = "https://forms.gle/GarYoFZff6R8iKNz9"
    st.components.v1.iframe(url_google_form, height=800, scrolling=True)
# =============================================================================
# MENÚ DE NAVEGACIÓN
# =============================================================================

import base64, os
import streamlit.components.v1 as components

def _logo_base64(ruta):
    if os.path.exists(ruta):
        with open(ruta, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

_logo_color_b64 = _logo_base64("Multimedia/Imagenes/logo_unal_color.png")
_logo_blanco_b64 = _logo_base64("Multimedia/Imagenes/logo_unal_blanco.png")

if _logo_color_b64 and _logo_blanco_b64:
    with st.sidebar:
        components.html(
            f"""
            <div style="width:100%;">
                <img id="logo-color" src="data:image/png;base64,{_logo_color_b64}"
                     style="width:100%; display:block;" />
                <img id="logo-blanco" src="data:image/png;base64,{_logo_blanco_b64}"
                     style="width:100%; display:none;" />
            </div>
            <script>
            function actualizarLogoUNAL() {{
                try {{
                    const doc = window.parent.document;
                    const contenedor = doc.querySelector('.stApp') || doc.body;
                    const bg = window.parent.getComputedStyle(contenedor).backgroundColor;
                    const valores = bg.match(/\\d+/g);
                    let oscuro = false;
                    if (valores) {{
                        const r = parseInt(valores[0]), g = parseInt(valores[1]), b = parseInt(valores[2]);
                        const luminancia = 0.299*r + 0.587*g + 0.114*b;
                        oscuro = luminancia < 128;
                    }}
                    document.getElementById('logo-color').style.display = oscuro ? 'none' : 'block';
                    document.getElementById('logo-blanco').style.display = oscuro ? 'block' : 'none';
                }} catch (e) {{ /* si algo falla, se queda con el logo de color por defecto */ }}
            }}
            actualizarLogoUNAL();
            setInterval(actualizarLogoUNAL, 600);
            </script>
            """,
            height=130,
        )
elif _logo_color_b64 or _logo_blanco_b64:
    st.sidebar.image(
        "Multimedia/Imagenes/logo_unal_color.png" if _logo_color_b64
        else "Multimedia/Imagenes/logo_unal_blanco.png",
        width="stretch",
    )
else:
    st.sidebar.info(
        "POR COMPLETAR: logo institucional. Guarda 'logo_unal_color.png' y "
        "'logo_unal_blanco.png' en Multimedia/Imagenes/."
    )

st.sidebar.write("## Menú de Navegación")

if st.sidebar.button("Inicio", width="stretch"):
    st.session_state.pagina = "inicio"
if st.sidebar.button("Información General", width="stretch"):
    st.session_state.pagina = "informacion_general"
if st.sidebar.button("Simulación", width="stretch"):
    st.session_state.pagina = "Simulación"
if st.sidebar.button("Documentación", width="stretch"):
    st.session_state.pagina = "Documentacion"
if st.sidebar.button("Guía de Usuario", width="stretch"):
    st.session_state.pagina = "Guia de Usuario"
if st.sidebar.button("Sube tus Datos", width="stretch"):
    st.session_state.pagina = "datos"
if st.sidebar.button("Encuesta de Percepción", width="stretch"):
    st.session_state.pagina = "encuesta"

# --- Imagen del equipo de ultrafiltración, al final del menú lateral ---
if os.path.exists("Multimedia/Imagenes/equipo_UF.png"):
    st.sidebar.image(
        "Multimedia/Imagenes/equipo_UF.png",
        caption="Equipo de Ultrafiltración",
        width="stretch",
    )


# =============================================================================
# ENRUTADOR DE PÁGINAS
# =============================================================================

if st.session_state.pagina == "inicio":
    inicio()
elif st.session_state.pagina == "informacion_general":
    informacion_general()
elif st.session_state.pagina == "Simulación":
    simulacion()
elif st.session_state.pagina == "Documentacion":
    documentacion()
elif st.session_state.pagina == "Guia de Usuario":
    guia_usuario()
elif st.session_state.pagina == "datos":
    datos()
elif st.session_state.pagina == "encuesta":
    encuesta()