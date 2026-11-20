/* Escena 3D del equipo de ultrafiltración MARTIN MTUF-PVC-4046 (AI-UF-1-4).
   Geometría esquemática construida con primitivas; topología según manual,
   tesis y P&ID (RIELCO). Dimensiones y recorridos: supuestos de representación. */

const COMPONENTES = __COMPONENTES__;
const CICLOS = __CICLOS__;
const JRATIO = __JRATIO__;   // J(t)/J0 del modelo de Hermia, t = 0..40 min
const JCURVE = __JCURVE__;   // J(t) en L/m2 h
const CCURVE = __CCURVE__;   // C(t) en g/L (balance por lotes)

// ------------------------------------------------------------- base
const canvas = document.getElementById("c");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeaf1f7);
scene.fog = new THREE.Fog(0xeaf1f7, 9, 16);

const camera = new THREE.PerspectiveCamera(42, 2, 0.1, 60);
camera.position.set(2.4, 1.85, 3.8);
const controls = new THREE.OrbitControls(camera, canvas);
controls.target.set(0, 0.95, 0.3);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 1.1;
controls.maxDistance = 9;
controls.maxPolarAngle = Math.PI * 0.49;

scene.add(new THREE.HemisphereLight(0xffffff, 0xb0bcc8, 0.75));
const sol = new THREE.DirectionalLight(0xffffff, 0.75);
sol.position.set(4, 6, 5);
scene.add(sol);
const sol2 = new THREE.DirectionalLight(0xdfe9ff, 0.3);
sol2.position.set(-5, 3, -4);
scene.add(sol2);

const piso = new THREE.Mesh(
  new THREE.CircleGeometry(9, 48),
  new THREE.MeshPhongMaterial({ color: 0xd8dee5 })
);
piso.rotation.x = -Math.PI / 2;
scene.add(piso);
const grid = new THREE.GridHelper(18, 36, 0xc2cbd4, 0xcfd7df);
grid.position.y = 0.002;
scene.add(grid);

// ------------------------------------------------------------- materiales
const M = {
  acero:  new THREE.MeshPhongMaterial({ color: 0xaab4bd, shininess: 70 }),
  aceroOsc: new THREE.MeshPhongMaterial({ color: 0x7d8992, shininess: 60 }),
  beige:  new THREE.MeshPhongMaterial({ color: 0xd6cfb4 }),
  blanco: new THREE.MeshPhongMaterial({ color: 0xf4f4f1 }),
  blancoMate: new THREE.MeshPhongMaterial({ color: 0xe9e9e4 }),
  negro:  new THREE.MeshPhongMaterial({ color: 0x23272b }),
  azulBarril: new THREE.MeshPhongMaterial({ color: 0x1f5fa8 }),
  azulTapa: new THREE.MeshPhongMaterial({ color: 0x154a86 }),
  azulFiltro: new THREE.MeshPhongMaterial({ color: 0x2b6fd4, transparent: true, opacity: 0.88 }),
  azulBomba: new THREE.MeshPhongMaterial({ color: 0x2457c5, shininess: 80 }),
  verde:  new THREE.MeshPhongMaterial({ color: 0x3a9e4d, shininess: 60 }),
  rojo:   new THREE.MeshPhongMaterial({ color: 0xc02a24, shininess: 60 }),
  naranja: new THREE.MeshPhongMaterial({ color: 0xf0a01a, emissive: 0x3a2400 }),
  vidrio: new THREE.MeshPhongMaterial({ color: 0xbfe2ef, transparent: true, opacity: 0.6 }),
};
const matMembrana = new THREE.MeshPhongMaterial({ color: 0xf2f2ee, shininess: 35 });

// ------------------------------------------------------------- helpers
const clicables = [];
function grupo(cid) {
  const g = new THREE.Group();
  if (cid) g.userData.cid = cid;
  scene.add(g);
  return g;
}
function caja(g, w, h, d, mat, x, y, z, ry) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  if (ry) m.rotation.y = ry;
  g.add(m);
  return m;
}
function cil(g, r, h, mat, x, y, z, rot) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, 28), mat);
  m.position.set(x, y, z);
  if (rot === "x") m.rotation.x = Math.PI / 2;
  if (rot === "z") m.rotation.z = Math.PI / 2;
  g.add(m);
  return m;
}
function registrar(g) {
  g.traverse(o => { if (o.isMesh) { o.userData.cid = g.userData.cid; clicables.push(o); } });
}

// ------------------------------------------------------------- estructura (skid)
const skid = grupo(null);
caja(skid, 1.42, 0.06, 0.78, M.acero, 0, 0.33, 0);                 // plataforma
[[-0.66, -0.34], [0.66, -0.34], [-0.66, 0.34], [0.66, 0.34]].forEach(p =>
  cil(skid, 0.024, 0.33, M.aceroOsc, p[0], 0.165, p[1]));
cil(skid, 0.024, 1.42, M.aceroOsc, -0.66, 1.07, -0.3);             // postes traseros
cil(skid, 0.024, 1.42, M.aceroOsc, 0.66, 1.07, -0.3);
caja(skid, 1.36, 0.045, 0.045, M.aceroOsc, 0, 1.76, -0.3);         // travesaño

// ------------------------------------------------------------- tablero de control
const tcontrol = grupo("tableroControl");
caja(tcontrol, 0.62, 0.58, 0.12, M.beige, -0.05, 1.32, -0.18);
cil(tcontrol, 0.016, 0.02, M.verde, -0.05, 1.555, -0.115, "x");     // piloto verde (energía)
const pilotos = [];
[-0.2, -0.05, 0.1].forEach(x => {                                   // fila 1: V1–V3
  pilotos.push(cil(tcontrol, 0.016, 0.02, M.naranja.clone(), x, 1.47, -0.115, "x"));
  cil(tcontrol, 0.014, 0.022, M.negro, x, 1.38, -0.115, "x");
});
const filaInf = [-0.245, -0.115, 0.015, 0.145];                     // fila 2: V4,V5,DOSIF,BOMBA
const extras = [];
filaInf.forEach(x => {
  extras.push(cil(tcontrol, 0.016, 0.02, M.naranja.clone(), x, 1.24, -0.115, "x"));
  cil(tcontrol, 0.014, 0.022, M.negro, x, 1.15, -0.115, "x");
});
pilotos.push(extras[0], extras[1]);                                 // V4 y V5
const pilotoDosif = extras[2], pilotoBomba = extras[3];
registrar(tcontrol);

// ------------------------------------------------------------- tablero hidráulico
const thid = grupo("tableroHidraulico");
caja(thid, 0.62, 0.4, 0.08, M.blanco, -0.05, 0.82, -0.16);
for (let i = 0; i < 3; i++) {                                       // rotámetros
  caja(thid, 0.05, 0.3, 0.035, M.vidrio, -0.28 + i * 0.075, 0.82, -0.115);
  caja(thid, 0.018, 0.02, 0.03, M.rojo, -0.28 + i * 0.075, 0.76 + i * 0.03, -0.112);
}
const posPI = [[-0.02, 0.9], [0.1, 0.9], [0.22, 0.9], [0.04, 0.73], [0.18, 0.73]];
posPI.forEach(p => {                                                // manómetros PI 1.01–1.05
  cil(thid, 0.035, 0.016, M.negro, p[0], p[1], -0.118, "x");
  cil(thid, 0.029, 0.02, M.blancoMate, p[0], p[1], -0.117, "x");
});
registrar(thid);

