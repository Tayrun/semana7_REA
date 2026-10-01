from flask import Flask, render_template, request
from data_loader import load_data

app = Flask(__name__)

df = load_data()

@app.route("/")
def inicio():
    return render_template("index.html")

@app.route("/poblacional")
def poblacional():
    # valor del filtro
    evento = request.args.get("evento", "Todos")

    # copia dataset
    df_filtrado = df.copy()

    # filtro por tipo de emergencia
    if evento != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["EVENTO"] == evento
        ]

    # Indicadores poblacionales
    total_eventos = len(df_filtrado)

    total_personas = float(df_filtrado["PERSONAS"].sum())
    total_familias = float(df_filtrado["FAMILIAS"].sum())
    total_fallecidos = int(df_filtrado["FALLECIDOS"].sum())
    total_heridos = int(df_filtrado["HERIDOS"].sum())
    total_desaparecidos = int(df_filtrado["DESAPARECIDOS"].sum())

    total_viv_destruidas = int(
        df_filtrado["VIVIENDAS DESTRUIDAS"].sum()
    )
    total_viv_averiadas = int(
        df_filtrado["VIVIENDAS AVERIADAS"].sum()
    )
    total_viviendas = total_viv_destruidas + total_viv_averiadas

    # --- Composición poblacional (diferencia con territorial) ---
    personas_por_familia = (
        round(total_personas / total_familias, 2)
        if total_familias > 0 else 0
    )
    total_victimas = (
        total_fallecidos + total_heridos + total_desaparecidos
    )
    tasa_fallecidos_10k = (
        round(total_fallecidos / total_personas * 10000, 2)
        if total_personas > 0 else 0
    )
    pct_averiadas = (
        round(total_viv_averiadas / total_viviendas * 100, 1)
        if total_viviendas > 0 else 0
    )

    # Severidad: promedio de personas por evento (no volumen total)
    severidad_evento = (
        df_filtrado.groupby("EVENTO")["PERSONAS"]
        .mean()
        .sort_values(ascending=False)
        .head(10)
    )

    # Composición hogar: personas y familias por evento (top 10)
    composicion_hogar = (
        df_filtrado.groupby("EVENTO")
        .agg(
            personas=("PERSONAS", "sum"),
            familias=("FAMILIAS", "sum"),
        )
        .sort_values("personas", ascending=False)
        .head(10)
        .reset_index()
    )

    promedio_personas = (
        float(df_filtrado["PERSONAS"].mean())
        if total_eventos > 0 else 0
    )
    mediana_personas = (
        float(df_filtrado["PERSONAS"].median())
        if total_eventos > 0 else 0
    )

    eventos_sin_personas = int((df_filtrado["PERSONAS"] <= 0).sum())
    pct_sin_personas = (
        round(eventos_sin_personas / total_eventos * 100, 1)
        if total_eventos > 0 else 0
    )

    # Personas afectadas por tipo de evento
    personas_evento = (
        df_filtrado.groupby("EVENTO")["PERSONAS"]
        .sum()
        .sort_values(ascending=False)
    )

    # Familias afectadas por tipo de evento
    familias_evento = (
        df_filtrado.groupby("EVENTO")["FAMILIAS"]
        .sum()
        .sort_values(ascending=False)
    )

    # Víctimas (fallecidos, heridos, desaparecidos) por evento
    victimas_evento = (
        df_filtrado.groupby("EVENTO")
        .agg(
            fallecidos=("FALLECIDOS", "sum"),
            heridos=("HERIDOS", "sum"),
            desaparecidos=("DESAPARECIDOS", "sum"),
            personas=("PERSONAS", "sum"),
        )
        .sort_values("fallecidos", ascending=False)
        .reset_index()
    )

    # Viviendas afectadas por evento
    viviendas_evento = (
        df_filtrado.groupby("EVENTO")
        .agg(
            destruidas=("VIVIENDAS DESTRUIDAS", "sum"),
            averiadas=("VIVIENDAS AVERIADAS", "sum"),
        )
        .reset_index()
    )
    viviendas_evento["total"] = (
        viviendas_evento["destruidas"]
        + viviendas_evento["averiadas"]
    )
    viviendas_evento = viviendas_evento.sort_values(
        "total", ascending=False
    )

    # Distribución de eventos según magnitud (rango de personas)
    import pandas as pd

    rangos = pd.cut(
        df_filtrado["PERSONAS"],
        bins=[-1, 0, 5, 50, 500, float("inf")],
        labels=[
            "0 (sin registro)",
            "1-5",
            "6-50",
            "51-500",
            "Más de 500",
        ],
    )
    distribucion_rangos = (
        rangos.value_counts().reindex(
            ["0 (sin registro)", "1-5", "6-50", "51-500", "Más de 500"]
        ).fillna(0).astype(int)
    )

    # Evento con mayor cantidad de personas afectadas
    if not personas_evento.empty:
        evento_mayor = personas_evento.index[0]
        personas_mayor = float(personas_evento.iloc[0])
        pct_evento_mayor = (
            round(personas_mayor / total_personas * 100, 1)
            if total_personas > 0 else 0
        )
    else:
        evento_mayor = "Sin datos"
        personas_mayor = 0
        pct_evento_mayor = 0

    # --- Categorías principales y % de participación ---
    total_categorias = int(df_filtrado["EVENTO"].nunique())

    tabla_categorias = (
        df_filtrado.groupby("EVENTO")
        .agg(
            registros=("EVENTO", "size"),
            personas=("PERSONAS", "sum"),
            familias=("FAMILIAS", "sum"),
            fallecidos=("FALLECIDOS", "sum"),
        )
        .reset_index()
    )
    if total_eventos > 0:
        tabla_categorias["pct_registros"] = (
            tabla_categorias["registros"] / total_eventos * 100
        ).round(1)
    else:
        tabla_categorias["pct_registros"] = 0.0
    if total_personas > 0:
        tabla_categorias["pct_personas"] = (
            tabla_categorias["personas"] / total_personas * 100
        ).round(1)
    else:
        tabla_categorias["pct_personas"] = 0.0
    tabla_categorias = tabla_categorias.sort_values(
        "registros", ascending=False
    ).head(12)
    tabla_categorias_dict = tabla_categorias.to_dict("records")

    # --- Grupos predominantes y minoritarios ---
    conteo = df_filtrado["EVENTO"].value_counts()
    personas_cat = df_filtrado.groupby("EVENTO")["PERSONAS"].sum()

    def _grupo(nombre, n, pct):
        return {"nombre": nombre, "n": n, "pct": pct}

    if not conteo.empty:
        pred_conteo_nombre = conteo.index[0]
        pred_conteo_n = int(conteo.iloc[0])
        pred_conteo_pct = round(pred_conteo_n / total_eventos * 100, 1)
        min_conteo_nombre = conteo.index[-1]
        min_conteo_n = int(conteo.iloc[-1])
        min_conteo_pct = round(min_conteo_n / total_eventos * 100, 2)
    else:
        pred_conteo_nombre = min_conteo_nombre = "Sin datos"
        pred_conteo_n = min_conteo_n = 0
        pred_conteo_pct = min_conteo_pct = 0

    if not personas_cat.empty and total_personas > 0:
        pred_pers_nombre = personas_cat.idxmax()
        pred_pers_n = float(personas_cat.max())
        pred_pers_pct = round(pred_pers_n / total_personas * 100, 1)
        min_pers_nombre = personas_cat.idxmin()
        min_pers_n = float(personas_cat.min())
        min_pers_pct = round(min_pers_n / total_personas * 100, 2)
    else:
        pred_pers_nombre = min_pers_nombre = "Sin datos"
        pred_pers_n = min_pers_n = 0
        pred_pers_pct = min_pers_pct = 0

    grupo_pred_conteo = _grupo(
        pred_conteo_nombre, pred_conteo_n, pred_conteo_pct
    )
    grupo_min_conteo = _grupo(
        min_conteo_nombre, min_conteo_n, min_conteo_pct
    )
    grupo_pred_personas = _grupo(
        pred_pers_nombre, pred_pers_n, pred_pers_pct
    )
    grupo_min_personas = _grupo(
        min_pers_nombre, min_pers_n, min_pers_pct
    )

    # opciones para el filtro
    eventos = sorted(
        df["EVENTO"].dropna().unique()
    )

    return render_template(
        "poblacional.html",

        total_eventos=total_eventos,
        total_personas=total_personas,
        total_familias=total_familias,
        total_fallecidos=total_fallecidos,
        total_heridos=total_heridos,
        total_desaparecidos=total_desaparecidos,
        total_viv_destruidas=total_viv_destruidas,
        total_viv_averiadas=total_viv_averiadas,
        total_viviendas=total_viviendas,

        personas_por_familia=personas_por_familia,
        total_victimas=total_victimas,
        tasa_fallecidos_10k=tasa_fallecidos_10k,
        pct_averiadas=pct_averiadas,

        promedio_personas=promedio_personas,
        mediana_personas=mediana_personas,
        eventos_sin_personas=eventos_sin_personas,
        pct_sin_personas=pct_sin_personas,

        evento_mayor=evento_mayor,
        personas_mayor=personas_mayor,
        pct_evento_mayor=pct_evento_mayor,

        eventos=eventos,
        evento_seleccionado=evento,

        total_categorias=total_categorias,
        tabla_categorias=tabla_categorias_dict,
        grupo_pred_conteo=grupo_pred_conteo,
        grupo_min_conteo=grupo_min_conteo,
        grupo_pred_personas=grupo_pred_personas,
        grupo_min_personas=grupo_min_personas,

        personas_evento=personas_evento.to_dict(),
        familias_evento=familias_evento.to_dict(),
        victimas_evento=victimas_evento.to_dict("records"),
        viviendas_evento=viviendas_evento.to_dict("records"),
        distribucion_rangos=distribucion_rangos.to_dict(),
        severidad_evento=severidad_evento.to_dict(),
        composicion_hogar=composicion_hogar.to_dict("records"),
    )

