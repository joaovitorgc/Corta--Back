# Cortaê - Backend

## Documentação interativa

Com o servidor em execução, abra [http://localhost:5000/docs](http://localhost:5000/docs). A página usa Swagger UI e funciona como o `/docs` do FastAPI: mostra métodos, corpos de requisição, respostas e permite testar as rotas. O contrato OpenAPI bruto está em [http://localhost:5000/openapi.json](http://localhost:5000/openapi.json), útil para importar no Postman.

## Autenticação

`POST /login` salva o JWT no cookie HTTP `access_token`. Rotas marcadas com cadeado na documentação exigem esse cookie. Os perfis são: `0` administrador, `1` cliente e `2` barbearia.

## Rotas por área

| Área | Rotas |
| --- | --- |
| Acesso | `POST /cadastro`, `POST /verificar-codigo`, `POST /login`, `POST /logout`, `POST /recuperar-senha` |
| Usuários | `GET /listar_usuarios`, `GET /dados-perfil/{id}`, `PUT /editar-usuario/{id}`, `PUT /usuarios/{id}/status`, `DELETE /excluir-foto-perfil/{id}` |
| Barbearias | `GET /barbearias-disponiveis`, `GET/POST/DELETE /barbearia/servicos`, `GET/POST/PUT /barbearia/personalizacao` |
| Arquivos | `GET /fotos-perfil/{arquivo}`, `GET /uploads/perfil/{arquivo}`, `GET /uploads/barbearia/{arquivo}` |

## E-mails

`funcoes.enviando_email` usa um único template HTML. Códigos de confirmação de seis dígitos recebem uma caixa destacada; comunicados administrativos e futuros avisos de barbearia recebem apenas texto formatado. A função `enviar_aviso_email` é o ponto de reutilização para esses comunicados.

## Execução local

```bash
pip install -r requirements.txt
python main.py
```
