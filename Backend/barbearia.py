import os
import json
import re
import jwt

from flask import jsonify, request, send_from_directory

from main import app, conectar_banco


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

EXTENSOES_PERMITIDAS = {
    'jpg',
    'jpeg',
    'png',
    'webp'
}


# ==========================================================
# USUÁRIO LOGADO
# ==========================================================

def obter_usuario_logado():

    token = request.cookies.get('access_token')

    if not token:
        return None

    try:

        dados = jwt.decode(
            token,
            app.config['SECRET_KEY'],
            algorithms=['HS256']
        )

        return dados

    except jwt.ExpiredSignatureError:

        return None

    except jwt.InvalidTokenError:

        return None


# ==========================================================
# ID DO USUÁRIO
# ==========================================================

def pegar_id_usuario():

    usuario = obter_usuario_logado()

    if not usuario:
        return None

    return usuario.get('id_usuario')


# ==========================================================
# OBTER SERVIÇOS DO FUNCIONÁRIO
# ==========================================================
#
# IMPORTANTE:
#
# Os serviços DEVEM estar previamente cadastrados
# na tabela SERVICO.
#
# Esta função NÃO cadastra serviços.
#
# Ela somente recebe os IDs dos serviços enviados
# pelo frontend/Postman.
#
# Aceita:
#
# funcionarios[0][servicos] = 1,2,3
#
# funcionarios[0][servicos][] = 1
# funcionarios[0][servicos][] = 2
#
# funcionarios[0][servicos][0] = 1
# funcionarios[0][servicos][1] = 2
#
# funcionarios[0][servicos] = [1,2,3]
#
# ==========================================================

def obter_servicos_funcionario(indice):

    prefixo = (
        f'funcionarios[{indice}][servicos]'
    )

    valores = []


    # ======================================================
    # FORMATO:
    #
    # funcionarios[0][servicos] = 1,2,3
    # ======================================================

    valores_diretos = request.form.getlist(
        prefixo
    )

    for valor in valores_diretos:

        if valor is not None and str(valor).strip():

            valores.append(valor)


    # ======================================================
    # FORMATO:
    #
    # funcionarios[0][servicos][] = 1
    # funcionarios[0][servicos][] = 2
    #
    # OU:
    #
    # funcionarios[0][servicos][0] = 1
    # funcionarios[0][servicos][1] = 2
    # ======================================================

    for chave in request.form.keys():

        if chave.startswith(prefixo + '['):

            valores_chave = request.form.getlist(
                chave
            )

            for valor in valores_chave:

                if (
                    valor is not None
                    and str(valor).strip()
                ):

                    valores.append(valor)


    ids_servicos = []


    # ======================================================
    # PROCESSAR VALORES
    # ======================================================

    for valor in valores:

        if valor is None:
            continue


        valor = str(valor).strip()


        if not valor:
            continue


        # ==================================================
        # JSON
        #
        # Exemplo:
        #
        # [1,2,3]
        # ==================================================

        if (
            valor.startswith('[')
            and valor.endswith(']')
        ):

            try:

                lista_json = json.loads(
                    valor
                )


                if isinstance(
                    lista_json,
                    list
                ):

                    for item in lista_json:

                        try:

                            id_servico = int(
                                item
                            )

                        except (
                            ValueError,
                            TypeError
                        ):

                            continue


                        if (
                            id_servico
                            not in ids_servicos
                        ):

                            ids_servicos.append(
                                id_servico
                            )


                    continue


            except (
                json.JSONDecodeError,
                TypeError
            ):

                pass


        # ==================================================
        # VÍRGULA OU PONTO E VÍRGULA
        # ==================================================

        partes = re.split(
            r'[,;]',
            valor
        )


        for parte in partes:

            parte = parte.strip()


            if not parte:
                continue


            try:

                id_servico = int(
                    parte
                )

            except (
                ValueError,
                TypeError
            ):

                continue


            if (
                id_servico
                not in ids_servicos
            ):

                ids_servicos.append(
                    id_servico
                )


    return ids_servicos


# ==========================================================
# VINCULAR SERVIÇOS AO FUNCIONÁRIO
# ==========================================================
#
# IMPORTANTE:
#
# Esta função NÃO cria serviços.
#
# Ela verifica se cada ID_SERVICO:
#
# 1. Existe na tabela SERVICO
# 2. Pertence ao usuário logado
#
# Depois cria a relação:
#
# SERVICO_POR_FUNCIONARIO
#
# ==========================================================

