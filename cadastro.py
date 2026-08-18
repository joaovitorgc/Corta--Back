from flask import request, jsonify, render_template
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import smtplib

from main import app, conectar_banco

from funcoes import (
    verificar_senha_forte,
    criptografar_senha,
    gerar_codigo_verificacao,
    enviando_email,
    decodificar_token
)


# ==========================================
# ENVIAR E-MAIL
# ==========================================

def enviar_email_ativacao(email_destino, nome, codigo):

    html = render_template(
        'ativacao.html',
        nome=nome,
        codigo=codigo
    )

    mensagem = MIMEMultipart('alternative')

    mensagem['Subject'] = 'Ative sua conta - Cortaê'
    mensagem['From'] = app.config['EMAIL_FROM']
    mensagem['To'] = email_destino

    mensagem.attach(
        MIMEText(
            html,
            'html',
            'utf-8'
        )
    )

    servidor = smtplib.SMTP(
        app.config['EMAIL_HOST'],
        app.config['EMAIL_PORT']
    )

    servidor.starttls()

    servidor.login(
        app.config['EMAIL_USER'],
        app.config['EMAIL_PASSWORD']
    )

    servidor.sendmail(
        app.config['EMAIL_FROM'],
        email_destino,
        mensagem.as_string()
    )

    servidor.quit()


# ==========================================
# CADASTRO
# ==========================================

@app.route('/cadastro', methods=['POST'])
def cadastro():

    con = None

    try:

        dados = request.get_json(silent=True)

        if not dados:
            return jsonify({
                'mensagem': {"informacao":'Envie os dados em formato JSON.',
                             "tipo":"erro"}
            }), 400

        nome = dados.get('nome')
        email = dados.get('email')
        telefone = dados.get('telefone')
        senha = dados.get('senha')
        confirmar_senha = dados.get('confirmarSenha')
        tipo = dados.get('tipo')

        # ==========================================
        # CAMPOS OBRIGATÓRIOS
        # ==========================================

        if not nome:
            return jsonify({
                'mensagem': {"informacao":'Nome é obrigatório.',
                             "tipo":"erro"}
            }), 400

        if not email:
            return jsonify({
                'mensagem': {"informacao":'E-mail é obrigatório.',
                         "tipo":"erro"}
            }), 400

        if not telefone:
            return jsonify({
                'mensagem': {"informacao":'Telefone é obrigatório.',
                         "tipo":"erro"}
            }), 400

        if not senha:
            return jsonify({
                'mensagem': {"informacao":'Senha é obrigatória.',
                             "tipo":"erro"}
            }), 400

        if not confirmar_senha:
            return jsonify({
                'mensagem': {"informacao":'Confirmação de senha é obrigatória.',
                             "tipo":"erro"}
            }), 400

        if tipo is None:
            return jsonify({
                'mensagem': {"informacao":'Tipo de usuário é obrigatório.',
                             "tipo":"erro"}
            }), 400

        # ==========================================
        # CONFIRMAR SENHA
        # ==========================================

        if senha != confirmar_senha:

            return jsonify({
                'mensagem': {"informacao":'As senhas não coincidem.',
                             "tipo":"erro"}
            }), 400

        # ==========================================
        # VERIFICAR SENHA FORTE
        # ==========================================

        senha_valida, mensagem_senha = verificar_senha_forte(
            senha
        )

        if not senha_valida:

            return jsonify({
                'mensagem': {"informacao":mensagem_senha,
                             "tipo":"erro"}
            }), 400

        # ==========================================
        # VALIDAR TIPO
        # ==========================================

        try:

            tipo = int(tipo)

        except (ValueError, TypeError):

            return jsonify({
                'mensagem': {"informacao":'Tipo de usuário inválido.',
                             "tipo":"erro"}
            }), 400

        if tipo not in [1, 2, 3]:

            return jsonify({
                'men': 'Tipo de usuário inválido.'
            }), 400

        # ==========================================
        # CONECTAR BANCO
        # ==========================================

        con = conectar_banco()

        cursor = con.cursor()

        # ==========================================
        # VERIFICAR SE EMAIL JÁ EXISTE
        # ==========================================

        cursor.execute(
            '''
            SELECT ID_USUARIO
            FROM USUARIO
            WHERE EMAIL = ?
            ''',
            (email,)
        )

        usuario_existente = cursor.fetchone()

        if usuario_existente:

            return jsonify({
                'mensagem': {"informacao":'Este e-mail já está cadastrado.',
                             "tipo":"erro"}
            }), 409

        # ==========================================
        # GERAR ID
        # ==========================================

        cursor.execute(
            '''
            SELECT COALESCE(MAX(ID_USUARIO), 0) + 1
            FROM USUARIO
            '''
        )

        resultado = cursor.fetchone()

        id_usuario = resultado[0]

        # ==========================================
        # CRIPTOGRAFAR SENHA
        # ==========================================

        senha_hash = criptografar_senha(
            senha
        )

        # ==========================================
        # GERAR CÓDIGO
        # ==========================================

        codigo = gerar_codigo_verificacao()

        # ==========================================
        # CADASTRAR USUÁRIO
        # ==========================================

        cursor.execute(
            '''
            INSERT INTO USUARIO
            (
                ID_USUARIO,
                NOME,
                EMAIL,
                TELEFONE,
                SENHA_HASH,
                TIPO,
                TENTATIVA,
                ATIVO,
                CODIGO_VERIFICACAO
            )
            VALUES
            (
                ?, ?, ?, ?, ?, ?,
                0,
                0,
                ?
            )
            ''',
            (
                id_usuario,
                nome,
                email,
                telefone,
                senha_hash,
                tipo,
                codigo
            )
        )

        # ==========================================
        # SALVAR NO BANCO
        # ==========================================

        con.commit()

        cursor.close()
        con.close()

        con = None

        # ==========================================
        # ENVIAR EMAIL
        # ==========================================

        email_enviado = enviando_email(
            destinatario=email,
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
                'mensagem':{"informacao":'Cadastro realizado, mas não foi possível '
                    'enviar o e-mail de confirmação.',"tipo":"erro"}

            }), 500

        # ==========================================
        # SUCESSO
        # ==========================================

        return jsonify({
            'mensagem':{"informacao":'Cadastro realizado com sucesso! '
                                    'Um código de confirmação foi enviado '
                                    'para seu e-mail.',
                        "tipo":"sucesso"}

        }), 201

    except Exception as erro:

        if con:

            con.rollback()

        print(
            'ERRO NO CADASTRO:',
            erro
        )

        return jsonify({
            'mensagem': {"informacao":'Erro ao realizar cadastro.',"tipo":"erro"},
            'detalhes': str(erro)
        }), 500

    finally:

        if con:

            con.close()