@app.route("/territorial")
def territorial():

    #valores de los filtros
    departamento = request.args.get("departamento", "Todos")
    evento = request.args.get("evento", "Todos")

    #copia dataset
    df_filtrado = df.copy()

    #filtro por depart
    if departamento != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["DEPARTAMENTO"] == departamento
        ]

    #filtro por tipo emerg
    if evento != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado["EVENTO"] == evento
        ]

    #Indicadores
    total_eventos = len(df_filtrado)

    total_personas = df_filtrado["PERSONAS"].sum()

    total_familias = df_filtrado["FAMILIAS"].sum()

    total_departamentos = df_filtrado["DEPARTAMENTO"].nunique()

    #Perosnas afectadas por dept
    personas_departamento = (
        df_filtrado.groupby("DEPARTAMENTO")["PERSONAS"]
        .sum()
        .sort_values(ascending=False)
    )

    #eventos registrados por depat
    eventos_departamento = (
        df_filtrado.groupby("DEPARTAMENTO")
        .size()
        .sort_values(ascending=False)
    )

    #relacion entre eventos  y personas afectadas por dept
    relacion_departamento = (
        df_filtrado.groupby("DEPARTAMENTO")
        .agg(
            eventos=("DEPARTAMENTO", "size"),
            personas=("PERSONAS", "sum")
        )
        .reset_index()
    )

    #departamento con mayor cantidad de personas afectadas
    if not personas_departamento.empty:
        departamento_mayor = personas_departamento.index[0]
        personas_mayor = personas_departamento.iloc[0]
    else:
        departamento_mayor = "Sin datos"
        personas_mayor = 0

    #oppciones para los filtros
    departamentos = sorted(
        df["DEPARTAMENTO"].dropna().unique()
    )

    eventos = sorted(
        df["EVENTO"].dropna().unique()
    )

    return render_template(
        "territorial.html",

        total_eventos=total_eventos,
        total_personas=total_personas,
        total_familias=total_familias,
        total_departamentos=total_departamentos,

        departamento_mayor=departamento_mayor,
        personas_mayor=personas_mayor,

        departamentos=departamentos,
        eventos=eventos,

        departamento_seleccionado=departamento,
        evento_seleccionado=evento,

        personas_departamento=personas_departamento.to_dict(),
        eventos_departamento=eventos_departamento.to_dict(),
        relacion_departamento=relacion_departamento.to_dict("records")
    )

@app.route("/temporal")
def temporal():
    return render_template("temporal.html")

if __name__ == "__main__":
    app.run(debug=True)