-- Insumos históricos da taxa real por data (F3-1c, pacote §2.4).
-- Uma linha por observação de uma coleta: série, data da observação, valor quando houver,
-- divulgação quando a fonte a prova, a linha original (detalhe_json), a fonte, o instante
-- da coleta e o hash do conteúdo baixado. Só inserção: a mesma observação coletada de novo
-- entra com outra coleta; nada é sobrescrito nem apagado.
CREATE TABLE series_macro (
    serie TEXT NOT NULL,
    data TEXT NOT NULL,
    valor REAL,
    divulgacao TEXT,
    detalhe_json TEXT NOT NULL,
    fonte TEXT NOT NULL,
    coleta TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    PRIMARY KEY (serie, data, coleta)
);

CREATE INDEX idx_series_macro_serie_data ON series_macro (serie, data);

CREATE TRIGGER series_macro_sem_update
BEFORE UPDATE ON series_macro
BEGIN
    SELECT RAISE(ABORT, 'series_macro é só de inserção');
END;

CREATE TRIGGER series_macro_sem_delete
BEFORE DELETE ON series_macro
BEGIN
    SELECT RAISE(ABORT, 'series_macro é só de inserção');
END;

CREATE TRIGGER series_macro_sem_sobrescrita
BEFORE INSERT ON series_macro
WHEN EXISTS (
    SELECT 1 FROM series_macro
    WHERE serie = NEW.serie AND data = NEW.data AND coleta = NEW.coleta
)
BEGIN
    SELECT RAISE(ABORT, 'series_macro é só de inserção');
END;
