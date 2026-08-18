from flask import request, jsonify, render_template
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import smtplib

from main import app, conectar_banco

from funcoes import (
    verificar_senha_forte,
    criptografar_senha,
    gerar_codigo_verificacao,
    enviando_email
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
                'erro': 'Envie os dados em formato JSON.'
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
                'erro': 'Nome é obrigatório.'
            }), 400

        if not email:
            return jsonify({
                'erro': 'E-mail é obrigatório.'
            }), 400

        if not telefone:
            return jsonify({
                'erro': 'Telefone é obrigatório.'
            }), 400

        if not senha:
            return jsonify({
                'erro': 'Senha é obrigatória.'
            }), 400

        if not confirmar_senha:
            return jsonify({
                'erro': 'Confirmação de senha é obrigatória.'
            }), 400

        if tipo is None:
            return jsonify({
                'erro': 'Tipo de usuário é obrigatório.'
            }), 400

        # ==========================================
        # CONFIRMAR SENHA
        # ==========================================

        if senha != confirmar_senha:

            return jsonify({
                'erro': 'As senhas não coincidem.'
            }), 400

        # ==========================================
        # VERIFICAR SENHA FORTE
        # ==========================================

        senha_valida, mensagem_senha = verificar_senha_forte(
            senha
        )

        if not senha_valida:

            return jsonify({
                'erro': mensagem_senha
            }), 400

        # ==========================================
        # VALIDAR TIPO
        # ==========================================

        try:

            tipo = int(tipo)

        except (ValueError, TypeError):

            return jsonify({
                'erro': 'Tipo de usuário inválido.'
            }), 400

        if tipo not in [1, 2, 3]:

            return jsonify({
                'erro': 'Tipo de usuário inválido.'
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
                'erro': 'Este e-mail já está cadastrado.'
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
                'erro':
                    'Cadastro realizado, mas não foi possível '
                    'enviar o e-mail de confirmação.'
            }), 500

        # ==========================================
        # SUCESSO
        # ==========================================

        return jsonify({
            'mensagem':
                'Cadastro realizado com sucesso! '
                'Um código de confirmação foi enviado '
                'para seu e-mail.'
        }), 201

    except Exception as erro:

        if con:

            con.rollback()

        print(
            'ERRO NO CADASTRO:',
            erro
        )

        return jsonify({
            'erro': 'Erro ao realizar cadastro.',
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

        dados = request.get_json()

        email = dados.get('email')
        codigo = dados.get('codigo')

        if not email or not codigo:

            return jsonify({
                'erro':
                    'E-mail e código são obrigatórios.'
            }), 400

        con = conectar_banco()
        cursor = con.cursor()

        cursor.execute(
            '''
            SELECT
                ID_USUARIO,
                CODIGO_VERIFICACAO,
                EMAIL_CONFIRMANDO
            FROM USUARIO
            WHERE EMAIL = ?
            ''',
            (email,)
        )

        usuario = cursor.fetchone()

        if not usuario:

            return jsonify({
                'erro': 'Usuário não encontrado.'
            }), 404

        id_usuario = usuario[0]
        codigo_banco = usuario[1]
        email_confirmado = usuario[2]

        # ==========================================
        # JÁ CONFIRMADO
        # ==========================================

        if email_confirmado == 1:

            return jsonify({
                'mensagem':
                    'Este e-mail já foi confirmado.'
            }), 200

        # ==========================================
        # COMPARAR CÓDIGO
        # ==========================================

        if str(codigo) != str(codigo_banco):

            return jsonify({
                'mensagem':
                    {"informacao":'Código de verificação inválido.',
                     "tipo":'erro'}
            }), 400

        # ==========================================
        # CONFIRMAR E-MAIL
        # ==========================================

        cursor.execute(
            '''
            UPDATE USUARIO
            SET
                ATIVO = 1,
                EMAIL_CONFIRMANDO = 1,
                CODIGO_VERIFICACAO = NULL
            WHERE ID_USUARIO = ?
            ''',
            (id_usuario,)
        )

        con.commit()

        return jsonify({
            'mensagem':
                'E-mail confirmado com sucesso!'
        }), 200

    except Exception as erro:

        if con:
            con.rollback()

        print('ERRO AO VERIFICAR CÓDIGO:', erro)

        return jsonify({
            'erro':
                'Erro ao verificar código.',
            'detalhes':
                str(erro)
        }), 500

    finally:

        if con:
            con.close()




