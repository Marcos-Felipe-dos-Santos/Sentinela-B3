"""BUG-2C-02: igualdade customizada não identifica a observação de um leitor B3.

Revisão interna F2C-26, 26/10/2026. Dois leitores distintos que comparam iguais não podem
compartilhar dados/proveniência. A chave deve conservar identidade e referência do leitor.
"""

import gc
import weakref

import pytest

from sentinela.data.cache_leitura import CacheCopia
from sentinela.data.providers import b3_fundos, b3_proventos
from tests.test_b3_proventos import AGORA, _B3Falsa


class LeitorIgual(_B3Falsa):
    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, LeitorIgual)

    def __hash__(self) -> int:
        return 1


class FundoIgual:
    def __init__(self, origem: int) -> None:
        self.origem = origem

    def __eq__(self, outro: object) -> bool:
        return isinstance(outro, FundoIgual)

    def __hash__(self) -> int:
        return 1

    def __call__(self, endereco: str) -> tuple[dict, dict]:
        return {
            "code": "HGLG",
            "fund": "FII SINTÉTICO",
            "cashDividends": [],
            "stockDividends": [],
            "origem": self.origem,
        }, {"url": endereco, "sha256": str(self.origem) * 64}


@pytest.mark.parametrize("provedor", ["proventos", "fundos"])
def test_igualdade_de_leitores_nao_compartilha_snapshot(provedor: str) -> None:
    if provedor == "proventos":
        primeiro = LeitorIgual([[{"origem": 1}]])
        segundo = LeitorIgual([[{"origem": 2}]])
        assert primeiro is not segundo and primeiro == segundo
        b3_proventos.coletar(8133, AGORA, primeiro)
        assert b3_proventos.coletar(8133, AGORA, segundo).registros == ({"origem": 2},)
    else:
        primeiro = FundoIgual(1)
        segundo = FundoIgual(2)
        b3_fundos.coletar("11.728.688/0001-47", "HGLG11", AGORA, primeiro)
        coleta = b3_fundos.coletar("11.728.688/0001-47", "HGLG11", AGORA, segundo)
        assert coleta["resposta"]["origem"] == 2
        assert coleta["fonte"]["sha256"] == "2" * 64


def test_cache_mantem_leitor_vivo_so_enquanto_entrada_existe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(b3_proventos, "_COLETAS", CacheCopia(limite=1))
    leitor = _B3Falsa([[{"n": 1}]])
    referencia = weakref.ref(leitor)
    b3_proventos.coletar(8133, AGORA, leitor)
    del leitor
    gc.collect()
    assert referencia() is not None
    b3_proventos.coletar(8133, AGORA, _B3Falsa([[{"n": 2}]]))
    gc.collect()
    assert referencia() is None


def test_chave_compara_identidade_e_nao_igualdade_do_leitor() -> None:
    from sentinela.data.cache_leitura import IdentidadeLeitor

    primeiro = LeitorIgual([[{"origem": 1}]])
    segundo = LeitorIgual([[{"origem": 2}]])
    chave = IdentidadeLeitor(primeiro)
    assert chave == IdentidadeLeitor(primeiro)
    assert chave != IdentidadeLeitor(segundo)
    assert chave != object()
