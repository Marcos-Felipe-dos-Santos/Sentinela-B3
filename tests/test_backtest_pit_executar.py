"""F3-8b: `BacktestPIT.executar` com universo de 29 ativos e duas datas D.

O serviço, o universo e as fontes de proventos e benchmarks são substituídos por
dublês na borda; preços e calendário vêm da tabela `precos` real (migrações).
Os esperados são contas à mão pela ficha (docs/metodologia/backtest.md):
quintis por ceil(5i/n) (§4), retorno entre fechamentos de D e T com deslistagem
pelo CDI em [L, T) e suspensão pelo último preço (§5), benchmarks do fechamento
de D ao de T (§6), relatório do §7 e janela incompleta do §8.
"""

import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime, time
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from backtesting.backtest_pit import BacktestPIT
from sentinela.data.providers import b3_indices, b3_proventos
from sentinela.data.referencia import universo
from sentinela.data.store import migracoes, resultados

FUSO = ZoneInfo("America/Sao_Paulo")
HOJE = date(2026, 11, 13)
D1, D2 = date(2022, 3, 31), date(2022, 4, 29)
MEIO = date(2022, 9, 30)
T1, T2 = date(2023, 3, 31), date(2023, 4, 28)
DESLISTADO, SUSPENSO, SEM_VALOR, MEIO_REAL = 3, 7, 26, 24
TICKERS = [f"TK{chr(65 + i // 26)}{chr(65 + i % 26)}3" for i in range(27)]
SEM_REGISTRO_COM_ERRO, SEM_REGISTRO = "TKZZ3", "TKZY3"
MOTIVO_BAZIN = "DY abaixo do critério de 6%"


def _linha_preco(conn, dia, ticker, centavos, fator=1):
    conn.execute(
        "INSERT INTO precos (data, codigo_negociacao, tipo_mercado, codbdi, prazo, "
        "especificacao, isin, abertura_centavos, maxima_centavos, minima_centavos, "
        "media_centavos, fechamento_centavos, negocios, quantidade, volume_centavos, "
        "fator_cotacao, fonte, coleta, hash_sha256) "
        "VALUES (?, ?, '010', '02', '', 'ON', ?, ?, ?, ?, ?, ?, 1, 1, 1, ?, "
        "'sintético', '2026-11-13T15:00:00+00:00', 'h')",
        (
            dia.isoformat(),
            ticker,
            f"BR{ticker[:4]}ACNOR1",
            *(centavos,) * 5,
            fator,
        ),
    )


def _carregar_precos(conn, deslocamento_t2=0):
    for i, ticker in enumerate(TICKERS):
        fator = 1000 if i == 0 else 1
        # entrada a R$ 10,00 nas duas datas; retorno i/100 até T1 e i/50 até T2
        for dia, centavos in (
            (D1, 1000),
            (D2, 1000),
            (MEIO, 1100 if i == DESLISTADO else 1200 if i == SUSPENSO else 1000),
            (T1, 1000 + 10 * i),
            (T2, 1000 + 20 * i + deslocamento_t2),
        ):
            if i == DESLISTADO and dia > MEIO:
                continue
            if i == SUSPENSO and dia > MEIO:
                continue
            _linha_preco(conn, dia, ticker, centavos * fator, fator)
    # pregão de maio fecha o mês de T2 (ficha §8, BUG-3-35)
    _linha_preco(conn, date(2023, 5, 31), TICKERS[1], 1000)


def _registro(ticker, as_of, metodo, execucao, resultado=None, motivo=None, versao="1"):
    return resultados.Registro(
        id=0,
        ticker=ticker,
        as_of=as_of.isoformat(),
        metodo=metodo,
        versao=versao,
        execucao_id=execucao,
        tipo="original",
        resultado=resultado,
        motivo_abstencao=motivo,
        hash_resultado="h",
        proveniencia={},
    )


