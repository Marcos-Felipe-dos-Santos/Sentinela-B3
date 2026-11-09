"""Cascata sem o Fundamentus (F2A-22; checkpoint da Fase 0, seção 2).

O passo 4 sai. `erro_scraper` vira a checagem genérica `fundamentos_incompletos`: campo
obrigatório faltando depois de todas as fontes. O rebaixamento da V1 continua, mas só quando
falta dado, não quando o scraper falhava e outras fontes completavam os campos.
"""

from apoio_apresentacao import verificar_lentes
from apoio_bazin import enriquecer_bazin
from apoio_escopo import de_empresa

from tests.test_market_engine import _engine, _historico
from valuation_engine import ValuationEngine

# Ação barata pelos métodos (Graham, Bazin e Gordon bem acima do preço): a V1 a classifica
# no topo, e o rebaixamento por dado faltando fica visível.
INFO_COMPLETO = {
    "currentPrice": 10.0,
    "trailingPE": 3.0,
    "priceToBook": 0.5,
    "returnOnEquity": 0.17,
    "dividendYield": 22.0,
    "quoteType": "EQUITY",
}


class _ScraperQueAnota:
    def __init__(self):
        self.chamadas = 0

    def buscar_dados(self, ticker):
        self.chamadas += 1
        return {"erro_scraper": True}


def _cascata(monkeypatch, info):
    engine = _engine(monkeypatch, info=info, historico=_historico(10.0))
    engine.scraper = _ScraperQueAnota()
    return engine, engine.buscar_dados_ticker("TSTE3")


def _processar(dados):
    # F2B-31: a cascata de teste não tem a relação B3; o Bazin a recebe sintética, com o
    # mesmo DY.
    return ValuationEngine().processar(de_empresa(enriquecer_bazin(dados)))


def test_cascata_nao_chama_o_fundamentus(monkeypatch):
    # Sem a brapi, a V1 chamava o Fundamentus mesmo com os campos completos.
    engine, dados = _cascata(monkeypatch, INFO_COMPLETO)
    assert engine.scraper.chamadas == 0
    assert "fundamentus" not in dados.get("valores_por_fonte", {})
    assert dados["fundamentos_incompletos"] is False


def test_campos_completos_nao_rebaixam_a_classificacao(monkeypatch):
    _, dados = _cascata(monkeypatch, INFO_COMPLETO)
    analise = _processar(dados)
    verificar_lentes(analise)
    assert "Dados fundamentais obrigatórios ausentes" not in analise["riscos"]


def test_campo_obrigatorio_faltando_rebaixa_como_antes(monkeypatch):
    # Sem P/VP em nenhuma fonte: a cascata marca a falta e o motor rebaixa como a V1 fazia
    # com `erro_scraper`, com o risco renomeado.
    info = {k: v for k, v in INFO_COMPLETO.items() if k != "priceToBook"}
    _, dados = _cascata(monkeypatch, info)
    assert dados["fundamentos_incompletos"] is True
    analise = _processar(dados)
    verificar_lentes(analise)
    assert "Dados fundamentais obrigatórios ausentes" in analise["riscos"]
    completo = _processar({**dados, "fundamentos_incompletos": False})
    assert completo["confianca"] - analise["confianca"] >= 30


def test_cache_que_completa_os_campos_nao_marca_incompletos(monkeypatch):
    # A flag é calculada depois do cache: o que ele completa não conta como faltando.
    from tests.test_market_engine import FakeCache

    info = {"currentPrice": 10.0, "trailingPE": 3.0, "quoteType": "EQUITY"}
    engine = _engine(
        monkeypatch,
        info=info,
        historico=_historico(10.0),
        cache=FakeCache({"pvp": 0.5, "roe": 0.17, "dy": 0.22}),
    )
    dados = engine.buscar_dados_ticker("TSTE3")
    assert dados["dados_cache"] is True
    assert dados["fundamentos_incompletos"] is False
    sem_cache = _engine(
        monkeypatch, info=info, historico=_historico(10.0), cache=FakeCache()
    )
    assert sem_cache.buscar_dados_ticker("TSTE3")["fundamentos_incompletos"] is True