// ------------------------------------------------------------- microfiltro
const micro = grupo("microfiltro");
cil(micro, 0.055, 0.5, M.azulFiltro, -0.52, 0.95, 0.02);
cil(micro, 0.062, 0.07, M.acero, -0.52, 1.23, 0.02);
cil(micro, 0.03, 0.1, M.acero, -0.52, 0.66, 0.02);
registrar(micro);

// ------------------------------------------------------------- membrana UF
const memb = grupo("membrana");
const cuerpoMembrana = cil(memb, 0.085, 1.15, matMembrana, 0.95, 1.08, 0);
cil(memb, 0.092, 0.07, M.negro, 0.95, 0.49, 0);
cil(memb, 0.092, 0.07, M.negro, 0.95, 1.665, 0);
cil(memb, 0.022, 0.08, M.negro, 0.95, 1.73, 0);                     // puerto permeado (arriba)
cil(memb, 0.02, 0.09, M.negro, 1.0, 1.56, 0, "z");                  // puerto rechazo (lateral)
cil(memb, 0.02, 0.09, M.negro, 0.9, 0.52, 0.03, "z");               // puerto entrada (abajo)
caja(memb, 0.26, 0.035, 0.04, M.aceroOsc, 0.8, 1.5, -0.15);         // soportes al marco
caja(memb, 0.26, 0.035, 0.04, M.aceroOsc, 0.8, 0.7, -0.15);
registrar(memb);

// ------------------------------------------------------------- bombas
const bAli = grupo("bombaAlimentacion");
caja(bAli, 0.16, 0.12, 0.12, M.azulBomba, -0.58, 0.1, 0.62);
cil(bAli, 0.05, 0.08, M.azulBomba, -0.46, 0.09, 0.62, "z");
caja(bAli, 0.2, 0.025, 0.15, M.aceroOsc, -0.56, 0.03, 0.62);
registrar(bAli);

const bLav = grupo("bombaLavado");                                  // del equipo (foto: BOMBA LAVADO)
cil(bLav, 0.065, 0.2, M.negro, 0.14, 0.45, 0.1, "z");               // motor negro
cil(bLav, 0.075, 0.07, M.acero, 0.29, 0.44, 0.1, "z");              // cabezal inoxidable
caja(bLav, 0.3, 0.03, 0.16, M.aceroOsc, 0.18, 0.375, 0.1);
registrar(bLav);

// ------------------------------------------------------------- tanques
function barril(cid, x, z, r, h, ladoEquipo) {
  const g = grupo(cid);
  caja(g, r * 2.6, 0.06, r * 2.6, M.acero, x, 0.07, z);             // báscula (plataforma)
  caja(g, 0.14, 0.05, 0.03, M.negro, x, 0.125, z + r * 1.3);        // indicador de peso
  cil(g, r, h, M.azulBarril, x, 0.1 + h / 2, z);
  cil(g, r + 0.012, 0.03, M.azulTapa, x, 0.1 + h + 0.015, z);
  cil(g, r + 0.008, 0.025, M.azulTapa, x, 0.1 + h * 0.4, z);        // aro
  // puertos: salida inferior y conexión superior (blancos, hacia el equipo)
  cil(g, 0.022, 0.09, M.blanco, x + ladoEquipo * (r + 0.04), 0.1 + 0.12, z, "z");
  cil(g, 0.022, 0.09, M.blanco, x + ladoEquipo * (r + 0.04), 0.1 + h - 0.1, z, "z");
  registrar(g);
  return g;
}
barril("tanqueAlimentacion", -0.95, 0.8, 0.25, 0.78, 1);
barril("tanquePermeado", 1.18, 0.85, 0.19, 0.58, -1);

const caneca = grupo("canecaResiduos");                             // residuos del químico
const canCuerpo = new THREE.Mesh(new THREE.CylinderGeometry(0.105, 0.085, 0.3, 20),
  new THREE.MeshPhongMaterial({ color: 0xc02a24 }));
canCuerpo.position.set(0.05, 0.2, 1.22);
caneca.add(canCuerpo);
caja(caneca, 0.3, 0.05, 0.3, M.acero, 0.05, 0.025, 1.22);          // báscula
caja(caneca, 0.1, 0.04, 0.025, M.negro, 0.05, 0.06, 1.385);         // indicador
cil(caneca, 0.095, 0.015, M.negro, 0.05, 0.355, 1.22);
registrar(caneca);

// ------------------------------------------------------------- otros
const vRoja = grupo("valvulaRoja");
const volanteRojo = cil(vRoja, 0.06, 0.028, M.rojo.clone(), 0.25, 0.95, -0.4, "x");
cil(vRoja, 0.012, 0.1, M.aceroOsc, 0.25, 0.95, -0.35, "x");
registrar(vRoja);

const aire = grupo("inyeccionAire");
cil(aire, 0.028, 0.15, M.negro, 0.72, 0.98, -0.13);                 // filtro-regulador
cil(aire, 0.022, 0.012, M.blancoMate, 0.72, 1.07, -0.115, "x");     // manómetro pequeño
caja(aire, 0.1, 0.02, 0.03, M.aceroOsc, 0.82, 1.05, -0.1);
registrar(aire);

const dren = grupo("drenaje");
caja(dren, 0.32, 0.035, 0.22, M.aceroOsc, 0.45, 0.02, 1.25);
for (let i = 0; i < 5; i++) caja(dren, 0.28, 0.04, 0.012, M.negro, 0.45, 0.022, 1.17 + i * 0.04);
registrar(dren);

const toma = grupo("tomaAgua");
cil(toma, 0.02, 1.5, M.verde, -1.5, 0.75, -0.32);
cil(toma, 0.05, 0.02, M.rojo, -1.5, 1.4, -0.27, "x");
registrar(toma);

// ------------------------------------------------------------- tuberías
const tubos = {};
function tubo(id, color, puntos, radio) {
  const curva = new THREE.CatmullRomCurve3(puntos.map(p => new THREE.Vector3(...p)));
  const mat = new THREE.MeshPhongMaterial({ color, transparent: true, opacity: 0.13 });
  const mesh = new THREE.Mesh(new THREE.TubeGeometry(curva, 72, radio || 0.016, 10), mat);
  scene.add(mesh);
  tubos[id] = { curva, mat, mesh, color, particulas: [], activo: false };
}
const C = { ent: 0x1fa23a, per: 0x1565d8, rec: 0xd8342c, lav: 0x18b8c4, aire: 0xf08c1a };

tubo("entradaLactosuero", C.ent, [
  [-0.68, 0.22, 0.8], [-0.62, 0.12, 0.7], [-0.52, 0.1, 0.62], [-0.44, 0.3, 0.4],
  [-0.52, 0.6, 0.06], [-0.52, 1.2, 0.02], [-0.3, 1.12, 0.1], [0.3, 0.6, 0.12],
  [0.75, 0.5, 0.08], [0.9, 0.52, 0.03]]);
tubo("entradaAgua", C.ent, [
  [-1.5, 1.42, -0.3], [-1.2, 1.0, -0.1], [-0.7, 0.55, 0.12], [-0.2, 0.45, 0.14],
  [-0.52, 0.6, 0.06], [-0.52, 1.2, 0.02], [-0.3, 1.12, 0.1], [0.3, 0.6, 0.12],
  [0.75, 0.5, 0.08], [0.9, 0.52, 0.03]]);
tubo("rechazoTanque", C.rec, [
  [1.0, 1.56, 0], [0.85, 1.35, -0.3], [0.45, 1.0, -0.42], [0.25, 0.95, -0.43],
  [-0.2, 1.05, -0.32], [-0.7, 1.05, 0.2], [-0.85, 0.95, 0.6], [-0.66, 0.8, 0.78]]);
