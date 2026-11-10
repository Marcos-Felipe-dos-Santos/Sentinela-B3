-- F3-2b: as tabelas e índices reais dos dois bancos atuais, com os mesmos nomes e colunas.
-- `recomendacao`, `recommendation` e `score` são colunas legadas, recriadas por fidelidade
-- dos dados históricos (R1); não são vocabulário novo.

-- sentinela_v6.db (database.py, DatabaseManager._init_db)
CREATE TABLE analises (
    ticker       TEXT PRIMARY KEY,
    data_analise TEXT,
    score        INTEGER,
    recomendacao TEXT,
    dados_completos TEXT
);

CREATE TABLE carteira_real (
    ticker      TEXT PRIMARY KEY,
    quantidade  INTEGER,
    preco_medio REAL,
    data_aporte TEXT
);

CREATE TABLE fundamentals_cache (
    ticker        TEXT PRIMARY KEY,
    dados_json    TEXT NOT NULL,
    fonte         TEXT,
    atualizado_em TEXT NOT NULL
);

CREATE INDEX idx_data ON analises (data_analise);

-- sentinela.db (sentinela/repositories/analysis_repository.py, AnalysisRepository._init_db)
CREATE TABLE analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    created_at TEXT NOT NULL,
    asset_type TEXT,
    recommendation TEXT,
    fair_value REAL,
    current_price REAL,
    upside REAL,
    confidence REAL,
    data_quality_score REAL,
    input_hash TEXT,
    payload_json TEXT NOT NULL
);

CREATE INDEX idx_analysis_runs_ticker ON analysis_runs(ticker);

CREATE INDEX idx_analysis_runs_created_at ON analysis_runs(created_at);

CREATE INDEX idx_analysis_runs_ticker_created_at ON analysis_runs(ticker, created_at);
