from flask import jsonify, request, make_response
import jwt
from datetime import datetime, timedelta
from main import app, conectar_banco
from funcoes import verificar_senha, gerar_codigo_verificacao, enviando_email


@app.route('/login', methods=['POST'])
def login():

    con = None
    cursor = None

    try:

        dados = request.get_json()

        if not dados:
            return jsonify({
                'mensagem': {
                    "informacao": 'Dados não enviados.',
                    "tipo": "erro"
                }
            }), 400

        email = dados.get('email')
        senha = dados.get('senha')

        # ==========================================
        # VALIDAR EMAIL
        # ==========================================

        if not email:
            return jsonify({
                'mensagem': {
                    "informacao": 'O email é obrigatório.',
                    "tipo": "erro"
                }
            }), 400

        # ==========================================
        # VALIDAR SENHA
        # ==========================================

        if not senha:
            return jsonify({
                'mensagem': {
                    "informacao": 'A senha é obrigatória.',
                    "tipo": "erro"
                }
            }), 400

        # ==========================================
        # CONECTAR AO BANCO
        # ==========================================

        con = conectar_banco()
        cursor = con.cursor()

        # ==========================================
        # BUSCAR USUÁRIO
        # ==========================================

        cursor.execute("""
            SELECT
                ID_USUARIO,
                NOME,
                EMAIL,
                SENHA_HASH,
                TIPO,
                ATIVO,
                EMAIL_CONFIRMADO,
                TENTATIVA
            FROM USUARIO
            WHERE EMAIL = ?
        """, (email,))

        usuario = cursor.fetchone()

        # ==========================================
        # EMAIL NÃO ENCONTRADO
        # ==========================================

        if not usuario:

            return jsonify({
                'mensagem': {
                    "informacao": 'Email ou senha incorretos.',
                    "tipo": 'erro'
                }
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
        tentativas = usuario[7] or 0

        # ==========================================
        # VERIFICAR E-MAIL
        # ==========================================

        if email_confirmado != 1:

            # ==========================================
            # GERAR NOVO CÓDIGO
            # ==========================================

            codigo = gerar_codigo_verificacao()

            # ==========================================
            # SALVAR CÓDIGO NO BANCO
            # ==========================================

            cursor.execute("""
                UPDATE USUARIO
                SET CODIGO_VERIFICACAO = ?
                WHERE ID_USUARIO = ?
            """, (codigo, id_usuario))

            con.commit()

            # ==========================================
            # ENVIAR EMAIL
            # ==========================================

            email_enviado = enviando_email(
                destinatario=email_banco,
                assunto='Confirmação de cadastro - Cortaê',
                mensagem='Seu cadastro foi realizado com sucesso!',
                codigo=codigo,
                nome=nome,
                mensagem_secundaria=(
                    'Utilize o código abaixo para confirmar '
                    'seu endereço de e-mail.'
                )
            )

            # ==========================================
            # VERIFICAR ENVIO
            # ==========================================

            if not email_enviado:

                return jsonify({
                    'mensagem': {
                        'informacao': (
                            'Seu e-mail ainda não foi confirmado, '
                            'mas não foi possível enviar o código '
                            'de verificação.'
                        ),
                        'tipo': 'erro'
                    }
                }), 500

            # ==========================================
            # EMAIL ENVIADO
            # ==========================================

            return jsonify({
                'mensagem': {
                    'informacao': (
                        'Seu e-mail ainda não foi confirmado. '
                        'Um novo código de verificação foi enviado '
                        'para seu e-mail.'
                    ),
                    'tipo': 'aviso'
                },
                'email_confirmacao': True
            }), 403

        # ==========================================
        # VERIFICAR STATUS DO USUÁRIO
        # ==========================================

        # ATIVO = 2 -> BLOQUEADO
        if ativo == 2:

            return jsonify({
                'mensagem': {
                    'informacao': (
                        'Usuário bloqueado após exceder o limite '
                        'de tentativas de login.'
                    ),
                    'tipo': 'erro'
                }
            }), 403

        # ATIVO DIFERENTE DE 1 -> INATIVO
        if ativo != 1:

            return jsonify({
                'mensagem': {
                    'informacao': 'Usuário inativo.',
                    'tipo': 'erro'
                }
            }), 403

        # ==========================================
        # VERIFICAR SENHA
        # ==========================================

        if not verificar_senha(senha, senha_hash):

            # Adicionar uma tentativa
            novas_tentativas = tentativas + 1

            # ==========================================
            # 3 TENTATIVAS -> BLOQUEAR
            # ==========================================

            if novas_tentativas >= 3:

                cursor.execute("""
                    UPDATE USUARIO
                    SET
                        TENTATIVA = ?,
                        ATIVO = 2
                    WHERE ID_USUARIO = ?
                """, (
                    novas_tentativas,
                    id_usuario
                ))

                con.commit()

                return jsonify({
                    'mensagem': {
                        'informacao': (
                            'Usuário bloqueado após 3 '
                            'tentativas de login incorretas.'
                        ),
                        'tipo': 'erro'
                    }
                }), 403

            # ==========================================
            # REGISTRAR TENTATIVA
            # ==========================================

            cursor.execute("""
                UPDATE USUARIO
                SET TENTATIVA = ?
                WHERE ID_USUARIO = ?
            """, (
                novas_tentativas,
                id_usuario
            ))

            con.commit()

            restantes = 3 - novas_tentativas

            return jsonify({
                'mensagem': {
                    'informacao': (
                        f'Email ou senha incorretos. '
                        f'Você possui {restantes} tentativa(s) restante(s).'
                    ),
                    'tipo': 'erro'
                }
            }), 401

        # ==========================================
        # SENHA CORRETA
        # ==========================================

        cursor.execute("""
            UPDATE USUARIO
            SET TENTATIVA = 0
            WHERE ID_USUARIO = ?
        """, (id_usuario,))

        con.commit()

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
            'mensagem': {
                'informacao': 'Login realizado com sucesso.',
                'tipo': 'sucesso'
            },
            'usuario': {
                'id': id_usuario,
                'nome': nome,
                'email': email_banco,
                'tipo': tipo
            }
        })

        # ==========================================
        # COOKIE JWT
        # ==========================================

        resposta.set_cookie(
            'access_token',
            token,
            httponly=True,
            samesite='Lax',
            secure=False
        )

        return resposta, 200

    # ==========================================
    # ERRO
    # ==========================================

    except Exception as e:

        if con:

            try:
                con.rollback()
            except:
                pass

        print('Erro no login:', e)

        return jsonify({
            'mensagem': {
                'informacao': 'Erro interno no servidor.',
                'tipo': 'erro'
            },
            'detalhes': str(e)
        }), 500

    # ==========================================
    # FECHAR CONEXÃO
    # ==========================================

    finally:

        if cursor:

            try:
                cursor.close()
            except:
                pass

        if con:

            try:
                con.close()
            except:
                pass

@app.route('/logout', methods=['POST'])
def logout():
    resp = make_response(jsonify({'mensagem': 'Logout realizado com sucesso!'}),200)
    resp.delete_cookie('acess_token')
    return resp