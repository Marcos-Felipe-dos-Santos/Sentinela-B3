-- Demonstrações ponto-no-tempo (F3-3a, PLANO §5): contas da DFP/ITR por versão, a data de
-- entrega de cada documento e versão, e a composição do capital por documento.
-- Só inserção: uma versão nova entra como linha nova; nada é sobrescrito nem apagado
-- (a leitura numa data D escolhe a última versão entregue até D, no F3-3c).

-- Data de entrega de cada documento e versão (índice dfp/itr_cia_aberta_AAAA.csv). FCA e
-- Informe de FII terão tabelas próprias no F3-3b (DD-42): aqui só DFP e ITR.
CREATE TABLE entregas (
    cnpj TEXT NOT NULL,
    documento TEXT NOT NULL CHECK (documento IN ('DFP', 'ITR')),
    dt_refer TEXT NOT NULL,
    versao INTEGER NOT NULL,
    cd_cvm TEXT,
    denominacao TEXT,
    categoria TEXT,
    id_documento TEXT,
    dt_receb TEXT NOT NULL,
    -- 1 quando o arquivo aberto traz os números desta versão (a última); 0 quando só o
    -- índice a registra (L1: as demonstrações guardam só a última versão, DD-34)
    valores_na_fonte INTEGER NOT NULL CHECK (valores_na_fonte IN (0, 1)),
    fonte TEXT NOT NULL,
    coleta TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    PRIMARY KEY (cnpj, documento, dt_refer, versao)
);

-- Contas da DFP/ITR com a escala do documento. A chave do PLANO §5 (cnpj, documento,
-- dt_refer, versao, conta) ganha o que separa as linhas da mesma conta nos arquivos da
-- CVM (DD-42): a demonstração (BPA_con, DRE_ind...), a ordem do exercício (ÚLTIMO,
-- PENÚLTIMO), o período (no ITR do 2º e do 3º trimestre, a DRE traz o trimestre isolado e
-- o acumulado com a mesma ordem, só com DT_INI_EXERC diferente) e a coluna da DMPL
-- (COLUNA_DF). Sem início de exercício (balanços) ou sem coluna, o valor é '' (vazio).
CREATE TABLE demonstracoes (
    cnpj TEXT NOT NULL,
    documento TEXT NOT NULL CHECK (documento IN ('DFP', 'ITR')),
    dt_refer TEXT NOT NULL,
    versao INTEGER NOT NULL,
    demonstracao TEXT NOT NULL,
    ordem_exerc TEXT NOT NULL CHECK (ordem_exerc IN ('ÚLTIMO', 'PENÚLTIMO')),
    dt_ini_exerc TEXT NOT NULL DEFAULT '',
    dt_fim_exerc TEXT NOT NULL,
    coluna_df TEXT NOT NULL DEFAULT '',
    conta TEXT NOT NULL,
    descricao TEXT,
    valor REAL,
    escala TEXT NOT NULL CHECK (escala IN ('MIL', 'UNIDADE')),
    moeda TEXT,
    conta_fixa TEXT,
    fonte TEXT NOT NULL,
    coleta TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    PRIMARY KEY (
        cnpj, documento, dt_refer, versao, demonstracao, ordem_exerc,
        dt_ini_exerc, dt_fim_exerc, coluna_df, conta
    )
);

-- Ações ON, PN e em tesouraria por documento (composição do capital). As quantidades
-- ficam como o documento declara: a escala (mil ou unidade) não vem no arquivo e é inferida
-- na leitura pelo LPA do mesmo documento (armadilha 10, F3-3c), sem valor derivado gravado.
-- O documento entra na chave (DFP e ITR com a mesma data, DD-42).
CREATE TABLE composicao_capital (
    cnpj TEXT NOT NULL,
    documento TEXT NOT NULL CHECK (documento IN ('DFP', 'ITR')),
    dt_refer TEXT NOT NULL,
    versao INTEGER NOT NULL,
    acoes_ordinarias REAL,
    acoes_preferenciais REAL,
    acoes_total REAL,
    tesouraria_ordinarias REAL,
    tesouraria_preferenciais REAL,
    tesouraria_total REAL,
    fonte TEXT NOT NULL,
    coleta TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    PRIMARY KEY (cnpj, documento, dt_refer, versao)
);

CREATE INDEX idx_entregas_receb ON entregas (cnpj, documento, dt_refer, dt_receb);

CREATE TRIGGER entregas_sem_update BEFORE UPDATE ON entregas
BEGIN SELECT RAISE(ABORT, 'entregas é só de inserção'); END;
CREATE TRIGGER entregas_sem_delete BEFORE DELETE ON entregas
BEGIN SELECT RAISE(ABORT, 'entregas é só de inserção'); END;
CREATE TRIGGER entregas_sem_sobrescrita BEFORE INSERT ON entregas
WHEN EXISTS (
    SELECT 1 FROM entregas WHERE cnpj = NEW.cnpj AND documento = NEW.documento
    AND dt_refer = NEW.dt_refer AND versao = NEW.versao
)
BEGIN SELECT RAISE(ABORT, 'entregas é só de inserção'); END;

CREATE TRIGGER demonstracoes_sem_update BEFORE UPDATE ON demonstracoes
BEGIN SELECT RAISE(ABORT, 'demonstracoes é só de inserção'); END;
CREATE TRIGGER demonstracoes_sem_delete BEFORE DELETE ON demonstracoes
BEGIN SELECT RAISE(ABORT, 'demonstracoes é só de inserção'); END;
CREATE TRIGGER demonstracoes_sem_sobrescrita BEFORE INSERT ON demonstracoes
WHEN EXISTS (
    SELECT 1 FROM demonstracoes WHERE cnpj = NEW.cnpj AND documento = NEW.documento
    AND dt_refer = NEW.dt_refer AND versao = NEW.versao AND demonstracao = NEW.demonstracao
    AND ordem_exerc = NEW.ordem_exerc AND dt_ini_exerc = NEW.dt_ini_exerc
    AND dt_fim_exerc = NEW.dt_fim_exerc AND coluna_df = NEW.coluna_df AND conta = NEW.conta
)
BEGIN SELECT RAISE(ABORT, 'demonstracoes é só de inserção'); END;

CREATE TRIGGER composicao_capital_sem_update BEFORE UPDATE ON composicao_capital
BEGIN SELECT RAISE(ABORT, 'composicao_capital é só de inserção'); END;
CREATE TRIGGER composicao_capital_sem_delete BEFORE DELETE ON composicao_capital
BEGIN SELECT RAISE(ABORT, 'composicao_capital é só de inserção'); END;
CREATE TRIGGER composicao_capital_sem_sobrescrita BEFORE INSERT ON composicao_capital
WHEN EXISTS (
    SELECT 1 FROM composicao_capital WHERE cnpj = NEW.cnpj AND documento = NEW.documento
    AND dt_refer = NEW.dt_refer AND versao = NEW.versao
)
BEGIN SELECT RAISE(ABORT, 'composicao_capital é só de inserção'); END;
