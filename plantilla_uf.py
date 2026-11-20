# plantilla_uf.py
# Construye en memoria la plantilla de Excel que los grupos descargan, llenan en
# el laboratorio y suben en "Sube tus Datos".
#
# Criterios de diseño:
#   - La condición de operación se registra como lo que el estudiante HACE en el
#     equipo: la VUELTA de la válvula roja trasera (V9). La relación
#     permeado/rechazo (p. ej. 28/72 = 28 % del caudal sale como permeado y
#     72 % como rechazo) se calcula sola con la caracterización de la válvula
#     (Tabla 10 de la tesis).
#   - Los cálculos siguen la misma definición que se usó para ajustar el modelo
#     (hoja "R 28-72"): flux = volumen acumulado de permeado / tiempo / área, y
#     el peso del tanque de alimentación se registra bruto y se le resta la tara.
#   - Las celdas clave tienen NOMBRES DEFINIDOS (p. ej. vuelta_V9, tabla_datos)
#     para que la app pueda leer el archivo de forma robusta.

import io

from openpyxl import Workbook
from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

# Caracterización de la válvula roja V9 (Tabla 10): vuelta → (% permeado, % rechazo)
TABLA_VALVULA = {0: (29, 71), 1: (29, 71), 2: (28, 72), 3: (26, 74), 4: (24, 76),
                 5: (22, 78), 6: (21, 79), 7: (20, 80), 8: (20, 80), 9: (20, 80)}

AZUL = "082E52"
AMARILLO = PatternFill("solid", fgColor="FFF2CC")
GRIS = PatternFill("solid", fgColor="E7E6E6")
ENCAB = PatternFill("solid", fgColor="082E52")
SUAVE = PatternFill("solid", fgColor="EAF2F8")
BORDE = Border(*(Side(style="thin", color="BFBFBF"),) * 4)
BLANCO_B = Font(bold=True, color="FFFFFF")
TIEMPOS = [0, 8, 16, 24, 32, 40, None, None, None, None]   # 4 filas libres por si se toman más tiempos


def descripcion_vuelta(v):
    p, r = TABLA_VALVULA[v]
    return f"Vuelta {v} → relación permeado/rechazo {p}/{r}"


def _nombre(wb, nombre, ref):
    wb.defined_names[nombre] = DefinedName(nombre, attr_text=ref)