class _Cenario:
    """Dublês da borda; cada execução registra o que recebeu."""

    def __init__(self, monkeypatch, conn):
        self.conn = conn
        self.servicos = []
        self.analises = []
        self.buscas = []
        self.estados = []
        self.universos = []
        self.raw_extra = {}
        self.premissas = "premissa A"
        self.motivo_bazin = MOTIVO_BAZIN
        self.fora = [{"ticker": "TKFORA3", "motivo": "liquidez"}]
        self.cdi_t1 = True
        cenario = self

        class _Servico:
            def __init__(self, *args, **kwargs):
                cenario.servicos.append((args, kwargs))

            def analisar(self, ticker, as_of, use_ai="padrão"):
                cenario.analises.append((ticker, as_of, use_ai))
                erro = (
                    "histórico sem cadastro"
                    if ticker == SEM_REGISTRO_COM_ERRO
                    else None
                )
                raw = {
                    "preco_atual": 9.9,
                    "cnpj": f"cnpj-{ticker}",
                    "setor": "Bebidas",
                    **cenario.raw_extra,
                }
                return SimpleNamespace(
                    raw=raw, execucao_id=f"exec-{ticker}-{as_of.date()}", error=erro
                )

        def buscar(conn, ticker, *, as_of=None):
            cenario.buscas.append((ticker, as_of))
            if ticker in (SEM_REGISTRO, SEM_REGISTRO_COM_ERRO):
                return []
            i = TICKERS.index(ticker)
            atual = f"exec-{ticker}-{as_of.date()}"
            valor = 0 if i == SEM_VALOR else 0.5 if i == MEIO_REAL else 20
            graham = {
                "valor": valor,
                "distancia_ao_preco_pct": 50 - i,
                "versao": "2.1.0",
                "premissas": cenario.premissas,
                "proveniencia": {"coleta": "variável"},
            }
            return [
                _registro(
                    ticker, as_of, "Graham", "exec-antiga", {**graham, "valor": 99}
                ),
                _registro(ticker, as_of, "Graham", atual, graham, versao="2.1.0"),
                _registro(
                    ticker,
                    as_of,
                    "Bazin",
                    atual,
                    motivo=cenario.motivo_bazin,
                    versao="2.0.0",
                ),
            ]

        def universo_backtest(conn, dia, cadastro, **kwargs):
            cenario.universos.append((dia, cadastro, kwargs))
            elegiveis = [
                {"ticker": t, "cnpj": f"cnpj-{t}", "classe": "STOCK"}
                for t in [*TICKERS, SEM_REGISTRO_COM_ERRO, SEM_REGISTRO]
            ]
            return {
                "elegiveis": elegiveis,
                "fora": cenario.fora,
                "sem_identificacao": [],
            }

        def benchmarks_ate(conn, serie, dia):
            assert dia == date.max
            if serie == "IBOV":
                return [
                    {"data": D1.isoformat(), "valor": 100000.0},
                    {"data": D2.isoformat(), "valor": 105000.0},
                    {"data": T1.isoformat(), "valor": 110000.0},
                ]
            taxas = [
                (date(2022, 3, 30), 9.0),
                (D1, 0.04),
                (date(2022, 4, 1), 0.02),
                (D2, 0.03),
                (MEIO, 0.05),
                (T1, 0.5),
            ]
            return [
                {"data": d.isoformat(), "valor": v}
                for d, v in taxas
                if d != T1 or cenario.cdi_t1
            ]

        def estado(executor, cnpj, ticker, fim, preco_final):
            cenario.estados.append((cnpj, ticker, fim, preco_final))
            if ticker == TICKERS[DESLISTADO]:
                return {
                    "deslistagem": MEIO,
                    "suspensao_confirmada": False,
                    "motivo_deslistagem": "OPA",
                }
            return {
                "deslistagem": None,
                "suspensao_confirmada": ticker == TICKERS[SUSPENSO],
                "motivo_deslistagem": None,
            }

        from sentinela.services import analyze_asset, historico

        self.motores = []
        monkeypatch.setattr(analyze_asset, "AnalysisService", _Servico)
        monkeypatch.setattr(resultados, "buscar", buscar)
        monkeypatch.setattr(universo, "universo_backtest", universo_backtest)
        monkeypatch.setattr(b3_indices, "benchmarks_ate", benchmarks_ate)
        monkeypatch.setattr(
            historico,
            "MotorHistorico",
            lambda *a, **k: cenario.motores.append((a, k)) or "motor",
        )
        monkeypatch.setattr(
            b3_proventos,
            "proventos_ate",
            lambda *a, **k: {"proventos": [], "sem_prova": []},
        )
        monkeypatch.setattr(
            b3_proventos,
            "eventos_ate",
            lambda *a, **k: {"eventos": [], "sem_prova": []},
        )
        monkeypatch.setattr(BacktestPIT, "_estado_terminal", estado)

    def executar(self, **kwargs):
        executor = BacktestPIT(self.conn, "cadastro", hoje=HOJE, cache_dir="pit")
        return executor.executar([D2, D1], horizontes=(12, 24), **kwargs)


