from flask import Flask
import fdb
from flask_cors import CORS


# ==========================================================
# APLICAÇÃO
# ==========================================================

app = Flask(__name__)

app.config.from_pyfile('config.py')


# ==========================================================
# CORS
# ==========================================================

CORS(
    app,

    supports_credentials=True,

    resources={
        r"/*": {
            "origins": [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://10.92.3.142:5173",
                "http://10.92.3.45:5173",
                "http://192.168.0.9:5173"
            ],

            "methods": [
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "OPTIONS"
            ],

            "allow_headers": [
                "Content-Type",
                "Authorization"
            ],

            "supports_credentials": True
        }
    }
)


# ==========================================================
# FIREBIRD
# ==========================================================

FBCLIENT = (
    r"C:\Program Files (x86)\Firebird\Firebird_5_0\fbclient.dll"
)


# ==========================================================
# CONEXÃO COM FIREBIRD
# ==========================================================

def conectar_banco():

    return fdb.connect(

        host=app.config['DB_HOST'],

        database=app.config['DB_NAME'],

        user=app.config['DB_USER'],

        password=app.config['DB_PASSWORD'],

        charset='UTF8',

        fb_library_name=FBCLIENT
    )


# ==========================================================
# TESTAR BANCO
# ==========================================================

try:

    con = conectar_banco()

    print("==========================================")
    print(" FIREBIRD CONECTADO COM SUCESSO!")
    print("==========================================")

    con.close()

except Exception as erro:

    print("ERRO FIREBIRD:")
    print(erro)


# ==========================================================
# IMPORTAR ROTAS
# ==========================================================

from view import *


# ==========================================================
# MOSTRAR ROTAS
# ==========================================================

print("")
print("==========================================")
print("ROTAS REGISTRADAS:")
print("==========================================")

for rota in app.url_map.iter_rules():

    print(
        rota,
        "->",
        ", ".join(rota.methods)
    )

print("==========================================")
print("")


# ==========================================================
# INICIAR
# ==========================================================

if __name__ == '__main__':

    app.run(

        host='0.0.0.0',

        port=5000,

        debug=True
    )