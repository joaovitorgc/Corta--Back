from flask import Flask, jsonify, request, render_template
from flask_bcrypt import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText
import jwt
import re
import random
from main import app
from flask_bcrypt import Bcrypt


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

import smtplib
from email.mime.text import MIMEText


def enviando_email(
    destinatario,
    assunto,
    mensagem,
    codigo,
    nome,
    mensagem_secundaria
):

    user = "mauroauroadm@gmail.com"
    senha = "dyql srcx kqss zqpz"

    try:

        with app.app_context():

            html = render_template(
                "ativacao.html",
                mensagem=mensagem,
                codigo=codigo,
                nome=nome,
                mensagem_secundaria=mensagem_secundaria
            )

        msg = MIMEText(
            html,
            "html",
            "utf-8"
        )

        msg["Subject"] = assunto
        msg["From"] = user
        msg["To"] = destinatario

        print("Conectando ao Gmail...")

        with smtplib.SMTP(
            "smtp.gmail.com",
            587,
            timeout=60
        ) as server:

            server.ehlo()

            print("Iniciando TLS...")
            server.starttls()

            server.ehlo()

            print("Fazendo login...")
            server.login(user, senha)

            print("Enviando email...")

            server.send_message(msg)

            print("Email enviado com sucesso!")

    except smtplib.SMTPAuthenticationError as e:
        print("Erro de autenticação:", e)

    except smtplib.SMTPServerDisconnected as e:
        print("Servidor desconectou:", e)

    except smtplib.SMTPException as e:
        print("Erro SMTP:", e)

    except Exception as e:
        print("Erro ao enviar email:", e)