tubo("rechazoDrenaje", C.rec, [
  [1.0, 1.56, 0], [1.12, 1.2, 0.2], [0.85, 0.6, 0.7], [0.5, 0.15, 1.18]]);
tubo("permeadoTanque", C.per, [
  [0.95, 1.75, 0], [1.08, 1.8, 0.12], [1.25, 1.2, 0.5], [0.93, 0.62, 0.85]]);
tubo("permeadoDrenaje", C.per, [
  [0.95, 1.75, 0], [0.8, 1.6, 0.35], [0.55, 0.7, 0.95], [0.42, 0.12, 1.2]]);
tubo("lavado", C.lav, [
  [-0.68, 0.22, 0.78], [-0.5, 0.2, 0.35], [-0.1, 0.3, 0.02], [0.14, 0.42, 0.06],
  [0.32, 0.44, 0.08], [0.7, 0.44, 0.02], [0.9, 0.5, 0.0]]);
tubo("quimicoEntrada", C.lav, [
  [-0.68, 0.22, 0.8], [-0.62, 0.12, 0.7], [-0.52, 0.1, 0.62], [-0.44, 0.3, 0.4],
  [-0.52, 0.6, 0.06], [-0.52, 1.2, 0.02], [-0.3, 1.12, 0.1], [0.3, 0.6, 0.12],
  [0.75, 0.5, 0.08], [0.9, 0.52, 0.03]]);
tubo("permeadoCaneca", C.per, [
  [0.95, 1.75, 0], [0.85, 1.65, 0.3], [0.55, 0.9, 0.95], [0.07, 0.4, 1.22]]);
tubo("aireLinea", C.aire, [
  [0.72, 1.05, -0.13], [0.8, 0.8, -0.1], [0.88, 0.58, -0.04]], 0.01);

// partículas
function crearParticulas(t) {
  const n = 16;
  for (let i = 0; i < n; i++) {
    const p = new THREE.Mesh(
      new THREE.SphereGeometry(0.02, 10, 10),
      new THREE.MeshBasicMaterial({ color: t.color })
    );
    p.visible = false;
    p.userData.fase = i / n;
    scene.add(p);
    t.particulas.push(p);
  }
}
Object.values(tubos).forEach(crearParticulas);

// --------------------------------------------- interior de la membrana
// Módulo inside-out (fichas UF-4046; tesis Fig. 4): la alimentación entra por
// el interior de cada fibra, el permeado atraviesa la pared hacia la carcasa
// y el concentrado sigue de largo. En retrolavado el sentido se invierte y
// entra aire a contracorriente.
const FIBRAS = [[0, 0], [0.038, 0], [-0.038, 0], [0.019, 0.033], [-0.019, 0.033],
                [0.019, -0.033], [-0.019, -0.033]];
const interiorG = new THREE.Group();
interiorG.visible = false;
scene.add(interiorG);
FIBRAS.forEach(f => {
  const fib = new THREE.Mesh(new THREE.CylinderGeometry(0.0115, 0.0115, 1.02, 10),
    new THREE.MeshPhongMaterial({ color: 0xcfc49a, transparent: true, opacity: 0.45, depthWrite: false }));
  fib.position.set(0.95 + f[0], 1.08, f[1]);
  fib.userData.cid = "membrana";
  clicables.push(fib);
  interiorG.add(fib);
});
const tortas = [], retenidos = [];
FIBRAS.forEach(f => {
  const t = new THREE.Mesh(new THREE.CylinderGeometry(0.0095, 0.0095, 1.0, 10),
    new THREE.MeshPhongMaterial({ color: 0xc08a3e, transparent: true, opacity: 0 }));
  t.position.set(0.95 + f[0], 1.08, f[1]);
  t.userData.cid = "membrana";
  interiorG.add(t); tortas.push(t);
});
for (let i = 0; i < 24; i++) {                        // proteína retenida en la pared
  const m = new THREE.Mesh(new THREE.SphereGeometry(0.006, 6, 6),
    new THREE.MeshBasicMaterial({ color: 0x2e7d32 }));
  const f = FIBRAS[i % 7], a = Math.random() * 6.28;
  m.position.set(0.95 + f[0] + Math.cos(a) * 0.0105, 0.6 + Math.random() * 0.95,
                 f[1] + Math.sin(a) * 0.0105);
  m.visible = false;
  interiorG.add(m); retenidos.push(m);
}
const pAlimFib = [], pPermRad = [], pBurbujas = [];
for (let i = 0; i < 21; i++) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(0.009, 8, 8),
    new THREE.MeshBasicMaterial({ color: 0x1fa23a }));
  m.visible = false; m.userData = { f: i % 7, fase: Math.random() };
  interiorG.add(m); pAlimFib.push(m);
}
for (let i = 0; i < 20; i++) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(0.008, 8, 8),
    new THREE.MeshBasicMaterial({ color: 0x4d9fe8 }));
  m.visible = false;
  m.userData = { f: i % 7, y: 0.6 + Math.random() * 0.9, prog: Math.random(), ang: Math.random() * 6.28 };
  interiorG.add(m); pPermRad.push(m);
}
for (let i = 0; i < 14; i++) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(0.01, 8, 8),
    new THREE.MeshBasicMaterial({ color: 0xf0a01a }));
  m.visible = false;
  m.userData = { fase: Math.random(), r: 0.025 + Math.random() * 0.045, ang: Math.random() * 6.28 };
  interiorG.add(m); pBurbujas.push(m);
}
function etiqueta(txt, color, ancho) {
  const c = document.createElement("canvas");
  c.width = 640; c.height = 56;
  const g = c.getContext("2d");
  g.font = "bold 30px Arial";
  g.fillStyle = "rgba(255,255,255,0.88)";
  const w = g.measureText(txt).width + 22;
  g.fillRect(0, 4, w, 44);
  g.fillStyle = color;
  g.fillText(txt, 11, 36);
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthTest: false }));
  sp.scale.set(ancho, ancho * 56 / 640, 1);
  sp.center.set(0, 0.5);
  return sp;
}

const FX = 0.42, FY = 1.12, FZ = 0.5, FR = 0.055, FH = 0.95;   // fibra ampliada
const fibraG = new THREE.Group();
fibraG.visible = false;
scene.add(fibraG);
const paredFibra = new THREE.Mesh(
  new THREE.CylinderGeometry(FR, FR, FH, 24, 1, true),
  new THREE.MeshPhongMaterial({ color: 0xdedcd2, transparent: true, opacity: 0.3,
                                side: THREE.DoubleSide, depthWrite: false }));
paredFibra.position.set(FX, FY, FZ);
paredFibra.userData.cid = "membrana";
clicables.push(paredFibra);
fibraG.add(paredFibra);
[FY - FH / 2, FY + FH / 2].forEach(y => {
  const aro = new THREE.Mesh(new THREE.TorusGeometry(FR, 0.006, 8, 24), M.negro);
  aro.rotation.x = Math.PI / 2;
  aro.position.set(FX, y, FZ);
  fibraG.add(aro);
});
const CAKE_R = 0.048;
const cake = new THREE.Mesh(
  new THREE.CylinderGeometry(CAKE_R, CAKE_R, FH * 0.97, 24, 1, true),
  new THREE.MeshPhongMaterial({ color: 0xc08a3e, transparent: true, opacity: 0.0,
                                side: THREE.DoubleSide }));