def vincular_servicos_funcionario(
    cursor,
    id_funcionario,
    id_usuario,
    indice
):

    ids_servicos = obter_servicos_funcionario(
        indice
    )


    print(
        '========================================='
    )

    print(
        f'FUNCIONÁRIO ID: {id_funcionario}'
    )

    print(
        'SERVIÇOS RECEBIDOS:',
        ids_servicos
    )


    for id_servico in ids_servicos:

        # ==================================================
        # VERIFICAR SE O SERVIÇO EXISTE
        # E PERTENCE AO USUÁRIO
        # ==================================================

        cursor.execute("""
            SELECT
                ID_SERVICO
            FROM SERVICO
            WHERE
                ID_SERVICO = ?
                AND ID_USUARIO = ?
        """, (
            id_servico,
            id_usuario
        ))


        servico = cursor.fetchone()


        if not servico:

            print(
                f'SERVIÇO {id_servico} '
                f'NÃO EXISTE OU NÃO PERTENCE '
                f'AO USUÁRIO {id_usuario}'
            )

            continue


        # ==================================================
        # EVITAR DUPLICIDADE
        # ==================================================

        cursor.execute("""
            SELECT
                ID_SERVI_FUNCI
            FROM SERVICO_POR_FUNCIONARIO
            WHERE
                ID_FUNCIONARIO = ?
                AND ID_SERVICO = ?
        """, (
            id_funcionario,
            id_servico
        ))


        vinculo_existente = (
            cursor.fetchone()
        )


        if vinculo_existente:

            print(
                f'SERVIÇO {id_servico} '
                f'JÁ ESTÁ VINCULADO '
                f'AO FUNCIONÁRIO {id_funcionario}'
            )

            continue


        # ==================================================
        # CRIAR VÍNCULO
        # ==================================================

        cursor.execute("""
            INSERT INTO SERVICO_POR_FUNCIONARIO (
                ID_FUNCIONARIO,
                ID_SERVICO
            )
            VALUES (?, ?)
        """, (
            id_funcionario,
            id_servico
        ))


        print(
            f'SERVIÇO {id_servico} '
            f'VINCULADO AO FUNCIONÁRIO '
            f'{id_funcionario}'
        )


    print(
        '========================================='
    )


    return ids_servicos


# ==========================================================
# PASTA DA BARBEARIA
# ==========================================================

def criar_pasta_barbearia():

    pasta = os.path.join(
        app.config['UPLOAD_FOLDER'],
        'barbearia'
    )

    os.makedirs(
        pasta,
        exist_ok=True
    )

    return pasta


# ==========================================================
# EXTENSÃO DA IMAGEM
# ==========================================================

def extensao_permitida(nome):

    if not nome:
        return False

    if '.' not in nome:
        return False

    extensao = nome.rsplit(
        '.',
        1
    )[-1].lower()

    return (
        extensao
        in EXTENSOES_PERMITIDAS
    )


# ==========================================================
# EXCLUIR ARQUIVO
# ==========================================================

def excluir_arquivo(caminho):

    if os.path.exists(caminho):

        try:

            os.remove(caminho)

        except Exception as erro:

            print(
                'ERRO AO EXCLUIR ARQUIVO:',
                erro
            )


# ==========================================================
# SALVAR IMAGEM
# ==========================================================

def salvar_imagem(
    arquivo,
    nome_base
):

    if not arquivo:
        return None

    if not arquivo.filename:
        return None

    if not extensao_permitida(
        arquivo.filename
    ):

        raise ValueError(
            'Formato de imagem não permitido. '
            'Use JPG, JPEG, PNG ou WEBP.'
        )


    pasta = criar_pasta_barbearia()


    extensao = (
        arquivo.filename
        .rsplit('.', 1)[-1]
        .lower()
    )


    # ------------------------------------------------------
    # EXCLUIR VERSÕES ANTIGAS
    # ------------------------------------------------------

    for ext in EXTENSOES_PERMITIDAS:

        antigo = os.path.join(
            pasta,
            f'{nome_base}.{ext}'
        )

        excluir_arquivo(
            antigo
        )


    # ------------------------------------------------------
    # SALVAR
    # ------------------------------------------------------

    nome_arquivo = (
        f'{nome_base}.{extensao}'
    )


    caminho = os.path.join(
        pasta,
        nome_arquivo
    )


    arquivo.save(
        caminho
    )


    return (
        f'/uploads/barbearia/'
        f'{nome_arquivo}'
    )


