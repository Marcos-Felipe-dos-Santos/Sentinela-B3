"""Consumidores da abstenção da taxa real com o motivo (F2B-51)."""

from datetime import UTC, datetime

import config
from sentinela.reports import rastreabilidade

INSTANTE = datetime(2026, 10, 20, 15, tzinfo=UTC)


def test_abstencao_nao_fica_no_cache(monkeypatch):
    chamadas = []

    def carregar(instante, janela):
        chamadas.append(instante)
        return {"abstencao": "desatualizada"}

    monkeypatch.setattr(config, "_carregar_taxa_real", carregar)
    monkeypatch.setattr(config, "_taxa_real_cache", {})
    assert config.get_taxa_real(as_of=INSTANTE) == {"abstencao": "desatualizada"}
    assert config.get_taxa_real(as_of=INSTANTE) == {"abstencao": "desatualizada"}
    assert len(chamadas) == 2
    assert config._taxa_real_cache == {}


def test_registro_valido_fica_no_cache(monkeypatch):
    chamadas = []

    def carregar(instante, janela):
        chamadas.append(instante)
        return {"custo_capital_real": 0.12, "pib": {}}

    monkeypatch.setattr(config, "_carregar_taxa_real", carregar)
    monkeypatch.setattr(config, "_taxa_real_cache", {})
    config.get_taxa_real(as_of=INSTANTE)
    config.get_taxa_real(as_of=INSTANTE)
    assert len(chamadas) == 1


def test_custo_de_capital_real_com_abstencao_e_none(monkeypatch):
    monkeypatch.setattr(config, "get_taxa_real", lambda: {"abstencao": "x"})
    assert config.MACRO.cost_of_equity_real() is None
    monkeypatch.setattr(config, "get_taxa_real", lambda: None)
    assert config.MACRO.cost_of_equity_real() is None
    monkeypatch.setattr(config, "get_taxa_real", lambda: {"custo_capital_real": 0.12})
    assert config.MACRO.cost_of_equity_real() == 0.12


def test_relatorio_mostra_a_abstencao_da_taxa_real():
    assert rastreabilidade._taxa_real(
        {"taxa_real": {"abstencao": "desatualizada"}}
    ) == [("Taxa real", "abstenção: desatualizada")]
    assert rastreabilidade._taxa_real({}) == []


def test_gordon_sem_registro_da_taxa_real_tem_motivo_proprio():
    from apoio_gordon import enriquecer_gordon

    from sentinela.data import gordon_cvm

    dados = enriquecer_gordon(
        {"ticker": "TST3", "preco_atual": 100.0, "roe": 0.12, "pl": 10.0, "pvp": 1.0}
    )
    for ausente in (None, {}):
        dados["taxa_real"] = ausente
        assert gordon_cvm.entradas(dados, INSTANTE) == gordon_cvm.Abstencao(
            "insumo ausente: taxa real"
        )


def test_falha_da_fonte_sem_mensagem_tem_o_tipo_como_motivo(tmp_path, monkeypatch):
    from datetime import date

    import requests

    from tests.test_macro_fontes import AS_OF, _registro_preparado

    provider = _registro_preparado(tmp_path, monkeypatch)

    def falha(*a, **kw):
        raise requests.RequestException()

    monkeypatch.setattr(provider, "inflacao", falha)
    monkeypatch.setattr(provider, "pib", lambda t: (_ for _ in ()).throw(OSError()))
    registro = provider.registro(AS_OF, (date(2025, 1, 1), date(2025, 12, 31)))
    assert registro["inflacao"] == {"abstencao": "RequestException"}
    assert registro["pib"] == {"abstencao": "OSError"}
    monkeypatch.setattr(provider, "calendario", falha)
    assert provider.registro(AS_OF) == {"abstencao": "RequestException"}
