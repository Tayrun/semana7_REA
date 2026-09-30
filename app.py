from flask import Flask, render_template, request
from data_loader import load_data

app = Flask(__name__)

df = load_data()

@app.route("/")
def inicio():
    return render_template("index.html")

@app.route("/poblacional")
def poblacional():
    return render_template("poblacional.html")

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