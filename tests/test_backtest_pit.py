"""F3-8a: contrato externo da ficha backtest aprovada, decisões41/42, §§4–10.

Esperados por aritmética manual/Fraction, nunca pelo código testado. API PIT nova:
formar_quintis, retorno_total, selecionar_horizonte, quintis_por_modo e
fronteira_calibracao. Nomes/formatos são escolha técnica do executor; regras e números
são os da ficha. A medição mutativa e a integração do serviço ficam no F3-8b.
O caso de modos fornece saídas documentais distintas já selecionadas pelo leitor PIT;
confere a fronteira do relatório, não substitui os testes existentes desse leitor.
"""

from datetime import date
from fractions import Fraction
from importlib import import_module

import pytest

pytestmark = pytest.mark.xfail(
    strict=True,
    reason="F3-8a — contrato aprovado; implementação da API PIT no F3-8b",
)

D = date(2020, 1, 31)
EX = date(2020, 4, 30)
COM = date(2020, 6, 30)
EVENTO = date(2020, 7, 1)
T = date(2021, 1, 29)


def _api():
    # Import dentro do teste: ausência da API fica vermelha, nunca skip/importorskip.
    return import_module("backtesting.backtest_pit")


def _observacoes(n):
    return [
        {"ticker": f"T{i:03d}3", "distancia_ao_preco_pct": float(n - i)}
        for i in range(n)
    ]


def _retorno(precos, proventos=(), eventos=(), **kwargs):
    return _api().retorno_total(precos, proventos, eventos, inicio=D, fim=T, **kwargs)


@pytest.mark.parametrize("n,tamanhos", [(25, [5, 5, 5, 5, 5]), (27, [5, 5, 6, 5, 6])])
def test_quintis_cortes_da_ficha_e_ordenacao_so_pela_distancia(n, tamanhos):
    obs = _observacoes(n)
    saida = _api().formar_quintis(list(reversed(obs)))
    grupos = saida["quintis"]
    assert [len(grupos[q]) for q in range(1, 6)] == tamanhos
    assert [t for q in range(1, 6) for t in grupos[q]] == [o["ticker"] for o in obs]
    assert saida["elegiveis"] == n
    assert saida["motivo"] is None
    assert saida["empates_nos_cortes"] == 0


def test_empate_atravessa_corte_por_codigo_sem_alterar_distancia():
    obs = _observacoes(25)
    for o in obs[:6]:
        o["distancia_ao_preco_pct"] = 100.0
    saida = _api().formar_quintis(list(reversed(obs)))
    assert saida["quintis"][1] == [f"T{i:03d}3" for i in range(5)]
    assert saida["quintis"][2][0] == "T0053"
    assert saida["empates_nos_cortes"] == 1


def test_menos_de_25_sem_quintis_com_mediana_contagem_e_motivo():
    obs = [dict(o, retorno_total=i / 100) for i, o in enumerate(_observacoes(24))]
    saida = _api().formar_quintis(obs)
    assert saida["quintis"] == {}
    assert saida["elegiveis"] == 24
    assert saida["mediana_retorno"] == pytest.approx(0.115)
    assert saida["motivo"] == "menos de 25 ativos elegíveis"


def test_abstencao_nao_vira_distancia_zero_nem_ativo_no_quintil():
    obs = _observacoes(25) + [
        {
            "ticker": "ABST3",
            "distancia_ao_preco_pct": None,
            "abstencao": "sem documento",
        }
    ]
    saida = _api().formar_quintis(obs)
    assert saida["elegiveis"] == 25
    assert saida["abstencoes"] == {"sem documento": 1}
    assert "ABST3" not in [t for grupo in saida["quintis"].values() for t in grupo]


def test_retorno_total_jcp_bruto_reinvestido_no_fechamento_da_ex():
    # 11/10 × (1 + 0,50/9,80) − 1 = 153/980; não descontar IR do JCP.
    saida = _retorno({D: 10, EX: 9.8, T: 11}, [{"data_ex": EX, "valor": 0.5}])
    assert saida["retorno"] == pytest.approx(float(Fraction(153, 980)))
    assert saida["abstencao"] is None


def test_desdobramento_sem_provento_nao_cria_retorno():
    saida = _retorno(
        {D: 10, COM: 10, EVENTO: 5, T: 5},
        eventos=[{"data_com": COM, "data_ex": EVENTO, "fator": 2.0}],
    )
    assert saida["retorno"] == pytest.approx(0)
    assert saida["abstencao"] is None


@pytest.mark.parametrize("fator,preco_final", [(2.0, 5.0), (0.5, 20.0)])
def test_provento_antes_de_split_ou_grupamento_na_mesma_base(fator, preco_final):
    # §10 casos10/11: uma ação→1,1→2,2 ou0,55; total11/entrada10 −1 =10%.
    # A conta por quantidades usa apenas constantes/Fraction, não serie_ajustada.
    quantidade = (1 + Fraction(1, 10)) * Fraction(str(fator))
    esperado = quantidade * Fraction(str(preco_final)) / 10 - 1
    assert esperado == Fraction(1, 10)
    saida = _retorno(
        {D: 10, EX: 10, COM: 10, EVENTO: preco_final, T: preco_final},
        [{"data_ex": EX, "valor": 1}],
        [{"data_com": COM, "data_ex": EVENTO, "fator": fator}],
    )
    assert saida["retorno"] == pytest.approx(float(esperado))
    assert saida["abstencao"] is None