@pytest.fixture
def cenario(monkeypatch):
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        _carregar_precos(conn)
        yield _Cenario(monkeypatch, conn)


def _obs(saida, ticker, dia, lente="Graham", horizonte=12):
    return next(
        o
        for o in saida["observacoes"]
        if (o["ticker"], o["D"], o["lente"], o["horizonte"])
        == (ticker, dia.isoformat(), lente, horizonte)
    )


def _cdi(*taxas):
    fator = 1.0
    for taxa in taxas:
        fator *= 1 + taxa / 100
    return fator - 1


def test_executar_liga_servico_universo_e_motor_historico_pela_data(cenario):
    from config import MACRO
    from fii_engine import FIIEngine

    cenario.executar()
    as_of_d1 = datetime.combine(D1, time.max, tzinfo=FUSO)
    assert cenario.universos[0][0] == D1 and cenario.universos[1][0] == D2
    assert cenario.universos[0][1] == "cadastro"
    assert cenario.universos[0][2] == {
        "presenca_min": MACRO.LIQUIDEZ_PRESENCA_MIN,
        "volume_acoes_min": MACRO.LIQUIDEZ_VOLUME_ACOES_MIN,
        "volume_fii_min": MACRO.LIQUIDEZ_VOLUME_FII_MIN,
    }
    args, kwargs = cenario.servicos[0]
    assert args[0] is None and isinstance(args[2], FIIEngine)
    assert kwargs["hoje"] == HOJE and kwargs["conexao_resultados"] is cenario.conn
    # D17: IA desligada na análise de data passada; as_of = fim do dia local de D
    assert (TICKERS[0], as_of_d1, False) in cenario.analises
    assert all(use_ai is False for *_, use_ai in cenario.analises)
    assert (TICKERS[0], as_of_d1) in cenario.buscas
    # 01:00 UTC de 01/04 ainda é 31/03 em São Paulo: a pasta do motor é a do dia local
    instante = datetime(2022, 4, 1, 1, tzinfo=UTC)
    assert kwargs["motor_historico"](instante) == "motor"
    a, k = cenario.motores[-1]
    assert a[0] is cenario.conn and a[1] == instante and a[3] == "cadastro"
    assert a[2].as_posix() == "pit/2022-03-31"
    assert k == {"modo": "estrito"}
    # o CNPJ do universo em D chega ao estado terminal
    assert (f"cnpj-{TICKERS[5]}", TICKERS[5], T1, True) in cenario.estados
    assert (
        f"cnpj-{TICKERS[SUSPENSO]}",
        TICKERS[SUSPENSO],
        T1,
        False,
    ) in cenario.estados


def test_executar_no_modo_exploratorio_passa_o_modo_ao_motor(cenario):
    saida = cenario.executar(modo="exploratorio")
    _, kwargs = cenario.servicos[0]
    kwargs["motor_historico"](datetime(2022, 3, 31, 12, tzinfo=UTC))
    assert cenario.motores[-1][1] == {"modo": "exploratorio"}
    assert {o["modo"] for o in saida["observacoes"]} == {"exploratorio"}
    grupo = next(g for g in saida["grupos"] if g["lente"] == "Graham")
    assert grupo["aviso"] == "possível reapresentação posterior não observável"


