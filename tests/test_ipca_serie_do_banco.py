"""F3-8f: IPCA de fim de exercício das janelas pelo `series_macro`, no motor histórico.

A conta é a de `MacroProvider.ipca_serie` (`macro.indices_ipca`), sobre a agenda do IBGE e os
meses do SIDRA gravados pelo produtor de sempre (`macro.gravar_series`); só entra mês com data
de divulgação guardada e anterior ao dia de D (decisão 31). Sem linha, abstém com motivo.
Dados no formato oficial do IBGE, com valores sintéticos (1% ao mês); não são dados do mercado.
"""

import json
import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime

import pytest
from apoio_janelas import enriquecer_janelas
from test_macro_ipca_serie import cenario
from test_servico_historico import CADASTRO

from market_engine import MarketEngine
from sentinela.data.providers import macro, tesouro
from sentinela.data.store import migracoes
from sentinela.services import historico

COLETA = datetime(2026, 3, 1, 12, tzinfo=UTC)
D = datetime(2026, 3, 2, 15, tzinfo=UTC)
JANELA = (date(2021, 12, 1), date(2025, 12, 31))
SIDRA = "https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/63/p/202112-202512?formato=json"


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _provedor(monkeypatch, linhas, eventos, hash_sha256="c" * 64):
    """IBGE e SIDRA pelo conteúdo dado; as outras famílias falham e ficam no resumo."""
    provedor = macro.MacroProvider()

    def baixar(url, instante):
        if url == macro.IBGE_CALENDARIO:
            conteudo = {"items": eventos}
        elif "apisidra" in url:
            conteudo = linhas
        else:
            raise OSError("família fora deste teste")
        return macro.SnapshotMacro(
            json.dumps(conteudo), url, instante.isoformat(), hash_sha256
        )

    def sem_tesouro(self, instante):
        raise OSError("Tesouro fora deste teste")

    monkeypatch.setattr(provedor, "baixar", baixar)
    monkeypatch.setattr(tesouro.TesouroProvider, "baixar", sem_tesouro)
    return provedor


def _gravar(conn, monkeypatch, linhas, eventos, *, coleta=COLETA, **kw):
    provedor = _provedor(monkeypatch, linhas, eventos, **kw)
    resumo = macro.gravar_series(
        conn, provedor, coleta=coleta, datas=[coleta.date()], janela=JANELA
    )
    assert isinstance(resumo["ipca"], int) and resumo["ipca"] > 0, resumo
    return provedor


def test_banco_da_a_mesma_serie_do_caminho_do_sidra(conn, monkeypatch):
    exercicios, linhas, eventos = cenario()
    provedor = _gravar(conn, monkeypatch, linhas, eventos)
    do_banco = macro.ipca_serie_do_banco(conn, exercicios, D)
    do_sidra = provedor.ipca_serie(exercicios, D)
    assert "abstencao" not in do_banco, do_banco
    assert do_banco["indices"] == pytest.approx(do_sidra["indices"])
    assert do_banco["indices"]["2021-12"] == 1.0
    assert do_banco["indices"]["2025-12"] == pytest.approx(1.01**48)
    assert do_banco["publicacoes"] == do_sidra["publicacoes"]
    assert do_banco["fonte"] == SIDRA
    assert do_banco["coleta"] == COLETA.isoformat()
    assert do_banco["proveniencia"] == {
        "fonte": SIDRA,
        "data_coleta": COLETA.isoformat(),
        "hash_sha256": "c" * 64,
        "aviso": None,
    }
    assert do_banco["calendario"]["fonte"] == macro.IBGE_CALENDARIO
    assert (do_banco["variavel"], do_banco["tabela"]) == ("63", "1737")
    assert do_banco["banco"] == "series_macro"


def test_mes_divulgado_no_proprio_dia_de_d_ainda_nao_entra(conn, monkeypatch):
    exercicios, linhas, eventos = cenario()  # dezembro de 2025 sai em 10/01/2026
    _gravar(conn, monkeypatch, linhas, eventos)
    no_dia = datetime(2026, 1, 10, 23, tzinfo=UTC)  # 20h em Brasília, ainda dia 10
    assert macro.ipca_serie_do_banco(conn, exercicios, no_dia) == {
        "abstencao": "IPCA ausente ou não publicado na janela: 202512"
    }
    depois = datetime(2026, 1, 11, 12, tzinfo=UTC)
    assert "indices" in macro.ipca_serie_do_banco(conn, exercicios, depois)