def test_entrada_no_fechamento_d_ex_d_excluida_e_ex_terminal_incluida():
    saida = _retorno(
        {date(2020, 1, 30): 8, D: 10, T: 12},
        [{"data_ex": D, "valor": 2}, {"data_ex": T, "valor": 1}],
    )
    assert saida["retorno"] == pytest.approx(0.30)
    benchmark = _retorno({D: 10, T: 12})
    assert benchmark["retorno"] == pytest.approx(0.20)


def test_deslistagem_mes_sete_ultimo_preco_depois_fator_di():
    ultimo, meio = date(2020, 8, 31), date(2020, 12, 30)
    # Taxa em % ao dia; CDI usa [último,T), excluindo a taxa de T.
    saida = _retorno(
        {D: 10, ultimo: 12},
        deslistagem=ultimo,
        cdi={ultimo: 1.0, meio: 2.0, T: 99.0},
        pregoes=[D, ultimo, meio, T],
    )
    assert saida["retorno"] == pytest.approx(
        float(Fraction(12, 10) * Fraction(101, 100) * Fraction(102, 100) - 1)
    )
    assert saida["abstencao"] is None


def test_deslistagem_cdi_com_pregao_sem_taxa_abstem_sem_fator_parcial():
    ultimo, meio = date(2020, 8, 31), date(2020, 12, 30)
    saida = _retorno(
        {D: 10, ultimo: 12},
        deslistagem=ultimo,
        cdi={ultimo: 1.0},
        pregoes=[D, ultimo, meio, T],
    )
    assert saida["retorno"] is None
    assert "CDI" in saida["abstencao"] and "2020-12-30" in saida["abstencao"]


def test_deslistagem_no_terminal_inclui_ex_terminal_e_exclui_ex_d():
    saida = _retorno(
        {D: 10, T: 12},
        [{"data_ex": D, "valor": 2}, {"data_ex": T, "valor": 1}],
        deslistagem=T,
        cdi={},
        pregoes=[D, T],
    )
    assert saida["retorno"] == pytest.approx(0.30)


def test_suspensao_mantem_ultimo_preco_e_as_mesmas_fronteiras_ex():
    saida = _retorno(
        {D: 10, EX: 12},
        [{"data_ex": D, "valor": 2}, {"data_ex": T, "valor": 1}],
        pregoes=[D, EX, T],
    )
    assert saida["retorno"] == pytest.approx(0.30)
    assert saida["suspensao"] is True


def test_janela_final_so_inclui_horizonte_completo():
    a = {"D": D, "horizonte": 12, "fim": T, "retorno": 0.1}
    b = {"D": D, "horizonte": 24, "fim": date(2022, 1, 31), "retorno": 0.2}
    api = _api()
    r12 = api.selecionar_horizonte([a, b], 12, limite=date(2021, 2, 1))
    r24 = api.selecionar_horizonte([a, b], 24, limite=date(2021, 2, 1))
    assert r12 == {"observacoes": [a], "incompletas": 0}
    assert r24 == {"observacoes": [], "incompletas": 1}


def test_estrito_e_exploratorio_na_mesma_data_nao_se_misturam():
    # A v1 conhecida emD e a reapresentação v2 posterior geram saídas distintas.
    # Os leitores de versões têm seus próprios testes: aqui é sua fronteira no relatório.
    estrito = [dict(o, modo="estrito", versao_documento="1") for o in _observacoes(25)]
    exploratorio = [
        dict(
            o, modo="exploratorio", versao_documento="2", distancia_ao_preco_pct=i + 1.0
        )
        for i, o in enumerate(_observacoes(25))
    ]
    saida = _api().quintis_por_modo(estrito + exploratorio)
    assert set(saida) == {"estrito", "exploratorio"}
    assert saida["estrito"]["quintis"][1] == [f"T{i:03d}3" for i in range(5)]
    assert saida["exploratorio"]["quintis"][1] == [
        f"T{i:03d}3" for i in range(24, 19, -1)
    ]
    assert (
        saida["exploratorio"]["aviso"]
        == "possível reapresentação posterior não observável"
    )


def test_calibracao_fronteira_par_e_corte_separado_por_horizonte():
    dias = [date(2019, 1, 31), D, T, date(2022, 1, 31)]
    api = _api()
    fronteira = api.fronteira_calibracao(list(reversed(dias)))
    assert fronteira == D  # ceil(4/2)=2; primeira metade inclui a fronteira.
    origem = date(2019, 1, 31)
    a = {"D": origem, "horizonte": 12, "fim": D, "retorno": 0.1}
    b = {"D": origem, "horizonte": 24, "fim": T, "retorno": 0.2}
    assert api.selecionar_horizonte([a, b], 12, limite=fronteira) == {
        "observacoes": [a],
        "incompletas": 0,
    }
    assert api.selecionar_horizonte([a, b], 24, limite=fronteira) == {
        "observacoes": [],
        "incompletas": 1,
    }
