# diagramas.py
# Diagramas de flujo del proceso, definidos como código (formato DOT).
# Se dibujan con st.graphviz_chart: no requieren imágenes ni librerías extra.

ESTILO = r'''
    bgcolor="transparent";
    nodesep=0.35; ranksep=0.45; pad=0.2;
    node [shape=box style="rounded,filled" fillcolor="#F5F7FA" color="#4A5568"
          fontname="Helvetica" fontsize=12 fontcolor="#1A202C" margin="0.25,0.12"];
    edge [color="#718096" fontname="Helvetica" fontsize=11 arrowsize=0.8];
'''

# Estilos reutilizables
INICIO = 'shape=oval fillcolor="#C6F6D5" color="#38A169"'
FIN = 'shape=oval fillcolor="#FED7D7" color="#E53E3E"'
DECISION = 'shape=diamond fillcolor="#FEEBC8" color="#DD6B20" margin="0.05,0.05"'
NOTA = 'shape=note fillcolor="#FEFCBF" color="#B7791F" fontsize=10'
SI = 'label="Sí" color="#38A169" fontcolor="#38A169"'
NO = 'label="No" color="#E53E3E" fontcolor="#E53E3E"'


def _dot(cuerpo):
    return "digraph {" + ESTILO + cuerpo + "}"


# ---------------------------------------------------------------- DIAGRAMA 1
def diagrama_lactosuero():
    return _dot(rf'''
    ini [label="Inicio" {INICIO}];
    a [label="Llenar de agua el tanque\nde alimentación (~80 L)"];
    b [label="Pesar ~5,21 kg de lactosuero\nen polvo y agregar al tanque\nde alimentación"];
    c [label="Abrir paso hacia la bomba\nde mezclado y encender" fillcolor="#BEE3F8" color="#3182CE"];
    d [label="Dejar hidratar la mezcla\nentre 5 y 10 min"];
    fin [label="Fin" {FIN}];
    nota [label="Mezclar también\ncon vara de apoyo" {NOTA}];

    ini -> a -> b -> c -> d -> fin;
    nota -> c [style=dashed arrowhead=none];
    {{rank=same; c; nota}}
    ''')


# ---------------------------------------------------------------- DIAGRAMA 2
def diagrama_purga():
    return _dot(rf'''
    ini [label="Inicio" {INICIO}];
    v [label="Verificar válvulas\ncerradas"];
    l [label="Conectar línea de agua\nal equipo"];
    e [label="Abrir válvulas de\nentrada de agua"];
    p1 [label="Abrir válvulas 1 y 3 por 5 a 10 min.\npara purgar línea de rechazo" fillcolor="#BEE3F8" color="#3182CE"];
    d1 [label="¿Se observa el agua\nclara en la salida?" {DECISION}];
    w1 [label="Esperar" fillcolor="#EDF2F7"];
    n1 [label="Tomar muestra de agua en las salidas\ny medir conductividad para verificar\nque es adecuado usarla (~ 30-33 µS/cm)" {NOTA}];
    p2 [label="Cerrar válvula 3, abrir válvula 4\npor 5 a 10 min. para purgar\nlínea de permeado" fillcolor="#BEE3F8" color="#3182CE"];
    d2 [label="¿Se observa el agua\nclara en la salida?" {DECISION}];
    w2 [label="Esperar" fillcolor="#EDF2F7"];
    f [label="Medir flux de agua pura\nen salida de permeado"];
    c1 [label="Cerrar válvulas 1 y 4\nen el panel"];
    c2 [label="Cerrar válvula de entrada de agua\ny desconectar línea de agua"];
    fin [label="Fin" {FIN}];

    ini -> v -> l -> e -> p1 -> d1;
    d1 -> p2 [{SI}];
    d1 -> w1 [{NO}];
    w1 -> d1;
    p2 -> d2;
    d2 -> f [{SI}];
    d2 -> w2 [{NO}];
    w2 -> d2;
    f -> c1 -> c2 -> fin;

    n1 -> d1 [style=dashed arrowhead=none];
    {{rank=same; d1; n1; w1}}
    ''')