def test_observacoes_carregam_lente_retorno_benchmarks_e_estado(cenario):
    saida = cenario.executar()
    normal = _obs(saida, TICKERS[5], D1)
    assert normal == {
        "ticker": TICKERS[5],
        "lente": "Graham",
        "versao": "2.1.0",
        "D": "2022-03-31",
        "fim": "2023-03-31",
        "horizonte": 12,
        "modo": "estrito",
        "preco_lente": 9.9,
        "preco_entrada": 10.0,
        "valor": 20,
        "distancia_ao_preco_pct": 45,
        "abstencao": None,
        "retorno_total": pytest.approx(0.05),
        "abstencao_retorno": None,
        "retorno_ibov": pytest.approx(0.1),
        # [D1, T1): 31/03, 01/04 (dia bancário sem pregão), 29/04 e 30/09
        "retorno_cdi": pytest.approx(_cdi(0.04, 0.02, 0.03, 0.05)),
        "suspensao": False,
        "deslistada": False,
        "motivo_deslistagem": None,
    }
    # cotação na unidade de FATCOT = 1000: preço = centavos / 100 / 1000
    assert _obs(saida, TICKERS[0], D1)["preco_entrada"] == pytest.approx(10.0)
    assert _obs(saida, TICKERS[0], D1)["retorno_total"] == pytest.approx(0.0)
    # valor 0,5 é finito e positivo: a lente vale
    assert _obs(saida, TICKERS[MEIO_REAL], D1)["abstencao"] is None
    assert _obs(saida, TICKERS[MEIO_REAL], D1)["valor"] == 0.5
    sem_valor = _obs(saida, TICKERS[SEM_VALOR], D1)
    assert sem_valor["abstencao"] == "lente sem valor finito e positivo"
    assert sem_valor["valor"] is None and sem_valor["distancia_ao_preco_pct"] is None
    bazin = _obs(saida, TICKERS[5], D1, lente="Bazin")
    assert bazin["abstencao"] == MOTIVO_BAZIN and bazin["versao"] == "2.0.0"
    assert bazin["valor"] is None and bazin["distancia_ao_preco_pct"] is None
    assert bazin["retorno_total"] == pytest.approx(0.05)
    # deslistagem em 30/09: 11/10 e CDI de [30/09, 31/03) só no pregão de 30/09
    deslistado = _obs(saida, TICKERS[DESLISTADO], D1)
    assert deslistado["retorno_total"] == pytest.approx(1.1 * 1.0005 - 1)
    assert deslistado["deslistada"] is True and deslistado["suspensao"] is False
    assert deslistado["motivo_deslistagem"] == "OPA"
    suspenso = _obs(saida, TICKERS[SUSPENSO], D1)
    assert suspenso["retorno_total"] == pytest.approx(0.2)
    assert suspenso["suspensao"] is True and suspenso["deslistada"] is False
    # D2: Ibovespa sem fechamento em T2; CDI sem a taxa do pregão de 31/03/2023
    cenario.cdi_t1 = False
    saida = cenario.executar()
    d2 = _obs(saida, TICKERS[5], D2)
    assert d2["fim"] == "2023-04-28" and d2["retorno_total"] == pytest.approx(0.1)
    assert d2["retorno_ibov"] is None and d2["retorno_cdi"] is None
    sem_cdi = _obs(saida, TICKERS[DESLISTADO], D2)
    assert sem_cdi["retorno_total"] is None
    assert sem_cdi["abstencao_retorno"] == "CDI indisponível no pregão 2023-03-31"
    assert sem_cdi["deslistada"] is False


def test_analise_sem_registro_fica_fora_das_lentes_com_o_motivo(cenario):
    """BUG-3-56: sem lente registrada, a análise vai para `sem_lentes`, sem pseudo-lente."""
    saida = cenario.executar()
    sem_lentes = {(s["ticker"], s["D"]): s for s in saida["sem_lentes"]}
    com_erro = sem_lentes[(SEM_REGISTRO_COM_ERRO, D1.isoformat())]
    assert com_erro["motivo"] == "histórico sem cadastro"
    assert com_erro["classe"] == "STOCK"
    assert sem_lentes[(SEM_REGISTRO, D1.isoformat())]["motivo"] == "análise sem lentes"
    sem_obs = {SEM_REGISTRO, SEM_REGISTRO_COM_ERRO}
    assert not [o for o in saida["observacoes"] if o["ticker"] in sem_obs]


