"""F3-4c: série ajustada só por eventos societários, separada do preço bruto.

Aritmética dos fatores oficiais (F = multiplicador da quantidade na data ex; o preço anterior é
dividido por F) e integração com o banco: COTAHIST pelo layout oficial (F3-4a) e os eventos
oficiais da Lojas Renner (F3-4b) → `serie_do_banco`.
"""

import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, date, datetime

import pytest
from test_cotahist import _linha
from test_eventos_societarios import _obter

from sentinela.data.pit import serie_ajustada as sa
from sentinela.data.providers import b3_cotahist, b3_proventos
from sentinela.data.store import migracoes

D1, D2, D3, D4 = (
    date(2024, 12, 10),
    date(2024, 12, 11),
    date(2024, 12, 12),
    date(2024, 12, 13),
)
PRECOS = [(D1, 10.0), (D2, 10.0), (D3, 9.10), (D4, 9.0)]


def _evento(data_com="2024-12-11", data_ex="2024-12-12", fator=1.1):
    return {"data_com": data_com, "data_ex": data_ex, "fator": fator}


def _ajustados(serie):
    return [p["ajustado"] for p in serie]


def test_bonificacao_divide_o_preco_anterior_a_data_ex():
    serie = sa.ajustar(PRECOS, [_evento()])
    assert _ajustados(serie) == pytest.approx([10 / 1.1, 10 / 1.1, 9.10, 9.0])
    assert [p["bruto"] for p in serie] == [
        p for _, p in PRECOS
    ]  # o bruto fica separado
    assert [p["fator"] for p in serie] == pytest.approx([1.1, 1.1, 1.0, 1.0])


def test_grupamento_multiplica_o_preco_anterior():
    serie = sa.ajustar(PRECOS, [_evento(fator=0.01)])  # 100 antigas viram 1
    assert _ajustados(serie)[:2] == pytest.approx([1000.0, 1000.0])


def test_eventos_acumulam_pela_data_ex():
    eventos = [
        _evento(),
        _evento(data_com="2024-12-12", data_ex="2024-12-13", fator=2.0),
    ]
    assert _ajustados(sa.ajustar(PRECOS, eventos)) == pytest.approx(
        [10 / 2.2, 10 / 2.2, 9.10 / 2, 9.0]
    )


def test_evento_antes_do_primeiro_preco_ou_ainda_nao_efetivado_nao_muda_a_serie():
    eventos = [
        _evento(data_com="2024-12-01", data_ex="2024-12-02", fator=5.0),
        _evento(data_com="2024-12-13", data_ex="2024-12-16", fator=5.0),
        _evento(data_com="2024-12-20", data_ex=None, fator=5.0),
    ]
    assert _ajustados(sa.ajustar(PRECOS, eventos)) == [p for _, p in PRECOS]


@pytest.mark.parametrize(
    ("evento", "motivo"),
    [
        (_evento(fator=None), sa.MOTIVO_SEM_FATOR),
        (_evento(fator=0.0), sa.MOTIVO_SEM_FATOR),
        (_evento(fator=float("nan")), sa.MOTIVO_SEM_FATOR),
        (_evento(fator=True), sa.MOTIVO_SEM_FATOR),
        (_evento(data_ex=None), sa.MOTIVO_SEM_DATA_EX),
    ],
)
def test_evento_sem_fator_ou_data_ex_abstem_o_intervalo_anterior(evento, motivo):
    serie = sa.ajustar(PRECOS, [evento])
    assert _ajustados(serie) == [None, None, 9.10, 9.0]
    assert [p.get("motivo") for p in serie] == [motivo, motivo, None, None]


def test_evento_sem_prova_abstem_o_intervalo_e_sem_data_abstem_tudo():
    serie = sa.ajustar(PRECOS, [], [{"data_com": "2024-12-11"}])
    assert _ajustados(serie) == [None, None, 9.10, 9.0]
    assert serie[0]["motivo"] == sa.MOTIVO_SEM_PROVA
    assert _ajustados(sa.ajustar(PRECOS, [], [{"data_com": None}])) == [None] * 4
    assert _ajustados(sa.ajustar(PRECOS, [], [{"data_com": "2024-12-20"}])) == [
        p for _, p in PRECOS
    ]


def test_bloqueio_mais_recente_prevalece_e_o_mais_antigo_nao_libera():
    eventos = [
        _evento(fator=None),
        _evento(data_com="2024-12-10", data_ex="2024-12-11", fator=2.0),
    ]
    serie = sa.ajustar(PRECOS, eventos)
    assert _ajustados(serie) == [None, None, 9.10, 9.0]


def test_serie_vazia():
    assert sa.ajustar([], [_evento()]) == []


# --- Banco único ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _carregar_precos(conn, tmp_path, *linhas):
    caminho = tmp_path / "COTAHIST_A2024.ZIP"
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("COTAHIST_A2024.TXT", "\n".join(linhas).encode("latin-1"))
    b3_cotahist.carregar(conn, caminho, fonte="b3", coleta="2026-11-12T00:00:00+00:00")


