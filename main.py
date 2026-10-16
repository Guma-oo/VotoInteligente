"""recolección y votación de práctica."""
import base64
import csv
import io
import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for
from PIL import Image, ImageOps

from config import (BALLOT_HEIGHT, BALLOT_WIDTH, BOXES_X, BOXES_Y,
                    CATEGORIES, CONFIDENCE_THRESHOLD, CONTESTS, DRAW_SIZE,
                    PARTIES)

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / 'dataset'
DATA = ROOT / 'data'
MODELS = ROOT / 'models'
METADATA = DATA / 'muestras.csv'
BALLOTS = DATA / 'cedulas.json'
GUARDADOS = DATA / 'dibujos_voto'
DB_LOCK = threading.RLock()
ML_LOCK = threading.Lock()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024


def init_folders():
    for category in CATEGORIES:
        (DATASET / category).mkdir(parents=True, exist_ok=True)
    GUARDADOS.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    if not BALLOTS.exists():
        BALLOTS.write_text('[]', encoding='utf-8')
    if not METADATA.exists():
        with METADATA.open('w', newline='', encoding='utf-8') as file:
            csv.writer(file).writerow(['archivo', 'categoria', 'columna', 'partido', 'dibujante', 'fecha_utc'])


def counts():
    return {category: len(list((DATASET / category).glob('*.png'))) for category in CATEGORIES}


def read_image(data_url):
    """valida el dibujo del canvas."""
    if not isinstance(data_url, str) or not data_url.startswith('data:image/png;base64,'):
        raise ValueError('Se necesita un dibujo PNG del canvas.')
    try:
        raw = base64.b64decode(data_url.split(',', 1)[1], validate=True)
        if len(raw) > 650_000:
            raise ValueError('Imagen demasiado grande.')
        image = Image.open(io.BytesIO(raw))
        image.load()
        if image.format != 'PNG' or image.size != (DRAW_SIZE, DRAW_SIZE):
            raise ValueError('Se espera un PNG de 200 x 200 píxeles.')
        image = image.convert('RGB')
    except (OSError, ValueError, base64.binascii.Error) as exc:
        raise ValueError('Imagen PNG no válida.') from exc
    # el marco no cuenta como dibujo
    gray = np.array(ImageOps.grayscale(image))
    mask = gray < 170
    mask[55:61, 55:145] = False
    mask[139:146, 55:145] = False
    mask[55:145, 55:61] = False
    mask[55:145, 139:146] = False
    if int(mask.sum()) < 20:
        raise ValueError('El dibujo está vacío.')
    return image


def safe_int(value, maximum):
    try:
        n = int(value)
        if not 0 <= n < maximum:
            raise ValueError()
        return n
    except (ValueError, TypeError):
        raise ValueError('Columna o partido fuera de rango.')


def as_response_err(exc, code=400):
    return jsonify({'ok': False, 'error': str(exc)}), code


@app.get('/')
def main():
    return render_template('recolectar.html', categories=CATEGORIES)


@app.get('/votar')
def vote_page():
    return render_template('index.html', mode='votar', categories=CATEGORIES,
                           contests=CONTESTS, parties=PARTIES, x=BOXES_X, y=BOXES_Y,
                           ballot_w=BALLOT_WIDTH, ballot_h=BALLOT_HEIGHT,
                           confidence_threshold=CONFIDENCE_THRESHOLD)


@app.get('/api/estadisticas-dataset')
def dataset_stats():
    c = counts()
    return jsonify({'categorias': CATEGORIES, 'conteos': c, 'total': sum(c.values()),
                    'objetivo_minimo_por_categoria': 500, 'objetivo_maximo_por_categoria': 1000})


@app.post('/upload')
def upload():
    """guarda un dibujo etiquetado."""
    init_folders()
    payload = (request.get_json(silent=True) or {}) if request.is_json else request.form
    try:
        label = payload.get('numero')
        if label not in CATEGORIES:
            raise ValueError('Selecciona una categoría.')
        image = read_image(payload.get('myImage'))
        col = safe_int(payload.get('columna', 0), len(CONTESTS))
        party = safe_int(payload.get('partido', 0), len(PARTIES))
        author = str(payload.get('dibujante', 'anonimo')).strip()[:60] or 'anonimo'
        author = ''.join(c for c in author if c.isalnum() or c in ' _-') or 'anonimo'
        name = f'{uuid.uuid4().hex}.png'
        path = DATASET / label / name
        with DB_LOCK:
            image.save(path, format='PNG')
            with METADATA.open('a', newline='', encoding='utf-8') as file:
                csv.writer(file).writerow([f'{label}/{name}', label, col, party,
                                          author, datetime.now(timezone.utc).isoformat()])
            c = counts()
        if not request.is_json:
            return redirect(url_for('main'))
        return jsonify({'ok': True, 'mensaje': 'Dibujo guardado', 'conteos': c})
    except ValueError as exc:
        return as_response_err(exc)



