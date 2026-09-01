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
                "http://10.92.11.47:5173",
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
from Listar_usuario import *

if __name__ == '__main__':
    from pyngrok import ngrok

    # 1. Configurar o seu Token (Substitua pelo seu token real do site do ngrok)
    # Você só precisa pegar esse token uma vez no painel do ngrok.com
    NGROK_TOKEN = "SEU_TOKEN_AQUI"
    ngrok.set_auth_token(NGROK_TOKEN)



    # 3. Iniciar o servidor Flask normalmente (Link Local)
    print("Iniciando servidor local...")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False  # Evita que o ngrok tente abrir dois túneis ao mesmo tempo no modo debug
    )