cake.position.set(FX, FY, FZ);
cake.userData.cid = "membrana";
fibraG.add(cake);
// líneas que conectan la fibra ampliada con el módulo real
[[0.86, 1.45], [0.86, 0.8]].forEach(pt => {
  const geo = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(pt[0], pt[1], 0.05), new THREE.Vector3(FX + FR, FY + (pt[1] > 1.1 ? FH / 2 : -FH / 2), FZ)]);
  fibraG.add(new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0x8aa0b4 })));
});
const etProt = etiqueta("Proteína → se acumula (torta)", "#2e7d32", 0.5);
etProt.position.set(FX + 0.08, FY + 0.36, FZ);
fibraG.add(etProt);
const etAgua = etiqueta("Agua, lactosa y sales → atraviesan", "#1565d8", 0.5);
etAgua.position.set(FX + 0.08, FY - 0.08, FZ);
fibraG.add(etAgua);
const etFib = etiqueta("Una fibra, ampliada", "#213547", 0.4);
etFib.position.set(FX - 0.1, FY + FH / 2 + 0.1, FZ);
fibraG.add(etFib);

const fAgua = [], fProt = [], fPegadas = [];
for (let i = 0; i < 26; i++) {                     // lo que permea (azul)
  const m = new THREE.Mesh(new THREE.SphereGeometry(0.0065, 8, 8),
    new THREE.MeshBasicMaterial({ color: 0x4d9fe8 }));
  m.userData = { fase: Math.random(), ySal: 0.15 + Math.random() * 0.7, ang: Math.random() * 6.28, r0: Math.random() * 0.025 };
  fibraG.add(m); fAgua.push(m);
}
for (let i = 0; i < 12; i++) {                     // proteína que sigue (verde)
  const m = new THREE.Mesh(new THREE.SphereGeometry(0.011, 8, 8),
    new THREE.MeshBasicMaterial({ color: 0x2e7d32 }));
  m.userData = { fase: Math.random(), ang: Math.random() * 6.28, r0: Math.random() * 0.02 };
  fibraG.add(m); fProt.push(m);
}
for (let i = 0; i < 26; i++) {                     // proteína ya pegada a la pared
  const m = new THREE.Mesh(new THREE.SphereGeometry(0.0105, 8, 8),
    new THREE.MeshBasicMaterial({ color: 0x2e7d32 }));
  m.userData = { ang: Math.random() * 6.28, y: (Math.random() - 0.5) * FH * 0.9 };
  m.visible = false;
  fibraG.add(m); fPegadas.push(m);
}

let interiorOn = false;
let vistaPrev = null;
let minuto = 0;
let tortaNivel = 0;
let reproduciendo = false;
const AV_MAX = 1 - JRATIO[JRATIO.length - 1];

function setMinuto(v) {
  minuto = Math.max(0, Math.min(40, v));
  tortaNivel = (1 - JRATIO[Math.round(minuto)]) / AV_MAX;
  const sl = document.getElementById("min");
  sl.value = Math.round(minuto);
  document.getElementById("minv").textContent = Math.round(minuto);
  const sl2 = document.getElementById("minInt");
  if (sl2) { sl2.value = Math.round(minuto); }
  refrescarInterior();
}

function textoFase() {
  const m = Math.round(minuto), jr = JRATIO[m];
  if (cicloActual === "uf") {
    if (m < 4) return ["🟢 Membrana limpia", "Mira la FIBRA AMPLIADA de la izquierda: el lactosuero entra por dentro de cada fibra. El flux arranca en su máximo (~" + JCURVE[0].toFixed(0) + " L/m²·h) y las primeras proteínas, demasiado grandes para los poros, comienzan a depositarse en la pared interna."];
    if (m < 15) return ["🟠 Se forma la torta", "La capa de proteína (ámbar) crece sobre la pared de las fibras y suma una resistencia extra: el flux cae rápido. El agua, la lactosa y las sales siguen atravesando hacia la carcasa."];
    if (m < 30) return ["🟤 La torta se compacta", "La capa ya formada crece más despacio y se compacta: la caída del flux se frena. En el tanque, el rechazo que retorna concentra la proteína cada vez más rápido."];
    return ["🔴 Final de la práctica", "La torta domina la resistencia: el flux queda en ~" + (100 * jr).toFixed(0) + " % del inicial. Es el momento de parar y lavar la membrana."];
  }
  if (cicloActual === "lavR" || cicloActual === "lavP")
    return ["🚿 Lavado con agua", "El agua arrastra el lactosuero residual de fibras y líneas hacia el drenaje, pero la torta ADHERIDA casi no se remueve: por eso después vienen el retrolavado y la limpieza química."];
  if (cicloActual === "quim")
    return ["🧪 Limpieza química", "La solución de NaOH (preparada en el tanque azul y bombeada con la MISMA bomba del lactosuero) disuelve la capa de proteína: mira cómo la torta desaparece de las fibras. La solución usada sale a la caneca de residuos."];
  if (cicloActual === "retro")
    return ["💨 Retrolavado + aire", "Agua en sentido contrario (de la carcasa hacia el lumen) y burbujas de aire a contracorriente despegan la torta mecánicamente. El fabricante lo recomienda cada 15–60 min, por 30–60 s."];
  return ["⏹ Equipo detenido", "Elige un modo de operación y presiona ▶ para ver qué pasa dentro de la membrana a lo largo del tiempo."];
}

function refrescarInterior() {
  // fibra ampliada: la torta cierra el canal y la proteína pegada aumenta
  const fCake = Math.max(0.03, 1 - 0.62 * tortaNivel);
  cake.scale.set(fCake, 1, fCake);
  cake.material.opacity = tortaNivel < 0.02 ? 0 : 0.55 + 0.35 * tortaNivel;
  fPegadas.forEach((m, i) => {
    m.visible = interiorOn && i < Math.round(tortaNivel * fPegadas.length);
    const rr = CAKE_R * fCake + 0.004;
    m.position.set(FX + Math.cos(m.userData.ang) * rr, FY + m.userData.y,
                   FZ + Math.sin(m.userData.ang) * rr);
  });
  // torta sobre las fibras y tinte de la carcasa
  tortas.forEach(t => { t.material.opacity = interiorOn ? 0.4 * tortaNivel : 0; });
  retenidos.forEach((m, i) => { m.visible = interiorOn && i < Math.round(tortaNivel * retenidos.length); });
  const col = new THREE.Color(0xf2f2ee).lerp(new THREE.Color(0xcfa05e), tortaNivel);
  matMembrana.color.copy(col);
  if (!interiorOn) return;
  const [tt, dd] = textoFase();
  document.getElementById("faseT").textContent = tt;
  document.getElementById("faseD").textContent = dd;
  const m = Math.round(minuto);
  document.getElementById("lectura").innerHTML = cicloActual === "uf"
    ? "min <b>" + m + "</b> · J ≈ <b>" + JCURVE[m].toFixed(1) + "</b> L/m²·h · C tanque ≈ <b>" + CCURVE[m].toFixed(1) + "</b> g/L"
    : "Torta depositada: <b>" + Math.round(tortaNivel * 100) + " %</b>" +
      (tortaNivel < 0.03 && (cicloActual === "quim" || cicloActual === "retro")
        ? " · ✅ membrana limpia: el flux vuelve a su línea base" : "");
  document.getElementById("barraTorta").style.width = Math.round(tortaNivel * 100) + "%";
  const esUF = cicloActual === "uf";
  document.getElementById("zonaGraficas").style.display = esUF ? "block" : "none";
  document.getElementById("ctrlTiempo").style.display = esUF ? "flex" : "none";
  if (esUF) dibujarGraficas();
}

