-- Eventos em ações da B3 (F3-4b): desdobramento, grupamento, bonificação e outros, como o
-- complemento do emissor (`GetListedSupplementCompany`, `stockDividends`) os traz. Cada linha
-- é identificada pelo hash do JSON do evento; a primeira coleta que o viu fica gravada. O fator
-- é o multiplicativo da quantidade (Manual Câmara B3: bonificação e desdobramento F = 1 + B/100,
-- grupamento: o fator declarado, já multiplicativo, 1/RL no manual), ou nulo com o motivo quando
-- a conversão não é demonstrada: o consumidor
-- abstém. Só inserção.
CREATE TABLE eventos_societarios (
    emissor TEXT NOT NULL,
    linha_sha256 TEXT NOT NULL,
    cd_cvm TEXT NOT NULL,
    rotulo TEXT NOT NULL,
    isin TEXT,
    ativo_emitido TEXT,
    data_com TEXT,
    aprovacao TEXT,
    fator_declarado TEXT,
    fator REAL CHECK (fator IS NULL OR fator > 0),
    motivo_sem_fator TEXT,
    linha_json TEXT NOT NULL,
    fonte TEXT NOT NULL,
    coleta TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    PRIMARY KEY (emissor, linha_sha256),
    CHECK ((fator IS NULL) <> (motivo_sem_fator IS NULL))
);

CREATE INDEX idx_eventos_societarios_isin ON eventos_societarios (isin, data_com);

CREATE TRIGGER eventos_societarios_sem_update BEFORE UPDATE ON eventos_societarios
BEGIN SELECT RAISE(ABORT, 'eventos_societarios é só de inserção'); END;
CREATE TRIGGER eventos_societarios_sem_delete BEFORE DELETE ON eventos_societarios
BEGIN SELECT RAISE(ABORT, 'eventos_societarios é só de inserção'); END;
CREATE TRIGGER eventos_societarios_sem_sobrescrita BEFORE INSERT ON eventos_societarios
WHEN EXISTS (
    SELECT 1 FROM eventos_societarios WHERE emissor = NEW.emissor
    AND linha_sha256 = NEW.linha_sha256
)
BEGIN SELECT RAISE(ABORT, 'eventos_societarios é só de inserção'); END;
