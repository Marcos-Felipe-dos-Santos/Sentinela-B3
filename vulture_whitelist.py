"""Exceções do vulture (falsos positivos), cada uma com o motivo.

Uso: python -m vulture . vulture_whitelist.py --min-confidence 80 --exclude venv,mutants,outputs,data

O vulture marca como usado todo nome que aparece como atributo. Por isso as
exceções são acessos de atributo em um objeto que aceita qualquer nome; o
arquivo nunca é executado nem importado pelo app. Item *investigar* do
inventário (`get_quote`, `buscar_noticias`, `baixar_itr`) NÃO entra aqui:
continua aparecendo no relatório até a decisão do Marcos.
"""


class _Usado:
    def __getattr__(self, nome):
        return self


_ = _Usado()

USADOS = [
    # ── Dublês de teste: precisam aceitar a assinatura da função substituída ──
    _.kwargs,  # tests/conftest.py, test_backtest_engine, test_cvm_provider, test_cvm_ticker_map, test_market_engine
    _.max_age_days,  # tests/test_market_engine.py: dublê de buscar_fundamentos_cache
    # ── sqlite3: atribuição a atributo da conexão, que o vulture não entende ──
    _.row_factory,  # auditoria.py, cvm_ticker_map.py, limpar_banco.py, sentinela/repositories
    # ── Camada sentinela/ (E-21, ainda desconectada; o F3-6 liga ao app) ──────
    _.fonte_preco,  # sentinela/domain/models.py: campo de dataclass lido na serialização
    _.fonte_fundamentos,  # idem
    _.roic,  # idem
    _.div_liq_patrimonio,  # idem
    _.margem_bruta,  # idem
    _.score_final,  # idem
    _.metodos_usados,  # idem
    _.atr,  # idem
    _.with_warning,  # sentinela/domain/provenance.py: API do domínio, sem chamador até o F3-6
    # ── Classe do ativo (F2A-1): previstas no enum, sem uso até lá ────────────
    _.ETF,  # sentinela/domain/enums.py
    _.BDR,  # sentinela/domain/enums.py
]