def test_quintis_e_relatorio_por_lente_com_contas_a_mao(cenario):
    cenario.cdi_t1 = False
    saida = cenario.executar()
    grupos = {(g["lente"], g["D"]): g for g in saida["grupos"]}
    # Bazin abstém em tudo: grupo sem quintis, só com as abstenções (BUG-3-56); Graham
    # forma quintis nas duas datas
    assert {lente for lente, _ in grupos} == {"Graham", "Bazin"}
    g1 = grupos[("Graham", "2022-03-31")]
    assert (
        g1["fim"] == "2023-03-31" and g1["horizonte"] == 12 and g1["modo"] == "estrito"
    )
    # n = 26 (o índice 26 abstém): posições 1–5, 6–10, 11–15, 16–20 e 21–26
    assert g1["elegiveis"] == 26
    assert g1["quintis"][1] == TICKERS[0:5] and g1["quintis"][5] == TICKERS[20:26]
    assert g1["abstencoes"] == {"lente sem valor finito e positivo": 1}  # BUG-3-56
    q1, q2, q5 = (g1["retornos_quintis"][q] for q in ("Q1", "Q2", "Q5"))
    r3 = 1.1 * 1.0005 - 1
    assert q1["retorno_medio"] == pytest.approx((0 + 0.01 + 0.02 + r3 + 0.04) / 5)
    assert q1["retorno_medio_sem_deslistadas"] == pytest.approx(0.07 / 4)
    assert q1["n_retorno"] == 5 and q1["n_retorno_sem_deslistadas"] == 4
    assert q1["n_deslistadas"] == 1 and q2["n_suspensas"] == 1
    assert q5["retorno_medio"] == pytest.approx(135 / 600)
    g2 = grupos[("Graham", "2022-04-29")]
    q1b = g2["retornos_quintis"]["Q1"]
    assert q1b["retorno_medio"] == pytest.approx(0.14 / 4)
    assert q1b["n_sem_retorno"] == 1 and q1b["n_retorno"] == 4
    assert q1b["retorno_ibov"] is None and q1b["retorno_cdi"] is None

    resumo = saida["resumo"]
    # §8: horizonte de 24 meses sem pregão final, contado por lente de cada ativo
    # (sem a pseudo-lente "analise" dos dois ativos sem lente, BUG-3-56)
    assert resumo["horizontes_incompletos"] == {24: 2 * (27 * 2)}
    linha = next(
        r
        for r in resumo["lentes"]
        if (r["lente"], r["horizonte"], r["modo"]) == ("Graham", 12, "estrito")
    )
    # BUG-3-62: as duas ações sem lente de cada data entram no universo elegível
    assert linha["universo_elegivel"] == 58 and linha["com_valor"] == 52
    assert linha["cobertura"] == pytest.approx(52 / 58)
    assert linha["abstencoes"] == {"lente sem valor finito e positivo": 2}
    assert linha["abstencoes_retorno"] == {"CDI indisponível no pregão 2023-03-31": 1}
    assert linha["contagem_motivo_deslistagem"] == {"OPA": 1}
    assert linha["datas_com_quintis"] == 2
    assert linha["ultima_data_D_horizonte_completo"] == "2022-04-29"
    a, b = (0 + 0.01 + 0.02 + r3 + 0.04) / 5, 0.035
    rq1 = linha["quintis"]["Q1"]
    assert rq1["mediana_retorno"] == pytest.approx((a + b) / 2)
    assert rq1["media_retorno"] == pytest.approx((a + b) / 2)
    assert rq1["primeiro_quartil_retorno"] == pytest.approx(a + (b - a) * 0.25)
    assert rq1["terceiro_quartil_retorno"] == pytest.approx(a + (b - a) * 0.75)
    assert rq1["mediana_retorno_sem_deslistadas"] == pytest.approx((0.0175 + 0.035) / 2)
    assert rq1["n_datas_com_retorno"] == 2
    # D1: Q1 abaixo do Ibovespa (10%) e acima do CDI; D2 sem nenhum dos dois
    assert rq1["fracao_supera_ibov"] == 0 and rq1["n_datas_com_ibov"] == 1
    assert rq1["fracao_supera_cdi"] == 1 and rq1["n_datas_com_cdi"] == 1
    assert rq1["n_datas_sem_ibov"] == 1 and rq1["n_datas_sem_cdi"] == 1
    assert rq1["n_ativos_por_data"] == {"minimo": 5, "mediana": 5, "maximo": 5}
    assert linha["quintis"]["Q5"]["n_ativos_por_data"] == {
        "minimo": 6,
        "mediana": 6,
        "maximo": 6,
    }
    # IQR dentro do Q1: D1 [0; 0,01; 0,02; 0,04; r3] → 0,04 − 0,01;
    # D2 [0; 0,02; 0,04; 0,08] → (0,04 + 0,25 × 0,04) − 0,75 × 0,02
    assert rq1["dispersao_iqr_mediana"] == pytest.approx((0.03 + 0.035) / 2)
    assert rq1["n_deslistadas"] == 1
    assert linha["quintis"]["Q2"]["n_suspensas"] == 2
    assert linha["q1_menos_q5"] == {
        "mediana": pytest.approx(((a - 0.225) + (b - 0.45)) / 2),
        "n_datas": 2,
    }
    bazin = next(
        r for r in resumo["lentes"] if (r["lente"], r["horizonte"]) == ("Bazin", 12)
    )
    assert bazin["abstencoes"] == {MOTIVO_BAZIN: 54}
    assert bazin["com_valor"] == 0 and bazin["datas_com_quintis"] == 0
    assert bazin["quintis"]["Q1"]["mediana_retorno"] is None
    assert set(linha["quintis"]) == {"Q1", "Q2", "Q3", "Q4", "Q5"}