# ==========================================================
# ==========================================================
# CRIAR PERSONALIZAÇÃO
# ==========================================================
# ==========================================================

@app.route(
    '/barbearia/personalizacao',
    methods=['POST']
)
def personalizacao_barbearia():

    con = None
    cursor = None

    try:

        # ==================================================
        # AUTENTICAÇÃO
        # ==================================================

        id_usuario = pegar_id_usuario()

        if not id_usuario:

            return jsonify({

                'mensagem': {

                    'informacao':
                        'Usuário não autenticado.',

                    'tipo':
                        'erro'

                }

            }), 401


        # ==================================================
        # CONEXÃO
        # ==================================================

        con = conectar_banco()

        cursor = con.cursor()


        # ==================================================
        # VERIFICAR PERSONALIZAÇÃO EXISTENTE
        # ==================================================

        cursor.execute("""
            SELECT ID_PERSONALIZACAO
            FROM PERSONALIZACAO
            WHERE ID_USUARIO = ?
        """, (
            id_usuario,
        ))


        existente = (
            cursor.fetchone()
        )


        if existente:

            return jsonify({

                'mensagem': {

                    'informacao':
                        'A barbearia já possui uma personalização.',

                    'tipo':
                        'aviso'

                },

                'id_personalizacao':
                    existente[0]

            }), 409


        # ==================================================
        # DADOS
        # ==================================================

        cor_primaria = request.form.get(
            'cor_primaria'
        )

        cor_secundaria = request.form.get(
            'cor_secundaria'
        )

        cor_terciaria = request.form.get(
            'cor_terciaria'
        )

        historia = request.form.get(
            'historia'
        )

        localizacao = request.form.get(
            'localizacao'
        )

        num_funcionarios = request.form.get(
            'num_funcionarios',
            '0'
        )


        try:

            num_funcionarios = int(
                num_funcionarios
            )

        except (
            ValueError,
            TypeError
        ):

            num_funcionarios = 0


        if num_funcionarios < 0:

            num_funcionarios = 0


        # ==================================================
        # PERSONALIZAÇÃO
        # ==================================================

        cursor.execute("""
            INSERT INTO PERSONALIZACAO (
                ID_USUARIO,
                COR_PRIMARIA,
                COR_SECUNDARIA,
                COR_TERCIARIA,
                TEXTO,
                LOCALIZACAO,
                NUM_FUNCIONARIOS
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING ID_PERSONALIZACAO
        """, (
            id_usuario,
            cor_primaria,
            cor_secundaria,
            cor_terciaria,
            historia,
            localizacao,
            num_funcionarios
        ))


        id_personalizacao = (
            cursor.fetchone()[0]
        )


        # ==================================================
        # DIAS DE SERVIÇO
        # ==================================================

        dias = [

            'segunda',
            'terca',
            'quarta',
            'quinta',
            'sexta',
            'sabado',
            'domingo'

        ]


        ids_dias = {}


        for dia in dias:

            entrada_manha = request.form.get(
                f'{dia}_entrada_manha'
            )

            saida_manha = request.form.get(
                f'{dia}_saida_manha'
            )

            entrada_tarde = request.form.get(
                f'{dia}_entrada_tarde'
            )

            saida_tarde = request.form.get(
                f'{dia}_saida_tarde'
            )


            if not any([

                entrada_manha,
                saida_manha,
                entrada_tarde,
                saida_tarde

            ]):

                continue


            cursor.execute("""
                INSERT INTO DIAS_DE_SERVICO (
                    ID_USUARIO,
                    ENTRADA_MANHA,
                    SAIDA_MANHA,
                    ENTRADA_TARDE,
                    SAIDA_TARDE
                )
                VALUES (?, ?, ?, ?, ?)
                RETURNING ID_DIA
            """, (
                id_usuario,
                entrada_manha,
                saida_manha,
                entrada_tarde,
                saida_tarde
            ))


            id_dia = (
                cursor.fetchone()[0]
            )


            ids_dias[dia] = id_dia


        # ==================================================
        # FUNCIONÁRIOS
        # ==================================================

        funcionarios_criados = []


        for i in range(
            num_funcionarios
        ):

            nome = request.form.get(
                f'funcionarios[{i}][nome]'
            )

            descricao = request.form.get(
                f'funcionarios[{i}][descricao]'
            )

            dia_funcionario = request.form.get(
                f'funcionarios[{i}][dia]'
            )


            if not nome:

                continue


            id_dias = None


            # ------------------------------------------------
            # USAR NOME DO DIA
            # ------------------------------------------------

            if dia_funcionario:

                id_dias = ids_dias.get(
                    dia_funcionario
                )


            # ------------------------------------------------
            # USAR ID_DIAS DIRETAMENTE
            # ------------------------------------------------

            if not id_dias:

                id_dias_form = request.form.get(
                    f'funcionarios[{i}][id_dias]'
                )


                if id_dias_form:

                    try:

                        id_dias = int(
                            id_dias_form
                        )

                    except (
                        ValueError,
                        TypeError
                    ):

                        id_dias = None


            # ==================================================
            # FUNCIONÁRIO
            # ==================================================

            cursor.execute("""
                INSERT INTO FUNCIONARIO (
                    ID_DIAS,
                    NOME,
                    DESCRICAO
                )
                VALUES (?, ?, ?)
                RETURNING ID_FUNCIONARIO
            """, (
                id_dias,
                nome,
                descricao
            ))


            id_funcionario = (
                cursor.fetchone()[0]
            )


            # ==================================================
            # SERVIÇOS DO FUNCIONÁRIO
            # ==================================================
            #
            # IMPORTANTE:
            #
            # Aqui NÃO cadastramos serviços.
            #
            # Os serviços já precisam existir em SERVICO.
            #
            # Apenas criamos a relação:
            #
            # FUNCIONARIO
            #       ↓
            # SERVICO_POR_FUNCIONARIO
            #       ↓
            # SERVICO
            #
            # ==================================================

            ids_servicos = (
                vincular_servicos_funcionario(
                    cursor,
                    id_funcionario,
                    id_usuario,
                    i
                )
            )


            funcionarios_criados.append({

                'id_funcionario':
                    id_funcionario,

                'id_dias':
                    id_dias,

                'nome':
                    nome,

                'descricao':
                    descricao,

                'servicos':
                    ids_servicos

            })


        # ==================================================
        # LOGO
        # ==================================================

        logo_url = None


        if 'logo' in request.files:

            arquivo_logo = (
                request.files['logo']
            )


            if (
                arquivo_logo
                and arquivo_logo.filename
            ):

                logo_url = salvar_imagem(
                    arquivo_logo,
                    str(id_usuario)
                )


        # ==================================================
        # FOTOS
        # ==================================================

        fotos = []


        for numero in range(1, 6):

            campo = f'foto{numero}'


            if campo not in request.files:

                continue


            foto = request.files[campo]


            if (
                not foto
                or not foto.filename
            ):

                continue


            nome_base = (
                f'{id_usuario}_{numero}'
            )


            url = salvar_imagem(
                foto,
                nome_base
            )


            if url:

                fotos.append({

                    'numero':
                        numero,

                    'url':
                        url

                })


        # ==================================================
        # COMMIT
        # ==================================================

        con.commit()


        # ==================================================
        # RESPOSTA
        # ==================================================

        return jsonify({

            'mensagem': {

                'informacao':
                    'Personalização criada com sucesso.',

                'tipo':
                    'sucesso'

            },

            'primeira_personalizacao':
                True,

            'id_personalizacao':
                id_personalizacao,

            'personalizacao': {

                'cor_primaria':
                    cor_primaria,

                'cor_secundaria':
                    cor_secundaria,

                'cor_terciaria':
                    cor_terciaria,

                'historia':
                    historia,

                'localizacao':
                    localizacao,

                'num_funcionarios':
                    num_funcionarios

            },

            'funcionarios':
                funcionarios_criados,

            'dias_servico':
                list(
                    ids_dias.values()
                ),

            'logo':
                logo_url,

            'fotos':
                fotos

        }), 201


    except ValueError as erro:

        if con:

            con.rollback()


        return jsonify({

            'mensagem': {

                'informacao':
                    str(erro),

                'tipo':
                    'erro'

            }

        }), 400


    except Exception as erro:

        if con:

            try:

                con.rollback()

            except Exception:

                pass


        print(
            'ERRO AO CRIAR PERSONALIZAÇÃO:',
            erro
        )


        return jsonify({

            'mensagem': {

                'informacao':
                    'Erro ao criar personalização.',

                'tipo':
                    'erro'

            },

            'detalhes':
                str(erro)

        }), 500


    finally:

        if cursor:

            try:

                cursor.close()

            except Exception:

                pass


        if con:

            try:

                con.close()

            except Exception:

                pass


