-- ATUALIZAÇÃO DO BANCO FIREBIRD
-- Execute uma única vez no BANCO.FDB antes de iniciar o Python atualizado.
-- As contas atuais e os novos cadastros começam com zero tentativas e sem bloqueio.

ALTER TABLE USUARIO ADD TENTATIVAS_LOGIN INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE USUARIO ADD BLOQUEADO_LOGIN SMALLINT DEFAULT 0 NOT NULL;
COMMIT;

-- CONSULTAR AS TENTATIVAS E O BLOQUEIO DE CADA USUÁRIO
SELECT ID_USUARIO, NOME, EMAIL, TENTATIVAS_LOGIN, BLOQUEADO_LOGIN
FROM USUARIO;

-- DESBLOQUEAR UMA CONTA
-- Execute separadamente, retirando os comentários e trocando 123 pelo ID correto.
-- O WHERE é obrigatório para alterar apenas o usuário escolhido.
-- UPDATE USUARIO
-- SET TENTATIVAS_LOGIN = 0, BLOQUEADO_LOGIN = 0
-- WHERE ID_USUARIO = 123;
-- COMMIT;
