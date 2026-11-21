-- Conflitos da carga da CVM (F3-3b-fix, BUG-3-26, DD-57): chave já gravada que um arquivo traz
-- com dados diferentes. A carga mantém a linha gravada (só inserção) e registra aqui cada caso,
-- com os dois lados e a proveniência do arquivo que o trouxe, para o leitor ponto-no-tempo
-- deixar o documento fora com o motivo. `documento` é DFP, ITR ou FCA; `versao` é a da chave.
CREATE TABLE conflitos_carga (
    tabela TEXT NOT NULL,
    cnpj TEXT NOT NULL,
    documento TEXT NOT NULL CHECK (documento IN ('DFP', 'ITR', 'FCA')),
    dt_refer TEXT NOT NULL,
    versao INTEGER NOT NULL,
    chave_json TEXT NOT NULL,
    gravado_json TEXT NOT NULL,
    arquivo_json TEXT NOT NULL,
    fonte TEXT NOT NULL,
    coleta TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    PRIMARY KEY (hash_sha256, tabela, chave_json, arquivo_json)
);

CREATE INDEX conflitos_carga_documento ON conflitos_carga (documento, cnpj, dt_refer);

CREATE TRIGGER conflitos_carga_sem_update BEFORE UPDATE ON conflitos_carga
BEGIN SELECT RAISE(ABORT, 'conflitos_carga é só de inserção'); END;
CREATE TRIGGER conflitos_carga_sem_delete BEFORE DELETE ON conflitos_carga
BEGIN SELECT RAISE(ABORT, 'conflitos_carga é só de inserção'); END;
