"""Documentação OpenAPI mantida junto ao backend Flask.

Flask não cria documentação automática como o FastAPI. Este módulo fornece o
mesmo ponto de entrada de uso (`/docs`) e publica o contrato em `/openapi.json`
sem acrescentar uma dependência de produção apenas para a interface.
"""

from flask import jsonify, render_template_string

from main import app


# Respostas padronizadas tornam a especificação curta e deixam claro que toda
# mensagem de falha usa `mensagem.informacao` ou `erro` no corpo JSON.
RESPOSTAS_PADRAO = {
    '200': {'description': 'Operação concluída.'},
    '400': {'description': 'Dados inválidos ou incompletos.'},
    '401': {'description': 'Sessão ausente, expirada ou inválida.'},
    '403': {'description': 'Perfil sem permissão.'},
    '500': {'description': 'Erro interno do servidor.'},
}


def operacao(resumo, descricao, corpo=None, autenticada=True):
    """Evita repetir o bloco de autenticação em cada operação do contrato."""
    resultado = {
        'summary': resumo,
        'description': descricao,
        'responses': RESPOSTAS_PADRAO,
    }
    if corpo:
        resultado['requestBody'] = {
            'required': True,
            'content': {'application/json': {'schema': corpo}},
        }
    if autenticada:
        resultado['security'] = [{'cookieAuth': []}]
    return resultado


USUARIO = {
    'type': 'object',
    'required': ['nome', 'email', 'telefone', 'senha', 'confirmarSenha', 'tipo'],
    'properties': {
        'nome': {'type': 'string', 'example': 'Maria Silva'},
        'email': {'type': 'string', 'format': 'email', 'example': 'maria@email.com'},
        'telefone': {'type': 'string', 'example': '11999999999'},
        'senha': {'type': 'string', 'format': 'password'},
        'confirmarSenha': {'type': 'string', 'format': 'password'},
        'tipo': {'type': 'integer', 'enum': [0, 1, 2], 'description': '0 ADM, 1 cliente, 2 barbearia.'},
    },
}


# Campos da personalização são multipart porque também incluem logo e fotos.
# A tela /docs informa esse detalhe para que o teste manual não envie JSON.
PERSONALIZACAO = {
    'type': 'object',
    'properties': {
        'cor_primaria': {'type': 'string', 'example': '#121212'},
        'cor_secundaria': {'type': 'string', 'example': '#D57C15'},
        'cor_terciaria': {'type': 'string', 'example': '#FFFFFF'},
        'cor_texto_primario': {'type': 'string', 'example': '#FFFFFF'},
        'cor_texto_secundario': {'type': 'string', 'example': '#333333'},
        'texto': {'type': 'string'},
        'localizacao': {'type': 'string'},
        'contato_telefone': {'type': 'string'},
        'contato_email': {'type': 'string', 'format': 'email'},
        'instagram': {'type': 'string'},
        'logo': {'type': 'string', 'format': 'binary'},
        'fotos': {'type': 'array', 'items': {'type': 'string', 'format': 'binary'}},
        'funcionarios[0][nome]': {'type': 'string'},
        'funcionarios[0][dias]': {'type': 'string', 'example': 'segunda,terca'},
        'funcionarios[0][servicos]': {'type': 'string', 'example': '1,2'},
    },
}


