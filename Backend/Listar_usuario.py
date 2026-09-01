from flask import request, jsonify
from main import app, conectar_banco


@app.route('/listar_usuarios', methods=['GET'])
def listar_usuarios():

    try:
        con = conectar_banco()
        cursor = con.cursor()

        tipo = request.args.get('tipo')

        if tipo is not None:

            tipo = int(tipo)

            cursor.execute("""
                SELECT ID_USUARIO, NOME, TIPO
                FROM USUARIO
                WHERE TIPO = ?
                ORDER BY ID_USUARIO
            """, (tipo,))

        else:

            cursor.execute("""
                SELECT ID_USUARIO, NOME, TIPO
                FROM USUARIO
                ORDER BY ID_USUARIO
            """)

        usuarios = cursor.fetchall()

        resultado = []

        for usuario in usuarios:

            if usuario[2] == 0:
                tipo_nome = 'ADM'

            elif usuario[2] == 1:
                tipo_nome = 'Usuário'

            elif usuario[2] == 2:
                tipo_nome = 'Barbeiro'

            else:
                tipo_nome = 'Desconhecido'

            resultado.append({
                'id': usuario[0],
                'nome': usuario[1],
                'tipo': usuario[2],
                'tipo_nome': tipo_nome
            })

        cursor.close()
        con.close()

        return jsonify(resultado), 200

    except Exception as erro:

        return jsonify({
            'erro': str(erro)
        }), 500