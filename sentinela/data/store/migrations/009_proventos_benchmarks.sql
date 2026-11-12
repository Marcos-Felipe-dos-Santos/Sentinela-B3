-- Proventos em dinheiro e benchmarks por data (F3-7a, decisões 7 e 10). Só inserção.
--
-- `proventos`: cada registro da relação da B3 (`GetListedCashDividends`), como a fonte o traz,
-- identificado pelo hash do JSON do registro; a primeira coleta que o viu fica gravada, com a
-- URL e o hash da página que o devolveu. O valor é o bruto por ação, literal (vírgula decimal);
-- a data ex é o pregão seguinte à data com e se calcula na leitura, com o calendário guardado.
CREATE TABLE proventos (
    emissor TEXT NOT NULL,
    linha_sha256 TEXT NOT NULL,
    cd_cvm TEXT NOT NULL,
    especie TEXT,
    natureza TEXT,
    data_com TEXT,
    aprovacao TEXT,
    valor_bruto TEXT,
    cotado_por TEXT,
    linha_json TEXT NOT NULL,
    fonte TEXT NOT NULL,
    coleta TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    PRIMARY KEY (emissor, linha_sha256)
);

-- Cada coleta da relação: o total que o serviço declarou, quantos registros vieram e a
-- identidade do emissor (decisão 33: nulo = conferida; senão, o motivo da falha).
CREATE TABLE proventos_coletas (
    emissor TEXT NOT NULL,
    coleta TEXT NOT NULL,
    cd_cvm TEXT NOT NULL,
    nome_pregao TEXT NOT NULL,
    total INTEGER,
    registros INTEGER NOT NULL,
    identidade TEXT,
    isins_json TEXT NOT NULL,
    fonte TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    PRIMARY KEY (emissor, coleta)
);

-- Quais registros cada coleta trouxe (o registro é gravado uma vez em `proventos`; cada coleta
-- o vê de novo aqui), para a leitura devolver a relação daquela coleta, sem a versão antiga de
-- um registro corrigido nem o cancelado.
CREATE TABLE proventos_vistos (
    emissor TEXT NOT NULL,
    coleta TEXT NOT NULL,
    linha_sha256 TEXT NOT NULL,
    PRIMARY KEY (emissor, coleta, linha_sha256)
);

-- `benchmarks`: fechamento diário do Ibovespa (B3, IndexCall/GetPortfolioDay, pontos) e a taxa
-- diária do CDI (BCB SGS 12, % ao dia), com o valor, a URL e o hash da
-- resposta que o devolveu (`valor_texto`: o literal da B3 no Ibovespa; o número lido no CDI,
-- que o leitor do SGS já converte). Uma mesma data pode vir de coletas diferentes.
CREATE TABLE benchmarks (
    serie TEXT NOT NULL CHECK (serie IN ('IBOV', 'CDI')),
    data TEXT NOT NULL,
    valor REAL NOT NULL,
    valor_texto TEXT NOT NULL,
    fonte TEXT NOT NULL,
    coleta TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    PRIMARY KEY (serie, data, hash_sha256)
);

CREATE TRIGGER proventos_sem_update BEFORE UPDATE ON proventos
BEGIN SELECT RAISE(ABORT, 'proventos é só de inserção'); END;
CREATE TRIGGER proventos_sem_delete BEFORE DELETE ON proventos
BEGIN SELECT RAISE(ABORT, 'proventos é só de inserção'); END;
CREATE TRIGGER proventos_sem_sobrescrita BEFORE INSERT ON proventos
WHEN EXISTS (
    SELECT 1 FROM proventos WHERE emissor = NEW.emissor AND linha_sha256 = NEW.linha_sha256
)
BEGIN SELECT RAISE(ABORT, 'proventos é só de inserção'); END;

CREATE TRIGGER proventos_coletas_sem_update BEFORE UPDATE ON proventos_coletas
BEGIN SELECT RAISE(ABORT, 'proventos_coletas é só de inserção'); END;
CREATE TRIGGER proventos_coletas_sem_delete BEFORE DELETE ON proventos_coletas
BEGIN SELECT RAISE(ABORT, 'proventos_coletas é só de inserção'); END;
CREATE TRIGGER proventos_coletas_sem_sobrescrita BEFORE INSERT ON proventos_coletas
WHEN EXISTS (
    SELECT 1 FROM proventos_coletas WHERE emissor = NEW.emissor AND coleta = NEW.coleta
)
BEGIN SELECT RAISE(ABORT, 'proventos_coletas é só de inserção'); END;

CREATE TRIGGER proventos_vistos_sem_update BEFORE UPDATE ON proventos_vistos
BEGIN SELECT RAISE(ABORT, 'proventos_vistos é só de inserção'); END;
CREATE TRIGGER proventos_vistos_sem_delete BEFORE DELETE ON proventos_vistos
BEGIN SELECT RAISE(ABORT, 'proventos_vistos é só de inserção'); END;

CREATE TRIGGER benchmarks_sem_update BEFORE UPDATE ON benchmarks
BEGIN SELECT RAISE(ABORT, 'benchmarks é só de inserção'); END;
CREATE TRIGGER benchmarks_sem_delete BEFORE DELETE ON benchmarks
BEGIN SELECT RAISE(ABORT, 'benchmarks é só de inserção'); END;
CREATE TRIGGER benchmarks_sem_sobrescrita BEFORE INSERT ON benchmarks
WHEN EXISTS (
    SELECT 1 FROM benchmarks WHERE serie = NEW.serie AND data = NEW.data
    AND hash_sha256 = NEW.hash_sha256
)
BEGIN SELECT RAISE(ABORT, 'benchmarks é só de inserção'); END;
