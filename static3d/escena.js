/* Escena 3D del equipo de ultrafiltración MARTIN MTUF-PVC-4046 (AI-UF-1-4).
   Geometría esquemática construida con primitivas; topología según manual,
   tesis y P&ID (RIELCO). Dimensiones y recorridos: supuestos de representación. */

const COMPONENTES = __COMPONENTES__;
const CICLOS = __CICLOS__;
const JRATIO = __JRATIO__;   // J(t)/J0 del modelo de Hermia, t = 0..40 min

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

const bDos = grupo("bombaDosificadora");
caja(bDos, 0.1, 0.13, 0.09, M.verde, 0.62, 1.45, -0.12);
cil(bDos, 0.025, 0.05, M.blanco, 0.62, 1.54, -0.12);
registrar(bDos);

// ------------------------------------------------------------- tanques
function barril(cid, x, z, r, h) {
  const g = grupo(cid);
  caja(g, r * 2.6, 0.06, r * 2.6, M.acero, x, 0.07, z);             // báscula
  cil(g, r, h, M.azulBarril, x, 0.1 + h / 2, z);
  cil(g, r + 0.012, 0.03, M.azulTapa, x, 0.1 + h + 0.015, z);
  cil(g, r + 0.008, 0.025, M.azulTapa, x, 0.1 + h * 0.4, z);        // aro
  registrar(g);
  return g;
}
barril("tanqueAlimentacion", -0.95, 0.8, 0.25, 0.78);
barril("tanquePermeado", 1.18, 0.85, 0.19, 0.58);

// ------------------------------------------------------------- otros
const vRoja = grupo("valvulaRoja");
cil(vRoja, 0.06, 0.028, M.rojo, 0.25, 0.95, -0.4, "x");
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
  [-0.95, 0.35, 0.8], [-0.75, 0.12, 0.7], [-0.52, 0.1, 0.62], [-0.44, 0.3, 0.4],
  [-0.52, 0.6, 0.06], [-0.52, 1.2, 0.02], [-0.3, 1.12, 0.1], [0.3, 0.6, 0.12],
  [0.75, 0.5, 0.08], [0.9, 0.52, 0.03]]);
tubo("entradaAgua", C.ent, [
  [-1.5, 1.42, -0.3], [-1.2, 1.0, -0.1], [-0.7, 0.55, 0.12], [-0.2, 0.45, 0.14],
  [-0.52, 0.6, 0.06], [-0.52, 1.2, 0.02], [-0.3, 1.12, 0.1], [0.3, 0.6, 0.12],
  [0.75, 0.5, 0.08], [0.9, 0.52, 0.03]]);
tubo("rechazoTanque", C.rec, [
  [1.0, 1.56, 0], [0.8, 1.7, -0.2], [0.1, 1.52, -0.38], [-0.6, 1.2, -0.05],
  [-0.9, 1.0, 0.55], [-0.95, 0.92, 0.78]]);
tubo("rechazoDrenaje", C.rec, [
  [1.0, 1.56, 0], [1.12, 1.2, 0.2], [0.85, 0.6, 0.7], [0.5, 0.15, 1.18]]);
tubo("permeadoTanque", C.per, [
  [0.95, 1.75, 0], [1.08, 1.8, 0.12], [1.32, 1.25, 0.45], [1.18, 0.78, 0.82]]);
tubo("permeadoDrenaje", C.per, [
  [0.95, 1.75, 0], [0.8, 1.6, 0.35], [0.55, 0.7, 0.95], [0.42, 0.12, 1.2]]);
tubo("lavado", C.lav, [
  [-0.95, 0.35, 0.72], [-0.5, 0.2, 0.35], [-0.1, 0.3, 0.02], [0.14, 0.42, 0.06],
  [0.32, 0.44, 0.08], [0.7, 0.44, 0.02], [0.9, 0.5, 0.0]]);
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
let interiorOn = false;
let vistaPrev = null;
function verInterior(on) {
  interiorOn = on;
  interiorG.visible = on;
  matMembrana.transparent = on;
  matMembrana.opacity = on ? 0.22 : 1.0;
  matMembrana.depthWrite = !on;
  matMembrana.needsUpdate = true;
  document.getElementById("interiorInfo").style.display = on ? "block" : "none";
  document.getElementById("btnInterior").classList.toggle("act", on);
  if (on) {
    vistaPrev = { pos: camera.position.clone(), tgt: controls.target.clone() };
    camera.position.set(2.15, 1.25, 1.3);
    controls.target.set(0.95, 1.1, 0);
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
  lavP: ["entradaAgua", "permeadoDrenaje"],
  retro: ["lavado", "aireLinea", "rechazoDrenaje"],
};
let cicloActual = "off";
let minuto = 0;

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
  const andando = c !== "off";
  pilotoBomba.material.emissive.setHex(andando ? 0xff9500 : 0x3a2400);
  pilotoBomba.material.color.setHex(andando ? 0xffc04d : 0xf0a01a);
  document.getElementById("detalleCiclo").innerHTML =
    "<b>" + CICLOS[c].etiqueta + "</b><br>" + CICLOS[c].detalle;
  document.getElementById("foul").style.display = c === "uf" ? "block" : "none";
  document.querySelectorAll(".panelbtns button").forEach(b =>
    b.classList.toggle("act", b.dataset.c === c));
  if (c !== "uf") pintarFouling(0);
}

function pintarFouling(min) {
  const jr = JRATIO[Math.min(min, JRATIO.length - 1)];
  const avance = (1 - jr) / (1 - JRATIO[JRATIO.length - 1]);   // 0 limpio → 1 sucio (40 min)
  const col = new THREE.Color(0xf2f2ee).lerp(new THREE.Color(0xcfa05e), avance);
  cuerpoMembrana.material.color.copy(col);
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
slider.oninput = () => {
  minuto = +slider.value;
  document.getElementById("minv").textContent = minuto;
  pintarFouling(minuto);
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
  document.getElementById("tF").innerHTML = "<b>Fuente:</b> " + info.fuente +
    "<br><b>Geometría:</b> proporciones supuestas (esquemática)";
  document.getElementById("tarjeta").style.display = "block";
});

// ------------------------------------------------------------- animación
const reloj = new THREE.Clock();
function animar() {
  requestAnimationFrame(animar);
  const dt = reloj.getDelta();
  const jr = cicloActual === "uf" ? JRATIO[Math.min(minuto, JRATIO.length - 1)] : 1;
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
