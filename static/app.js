const cfg = window.VOTO_CONFIG;
const draw = document.getElementById('myCanvas');
const ctx = draw.getContext('2d');
const overlay = document.getElementById('ballot-overlay');
const bg = overlay.getContext('2d');
const selCol = document.getElementById('columna');
const selParty = document.getElementById('partido');
const box = {x: 58, y: 58, size: 84};
let strokesByBox = {};
let currentStroke = null;
let drawing = false;
let predictionTimer = null;
let predictionVersion = 0;
let predictionController = null;
const predictionRows = document.getElementById('prediction-rows');
const predictionSummary = document.getElementById('prediction-summary');
const predictionWarning = document.getElementById('prediction-warning');

function clearPrediction(message = 'Dibuja una marca para ver las categorías.') {
  clearTimeout(predictionTimer);
  predictionVersion++;
  if (predictionController) predictionController.abort();
  predictionController = null;
  predictionRows.replaceChildren();
  predictionSummary.textContent = message;
  predictionSummary.className = 'small';
  predictionWarning.textContent = '';
}
function showPrediction(data) {
  predictionRows.replaceChildren();
  for (const item of data.probabilidades) {
    const row = document.createElement('div');
    row.className = 'probability-row';
    const name = document.createElement('span');
    name.className = 'probability-name';
    name.textContent = item.nombre;
    const value = document.createElement('span');
    value.textContent = String(item.probabilidad);
    const track = document.createElement('div');
    track.className = 'probability-track';
    track.setAttribute('role', 'progressbar');
    track.setAttribute('aria-label', item.nombre);
    track.setAttribute('aria-valuemin', '0');
    track.setAttribute('aria-valuemax', '100');
    track.setAttribute('aria-valuenow', String(100 * item.probabilidad));
    const bar = document.createElement('span');
    bar.style.width = (100 * item.probabilidad) + '%';
    track.append(bar);
    row.append(name, value, track);
    predictionRows.append(row);
  }
  predictionSummary.textContent = `La categoría más probable es: ${data.nombre} (${data.confianza})`;
  predictionSummary.className = 'small';
  predictionWarning.textContent = data.confianza < cfg.umbral
    ? 'Seguridad baja, esta marca iría a revisión' : '';
}
function schedulePrediction() {
  clearPrediction();
  if (!hasMark(key())) return;
  predictionSummary.textContent = 'Consultando modelo...';
  const version = predictionVersion;
  const slot = key();
  const image = draw.toDataURL('image/png');
  predictionTimer = setTimeout(async () => {
    const controller = new AbortController();
    predictionController = controller;
    try {
      const response = await fetch('/api/predecir', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({myImage: image}), signal: controller.signal
      });
      const data = await response.json();
      if (version !== predictionVersion || slot !== key() || drawing) return;
      if (!response.ok || !data.ok) throw Error(data.error || 'No se pudo usar el modelo.');
      showPrediction(data);
    } catch (error) {
      if (error.name === 'AbortError' || version !== predictionVersion || slot !== key()) return;
      predictionSummary.textContent = error.message === 'Failed to fetch'
        ? 'No se pudo consultar el modelo.' : error.message;
      predictionSummary.className = 'small error-text';
    } finally {
      if (predictionController === controller) predictionController = null;
    }
  }, 500);
}
function changeSelection() {
  stopDrawing();
  redraw();
  schedulePrediction();
}

