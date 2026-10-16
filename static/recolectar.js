const canvas = document.getElementById('myCanvas');
const ctx = canvas.getContext('2d');
const categoria = document.getElementById('numero');
const guardar = document.getElementById('guardar');
let dibujando = false;
let tieneMarca = false;
function mensaje(texto, tipo = '') {
  const elemento = document.getElementById('mensaje');
  elemento.textContent = texto;
  elemento.className = 'message ' + tipo;
}
function borrar() {
  dibujando = false;
  tieneMarca = false;
  ctx.fillStyle = 'white';
  ctx.fillRect(0, 0, 200, 200);
  ctx.strokeStyle = '#222';
  ctx.lineWidth = 2;
  ctx.strokeRect(58, 58, 84, 84);
}
function punto(evento) {
  const rect = canvas.getBoundingClientRect();
  return {x: Math.max(0, Math.min(199, (evento.clientX - rect.left) * 200 / rect.width)),
          y: Math.max(0, Math.min(199, (evento.clientY - rect.top) * 200 / rect.height))};
}
canvas.addEventListener('pointerdown', evento => {
  if (guardar.disabled || evento.button !== 0) return;
  evento.preventDefault();
  canvas.setPointerCapture(evento.pointerId);
  const p = punto(evento);
  dibujando = true;
  tieneMarca = true;
  ctx.beginPath();
  ctx.lineWidth = 7;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.strokeStyle = '#101010';
  ctx.moveTo(p.x, p.y);
  ctx.lineTo(p.x + 0.01, p.y + 0.01);
  ctx.stroke();
});
canvas.addEventListener('pointermove', evento => {
  if (!dibujando) return;
  const p = punto(evento);
  ctx.lineTo(p.x, p.y);
  ctx.stroke();
});
for (const evento of ['pointerup', 'pointercancel', 'lostpointercapture']) {
  canvas.addEventListener(evento, () => { dibujando = false; });
}
function mostrarConteos(conteos) {
  const lista = document.getElementById('counters');
  lista.replaceChildren();
  for (const [clase, nombre] of Object.entries(window.CATEGORIAS)) {
    const fila = document.createElement('p');
    fila.textContent = nombre + ': ' + (conteos[clase] || 0);
    lista.append(fila);
  }
}
categoria.addEventListener('change', () => {
  borrar();
  mensaje('');
});
document.getElementById('borrar').addEventListener('click', () => { borrar(); mensaje(''); });
guardar.addEventListener('click', async () => {
  if (!tieneMarca) { mensaje('Primero dibuja una marca.', 'error'); return; }
  dibujando = false;
  guardar.disabled = true;
  categoria.disabled = true;
  document.getElementById('borrar').disabled = true;
  try {
    const respuesta = await fetch('/upload', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({numero: categoria.value, myImage: canvas.toDataURL('image/png')})
    });
    const datos = await respuesta.json();
    if (!respuesta.ok) throw Error(datos.error || 'No se pudo guardar.');
    mostrarConteos(datos.conteos);
    borrar();
    mensaje('Dibujo guardado', 'ok');
  } catch (error) { mensaje(error.message, 'error'); }
  finally {
    guardar.disabled = false;
    categoria.disabled = false;
    document.getElementById('borrar').disabled = false;
  }
});
borrar();
fetch('/api/estadisticas-dataset').then(r => {
  if (!r.ok) throw Error('No se pudieron cargar los conteos.');
  return r.json();
}).then(datos => mostrarConteos(datos.conteos)).catch(error => mensaje(error.message, 'error'));
