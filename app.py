from flask import Flask, render_template, request
from data_loader import (
    load_data,
    NOMBRES_MESES,
    NOMBRES_TRIMESTRES
)

app = Flask(__name__)

df = load_data()


def _numero(valor, decimales=0):
    texto = "{:,.{d}f}".format(valor, d=decimales)

    if decimales == 0:
        return texto.replace(",", ".")

    entero, decimal = texto.split(".")

    return entero.replace(",", ".") + "," + decimal


def _porcentaje(valor):
    return "{:.1f}".format(valor).replace(".", ",")


def _direccion(var, plural=False):
    termino_s = "aumentó"
    termino_p = "aumentaron"
    cantidad = _porcentaje(abs(var))

    if var > 0:
        base = termino_p if plural else termino_s
        return base + " " + cantidad + "%"

    if var < 0:
        base = "disminuyó" if not plural else "disminuyeron"
        return base + " " + cantidad + "%"

    return "se mantuvo igual"


def _anos_texto(cantidad):
    if cantidad == 1:
        return "1 año"

    return str(cantidad) + " años"


def _entero_seguro(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None

@app.template_filter("numero")
def filtro_numero(valor, decimales=0):
    return _numero(valor, int(decimales))


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

    #valores de los filtros
    anio = request.args.get("anio", "Todos")
    trimestre = request.args.get("trimestre", "Todos")

    anio_seleccion = _entero_seguro(anio)
    trimestre_seleccion = _entero_seguro(trimestre)

    #copia dataset
    df_filtrado = df.copy()

    #filtro por anio
    if anio_seleccion is not None:
        df_filtrado = df_filtrado[
            df_filtrado["anio"] == anio_seleccion
        ]

    #filtro por trimestre
    if trimestre_seleccion is not None:
        df_filtrado = df_filtrado[
            df_filtrado["trimestre"] == trimestre_seleccion
        ]

    # --- Indicadores del periodo ---
    total_registros = len(df_filtrado)

    total_personas = float(
        df_filtrado["PERSONAS"].sum()
    )

    total_familias = float(
        df_filtrado["FAMILIAS"].sum()
    )

    total_fallecidos = int(
        df_filtrado["FALLECIDOS"].sum()
    )

    total_heridos = int(
        df_filtrado["HERIDOS"].sum()
    )

    total_desaparecidos = int(
        df_filtrado["DESAPARECIDOS"].sum()
    )

    promedio_personas = (
        float(df_filtrado["PERSONAS"].mean())
        if total_registros > 0 else 0
    )

    mediana_personas = (
        float(df_filtrado["PERSONAS"].median())
        if total_registros > 0 else 0
    )

    anios_disponibles = sorted({
        int(a) for a in df["anio"].dropna().unique()
    })

    # --- Comparacion con el periodo equivalente anterior ---
    trimestre_valido = (
        trimestre_seleccion is not None
        and trimestre_seleccion in NOMBRES_TRIMESTRES
    )

    if anio_seleccion is not None:

        anio_actual = anio_seleccion
        anio_previo = anio_actual - 1

        mascara_actual = df["anio"] == anio_actual
        mascara_previa = df["anio"] == anio_previo

        if trimestre_valido:

            trimestre_actual = trimestre_seleccion

            etiqueta_periodo = (
                NOMBRES_TRIMESTRES[trimestre_actual]
                + " de " + str(anio_actual)
            )

            texto_comparacion = (
                "Variación frente al "
                + NOMBRES_TRIMESTRES[trimestre_actual].lower()
                + " de " + str(anio_previo)
            )

            mascara_actual = mascara_actual & (
                df["trimestre"] == trimestre_actual
            )

            mascara_previa = mascara_previa & (
                df["trimestre"] == trimestre_actual
            )

        else:

            etiqueta_periodo = str(anio_actual)

            texto_comparacion = (
                "Variación frente a " + str(anio_previo)
            )

    else:

        anio_actual = anios_disponibles[-1]
        anio_previo = anios_disponibles[-2]

        mascara_actual = df["anio"] == anio_actual
        mascara_previa = df["anio"] == anio_previo

        etiqueta_periodo = (
            str(anios_disponibles[0])
            + "-"
            + str(anios_disponibles[-1])
        )

        if trimestre_valido:

            trimestre_actual = trimestre_seleccion

            nombre_trimestre = NOMBRES_TRIMESTRES[
                trimestre_actual
            ].lower()

            etiqueta_periodo = (
                etiqueta_periodo
                + " · " + nombre_trimestre
            )

            texto_comparacion = (
                "Variación del " + nombre_trimestre
                + " de " + str(anio_actual)
                + " frente al de " + str(anio_previo)
            )

            mascara_actual = mascara_actual & (
                df["trimestre"] == trimestre_actual
            )

            mascara_previa = mascara_previa & (
                df["trimestre"] == trimestre_actual
            )

        else:

            texto_comparacion = (
                "Variación de " + str(anio_actual)
                + " frente a " + str(anio_previo)
            )

    registros_actual = len(df[mascara_actual])
    personas_actual = float(
        df.loc[mascara_actual, "PERSONAS"].sum()
    )

    registros_previo = len(df[mascara_previa])
    personas_previas = float(
        df.loc[mascara_previa, "PERSONAS"].sum()
    )

    var_registros = (
        round(
            (registros_actual - registros_previo)
            / registros_previo * 100,
            1
        )
        if registros_previo > 0 else 0
    )

    var_personas = (
        round(
            (personas_actual - personas_previas)
            / personas_previas * 100,
            1
        )
        if personas_previas > 0 else 0
    )

    # --- Concentracion por mes del calendario ---
    conteo_mes = df_filtrado.groupby("mes").size().to_dict()
    personas_mes = (
        df_filtrado.groupby("mes")["PERSONAS"].sum().to_dict()
    )

    meses_ordenados = sorted(
        conteo_mes,
        key=lambda m: conteo_mes[m],
        reverse=True
    )

    top_meses = meses_ordenados[:3]

    registros_top_meses = sum(
        conteo_mes[m] for m in top_meses
    )

    pct_top_meses = (
        round(registros_top_meses / total_registros * 100, 1)
        if total_registros > 0 else 0
    )

    mes_pico = top_meses[0] if top_meses else None
    mes_valle = (
        min(conteo_mes, key=lambda m: conteo_mes[m])
        if conteo_mes else None
    )

    pct_mes_pico = (
        round(conteo_mes[mes_pico] / total_registros * 100, 1)
        if mes_pico is not None and total_registros > 0
        else 0
    )

    estacionalidad = [
        {
            "mes": m,
            "nombre": NOMBRES_MESES[m],
            "registros": int(conteo_mes.get(m, 0)),
            "personas": float(personas_mes.get(m, 0))
        }
        for m in range(1, 13)
    ]

    # --- Serie mensual (evolucion y aumentos/disminuciones) ---
    conteo_mensual = (
        df_filtrado.groupby(["anio", "mes"]).size().to_dict()
    )

    personas_mensual = (
        df_filtrado.groupby(["anio", "mes"])["PERSONAS"]
        .sum()
        .to_dict()
    )

    puntos_mensuales = []

    for clave in sorted(conteo_mensual.keys()):

        clave_anio = int(clave[0])
        clave_mes = int(clave[1])

        puntos_mensuales.append({
            "anio": clave_anio,
            "mes": clave_mes,
            "etiqueta": (
                str(clave_anio)
                + "-"
                + str(clave_mes).zfill(2)
            ),
            "nombre_mes": NOMBRES_MESES[clave_mes],
            "registros": int(conteo_mensual[clave]),
            "personas": float(personas_mensual[clave])
        })

    for i, punto in enumerate(puntos_mensuales):

        if i == 0:
            punto["var_pct"] = 0.0
            punto["sube"] = True
        else:

            registros_previos = puntos_mensuales[i - 1]["registros"]

            punto["var_pct"] = (
                round(
                    (punto["registros"] - registros_previos)
                    / registros_previos * 100,
                    1
                )
                if registros_previos > 0 else 0.0
            )

            punto["sube"] = (
                punto["registros"] >= registros_previos
            )

    # --- Serie trimestral (comparacion entre periodos) ---
    conteo_trimestral = (
        df_filtrado.groupby(["anio", "trimestre"])
        .size()
        .to_dict()
    )

    personas_trimestral = (
        df_filtrado.groupby(["anio", "trimestre"])["PERSONAS"]
        .sum()
        .to_dict()
    )

    puntos_trimestrales = []

    for clave in sorted(conteo_trimestral.keys()):

        clave_anio = int(clave[0])
        clave_trimestre = int(clave[1])

        puntos_trimestrales.append({
            "anio": clave_anio,
            "trimestre": clave_trimestre,
            "etiqueta": (
                str(clave_anio) + " T" + str(clave_trimestre)
            ),
            "registros": int(conteo_trimestral[clave]),
            "personas": float(personas_trimestral[clave])
        })

    for i, punto in enumerate(puntos_trimestrales):

        if i == 0:
            punto["var_pct"] = 0.0
        else:

            registros_previos = puntos_trimestrales[i - 1]["registros"]

            punto["var_pct"] = (
                round(
                    (punto["registros"] - registros_previos)
                    / registros_previos * 100,
                    1
                )
                if registros_previos > 0 else 0.0
            )

    # --- Serie anual (comparacion entre periodos) ---
    conteo_anual = df_filtrado.groupby("anio").size().to_dict()
    personas_anual = (
        df_filtrado.groupby("anio")["PERSONAS"].sum().to_dict()
    )
    fallecidos_anual = (
        df_filtrado.groupby("anio")["FALLECIDOS"].sum().to_dict()
    )

    anios_filtrados = sorted({
        int(a) for a in df_filtrado["anio"].dropna().unique()
    })

    serie_anual = [
        {
            "anio": a,
            "registros": int(conteo_anual.get(a, 0)),
            "personas": float(personas_anual.get(a, 0)),
            "fallecidos": int(fallecidos_anual.get(a, 0))
        }
        for a in anios_filtrados
    ]

    # --- Variaciones entre anos consecutivos ---
    variaciones_anuales = []

    for i in range(1, len(serie_anual)):

        registros_previo = serie_anual[i - 1]["registros"]
        personas_previa = serie_anual[i - 1]["personas"]

        if registros_previo == 0 or personas_previa == 0:
            continue

        variaciones_anuales.append({
            "anio": serie_anual[i]["anio"],
            "var_registros": round(
                (serie_anual[i]["registros"] - registros_previo)
                / registros_previo * 100,
                1
            ),
            "var_personas": round(
                (serie_anual[i]["personas"] - personas_previa)
                / personas_previa * 100,
                1
            )
        })

    # --- Interpretaciones dinamicas por visualizacion ---
    if puntos_mensuales:

        mes_max = max(
            puntos_mensuales,
            key=lambda p: p["registros"]
        )

        mes_min = min(
            puntos_mensuales,
            key=lambda p: p["registros"]
        )

        primero = puntos_mensuales[0]
        ultimo = puntos_mensuales[-1]

        total_periodos = len(puntos_mensuales)

        meses_en_alza = sum(
            1 for p in puntos_mensuales if p["sube"]
        )

        if total_periodos > 12:

            cierre_evolucion = (
                " la serie se repite año tras año y no "
                "decrece de forma sostenida."
            )

        else:

            cierre_evolucion = (
                " dentro de un solo año la serie ya "
                "muestra alternancia entre periodos altos "
                "y bajos."
            )

        interp_evolucion = (
            "La serie mensual pasa de "
            + _numero(primero["registros"])
            + " registros en " + primero["etiqueta"]
            + " a " + _numero(ultimo["registros"])
            + " en " + ultimo["etiqueta"]
            + ". El máximo se alcanza en "
            + mes_max["nombre_mes"].lower()
            + " de " + str(mes_max["anio"]) + " ("
            + _numero(mes_max["registros"])
            + " registros) y el mínimo en "
            + mes_min["nombre_mes"].lower()
            + " de " + str(mes_min["anio"]) + " ("
            + _numero(mes_min["registros"])
            + "). De " + str(total_periodos)
            + " periodos observados, " + str(meses_en_alza)
            + " superan al periodo anterior:"
            + cierre_evolucion
        )

    else:

        interp_evolucion = (
            "No hay registros para el periodo "
            "seleccionado."
        )

    if len(serie_anual) > 1:

        anio_inicial = serie_anual[0]
        anio_final = serie_anual[-1]

        var_reg_total = round(
            (anio_final["registros"] - anio_inicial["registros"])
            / anio_inicial["registros"] * 100,
            1
        ) if anio_inicial["registros"] > 0 else 0

        var_per_total = round(
            (anio_final["personas"] - anio_inicial["personas"])
            / anio_inicial["personas"] * 100,
            1
        ) if anio_inicial["personas"] > 0 else 0

        if variaciones_anuales:

            mayor_salto = max(
                variaciones_anuales,
                key=lambda v: v["var_registros"]
            )

            mayor_caida = min(
                variaciones_anuales,
                key=lambda v: v["var_registros"]
            )

            detalle_saltos = (
                " El cambio más fuerte en registros ocurre "
                "en " + str(mayor_salto["anio"]) + ", donde el "
                "número de emergencias " + _direccion(
                    mayor_salto["var_registros"]
                ) + ", y la mayor caída en "
                + str(mayor_caida["anio"]) + ", donde "
                + _direccion(mayor_caida["var_registros"]) + "."
            )

        else:

            detalle_saltos = ""

        if var_reg_total > 0 and var_per_total > 0:

            cierre = (
                "Ambos indicadores crecen, así que el "
                "aumento del esfuerzo de registro va "
                "acompañado de mayor impacto poblacional."
            )

        elif var_reg_total > 0 > var_per_total:

            cierre = (
                "Los registros crecen pero las personas "
                "afectadas bajan: hay más emergencias "
                "reportadas y de menor magnitud."
            )

        elif var_reg_total < 0 < var_per_total:

            cierre = (
                "Los registros bajan mientras las personas "
                "afectadas suben: menos emergencias, pero "
                "de mayor impacto poblacional."
            )

        else:

            cierre = (
                "Ninguno de los dos indicadores crece de "
                "forma sostenida en el periodo."
            )

        interp_anual = (
            "Entre " + str(anio_inicial["anio"])
            + " y " + str(anio_final["anio"])
            + " los registros " + _direccion(
                var_reg_total, plural=True
            )
            + " (" + _numero(anio_inicial["registros"])
            + " a " + _numero(anio_final["registros"])
            + ") y las personas afectadas "
            + _direccion(var_per_total, plural=True) + " ("
            + _numero(anio_inicial["personas"]) + " a "
            + _numero(anio_final["personas"])
            + ")." + detalle_saltos + " " + cierre
        )

    else:

        interp_anual = (
            "Selecciona dos o más años para comparar la "
            "evolución entre periodos."
        )

    meses_presentes = len(meses_ordenados)

    if conteo_mes:

        nombres_pico = ", ".join(
            NOMBRES_MESES[int(m)].lower() for m in top_meses
        )

        if meses_presentes >= 6:

            cierre_estacionalidad = (
                " El comportamiento se repite cada año: "
                "los picos se concentran en los meses de "
                "lluvias y el valle en la temporada seca, "
                "por lo que la emergencia es estacional y "
                "no uniforme."
            )

        else:

            cierre_estacionalidad = (
                " El filtro deja solo " + str(meses_presentes)
                + " meses en pantalla, así que la gráfica "
                "no permite evaluar el ciclo anual "
                "completo: quita el filtro de trimestre "
                "para comparar los doce meses."
            )

        interp_estacionalidad = (
            "Al agrupar los registros por mes del "
            "calendario, los " + str(len(top_meses))
            + " meses con más emergencias ("
            + nombres_pico + ") concentran "
            + _porcentaje(pct_top_meses) + "% del total, "
            "mientras el mes con menos registros es "
            + NOMBRES_MESES[int(mes_valle)].lower() + " ("
            + _numero(conteo_mes[mes_valle]) + ")."
            + cierre_estacionalidad
        )

    else:

        interp_estacionalidad = (
            "No hay registros para el periodo "
            "seleccionado."
        )

    # --- Conocimientos evidentes ---
    if variaciones_anuales and len(serie_anual) > 1:

        mayor_crecimiento = max(
            variaciones_anuales,
            key=lambda v: v["var_registros"]
        )

        mayor_descenso = min(
            variaciones_anuales,
            key=lambda v: v["var_registros"]
        )

        conocimiento_1 = {
            "titulo": (
                "1. El número de emergencias cambia "
                "entre años, sin una tendencia única"
            ),
            "pregunta": (
                "¿El número de emergencias registradas "
                "aumenta o disminuye de forma sostenida a "
                "lo largo de los años disponibles?"
            ),
            "variables": (
                "FECHA (año) y el conteo de registros "
                "por año."
            ),
            "procedimiento": (
                "Se agruparon los "
                + _numero(total_registros)
                + " registros por año a partir de FECHA y "
                "se calculó la variación porcentual de "
                "cada año frente al inmediatamente "
                "anterior."
            ),
            "evidencia": (
                "Gráfica 2 (comparación entre años) y la "
                "tabla de evolución trimestral. En "
                + str(mayor_crecimiento["anio"]) + " el "
                "número de registros " + _direccion(
                    mayor_crecimiento["var_registros"]
                ) + " y en " + str(mayor_descenso["anio"])
                + " " + _direccion(
                    mayor_descenso["var_registros"]
                ) + "."
            ),
            "hallazgo": (
                "El volumen de emergencias registradas no "
                "crece de manera constante: se alternan "
                "años de aumento y de reducción. El mayor "
                "aumento ocurre en "
                + str(mayor_crecimiento["anio"]) + " ("
                + _direccion(mayor_crecimiento["var_registros"])
                + ") y la mayor caída en "
                + str(mayor_descenso["anio"]) + " ("
                + _direccion(mayor_descenso["var_registros"])
                + ")."
            ),
            "interpretacion": (
                "El comportamiento irregular sugiere que "
                "las emergencias dependen de factores "
                "que varían año a año (intensidad de la "
                "temporada lluviosa, exposición de los "
                "territorios y capacidad de reporte) y no "
                "de una tendencia demográfica simple."
            ),
            "utilidad": (
                "Permite dimensionar recursos de respuesta "
                "sin asumir que el próximo año repetirá el "
                "comportamiento del actual."
            ),
            "limitacion": (
                "El conteo de registros mide eventos "
                "reportados, no la magnitud de la "
                "emergencia; además el dataset cubre "
                "solo cuatro años, insuficientes para "
                "confirmar un ciclo."
            )
        }

    else:

        conocimiento_1 = {
            "titulo": "1. Evolución entre años",
            "pregunta": "Sin datos suficientes.",
            "variables": "Sin datos.",
            "procedimiento": "Sin datos.",
            "evidencia": "Sin datos.",
            "hallazgo": (
                "Selecciona al menos dos años para "
                "obtener este conocimiento."
            ),
            "interpretacion": "Sin datos.",
            "utilidad": "Sin datos.",
            "limitacion": "Sin datos."
        }

    if conteo_mes and len(anios_filtrados) > 1:

        nombres_top = ", ".join(
            NOMBRES_MESES[int(m)].lower() for m in top_meses
        )

        if meses_presentes >= 6:

            alcance_2 = (
                "Se agruparon los registros de "
                + _anos_texto(len(anios_filtrados))
                + " por mes calendario (12 grupos) y se "
                "midió el peso de los "
                + str(len(top_meses))
                + " meses con más registros sobre el total."
            )

            evidencia_2 = (
                "Gráfica 3 (estacionalidad): los meses "
                + nombres_top + " concentran "
                + _porcentaje(pct_top_meses)
                + "% de los registros y "
                + NOMBRES_MESES[int(mes_valle)].lower()
                + " aporta solo "
                + _numero(conteo_mes[mes_valle]) + "."
            )

            limitacion_2 = (
                "Con solo cuatro años y "
                + _anos_texto(len(anios_filtrados))
                + " en el filtro no puede distinguirse "
                "entre estacionalidad real y casualidad."
            )

        else:

            alcance_2 = (
                "El filtro de trimestre deja solo "
                + str(meses_presentes)
                + " meses visibles, por lo que el "
                "agrupamiento se hizo sobre un "
                "subconjunto del calendario."
            )

            evidencia_2 = (
                "Gráfica 3 (estacionalidad) con los "
                + str(meses_presentes) + " meses del "
                "filtro: el más cargado es "
                + nombres_top.split(", ")[0] + " con "
                + _numero(conteo_mes[top_meses[0]])
                + " registros."
            )

            limitacion_2 = (
                "Alfiltrar por trimestre quedan fuera "
                + str(12 - meses_presentes)
                + " meses del ciclo anual, así que no "
                "puede afirmarse un patrón estacional "
                "completo con este filtro."
            )

        conocimiento_2 = {
            "titulo": (
                "2. Las emergencias se concentran en los "
                "mismos meses cada año"
            ),
            "pregunta": (
                "¿Se repiten los picos de emergencias en "
                "los mismos meses del año o están "
                "repartidos de forma uniforme?"
            ),
            "variables": (
                "FECHA (mes del calendario), conteo de "
                "registros y PERSONAS."
            ),
            "procedimiento": alcance_2,
            "evidencia": evidencia_2,
            "hallazgo": (
                "Existe un patrón estacional: la "
                "distribución de emergencias se repite "
                "cada año y se concentra en " + nombres_top
                + ", con un valle marcado en "
                + NOMBRES_MESES[int(mes_valle)].lower() + "."
            ),
            "interpretacion": (
                "El calendario de emergencias responde al "
                "ciclo climatico: los meses de mayores "
                "precipitaciones generan inundaciones, "
                "avenidas torrenciales y movimientos en "
                "masa, mientras los meses de menor lluvia "
                "registran menos eventos."
            ),
            "utilidad": (
                "Permite adelantar el despliegue de "
                "equipos, anticipar brigadas y reservar "
                "insumos en los meses "
                "de mayor probabilidad."
            ),
            "limitacion": limitacion_2
        }

    else:

        conocimiento_2 = {
            "titulo": "2. Estacionalidad mensual",
            "pregunta": "Sin datos suficientes.",
            "variables": "Sin datos.",
            "procedimiento": "Sin datos.",
            "evidencia": "Sin datos.",
            "hallazgo": (
                "Mantén el filtro de año en Todos para "
                "comparar varios años y obtener este "
                "conocimiento."
            ),
            "interpretacion": "Sin datos.",
            "utilidad": "Sin datos.",
            "limitacion": "Sin datos."
        }

    divergencias = [
        v for v in variaciones_anuales
        if v["var_registros"] * v["var_personas"] < 0
    ]

    if divergencias:

        anio_divergente = max(
            divergencias,
            key=lambda v: abs(v["var_personas"])
        )

        conocimiento_3 = {
            "titulo": (
                "3. Más registros no significa más "
                "personas afectadas"
            ),
            "pregunta": (
                "¿Los periodos con más registros "
                "registrados son también los que afectan a "
                "más personas?"
            ),
            "variables": (
                "FECHA (año), conteo de registros, "
                "PERSONAS y FAMILIAS."
            ),
            "procedimiento": (
                "Se compararon, año a año, el número de "
                "registros con la suma de PERSONAS, y se "
                "buscaron los años en que ambas variables "
                "se movieron en direcciones opuestas."
            ),
            "evidencia": (
                "Gráfica 2, donde las barras de registros y "
                "la línea de personas no siguen la misma "
                "tendencia, e indicador 3 del tablero: el "
                "promedio de personas por evento es de "
                + _numero(promedio_personas, 1) + " con "
                "mediana " + _numero(mediana_personas) + "."
            ),
            "hallazgo": (
                "En " + str(anio_divergente["anio"])
                + " los registros " + _direccion(
                    anio_divergente["var_registros"],
                    plural=True
                ) + " mientras las personas afectadas "
                + _direccion(
                    anio_divergente["var_personas"],
                    plural=True
                )
                + ": hay una disociación entre la "
                "frecuencia de los eventos y su impacto "
                "sobre la población."
            ),
            "interpretacion": (
                "La cantidad de reportes mide la "
                "ocurrencia del evento, no su gravedad. Un "
                "año puede tener muchas emergencias "
                "pequeñas y otro pocas emergencias "
                "masivas, por lo que priorizar solo por "
                "número de registros deja "
                "fuera a la población realmente "
                "afectada."
            ),
            "utilidad": (
                "Orienta la planificación usando el tamaño "
                "del evento (PERSONAS, FAMILIAS) y no "
                "solo el conteo de reportes."
            ),
            "limitacion": (
                "El "
                + _porcentaje(
                    round(
                        (df_filtrado["PERSONAS"] <= 0).sum()
                        / total_registros * 100,
                        1
                    ) if total_registros > 0 else 0
                )
                + "% de los registros del filtro no "
                "reporta personas afectadas, lo que "
                "debilita la comparación de impacto."
            )
        }

    elif total_registros == 0:

        conocimiento_3 = {
            "titulo": (
                "3. Más registros no significa más "
                "personas afectadas"
            ),
            "pregunta": (
                "¿Los periodos con más registros "
                "registrados son también los que afectan a "
                "más personas?"
            ),
            "variables": (
                "FECHA (año), conteo de registros, "
                "PERSONAS y FAMILIAS."
            ),
            "procedimiento": "Sin registros en el filtro.",
            "evidencia": "Sin datos.",
            "hallazgo": (
                "No hay registros en el periodo "
                "seleccionado, así que no existe evidencia "
                "para sostener este conocimiento."
            ),
            "interpretacion": "Sin datos.",
            "utilidad": "Sin datos.",
            "limitacion": (
                "Amplía el rango de años para obtener "
                "comparaciones entre periodos."
            )
        }

    else:

        conocimiento_3 = {
            "titulo": (
                "3. Más registros no significa más "
                "personas afectadas"
            ),
            "pregunta": (
                "¿Los periodos con más registros "
                "registrados son también los que afectan a "
                "más personas?"
            ),
            "variables": (
                "FECHA (año), conteo de registros, "
                "PERSONAS y FAMILIAS."
            ),
            "procedimiento": (
                "Se compararon, año a año, el número de "
                "registros con la suma de PERSONAS."
            ),
            "evidencia": (
                "Gráfica 2 e indicador 3 del tablero."
            ),
            "hallazgo": (
                "En los periodos comparados los registros "
                "y las personas afectadas se mueven en la "
                "misma dirección, así que en este filtro no "
                "se observa disociación entre frecuencia e "
                "impacto."
            ),
            "interpretacion": (
                "El conteo de reportes y el impacto "
                "poblacional avanzan juntos, lo que "
                "simplifica la lectura pero no garantiza "
                "que ocurra en otros periodos."
            ),
            "utilidad": (
                "Permite usar el conteo de registros como "
                "proxy del impacto en este filtro."
            ),
            "limitacion": (
                "El resultado depende del filtro aplicado y "
                "no puede generalizarse sin comparar los "
                "cuatro años completos."
            )
        }

    # ---opciones de los filtros---
    eventos = sorted(
        df["EVENTO"].dropna().unique()
    )

    return render_template(
        "temporal.html",

        total_registros=total_registros,
        total_personas=total_personas,
        total_familias=total_familias,
        total_fallecidos=total_fallecidos,
        total_heridos=total_heridos,
        total_desaparecidos=total_desaparecidos,

        promedio_personas=promedio_personas,
        mediana_personas=mediana_personas,

        etiqueta_periodo=etiqueta_periodo,
        texto_comparacion=texto_comparacion,

        registros_actual=registros_actual,
        registros_previo=registros_previo,
        personas_actual=personas_actual,
        personas_previas=personas_previas,
        var_registros=var_registros,
        var_personas=var_personas,

        pct_top_meses=pct_top_meses,
        pct_mes_pico=pct_mes_pico,
        mes_pico=NOMBRES_MESES[int(mes_pico)] if mes_pico else "Sin datos",
        mes_valle=NOMBRES_MESES[int(mes_valle)] if mes_valle else "Sin datos",
        registros_mes_pico=int(conteo_mes[mes_pico]) if mes_pico else 0,
        registros_mes_valle=int(conteo_mes[mes_valle]) if mes_valle else 0,

        anios_disponibles=anios_disponibles,
        total_dataset=len(df),
        anio_seleccionado=anio,
        trimestre_seleccionado=trimestre,

        puntos_mensuales=puntos_mensuales,
        puntos_trimestrales=puntos_trimestrales,
        serie_anual=serie_anual,
        estacionalidad=estacionalidad,

        interp_evolucion=interp_evolucion,
        interp_anual=interp_anual,
        interp_estacionalidad=interp_estacionalidad,

        conocimiento_1=conocimiento_1,
        conocimiento_2=conocimiento_2,
        conocimiento_3=conocimiento_3,

        eventos=eventos
    )

if __name__ == "__main__":
    app.run(debug=True)