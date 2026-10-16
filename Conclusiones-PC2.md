# Conclusiones

1. En este proyecto aplicamos una red neuronal **ResNet** en una página web que simula una votación. El usuario dibuja una marca y el sistema la analiza para identificar si es una **cruz válida**, un **aspa válida**, una **intersección fuera del recuadro** o una **marca diferente**. En las pruebas realizadas, el modelo obtuvo una exactitud del **95,49 %**, al clasificar correctamente **360 de 377 imágenes**.

2. Aprendimos que no basta con que la red neuronal reconozca una marca para contar un voto. El sistema comprueba que exista **una sola marca**, que sea una **cruz o un aspa válida** y que la confianza de la predicción sea de **80 % o más**. Así se evita aceptar automáticamente marcas que no cumplen las reglas, incluso cuando el modelo está muy seguro de su predicción.

3. También incorporamos una sección de **revisión** para los casos que el sistema no puede aceptar automáticamente. Por ejemplo, cuando la confianza es menor al 80 %, la marca es diferente o no cumple alguna de las condiciones establecidas, el voto queda pendiente para que una persona lo revise. De esta manera, el sistema combina la ayuda de la inteligencia artificial con una verificación humana antes de tomar una decisión final.

## Cuadro de métricas de la red neuronal

| Métrica | Resultado | ¿Qué indica? |
|---|---:|---|
| Exactitud (Accuracy) | **95,49 %** | Porcentaje de imágenes clasificadas correctamente. |
| Precisión macro (Precision) | **95,82 %** | Promedio de la precisión de las cuatro categorías. |
| Sensibilidad macro (Recall) | **95,49 %** | Promedio de las marcas reales identificadas en cada categoría. |
| F1-score macro | **95,60 %** | Equilibrio entre precisión y recall de las cuatro categorías. |
| Pérdida en prueba (Loss) | **0,1699** | Valor de error de la función de pérdida en el conjunto de prueba; menor suele ser mejor para el mismo problema. |
| Clasificaciones correctas | **360 de 377** | Cantidad de aciertos en el conjunto de prueba. |