def _lren(data, preco):
    return _linha(
        DATA=data, CODNEG="LREN3", CODISI="BRLRENACNOR1", PREULT=f"{preco:013d}"
    )


def test_serie_do_banco_com_a_bonificacao_oficial_da_lojas_renner(conn, tmp_path):
    relacao = b3_proventos.coletar(
        8133, datetime(2026, 10, 20, 20, 40, tzinfo=UTC), _obter()
    )
    b3_proventos.gravar_eventos(conn, relacao, 8133)
    _carregar_precos(
        conn,
        tmp_path,
        _lren("20241210", 1650),
        _lren("20241211", 1650),
        _lren("20241212", 1500),
        _lren("20241213", 1510),
        _linha(DATA="20241212", CODNEG="OUT3", CODISI="BROUTRACNOR1"),
    )
    lido = sa.serie_do_banco(conn, "LREN3", "LREN", date(2024, 12, 14), 63)
    assert lido["isin"] == "BRLRENACNOR1"
    serie = lido["serie"]
    assert [p["data"] for p in serie] == [
        "2024-12-10",
        "2024-12-11",
        "2024-12-12",
        "2024-12-13",
    ]
    assert [p["bruto"] for p in serie] == pytest.approx([16.5, 16.5, 15.0, 15.1])
    assert _ajustados(serie) == pytest.approx([15.0, 15.0, 15.0, 15.1])  # 16,50 / 1,1


def test_evento_de_outra_especie_abstem_o_intervalo(conn, tmp_path):
    relacao = b3_proventos.coletar(
        8133, datetime(2026, 10, 20, 20, 40, tzinfo=UTC), _obter()
    )
    outra = b3_proventos.Relacao(
        **{
            **relacao.__dict__,
            "eventos_acoes": (
                {"label": "DESDOBRAMENTO", "factor": "100,0", "isinCode": "BRLRENACNOR1",
                 "assetIssued": "BRLRENACNPR9", "lastDatePrior": "11/12/2024", "approvedOn": "01/12/2024"},
            ),
        }
    )  # fmt: skip
    b3_proventos.gravar_eventos(conn, outra, 8133)
    _carregar_precos(conn, tmp_path, _lren("20241211", 1650), _lren("20241212", 1500))
    serie = sa.serie_do_banco(conn, "LREN3", "LREN", date(2024, 12, 14), 63)["serie"]
    assert _ajustados(serie) == [
        None,
        15.0,
    ]  # abstém: sem reconciliação entre as espécies
    assert serie[0]["motivo"] == sa.MOTIVO_OUTRA_ESPECIE


def test_codigo_sem_isin_unico_abstem(conn, tmp_path):
    _carregar_precos(
        conn,
        tmp_path,
        _linha(DATA="20241211", CODISI="BRAAAACNOR1"),
        _linha(DATA="20241212", CODISI="BRBBBBCNOR1"),
    )
    assert sa.serie_do_banco(conn, "TST3", "X", date(2024, 12, 14), 63) == {
        "serie": [],
        "motivo": "código sem ISIN único nos preços do período",
    }
    assert sa.serie_do_banco(conn, "NADA3", "X", date(2024, 12, 14), 63)[
        "motivo"
    ].startswith("código sem ISIN")


def test_serie_do_banco_recusa_instante(conn):
    with pytest.raises(
        TypeError,
        match=r"^serie_do_banco recebe o dia local de D \(date\), não um instante$",
    ):
        sa.serie_do_banco(conn, "X", "X", datetime(2024, 12, 14, tzinfo=UTC), 63)


# --- Fronteiras (lacunas da mutação) ----------------------------------------------------------


def test_evento_com_data_com_no_primeiro_preco_ajusta_o_primeiro():
    serie = sa.ajustar(
        PRECOS, [_evento(data_com="2024-12-10", data_ex="2024-12-11", fator=2.0)]
    )
    assert _ajustados(serie) == pytest.approx([5.0, 10.0, 9.10, 9.0])


def test_evento_com_data_com_no_ultimo_preco_nao_muda_nem_bloqueia():
    eventos = [_evento(data_com="2024-12-13", data_ex=None)]
    assert _ajustados(sa.ajustar(PRECOS, eventos)) == [p for _, p in PRECOS]


def test_sem_prova_nas_bordas():
    no_inicio = sa.ajustar(PRECOS, [], [{"data_com": "2024-12-10"}])
    assert _ajustados(no_inicio) == [None, 10.0, 9.10, 9.0]
    no_fim = sa.ajustar(PRECOS, [], [{"data_com": "2024-12-13"}])
    assert _ajustados(no_fim) == [p for _, p in PRECOS]


def test_item_abstido_traz_data_e_bruto():
    (primeiro, *_) = sa.ajustar(PRECOS, [_evento(fator=None)])
    assert primeiro == {
        "data": "2024-12-10",
        "bruto": 10.0,
        "ajustado": None,
        "motivo": sa.MOTIVO_SEM_FATOR,
    }


