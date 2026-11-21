-- Carga dos arquivos abertos da CVM (F3-3b): registro de cada arquivo carregado, FCA e
-- Informe mensal de FII. DFP e ITR vão para as tabelas da 004 (DD-42: FCA e FII com tabelas
-- próprias). Só inserção, como a 004.

-- Um registro por arquivo carregado, pelo hash do conteúdo: o mesmo arquivo não é lido de
-- novo (idempotência). `so_ultima_versao` é medido no próprio arquivo: 1 quando cada
-- documento do conteúdo tem uma só versão (e, com índice, a maior do índice); é a marca do L1
-- (DD-34). `resumo_json` guarda as contagens, os conflitos e as linhas recusadas.
CREATE TABLE cargas_arquivo (
    hash_sha256 TEXT NOT NULL PRIMARY KEY,
    tipo TEXT NOT NULL CHECK (tipo IN ('DFP', 'ITR', 'FCA', 'FII_INFORME')),
    arquivo TEXT NOT NULL,
    fonte TEXT NOT NULL,
    coleta TEXT NOT NULL,
    so_ultima_versao INTEGER NOT NULL CHECK (so_ultima_versao IN (0, 1)),
    resumo_json TEXT NOT NULL
);

-- Índice de entregas do FCA (fca_cia_aberta_AAAA.csv), com todas as versões que ele lista.
CREATE TABLE fca_entregas (
    cnpj TEXT NOT NULL,
    dt_refer TEXT NOT NULL,
    versao INTEGER NOT NULL,
    cd_cvm TEXT,
    denominacao TEXT,
    categoria TEXT,
    id_documento TEXT,
    dt_receb TEXT NOT NULL,
    valores_na_fonte INTEGER NOT NULL CHECK (valores_na_fonte IN (0, 1)),
    fonte TEXT NOT NULL,
    coleta TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    PRIMARY KEY (cnpj, dt_refer, versao)
);

-- Linhas das partes do FCA (geral, valor_mobiliario...), como o arquivo as traz: a linha
-- inteira em JSON, identificada pelo hash dela. A versão fica como texto, sem conversão.
CREATE TABLE fca_linhas (
    cnpj TEXT NOT NULL,
    dt_refer TEXT NOT NULL,
    versao TEXT NOT NULL,
    parte TEXT NOT NULL,
    linha_sha256 TEXT NOT NULL,
    linha_json TEXT NOT NULL,
    fonte TEXT NOT NULL,
    coleta TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    PRIMARY KEY (cnpj, dt_refer, versao, parte, linha_sha256)
);

-- Linhas do Informe mensal de FII (geral, complemento, ativo_passivo). Linhas diferentes da
-- mesma versão ficam todas (o conflito de mesma versão abstém na leitura, ficha FII 1.3); a
-- versão fica como texto, porque a legível é decidida na leitura (F3-P08). `data_entrega` é a
-- do arquivo geral; nas outras partes, '' (a entrega é a do geral, regra 3 da F2C-47).
CREATE TABLE fii_informe_linhas (
    cnpj TEXT NOT NULL,
    dt_refer TEXT NOT NULL,
    versao TEXT NOT NULL,
    parte TEXT NOT NULL CHECK (parte IN ('geral', 'complemento', 'ativo_passivo')),
    data_entrega TEXT NOT NULL DEFAULT '',
    linha_sha256 TEXT NOT NULL,
    linha_json TEXT NOT NULL,
    fonte TEXT NOT NULL,
    coleta TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    PRIMARY KEY (cnpj, dt_refer, versao, parte, linha_sha256)
);

CREATE INDEX idx_fca_entregas_receb ON fca_entregas (cnpj, dt_refer, dt_receb);

CREATE TRIGGER cargas_arquivo_sem_update BEFORE UPDATE ON cargas_arquivo
BEGIN SELECT RAISE(ABORT, 'cargas_arquivo é só de inserção'); END;
CREATE TRIGGER cargas_arquivo_sem_delete BEFORE DELETE ON cargas_arquivo
BEGIN SELECT RAISE(ABORT, 'cargas_arquivo é só de inserção'); END;
CREATE TRIGGER cargas_arquivo_sem_sobrescrita BEFORE INSERT ON cargas_arquivo
WHEN EXISTS (SELECT 1 FROM cargas_arquivo WHERE hash_sha256 = NEW.hash_sha256)
BEGIN SELECT RAISE(ABORT, 'cargas_arquivo é só de inserção'); END;

CREATE TRIGGER fca_entregas_sem_update BEFORE UPDATE ON fca_entregas
BEGIN SELECT RAISE(ABORT, 'fca_entregas é só de inserção'); END;
CREATE TRIGGER fca_entregas_sem_delete BEFORE DELETE ON fca_entregas
BEGIN SELECT RAISE(ABORT, 'fca_entregas é só de inserção'); END;
CREATE TRIGGER fca_entregas_sem_sobrescrita BEFORE INSERT ON fca_entregas
WHEN EXISTS (
    SELECT 1 FROM fca_entregas WHERE cnpj = NEW.cnpj AND dt_refer = NEW.dt_refer
    AND versao = NEW.versao
)
BEGIN SELECT RAISE(ABORT, 'fca_entregas é só de inserção'); END;

CREATE TRIGGER fca_linhas_sem_update BEFORE UPDATE ON fca_linhas
BEGIN SELECT RAISE(ABORT, 'fca_linhas é só de inserção'); END;
CREATE TRIGGER fca_linhas_sem_delete BEFORE DELETE ON fca_linhas
BEGIN SELECT RAISE(ABORT, 'fca_linhas é só de inserção'); END;
CREATE TRIGGER fca_linhas_sem_sobrescrita BEFORE INSERT ON fca_linhas
WHEN EXISTS (
    SELECT 1 FROM fca_linhas WHERE cnpj = NEW.cnpj AND dt_refer = NEW.dt_refer
    AND versao = NEW.versao AND parte = NEW.parte AND linha_sha256 = NEW.linha_sha256
)
BEGIN SELECT RAISE(ABORT, 'fca_linhas é só de inserção'); END;

CREATE TRIGGER fii_informe_linhas_sem_update BEFORE UPDATE ON fii_informe_linhas
BEGIN SELECT RAISE(ABORT, 'fii_informe_linhas é só de inserção'); END;
CREATE TRIGGER fii_informe_linhas_sem_delete BEFORE DELETE ON fii_informe_linhas
BEGIN SELECT RAISE(ABORT, 'fii_informe_linhas é só de inserção'); END;
CREATE TRIGGER fii_informe_linhas_sem_sobrescrita BEFORE INSERT ON fii_informe_linhas
WHEN EXISTS (
    SELECT 1 FROM fii_informe_linhas WHERE cnpj = NEW.cnpj AND dt_refer = NEW.dt_refer
    AND versao = NEW.versao AND parte = NEW.parte AND linha_sha256 = NEW.linha_sha256
)
BEGIN SELECT RAISE(ABORT, 'fii_informe_linhas é só de inserção'); END;