function dibujarGraficas() {
  const cv = document.getElementById("gf");
  const g = cv.getContext("2d");
  const W = cv.width, H = cv.height, mx = 34, mt = 14, gap = 26;
  const ph = (H - mt * 2 - gap) / 2;
  g.clearRect(0, 0, W, H);
  function serie(datos, y0, cmin, cmax, color, titulo, unidad) {
    g.strokeStyle = "#e2e8f0"; g.strokeRect(mx, y0, W - mx - 8, ph);
    g.strokeStyle = color; g.lineWidth = 2; g.beginPath();
    datos.forEach((v, i) => {
      const x = mx + (W - mx - 8) * i / 40;
      const y = y0 + ph - ph * (v - cmin) / (cmax - cmin);
      i ? g.lineTo(x, y) : g.moveTo(x, y);
    });
    g.stroke();
    const i = Math.round(minuto);
    const x = mx + (W - mx - 8) * i / 40;
    const y = y0 + ph - ph * (datos[i] - cmin) / (cmax - cmin);
    g.fillStyle = color; g.beginPath(); g.arc(x, y, 4, 0, 6.3); g.fill();
    g.fillStyle = "#213547"; g.font = "bold 10px Arial";
    g.fillText(titulo, mx, y0 - 3);
    g.fillStyle = "#586c7c"; g.font = "9px Arial";
    g.fillText(cmax.toFixed(0), 4, y0 + 9);
    g.fillText(cmin.toFixed(0), 4, y0 + ph);
    g.fillText(unidad, W - 56, y0 - 3);
  }
  serie(JCURVE, mt, 5, 20, "#1565d8", "Flux de permeado J(t)", "L/m²·h");
  serie(CCURVE, mt + ph + gap, 7, 13, "#082e52", "C de proteína en el tanque", "g/L");
  g.fillStyle = "#586c7c"; g.font = "9px Arial";
  g.fillText("0", mx, H - 2); g.fillText("40 min", W - 40, H - 2);
}
function verInterior(on) {
  interiorOn = on;
  interiorG.visible = on;
  fibraG.visible = on;
  matMembrana.transparent = on;
  matMembrana.opacity = on ? 0.22 : 1.0;
  matMembrana.depthWrite = !on;
  matMembrana.needsUpdate = true;
  document.getElementById("panelInterior").style.display = on ? "block" : "none";
  document.getElementById("foul").style.display = (!on && cicloActual === "uf") ? "block" : "none";
  document.getElementById("btnInterior").classList.toggle("act", on);
  refrescarInterior();
  if (on) {
    vistaPrev = { pos: camera.position.clone(), tgt: controls.target.clone() };
    camera.position.set(1.45, 1.45, 2.25);
    controls.target.set(0.68, 1.1, 0.25);
  } else if (vistaPrev) {
    camera.position.copy(vistaPrev.pos);
    controls.target.copy(vistaPrev.tgt);
  }
  // dentro del interior, atenuar las tuberías externas para que no tapen
  Object.values(tubos).forEach(t => {
    t.mat.opacity = on ? 0.1 : (t.activo ? 0.95 : 0.13);
    t.particulas.forEach(q => (q.visible = !on && t.activo));
  });
}

// ------------------------------------------------------------- ciclos
const RUTAS = {
  off: [],
  uf: ["entradaLactosuero", "rechazoTanque", "permeadoTanque"],
  lavR: ["entradaAgua", "rechazoDrenaje"],
  lavP: ["entradaAgua", "permeadoCaneca"],
  quim: ["quimicoEntrada", "rechazoTanque"],
  retro: ["lavado", "aireLinea", "rechazoDrenaje"],
};
let cicloActual = "off";

function aplicarCiclo(c) {
  cicloActual = c;
  const activos = RUTAS[c];
  Object.entries(tubos).forEach(([id, t]) => {
    t.activo = activos.includes(id);
    t.mat.opacity = interiorOn ? 0.1 : (t.activo ? 0.95 : 0.13);
    t.particulas.forEach(p => (p.visible = t.activo && !interiorOn));
  });
  const abiertas = CICLOS[c].valvulas;
  pilotos.forEach((p, i) => {
    p.material.emissive.setHex(abiertas.includes(i + 1) ? 0xff9500 : 0x3a2400);
    p.material.color.setHex(abiertas.includes(i + 1) ? 0xffc04d : 0xf0a01a);
  });
  const regula = c === "uf" || c === "quim";
  volanteRojo.material.emissive.setHex(regula ? 0x661010 : 0x000000);
  const andando = c !== "off";
  pilotoBomba.material.emissive.setHex(andando ? 0xff9500 : 0x3a2400);
  pilotoBomba.material.color.setHex(andando ? 0xffc04d : 0xf0a01a);
  document.getElementById("detalleCiclo").innerHTML =
    "<b>" + CICLOS[c].etiqueta + "</b><br>" + CICLOS[c].detalle;
  document.getElementById("foul").style.display = (c === "uf" && !interiorOn) ? "block" : "none";
  document.querySelectorAll(".panelbtns button").forEach(b =>
    b.classList.toggle("act", b.dataset.c === c));
  reproduciendo = false;
  const bp = document.getElementById("btnPlay");
  if (bp) bp.textContent = "▶ Reproducir 0–40 min";
  // color de lo que circula por dentro de las fibras según el modo
  const colAlim = c === "uf" ? 0xd9cf9e : (c === "quim" ? 0x18b8c4 : 0x7fd4ff);
  pAlimFib.forEach(m => m.material.color.setHex(colAlim));
  const colAgua = c === "quim" ? 0x18b8c4 : (c === "uf" ? 0x4d9fe8 : 0x7fd4ff);
  fAgua.forEach(m => m.material.color.setHex(colAgua));
  if (c === "uf") setMinuto(minuto); else refrescarInterior();
}

const cont = document.getElementById("botones");
Object.keys(CICLOS).forEach(c => {
  const b = document.createElement("button");
  b.textContent = CICLOS[c].etiqueta;
  b.dataset.c = c;
  b.onclick = () => aplicarCiclo(c);
  cont.appendChild(b);
});
const bi = document.createElement("button");
bi.id = "btnInterior";
bi.textContent = "🔬 Interior de la membrana";
bi.onclick = () => verInterior(!interiorOn);
cont.appendChild(bi);
const slider = document.getElementById("min");
slider.oninput = () => setMinuto(+slider.value);
const sliderInt = document.getElementById("minInt");
sliderInt.oninput = () => setMinuto(+sliderInt.value);
document.getElementById("btnPlay").onclick = () => {
  if (minuto >= 40) setMinuto(0);
  reproduciendo = !reproduciendo;
  document.getElementById("btnPlay").textContent =
    reproduciendo ? "⏸ Pausar" : "▶ Reproducir 0–40 min";
};
aplicarCiclo("off");

// ------------------------------------------------------------- selección
const ray = new THREE.Raycaster();
const puntero = new THREE.Vector2();
let hover = null, bajada = null;

function meshEn(ev) {
  const r = canvas.getBoundingClientRect();
  puntero.x = ((ev.clientX - r.left) / r.width) * 2 - 1;
  puntero.y = -((ev.clientY - r.top) / r.height) * 2 + 1;
  ray.setFromCamera(puntero, camera);
  const hit = ray.intersectObjects(clicables, false);
  return hit.length ? hit[0].object : null;
}
function resaltar(cid, on) {
  clicables.forEach(o => {
    if (o.userData.cid === cid) {
      if (!o.userData.matProp) { o.material = o.material.clone(); o.userData.matProp = true; }
      o.material.emissive.setHex(on ? 0x1d4f82 : 0x000000);
    }
  });
}
canvas.addEventListener("pointermove", ev => {
  const m = meshEn(ev);
  const cid = m ? m.userData.cid : null;
  if (hover && hover !== cid) resaltar(hover, false);
  if (cid && cid !== hover) resaltar(cid, true);
  hover = cid;
  canvas.style.cursor = cid ? "pointer" : "grab";
});
canvas.addEventListener("pointerdown", ev => (bajada = [ev.clientX, ev.clientY]));
canvas.addEventListener("pointerup", ev => {
  if (!bajada) return;
  const dx = ev.clientX - bajada[0], dy = ev.clientY - bajada[1];
  bajada = null;
  if (dx * dx + dy * dy > 25) return;               // fue un arrastre, no un clic
  const m = meshEn(ev);
  if (!m || !m.userData.cid) return;
  const info = COMPONENTES[m.userData.cid];
  if (!info) return;
  document.getElementById("tN").textContent = info.nombre;
  document.getElementById("tD").textContent = info.desc;
  document.getElementById("tarjeta").style.display = "block";
});

