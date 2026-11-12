-- Registro da listagem (F3-5): cada código de negociação e ISIN do mercado à vista no
-- COTAHIST guardado em `precos`, com o primeiro e o último pregão de toda a história guardada e
-- a classe pelo ISIN, gravado por geração (o instante em que foi gerado). Não é lido pelo
-- universo ponto-no-tempo: o último pregão pode ser posterior a D. Só inserção.
CREATE TABLE universo (
    gerado_em TEXT NOT NULL,
    codigo_negociacao TEXT NOT NULL,
    isin TEXT NOT NULL,
    classe TEXT NOT NULL CHECK (classe IN ('STOCK', 'UNIT', 'FUNDO', 'BDR', 'OUTRO')),
    primeiro_pregao TEXT NOT NULL,
    ultimo_pregao TEXT NOT NULL,
    pregoes INTEGER NOT NULL CHECK (pregoes > 0),
    PRIMARY KEY (gerado_em, codigo_negociacao, isin)
);

CREATE TRIGGER universo_sem_update BEFORE UPDATE ON universo
BEGIN SELECT RAISE(ABORT, 'universo é só de inserção'); END;
CREATE TRIGGER universo_sem_delete BEFORE DELETE ON universo
BEGIN SELECT RAISE(ABORT, 'universo é só de inserção'); END;
CREATE TRIGGER universo_sem_sobrescrita BEFORE INSERT ON universo
WHEN EXISTS (
    SELECT 1 FROM universo WHERE gerado_em = NEW.gerado_em
    AND codigo_negociacao = NEW.codigo_negociacao AND isin = NEW.isin
)
BEGIN SELECT RAISE(ABORT, 'universo é só de inserção'); END;
