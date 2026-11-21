-- Preços brutos do COTAHIST da B3 (F3-4a): uma linha por pregão, código e mercado, como o
-- arquivo declara. Os preços ficam em centavos inteiros do lote de `fator_cotacao` ações
-- (PREABE, PREMAX, PREMIN, PREMED, PREULT), o volume em centavos (VOLTOT), a quantidade
-- (QUATOT) e os negócios (TOTNEG): nada é ajustado nem arredondado. Só inserção.
CREATE TABLE precos (
    data TEXT NOT NULL,
    codigo_negociacao TEXT NOT NULL,
    tipo_mercado TEXT NOT NULL,
    codbdi TEXT NOT NULL,
    prazo TEXT NOT NULL DEFAULT '',
    especificacao TEXT,
    isin TEXT,
    abertura_centavos INTEGER NOT NULL,
    maxima_centavos INTEGER NOT NULL,
    minima_centavos INTEGER NOT NULL,
    media_centavos INTEGER NOT NULL,
    fechamento_centavos INTEGER NOT NULL,
    negocios INTEGER NOT NULL,
    quantidade INTEGER NOT NULL,
    volume_centavos INTEGER NOT NULL,
    fator_cotacao INTEGER NOT NULL CHECK (fator_cotacao > 0),
    fonte TEXT NOT NULL,
    coleta TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    PRIMARY KEY (data, codigo_negociacao, tipo_mercado, codbdi, prazo)
);

CREATE INDEX idx_precos_codigo_data ON precos (codigo_negociacao, data);

-- Um registro por arquivo do COTAHIST carregado, pelo hash: o mesmo arquivo não é lido de
-- novo. `resumo_json` guarda as contagens, os conflitos e as linhas recusadas.
CREATE TABLE cargas_cotahist (
    hash_sha256 TEXT NOT NULL PRIMARY KEY,
    arquivo TEXT NOT NULL,
    data_geracao TEXT,
    fonte TEXT NOT NULL,
    coleta TEXT NOT NULL,
    resumo_json TEXT NOT NULL
);

CREATE TRIGGER precos_sem_update BEFORE UPDATE ON precos
BEGIN SELECT RAISE(ABORT, 'precos é só de inserção'); END;
CREATE TRIGGER precos_sem_delete BEFORE DELETE ON precos
BEGIN SELECT RAISE(ABORT, 'precos é só de inserção'); END;
CREATE TRIGGER precos_sem_sobrescrita BEFORE INSERT ON precos
WHEN EXISTS (
    SELECT 1 FROM precos WHERE data = NEW.data AND codigo_negociacao = NEW.codigo_negociacao
    AND tipo_mercado = NEW.tipo_mercado AND codbdi = NEW.codbdi AND prazo = NEW.prazo
)
BEGIN SELECT RAISE(ABORT, 'precos é só de inserção'); END;

CREATE TRIGGER cargas_cotahist_sem_update BEFORE UPDATE ON cargas_cotahist
BEGIN SELECT RAISE(ABORT, 'cargas_cotahist é só de inserção'); END;
CREATE TRIGGER cargas_cotahist_sem_delete BEFORE DELETE ON cargas_cotahist
BEGIN SELECT RAISE(ABORT, 'cargas_cotahist é só de inserção'); END;
CREATE TRIGGER cargas_cotahist_sem_sobrescrita BEFORE INSERT ON cargas_cotahist
WHEN EXISTS (SELECT 1 FROM cargas_cotahist WHERE hash_sha256 = NEW.hash_sha256)
BEGIN SELECT RAISE(ABORT, 'cargas_cotahist é só de inserção'); END;
