import os


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATA_PATH = os.path.join(
    BASE_DIR,
    "data",
    "dataset.csv"
)

DATA_ENCODING = "utf-8"
DATA_SEP = ","

#territorial
COL_TERRITORIO = "DEPARTAMENTO"
COL_SUBTERRITORIO = "MUNICIPIO"

COL_CATEGORIA = "EVENTO"

COL_FECHA = "FECHA"


NOMBRE_PROYECTO = "Análisis de Emergencias UNGRD 2019-2022"

NOMBRE_DATASET = "Emergencias UNGRD"

ENTIDAD = (
    "Unidad Nacional para la Gestión del Riesgo "
    "de Desastres (UNGRD)"
)

URL_DATASET = (
    "https://www.datos.gov.co/"
    "Ambiente-y-Desarrollo-Sostenible/"
    "Emergencias-UNGRD-/wwkg-r6te"
)