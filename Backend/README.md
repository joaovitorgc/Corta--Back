# Cortaê - Backend

Ajustes desta versão:
- correção do nome do cookie JWT (`access_token`) usado pelo login, edição e logout;
- compatibilidade temporária com o nome antigo `acess_token` ao decodificar o token;
- CORS para `localhost:5173`, `127.0.0.1:5173` e o IP da rede usado anteriormente;
- normalização/validação de nome, e-mail e telefone no cadastro e na edição;
- troca de senha pelo endpoint `PUT /editar-usuario/<id_usuario>` continua usando o mesmo fluxo de hash e confirmação de senha;
- recuperação de senha em 3 etapas mantém a validação do código antes de salvar a nova senha.
