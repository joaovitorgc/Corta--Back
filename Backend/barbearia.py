import os
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

    extensao = nome.rsplit('.', 1)[-1].lower()

    return extensao in EXTENSOES_PERMITIDAS


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

def salvar_imagem(arquivo, nome_base):

    if not arquivo:
        return None

    if not arquivo.filename:
        return None

    if not extensao_permitida(
        arquivo.filename
    ):
        raise ValueError(
            'Formato de imagem não permitido.'
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

        excluir_arquivo(antigo)

    # ------------------------------------------------------
    # SALVAR NOVA
    # ------------------------------------------------------

    nome_arquivo = (
        f'{nome_base}.{extensao}'
    )

    caminho = os.path.join(
        pasta,
        nome_arquivo
    )

    arquivo.save(caminho)

    return (
        f'/uploads/barbearia/'
        f'{nome_arquivo}'
    )


# ==========================================================
# BUSCAR ID DO USUÁRIO
# ==========================================================

def pegar_id_usuario():

    usuario = obter_usuario_logado()

    if not usuario:
        return None

    return usuario.get('id_usuario')


# ==========================================================
# ==========================================================
# PRIMEIRA PERSONALIZAÇÃO
# ==========================================================
# ==========================================================

@app.route('/barbearia/personalizacao', methods=['POST'])
def personalizacao_barbearia():

    con = None
    cursor = None

    try:

        # ==========================================================
        # AUTENTICAÇÃO
        # ==========================================================

        id_usuario = pegar_id_usuario()

        if not id_usuario:
            return jsonify({
                'mensagem': {
                    'informacao': 'Usuário não autenticado.',
                    'tipo': 'erro'
                }
            }), 401


        # ==========================================================
        # CONEXÃO COM BANCO
        # ==========================================================

        con = conectar_banco()
        cursor = con.cursor()


        # ==========================================================
        # VERIFICAR SE JÁ EXISTE PERSONALIZAÇÃO
        # ==========================================================

        cursor.execute("""
            SELECT ID_PERSONALIZACAO
            FROM PERSONALIZACAO
            WHERE ID_USUARIO = ?
        """, (id_usuario,))

        existente = cursor.fetchone()

        if existente:
            return jsonify({
                'mensagem': {
                    'informacao':
                        'A barbearia já possui uma personalização.',
                    'tipo': 'aviso'
                },
                'id_personalizacao': existente[0]
            }), 409


        # ==========================================================
        # DADOS VINDOS DO REQUEST
        # ==========================================================

        cor_primaria = request.form.get('cor_primaria')
        cor_secundaria = request.form.get('cor_secundaria')
        cor_terciaria = request.form.get('cor_terciaria')

        historia = request.form.get('historia')
        localizacao = request.form.get('localizacao')

        num_funcionarios = request.form.get(
            'num_funcionarios',
            '0'
        )

        try:
            num_funcionarios = int(num_funcionarios)
        except (ValueError, TypeError):
            num_funcionarios = 0


        # ==========================================================
        # PERSONALIZAÇÃO
        # ==========================================================

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

        id_personalizacao = cursor.fetchone()[0]


        # ==========================================================
        # FUNCIONÁRIOS
        # ==========================================================

        funcionarios_criados = []

        for i in range(num_funcionarios):

            nome = request.form.get(
                f'funcionarios[{i}][nome]'
            )

            descricao = request.form.get(
                f'funcionarios[{i}][descricao]'
            )

            horario = request.form.get(
                f'funcionarios[{i}][horario]'
            )

            servicos = request.form.get(
                f'funcionarios[{i}][servicos]',
                ''
            )


            # Se não informou nome, ignora
            if not nome:
                continue


            cursor.execute("""
                INSERT INTO FUNCIONARIO (
                    ID_USUARIO,
                    NOME,
                    DESCRICAO,
                    HORARIO
                )
                VALUES (?, ?, ?, ?)
                RETURNING ID_FUNCIONARIO
            """, (
                id_usuario,
                nome,
                descricao,
                horario
            ))

            id_funcionario = cursor.fetchone()[0]


            # ======================================================
            # SERVIÇOS DO FUNCIONÁRIO
            # ======================================================

            if servicos:

                lista_servicos = servicos.split(',')

                for servico in lista_servicos:

                    try:
                        id_servico = int(servico.strip())
                    except (ValueError, TypeError):
                        continue


                    cursor.execute("""
                        SELECT ID_SERVICO
                        FROM SERVICO
                        WHERE ID_SERVICO = ?
                    """, (id_servico,))

                    existe_servico = cursor.fetchone()

                    if not existe_servico:
                        continue


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


            funcionarios_criados.append({
                'id_funcionario': id_funcionario,
                'nome': nome
            })


        # ==========================================================
        # DIAS DE SERVIÇO
        # ==========================================================

        dias = [
            'segunda',
            'terca',
            'quarta',
            'quinta',
            'sexta',
            'sabado',
            'domingo'
        ]

        dias_criados = []

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


            # Nenhum horário informado
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
                    DIA_SEMANA,
                    ENTRADA_MANHA,
                    SAIDA_MANHA,
                    ENTRADA_TARDE,
                    SAIDA_TARDE
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                id_usuario,
                dia,
                entrada_manha,
                saida_manha,
                entrada_tarde,
                saida_tarde
            ))


            dias_criados.append(dia)


        # ==========================================================
        # LOGO
        # ==========================================================

        logo_url = None

        if 'logo' in request.files:

            arquivo_logo = request.files['logo']

            if arquivo_logo and arquivo_logo.filename:

                logo_url = salvar_imagem(
                    arquivo_logo,
                    str(id_usuario)
                )


        # ==========================================================
        # FOTOS DA BARBEARIA
        # MÁXIMO DE 5
        # ==========================================================

        fotos = []

        for numero in range(1, 6):

            nome_campo = f'foto{numero}'

            if nome_campo not in request.files:
                continue


            arquivo = request.files[nome_campo]

            if not arquivo or not arquivo.filename:
                continue


            url = salvar_imagem(
                arquivo,
                f'{id_usuario}_foto_{numero}'
            )


            if url:

                fotos.append({
                    'numero': numero,
                    'url': url
                })


        # ==========================================================
        # COMMIT
        # ==========================================================

        con.commit()


        # ==========================================================
        # RESPOSTA
        # ==========================================================

        return jsonify({

            'mensagem': {
                'informacao':
                    'Personalização criada com sucesso.',
                'tipo': 'sucesso'
            },

            'primeira_personalizacao': True,

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
                dias_criados,

            'logo':
                logo_url,

            'fotos':
                fotos

        }), 201


    # ==========================================================
    # ERRO DE VALIDAÇÃO
    # ==========================================================

    except ValueError as erro:

        if con:
            con.rollback()

        return jsonify({
            'mensagem': {
                'informacao': str(erro),
                'tipo': 'erro'
            }
        }), 400


    # ==========================================================
    # ERRO GERAL
    # ==========================================================

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
                'tipo': 'erro'
            },

            'detalhes':
                str(erro)

        }), 500


    # ==========================================================
    # FECHAR CONEXÃO
    # ==========================================================

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
# EDITAR PERSONALIZAÇÃO / PERFIL
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
                    'tipo': 'erro'
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

        personalizacao = cursor.fetchone()


        if not personalizacao:

            return jsonify({
                'mensagem': {
                    'informacao':
                        'A barbearia ainda não possui personalização. '
                        'Utilize a rota POST para criar.',
                    'tipo': 'aviso'
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
        # FUNCIONÁRIOS
        # ==================================================

        quantidade_funcionarios = dados.get(
            'num_funcionarios'
        )


        if quantidade_funcionarios is not None:

            try:

                quantidade_funcionarios = int(
                    quantidade_funcionarios
                )

            except:

                quantidade_funcionarios = 0


            # ----------------------------------------------
            # FUNCIONÁRIOS ANTIGOS
            # ----------------------------------------------

            cursor.execute("""
                SELECT ID_FUNCIONARIO
                FROM FUNCIONARIO
                WHERE ID_USUARIO = ?
            """, (
                id_usuario,
            ))

            funcionarios_antigos = (
                cursor.fetchall()
            )


            # ----------------------------------------------
            # SERVIÇOS
            # ----------------------------------------------

            for funcionario in funcionarios_antigos:

                cursor.execute("""
                    DELETE FROM
                    SERVICO_POR_FUNCIONARIO
                    WHERE ID_FUNCIONARIO = ?
                """, (
                    funcionario[0],
                ))


            # ----------------------------------------------
            # FUNCIONÁRIOS
            # ----------------------------------------------

            cursor.execute("""
                DELETE FROM FUNCIONARIO
                WHERE ID_USUARIO = ?
            """, (
                id_usuario,
            ))


            # ----------------------------------------------
            # NOVOS FUNCIONÁRIOS
            # ----------------------------------------------

            for i in range(
                quantidade_funcionarios
            ):

                nome = dados.get(
                    f'funcionarios[{i}][nome]'
                )

                descricao = dados.get(
                    f'funcionarios[{i}][descricao]'
                )

                horario = dados.get(
                    f'funcionarios[{i}][horario]'
                )


                if not nome:

                    continue


                cursor.execute("""
                    INSERT INTO FUNCIONARIO (
                        ID_USUARIO,
                        NOME,
                        DESCRICAO,
                        HORARIO
                    )
                    VALUES (?, ?, ?, ?)
                    RETURNING ID_FUNCIONARIO
                """, (
                    id_usuario,
                    nome,
                    descricao,
                    horario
                ))


                id_funcionario = (
                    cursor.fetchone()[0]
                )


                servicos = dados.get(
                    f'funcionarios[{i}][servicos]',
                    ''
                )


                if servicos:

                    for id_servico in servicos.split(','):

                        try:

                            id_servico = int(
                                id_servico.strip()
                            )

                        except:

                            continue


                        cursor.execute("""
                            SELECT ID_SERVICO
                            FROM SERVICO
                            WHERE ID_SERVICO = ?
                        """, (
                            id_servico,
                        ))


                        if cursor.fetchone():

                            cursor.execute("""
                                INSERT INTO
                                SERVICO_POR_FUNCIONARIO (
                                    ID_FUNCIONARIO,
                                    ID_SERVICO
                                )
                                VALUES (?, ?)
                            """, (
                                id_funcionario,
                                id_servico
                            ))


            # ----------------------------------------------
            # ATUALIZAR QUANTIDADE
            # ----------------------------------------------

            cursor.execute("""
                UPDATE PERSONALIZACAO
                SET NUM_FUNCIONARIOS = ?
                WHERE ID_USUARIO = ?
            """, (
                quantidade_funcionarios,
                id_usuario
            ))


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


            # ----------------------------------------------
            # VERIFICAR DIA
            # ----------------------------------------------

            cursor.execute("""
                SELECT ID_DIA
                FROM DIAS_DE_SERVICO
                WHERE ID_USUARIO = ?
                AND DIA_SEMANA = ?
            """, (
                id_usuario,
                dia
            ))


            dia_existente = (
                cursor.fetchone()
            )


            # ----------------------------------------------
            # SE NÃO TEM HORÁRIO
            # ----------------------------------------------

            if not any([
                entrada_manha,
                saida_manha,
                entrada_tarde,
                saida_tarde
            ]):

                if dia_existente:

                    cursor.execute("""
                        DELETE FROM DIAS_DE_SERVICO
                        WHERE ID_DIA = ?
                    """, (
                        dia_existente[0],
                    ))

                continue


            # ----------------------------------------------
            # ATUALIZAR
            # ----------------------------------------------

            if dia_existente:

                cursor.execute("""
                    UPDATE DIAS_DE_SERVICO
                    SET
                        ENTRADA_MANHA = ?,
                        SAIDA_MANHA = ?,
                        ENTRADA_TARDE = ?,
                        SAIDA_TARDE = ?
                    WHERE ID_DIA = ?
                """, (
                    entrada_manha,
                    saida_manha,
                    entrada_tarde,
                    saida_tarde,
                    dia_existente[0]
                ))

            # ----------------------------------------------
            # CRIAR
            # ----------------------------------------------

            else:

                cursor.execute("""
                    INSERT INTO DIAS_DE_SERVICO (
                        ID_USUARIO,
                        DIA_SEMANA,
                        ENTRADA_MANHA,
                        SAIDA_MANHA,
                        ENTRADA_TARDE,
                        SAIDA_TARDE
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    id_usuario,
                    dia,
                    entrada_manha,
                    saida_manha,
                    entrada_tarde,
                    saida_tarde
                ))


        # ==================================================
        # LOGO
        # ==================================================

        logo_url = None


        if 'logo' in request.files:

            logo_url = salvar_imagem(
                request.files['logo'],
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


            url = salvar_imagem(
                foto,
                f'{id_usuario}_{numero}'
            )


            if url:

                fotos.append({
                    'numero': numero,
                    'url': url
                })


        # ==================================================
        # COMMIT
        # ==================================================

        con.commit()


        return jsonify({

            'mensagem': {
                'informacao':
                    'Personalização atualizada com sucesso.',
                'tipo': 'sucesso'
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
                'informacao': str(erro),
                'tipo': 'erro'
            }
        }), 400


    except Exception as erro:

        if con:

            try:
                con.rollback()
            except:
                pass


        print(
            'ERRO AO EDITAR PERSONALIZAÇÃO:',
            erro
        )


        return jsonify({

            'mensagem': {
                'informacao':
                    'Erro ao editar personalização.',
                'tipo': 'erro'
            },

            'detalhes':
                str(erro)

        }), 500


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


# ==========================================================
# BUSCAR PERSONALIZAÇÃO
# ==========================================================

@app.route(
    '/barbearia/personalizacao',
    methods=['GET']
)
def buscar_personalizacao():

    con = None
    cursor = None

    try:

        id_usuario = pegar_id_usuario()

        if not id_usuario:

            return jsonify({
                'mensagem': {
                    'informacao':
                        'Usuário não autenticado.',
                    'tipo': 'erro'
                }
            }), 401


        con = conectar_banco()
        cursor = con.cursor()


        # ==================================================
        # PERSONALIZAÇÃO
        # ==================================================

        cursor.execute("""
            SELECT
                ID_PERSONALIZACAO,
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
                    None

            }), 200


        # ==================================================
        # FUNCIONÁRIOS
        # ==================================================

        cursor.execute("""
            SELECT
                ID_FUNCIONARIO,
                NOME,
                DESCRICAO,
                HORARIO
            FROM FUNCIONARIO
            WHERE ID_USUARIO = ?
            ORDER BY ID_FUNCIONARIO
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


            cursor.execute("""
                SELECT ID_SERVICO
                FROM SERVICO_POR_FUNCIONARIO
                WHERE ID_FUNCIONARIO = ?
            """, (
                id_funcionario,
            ))


            servicos_db = (
                cursor.fetchall()
            )


            funcionarios.append({

                'id_funcionario':
                    id_funcionario,

                'nome':
                    funcionario[1],

                'descricao':
                    funcionario[2],

                'horario':
                    funcionario[3],

                'servicos': [
                    servico[0]
                    for servico in servicos_db
                ]

            })


        # ==================================================
        # DIAS
        # ==================================================

        cursor.execute("""
            SELECT
                ID_DIA,
                DIA_SEMANA,
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


        dias_db = cursor.fetchall()


        dias = []


        for dia in dias_db:

            dias.append({

                'id_dia':
                    dia[0],

                'dia_semana':
                    dia[1],

                'entrada_manha':
                    str(dia[2])
                    if dia[2]
                    else None,

                'saida_manha':
                    str(dia[3])
                    if dia[3]
                    else None,

                'entrada_tarde':
                    str(dia[4])
                    if dia[4]
                    else None,

                'saida_tarde':
                    str(dia[5])
                    if dia[5]
                    else None

            })


        # ==================================================
        # IMAGENS
        # ==================================================

        pasta = criar_pasta_barbearia()


        logo = None


        for extensao in EXTENSOES_PERMITIDAS:

            caminho = os.path.join(
                pasta,
                f'{id_usuario}.{extensao}'
            )


            if os.path.exists(caminho):

                logo = (
                    f'/uploads/barbearia/'
                    f'{id_usuario}.{extensao}'
                )

                break


        fotos = []


        for numero in range(1, 6):

            for extensao in EXTENSOES_PERMITIDAS:

                caminho = os.path.join(
                    pasta,
                    f'{id_usuario}_{numero}.{extensao}'
                )


                if os.path.exists(caminho):

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
                    id_usuario,

                'cor_primaria':
                    personalizacao[1],

                'cor_secundaria':
                    personalizacao[2],

                'cor_terciaria':
                    personalizacao[3],

                'historia':
                    personalizacao[4],

                'localizacao':
                    personalizacao[5],

                'num_funcionarios':
                    personalizacao[6]

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
                'tipo': 'erro'
            },

            'detalhes':
                str(erro)

        }), 500


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


# ==========================================================
# IMAGENS DA BARBEARIA
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