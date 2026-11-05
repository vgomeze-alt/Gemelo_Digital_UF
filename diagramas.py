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
    nodesep=0.9; ranksep=0.5;

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

    // Primera decisión: "No" sale por arriba, el retorno vuelve por abajo
    d1 -> p2 [{SI}];
    d1:ne -> w1:nw [{NO} constraint=false];
    w1:sw -> d1:se [constraint=false style=dashed];

    p2 -> d2;

    // Segunda decisión
    d2 -> f [{SI}];
    d2:ne -> w2:nw [{NO} constraint=false];
    w2:sw -> d2:se [constraint=false style=dashed];

    f -> c1 -> c2 -> fin;

    // Nota a la izquierda, "Esperar" a la derecha
    {{rank=same; n1; d1; w1}}
    n1 -> d1 [style=dashed dir=none];
    d1 -> w1 [style=invis weight=10];
    {{rank=same; d2; w2}}
    d2 -> w2 [style=invis weight=10];
    ''')

# ---------------------------------------------------------------- DIAGRAMA 3
def diagrama_practica():
    # Colores por fase (columna)
    AZ = 'fillcolor="#EBF8FF" color="#3182CE"'   # Montaje
    VE = 'fillcolor="#F0FFF4" color="#38A169"'   # Arranque y toma de datos
    NA = 'fillcolor="#FFFAF0" color="#DD6B20"'   # Limpieza
    RO = 'fillcolor="#FFF5F5" color="#E53E3E"'   # Cierre
    GR = 'fillcolor="#EDF2F7"'                   # Pasos auxiliares

    # Con líneas rectas (ortho) las etiquetas se ponen con xlabel
    SIX = 'xlabel="Sí" color="#38A169" fontcolor="#38A169"'
    NOX = 'xlabel="No" color="#E53E3E" fontcolor="#E53E3E"'

    return _dot(rf'''
    newrank=true; splines=ortho; nodesep=0.6; ranksep=0.6;

    h1 [label="1. Montaje" shape=plaintext style="" fontsize=14 fontcolor="#2B6CB0"];
    h2 [label="2. Arranque y toma de datos" shape=plaintext style="" fontsize=14 fontcolor="#2F855A"];
    h3 [label="3. Limpieza" shape=plaintext style="" fontsize=14 fontcolor="#C05621"];
    h4 [label="4. Cierre" shape=plaintext style="" fontsize=14 fontcolor="#C53030"];

    ini [label="Inicio" {INICIO}];
    v [label="Verificar válvulas\ncerradas" {AZ}];
    c1 [label="Conectar salida del\nrechazo al tanque\nde alimentación" {AZ}];
    c2 [label="Conectar salida de\npermeado al tanque\nde recolección" {AZ}];
    c3 [label="Conectar el tanque de\nalimentación al equipo" {AZ}];
    A [label="(A) Abrir válvulas de\nentrada del lactosuero" {AZ}];
    v12 [label="Abrir válvulas 1 y 2\nen el panel para iniciar\nla ultrafiltración" {AZ}];
    aj [label="Ajustar flujo de\nentrada a ~6 L/min" {AZ}];

    q1 [label="¿El flujo es de\n~6 L/min en el rotámetro\nde alimentación?" {DECISION}];
    ap [label="Abrir válvula de\npermeado ~2 vueltas" {VE}];
    q2 [label="¿Las condiciones\nson adecuadas\npara iniciar?" {DECISION}];
    td [label="Iniciar toma de datos\ncada 8 min." {VE}];
    brix [label="Medir °Brix a muestra de\nalimentación, permeado\ny rechazo" {VE}];
    q3 [label="¿Ensayo\nfinalizado?" {DECISION}];

    nota [label="Peso de permeado y rechazo,\npresión de entrada\ny de membrana" {NOTA}];
    ver [label="Verificar\ndesde (A)" {GR}];
    cont [label="Continuar toma de\ndatos hasta culminar" {GR}];
    rep [label="Repetir a\npartir de (B)" {GR}];

    lp [label="Limpiar línea de rechazo\ny de permeado siguiendo\nel procedimiento de purga\nde agua." {NA}];
    ce [label="Cerrar entrada de\nlactosuero y\ndesconectar tanque" {NA}];
    naoh [label="(B) Conectar alimento de\nNaOH (1% p/v) y\nrecircular por el equipo" {NA}];
    dn [label="Desconectar alimento de\nNaOH y conectar línea\nde agua de la planta" {NA}];
    pg [label="Realizar nuevamente\npurga de agua, midiendo\nflux y conductividad" {NA}];
    q4 [label="¿La conductividad\ny el flux retoman\nvalor inicial?" {DECISION}];

    s1 [label="Detener el flujo\nde agua" {RO}];
    s2 [label="Apagar bomba\nde mezclado" {RO}];
    s3 [label="Desocupar y limpiar\ntanque de alimento" {RO}];
    s4 [label="Apagar el equipo" {RO}];
    fin [label="Fin" {FIN}];

    // ---- Títulos de columna
    {{rank=same; h1; h2; h3; h4}}
    h1 -> h2 -> h3 -> h4 [style=invis];
    h1 -> ini [style=invis];
    h2 -> q3 [style=invis weight=5];
    h3 -> lp [style=invis weight=5];
    h4 -> fin [style=invis weight=5];

    // ---- Filas (alinean las 4 columnas de izquierda a derecha)
    {{rank=same; c1; q3; lp}}              c1 -> q3 -> lp [style=invis];
    {{rank=same; c2; brix; cont; ce}}      c2 -> brix -> cont -> ce [style=invis];
    {{rank=same; c3; td; nota; naoh; fin}} c3 -> td -> nota -> naoh -> fin [style=invis];
    {{rank=same; A; q2; ver; dn; s4}}      A -> q2 -> ver -> dn -> s4 [style=invis];
    {{rank=same; v12; ap; pg; s3}}         v12 -> ap -> pg -> s3 [style=invis];
    {{rank=same; aj; q1; rep; q4; s1}}     aj -> q1 -> rep -> q4 -> s1 [style=invis];

    // ---- Columna 1: montaje (baja)
    ini -> v -> c1 -> c2 -> c3 -> A -> v12 -> aj;
    aj -> q1;
    q1 -> aj [{NOX} constraint=false];

    // ---- Columna 2: arranque y toma de datos (sube)
    ap -> q1 [dir=back {SIX}];
    q2 -> ap [dir=back];
    td -> q2 [dir=back {SIX}];
    brix -> td [dir=back];
    q3 -> brix [dir=back];
    q2 -> ver [{NOX} constraint=false];
    ver -> A [constraint=false style=dashed];
    q3 -> cont [{NOX} tailport=se headport=w constraint=false];
    cont -> q3 [constraint=false style=dashed color="#718096" tailport=n headport=e];
    nota -> td [style=dashed dir=none constraint=false];

    // ---- Columna 3: limpieza (baja)
    q3 -> lp [{SIX} constraint=false];
    lp -> ce -> naoh -> dn -> pg -> q4;
    rep -> q4 [dir=back {NOX} constraint=false];
    rep -> naoh [constraint=false style=dashed];

    // ---- Columna 4: cierre (sube)
    q4 -> s1 [{SIX} constraint=false];
    s2 -> s1 [dir=back];
    s3 -> s2 [dir=back];
    s4 -> s3 [dir=back];
    fin -> s4 [dir=back];
    ''')
