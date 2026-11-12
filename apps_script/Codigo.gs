// =============================================================================
// Apps Script para guardar los registros del Gemelo Digital UF en esta hoja.
// Pegar en: Extensiones > Apps Script (desde la hoja "Registros Gemelo UF").
// Luego: Implementar > Nueva implementación > Aplicación web
//        Ejecutar como: Yo   |   Quién tiene acceso: Cualquier usuario
// =============================================================================

// Cambia esta clave por una tuya y pon LA MISMA en los Secrets de Streamlit.
const TOKEN = "CAMBIA_ESTA_CLAVE";

const COLUMNAS = ["nombre", "correo", "tipo_practica", "archivo", "tamano_kb",
                  "fecha", "estado", "observaciones"];

function hoja_() {
  const libro = SpreadsheetApp.getActiveSpreadsheet();
  let hoja = libro.getSheetByName("registros");
  if (!hoja) hoja = libro.insertSheet("registros");
  if (hoja.getLastRow() === 0) hoja.appendRow(COLUMNAS);
  return hoja;
}

function respuesta_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// GET: devuelve todos los registros
function doGet(e) {
  if (e.parameter.token !== TOKEN) return respuesta_({ok: false, error: "token inválido"});
  const datos = hoja_().getDataRange().getDisplayValues();
  const filas = datos.slice(1).map(f => {
    const o = {};
    COLUMNAS.forEach((c, i) => o[c] = f[i]);
    return o;
  });
  return respuesta_({ok: true, filas: filas});
}

// POST: agrega un registro o cambia el estado de uno
function doPost(e) {
  const p = JSON.parse(e.postData.contents);
  if (p.token !== TOKEN) return respuesta_({ok: false, error: "token inválido"});
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const hoja = hoja_();
    if (p.accion === "agregar") {
      hoja.appendRow(COLUMNAS.map(c => "'" + String(p.fila[c] ?? "")));
    } else if (p.accion === "estado") {
      // fila 1 = encabezados, así que el registro con índice i está en la fila i + 2
      hoja.getRange(Number(p.indice) + 2, COLUMNAS.indexOf("estado") + 1).setValue(p.estado);
    } else {
      return respuesta_({ok: false, error: "acción desconocida"});
    }
    return respuesta_({ok: true});
  } finally {
    lock.releaseLock();
  }
}