def test_mes_sem_data_de_divulgacao_guardada_abstem_sem_inferir(conn, monkeypatch):
    exercicios, linhas, eventos = cenario()
    eventos = [
        e
        for e in eventos
        if (e["ano_referencia_inicio"], e["mes_referencia_inicio"]) != (2023, 6)
    ]
    _gravar(conn, monkeypatch, linhas, eventos)
    assert macro.ipca_serie_do_banco(conn, exercicios, D) == {
        "abstencao": "IPCA ausente ou não publicado na janela: 202306"
    }


def test_mes_ausente_no_sidra_abstem(conn, monkeypatch):
    exercicios, linhas, eventos = cenario()
    linhas = [l for l in linhas if l["D3C"] != "202404"]
    _gravar(conn, monkeypatch, linhas, eventos)
    assert macro.ipca_serie_do_banco(conn, exercicios, D) == {
        "abstencao": "IPCA ausente ou não publicado na janela: 202404"
    }


def test_banco_sem_linhas_abstem_sem_numero(conn, monkeypatch):
    exercicios, linhas, eventos = cenario()
    assert macro.ipca_serie_do_banco(conn, exercicios, D) == {
        "abstencao": "IPCA ausente no banco"
    }
    provedor = _provedor(monkeypatch, linhas, eventos)
    macro.gravar_series(
        conn, provedor, coleta=COLETA, datas=[COLETA.date()]
    )  # só a agenda
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM series_macro WHERE serie = 'ipca_divulgacao'"
        ).fetchone()[0]
        > 0
    )
    assert macro.ipca_serie_do_banco(conn, exercicios, D) == {
        "abstencao": "IPCA ausente no banco"
    }


def test_sidra_sem_agenda_abstem(conn, monkeypatch):
    exercicios, linhas, eventos = cenario()
    _gravar(conn, monkeypatch, linhas, eventos)
    gatilhos = [
        nome
        for (nome,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'series_macro'"
        )
    ]
    for nome in gatilhos:
        conn.execute(f'DROP TRIGGER "{nome}"')
    conn.execute("DELETE FROM series_macro WHERE serie = 'ipca_divulgacao'")
    assert macro.ipca_serie_do_banco(conn, exercicios, D) == {
        "abstencao": "IPCA ausente no banco"
    }


def test_coleta_mais_recente_prevalece(conn, monkeypatch):
    exercicios, linhas, eventos = cenario()
    _gravar(conn, monkeypatch, linhas, eventos)
    novas = [
        dict(l, V="2") if l["D3C"] == "202512" else l for l in linhas
    ]  # revisão do mês
    depois = datetime(2026, 3, 1, 18, tzinfo=UTC)
    _gravar(conn, monkeypatch, novas, eventos, coleta=depois, hash_sha256="d" * 64)
    serie = macro.ipca_serie_do_banco(conn, exercicios, D)
    assert serie["indices"]["2025-12"] == pytest.approx(1.01**47 * 1.02)
    assert serie["indices"]["2024-12"] == pytest.approx(1.01**36)
    assert serie["coleta"] == depois.isoformat()
    assert serie["proveniencia"]["hash_sha256"] == "d" * 64


@pytest.mark.parametrize(
    ("exercicios", "motivo"),
    [
        (
            [{"fim": f"{a}-12-31"} for a in range(2022, 2026)],
            "IPCA exige cinco encerramentos distintos",
        ),
        (
            [{"fim": f"{a}-12-30"} for a in range(2021, 2026)],
            "IPCA exige encerramento no fim do mês",
        ),
    ],
)
def test_encerramentos_invalidos_abstem(conn, monkeypatch, exercicios, motivo):
    _, linhas, eventos = cenario()
    _gravar(conn, monkeypatch, linhas, eventos)
    assert macro.ipca_serie_do_banco(conn, exercicios, D) == {"abstencao": motivo}


def test_d_sem_fuso_e_linha_invalida_abstem_com_motivo(conn, monkeypatch):
    exercicios, linhas, eventos = cenario()
    _gravar(conn, monkeypatch, linhas, eventos)
    sem_fuso = macro.ipca_serie_do_banco(conn, exercicios, D.replace(tzinfo=None))
    assert set(sem_fuso) == {"abstencao"}
    for nome in [
        n
        for (n,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'series_macro'"
        )
    ]:
        conn.execute(f'DROP TRIGGER "{nome}"')
    conn.execute(
        "UPDATE series_macro SET detalhe_json = ? WHERE serie = 'ipca_sidra' AND data = '2023-01-01'",
        (json.dumps({"D1C": "1", "D2C": "63", "D3C": "202301", "MN": "R$", "V": "1"}),),
    )
    assert macro.ipca_serie_do_banco(conn, exercicios, D) == {
        "abstencao": "unidade do IPCA inválida"
    }