# ==========================================
# VERIFICAR CÓDIGO
# ==========================================

@app.route('/verificar-codigo', methods=['POST'])
def verificar_codigo():

    con = None

    try:

        dados = request.get_json(silent=True)

        if not dados:
            return jsonify({
                'mensagem': {
                    'informacao': 'Envie os dados em formato JSON.',
                    'tipo': 'erro'
                }
            }), 400

        email = dados.get('email')
        codigo = dados.get('codigo')

        if not email:
            return jsonify({
                'mensagem': {
                    'informacao': 'E-mail é obrigatório.',
                    'tipo': 'erro'
                }
            }), 400

        if not codigo:
            return jsonify({
                'mensagem': {
                    'informacao': 'Código de ativação é obrigatório.',
                    'tipo': 'erro'
                }
            }), 400

        email = str(email).strip()
        codigo = str(codigo).strip()

        con = conectar_banco()
        cursor = con.cursor()

        cursor.execute(
            '''
            SELECT
                ID_USUARIO,
                CODIGO_VERIFICACAO,
                ATIVO
            FROM USUARIO
            WHERE EMAIL = ?
            ''',
            (email,)
        )

        usuario = cursor.fetchone()

        if not usuario:

            return jsonify({
                'mensagem': {
                    'informacao': 'Usuário não encontrado.',
                    'tipo': 'erro'
                }
            }), 404

        id_usuario = usuario[0]
        codigo_banco = usuario[1]
        ativo = usuario[2]

        print('==============================')
        print('VERIFICAÇÃO DE E-MAIL')
        print('ID:', id_usuario)
        print('E-MAIL:', email)
        print('CÓDIGO RECEBIDO:', codigo)
        print('CÓDIGO BANCO:', codigo_banco)
        print('ATIVO:', ativo)
        print('==============================')

        # ==========================================
        # JÁ ATIVADO
        # ==========================================

        if int(ativo or 0) == 1:

            return jsonify({
                'mensagem': {
                    'informacao': 'Esta conta já está ativada.',
                    'tipo': 'sucesso'
                }
            }), 200

        # ==========================================
        # CÓDIGO NÃO EXISTE
        # ==========================================

        if codigo_banco is None:

            return jsonify({
                'mensagem': {
                    'informacao': 'Código de ativação não encontrado.',
                    'tipo': 'erro'
                }
            }), 400

        # ==========================================
        # COMPARAR CÓDIGO
        # ==========================================

        if codigo != str(codigo_banco).strip():

            return jsonify({
                'mensagem': {
                    'informacao': 'Código de verificação inválido.',
                    'tipo': 'erro'
                }
            }), 400

        # ==========================================
        # ATIVAR USUÁRIO
        # ==========================================

        cursor.execute(
            '''
            UPDATE USUARIO
            SET
                ATIVO = 1,
                EMAIL_CONFIRMADO = 1,
                CODIGO_VERIFICACAO = NULL
            WHERE ID_USUARIO = ?
            ''',
            (id_usuario,)
        )

        con.commit()

        print('USUÁRIO ATIVADO COM SUCESSO!')

        return jsonify({
            'mensagem': {
                'informacao': 'E-mail confirmado com sucesso! Sua conta foi ativada.',
                'tipo': 'sucesso'
            }
        }), 200

    except Exception as erro:

        if con:
            con.rollback()

        print('ERRO AO VERIFICAR CÓDIGO:', erro)

        return jsonify({
            'mensagem': {
                'informacao': 'Erro ao verificar código.',
                'tipo': 'erro'
            },
            'detalhes': str(erro)
        }), 500

    finally:

        if con:
            con.close()


