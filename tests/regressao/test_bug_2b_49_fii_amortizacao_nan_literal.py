"""BUG-2B-49: amortização `NaN` declarada no Informe é lida como célula vazia.

Auditoria de fechamento da 2B (Codex, 25/10/2026): o provedor lê o complemento com os
`na_values` padrão do pandas, e o literal `NaN` e a célula vazia chegam iguais
(`float('nan')`); a lente trata os dois como "sem amortização". Pela ficha FII 1.3 (§3c),
vazio vale zero e `NaN`, texto ou negativo abstêm.
"""

import zipfile
from datetime import date

import pytest

import cvm_fii_provider
from cvm_fii_provider import CVMFIIProvider
from sentinela.data import rendimento_fii as rf

CNPJ = "11.111.111/0001-11"
CAB = (
    "CNPJ_Fundo_Classe;Data_Referencia;Versao;Valor_Patrimonial_Cotas;"
    "Percentual_Dividend_Yield_Mes;Percentual_Amortizacao_Cotas_Mes;Cotas_Emitidas\n"
)


class _Hoje(date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 19)


def _linhas(amortizacao):
    return [
        {
            "Data_Referencia": f"2026-{m:02d}-01",
            "Percentual_Amortizacao_Cotas_Mes": amortizacao if m == 5 else "",
        }
        for m in range(1, 10)
    ]


@pytest.mark.parametrize("declarado", ["NaN", "abc", "-0.01"])
def test_amortizacao_declarada_invalida_nao_vira_vazio(
    tmp_path, monkeypatch, declarado
):
    corpo = "".join(
        f"{CNPJ};{l['Data_Referencia']};1;100;0.01;{l['Percentual_Amortizacao_Cotas_Mes']};1000\n"
        for l in _linhas(declarado)
    )
    caminho = tmp_path / "2026.zip"
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr(
            "inf_mensal_fii_complemento_2026.csv", (CAB + corpo).encode("latin-1")
        )
    provedor = CVMFIIProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(cvm_fii_provider, "date", _Hoje)
    monkeypatch.setattr(provedor, "baixar_informe", lambda ano: caminho)
    monkeypatch.setattr(provedor, "_proveniencia", lambda *a: None)
    registros = provedor.obter_rendimentos_fii(CNPJ)["registros"]
    por_mes = {
        r["Data_Referencia"]: r["Percentual_Amortizacao_Cotas_Mes"] for r in registros
    }
    assert por_mes["2026-05-01"] == declarado
    assert por_mes["2026-04-01"] == ""
    assert rf._numero(por_mes["2026-05-01"]) is None or float(declarado) < 0


@pytest.mark.parametrize(
    ("celula", "motivo"),
    [
        ("", None),
        ("NaN", rf.MOTIVO_AMORTIZACAO_INVALIDA),
        ("abc", rf.MOTIVO_AMORTIZACAO_INVALIDA),
        ("-0.01", rf.MOTIVO_AMORTIZACAO_INVALIDA),
    ],
)
def test_lente_le_a_amortizacao_pela_ficha_1_3(celula, motivo):
    from tests.test_fii_rendimento_elegivel import _avaliar, _registros

    r = _avaliar(
        _registros(**{"2026-05": {"Percentual_Amortizacao_Cotas_Mes": celula}})
    )
    if motivo is None:
        assert r["rendimento_12m"] == pytest.approx(12.0)
    else:
        assert r == rf.Abstencao(motivo)
