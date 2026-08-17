from flask import jsonify, request
import jwt
from datetime import datetime, timedelta
from main import app, conectar_banco
from funcoes import verificar_senha


@app.route('/login', methods=['POST'])
def login():

    con = None

    try:

        dados = request.get_json()

        if not dados:
            return jsonify({
                'erro': 'Dados não enviados.'
            }), 400

        email = dados.get('email')
        senha = dados.get('senha')

        if not email:
            return jsonify({
                'erro': 'O email é obrigatório.'
            }), 400

        if not senha:
            return jsonify({
                'erro': 'A senha é obrigatória.'
            }), 400

        # ==========================================
        # CONECTAR AO BANCO
        # ==========================================

        con = conectar_banco()
        cursor = con.cursor()

        cursor.execute("""
            SELECT
                ID_USUARIO,
                NOME,
                EMAIL,
                SENHA_HASH,
                TIPO,
                ATIVO,
                EMAIL_CONFIRMA DO
            FROM USUARIO
            WHERE EMAIL = ?
        """, (email,))

        usuario = cursor.fetchone()

        cursor.close()
        con.close()
        con = None

        # ==========================================
        # USUÁRIO NÃO ENCONTRADO
        # ==========================================

        if not usuario:

            return jsonify({
                'erro': 'Email ou senha incorretos.'
            }), 401

        # ==========================================
        # DADOS DO USUÁRIO
        # ==========================================

        id_usuario = usuario[0]
        nome = usuario[1]
        email_banco = usuario[2]
        senha_hash = usuario[3]
        tipo = usuario[4]
        ativo = usuario[5]
        email_confirmado = usuario[6]

        # ==========================================
        # VERIFICAR E-MAIL
        # ==========================================

        if email_confirmado != 1:

            return jsonify({
                'erro': 'Confirme seu e-mail antes de fazer login.'
            }), 403

        # ==========================================
        # VERIFICAR USUÁRIO ATIVO
        # ==========================================

        if ativo != 1:

            return jsonify({
                'erro': 'Usuário inativo ou bloqueado.'
            }), 403

        # ==========================================
        # VERIFICAR SENHA
        # ==========================================

        if not verificar_senha(senha, senha_hash):

            return jsonify({
                'erro': 'Email ou senha incorretos.'
            }), 401

        # ==========================================
        # GERAR TOKEN
        # ==========================================

        token = jwt.encode(
            {
                'id_usuario': id_usuario,
                'email': email_banco,
                'tipo': tipo,
                'exp': datetime.utcnow() + timedelta(hours=2)
            },
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )

        # ==========================================
        # RESPOSTA
        # ==========================================

        resposta = jsonify({
            'mensagem': 'Login realizado com sucesso.',
            'usuario': {
                'id': id_usuario,
                'nome': nome,
                'email': email_banco,
                'tipo': tipo
            }
        })

        resposta.set_cookie(
            'access_token',
            token,
            httponly=True,
            samesite='Lax',
            secure=False
        )

        return resposta, 200

    except Exception as e:

        if con:
            con.rollback()
            con.close()

        print('Erro no login:', e)

        return jsonify({
            'erro': 'Erro interno no servidor.',
            'detalhes': str(e)
        }), 500