OPENAPI = {
    'openapi': '3.0.3',
    'info': {
        'title': 'Cortaê API',
        'version': '1.0.0',
        'description': 'API do sistema Cortaê. O login grava o JWT no cookie `access_token`.',
    },
    'servers': [{'url': 'http://localhost:5000', 'description': 'Servidor local'}],
    'paths': {
        '/cadastro': {'post': operacao('Cadastrar usuário', 'Cria usuário e envia código de confirmação por e-mail.', USUARIO, False)},
        '/verificar-codigo': {'post': operacao('Confirmar e-mail', 'Ativa o cadastro usando o código de seis dígitos.', {
            'type': 'object', 'required': ['email', 'codigo'], 'properties': {'email': {'type': 'string'}, 'codigo': {'type': 'string', 'example': '123456'}}
        }, False)},
        '/login': {'post': operacao('Entrar', 'Autentica e grava o cookie de sessão.', {
            'type': 'object', 'required': ['email', 'senha'], 'properties': {'email': {'type': 'string'}, 'senha': {'type': 'string', 'format': 'password'}}
        }, False)},
        '/logout': {'post': operacao('Sair', 'Remove o cookie de sessão.')},
        '/recuperar-senha': {'post': operacao('Recuperar senha', 'Fluxo de envio, validação e troca de senha; consulte os campos exigidos pela etapa enviada.')},
        '/listar_usuarios': {'get': operacao('Listar usuários', 'Exclusivo para ADM. Aceita o filtro opcional `tipo` (0, 1 ou 2).')},
        '/usuarios/{id_usuario}/status': {'put': operacao('Ativar/desativar usuário', 'Exclusivo para ADM. Ao desativar, `motivo` é obrigatório e é enviado por e-mail.', {
            'type': 'object', 'required': ['ativo'], 'properties': {'ativo': {'type': 'boolean'}, 'motivo': {'type': 'string'}}
        })},
        '/dados-perfil/{id_usuario}': {'get': operacao('Buscar perfil', 'Busca os dados de um perfil autorizado.')},
        '/editar-usuario/{id_usuario}': {'put': operacao('Editar perfil', 'Atualiza os campos do usuário autenticado ou do usuário administrado.', USUARIO)},
        '/excluir-foto-perfil/{id_usuario}': {'delete': operacao('Excluir foto de perfil', 'Remove a foto de perfil do usuário.')},
        '/barbearias-disponiveis': {'get': operacao('Listar barbearias', 'Lista as barbearias cadastradas e a indicação de personalização.')},
        '/barbearia/servicos': {
            'get': operacao('Listar serviços', 'Lista os serviços da barbearia autenticada.'),
            'post': operacao('Criar serviço', 'Cria um serviço para posterior vínculo a funcionários.', {
                'type': 'object', 'required': ['nome'], 'properties': {'nome': {'type': 'string'}, 'preco': {'type': 'number'}, 'duracao': {'type': 'integer'}}
            }),
        },
        '/barbearia/servicos/{id_servico}': {'delete': operacao('Excluir serviço', 'Exclui um serviço pertencente à barbearia autenticada.')},
        '/barbearia/personalizacao': {
            'get': operacao('Buscar personalização', 'Retorna cores, contatos, fotos, serviços, funcionários e dias. ADM pode informar `id_usuario` na query.'),
            'post': {
                **operacao('Criar personalização', 'Primeira personalização da barbearia. Envie `multipart/form-data`.', None),
                'requestBody': {'required': True, 'content': {'multipart/form-data': {'schema': PERSONALIZACAO}}},
            },
            'put': {
                **operacao('Editar personalização', 'Atualiza a personalização existente. Envie `multipart/form-data`.', None),
                'requestBody': {'required': True, 'content': {'multipart/form-data': {'schema': PERSONALIZACAO}}},
            },
        },
        '/fotos-perfil/{nome_arquivo}': {'get': operacao('Exibir foto de perfil', 'Entrega um arquivo de foto.', autenticada=False)},
        '/uploads/perfil/{nome_arquivo}': {'get': operacao('Exibir upload de perfil', 'Entrega um arquivo de perfil.', autenticada=False)},
        '/uploads/barbearia/{nome_arquivo}': {'get': operacao('Exibir imagem da barbearia', 'Entrega logo ou foto da barbearia.', autenticada=False)},
    },
    'components': {'securitySchemes': {'cookieAuth': {'type': 'apiKey', 'in': 'cookie', 'name': 'access_token'}}},
}


@app.route('/openapi.json', methods=['GET'])
def openapi_json():
    """Contrato consumível por Swagger, Postman e outras ferramentas."""
    return jsonify(OPENAPI)


@app.route('/docs', methods=['GET'])
def documentacao_api():
    """Interface interativa equivalente ao `/docs` oferecido pelo FastAPI."""
    return render_template_string('''
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cortaê API Docs</title><link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css"></head>
<body><div id="swagger-ui"></div><script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script><script>SwaggerUIBundle({url:'/openapi.json',dom_id:'#swagger-ui',persistAuthorization:true})</script></body></html>
''')