def test_serie_do_banco_respeita_os_pregoes_e_o_sem_prova_do_papel(conn, tmp_path):
    relacao = b3_proventos.coletar(
        8133, datetime(2026, 10, 20, 20, 40, tzinfo=UTC), _obter()
    )
    ilegivel = {"label": "DESDOBRAMENTO", "factor": "100,0", "isinCode": "BRLRENACNOR1",
                "assetIssued": "BRLRENACNOR1", "lastDatePrior": "11/12/2024", "approvedOn": "31/02/2024"}  # fmt: skip
    outro = dict(
        ilegivel,
        isinCode="BROUTRACNOR1",
        assetIssued="BROUTRACNOR1",
        lastDatePrior="12/12/2024",
    )
    b3_proventos.gravar_eventos(
        conn,
        b3_proventos.Relacao(
            **{**relacao.__dict__, "eventos_acoes": (ilegivel, outro)}
        ),
        8133,
    )
    _carregar_precos(
        conn,
        tmp_path,
        _lren("20241211", 1650),
        _lren("20241212", 1500),
        _lren("20241213", 1510),
    )
    serie = sa.serie_do_banco(conn, "LREN3", "LREN", date(2024, 12, 14), 63)["serie"]
    assert _ajustados(serie) == [
        None,
        15.0,
        15.1,
    ]  # o sem prova do papel bloqueia; o de outro ISIN, não
    assert (
        serie[0]["motivo"] == b3_proventos.MOTIVO_SEM_DATAS
    )  # o motivo do `eventos_ate`
    curta = sa.serie_do_banco(conn, "LREN3", "LREN", date(2024, 12, 14), 2)["serie"]
    assert [p["data"] for p in curta] == ["2024-12-12", "2024-12-13"]


def test_evento_sem_data_com_abstem_a_serie_inteira():
    serie = sa.ajustar(PRECOS, [_evento(data_com=None)])
    assert _ajustados(serie) == [None] * 4 and serie[0]["motivo"] == sa.MOTIVO_SEM_PROVA


def test_bloqueio_com_motivo_proprio():
    serie = sa.ajustar(
        PRECOS, [], [{"data_com": "2024-12-11", "motivo": "outro motivo"}]
    )
    assert [p.get("motivo") for p in serie] == [
        "outro motivo",
        "outro motivo",
        None,
        None,
    ]


@pytest.mark.parametrize("precos", [[(D2, 1.0), (D1, 1.0)], [(D1, 1.0), (D1, 2.0)]])
def test_datas_fora_de_ordem_ou_repetidas_sao_recusadas(precos):
    with pytest.raises(ValueError, match="^datas da série fora de ordem ou repetidas$"):
        sa.ajustar(precos, [])


def test_evento_sem_ativo_emitido_abstem(conn, tmp_path):
    relacao = b3_proventos.coletar(
        8133, datetime(2026, 10, 20, 20, 40, tzinfo=UTC), _obter()
    )
    sem_emitido = {"label": "DESDOBRAMENTO", "factor": "100,0", "isinCode": "BRLRENACNOR1",
                   "lastDatePrior": "11/12/2024", "approvedOn": "01/12/2024"}  # fmt: skip
    b3_proventos.gravar_eventos(
        conn,
        b3_proventos.Relacao(**{**relacao.__dict__, "eventos_acoes": (sem_emitido,)}),
        8133,
    )
    _carregar_precos(conn, tmp_path, _lren("20241211", 1650), _lren("20241212", 1500))
    serie = sa.serie_do_banco(conn, "LREN3", "LREN", date(2024, 12, 14), 63)["serie"]
    assert serie[0]["motivo"] == sa.MOTIVO_OUTRA_ESPECIE


def test_banco_com_linha_sem_isin_ou_cotacao_repetida_abstem(conn, tmp_path):
    _carregar_precos(
        conn,
        tmp_path,
        _lren("20241211", 1650),
        _linha(DATA="20241212", CODNEG="LREN3", CODISI=""),
    )
    assert sa.serie_do_banco(conn, "LREN3", "X", date(2024, 12, 14), 63) == {
        "serie": [],
        "motivo": sa.MOTIVO_SEM_ISIN,
    }


def test_banco_com_duas_cotacoes_do_codigo_no_mesmo_pregao_abstem(conn, tmp_path):
    _carregar_precos(
        conn,
        tmp_path,
        _lren("20241211", 1650),
        _linha(DATA="20241211", CODNEG="LREN3", CODISI="BRLRENACNOR1", CODBDI="96"),
    )
    assert sa.serie_do_banco(conn, "LREN3", "X", date(2024, 12, 14), 63) == {
        "serie": [],
        "motivo": sa.MOTIVO_COTACAO_REPETIDA,
    }


def test_banco_so_com_linhas_sem_isin_abstem(conn, tmp_path):
    _carregar_precos(conn, tmp_path, _linha(DATA="20241211", CODNEG="LREN3", CODISI=""))
    assert sa.serie_do_banco(conn, "LREN3", "X", date(2024, 12, 14), 63) == {
        "serie": [],
        "motivo": sa.MOTIVO_SEM_ISIN,
    }