def test_hash_dos_insumos_acompanha_as_fontes_e_ignora_a_coleta(cenario, monkeypatch):
    base = cenario.executar()
    assert cenario.executar()["hash_insumos"] == base["hash_insumos"]

    cenario.raw_extra = {
        "historico": "série refeita",
        "fontes": {"yfinance": "outra"},
        "coleta": "2026-11-14",
        "detalhe": {"data_coleta": "agora", "proveniencia": "x", "hash_sha256": "y"},
        "lista": [{"coleta": "ontem", "v": 1}],
    }
    instavel = cenario.executar()
    cenario.raw_extra = {"detalhe": {}, "lista": [{"v": 1}]}
    estavel = cenario.executar()
    assert instavel["hash_insumos"] == estavel["hash_insumos"]
    assert estavel["hash_insumos"] != base["hash_insumos"]
    assert estavel["hash_resultado"] == base["hash_resultado"]
    cenario.raw_extra = {}

    cenario.fora = [{"ticker": "TKFORA3", "motivo": "presença abaixo de 80%"}]
    universo_novo = cenario.executar()
    assert universo_novo["hash_insumos"] != base["hash_insumos"]
    assert universo_novo["hash_resultado"] == base["hash_resultado"]
    cenario.fora = [{"ticker": "TKFORA3", "motivo": "liquidez"}]

    cenario.premissas = "premissa B"
    premissa = cenario.executar()
    assert premissa["hash_insumos"] != base["hash_insumos"]
    assert premissa["hash_resultado"] == base["hash_resultado"]
    cenario.premissas = "premissa A"

    cenario.motivo_bazin = "outro motivo"
    assert cenario.executar()["hash_insumos"] != base["hash_insumos"]
    cenario.motivo_bazin = MOTIVO_BAZIN

    cenario.conn.execute(
        "INSERT INTO series_macro VALUES ('IPCA', '2021-12-01', 0.73, '2022-01-11', "
        "'{}', 'IBGE', '2026-11-13', 'hash-ipca')"
    )
    macro = cenario.executar()
    assert macro["hash_insumos"] != base["hash_insumos"]
    assert macro["hash_resultado"] == base["hash_resultado"]
    fonte = next(
        f for f in _fontes(cenario, monkeypatch) if f.get("ticker") == TICKERS[1]
    )
    assert fonte["hashes_fontes_pit"]["series_macro"] == ["hash-ipca"]