@lru_cache(maxsize=1)
def trained_model():
    """carga el modelo cuando se necesita."""
    model_path = MODELS / 'modelo_voto.keras'
    labels_path = MODELS / 'classes.json'
    if not model_path.exists() or not labels_path.exists():
        raise FileNotFoundError('Todavía no hay modelo entrenado.')
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise ImportError('Falta instalar TensorFlow para usar el modelo.') from exc
    model = tf.keras.models.load_model(model_path)
    labels = json.loads(labels_path.read_text(encoding='utf-8'))
    if labels != sorted(CATEGORIES) or int(model.output_shape[-1]) != len(labels):
        raise ValueError('Las clases del modelo no corresponden con la aplicación.')
    return model, labels


def predict_probabilities(image):
    model, labels = trained_model()
    from tensorflow.keras.applications.resnet50 import preprocess_input
    img = image.resize((224, 224), Image.Resampling.BILINEAR)
    x = np.asarray(img, dtype=np.float32)
    x = preprocess_input(np.expand_dims(x, axis=0))
    with ML_LOCK:
        probs = np.asarray(model.predict(x, verbose=0)[0], dtype=np.float64)
    if (probs.shape != (len(labels),) or not np.isfinite(probs).all()
            or (probs < 0).any() or (probs > 1).any()
            or not np.isclose(probs.sum(), 1.0, atol=1e-5, rtol=0)):
        raise ValueError('El modelo devolvió probabilidades inválidas.')
    return sorted([
        {'clase': label, 'nombre': CATEGORIES[label], 'probabilidad': float(prob)}
        for label, prob in zip(labels, probs)
    ], key=lambda item: item['probabilidad'], reverse=True)


def predict_mark(image):
    probabilities = predict_probabilities(image)
    best = probabilities[0]
    return {'clase': best['clase'], 'nombre': best['nombre'],
            'confianza': best['probabilidad'], 'probabilidades': probabilities}


@app.post('/api/predecir')
def predict_drawing():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return as_response_err(ValueError('Envía el dibujo como JSON.'))
    try:
        image = read_image(payload.get('myImage'))
    except ValueError as exc:
        return as_response_err(exc)
    try:
        return jsonify({'ok': True, **predict_mark(image)})
    except (FileNotFoundError, ImportError) as exc:
        return as_response_err(exc, 409)
    except Exception:
        return as_response_err(ValueError('No se pudo usar el modelo. Revisa sus archivos.'), 503)


@app.get('/api/modelo')
def model_status():
    ready = (MODELS / 'modelo_voto.keras').exists() and (MODELS / 'classes.json').exists()
    return jsonify({'entrenado': ready, 'umbral': CONFIDENCE_THRESHOLD,
                    'aviso': 'Simulación educativa.'})


def load_ballots():
    init_folders()
    return json.loads(BALLOTS.read_text(encoding='utf-8'))


def save_ballots(data):
    file = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json',
                                       dir=DATA, delete=False)
    try:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.close()
        os.replace(file.name, BALLOTS)
    finally:
        if os.path.exists(file.name):
            os.unlink(file.name)


