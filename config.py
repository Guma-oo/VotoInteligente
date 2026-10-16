"""datos de la cédula de práctica."""
CATEGORIES = {
    'cruz_valida': 'Cruz (+), intersección dentro',
    'aspa_valida': 'Aspa (X), intersección dentro',
    'interseccion_fuera': 'Intersección fuera del recuadro',
    'marca_diferente': 'Marca diferente (círculo, visto, garabato, etc.)',
}
CONTESTS = [
    'Gobernador y vicegobernador regional',
    'Consejero regional',
    'Provincia de la Galaxia',
    'Distrito de Júpiter',
]
PARTIES = [
    'Amanecer de Nuevo', 'Paz y Amor', 'Gotas de Lluvia',
    'La Magia del Encuentro', 'En la Distancia', 'Al Otro Lado',
    'El Trabajo Dignifica', 'Hojas al Viento',
]
# coordenadas medidas sobre la cédula
BALLOT_WIDTH = 1132
BALLOT_HEIGHT = 626
BOXES_X = [225, 504, 784, 1062]
BOXES_Y = [144, 198, 252, 306, 360, 414, 468, 523]
BOX_SIZE = 54
# recuadro fijo del canvas
DRAW_SIZE = 200
DRAW_BOX = (58, 58, 142, 142)
CONFIDENCE_THRESHOLD = 0.80  # umbral para revisión