# --- motor histórico ----------------------------------------------------------------------------


def _motor(conn, tmp_path):
    return historico.MotorHistorico(conn, D, tmp_path / "pit", CADASTRO)


def test_motor_le_o_ipca_do_banco_e_nao_apaga_o_existente(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(MarketEngine, "_contexto_janelas", lambda self, d, i, **k: None)
    chamadas = []

    def ler(conexao, exercicios, instante):
        chamadas.append((conexao, exercicios, instante))
        return {"abstencao": "IPCA ausente no banco"}

    monkeypatch.setattr(historico.macro, "ipca_serie_do_banco", ler)
    motor = _motor(conn, tmp_path)
    exercicios = [{"fim": f"{a}-12-31"} for a in range(2021, 2026)]
    dados = {"serie_cvm": {"exercicios": exercicios}}
    motor._contexto_janelas(dados, D, coletado_em=datetime(2026, 11, 16, tzinfo=UTC))
    assert dados["ipca_serie"] == {"abstencao": "IPCA ausente no banco"}
    assert chamadas == [(conn, exercicios, D)]  # D, não o instante da coleta
    for quantos in (0, 4, 6):  # a cascata só pede o IPCA com os cinco exercícios
        outro = {"serie_cvm": {"exercicios": [{}] * quantos}}
        motor._contexto_janelas(outro, D)
        assert "ipca_serie" not in outro
    ja = {"serie_cvm": {"exercicios": exercicios}, "ipca_serie": {"valor": 1}}
    motor._contexto_janelas(ja, D)
    assert ja["ipca_serie"] == {"valor": 1}
    assert len(chamadas) == 1


def test_motor_com_series_macro_indisponivel_abstem(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(MarketEngine, "_contexto_janelas", lambda self, d, i, **k: None)

    def falha(*a):
        raise sqlite3.OperationalError("no such table: series_macro")

    monkeypatch.setattr(historico.macro, "ipca_serie_do_banco", falha)
    dados = {"serie_cvm": {"exercicios": [{}] * 5}}
    _motor(conn, tmp_path)._contexto_janelas(dados, D)
    assert dados["ipca_serie"] == {
        "abstencao": "series_macro indisponível: no such table: series_macro"
    }


def test_e2e_produtor_banco_motor_ate_a_janela_do_graham(conn, tmp_path, monkeypatch):
    """[e2e] calendário e SIDRA → `gravar_series` → `series_macro` → `MotorHistorico` →
    `janelas_fundamentais` (Graham): o LPA médio corrigido é o do caminho do SIDRA."""
    _, linhas, eventos = cenario()
    provedor = _gravar(conn, monkeypatch, linhas, eventos)
    base = enriquecer_janelas(
        {"ticker": "TST3", "preco_atual": 100.0, "pl": 10.0, "pvp": 1.0, "roe": 0.1}
    )
    base["disponibilidade_por_publicacao"] = True  # decisão 40, como no motor histórico
    del base["ipca_serie"]
    pelo_motor = dict(base)
    _motor(conn, tmp_path)._contexto_janelas(pelo_motor, D, coletado_em=COLETA)
    graham = pelo_motor["janelas_fundamentais"]["graham"]
    assert "abstencao" not in graham, graham
    assert graham["fonte_ipca"] == SIDRA
    assert pelo_motor["ipca_serie"]["banco"] == "series_macro"
    pelo_sidra = dict(base)
    pelo_sidra["ipca_serie"] = provedor.ipca_serie(
        pelo_sidra["serie_cvm"]["exercicios"], D
    )
    MarketEngine._contexto_janelas(_motor(conn, tmp_path), pelo_sidra, D)
    assert graham["lpa"] == pytest.approx(
        pelo_sidra["janelas_fundamentais"]["graham"]["lpa"]
    )
    assert graham["lpa"] != pytest.approx(10.0)  # a correção pelo IPCA mudou a média


def test_motor_sem_ipca_no_banco_graham_abstem_com_o_motivo(conn, tmp_path):
    dados = enriquecer_janelas(
        {"ticker": "TST3", "preco_atual": 100.0, "pl": 10.0, "pvp": 1.0, "roe": 0.1}
    )
    dados["disponibilidade_por_publicacao"] = True
    del dados["ipca_serie"]
    _motor(conn, tmp_path)._contexto_janelas(dados, D)
    assert (
        dados["janelas_fundamentais"]["graham"]["abstencao"] == "IPCA ausente no banco"
    )


# --- a conta compartilhada (`indices_ipca`, `_encerramentos`), testada direto ------------------

FINAIS = [date(a, 12, 31) for a in range(2021, 2026)]
DIA = date(2026, 3, 2)


def _mensal(mes, valor="1", **kw):
    return {"D1C": "1", "D2C": "63", "D3C": mes, "MN": "%", "V": valor} | kw


def _meses(inicio=FINAIS[0], fim=FINAIS[-1]):
    numero, ultimo = inicio.year * 12 + inicio.month - 1, fim.year * 12 + fim.month - 1
    return [f"{n // 12:04}{n % 12 + 1:02}" for n in range(numero, ultimo + 1)]


def test_linha_de_outro_territorio_ou_variavel_antes_nao_interrompe_nem_conta():
    publicacoes = dict.fromkeys(_meses(), date(2026, 1, 10))
    publicacoes["202601"] = DIA  # divulgado no dia: fora, e não interrompe a leitura
    linhas = [
        _mensal("202512", "9", D1C="2"),
        _mensal("202512", "9", D2C="2265"),
        _mensal("202601", "9"),
        *(_mensal(m) for m in _meses()),
    ]
    indices = macro.indices_ipca(linhas, publicacoes, FINAIS, DIA)
    assert indices["2025-12"] == pytest.approx(1.01**48)


def test_mesmo_mes_igual_vale_e_diferente_e_conflito():
    publicacoes = dict.fromkeys(_meses(), date(2026, 1, 10))
    linhas = [_mensal(m) for m in _meses()]
    assert macro.indices_ipca(linhas + [_mensal("202306")], publicacoes, FINAIS, DIA)
    with pytest.raises(ValueError, match="^IPCA conflitante$"):
        macro.indices_ipca(linhas + [_mensal("202306", "2")], publicacoes, FINAIS, DIA)


def test_encerramentos_de_meses_diferentes_usam_o_primeiro_e_o_ultimo():
    finais = [date(2021, 6, 30), *FINAIS[1:]]
    publicacoes = dict.fromkeys(_meses(finais[0]), date(2026, 1, 10))
    linhas = [_mensal(m) for m in _meses(finais[0])]
    indices = macro.indices_ipca(linhas, publicacoes, finais, DIA)
    assert indices == pytest.approx(
        {"2021-06": 1.0}
        | {f"{a}-12": 1.01 ** (18 + 12 * (a - 2022)) for a in range(2022, 2026)}
    )
    sem_junho = [l for l in linhas if l["D3C"] != "202106"]
    with pytest.raises(ValueError, match="202106"):
        macro.indices_ipca(sem_junho, publicacoes, finais, DIA)


def test_produto_sem_fator_positivo_finito_falha_com_o_motivo():
    publicacoes = dict.fromkeys(_meses(), date(2026, 1, 10))
    linhas = [_mensal(m, "1e308") for m in _meses()]
    with pytest.raises(ValueError, match="^IPCA acumulado sem fator positivo finito$"):
        macro.indices_ipca(linhas, publicacoes, FINAIS, DIA)


def test_encerramento_repetido_nao_conta_como_cinco():
    with pytest.raises(ValueError, match="^IPCA exige cinco encerramentos distintos$"):
        macro._encerramentos(
            [{"fim": "2021-12-31"}] * 2
            + [{"fim": f"{a}-12-31"} for a in (2022, 2023, 2024)]
        )


def test_motor_repassa_o_instante_da_coleta_a_cascata(conn, tmp_path, monkeypatch):
    vistos = []
    monkeypatch.setattr(
        MarketEngine, "_contexto_janelas", lambda self, d, i, **k: vistos.append((i, k))
    )
    monkeypatch.setattr(
        historico.macro, "ipca_serie_do_banco", lambda *a: {"abstencao": "x"}
    )
    coleta = datetime(2026, 11, 16, tzinfo=UTC)
    _motor(conn, tmp_path)._contexto_janelas({"serie_cvm": {}}, D, coletado_em=coleta)
    assert vistos == [(D, {"coletado_em": coleta})]