function key(col = +selCol.value, party = +selParty.value) { return `${col}_${party}`; }
function strokes() { return strokesByBox[key()] || []; }
function selectedRect(col = +selCol.value, party = +selParty.value) {
  return {x: cfg.xs[col], y: cfg.ys[party], width: 54, height: 54};
}
function linePath(context, points) {
  if (!points.length) return;
  context.beginPath();
  context.lineCap = 'round';
  context.lineJoin = 'round';
  context.lineWidth = 7;
  context.strokeStyle = '#101010';
  context.moveTo(points[0].x, points[0].y);
  if (points.length === 1) context.lineTo(points[0].x + 0.01, points[0].y + 0.01);
  for (let i=1; i<points.length; i++) context.lineTo(points[i].x, points[i].y);
  context.stroke();
}
function renderCanvas() {
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, draw.width, draw.height);
  ctx.strokeStyle = '#222';
  ctx.lineWidth = 2;
  ctx.strokeRect(box.x, box.y, box.size, box.size);
  for (const points of strokes()) linePath(ctx, points);
}
function renderBallot() {
  bg.clearRect(0,0,overlay.width,overlay.height);
  for (const [slot, lines] of Object.entries(strokesByBox)) {
    const [col, party] = slot.split('_').map(Number);
    const rect = selectedRect(col,party);
    const scale = rect.width / box.size;
    bg.save();
    bg.translate(rect.x - box.x * scale, rect.y - box.y * scale);
    bg.scale(scale,scale);
    for (const points of lines) linePath(bg,points);
    bg.restore();
  }
  const rect = selectedRect();
  bg.strokeStyle = '#d99a2b';
  bg.lineWidth = 3;
  bg.setLineDash([5,4]);
  bg.strokeRect(rect.x - 1, rect.y - 1, rect.width + 2, rect.height + 2);
  bg.setLineDash([]);
}
function redraw() { renderCanvas(); renderBallot(); }
function getPoint(ev) {
  const r = draw.getBoundingClientRect();
  return {x: Math.min(199, Math.max(0, (ev.clientX-r.left)*draw.width/r.width)),
          y: Math.min(199, Math.max(0, (ev.clientY-r.top)*draw.height/r.height))};
}
draw.addEventListener('pointerdown', ev => {
  if (ev.button !== undefined && ev.button !== 0) return;
  ev.preventDefault();
  draw.setPointerCapture(ev.pointerId);
  clearPrediction('Termina el trazo para ver las categorías.');
  drawing = true;
  const k=key();
  if (!strokesByBox[k]) strokesByBox[k]=[];
  currentStroke=[getPoint(ev)];
  strokesByBox[k].push(currentStroke);
  redraw();
});
draw.addEventListener('pointermove', ev => {
  if (!drawing) return;
  currentStroke.push(getPoint(ev));
  redraw();
});
function stopDrawing() { drawing=false; currentStroke=null; }
function finishStroke() {
  if (!drawing) return;
  stopDrawing();
  schedulePrediction();
}
draw.addEventListener('pointerup', finishStroke);
draw.addEventListener('pointercancel', finishStroke);
draw.addEventListener('lostpointercapture', finishStroke);
overlay.addEventListener('click', ev => {
  const r=overlay.getBoundingClientRect();
  const x=(ev.clientX-r.left)*overlay.width/r.width;
  const y=(ev.clientY-r.top)*overlay.height/r.height;
  const col=cfg.xs.findIndex(start => x>=start-3 && x<=start+57);
  const party=cfg.ys.findIndex(start => y>=start && y<=start+54);
  if (col>=0 && party>=0) {selCol.value=col; selParty.value=party; changeSelection();}
  else say('Selecciona una casilla de la cédula.');
});
selCol.addEventListener('change',changeSelection);
selParty.addEventListener('change',changeSelection);
document.getElementById('borrar').addEventListener('click',() => {stopDrawing();delete strokesByBox[key()];redraw();clearPrediction();say('Casilla borrada.');});
document.getElementById('borrar-todo').addEventListener('click',()=> {stopDrawing();strokesByBox={};redraw();clearPrediction();say('Cédula limpia.');});
function say(message, css='') {
  const e=document.getElementById('mensaje'); e.textContent=message; e.className='message '+css;
}
function pngOfSlot(slot) {
  const save=key();
  const [col,party]=slot.split('_');
  selCol.value=col; selParty.value=party;
  renderCanvas();
  const image=draw.toDataURL('image/png');
  const [oldC,oldP]=save.split('_');
  selCol.value=oldC;selParty.value=oldP;
  renderCanvas();
  return image;
}
function hasMark(slot) {return (strokesByBox[slot] || []).length>0;}
  fetch('/api/modelo').then(r=>r.json()).then(data=>{
    document.getElementById('ml-status').textContent=data.entrenado
      ? 'Modelo disponible.'
      : 'Todavía no hay modelo entrenado.';
  }).catch(() => { document.getElementById('ml-status').textContent='No se pudo consultar el modelo.'; });
  document.getElementById('registrar').addEventListener('click',async()=>{
    const marks=[];
    for(const slot of Object.keys(strokesByBox)) if(hasMark(slot)){
      const [col,party]=slot.split('_').map(Number);
      marks.push({columna:col,partido:party,imagen:pngOfSlot(slot)});
    }
    redraw();
    const button=document.getElementById('registrar');button.disabled=true;
    try{
      const r=await fetch('/api/registrar-voto',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({marcas:marks})});
      const d=await r.json();if(!r.ok)throw Error(d.error||'No se pudo registrar.');
      stopDrawing();strokesByBox={};redraw();clearPrediction();
      say(`Cédula guardada. Columnas por revisar: ${d.pendientes}.`, 'ok');
      const a=document.createElement('a');a.href='/resultados';a.textContent='Ver resultados';
      document.getElementById('mensaje').append(' · ',a);
    }catch(err){say(err.message,'error');}finally{button.disabled=false;}
  });
redraw();
