"""BUG-4-20: a relação da B3 lida do cache ganha um `baixado_em` novo, sem novo download.

O F4-A10 grava em `baixado_em` a hora em que a chamada ao provedor da B3 retorna. Na repetição
da mesma coleta explícita (mesmo emissor e mesmo instante de coleta), o provedor devolve a
relação do cache em memória, e a nova hora era registrada como se houvesse novo download
(ressalva da auditoria R2 do bloco 0, `docs/loop/auditorias/bloco0-codex.md`, F4-A10).

Arranjo do BUG-3-63 (`AnalysisService`, relógio fixo do motor); a mesma análise é repetida com o
relógio adiantado e as chamadas HTTP à B3 são contadas.
"""

from datetime import timedelta

import requests
from regressao.test_bug_3_63_coleta_da_execucao_apos_o_as_of import (  # noqa: F401
    AGORA,
    DEPOIS,
    _Relogio,
    servico,
)


def _contar_b3(monkeypatch) -> list[str]:
    chamadas: list[str] = []
    original = requests.get

    def get(endereco, *args, **kwargs):
        if "b3.com.br" in str(endereco):
            chamadas.append(str(endereco))
        return original(endereco, *args, **kwargs)

    monkeypatch.setattr(requests, "get", get)
    return chamadas


def test_relacao_de_proventos_do_cache_preserva_o_instante_original(
    servico,  # noqa: F811
    monkeypatch,
):
    chamadas = _contar_b3(monkeypatch)
    primeira = servico.analisar("ABEV3", AGORA, use_ai=False).raw["proventos_b3"]
    baixadas = len(chamadas)
    assert baixadas > 0  # a primeira análise consultou a fonte
    monkeypatch.setattr(_Relogio, "atual", DEPOIS + timedelta(seconds=30))

    segunda = servico.analisar("ABEV3", AGORA, use_ai=False).raw["proventos_b3"]

    assert len(chamadas) == baixadas  # a segunda leitura veio do cache
    assert primeira["proveniencia"]["baixado_em"] == DEPOIS.isoformat()
    assert segunda["proveniencia"]["baixado_em"] == DEPOIS.isoformat()


def test_complemento_do_fundo_do_cache_preserva_o_instante_original(
    servico,  # noqa: F811
    monkeypatch,
):
    chamadas = _contar_b3(monkeypatch)
    primeira = servico.analisar("HGLG11", AGORA, use_ai=False).raw["b3_fundo"]
    baixadas = len(chamadas)
    assert baixadas > 0  # a primeira análise consultou a fonte
    monkeypatch.setattr(_Relogio, "atual", DEPOIS + timedelta(seconds=30))

    segunda = servico.analisar("HGLG11", AGORA, use_ai=False).raw["b3_fundo"]

    assert len(chamadas) == baixadas
    assert primeira["baixado_em"] == DEPOIS.isoformat()
    assert segunda["baixado_em"] == DEPOIS.isoformat()
