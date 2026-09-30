from functools import lru_cache
import pandas as pd
import config


MESES = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12
}


COLUMNAS_NUMERICAS = [
    "PERSONAS",
    "FAMILIAS",
    "FALLECIDOS",
    "HERIDOS",
    "DESAPARECIDOS",
    "VIVIENDAS DESTRUIDAS",
    "VIVIENDAS AVERIADAS",
    "HECTAREAS"
]


@lru_cache(maxsize=1)
def _cargar():

    df = pd.read_csv(
        config.DATA_PATH,
        encoding=config.DATA_ENCODING,
        sep=config.DATA_SEP,
        low_memory=False
    )

    df.columns = (
        df.columns
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    columnas_texto = [
        "DEPARTAMENTO",
        "MUNICIPIO",
        "EVENTO"
    ]

    for col in columnas_texto:

        if col in df.columns:

            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.upper()
            )

    for col in COLUMNAS_NUMERICAS:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.strip(),
                errors="coerce"
            )

    partes = df["FECHA"].astype(str).str.extract(
        r"^(\d{4})\s+([A-Za-z]{3})"
    )

    df["anio"] = pd.to_numeric(
        partes[0],
        errors="coerce"
    )

    df["mes"] = partes[1].map(MESES)

    df = df.drop_duplicates()

    df = df[df["DEPARTAMENTO"] != "PERÚ"]

    return df


def load_data():
    return _cargar().copy()