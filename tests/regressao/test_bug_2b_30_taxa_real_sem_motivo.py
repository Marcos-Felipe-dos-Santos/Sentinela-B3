"""BUG-2B-30: a abstenção da taxa real perde o motivo (auditoria do F2B-48/F2B-30, achado 1).

`MacroProvider.registro` devolvia `None` quando a cesta se abstinha ou a fonte falhava, e o
Gordon mostrava um motivo enganoso ("inflação incompatível com a janela da DFP").
"""

from datetime import UTC, datetime

from apoio_gordon import enriquecer_gordon

from sentinela.data import gordon_cvm, taxas
from tests.test_macro_fontes import AS_OF, _registro_preparado


def test_cesta_abstem_com_o_motivo(tmp_path, monkeypatch):
    provider = _registro_preparado(tmp_path, monkeypatch)
    monkeypatch.setattr(
        taxas, "calcular", lambda *a, **kw: taxas.Abstencao("desatualizada")
    )
    assert provider.registro(AS_OF) == {"abstencao": "desatualizada"}


def test_falha_da_fonte_abstem_com_o_motivo(tmp_path, monkeypatch):
    provider = _registro_preparado(tmp_path, monkeypatch)

    def falha(*a, **kw):
        raise ValueError("calendário ANBIMA inválido ou de outro ano")

    monkeypatch.setattr(provider, "calendario", falha)
    assert provider.registro(AS_OF) == {
        "abstencao": "calendário ANBIMA inválido ou de outro ano"
    }


def test_gordon_mostra_o_motivo_da_taxa_real():
    dados = enriquecer_gordon(
        {"ticker": "TST3", "preco_atual": 100.0, "roe": 0.12, "pl": 10.0, "pvp": 1.0}
    )
    dados["taxa_real"] = {"abstencao": "desatualizada"}
    entradas = gordon_cvm.entradas(dados, datetime(2026, 10, 20, 15, tzinfo=UTC))
    assert entradas == gordon_cvm.Abstencao("taxa real indisponível: desatualizada")
