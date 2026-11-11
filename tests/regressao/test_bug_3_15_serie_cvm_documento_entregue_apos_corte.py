"""BUG-3-15: o corte da série CVM usa o fim do período, não a data de entrega.

Auditoria cruzada da 3-a (Claude, 11/11/2026), sobre o F3-P13: a DFP de 2023 da fixture foi
recebida em 01/03/2024 (`DT_RECEB`), mas entra na série e no lucro no corte de 31/12/2023
(São Paulo). Histórico estrito (decisão 3, D17): vale o documento com `DT_RECEB ≤ as_of`.
Corrige: F3-3d, que liga o leitor estrito do F3-3c à cascata. O TTM sem ITR recebido depois do
corte fica para o teste do F3-3d (esta fixture não tem ITR). A asserção fixa o desenho do modo
estrito (DD-30): a série fica só com os documentos recebidos até o corte. O `test_bug_3_12` afirma hoje o contrário (2023 no corte);
a forma de conciliar os dois é a pergunta 1 da auditoria ao Marcos.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from apoio_escopo import de_empresa

from market_engine import MarketEngine
from tests.regressao.test_bug_2c_62_qualidade_produtor import fonte_anual
from tests.test_cvm_series import _Hoje


def _motor(tmp_path, monkeypatch):
    provedor = fonte_anual(tmp_path, monkeypatch)  # DT_RECEB do exercício N: 01/03/N+1
    monkeypatch.setattr("market_engine.date", _Hoje)  # 13/10/2026
    motor = MarketEngine.__new__(MarketEngine)
    motor.cvm = provedor
    dados = de_empresa(
        {"ticker": "TSTA3", "cd_cvm": 9999, "preco_atual": 100, "especie": "ON"}
    )
    return motor, dados


def _exercicios(dados):
    return [
        e["exercicio"] for e in (dados.get("serie_cvm") or {}).get("exercicios", [])
    ]


@pytest.mark.xfail(
    strict=True,
    reason="BUG-3-15 · DFP entregue depois do corte entra na série · corrige: F3-3d",
)
def test_dfp_recebida_depois_do_corte_nao_entra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    motor, dados = _motor(tmp_path, monkeypatch)
    corte = datetime(
        2024, 1, 1, 2, tzinfo=UTC
    )  # 31/12/2023 em São Paulo; DFP 2023 recebida em 01/03/2024
    assert motor._buscar_cvm("TSTA3", dados, as_of=corte)
    assert _exercicios(dados) == [2021, 2022]  # só o que foi recebido até o corte
    assert dados.get("lucro_liquido") != -2  # o lucro de 2023 não pode aparecer


def test_dfp_recebida_antes_do_corte_entra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Contraprova: no corte de 02/03/2024 (São Paulo), a DFP de 2023 já foi recebida."""
    motor, dados = _motor(tmp_path, monkeypatch)
    corte = datetime(2024, 3, 2, 15, tzinfo=UTC)
    assert motor._buscar_cvm("TSTA3", dados, as_of=corte)
    assert 2023 in _exercicios(dados)