def construir_plantilla():
    wb = Workbook()

    # ================================================================ INSTRUCCIONES
    ins = wb.active
    ins.title = "Instrucciones"
    ins.sheet_view.showGridLines = False
    ins.column_dimensions["A"].width = 2
    ins.column_dimensions["B"].width = 110
    filas = [
        ("PLANTILLA DE DATOS — GEMELO DIGITAL DE LA MEMBRANA DE ULTRAFILTRACIÓN", "titulo"),
        ("", None),
        ("Cómo llenarla", "sub"),
        ("1. Ve a la hoja 'Datos_Practica'. Llena SOLO las celdas AMARILLAS; las GRISES se calculan solas.", None),
        ("2. Escribe la VUELTA en que dejaste la válvula roja trasera (V9). La relación permeado/rechazo "
         "se calcula sola: por ejemplo, vuelta 2 = 28/72, es decir, 28 % del caudal sale como permeado "
         "y 72 % como rechazo.", None),
        ("3. Registra cada 8 minutos el peso ACUMULADO de permeado (báscula del tanque de permeado, "
         "descontando su tara) y el peso BRUTO del tanque de alimentación (como lo marca su báscula).", None),
        ("4. Anota las presiones de los manómetros, los °Brix y las absorbancias. Si una medida no se "
         "tomó, deja la celda vacía: no escribas 0 ni '-'.", None),
        ("5. Escribe la pendiente (m) y el intercepto (b) de tu curva de calibración de proteína "
         "(Concentración = m × Absorbancia + b).", None),
        ("6. Guarda el archivo como Datos_GrupoX_VueltaN.xlsx (ej. Datos_Grupo3_Vuelta2.xlsx) y súbelo "
         "en la pestaña 'Sube tus Datos' del gemelo digital.", None),
        ("", None),
        ("Qué calcula la plantilla", "sub"),
        ("• Volumen de permeado = peso acumulado / densidad del lactosuero.", None),
        ("• Flux J = volumen acumulado / tiempo transcurrido / área de membrana (L/m²·h), la misma "
         "definición con la que se ajustó el modelo del gemelo digital.", None),
        ("• Volumen en el tanque = (peso bruto − tara del tanque) / densidad.", None),
        ("• Concentración de proteína = m × absorbancia + b, en el tanque y en el permeado.", None),
        ("• Coeficiente de rechazo R = (1 − C_permeado / C_tanque) × 100. En operación normal: 93–95 %.", None),
        ("", None),
        ("Código de colores", "sub"),
        ("Escribir aquí (dato medido en el laboratorio)", "amarillo"),
        ("No tocar (fórmula automática)", "gris"),
    ]
    for i, (txt, tipo) in enumerate(filas, start=2):
        c = ins.cell(row=i, column=2, value=txt)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if tipo == "titulo":
            c.font = Font(bold=True, size=14, color=AZUL)
        elif tipo == "sub":
            c.font = Font(bold=True, size=12, color=AZUL)
        elif tipo == "amarillo":
            c.fill = AMARILLO
        elif tipo == "gris":
            c.fill = GRIS

    # ================================================================ VÁLVULA (referencia)
    val = wb.create_sheet("Valvula_V9")
    val.sheet_view.showGridLines = False
    val["B2"] = "Caracterización de la válvula roja trasera (V9)"
    val["B2"].font = Font(bold=True, size=13, color=AZUL)
    val["B3"] = ("Al cerrar la válvula (más vueltas) sale menos permeado y más rechazo. "
                 "La práctica estándar se hace en la vuelta 2.")
    for j, h in enumerate(["Vuelta", "% Permeado", "% Rechazo", "Relación"], start=2):
        c = val.cell(row=5, column=j, value=h)
        c.fill, c.font, c.border = ENCAB, BLANCO_B, BORDE
    for k, (v, (p, r)) in enumerate(TABLA_VALVULA.items(), start=6):
        for j, x in enumerate([v, p, r, f"{p}/{r}"], start=2):
            c = val.cell(row=k, column=j, value=x)
            c.border = BORDE
            c.alignment = Alignment(horizontal="center")
            if v == 2:
                c.fill = SUAVE
    for col, w in zip("BCDE", (10, 13, 13, 12)):
        val.column_dimensions[col].width = w
    _nombre(wb, "tabla_valvula", "Valvula_V9!$B$6:$E$15")

    # ================================================================ DATOS
    ws = wb.create_sheet("Datos_Practica", 1)
    ws.sheet_view.showGridLines = False
    ws["B2"] = "DATOS DE LA PRÁCTICA — ULTRAFILTRACIÓN DE LACTOSUERO"
    ws["B2"].font = Font(bold=True, size=14, color=AZUL)

    def etiqueta(fila, texto, col=2):
        c = ws.cell(row=fila, column=col, value=texto)
        c.font = Font(bold=True, color="213547")
        c.alignment = Alignment(vertical="center")
        ws.merge_cells(start_row=fila, start_column=col, end_row=fila, end_column=col + (1 if col == 2 else 2))
        ws.row_dimensions[fila].height = 20

    def entrada(celda, nombre=None, valor=None, gris=False, fmt=None):
        c = ws[celda]
        if valor is not None:
            c.value = valor
        c.fill = GRIS if gris else AMARILLO
        c.border = BORDE
        c.alignment = Alignment(horizontal="center", vertical="center")
        if fmt:
            c.number_format = fmt
        if nombre:
            _nombre(wb, nombre, f"Datos_Practica!${celda[0]}${celda[1:]}")

    # --- Identificación
    ws["B4"] = "Identificación"
    ws["B4"].font = Font(bold=True, size=12, color=AZUL)
    ident = [("Integrante 1", "integrante_1"), ("Integrante 2", "integrante_2"),
             ("Integrante 3", "integrante_3"), ("Correo de contacto del grupo", "correo_grupo"),
             ("Fecha de la práctica", "fecha_practica"), ("Profesor a cargo", "profesor")]
    for k, (txt, nom) in enumerate(ident, start=5):
        etiqueta(k, txt)
        ws.merge_cells(start_row=k, start_column=4, end_row=k, end_column=6)
        entrada(f"D{k}", nom)
    ws["D9"].number_format = "DD/MM/YYYY"
    ws["D10"] = "Mario Andrés Noriega Valencia"

    # --- Condiciones de operación
    ws["H4"] = "Condiciones de operación"
    ws["H4"].font = Font(bold=True, size=12, color=AZUL)
    etiqueta(5, "Vuelta de la válvula roja V9 (0–9)", 8)
    entrada("K5", "vuelta_V9", 2)
    etiqueta(6, "Relación permeado/rechazo (automática)", 8)
    entrada("K6", "relacion_PR", gris=True)
    ws["K6"] = ('=IF(K5="","",VLOOKUP(K5,Valvula_V9!$B$6:$E$15,2,FALSE)&"/"'
                '&VLOOKUP(K5,Valvula_V9!$B$6:$E$15,3,FALSE))')
    etiqueta(7, "Caudal de alimentación (L/min)", 8)
    entrada("K7", "caudal_alimentacion", 6, fmt="0.0")
    etiqueta(8, "Temperatura del lactosuero (°C)", 8)
    entrada("K8", "temperatura", fmt="0.0")
    etiqueta(9, "pH del lactosuero (opcional)", 8)
    entrada("K9", "pH", fmt="0.0")
    etiqueta(10, "Réplica Nº", 8)
    entrada("K10", "replica", 1)

    # --- Constantes y calibración
    ws["B12"] = "Constantes y calibración"
    ws["B12"].font = Font(bold=True, size=12, color=AZUL)
    consts = [("Área de membrana, A (m²)", "area_membrana", 4.8, True, "0.0"),
              ("Densidad del lactosuero, ρ (kg/L)", "densidad", 1.0208, True, "0.0000"),
              ("Tara del tanque de alimentación (kg)", "tara_tanque", 8.3, False, "0.00"),
              ("Pendiente de calibración, m (g/L por u.a.)", "cal_m", None, False, "0.0000"),
              ("Intercepto de calibración, b (g/L)", "cal_b", 0, False, "0.0000")]
    for k, (txt, nom, v, gris, fmt) in enumerate(consts, start=13):
        etiqueta(k, txt)
        ws.merge_cells(start_row=k, start_column=4, end_row=k, end_column=6)
        entrada(f"D{k}", nom, v, gris=gris, fmt=fmt)
    ws["H13"] = ("La tara es el peso del tanque de alimentación VACÍO (8.3 kg en los ensayos "
                 "del laboratorio). Pesa tu tanque si es otro. La calibración sale de tu curva "
                 "de Bradford: Concentración = m × Absorbancia + b.")
    ws.merge_cells("H13:P16")
    ws["H13"].alignment = Alignment(wrap_text=True, vertical="top")
    ws["H13"].font = Font(italic=True, color="586C7C")

    # --- Tabla de datos
    f0 = 19
    cols = [
        ("Tiempo (min)", False), ("Peso acumulado permeado (kg)", False),
        ("Peso bruto tanque alimentación (kg)", False), ("Presión entrada (psi)", False),
        ("Presión post-filtro (psi)", False), ("°Brix tanque", False), ("°Brix permeado", False),
        ("Absorbancia tanque (u.a.)", False), ("Absorbancia permeado (u.a.)", False),
        ("Volumen permeado (L)", True), ("Volumen en tanque (L)", True),
        ("Flux J (L/m²·h)", True), ("C tanque (g/L)", True), ("C permeado (g/L)", True),
        ("Rechazo R (%)", True),
    ]
    for j, (h, gris) in enumerate(cols, start=2):
        c = ws.cell(row=f0, column=j, value=h)
        c.fill = PatternFill("solid", fgColor="586C7C") if gris else ENCAB
        c.font = BLANCO_B
        c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
        c.border = BORDE
    ws.row_dimensions[f0].height = 62
    for i, t in enumerate(TIEMPOS):
        r = f0 + 1 + i
        for j in range(2, 17):
            c = ws.cell(row=r, column=j)
            c.border = BORDE
            c.alignment = Alignment(horizontal="center")
            c.fill = GRIS if j >= 11 else AMARILLO
        if t is not None:
            ws.cell(row=r, column=2, value=t)
        if t == 0:
            ws.cell(row=r, column=3, value=0)
        ws.cell(row=r, column=11, value=f'=IF(C{r}="","",C{r}/densidad)')
        ws.cell(row=r, column=12, value=f'=IF(D{r}="","",(D{r}-tara_tanque)/densidad)')
        ws.cell(row=r, column=13, value=f'=IF(OR(K{r}="",B{r}=0,B{r}=""),"",K{r}/(B{r}/60)/area_membrana)')
        ws.cell(row=r, column=14, value=f'=IF(OR(I{r}="",cal_m=""),"",cal_m*I{r}+cal_b)')
        ws.cell(row=r, column=15, value=f'=IF(OR(J{r}="",cal_m=""),"",cal_m*J{r}+cal_b)')
        ws.cell(row=r, column=16, value=f'=IF(OR(N{r}="",O{r}="",N{r}=0),"",(1-O{r}/N{r})*100)')
        for j, fmt in zip(range(3, 17), ["0.00", "0.00", "0.0", "0.0", "0.0", "0.0", "0.000",
                                         "0.000", "0.00", "0.0", "0.00", "0.00", "0.00", "0.0"]):
            ws.cell(row=r, column=j).number_format = fmt
    r1, r2 = f0 + 1, f0 + len(TIEMPOS)
    _nombre(wb, "tabla_datos", f"Datos_Practica!$B${f0}:$P${r2}")
    ws.cell(row=r2 + 1, column=2,
            value="Las últimas 4 filas están libres por si tomaste más tiempos "
                  "(escribe el tiempo en la primera columna).").font = Font(italic=True, color="586C7C")

    # --- Validaciones
    dv_v = DataValidation(type="whole", operator="between", formula1="0", formula2="9",
                          showErrorMessage=True, errorTitle="Vuelta inválida",
                          error="La válvula roja tiene 9 vueltas: escribe un número entero de 0 a 9.")
    dv_v.add("K5")
    dv_pos = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0",
                            showErrorMessage=True, errorTitle="Valor inválido",
                            error="Escribe un número mayor o igual a 0 (usa punto o coma decimal "
                                  "según tu Excel). Deja vacío si no tomaste la medida.")
    dv_pos.add(f"B{r1}:J{r2}")
    dv_pos.add("K7:K9")
    dv_pos.add("D15:D17")
    dv_f = DataValidation(type="date", operator="greaterThan", formula1="44927",
                          showErrorMessage=True, error="Escribe una fecha válida (dd/mm/aaaa).")
    dv_f.add("D9")
    for dv in (dv_v, dv_pos, dv_f):
        ws.add_data_validation(dv)

    # --- Gráfica de flux para revisar los datos al momento
    ch = ScatterChart()
    ch.title = "Flux de permeado"
    ch.style = 13
    ch.x_axis.title = "Tiempo (min)"
    ch.y_axis.title = "J (L/m²·h)"
    ch.legend = None
    s = Series(Reference(ws, min_col=13, min_row=r1, max_row=r2),
               Reference(ws, min_col=2, min_row=r1, max_row=r2), title="Flux")
    s.marker.symbol = "circle"
    ch.series.append(s)
    ch.height, ch.width = 7.5, 13
    ws.add_chart(ch, "R4")

    # --- Anchos
    ws.column_dimensions["A"].width = 2
    for col in "BC":
        ws.column_dimensions[col].width = 15
    for col in "DEFGHIJKLMNOP":
        ws.column_dimensions[col].width = 13
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 22
    ws.freeze_panes = f"C{f0 + 1}"

    # --- Proteger celdas de fórmula (sin contraseña): solo se editan las amarillas
    for fila in ws.iter_rows(min_row=1, max_row=r2 + 25, min_col=1, max_col=17):
        for c in fila:
            c.protection = Protection(locked=c.fill != AMARILLO)
    ws.protection.sheet = True
    ws.protection.formatCells = False
    ws.protection.formatColumns = False
    ws.protection.insertRows = False

    wb.active = 1
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


if __name__ == "__main__":
    with open("Plantilla_Carga_Datos_UF.xlsx", "wb") as f:
        f.write(construir_plantilla())
