-- Resultados imutáveis por ticker, as_of, método e versão (F3-2d, decisão 16, PLANO §5).
-- Só inserção: os gatilhos recusam UPDATE, DELETE e qualquer INSERT que reuse um id,
-- repita a execução ou crie um segundo "original"; "recalculo" exige o original antes.
CREATE TABLE resultados_analise (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    as_of TEXT NOT NULL,
    metodo TEXT NOT NULL,
    versao TEXT NOT NULL,
    execucao_id TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('original', 'recalculo')),
    resultado_json TEXT,
    motivo_abstencao TEXT,
    hash_resultado TEXT NOT NULL,
    proveniencia_json TEXT NOT NULL,
    CHECK ((resultado_json IS NULL) <> (motivo_abstencao IS NULL))
);

CREATE UNIQUE INDEX idx_resultados_analise_execucao
ON resultados_analise (ticker, as_of, metodo, versao, execucao_id);

CREATE UNIQUE INDEX idx_resultados_analise_original
ON resultados_analise (ticker, as_of, metodo, versao) WHERE tipo = 'original';

CREATE INDEX idx_resultados_analise_ticker_as_of
ON resultados_analise (ticker, as_of);

CREATE TRIGGER resultados_analise_sem_update
BEFORE UPDATE ON resultados_analise
BEGIN
    SELECT RAISE(ABORT, 'resultados_analise é só de inserção');
END;

CREATE TRIGGER resultados_analise_sem_delete
BEFORE DELETE ON resultados_analise
BEGIN
    SELECT RAISE(ABORT, 'resultados_analise é só de inserção');
END;

CREATE TRIGGER resultados_analise_sem_sobrescrita
BEFORE INSERT ON resultados_analise
WHEN NEW.id IS NOT NULL AND EXISTS (SELECT 1 FROM resultados_analise WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'resultados_analise é só de inserção');
END;

CREATE TRIGGER resultados_analise_execucao_unica
BEFORE INSERT ON resultados_analise
WHEN EXISTS (
    SELECT 1 FROM resultados_analise
    WHERE ticker = NEW.ticker AND as_of = NEW.as_of AND metodo = NEW.metodo
      AND versao = NEW.versao AND execucao_id = NEW.execucao_id
)
BEGIN
    SELECT RAISE(ABORT, 'resultados_analise é só de inserção');
END;

CREATE TRIGGER resultados_analise_tipo
BEFORE INSERT ON resultados_analise
WHEN (NEW.tipo = 'original') = EXISTS (
    SELECT 1 FROM resultados_analise
    WHERE ticker = NEW.ticker AND as_of = NEW.as_of AND metodo = NEW.metodo
      AND versao = NEW.versao AND tipo = 'original'
)
BEGIN
    SELECT RAISE(ABORT, 'resultados_analise: tipo incompatível com as execuções gravadas');
END;