// ------------------------------------------------------------- animación
const reloj = new THREE.Clock();
function animar() {
  requestAnimationFrame(animar);
  const dt = reloj.getDelta();
  if (interiorOn && reproduciendo && cicloActual === "uf") {
    setMinuto(minuto + dt * 2.2);                     // 40 min en ~18 s
    if (minuto >= 40) {
      reproduciendo = false;
      document.getElementById("btnPlay").textContent = "▶ Reproducir 0–40 min";
    }
  }
  if (interiorOn && (cicloActual === "quim" || cicloActual === "retro") && tortaNivel > 0) {
    tortaNivel = Math.max(0, tortaNivel - dt * (cicloActual === "quim" ? 0.07 : 0.1));
    refrescarInterior();
  }
  const jr = cicloActual === "uf"
    ? JRATIO[Math.min(Math.round(minuto), JRATIO.length - 1)]
    : 1 - 0.5 * tortaNivel;
  if (interiorOn) {
    const retro = cicloActual === "retro";
    const vAlim = cicloActual === "off" ? 0 : 0.35;
    pAlimFib.forEach(m => {
      m.visible = vAlim > 0 && !retro;
      if (!m.visible) return;
      m.userData.fase = (m.userData.fase + vAlim * dt) % 1;
      const f = FIBRAS[m.userData.f];
      m.position.set(0.95 + f[0], 0.57 + m.userData.fase * 1.02, f[1]);
    });
    pPermRad.forEach(m => {
      m.visible = cicloActual !== "off";
      if (!m.visible) return;
      const paso = (retro ? -1 : 1) * (0.55 * (retro ? 1 : jr)) * dt;
      m.userData.prog += paso;
      if (m.userData.prog > 1) { m.userData.prog = 0; m.userData.y = 0.6 + Math.random() * 0.9; }
      if (m.userData.prog < 0) { m.userData.prog = 1; m.userData.y = 0.6 + Math.random() * 0.9; }
      const f = FIBRAS[m.userData.f];
      const r0 = 0.014, r1 = 0.072;
      const r = r0 + (r1 - r0) * m.userData.prog;
      const cx = 0.95 + f[0] * (1 - m.userData.prog);     // converge hacia la carcasa
      m.position.set(cx + Math.cos(m.userData.ang) * r,
                     m.userData.y + m.userData.prog * 0.05,
                     f[1] * (1 - m.userData.prog) + Math.sin(m.userData.ang) * r);
    });
    pBurbujas.forEach(m => {
      m.visible = retro;
      if (!m.visible) return;
      m.userData.fase = (m.userData.fase + 0.3 * dt) % 1;
      m.position.set(0.95 + Math.cos(m.userData.ang) * m.userData.r,
                     0.57 + m.userData.fase * 1.02,
                     Math.sin(m.userData.ang) * m.userData.r);
    });
  }
  if (interiorOn && cicloActual !== "off") {
    const retroF = cicloActual === "retro";
    const fC = Math.max(0.03, 1 - 0.62 * tortaNivel);
    const rLum = Math.max(0.012, CAKE_R * fC - 0.01);
    const velF = cicloActual === "uf" ? 0.3 + 0.7 * jr : 1;
    fAgua.forEach(m => {
      m.visible = true;
      m.userData.fase = (m.userData.fase + 0.16 * velF * dt) % 1;
      let p = retroF ? 1 - m.userData.fase : m.userData.fase;
      const yBase = FY - FH * 0.485;
      if (p < m.userData.ySal) {                        // sube por el lumen
        m.position.set(FX + Math.cos(m.userData.ang) * Math.min(m.userData.r0, rLum * 0.8),
                       yBase + p * FH * 0.97,
                       FZ + Math.sin(m.userData.ang) * Math.min(m.userData.r0, rLum * 0.8));
      } else {                                          // atraviesa la pared
        const q = (p - m.userData.ySal) / (1 - m.userData.ySal);
        const r = rLum * 0.8 + (FR + 0.05 - rLum * 0.8) * q;
        m.position.set(FX + Math.cos(m.userData.ang) * r,
                       yBase + m.userData.ySal * FH * 0.97 + q * 0.04,
                       FZ + Math.sin(m.userData.ang) * r);
      }
    });
    const verProt = cicloActual === "uf";
    fProt.forEach(m => {
      m.visible = verProt;
      if (!verProt) return;
      m.userData.fase = (m.userData.fase + 0.11 * velF * dt) % 1;
      const r = Math.min(m.userData.r0, rLum * 0.55);
      m.position.set(FX + Math.cos(m.userData.ang + m.userData.fase * 2.5) * r,
                     FY - FH * 0.485 + m.userData.fase * FH * 0.97,
                     FZ + Math.sin(m.userData.ang + m.userData.fase * 2.5) * r);
    });
  } else { fAgua.forEach(m => (m.visible = false)); fProt.forEach(m => (m.visible = false)); }
  Object.entries(tubos).forEach(([id, t]) => {
    if (!t.activo) return;
    const esPermeado = id.startsWith("permeado");
    const v = 0.07 * (esPermeado ? jr : 1);
    t.particulas.forEach(p => {
      p.userData.fase = (p.userData.fase + v * dt) % 1;
      p.position.copy(t.curva.getPointAt(p.userData.fase));
    });
  });
  controls.update();
  renderer.render(scene, camera);
}
function ajustar() {
  const w = canvas.clientWidth || canvas.parentElement.clientWidth;
  const h = canvas.clientHeight || 640;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
canvas.style.width = "100%";
canvas.style.height = "640px";
window.addEventListener("resize", ajustar);
ajustar();
animar();

// =============================================================================
// MODO PRÁCTICA: el estudiante opera el tablero y la página revisa cada paso
// =============================================================================
const PROCED = {
  uf: { nombre: "🥛 Operación con lactosuero (V1+V2)", pasos: [
    { t: "Antes de conectar nada, deja todas las válvulas cerradas y la bomba apagada.",
      req: { valv: [], bomba: false } },
    { t: "Conecta la entrada al tanque de alimentación con el lactosuero preparado (80 L).",
      req: { valv: [], bomba: false, fuente: "tanque", contenido: "lactosuero" } },
    { t: "Ubica la válvula roja V9 en la vuelta 2, contada desde totalmente cerrada.",
      req: { v9: 2, bomba: false } },
    { t: "Abre únicamente V1 y V2 en el tablero (V3, V4 y V5 cerradas).",
      req: { valv: [1, 2], bomba: false } },
    { t: "Enciende la bomba y ajusta el rotámetro de entrada a unos 6 L/min.",
      req: { valv: [1, 2], bomba: true, caudal: [5.5, 6.5], v9: 2, fuente: "tanque", contenido: "lactosuero" } },
  ]},
  lavR: { nombre: "🚿 Enjuague de la línea de rechazo (V1+V3)", pasos: [
    { t: "Deja todas las válvulas cerradas y la bomba apagada.", req: { valv: [], bomba: false } },
    { t: "Conecta la entrada a la toma de agua de red.", req: { fuente: "red", bomba: false } },
    { t: "Abre V1 y V3.", req: { valv: [1, 3], bomba: false } },
    { t: "Enciende la bomba: el agua barre la línea de rechazo y sale por la manguera gruesa.",
      req: { valv: [1, 3], bomba: true, fuente: "red" }, inicia: "cond" },
    { t: "Mira el conductímetro y apaga la bomba cuando la conductividad esté entre 30 y 33 µS/cm.",
      req: { bomba: false, cond: true } },
    { t: "Termina cerrando todas las válvulas.", req: { valv: [], bomba: false } },
  ]},
  lavP: { nombre: "🚿 Enjuague de la línea de permeado (V1+V4)", pasos: [
    { t: "Deja todas las válvulas cerradas y la bomba apagada.", req: { valv: [], bomba: false } },
    { t: "Conecta la entrada a la toma de agua de red.", req: { fuente: "red", bomba: false } },
    { t: "Abre V1 y V4.", req: { valv: [1, 4], bomba: false } },
    { t: "Enciende la bomba: el agua limpia la manguera delgada del permeado y descarga en la caneca sobre la báscula.",
      req: { valv: [1, 4], bomba: true, fuente: "red" } },
    { t: "Termina: apaga la bomba y cierra todas las válvulas.", req: { valv: [], bomba: false } },
  ]},
  quim: { nombre: "🧪 Limpieza química con NaOH 1 %", pasos: [
    { t: "Deja todas las válvulas cerradas y la bomba apagada.", req: { valv: [], bomba: false } },
    { t: "Prepara la soda en el tanque de alimentación (~1 kg de NaOH en 80 L de agua, 1 %) y conecta la entrada al tanque.",
      req: { fuente: "tanque", contenido: "naoh", bomba: false } },
    { t: "Recircula la soda en modo V1+V2 (bomba encendida) para desintegrar la capa orgánica dentro del módulo.",
      req: { valv: [1, 2], bomba: true, fuente: "tanque", contenido: "naoh" } },
    { t: "Apaga la bomba, cierra las válvulas y cambia la entrada a la toma de agua limpia.",
      req: { valv: [], bomba: false, fuente: "red" } },
    { t: "Expulsa la soda de la línea de rechazo: V1+V3 con la bomba encendida.",
      req: { valv: [1, 3], bomba: true, fuente: "red" } },
    { t: "Expulsa la soda de la línea de permeado: V1+V4 con la bomba encendida (descarga a la caneca).",
      req: { valv: [1, 4], bomba: true, fuente: "red" } },
    { t: "Termina: apaga la bomba y cierra todas las válvulas.", req: { valv: [], bomba: false } },
  ]},
};

const POR_QUE = {   // explicación física de cada válvula sobrante o faltante
  extra: {
    1: "V1 es la entrada; aquí debería estar cerrada.",
    2: "V2 manda el flujo a la membrana y al permeado; en este paso no corresponde.",
    3: "V3 abre la línea de rechazo hacia afuera: el líquido se iría por la manguera gruesa en vez de volver al tanque por la V9.",
    4: "V4 es de enjuague: desvía el flujo por la línea de permeado hacia la caneca.",
    5: "V5 inyecta aire comprimido; solo se usa en el retrolavado.",
  },
  falta: {
    1: "V1 es la entrada: sin ella no pasa nada y la bomba empuja contra una válvula cerrada.",
    2: "Sin V2 el flujo no llega a la membrana y no sale permeado.",
    3: "Sin V3 el agua no barre la línea de rechazo.",
    4: "Sin V4 el agua no limpia la línea de permeado.",
    5: "Falta V5 (aire).",
  },
};

const pr = { on: false, proc: "uf", paso: 0, errores: 0, t0: 0, cond: 850, tCond: 0,
             st: { valv: [], bomba: false, v9: 9, fuente: "tanque", contenido: "agua", caudal: 0 } };

function iguales(a, b) { return a.length === b.length && a.every(x => b.includes(x)); }

function revisar(req) {
  const s = pr.st, err = [];
  if (req.valv) {
    req.valv.filter(v => !s.valv.includes(v)).forEach(v => err.push("Falta abrir V" + v + ". " + POR_QUE.falta[v]));
    s.valv.filter(v => !req.valv.includes(v)).forEach(v => err.push("V" + v + " debe estar cerrada. " + POR_QUE.extra[v]));
  }
  if (req.bomba === true && !s.bomba) err.push("La bomba debe estar encendida.");
  if (req.bomba === false && s.bomba && !req.cond)
    err.push("Apaga la bomba: válvulas y conexiones se cambian con la bomba apagada.");
  if (req.fuente && s.fuente !== req.fuente)
    err.push(req.fuente === "red" ? "La entrada debe ir a la toma de agua de red (los enjuagues son con agua limpia)."
                                  : "La entrada debe ir al tanque de alimentación.");
  if (req.contenido && s.contenido !== req.contenido)
    err.push(req.contenido === "naoh" ? "El tanque debe tener la solución de NaOH al 1 % (~1 kg en 80 L)."
                                      : "El tanque debe tener el lactosuero preparado.");
  if (req.v9 !== undefined && s.v9 !== req.v9)
    err.push(s.v9 < req.v9
      ? "La V9 está más cerrada que la vuelta 2: aumenta la restricción y la presión transmembrana (riesgo de pasar los 4 bar de la membrana)."
      : "La V9 está más abierta que la vuelta 2: el rechazo vuelve libre al tanque, baja la presión y casi no sale permeado.");
  if (req.caudal && (s.caudal < req.caudal[0] || s.caudal > req.caudal[1]))
    err.push("El rotámetro marca " + s.caudal.toFixed(1) + " L/min; ajústalo a unos 6 L/min.");
  if (req.cond) {
    if (s.bomba) err.push("Aún no has apagado la bomba.");
    else if (pr.cond > 33) err.push("Apagaste antes de tiempo: el conductímetro marca " + Math.round(pr.cond) +
                                    " µS/cm (> 33). La línea todavía no está limpia; vuelve a encender la bomba.");
  }
  return err;
}

function peligros() {
  const s = pr.st, w = [];
  if (s.bomba && !s.valv.includes(1)) w.push("Bomba encendida con V1 cerrada: trabaja contra una válvula cerrada.");
  if (s.bomba && s.valv.includes(2) && !s.valv.includes(3) && s.v9 === 0)
    w.push("V9 totalmente cerrada: el rechazo no tiene salida y la presión puede superar los 4 bar.");
  if (s.bomba && s.fuente === "tanque" && s.contenido === "lactosuero" && s.valv.includes(3))
    w.push("¡El lactosuero se está yendo por la línea de rechazo hacia afuera!");
  if (s.bomba && s.fuente === "tanque" && s.contenido === "lactosuero" && s.valv.includes(4))
    w.push("¡El lactosuero está saliendo por la línea de enjuague hacia la caneca!");
  return w;
}

function cicloDeEstado() {
  const s = pr.st;
  if (!s.bomba) return "off";
  if (iguales(s.valv, [1, 2])) return s.contenido === "naoh" && s.fuente === "tanque" ? "quim" : "uf";
  if (iguales(s.valv, [1, 3])) return "lavR";
  if (iguales(s.valv, [1, 4])) return "lavP";
  if (iguales(s.valv, [5])) return "retro";
  return "off";
}

function pintarPractica() {
  aplicarCiclo(cicloDeEstado());
  const s = pr.st;
  pilotos.forEach((p, i) => {
    const on = s.valv.includes(i + 1);
    p.material.emissive.setHex(on ? 0xff9500 : 0x3a2400);
    p.material.color.setHex(on ? 0xffc04d : 0xf0a01a);
  });
  pilotoBomba.material.emissive.setHex(s.bomba ? 0xff9500 : 0x3a2400);
  volanteRojo.material.emissive.setHex(s.v9 <= 1 ? 0xaa1010 : (s.v9 === 2 ? 0x661010 : 0x200000));
  document.querySelectorAll("#prTab button[data-v]").forEach(b =>
    b.classList.toggle("act", s.valv.includes(+b.dataset.v)));
  document.getElementById("prBomba").classList.toggle("act", s.bomba);
  document.getElementById("prBomba").textContent = s.bomba ? "BOMBA: ENCENDIDA" : "BOMBA: apagada";
  document.getElementById("prV9").textContent = s.v9;
  document.getElementById("prCau").textContent = s.caudal.toFixed(1);
  const w = peligros();
  document.getElementById("prPeligro").innerHTML = w.map(x => "⚠️ " + x).join("<br>");
  document.getElementById("prPeligro").style.display = w.length ? "block" : "none";
  const condVis = pr.proc === "lavR" && pr.paso >= 3;
  document.getElementById("prCond").style.display = condVis ? "block" : "none";
  document.getElementById("prCondV").textContent = Math.round(pr.cond);
  const p = PROCED[pr.proc];
  document.getElementById("prPasos").innerHTML = p.pasos.map((x, i) =>
    '<li class="' + (i < pr.paso ? "ok" : (i === pr.paso ? "cur" : "")) + '">' +
    (i < pr.paso ? "✅ " : "") + x.t + "</li>").join("");
  document.getElementById("detalleCiclo").innerHTML =
    "<b>🎮 Modo práctica: " + p.nombre + "</b><br>" +
    (pr.paso < p.pasos.length ? "Paso " + (pr.paso + 1) + " de " + p.pasos.length + ": " + p.pasos[pr.paso].t
                              : "Procedimiento terminado.");
}

function reiniciarPractica() {
  pr.paso = 0; pr.errores = 0; pr.t0 = Date.now(); pr.cond = 850; pr.tCond = 0;
  pr.st = { valv: [], bomba: false, v9: 9, fuente: "tanque", contenido: "agua", caudal: 0 };
  // en los enjuagues la V9 ya queda en su posición de trabajo
  if (pr.proc !== "uf") pr.st.v9 = 2;
  document.getElementById("prFuente").value = pr.st.fuente;
  document.getElementById("prCont").value = pr.st.contenido;
  document.getElementById("prMsg").innerHTML = "";
  document.getElementById("prFin").style.display = "none";
  pintarPractica();
}

function comprobarPaso() {
  const p = PROCED[pr.proc];
  if (pr.paso >= p.pasos.length) return;
  const err = revisar(p.pasos[pr.paso].req);
  const msg = document.getElementById("prMsg");
  if (err.length) {
    pr.errores += 1;
    msg.className = "mal";
    msg.innerHTML = "<b>Revisa:</b><ul>" + err.map(e => "<li>" + e + "</li>").join("") + "</ul>";
    return;
  }
  msg.className = "bien";
  msg.innerHTML = "✅ ¡Correcto! " + (pr.paso + 1 < p.pasos.length ? "Sigue con el próximo paso." : "");
  if (p.pasos[pr.paso].inicia === "cond") { pr.cond = 850; pr.tCond = 0; }
  pr.paso += 1;
  if (pr.paso >= p.pasos.length) {
    const nota = Math.max(0, 100 - 10 * pr.errores);
    const seg = Math.round((Date.now() - pr.t0) / 1000);
    document.getElementById("prFin").style.display = "block";
    document.getElementById("prFin").innerHTML =
      "🏁 <b>¡Procedimiento completo!</b><br>Puntaje: <b>" + nota + "/100</b> · " +
      pr.errores + " intento(s) fallido(s) · " + Math.floor(seg / 60) + " min " + (seg % 60) + " s" +
      (nota === 100 ? "<br>¡Perfecto! Ya puedes hacerlo en el laboratorio." :
                      "<br>Repítelo hasta hacerlo sin errores.");
    msg.innerHTML = ""; msg.className = "";
  }
  pintarPractica();
}

function modoPractica(on) {
  pr.on = on;
  document.getElementById("panelPractica").style.display = on ? "block" : "none";
  document.getElementById("tarjeta").style.display = "none";
  document.getElementById("btnPractica").classList.toggle("act", on);
  document.querySelectorAll(".panelbtns button[data-c]").forEach(b => (b.style.display = on ? "none" : ""));
  document.getElementById("leyenda").style.display = on ? "none" : "";
  if (on) { if (interiorOn) verInterior(false); reiniciarPractica(); }
  else aplicarCiclo("off");
}

(function construirPractica() {
  const b = document.createElement("button");
  b.id = "btnPractica";
  b.textContent = "🎮 Modo práctica";
  b.onclick = () => modoPractica(!pr.on);
  document.getElementById("botones").appendChild(b);
  const sel = document.getElementById("prProc");
  Object.entries(PROCED).forEach(([k, v]) => {
    const o = document.createElement("option"); o.value = k; o.textContent = v.nombre; sel.appendChild(o);
  });
  sel.onchange = () => { pr.proc = sel.value; reiniciarPractica(); };
  document.querySelectorAll("#prTab button[data-v]").forEach(btn => btn.onclick = () => {
    const v = +btn.dataset.v, s = pr.st;
    s.valv = s.valv.includes(v) ? s.valv.filter(x => x !== v) : s.valv.concat([v]).sort();
    pintarPractica();
  });
  document.getElementById("prBomba").onclick = () => {
    pr.st.bomba = !pr.st.bomba;
    if (pr.st.bomba && pr.st.caudal === 0) pr.st.caudal = 3.0;
    if (!pr.st.bomba) pr.st.caudal = 0;
    pintarPractica();
  };
  document.getElementById("prV9m").onclick = () => { pr.st.v9 = Math.max(0, pr.st.v9 - 1); pintarPractica(); };
  document.getElementById("prV9p").onclick = () => { pr.st.v9 = Math.min(9, pr.st.v9 + 1); pintarPractica(); };
  document.getElementById("prCm").onclick = () => { if (pr.st.bomba) pr.st.caudal = Math.max(0.5, pr.st.caudal - 0.5); pintarPractica(); };
  document.getElementById("prCp").onclick = () => { if (pr.st.bomba) pr.st.caudal = Math.min(10, pr.st.caudal + 0.5); pintarPractica(); };
  document.getElementById("prFuente").onchange = e => { pr.st.fuente = e.target.value; pintarPractica(); };
  document.getElementById("prCont").onchange = e => { pr.st.contenido = e.target.value; pintarPractica(); };
  document.getElementById("prComprobar").onclick = comprobarPaso;
  document.getElementById("prReiniciar").onclick = reiniciarPractica;
  // conductímetro: baja mientras corre el enjuague de rechazo con agua de red
  setInterval(() => {
    if (!pr.on || pr.proc !== "lavR" || pr.paso < 4) return;
    const s = pr.st;
    if (s.bomba && s.fuente === "red" && iguales(s.valv, [1, 3])) {
      pr.tCond += 0.25;
      pr.cond = 31 + (850 - 31) * Math.exp(-pr.tCond / 7);
      document.getElementById("prCondV").textContent = Math.round(pr.cond);
      document.getElementById("prCondM").textContent = (pr.tCond * 10 / 45).toFixed(1);
    }
  }, 250);
})();
