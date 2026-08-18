from flask import Flask, jsonify, request, render_template
from flask_bcrypt import generate_password_hash, check_password_hash

import jwt
import re
import random
from main import app
from flask_bcrypt import Bcrypt

import smtplib
from email.mime.text import MIMEText

bcrypt = Bcrypt()


# ==========================================
# VERIFICAR SENHA FORTE
# ==========================================

def verificar_senha_forte(senha):

    if len(senha) < 8:
        return False, "A senha deve ter no mínimo 8 caracteres."

    if not re.search(r"[A-Z]", senha):
        return False, "A senha deve possuir uma letra maiúscula."

    if not re.search(r"[a-z]", senha):
        return False, "A senha deve possuir uma letra minúscula."

    if not re.search(r"[0-9]", senha):
        return False, "A senha deve possuir um número."

    if not re.search(r"[^A-Za-z0-9]", senha):
        return False, "A senha deve possuir um caractere especial."

    return True, "Senha válida."


# ==========================================
# CRIPTOGRAFAR SENHA
# ==========================================

def criptografar_senha(senha):

    return bcrypt.generate_password_hash(
        senha
    ).decode("utf-8")


# ==========================================
# VERIFICAR SENHA
# ==========================================

def verificar_senha(senha, senha_hash):

    return bcrypt.check_password_hash(
        senha_hash,
        senha
    )


# ==========================================
# GERAR CÓDIGO
# ==========================================

def gerar_codigo_verificacao():

    return str(
        random.randint(100000, 999999)
    )

# =========================================
# ENVIAR EMAIL
# =========================================

def enviando_email(
    destinatario,
    assunto,
    mensagem,
    nome,
    codigo,
    mensagem_secundaria
):

    user = "mauroauroadm@gmail.com"
    senha = "dyql srcx kqss zqpz"

    try:

        # Renderiza o HTML e substitui as variáveis
        with app.app_context():

            html = render_template(
                "ativacao.html",
                nome=nome,
                mensagem=mensagem,
                codigo=codigo,
                mensagem_secundaria=mensagem_secundaria
            )

        # Cria o email
        msg = MIMEText(
            html,
            "html",
            "utf-8"
        )

        msg["Subject"] = assunto
        msg["From"] = user
        msg["To"] = destinatario

        # Conexão com Gmail
        server = smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465,
            timeout=60
        )

        # Login
        server.login(
            user,
            senha
        )

        # Envio
        server.send_message(msg)

        # Fecha conexão
        server.quit()

        print("Email enviado com sucesso!")


        return True

    except Exception as e:

        print("Erro ao enviar email:", e)

        return False
