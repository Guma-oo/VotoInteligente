# VotoInteligente

## Ejecutar en Windows

Desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Abre http://127.0.0.1:5000/ para recolectar y http://127.0.0.1:5000/votar para simular.
La recolección funciona sin TensorFlow. Sin modelo, /api/predecir responde 409.

## Entrenar en Colab

1. Abre notebooks/Entrenamiento_VotosResnet.ipynb en Colab.
2. En Entorno de ejecución > Cambiar tipo de entorno de ejecución, selecciona una GPU.
3. En tu PC, comprime la carpeta dataset/ que contiene tus PNG como dataset.zip. Dentro deben quedar dataset/aspa_valida/, dataset/cruz_valida/, dataset/interseccion_fuera/ y dataset/marca_diferente/. Usa esos nombres, sin números al final.
4. Ejecuta las celdas en orden. Cuando aparezca el selector, sube dataset.zip. También se acepta un ZIP con las cuatro carpetas directamente.
5. Espera las dos fases y revisa curvas, métricas y diagnóstico. La prueba se evalúa después de elegir la época por validación.
6. La última celda de código descarga modelo_voto.keras y classes.json. Si el navegador bloquea una descarga, baja ambos desde /content/resultados_entrenamiento/ en el panel Archivos de Colab.
7. Copia los dos archivos a models/ en tu PC, reemplazando los anteriores y sin cambiar sus nombres ni el orden de las clases.
8. Detén Flask con Ctrl+C, instala las dependencias del modelo y vuelve a iniciar:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe main.py
```

El ZIP del proyecto trae los registros y dibujos de cédulas recibidos, pero no los PNG de entrenamiento ni un modelo entrenado.

## Probar la app

1. En /, guarda un dibujo y comprueba el contador.
2. En /votar, dibuja una marca y espera medio segundo. Deben aparecer cuatro categorías ordenadas, con barras y los valores originales de la red entre 0 y 1, sin redondeo ni normalización adicional.
3. Añade otro trazo, cambia de casilla y usa Borrar y Limpiar cédula. El panel debe corresponder al dibujo actual.
4. Registra una cédula. Las probabilidades quedan en data/cedulas.json por columna; si hay varias marcas, cada una queda en predicciones.
5. Revisa las columnas pendientes en /revision y consulta el conteo en /resultados. Los registros antiguos muestran que no tienen probabilidades guardadas.

## Revisar el entrenamiento

El notebook usa aumento solo en train, dropout, L2, pesos balanceados y dos fases. Guarda el menor val_loss que cumple una brecha absoluta train-validación de hasta 5 puntos. Si ninguna época cumple, usa el mínimo global y lo indica.

El diagnóstico exige además una diferencia prueba-validación de hasta 3 puntos. Para detectar accuracy baja se usa accuracy_minima = 0.80 como referencia ajustable. Train se mide sin aumento ni dropout. Si la prueba se usa para ajustar parámetros, hace falta reservar una nueva prueba final.

El punto dulce se comprueba al entrenar con los PNG; estos cambios no garantizan alcanzarlo. Como todos los dibujos están registrados como anonimo, la separación no se puede hacer por persona.

## Comprobaciones realizadas

- Notebook abierto y validado con nbformat, con sintaxis revisada y sin salidas guardadas.
- Pipeline, relleno blanco, arquitectura, BatchNorm congelada y guardado/carga comprobados con TensorFlow/Keras, sin entrenar.
- Ocho pruebas del servidor con datos temporales y modelo simulado.
- Pruebas de JavaScript para debounce, respuestas viejas, cambio de casilla, borrado, registro y recolección sin modelo.
- No se pudo comprobar el diseño en un navegador en este entorno.
