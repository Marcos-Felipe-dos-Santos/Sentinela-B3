"""F4-A10: a proveniência da coleta de hoje traz o clique e o instante real do download.

Ressalva do BUG-3-63: a coleta desta execução é registrada no `as_of` da análise (o clique),
segundos antes do download real. A proveniência passa a trazer os dois instantes, rotulados:
`as_of_analise` (o clique) e `baixado_em` (o download). As guardas continuam lendo só a coleta
da execução (`coleta` e `data_coleta`), e nenhum valor de lente muda.

Arranjos dos testes de regressão: BUG-3-63 (B3 da ação e do FII, pelo `AnalysisService`) e
BUG-4-10 (ZIP da CVM, Informe e IF.data de banco, pelo `MarketEngine`), com o relógio do motor
fixo 3 s depois do clique. O instante real do arquivo baixado é o `mtime` que ele recebeu.
"""

import os
from datetime import datetime, timedelta

from regressao.test_bug_3_63_coleta_da_execucao_apos_o_as_of import (  # noqa: F401
    AGORA,
    DEPOIS,
    servico,
)
from regressao.test_bug_4_10_download_da_execucao_no_as_of import AGORA as CLIQUE
from regressao.test_bug_4_10_download_da_execucao_no_as_of import DEPOIS as RELOGIO
from regressao.test_bug_4_10_download_da_execucao_no_as_of import (  # noqa: F401
    _bancos,
    _vencido,
    _zip,
    motor,
)

from sentinela.data import proveniencia
from sentinela.data.providers import ifdata


def _real(caminho) -> str:
    return proveniencia.data_da_coleta(caminho)


def test_relacao_de_proventos_da_b3_traz_os_dois_instantes(servico):  # noqa: F811
    dados = servico.analisar("ABEV3", AGORA, use_ai=False).raw
    registro = dados["proventos_b3"]["proveniencia"]

    assert registro["coleta"] == AGORA.isoformat()
    assert registro["as_of_analise"] == AGORA.isoformat()
    assert registro["baixado_em"] == DEPOIS.isoformat()


def test_complemento_do_fundo_na_b3_traz_os_dois_instantes(servico):  # noqa: F811
    fundo = servico.analisar("HGLG11", AGORA, use_ai=False).raw["b3_fundo"]

    assert fundo["coleta"] == AGORA.isoformat()
    assert fundo["as_of_analise"] == AGORA.isoformat()
    assert fundo["baixado_em"] == DEPOIS.isoformat()


def test_zip_da_cvm_baixado_hoje_traz_os_dois_instantes(motor):  # noqa: F811
    _vencido(motor.cvm._cache_path("dfp_2026.zip"), _zip("antigo.csv"))
    motor.coletado["baixar_dfp"] = True

    motor.buscar_dados_ticker("BBAS3", as_of=CLIQUE)
    registro = motor.coletado["dfp"]

    assert datetime.fromisoformat(registro.data_coleta) == CLIQUE
    assert registro.as_of_analise == CLIQUE.isoformat()
    assert registro.baixado_em == _real(motor.coletado["caminho_dfp"])
    # o registro do documento dentro do ZIP (`do_documento`) é o que chega aos `dados`
    documento = registro.do_documento(
        "2025-12-31", "1", "2026-03-01", "motivo"
    ).para_dict()
    assert documento["as_of_analise"] == CLIQUE.isoformat()
    assert documento["baixado_em"] == registro.baixado_em
    assert documento["data_coleta"] == registro.data_coleta


def test_informe_baixado_hoje_traz_os_dois_instantes(motor):  # noqa: F811
    caminho = motor.cvm_fii._cache_path("inf_mensal_fii_2026.zip")
    _vencido(caminho, _zip("antigo.csv"))
    motor.coletado["baixar_informe"] = True

    motor.buscar_dados_ticker("BBAS3", as_of=CLIQUE)
    registro = motor.coletado["informe"]

    assert datetime.fromisoformat(registro.data_coleta) == CLIQUE
    assert registro.as_of_analise == CLIQUE.isoformat()
    assert registro.baixado_em == _real(caminho)


def test_ifdata_de_banco_baixado_hoje_traz_os_dois_instantes(motor):  # noqa: F811
    dados, resultado = _bancos(motor)
    relatorios = [
        r for r in dados["ifdata"]["proveniencia"] if "calendario" not in r["fonte"]
    ]

    assert len(relatorios) == 3
    for registro in relatorios:
        assert datetime.fromisoformat(registro["data_coleta"]) == CLIQUE
        assert registro["as_of_analise"] == CLIQUE.isoformat()
        assert registro["baixado_em"] == _real(
            motor.ifdata._arquivo(registro["fonte"].removeprefix(ifdata.URL_BASE + "/"))
        )
    assert resultado["inadimplencia_ifdata"].startswith(
        "inadimplência IF.data (carteira ativa inadimplida arrastada ÷ Total Geral"
    )


def test_cache_de_outra_execucao_nao_ganha_os_instantes_da_analise(motor):  # noqa: F811
    caminho = motor.cvm._cache_path("dfp_2026.zip")
    _vencido(caminho, _zip("dfp_cia_aberta_2026.csv"))
    marca = RELOGIO.timestamp()
    os.utime(caminho, (marca, marca))
    motor.coletado["baixar_dfp"] = True

    motor.buscar_dados_ticker("BBAS3", as_of=CLIQUE)
    registro = motor.coletado["dfp"]

    assert type(registro) is proveniencia.Proveniencia
    assert {"as_of_analise", "baixado_em"}.isdisjoint(registro.para_dict())


def test_data_passada_nao_ganha_os_instantes_na_b3(servico, monkeypatch):  # noqa: F811
    """Numa data passada, a coleta é o relógio (decisão 40): não há clique a registrar."""
    from regressao.test_bug_3_63_coleta_da_execucao_apos_o_as_of import _Relogio

    monkeypatch.setattr(_Relogio, "atual", DEPOIS + timedelta(days=1))
    dados = servico.analisar("ABEV3", AGORA, use_ai=False).raw
    registro = dados["proventos_b3"].get("proveniencia", {})

    assert {"as_of_analise", "baixado_em"}.isdisjoint(registro)
    assert {"as_of_analise", "baixado_em"}.isdisjoint(dados.get("b3_fundo") or {})
