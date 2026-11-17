"""Casos de borda da integração PIT e do relatório do F3-8b."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from backtesting.backtest_pit import (
    BacktestPIT,
    _abstencao,
    _normalizar_hash,
    _preco_mantido,
    retorno_total,
)
from sentinela.data.providers import b3_proventos

D = date(2022, 3, 31)
EX = date(2022, 4, 29)
T = date(2023, 3, 31)


class _Consulta:
    def __init__(self, linhas):
        self.linhas = linhas

    def fetchall(self):
        return self.linhas

    def fetchone(self):
        return self.linhas[0] if self.linhas else None


class _BancoRetornos:
    def __init__(self, precos, isin="BRABEVACNOR1"):
        self.precos = precos
        self.isin = isin

    def execute(self, sql, parametros):
        if "SELECT data, fechamento_centavos" in sql:
            return _Consulta(self.precos)
        if "SELECT isin FROM precos" in sql:
            return _Consulta([(self.isin,)] if self.isin else [])
        raise AssertionError(f"consulta não prevista no teste: {sql}")


def _exec(
    monkeypatch,
    *,
    precos=(("2022-03-31", 1000, 1), ("2023-03-31", 1100, 1)),
    proventos=None,
    eventos=None,
    sem_prova_eventos=(),
    isin="BRABEVACNOR1",
    ticker="ABEV3",
):
    monkeypatch.setattr(
        b3_proventos,
        "proventos_ate",
        lambda *a, **k: (
            proventos
            if proventos is not None
            else {"proventos": [], "sem_prova": [], "coleta": "fixa"}
        ),
    )
    monkeypatch.setattr(
        b3_proventos,
        "eventos_ate",
        lambda *a, **k: {
            "eventos": eventos or [],
            "sem_prova": list(sem_prova_eventos),
        },
    )
    executor = BacktestPIT(
        _BancoRetornos(list(precos), isin),
        None,
        hoje=date(2026, 11, 13),
        cache_dir="cache",
    )
    return executor._retornos(
        ticker,
        None,
        D,
        T,
        [D, EX, T],
        {"IBOV": [], "CDI": []},
        b3_proventos,
    )


def test_retorno_integrado_abstem_quando_fechamento_de_entrada_falta(monkeypatch):
    retorno, entrada, ibov, cdi, evidencia = _exec(
        monkeypatch, precos=(("2023-03-31", 1100, 1),)
    )
    assert retorno["retorno"] is None
    assert retorno["abstencao"] == "fechamento de entrada indisponível"
    assert entrada is ibov is cdi is None
    assert evidencia["precos"] == [("2023-03-31", 1100, 1)]


def test_retorno_integrado_nao_infere_suspensao_sem_fca(monkeypatch):
    retorno, entrada, *_ = _exec(monkeypatch, precos=((D.isoformat(), 1000, 1),))
    assert entrada == 10
    assert retorno["retorno"] is None
    assert retorno["abstencao"] == (
        "estado terminal sem prova de suspensão ou deslistagem"
    )


def test_provento_abstido_na_fonte_nao_vira_zero(monkeypatch):
    retorno, *_ = _exec(
        monkeypatch, proventos={"abstencao": "identidade do emissor não comprovada"}
    )
    assert retorno["retorno"] is None
    assert retorno["abstencao"] == "identidade do emissor não comprovada"


def test_provento_com_unidade_bruta_e_especie_incompativel_abstem(monkeypatch):
    retorno, *_ = _exec(
        monkeypatch,
        proventos={
            "proventos": [
                {
                    "especie": "ON",
                    "data_ex": EX.isoformat(),
                    "valor_bruto": "0,50",
                    "cotado_por": "0",
                }
            ],
            "sem_prova": [],
        },
    )
    assert retorno["abstencao"] == "provento bruto ou unidade inválidos"


def test_provento_bruto_reinvestido_e_evento_de_outra_especie_ignorado(monkeypatch):
    retorno, entrada, *_ = _exec(
        monkeypatch,
        proventos={
            "proventos": [
                {
                    "especie": "ON",
                    "natureza": "DIVIDENDO",
                    "data_ex": EX.isoformat(),
                    "valor_bruto": "1,00",
                    "cotado_por": "1",
                }
            ],
            "sem_prova": [],
        },
        eventos=[
            {
                "isin": "BRABEVACPNR1",
                "data_com": "2022-04-01",
                "data_ex": EX.isoformat(),
                "fator": 2,
            }
        ],
    )
    assert entrada == 10
    assert retorno["abstencao"] is None
    assert retorno["retorno"] == pytest.approx(0.21)


def test_evento_sem_data_ex_no_intervalo_abstem(monkeypatch):
    retorno, *_ = _exec(
        monkeypatch,
        eventos=[
            {
                "isin": "BRABEVACNOR1",
                "data_com": "2022-04-01",
                "data_ex": None,
                "motivo_data_ex": "calendário indisponível",
            }
        ],
    )
    assert retorno["abstencao"] == "calendário indisponível"


def test_evento_sem_fator_no_intervalo_abstem(monkeypatch):
    retorno, *_ = _exec(
        monkeypatch,
        eventos=[
            {
                "isin": "BRABEVACNOR1",
                "data_com": "2022-04-01",
                "data_ex": EX.isoformat(),
                "fator": None,
                "motivo_sem_fator": "fator não conversível",
            }
        ],
    )
    assert retorno["abstencao"] == "fator não conversível"


def test_evento_sem_prova_sem_data_com_abstem(monkeypatch):
    retorno, *_ = _exec(monkeypatch, sem_prova_eventos=({"motivo": "datas ilegíveis"},))
    assert retorno["abstencao"] == "evento em ações sem prova no horizonte"


def test_fca_com_fim_de_negociacao_classifica_deslistagem(monkeypatch):
    from sentinela.data.referencia import universo

    class _Cadastro:
        columns = ("CNPJ_CIA", "MOTIVO_CANCEL")

        def to_dict(self, orient):
            assert orient == "records"
            return [{"CNPJ_CIA": "12.345.678/0001-90", "MOTIVO_CANCEL": "OPA"}]

    cnpj = "12345678000190"

    monkeypatch.setattr(
        universo,
        "_fca_por_referencia",
        lambda conn, corte: (
            (conn is executor.conn)
            and (corte == date.max.isoformat())
            and {
                (cnpj, "2022-12-31"): [
                    {
                        "Codigo_Negociacao": "ABEV3",
                        "Data_Fim_Negociacao": "2022-10-31",
                    }
                ]
            }
        ),
    )
    executor = BacktestPIT(
        _BancoRetornos([]), _Cadastro(), hoje=date(2026, 11, 13), cache_dir="cache"
    )
    assert executor._estado_terminal(cnpj, "ABEV3", T, False) == {
        "deslistagem": date(2022, 10, 31),
        "suspensao_confirmada": False,
        "motivo_deslistagem": "OPA",
    }


def test_motivo_cancelamento_normaliza_cnpj_e_preserva_cache():
    class _Cadastro:
        columns = ("CNPJ_CIA", "MOTIVO_CANCEL")

        def __init__(self):
            self.leituras = 0

        def to_dict(self, orient):
            self.leituras += 1
            assert orient == "records"
            return [
                {
                    "CNPJ_CIA": "12.345.678/0001-90",
                    "MOTIVO_CANCEL": "  OPA  ",
                }
            ]

    cadastro = _Cadastro()
    executor = BacktestPIT(
        _BancoRetornos([]), cadastro, hoje=date(2026, 11, 13), cache_dir="cache"
    )
    assert executor._motivo_cancelamento("12345678000190") == "OPA"
    assert executor._motivo_cancelamento("12.345.678/0001-90") == "OPA"
    assert executor._motivo_cancelamento("00000000000000") is None
    assert cadastro.leituras == 1


def test_fca_sem_fim_confirma_suspensao_e_falta_de_fca_permanece_desconhecida(
    monkeypatch,
):
    from sentinela.data.referencia import universo

    monkeypatch.setattr(
        universo,
        "_fca_por_referencia",
        lambda *a: {
            ("cnpj", "2023-03-31"): [
                {"Codigo_Negociacao": "ABEV3", "Data_Fim_Negociacao": ""}
            ]
        },
    )
    executor = BacktestPIT(
        _BancoRetornos([]), None, hoje=date(2026, 11, 13), cache_dir="cache"
    )
    assert executor._estado_terminal("cnpj", "ABEV3", T, False)["suspensao_confirmada"]
    assert executor._estado_terminal(None, "ABEV3", T, False) == {
        "deslistagem": None,
        "suspensao_confirmada": False,
        "motivo_deslistagem": None,
    }


def test_fca_com_fim_apos_horizonte_preserva_estado_listado(monkeypatch):
    from sentinela.data.referencia import universo

    executor = BacktestPIT(
        _BancoRetornos([]), None, hoje=date(2026, 11, 13), cache_dir="cache"
    )
    monkeypatch.setattr(
        universo,
        "_fca_por_referencia",
        lambda *_: {
            ("cnpj", "2023-12-31"): [
                {"Codigo_Negociacao": "ABEV3", "Data_Fim_Negociacao": "2024-01-31"}
            ]
        },
    )
    assert executor._estado_terminal("cnpj", "ABEV3", T, False) == {
        "deslistagem": None,
        "suspensao_confirmada": True,
        "motivo_deslistagem": None,
    }


@pytest.mark.parametrize(
    "linhas",
    [
        None,
        [{"Codigo_Negociacao": "ABEV4", "Data_Fim_Negociacao": ""}],
        [{"Codigo_Negociacao": "ABEV3", "Data_Fim_Negociacao": "data ilegível"}],
    ],
)
def test_fca_sem_status_demonstravel_nao_confirma_suspensao(monkeypatch, linhas):
    from sentinela.data.referencia import universo

    executor = BacktestPIT(
        _BancoRetornos([]), None, hoje=date(2026, 11, 13), cache_dir="cache"
    )
    monkeypatch.setattr(
        universo,
        "_fca_por_referencia",
        lambda *_: {("cnpj", "2023-12-31"): linhas},
    )
    assert executor._estado_terminal("cnpj", "ABEV3", T, False) == {
        "deslistagem": None,
        "suspensao_confirmada": False,
        "motivo_deslistagem": None,
    }


def test_fca_antigo_sem_fim_nao_comprova_status_no_horizonte(monkeypatch):
    from sentinela.data.referencia import universo

    executor = BacktestPIT(
        _BancoRetornos([]), None, hoje=date(2026, 11, 13), cache_dir="cache"
    )
    monkeypatch.setattr(
        universo,
        "_fca_por_referencia",
        lambda *_: {
            ("cnpj", "2022-12-31"): [
                {"Codigo_Negociacao": "ABEV3", "Data_Fim_Negociacao": ""}
            ]
        },
    )
    assert executor._estado_terminal("cnpj", "ABEV3", T, False) == {
        "deslistagem": None,
        "suspensao_confirmada": False,
        "motivo_deslistagem": None,
    }


def test_estado_de_abstencao_e_normalizacao_de_hash_sao_explicitos():
    assert _abstencao("motivo") == {
        "retorno": None,
        "abstencao": "motivo",
        "suspensao": False,
        "deslistada": False,
    }
    assert _normalizar_hash(
        {
            "data": date(2020, 1, 2),
            "hora": datetime(2020, 1, 2, 12, 30, tzinfo=UTC),
            "Coleta": "volátil",
            "data_coleta": "volátil",
            "valores": (1.0, float("nan"), Decimal("1.25")),
        }
    ) == {
        "data": "2020-01-02",
        "hora": "2020-01-02T12:30:00+00:00",
        "valores": [1.0, {"numero_nao_finito": "nan"}, "1.25"],
    }


def test_hash_canonico_usa_data_iso_e_chaves_ordenadas():
    assert BacktestPIT._hash({"value": 1, "data": D}) == (
        "8e85e530f07a8260f0d52e21507f59226a3c51f56ddfae01a354f37e7bb9641c"
    )
    assert BacktestPIT._hash({"data": D, "value": 1}) == BacktestPIT._hash(
        {"value": 1, "data": D}
    )


def test_preco_mantido_aplica_eventos_e_abstem_sem_preco_anterior():
    assert _preco_mantido(
        [(D, 10.0)],
        EX,
        [{"data_com": D, "data_ex": EX, "fator": 2.0}],
    ) == (5.0, None)
    assert _preco_mantido([], EX, []) == (None, f"sem preço para manter em {EX}")


def test_retorno_total_preserva_motivos_de_fronteira():
    invertido = retorno_total({}, inicio=T, fim=D)
    sem_entrada = retorno_total({}, inicio=D, fim=T)
    assert invertido["abstencao"] == "intervalo de retorno invertido"
    assert sem_entrada["abstencao"] == "fechamento de entrada indisponível"


def test_fim_horizonte_usa_ultimo_pregao_do_mes_alvo_ou_informa_lacuna():
    alvo1, alvo2 = date(2023, 3, 30), date(2023, 3, 31)
    # o pregão de abril fecha o mês de março (ficha §8, BUG-3-35)
    seguinte = date(2023, 4, 3)
    assert BacktestPIT._fim_horizonte(D, 12, [alvo1, alvo2, seguinte]) == (alvo2, None)
    assert BacktestPIT._fim_horizonte(D, 12, []) == (
        None,
        "horizonte sem pregão final carregado",
    )


@pytest.mark.parametrize(
    "datas,horizontes,modo,mensagem",
    [
        ([D], (12,), "futuro", "modo histórico desconhecido"),
        ([], (12,), "estrito", "datas deve conter datas locais de análise"),
        (
            [datetime(2022, 3, 31, tzinfo=UTC)],
            (12,),
            "estrito",
            "datas deve conter datas locais de análise",
        ),
        ([D], (6,), "estrito", "horizontes deve conter 12, 24 ou 36 meses"),
    ],
)
def test_executar_recusa_entradas_fora_do_contrato(datas, horizontes, modo, mensagem):
    executor = BacktestPIT(
        _BancoRetornos([]), None, hoje=date(2026, 11, 13), cache_dir="cache"
    )
    with pytest.raises(ValueError, match=mensagem):
        executor.executar(datas, horizontes=horizontes, modo=modo)


def test_hashes_fontes_pit_retem_os_hashes_de_cada_fonte_e_o_corte():
    class _BancoHashes:
        def __init__(self):
            self.consultas = []

        def execute(self, sql, parametros):
            self.consultas.append((sql, parametros))
            nome = next(
                nome
                for nome in (
                    "demonstracoes",
                    "composicao_capital",
                    "fca_linhas",
                    "fii_informe_linhas",
                    "series_macro",
                )
                if nome in sql
            )
            return [(f"hash-{nome}",)]

    banco = _BancoHashes()
    executor = BacktestPIT(banco, None, hoje=date(2026, 11, 13), cache_dir="cache")
    hashes = executor._hashes_fontes_pit("cnpj", D)
    assert hashes == {
        "demonstracoes": ["hash-demonstracoes"],
        "composicao": ["hash-composicao_capital"],
        "fca": ["hash-fca_linhas"],
        "informe_fii": ["hash-fii_informe_linhas"],
        "series_macro": ["hash-series_macro"],
    }
    assert len(banco.consultas) == 5
    assert all("?" in sql for sql, _ in banco.consultas)
    assert [parametros for _, parametros in banco.consultas] == [
        ("cnpj", D.isoformat(), D.isoformat()),
        ("cnpj", D.isoformat(), D.isoformat()),
        ("cnpj", D.isoformat(), D.isoformat()),
        ("cnpj", D.isoformat(), D.isoformat()),
        (D.isoformat(), D.isoformat()),
    ]


def test_grupos_e_resumo_preservam_cobertura_retorno_e_contexto_terminal():
    observacoes = []
    for i in range(25):
        observacoes.append(
            {
                "ticker": f"T{i:03d}3",
                "lente": "Gordon",
                "D": D.isoformat(),
                "fim": T.isoformat(),
                "horizonte": 12,
                "modo": "estrito",
                "distancia_ao_preco_pct": float(25 - i),
                "abstencao": None,
                "abstencao_retorno": "retorno sem prova" if i == 0 else None,
                "retorno_total": None if i == 0 else i / 100,
                "retorno_ibov": 0.2,
                "retorno_cdi": 0.1,
                "deslistada": i == 1,
                "motivo_deslistagem": "OPA" if i == 1 else None,
                "suspensao": i == 2,
            }
        )
    grupos = BacktestPIT._grupos(observacoes)
    assert len(grupos) == 1
    grupo = grupos[0]
    q1 = grupo["retornos_quintis"]["Q1"]
    assert grupo["elegiveis"] == 25
    assert grupo["quintis"][1] == [f"T{i:03d}3" for i in range(5)]
    assert q1["n_retorno"] == 4 and q1["n_sem_retorno"] == 1
    assert q1["retorno_medio_sem_deslistadas"] == pytest.approx(0.03)
    assert q1["n_retorno_sem_deslistadas"] == 3
    assert q1["n_deslistadas"] == q1["n_suspensas"] == 1
    assert q1["retorno_ibov"] == 0.2 and q1["retorno_cdi"] == 0.1
    resumo = BacktestPIT._resumir(observacoes, grupos, {24: 2})
    linha = resumo["lentes"][0]
    assert resumo["horizontes_incompletos"] == {24: 2}
    assert linha["universo_elegivel"] == linha["com_valor"] == 25
    assert linha["cobertura"] == 1
    assert linha["abstencoes_retorno"] == {"retorno sem prova": 1}
    assert linha["contagem_motivo_deslistagem"] == {"OPA": 1}
    assert linha["datas_com_quintis"] == 1
    assert linha["quintis"]["Q1"]["n_datas_com_retorno"] == 1
    assert linha["quintis"]["Q1"]["mediana_retorno_sem_deslistadas"] == pytest.approx(
        0.03
    )
    assert linha["quintis"]["Q1"][
        "primeiro_quartil_retorno_sem_deslistadas"
    ] == pytest.approx(0.03)
    assert linha["quintis"]["Q1"][
        "terceiro_quartil_retorno_sem_deslistadas"
    ] == pytest.approx(0.03)
    assert linha["quintis"]["Q1"]["media_retorno_sem_deslistadas"] == pytest.approx(
        0.03
    )
    assert linha["quintis"]["Q1"]["n_datas_sem_ibov"] == 0
    assert linha["q1_menos_q5"]["n_datas"] == 1


def test_resumo_informa_cobertura_abstencoes_e_quintis_por_data():
    observacoes = []
    membros = {q: [] for q in range(1, 6)}
    retornos_quintis = {}
    for i in range(25):
        ticker = f"T{i:03d}3"
        observacoes.append(
            {
                "ticker": ticker,
                "lente": "Gordon",
                "horizonte": 12,
                "modo": "estrito",
                "D": "2022-03-31",
                "fim": "2023-03-31",
                "abstencao": None,
                "abstencao_retorno": None,
                "retorno_total": i / 100,
                "retorno_ibov": 0.1,
                "retorno_cdi": 0.05,
            }
        )
    for q in range(1, 6):
        tickers = [f"T{i:03d}3" for i in range((q - 1) * 5, q * 5)]
        membros[q] = tickers
        valores = [i / 100 for i in range((q - 1) * 5, q * 5)]
        retornos_quintis[f"Q{q}"] = {
            "retorno_medio": sum(valores) / len(valores),
            "n_retorno": len(valores),
            "n_sem_retorno": 0,
            "retornos_ativos": valores,
            "retorno_ibov": 0.1,
            "retorno_cdi": 0.05,
            "n_deslistadas": 0,
            "n_suspensas": 0,
        }
    grupo = {
        "lente": "Gordon",
        "horizonte": 12,
        "modo": "estrito",
        "D": "2022-03-31",
        "quintis": membros,
        "retornos_quintis": retornos_quintis,
    }
    resumo = BacktestPIT._resumir(observacoes, [grupo], {})
    linha = resumo["lentes"][0]
    assert linha["cobertura"] == 1
    assert linha["datas_com_quintis"] == 1
    assert linha["quintis"]["Q1"]["n_datas_com_retorno"] == 1
    assert linha["quintis"]["Q1"]["n_ativos_por_data"] == {
        "minimo": 5,
        "mediana": 5,
        "maximo": 5,
    }
    assert linha["quintis"]["Q1"]["fracao_supera_ibov"] == 0
    assert linha["q1_menos_q5"]["n_datas"] == 1
    assert "score" not in resumo


def test_resumo_agrega_quartis_medias_e_motivos_em_varias_datas():
    dias = ("2022-03-31", "2022-06-30", "2022-09-30")
    medias_q1 = (0.01, 0.03, 0.09)
    medias_q5 = (0.12, 0.08, 0.02)
    benchmarks_ibov = (0.02, 0.02, 0.08)
    observacoes = []
    grupos = []
    for indice, dia in enumerate(dias):
        for ticker_indice in range(25):
            deslistada = ticker_indice == 0 and indice < 2
            observacoes.append(
                {
                    "ticker": f"T{ticker_indice:03d}3",
                    "lente": "Gordon",
                    "D": dia,
                    "fim": "2023-03-31",
                    "horizonte": 12,
                    "modo": "estrito",
                    "distancia_ao_preco_pct": float(ticker_indice),
                    "abstencao": None,
                    "abstencao_retorno": None,
                    "retorno_total": medias_q1[indice],
                    "retorno_ibov": benchmarks_ibov[indice],
                    "retorno_cdi": 0.04,
                    "deslistada": deslistada,
                    "motivo_deslistagem": (
                        ("OPA", "INCORPORACAO")[indice] if deslistada else None
                    ),
                    "suspensao": False,
                }
            )
        grupos.append(
            {
                "lente": "Gordon",
                "D": dia,
                "fim": "2023-03-31",
                "horizonte": 12,
                "modo": "estrito",
                "quintis": {
                    numero: [f"T{i:03d}3" for i in range((numero - 1) * 5, numero * 5)]
                    for numero in range(1, 6)
                },
                "retornos_quintis": {
                    "Q1": {
                        "retorno_medio": medias_q1[indice],
                        "retorno_medio_sem_deslistadas": medias_q1[indice],
                        "retornos_ativos": [medias_q1[indice]],
                        "retorno_ibov": benchmarks_ibov[indice],
                        "retorno_cdi": 0.04,
                        "n_deslistadas": int(indice < 2),
                        "n_suspensas": 0,
                    },
                    "Q5": {
                        "retorno_medio": medias_q5[indice],
                        "retorno_medio_sem_deslistadas": medias_q5[indice],
                        "retornos_ativos": [medias_q5[indice]],
                        "retorno_ibov": benchmarks_ibov[indice],
                        "retorno_cdi": 0.04,
                        "n_deslistadas": 0,
                        "n_suspensas": 0,
                    },
                },
            }
        )

    linha = BacktestPIT._resumir(observacoes, grupos, {})["lentes"][0]
    q1 = linha["quintis"]["Q1"]
    assert q1["mediana_retorno_sem_deslistadas"] == pytest.approx(0.03)
    assert q1["primeiro_quartil_retorno_sem_deslistadas"] == pytest.approx(0.02)
    assert q1["terceiro_quartil_retorno_sem_deslistadas"] == pytest.approx(0.06)
    assert q1["media_retorno_sem_deslistadas"] == pytest.approx(0.13 / 3)
    assert q1["n_datas_com_retorno_sem_deslistadas"] == 3
    assert q1["fracao_supera_ibov"] == pytest.approx(2 / 3)
    assert q1["n_deslistadas"] == 2
    assert linha["contagem_motivo_deslistagem"] == {"OPA": 1, "INCORPORACAO": 1}
    assert linha["q1_menos_q5"] == {"mediana": pytest.approx(-0.05), "n_datas": 3}


def test_hashes_fontes_pit_selecionam_so_hashes_elegiveis():
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.executescript(
        "CREATE TABLE demonstracoes(cnpj, documento, dt_refer, versao, dt_fim_exerc, hash_sha256);"
        "CREATE TABLE entregas(cnpj, documento, dt_refer, versao, dt_receb);"
        "CREATE TABLE composicao_capital(cnpj, documento, dt_refer, versao, hash_sha256);"
        "CREATE TABLE fca_linhas(cnpj, dt_refer, versao, hash_sha256);"
        "CREATE TABLE fca_entregas(cnpj, dt_refer, versao, dt_receb);"
        "CREATE TABLE fii_informe_linhas(cnpj, data_entrega, dt_refer, hash_sha256);"
        "CREATE TABLE series_macro(data, divulgacao, hash_sha256);"
    )
    executor = BacktestPIT(conn, None, hoje=date(2026, 11, 13), cache_dir="cache")
    assert executor._hashes_fontes_pit("CNPJ", D) == {
        "demonstracoes": [],
        "composicao": [],
        "fca": [],
        "informe_fii": [],
        "series_macro": [],
    }
    assert executor._hashes_fontes_pit(None, D) == {
        "abstencao": "CNPJ não demonstrado na análise"
    }


def test_hash_exclui_reconstrucao_variavel_sem_descartar_conteudo():
    dados = {
        "proveniencia": {"data_coleta": "agora", "hash_sha256": "zip derivado"},
        "valor": 10,
        "coleta": "agora",
    }
    assert BacktestPIT._sem_proveniencia_instavel(dados) == {"valor": 10}
    assert BacktestPIT._hash({"fonte": "A", "valor": 10}) != BacktestPIT._hash(
        {"fonte": "A", "valor": 11}
    )