# ---------------------------------------------------------------- DIAGRAMA 3
def diagrama_practica():
    return _dot(rf'''
    compound=true;
    ini [label="Inicio" {INICIO}];

    subgraph cluster_montaje {{
        label="1. Montaje"; fontname="Helvetica"; fontcolor="#2B6CB0";
        style="rounded,filled"; fillcolor="#EBF8FF"; color="#90CDF4";
        v [label="Verificar válvulas\ncerradas"];
        c1 [label="Conectar salida del rechazo\nal tanque de alimentación"];
        c2 [label="Conectar salida de permeado\nal tanque de recolección"];
        c3 [label="Conectar el tanque de\nalimentación al equipo"];
    }}

    subgraph cluster_arranque {{
        label="2. Arranque"; fontname="Helvetica"; fontcolor="#2F855A";
        style="rounded,filled"; fillcolor="#F0FFF4"; color="#9AE6B4";
        A [label="(A) Abrir válvulas de entrada\ndel lactosuero"];
        v12 [label="Abrir válvulas 1 y 2 en el panel\npara iniciar la ultrafiltración"];
        aj [label="Ajustar flujo de\nentrada a ~6 L/min"];
        q1 [label="¿El flujo es de ~6 L/min\nen el rotámetro\nde alimentación?" {DECISION}];
        ap [label="Abrir válvula de\npermeado ~2 vueltas"];
        q2 [label="¿Las condiciones son\nadecuadas para iniciar?" {DECISION}];
        ver [label="Verificar desde (A)" fillcolor="#EDF2F7"];
    }}

    subgraph cluster_datos {{
        label="3. Toma de datos"; fontname="Helvetica"; fontcolor="#B7791F";
        style="rounded,filled"; fillcolor="#FFFFF0"; color="#F6E05E";
        td [label="Iniciar toma de datos\ncada 8 min."];
        nota [label="Peso de permeado y rechazo,\npresión de entrada\ny de membrana" {NOTA}];
        brix [label="Medir °Brix a muestra de\nalimentación, permeado y rechazo"];
        q3 [label="¿Ensayo finalizado?" {DECISION}];
        cont [label="Continuar toma de datos\nhasta culminar" fillcolor="#EDF2F7"];
    }}

    subgraph cluster_limpieza {{
        label="4. Limpieza"; fontname="Helvetica"; fontcolor="#C05621";
        style="rounded,filled"; fillcolor="#FFFAF0"; color="#FBD38D";
        lp [label="Limpiar línea de rechazo y de permeado\nsiguiendo el procedimiento de purga de agua."];
        ce [label="Cerrar entrada de lactosuero\ny desconectar tanque"];
        naoh [label="(B) Conectar alimento de NaOH (1% p/v)\ny recircular por el equipo" fillcolor="#FEEBC8" color="#DD6B20"];
        dn [label="Desconectar alimento de NaOH y\nconectar línea de agua de la planta"];
        pg [label="Realizar nuevamente purga de agua,\nmidiendo flux y conductividad"];
        q4 [label="¿La conductividad y el flux\nretoman valor inicial?" {DECISION}];
        rep [label="Repetir a partir de (B)" fillcolor="#EDF2F7"];
    }}

    subgraph cluster_cierre {{
        label="5. Cierre"; fontname="Helvetica"; fontcolor="#C53030";
        style="rounded,filled"; fillcolor="#FFF5F5"; color="#FEB2B2";
        s1 [label="Detener el flujo de agua"];
        s2 [label="Apagar bomba de mezclado"];
        s3 [label="Desocupar y limpiar\ntanque de alimento"];
        s4 [label="Apagar el equipo"];
    }}

    fin [label="Fin" {FIN}];

    ini -> v -> c1 -> c2 -> c3 -> A -> v12 -> aj -> q1;
    q1 -> aj [{NO}];
    q1 -> ap [{SI}];
    ap -> q2;
    q2 -> ver [{NO}];
    ver -> A;
    q2 -> td [{SI}];
    td -> brix -> q3;
    nota -> td [style=dashed arrowhead=none];
    q3 -> cont [{NO}];
    cont -> q3;
    q3 -> lp [{SI}];
    lp -> ce -> naoh -> dn -> pg -> q4;
    q4 -> rep [{NO}];
    rep -> naoh;
    q4 -> s1 [{SI}];
    s1 -> s2 -> s3 -> s4 -> fin;
    ''')