# ==========================================================
# ==========================================================
# EDITAR PERSONALIZAÇÃO
# ==========================================================
# ==========================================================

@app.route(
    '/barbearia/personalizacao',
    methods=['PUT']
)
def editar_personalizacao():

    con = None
    cursor = None

    try:

        # ==================================================
        # AUTENTICAÇÃO
        # ==================================================

        id_usuario = pegar_id_usuario()


        if not id_usuario:

            return jsonify({

                'mensagem': {

                    'informacao':
                        'Usuário não autenticado.',

                    'tipo':
                        'erro'

                }

            }), 401


        # ==================================================
        # CONEXÃO
        # ==================================================

        con = conectar_banco()

        cursor = con.cursor()


        # ==================================================
        # VERIFICAR PERSONALIZAÇÃO
        # ==================================================

        cursor.execute("""
            SELECT ID_PERSONALIZACAO
            FROM PERSONALIZACAO
            WHERE ID_USUARIO = ?
        """, (
            id_usuario,
        ))


        personalizacao = (
            cursor.fetchone()
        )


        if not personalizacao:

            return jsonify({

                'mensagem': {

                    'informacao':
                        'A barbearia ainda não possui personalização. '
                        'Utilize a rota POST para criar.',

                    'tipo':
                        'aviso'

                }

            }), 404


        # ==================================================
        # DADOS
        # ==================================================

        dados = request.form.to_dict()


        cor_primaria = dados.get(
            'cor_primaria'
        )

        cor_secundaria = dados.get(
            'cor_secundaria'
        )

        cor_terciaria = dados.get(
            'cor_terciaria'
        )

        historia = dados.get(
            'historia'
        )

        localizacao = dados.get(
            'localizacao'
        )


        # ==================================================
        # ATUALIZAR PERSONALIZAÇÃO
        # ==================================================

        cursor.execute("""
            UPDATE PERSONALIZACAO
            SET
                COR_PRIMARIA = ?,
                COR_SECUNDARIA = ?,
                COR_TERCIARIA = ?,
                TEXTO = ?,
                LOCALIZACAO = ?
            WHERE ID_USUARIO = ?
        """, (
            cor_primaria,
            cor_secundaria,
            cor_terciaria,
            historia,
            localizacao,
            id_usuario
        ))


        # ==================================================
        # BUSCAR FUNCIONÁRIOS ANTIGOS
        # ==================================================

        cursor.execute("""
            SELECT F.ID_FUNCIONARIO
            FROM FUNCIONARIO F
            INNER JOIN DIAS_DE_SERVICO D
                ON D.ID_DIA = F.ID_DIAS
            WHERE D.ID_USUARIO = ?
        """, (
            id_usuario,
        ))


        funcionarios_antigos = (
            cursor.fetchall()
        )


        # ==================================================
        # EXCLUIR VÍNCULOS DE SERVIÇOS
        # ==================================================

        for funcionario in funcionarios_antigos:

            cursor.execute("""
                DELETE FROM SERVICO_POR_FUNCIONARIO
                WHERE ID_FUNCIONARIO = ?
            """, (
                funcionario[0],
            ))


        # ==================================================
        # EXCLUIR FUNCIONÁRIOS
        # ==================================================

        for funcionario in funcionarios_antigos:

            cursor.execute("""
                DELETE FROM FUNCIONARIO
                WHERE ID_FUNCIONARIO = ?
            """, (
                funcionario[0],
            ))


        # ==================================================
        # EXCLUIR DIAS ANTIGOS
        # ==================================================

        cursor.execute("""
            DELETE FROM DIAS_DE_SERVICO
            WHERE ID_USUARIO = ?
        """, (
            id_usuario,
        ))


        # ==================================================
        # NOVOS DIAS
        # ==================================================

        dias = [

            'segunda',
            'terca',
            'quarta',
            'quinta',
            'sexta',
            'sabado',
            'domingo'

        ]


        ids_dias = {}


        for dia in dias:

            entrada_manha = dados.get(
                f'{dia}_entrada_manha'
            )

            saida_manha = dados.get(
                f'{dia}_saida_manha'
            )

            entrada_tarde = dados.get(
                f'{dia}_entrada_tarde'
            )

            saida_tarde = dados.get(
                f'{dia}_saida_tarde'
            )


            if not any([

                entrada_manha,
                saida_manha,
                entrada_tarde,
                saida_tarde

            ]):

                continue


            cursor.execute("""
                INSERT INTO DIAS_DE_SERVICO (
                    ID_USUARIO,
                    ENTRADA_MANHA,
                    SAIDA_MANHA,
                    ENTRADA_TARDE,
                    SAIDA_TARDE
                )
                VALUES (?, ?, ?, ?, ?)
                RETURNING ID_DIA
            """, (
                id_usuario,
                entrada_manha,
                saida_manha,
                entrada_tarde,
                saida_tarde
            ))


            id_dia = (
                cursor.fetchone()[0]
            )


            ids_dias[dia] = id_dia


        # ==================================================
        # FUNCIONÁRIOS NOVOS
        # ==================================================

        quantidade_funcionarios = (
            dados.get(
                'num_funcionarios'
            )
        )


        try:

            quantidade_funcionarios = int(
                quantidade_funcionarios
                if quantidade_funcionarios is not None
                else 0
            )

        except (
            ValueError,
            TypeError
        ):

            quantidade_funcionarios = 0


        if quantidade_funcionarios < 0:

            quantidade_funcionarios = 0


        for i in range(
            quantidade_funcionarios
        ):

            nome = dados.get(
                f'funcionarios[{i}][nome]'
            )

            descricao = dados.get(
                f'funcionarios[{i}][descricao]'
            )

            dia_funcionario = dados.get(
                f'funcionarios[{i}][dia]'
            )


            if not nome:

                continue


            id_dias = None


            if dia_funcionario:

                id_dias = ids_dias.get(
                    dia_funcionario
                )


            # ------------------------------------------------
            # ID_DIAS DIRETO
            # ------------------------------------------------

            if not id_dias:

                id_dias_form = dados.get(
                    f'funcionarios[{i}][id_dias]'
                )


                if id_dias_form:

                    try:

                        id_dias = int(
                            id_dias_form
                        )

                    except (
                        ValueError,
                        TypeError
                    ):

                        id_dias = None


            # ==================================================
            # FUNCIONÁRIO
            # ==================================================

            cursor.execute("""
                INSERT INTO FUNCIONARIO (
                    ID_DIAS,
                    NOME,
                    DESCRICAO
                )
                VALUES (?, ?, ?)
                RETURNING ID_FUNCIONARIO
            """, (
                id_dias,
                nome,
                descricao
            ))


            id_funcionario = (
                cursor.fetchone()[0]
            )


            # ==================================================
            # SERVIÇOS DO FUNCIONÁRIO
            # ==================================================
            #
            # NÃO CADASTRA SERVIÇOS.
            #
            # SOMENTE VINCULA SERVIÇOS JÁ EXISTENTES.
            #
            # ==================================================

            vincular_servicos_funcionario(
                cursor,
                id_funcionario,
                id_usuario,
                i
            )


        # ==================================================
        # ATUALIZAR QUANTIDADE
        # ==================================================

        cursor.execute("""
            UPDATE PERSONALIZACAO
            SET NUM_FUNCIONARIOS = ?
            WHERE ID_USUARIO = ?
        """, (
            quantidade_funcionarios,
            id_usuario
        ))


        # ==================================================
        # LOGO
        # ==================================================

        logo_url = None


        if 'logo' in request.files:

            arquivo_logo = (
                request.files['logo']
            )


            if (
                arquivo_logo
                and arquivo_logo.filename
            ):

                logo_url = salvar_imagem(
                    arquivo_logo,
                    str(id_usuario)
                )


        # ==================================================
        # FOTOS
        # ==================================================

        fotos = []


        for numero in range(1, 6):

            campo = f'foto{numero}'


            if campo not in request.files:

                continue


            foto = request.files[campo]


            if (
                not foto
                or not foto.filename
            ):

                continue


            url = salvar_imagem(
                foto,
                f'{id_usuario}_{numero}'
            )


            if url:

                fotos.append({

                    'numero':
                        numero,

                    'url':
                        url

                })


        # ==================================================
        # COMMIT
        # ==================================================

        con.commit()


        # ==================================================
        # RESPOSTA
        # ==================================================

        return jsonify({

            'mensagem': {

                'informacao':
                    'Personalização atualizada com sucesso.',

                'tipo':
                    'sucesso'

            },

            'primeira_personalizacao':
                False,

            'logo':
                logo_url,

            'fotos':
                fotos

        }), 200


    except ValueError as erro:

        if con:

            con.rollback()


        return jsonify({

            'mensagem': {

                'informacao':
                    str(erro),

                'tipo':
                    'erro'

            }

        }), 400


    except Exception as erro:

        if con:

            try:

                con.rollback()

            except Exception:

                pass


        print(
            'ERRO AO EDITAR PERSONALIZAÇÃO:',
            erro
        )


        return jsonify({

            'mensagem': {

                'informacao':
                    'Erro ao editar personalização.',

                'tipo':
                    'erro'

            },

            'detalhes':
                str(erro)

        }), 500


    finally:

        if cursor:

            try:

                cursor.close()

            except Exception:

                pass


        if con:

            try:

                con.close()

            except Exception:

                pass


