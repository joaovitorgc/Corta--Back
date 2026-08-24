# ==========================================================
# IMPORTADOR CENTRAL DAS ROTAS
# ==========================================================

from cadastro import *
from login import *
from recuperar_senha import *
from editar_usuario import *


# ==========================================================
# SERVIR FOTOS DE PERFIL
# ==========================================================

import os

from flask import (
    send_from_directory,
    current_app
)


@app.route(
    '/fotos-perfil/<nome_arquivo>',
    methods=['GET']
)
def fotos_perfil(nome_arquivo):

    pasta_perfil = current_app.config.get(
        'PERFIL_FOLDER'
    )

    if not pasta_perfil:

        return {
            'erro': 'Pasta de perfil não configurada.'
        }, 500

    if not os.path.isdir(
            pasta_perfil
    ):

        return {
            'erro': 'Pasta de perfil não encontrada.'
        }, 404

    return send_from_directory(
        pasta_perfil,
        nome_arquivo
    )