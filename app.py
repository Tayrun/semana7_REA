from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/poblacional')
def poblacional():
    # Aquí cargarás luego los datos y cálculos de tu dimensión
    return render_template('poblacional.html')

@app.route('/territorial')
def territorial():
    return render_template('territorial.html')

@app.route('/temporal')
def temporal():
    return render_template('temporal.html')

@app.route('/multivariada')
def multivariada():
    return render_template('multivariada.html')

if __name__ == '__main__':
    app.run(debug=True)