from flask import Flask, render_template
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

    total_eventos = len(df)

    total_personas = df["PERSONAS"].sum()

    total_familias = df["FAMILIAS"].sum()

    total_departamentos = df["DEPARTAMENTO"].nunique()

    personas_departamento = (
        df.groupby("DEPARTAMENTO")["PERSONAS"]
        .sum()
        .sort_values(ascending=False)
    )

    departamento_mayor = personas_departamento.index[0]

    personas_mayor = personas_departamento.iloc[0]

    return render_template(
        "territorial.html",
        total_eventos=total_eventos,
        total_personas=total_personas,
        total_familias=total_familias,
        total_departamentos=total_departamentos,
        departamento_mayor=departamento_mayor,
        personas_mayor=personas_mayor
    )

@app.route("/temporal")
def temporal():
    return render_template("temporal.html")

if __name__ == "__main__":
    app.run(debug=True)