def _fontes(cenario, monkeypatch):
    """As fontes que a execução entrega ao hash dos insumos."""
    capturadas = []
    original = BacktestPIT._hash

    def capturar(valor):
        if isinstance(valor, list) and valor and "universo" in valor[0]:
            capturadas.append(valor)
        return original(valor)

    monkeypatch.setattr(BacktestPIT, "_hash", staticmethod(capturar))
    cenario.executar()
    monkeypatch.setattr(BacktestPIT, "_hash", staticmethod(original))
    fontes = capturadas[0]
    assert fontes[0] == {
        "D": "2022-03-31",
        "universo": {
            "elegiveis": fontes[0]["universo"]["elegiveis"],
            "fora": cenario.fora,
            "sem_identificacao": [],
        },
    }
    return fontes


def test_fontes_registram_analise_e_hash_de_cada_lente(cenario, monkeypatch):
    fontes = _fontes(cenario, monkeypatch)
    analise = next(
        f
        for f in fontes
        if f.get("tipo") == "analise_por_as_of" and f["ticker"] == TICKERS[1]
    )
    assert analise["D"] == "2022-03-31"
    assert analise["dados"] == {
        "preco_atual": 9.9,
        "cnpj": f"cnpj-{TICKERS[1]}",
        "setor": "Bebidas",
    }
    assert set(analise["hashes_fontes_pit"]) == {
        "demonstracoes",
        "composicao",
        "fca",
        "informe_fii",
        "series_macro",
    }
    metodos = [(m, v) for m, v, _ in analise["hashes_resultado_lente"]]
    assert metodos == [("Bazin", "2.0.0"), ("Graham", "2.1.0")]
    bazin_hash = analise["hashes_resultado_lente"][0][2]
    assert bazin_hash == BacktestPIT._hash({"abstencao": MOTIVO_BAZIN})
    graham_hash = analise["hashes_resultado_lente"][1][2]
    assert graham_hash == BacktestPIT._hash(
        {
            "valor": 20,
            "distancia_ao_preco_pct": 49,
            "versao": "2.1.0",
            "premissas": "premissa A",
        }
    )


def test_hash_do_resultado_muda_com_o_preco_final(cenario, monkeypatch):
    base = cenario.executar()
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        _carregar_precos(conn, deslocamento_t2=5)
        outro = _Cenario(monkeypatch, conn).executar()
    assert outro["hash_resultado"] != base["hash_resultado"]
    assert set(base) == {
        "hash_insumos",
        "hash_resultado",
        "observacoes",
        "sem_lentes",
        "grupos",
        "resumo",
    }
    assert len(base["hash_resultado"]) == len(base["hash_insumos"]) == 64


@pytest.mark.parametrize(
    "datas,mensagem",
    [
        ([HOJE], "data de análise precisa ser anterior a hoje"),
        ([date(2022, 4, 2)], "D precisa ser pregão carregado: 2022-04-02"),
        ([], "datas deve conter datas locais de análise"),
    ],
    ids=["hoje", "dia_sem_pregao", "sem_datas"],
)
def test_executar_recusa_data_com_mensagem_exata(cenario, datas, mensagem):
    executor = BacktestPIT(cenario.conn, "cadastro", hoje=HOJE, cache_dir="pit")
    with pytest.raises(ValueError) as erro:
        executor.executar(datas)
    assert str(erro.value) == mensagem


def test_executar_recusa_horizonte_fora_do_contrato_com_mensagem_exata(cenario):
    executor = BacktestPIT(cenario.conn, "cadastro", hoje=HOJE, cache_dir="pit")
    with pytest.raises(ValueError) as erro:
        executor.executar([D1], horizontes=(6,))
    assert str(erro.value) == "horizontes deve conter 12, 24 ou 36 meses"


def test_executar_sem_modo_usa_o_estrito(cenario):
    executor = BacktestPIT(cenario.conn, "cadastro", hoje=HOJE, cache_dir="pit")
    saida = executor.executar([D1], horizontes=(12,))
    assert {o["modo"] for o in saida["observacoes"]} == {"estrito"}


def test_registro_substituido_nao_entra(cenario):
    # o registro da execução antiga (valor 99) nunca chega à observação
    saida = cenario.executar()
    assert all(o["valor"] != 99 for o in saida["observacoes"])