# ==========================================
# EDITAR USUÁRIO
# ==========================================

@app.route('/editar-usuario/<int:id_usuario>', methods=['PUT'])
def editar_usuario(id_usuario):

    con = None

    try:

        # ==========================================
        # VERIFICAR TOKEN
        # ==========================================

        token_data = decodificar_token()

        if not token_data:
            return jsonify({
                'mensagem': {"informacao":'Token necessário.',
                             "tipo":"erro"}
            }), 401

        if token_data['id_usuario'] != id_usuario and token_data['tipo'] != 0:
            return jsonify({
                'mensagem': {"informacao":'Você só pode editar seu próprio perfil.',"tipo":"erro"}
            }), 403

        # ==========================================
        # PEGAR DADOS
        # ==========================================

        dados = request.get_json(silent=True)

        if not dados:
            return jsonify({
                'mensagem': {"informacao":'Envie os dados em formato JSON.',"tipo":"erro"}
            }), 400

        nome = dados.get('nome')
        email = dados.get('email')
        telefone = dados.get('telefone')
        senha = dados.get('senha')
        confirmar_senha = dados.get('confirmarSenha')

        # ==========================================
        # CONECTAR BANCO
        # ==========================================

        con = conectar_banco()
        cursor = con.cursor()

        # ==========================================
        # BUSCAR USUÁRIO
        # ==========================================

        cursor.execute(
            '''
            SELECT
                ID_USUARIO,
                NOME,
                EMAIL,
                TELEFONE,
                SENHA_HASH
            FROM USUARIO
            WHERE ID_USUARIO = ?
            ''',
            (id_usuario,)
        )

        usuario = cursor.fetchone()

        if not usuario:
            return jsonify({
                'mensagem': {"informacao":'Usuário não encontrado.',"tipo":"erro"}
            }), 404

        # ==========================================
        # MANTER DADOS ANTIGOS
        # ==========================================

        if not nome:
            nome = usuario[1]

        if not email:
            email = usuario[2]

        if not telefone:
            telefone = usuario[3]

        senha_hash = usuario[4]

        # ==========================================
        # VALIDAR NOME
        # ==========================================

        if not nome.strip():
            return jsonify({
                'mensagem': {"informacao":'Nome é obrigatório.',"tipo":"erro"}
            }), 400

        # ==========================================
        # VALIDAR EMAIL
        # ==========================================

        if not email.strip():
            return jsonify({
                'mensagem': {"informacao":'E-mail é obrigatório.',"tipo":'erro'}
            }), 400

        # ==========================================
        # VERIFICAR EMAIL DUPLICADO
        # ==========================================

        if email != usuario[2]:

            cursor.execute(
                '''
                SELECT ID_USUARIO
                FROM USUARIO
                WHERE EMAIL = ?
                AND ID_USUARIO <> ?
                ''',
                (email, id_usuario)
            )

            email_existente = cursor.fetchone()

            if email_existente:
                return jsonify({
                    'mensagem': {"informacao":'Este e-mail já está cadastrado.',"tipo":"erro"}
                }), 409

        # ==========================================
        # ALTERAR SENHA
        # ==========================================

        if senha:

            if not confirmar_senha:
                return jsonify({
                    'mensagem': {"informacao":'Confirmação de senha é obrigatória.',"tipo":"erro"}
                }), 400

            if senha != confirmar_senha:
                return jsonify({
                    'mensagem': {"informacao":'As senhas não coincidem.',"tipo":"erro"}
                }), 400

            senha_valida, mensagem_senha = verificar_senha_forte(senha)

            if not senha_valida:
                return jsonify({
                    'mensagem': {"informacao":mensagem_senha,"tipo":"erro"}
                }), 400

            senha_hash = criptografar_senha(senha)

        # ==========================================
        # ATUALIZAR USUÁRIO
        # ==========================================

        cursor.execute(
            '''
            UPDATE USUARIO
            SET
                NOME = ?,
                EMAIL = ?,
                TELEFONE = ?,
                SENHA_HASH = ?
            WHERE ID_USUARIO = ?
            ''',
            (
                nome,
                email,
                telefone,
                senha_hash,
                id_usuario
            )
        )

        # ==========================================
        # SALVAR NO BANCO
        # ==========================================

        con.commit()

        return jsonify({
            'mensagem': {"informacao":'Usuário editado com sucesso!',"tipo":"sucesso"},
            'usuario': {
                'id_usuario': id_usuario,
                'nome': nome,
                'email': email,
                'telefone': telefone
            }
        }), 200

    except Exception as erro:

        if con:
            con.rollback()

        print('ERRO AO EDITAR USUÁRIO:', erro)

        return jsonify({
            'erro': {"informacao":'Erro ao editar usuário.',"tipo":"erro"},
            'detalhes': str(erro)
        }), 500

    finally:

        if con:
            con.close()