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
cil(tcontrol, 0.02, 0.025, M.verde, -0.05, 1.52, -0.115, "x");      // switch general
const pilotos = [];
for (let i = 0; i < 5; i++) {                                       // pilotos V1–V5
  const p = cil(tcontrol, 0.016, 0.02, M.naranja.clone(), -0.25 + i * 0.1, 1.42, -0.115, "x");
  pilotos.push(p);
}
for (let i = 0; i < 5; i++)                                         // perillas MAN-0-AUTO
  cil(tcontrol, 0.014, 0.022, M.negro, -0.25 + i * 0.1, 1.33, -0.115, "x");
for (let i = 0; i < 2; i++) {                                       // dosificadora y bomba
  cil(tcontrol, 0.016, 0.02, M.naranja.clone(), -0.1 + i * 0.1, 1.22, -0.115, "x");
  cil(tcontrol, 0.014, 0.022, M.negro, -0.1 + i * 0.1, 1.13, -0.115, "x");
}
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
caja(bAli, 0.22, 0.16, 0.16, M.azulBomba, -0.25, 0.45, 0.12);
cil(bAli, 0.07, 0.1, M.azulBomba, -0.09, 0.43, 0.12, "z");
caja(bAli, 0.26, 0.03, 0.2, M.aceroOsc, -0.22, 0.375, 0.12);
registrar(bAli);

const bRetro = grupo("bombaRetrolavado");
caja(bRetro, 0.16, 0.12, 0.12, M.acero, 0.28, 0.43, -0.08);
cil(bRetro, 0.05, 0.08, M.azulBomba, 0.39, 0.42, -0.08, "z");
registrar(bRetro);

const bDos = grupo("bombaDosificadora");
caja(bDos, 0.1, 0.13, 0.09, M.verde, 0.62, 1.45, -0.12);
cil(bDos, 0.025, 0.05, M.blanco, 0.62, 1.54, -0.12);
registrar(bDos);

// ------------------------------------------------------------- tanques
const tQuim = grupo("tanqueQuimico");
cil(tQuim, 0.085, 0.24, M.blanco, 0.5, 0.48, 0.22);
cil(tQuim, 0.045, 0.04, M.rojo, 0.5, 0.62, 0.22);
registrar(tQuim);

const tLav = grupo("tanqueLavado");
cil(tLav, 0.21, 0.72, M.blancoMate, -1.12, 0.72, -0.05);
cil(tLav, 0.215, 0.045, M.rojo, -1.12, 1.1, -0.05);
cil(tLav, 0.16, 0.06, M.acero, -1.12, 0.33, -0.05);
registrar(tLav);

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
cil(aire, 0.03, 0.16, M.acero, 0.5, 0.78, -0.22);
cil(aire, 0.024, 0.012, M.blancoMate, 0.5, 0.88, -0.205, "x");
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
  [-0.95, 0.9, 0.8], [-0.78, 0.6, 0.5], [-0.42, 0.45, 0.2], [-0.2, 0.45, 0.14],
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
  [-1.12, 1.12, -0.05], [-0.7, 0.7, -0.18], [0.1, 0.46, -0.12], [0.33, 0.44, -0.08],
  [0.7, 0.44, -0.04], [0.9, 0.5, 0.0]]);
tubo("aireLinea", C.aire, [
  [0.5, 0.86, -0.2], [0.72, 0.62, -0.14], [0.88, 0.52, -0.04]], 0.012);

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
    t.mat.opacity = t.activo ? 0.95 : 0.13;
    t.particulas.forEach(p => (p.visible = t.activo));
  });
  const abiertas = CICLOS[c].valvulas;
  pilotos.forEach((p, i) => {
    p.material.emissive.setHex(abiertas.includes(i + 1) ? 0xff9500 : 0x3a2400);
    p.material.color.setHex(abiertas.includes(i + 1) ? 0xffc04d : 0xf0a01a);
  });
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
