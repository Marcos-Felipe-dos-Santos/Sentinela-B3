-- Complemento em dinheiro da B3 por coleta (F3-8d-fix, BUG-3-37, decisão 43 do Marcos, DD-74):
-- os proventos em dinheiro do GetListedSupplementCompany com que a coleta conferiu a parte (b)
-- da decisão 33. Gravados para a conferência ser refeita na leitura com o ISIN do ticker no
-- pregão (CODISI do COTAHIST). `dinheiro_json` é a lista inteira, inclusive vazia; coleta sem
-- linha aqui é anterior a esta migração e não tem o complemento guardado.
CREATE TABLE proventos_complemento (
    emissor TEXT NOT NULL,
    coleta TEXT NOT NULL,
    dinheiro_json TEXT NOT NULL,
    fonte TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    PRIMARY KEY (emissor, coleta),
    FOREIGN KEY (emissor, coleta) REFERENCES proventos_coletas (emissor, coleta)
);