@app.post('/api/registrar-voto')
def register_ballot():
    """registra la cédula y las predicciones."""
    init_folders()
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return as_response_err(ValueError('Envía la cédula como JSON.'))
    marks = payload.get('marcas', [])
    if not isinstance(marks, list) or len(marks) > 32:
        return as_response_err(ValueError('Se esperaban hasta 32 recuadros marcados.'))
    try:
        if marks:
            trained_model()
        decoded = []
        already = set()
        for mark in marks:
            if not isinstance(mark, dict):
                raise ValueError('Marca no válida.')
            col = safe_int(mark.get('columna'), len(CONTESTS))
            party = safe_int(mark.get('partido'), len(PARTIES))
            if (col, party) in already:
                raise ValueError('Un recuadro aparece repetido.')
            already.add((col, party))
            image = read_image(mark.get('imagen'))
            decoded.append((col, party, image))
    except (ValueError, FileNotFoundError, ImportError, OSError) as exc:
        return as_response_err(exc, 409 if isinstance(exc, (FileNotFoundError, ImportError)) else 400)
    except Exception as exc:
        return as_response_err(ValueError('No se pudo cargar el modelo.'), 503)

    # cada columna se cuenta por separado
    new_id = uuid.uuid4().hex
    result = []
    by_col = {k: [] for k in range(len(CONTESTS))}
    for col, party, image in decoded:
        by_col[col].append((party, image))
    try:
        for col in range(len(CONTESTS)):
            selected = by_col[col]
            if len(selected) == 0:
                result.append({'estado': 'blanco', 'partido': None, 'clase': None,
                               'confianza': None, 'probabilidades': [], 'revisado': False})
            elif len(selected) > 1:
                result.append({'estado': 'pendiente', 'partido': None, 'clase': 'marcas_multiples',
                               'confianza': None, 'probabilidades': [], 'revisado': False,
                               'predicciones': [dict(partido=party, **predict_mark(image))
                                                for party, image in selected]})
            else:
                party, image = selected[0]
                p = predict_mark(image)
                # resultado provisional de la práctica
                accepted = p['clase'] in ('cruz_valida', 'aspa_valida') and p['confianza'] >= CONFIDENCE_THRESHOLD
                result.append({'estado': 'valido' if accepted else 'pendiente',
                               'partido': party if accepted else None,
                               'partido_marcado': party, 'clase': p['clase'],
                               'confianza': p['confianza'],
                               'probabilidades': p['probabilidades'], 'revisado': False})
    except Exception:
        return as_response_err(ValueError('No se pudo usar el modelo.'), 503)
    stored = {'id': new_id, 'fecha_utc': datetime.now(timezone.utc).isoformat(),
              'columnas': result, 'marcados': [{'columna': c, 'partido': p} for c,p,_ in decoded]}
    with DB_LOCK:
        images_dir = GUARDADOS / new_id
        images_dir.mkdir(exist_ok=False)
        for col, party, img in decoded:
            img.save(images_dir / f'{col}_{party}.png')
        ballots = load_ballots()
        ballots.append(stored)
        save_ballots(ballots)
    return jsonify({'ok': True, 'cedula': stored,
                    'pendientes': sum(r['estado'] == 'pendiente' for r in result)})


@app.get('/api/votos')
def vote_records():
    return jsonify({'cedulas': load_ballots()})


@app.get('/dibujo-voto/<ballot_id>/<int:col>/<int:party>')
def drawing_ballot(ballot_id, col, party):
    if not (len(ballot_id) == 32 and all(k in '0123456789abcdef' for k in ballot_id)):
        return 'No encontrado', 404
    if not (0 <= col < 4 and 0 <= party < 8):
        return 'No encontrado', 404
    path = GUARDADOS / ballot_id / f'{col}_{party}.png'
    return send_file(path) if path.is_file() else ('No encontrado', 404)


@app.post('/api/revisar')
def human_review():
    payload = request.get_json(silent=True) or {}
    try:
        ballot_id = str(payload.get('cedula'))
        col = safe_int(payload.get('columna'), len(CONTESTS))
        choice = payload.get('decision')
        if choice not in ('valido', 'nulo', 'blanco'):
            raise ValueError('Decisión inválida.')
        party = safe_int(payload.get('partido'), len(PARTIES)) if choice == 'valido' else None
        with DB_LOCK:
            ballots = load_ballots()
            item = next((b for b in ballots if b['id'] == ballot_id), None)
            if item is None or item['columnas'][col]['estado'] != 'pendiente':
                raise ValueError('Caso no encontrado o ya revisado.')
            item['columnas'][col].update({'estado': choice, 'partido': party,
                                           'revisado': True})
            save_ballots(ballots)
        return jsonify({'ok': True})
    except ValueError as exc:
        return as_response_err(exc)


@app.get('/revision')
def review_page():
    return render_template('revision.html', contests=CONTESTS, parties=PARTIES, categories=CATEGORIES)


@app.get('/resultados')
def results_page():
    return render_template('resultados.html', contests=CONTESTS, parties=PARTIES)


@app.get('/api/resultados')
def results_data():
    ballots = load_ballots()
    totals = []
    for col in range(len(CONTESTS)):
        count = [0] * len(PARTIES)
        other = {'blanco': 0, 'nulo': 0, 'pendiente': 0}
        for ballot in ballots:
            result = ballot['columnas'][col]
            if result['estado'] == 'valido':
                count[result['partido']] += 1
            else:
                other[result['estado']] += 1
        totals.append({'titulo': CONTESTS[col], 'partidos': count, **other,
                       'votos_validos': sum(count), 'total': len(ballots)})
    return jsonify({'cedulas': len(ballots), 'columnas': totals})


init_folders()

if __name__ == '__main__':
    app.run(debug=True)