# ==========================================================
# ==========================================================
# BUSCAR PERSONALIZAÇÃO
# ==========================================================
# ==========================================================

@app.route(
    '/barbearia/personalizacao',
    methods=['GET']
)
def buscar_personalizacao():

    con = None
    cursor = None

    try:

        # ==================================================
        # AUTENTICAÇÃO
        # ==================================================

        id_usuario = pegar_id_usuario()


        if not id_usuario:

            return jsonify({

                'mensagem': {

                    'informacao':
                        'Usuário não autenticado.',

                    'tipo':
                        'erro'

                }

            }), 401


        # ==================================================
        # CONEXÃO
        # ==================================================

        con = conectar_banco()

        cursor = con.cursor()


        # ==================================================
        # PERSONALIZAÇÃO
        # ==================================================

        cursor.execute("""
            SELECT
                ID_PERSONALIZACAO,
                ID_USUARIO,
                COR_PRIMARIA,
                COR_SECUNDARIA,
                COR_TERCIARIA,
                TEXTO,
                LOCALIZACAO,
                NUM_FUNCIONARIOS
            FROM PERSONALIZACAO
            WHERE ID_USUARIO = ?
        """, (
            id_usuario,
        ))


        personalizacao = (
            cursor.fetchone()
        )


        # ==================================================
        # NÃO PERSONALIZADO
        # ==================================================

        if not personalizacao:

            return jsonify({

                'personalizado':
                    False,

                'personalizacao':
                    None,

                'funcionarios':
                    [],

                'dias_servico':
                    [],

                'logo':
                    None,

                'fotos':
                    []

            }), 200


        # ==================================================
        # DIAS
        # ==================================================

        cursor.execute("""
            SELECT
                ID_DIA,
                ENTRADA_MANHA,
                SAIDA_MANHA,
                ENTRADA_TARDE,
                SAIDA_TARDE
            FROM DIAS_DE_SERVICO
            WHERE ID_USUARIO = ?
            ORDER BY ID_DIA
        """, (
            id_usuario,
        ))


        dias_db = (
            cursor.fetchall()
        )


        dias = []


        for dia in dias_db:

            dias.append({

                'id_dia':
                    dia[0],

                'entrada_manha':
                    str(dia[1])
                    if dia[1]
                    else None,

                'saida_manha':
                    str(dia[2])
                    if dia[2]
                    else None,

                'entrada_tarde':
                    str(dia[3])
                    if dia[3]
                    else None,

                'saida_tarde':
                    str(dia[4])
                    if dia[4]
                    else None

            })


        # ==================================================
        # FUNCIONÁRIOS
        # ==================================================

        cursor.execute("""
            SELECT
                F.ID_FUNCIONARIO,
                F.ID_DIAS,
                F.NOME,
                F.DESCRICAO
            FROM FUNCIONARIO F
            INNER JOIN DIAS_DE_SERVICO D
                ON D.ID_DIA = F.ID_DIAS
            WHERE D.ID_USUARIO = ?
            ORDER BY F.ID_FUNCIONARIO
        """, (
            id_usuario,
        ))


        funcionarios_db = (
            cursor.fetchall()
        )


        funcionarios = []


        for funcionario in funcionarios_db:

            id_funcionario = (
                funcionario[0]
            )


            # =================================================
            # SERVIÇOS
            # =================================================

            cursor.execute("""
                SELECT
                    SPF.ID_SERVICO
                FROM SERVICO_POR_FUNCIONARIO SPF
                INNER JOIN SERVICO S
                    ON S.ID_SERVICO = SPF.ID_SERVICO
                WHERE
                    SPF.ID_FUNCIONARIO = ?
                    AND S.ID_USUARIO = ?
                ORDER BY SPF.ID_SERVI_FUNCI
            """, (
                id_funcionario,
                id_usuario
            ))


            servicos_db = (
                cursor.fetchall()
            )


            funcionarios.append({

                'id_funcionario':
                    funcionario[0],

                'id_dias':
                    funcionario[1],

                'nome':
                    funcionario[2],

                'descricao':
                    funcionario[3],

                'servicos': [

                    servico[0]

                    for servico in servicos_db

                ]

            })


        # ==================================================
        # LOGO
        # ==================================================

        pasta = (
            criar_pasta_barbearia()
        )


        logo = None


        for extensao in EXTENSOES_PERMITIDAS:

            caminho = os.path.join(
                pasta,
                f'{id_usuario}.{extensao}'
            )


            if os.path.exists(
                caminho
            ):

                logo = (
                    f'/uploads/barbearia/'
                    f'{id_usuario}.{extensao}'
                )

                break


        # ==================================================
        # FOTOS
        # ==================================================

        fotos = []


        for numero in range(1, 6):

            for extensao in EXTENSOES_PERMITIDAS:

                caminho = os.path.join(
                    pasta,
                    f'{id_usuario}_{numero}.{extensao}'
                )


                if os.path.exists(
                    caminho
                ):

                    fotos.append({

                        'numero':
                            numero,

                        'url':
                            f'/uploads/barbearia/'
                            f'{id_usuario}_{numero}.{extensao}'

                    })

                    break


        # ==================================================
        # RESPOSTA
        # ==================================================

        return jsonify({

            'personalizado':
                True,

            'personalizacao': {

                'id_personalizacao':
                    personalizacao[0],

                'id_usuario':
                    personalizacao[1],

                'cor_primaria':
                    personalizacao[2],

                'cor_secundaria':
                    personalizacao[3],

                'cor_terciaria':
                    personalizacao[4],

                'historia':
                    personalizacao[5],

                'localizacao':
                    personalizacao[6],

                'num_funcionarios':
                    personalizacao[7]

            },

            'funcionarios':
                funcionarios,

            'dias_servico':
                dias,

            'logo':
                logo,

            'fotos':
                fotos

        }), 200


    except Exception as erro:

        print(
            'ERRO AO BUSCAR PERSONALIZAÇÃO:',
            erro
        )


        return jsonify({

            'mensagem': {

                'informacao':
                    'Erro ao buscar personalização.',

                'tipo':
                    'erro'

            },

            'detalhes':
                str(erro)

        }), 500


    finally:

        if cursor:

            try:

                cursor.close()

            except Exception:

                pass


        if con:

            try:

                con.close()

            except Exception:

                pass


# ==========================================================
# IMAGENS
# ==========================================================

@app.route(
    '/uploads/barbearia/<path:nome_arquivo>',
    methods=['GET']
)
def imagem_barbearia(nome_arquivo):

    return send_from_directory(

        os.path.join(
            app.config['UPLOAD_FOLDER'],
            'barbearia'
        ),

        nome_arquivo

    )