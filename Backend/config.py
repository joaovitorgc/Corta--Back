import os


# ==========================================================
# SEGURANÇA
# ==========================================================

SECRET_KEY = 'minhasenhasupersecretacomçe~´`^antihackeramericanoerusso'

DEBUG = True


# ==========================================================
# DIRETÓRIO PRINCIPAL DO BACKEND
# ==========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ==========================================================
# FIREBIRD
# ==========================================================

DB_HOST = 'localhost'

DB_NAME = os.path.join(
    BASE_DIR,
    'CORTAE.FDB'
)

DB_USER = 'SYSDBA'

DB_PASSWORD = 'sysdba'


# ==========================================================
# EMAIL - GMAIL
# ==========================================================

MAIL_USER = 'mauroauroadm@gmail.com'

MAIL_PASSWORD = 'dyql srcx kqss zqpz'


# ==========================================================
# SMTP
# ==========================================================

MAIL_SERVER = 'smtp.gmail.com'

MAIL_PORT = 465


# ==========================================================
# UPLOADS
# ==========================================================

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    'uploads'
)


# ==========================================================
# FOTOS DE PERFIL
# ==========================================================

PERFIL_FOLDER = os.path.join(
    UPLOAD_FOLDER,
    'perfil'
)