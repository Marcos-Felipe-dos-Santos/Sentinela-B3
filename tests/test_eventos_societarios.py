"""F3-4b: eventos em ações da B3 no banco único (`eventos_societarios`) com o fator oficial.

Ponta a ponta: respostas oficiais do CompanyCall da Lojas Renner (contrato D18, coletadas em
20/10/2026) → `b3_proventos.coletar` → `gravar_eventos` → `eventos_ate(D)`. Casos públicos:
grupamento de 2005 (fator 0,00395256920), desdobramento de 400% em 2015 e bonificação de
10% em 2024; "CIS RED CAP" fica sem fator, com o motivo.
"""

import json
import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, date, datetime

import pytest
from test_contratos_provedores import _b3_obter, _fixture
from test_cotahist import _linha

from sentinela.data.providers import b3_cotahist, b3_proventos
from sentinela.data.store import migracoes

COLETA = datetime(2026, 10, 20, 20, 40, tzinfo=UTC)


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _obter(instante_fixture="b3_proventos_lren_2026.json"):
    """O falso do contrato, com o SHA-256 de cada resposta, como o `obter_json` real."""
    import hashlib

    fixture = _fixture(instante_fixture)
    base = _b3_obter(fixture)

    def obter(endereco):
        corpo, fonte = base(endereco)
        texto = json.dumps(corpo, sort_keys=True).encode()
        return corpo, {**fonte, "sha256": hashlib.sha256(texto).hexdigest()}

    return obter


@pytest.fixture
def relacao():
    return b3_proventos.coletar(8133, COLETA, _obter())


def _por_rotulo(eventos, rotulo):
    return [e for e in eventos if e["rotulo"] == rotulo]


def test_eventos_oficiais_gravados_com_o_fator_da_b3(conn, relacao):
    resumo = b3_proventos.gravar_eventos(conn, relacao, 8133)
    assert (
        resumo["inseridos"] == len(relacao.eventos_acoes) and resumo["repetidos"] == 0
    )
    eventos = b3_proventos.eventos_ate(conn, "LREN", date(2026, 10, 21))["eventos"]
    (grupamento,) = _por_rotulo(eventos, "GRUPAMENTO")
    assert (
        grupamento["data_com"] == "2005-06-29"
        and grupamento["aprovacao"] == "2005-06-28"
    )
    assert grupamento["fator"] == pytest.approx(0.0039525692)  # 1 nova a cada 253
    (desdobramento,) = _por_rotulo(eventos, "DESDOBRAMENTO")
    assert desdobramento["data_com"] == "2015-09-23" and desdobramento[
        "fator"
    ] == pytest.approx(5.0)
    (bonificacao,) = _por_rotulo(eventos, "BONIFICACAO")
    assert bonificacao["data_com"] == "2024-12-11" and bonificacao[
        "fator"
    ] == pytest.approx(1.1)
    assert bonificacao["fator_declarado"] == "10,00000000000"
    assert bonificacao["proveniencia"] == {
        "fonte": relacao.fontes[-1]["url"],
        "coleta": COLETA.isoformat(),
        "hash_sha256": relacao.fontes[-1]["sha256"],
    }


def test_evento_sem_conversao_documentada_fica_sem_fator_com_o_motivo(conn, relacao):
    resumo = b3_proventos.gravar_eventos(conn, relacao, 8133)
    eventos = b3_proventos.eventos_ate(conn, "LREN", date(2026, 10, 21))["eventos"]
    cis = _por_rotulo(eventos, "CIS RED CAP")
    assert cis and all(e["fator"] is None for e in cis)
    assert all(
        e["motivo_sem_fator"] == "evento em ações não demonstrado: CIS RED CAP"
        for e in cis
    )
    assert resumo["sem_fator"] == len(
        [
            e
            for e in relacao.eventos_acoes
            if e["label"] not in ("DESDOBRAMENTO", "BONIFICACAO", "GRUPAMENTO")
        ]
    )


def test_so_eventos_aprovados_antes_do_dia_de_d(conn, relacao):
    b3_proventos.gravar_eventos(conn, relacao, 8133)
    antes = b3_proventos.eventos_ate(conn, "LREN", date(2024, 12, 11))["eventos"]
    assert not _por_rotulo(
        antes, "BONIFICACAO"
    )  # aprovada em 11/12/2024: no próprio dia, ainda não
    depois = b3_proventos.eventos_ate(conn, "LREN", date(2024, 12, 12))["eventos"]
    assert _por_rotulo(depois, "BONIFICACAO")
    assert _por_rotulo(antes, "DESDOBRAMENTO")


def _precos(conn, tmp_path, *datas):
    linhas = [_linha(DATA=d, CODNEG="LREN3") for d in datas]
    caminho = tmp_path / f"COTAHIST_{datas[0]}.ZIP"
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("COTAHIST.TXT", "\n".join(linhas).encode("latin-1"))
    b3_cotahist.carregar(conn, caminho, fonte="b3", coleta=COLETA.isoformat())


def test_data_ex_so_com_pregoes_em_volta_da_data_com(conn, relacao, tmp_path):
    b3_proventos.gravar_eventos(conn, relacao, 8133)
    _precos(conn, tmp_path, "20241211", "20241212", "20241213")
    eventos = b3_proventos.eventos_ate(conn, "LREN", date(2026, 10, 21))["eventos"]
    (bonificacao,) = _por_rotulo(eventos, "BONIFICACAO")
    assert (
        bonificacao["data_ex"] == "2024-12-12" and bonificacao["motivo_data_ex"] is None
    )
    # o desdobramento de 2015 não tem pregões guardados em volta: o primeiro guardado depois
    # da data com (2024) não é a data ex
    (desdobramento,) = _por_rotulo(eventos, "DESDOBRAMENTO")
    assert desdobramento["data_ex"] is None
    assert desdobramento["motivo_data_ex"] == b3_proventos.MOTIVO_SEM_CALENDARIO
    assert b3_proventos.eventos_ate(conn, "OUTRO", date(2026, 10, 21)) == {
        "eventos": [],
        "sem_prova": [],
    }


@pytest.mark.parametrize(
    ("datas", "dia", "esperado"),
    [
        (("20241128", "20241212"), date(2026, 1, 1), None),  # pregão anterior a 13 dias
        (("20241211", "20241226"), date(2026, 1, 1), None),  # pregão seguinte a 15 dias
        (
            ("20241211", "20241212"),
            date(2024, 12, 12),
            None,
        ),  # o seguinte é o próprio dia de D
        (("20241211", "20241212"), date(2024, 12, 13), "2024-12-12"),
        (
            ("20241201", "20241221"),
            date(2026, 1, 1),
            "2024-12-21",
        ),  # no limite de 10 dias
    ],
)
def test_prova_de_calendario_da_data_ex(conn, tmp_path, datas, dia, esperado):
    _precos(conn, tmp_path, *datas)
    assert b3_proventos._data_ex(conn, "2024-12-11", dia) == esperado


def test_sem_pregao_depois_da_data_com_a_data_ex_fica_nula(conn, relacao):
    b3_proventos.gravar_eventos(conn, relacao, 8133)
    eventos = b3_proventos.eventos_ate(conn, "LREN", date(2026, 10, 21))["eventos"]
    assert all(e["data_ex"] is None for e in eventos)
    assert all(
        e["motivo_data_ex"] == b3_proventos.MOTIVO_SEM_CALENDARIO for e in eventos
    )


def test_mesma_coleta_de_novo_so_conta_repetidos_e_fica_a_primeira(conn, relacao):
    b3_proventos.gravar_eventos(conn, relacao, 8133)
    depois = b3_proventos.coletar(
        8133,
        datetime(2026, 11, 1, tzinfo=UTC),
        _obter(),
    )
    resumo = b3_proventos.gravar_eventos(conn, depois, 8133)
    assert resumo == {
        "inseridos": 0,
        "repetidos": len(relacao.eventos_acoes),
        "sem_fator": 0,
    }
    coletas = {
        c for (c,) in conn.execute("SELECT DISTINCT coleta FROM eventos_societarios")
    }
    assert coletas == {COLETA.isoformat()}


def test_aprovacao_ilegivel_vai_para_sem_prova(conn, relacao):
    estragada = b3_proventos.Relacao(
        **{
            **relacao.__dict__,
            "eventos_acoes": (
                {"label": "DESDOBRAMENTO", "factor": "100,0", "isinCode": "BRLRENACNOR1",
                 "assetIssued": "BRLRENACNOR1", "lastDatePrior": "01/02/2020", "approvedOn": "31/02/2020"},
            ),
        }
    )  # fmt: skip
    b3_proventos.gravar_eventos(conn, estragada, 8133)
    lido = b3_proventos.eventos_ate(conn, "LREN", date(2026, 10, 21))
    assert lido["eventos"] == [] and len(lido["sem_prova"]) == 1
    assert lido["sem_prova"][0]["fator"] == pytest.approx(2.0)


@pytest.mark.parametrize(
    ("factor", "motivo"),
    [
        ("", "insumo ausente: fator oficial B3"),
        ("0,0", "fator oficial B3 não positivo ou não finito"),
    ],
)
def test_fator_ausente_ou_invalido_fica_sem_fator(conn, relacao, factor, motivo):
    evento = {"label": "GRUPAMENTO", "factor": factor, "isinCode": "X", "assetIssued": "X",
              "lastDatePrior": "01/02/2020", "approvedOn": "01/01/2020"}  # fmt: skip
    b3_proventos.gravar_eventos(
        conn,
        b3_proventos.Relacao(**{**relacao.__dict__, "eventos_acoes": (evento,)}),
        8133,
    )
    (gravado,) = b3_proventos.eventos_ate(conn, "LREN", date(2026, 10, 21))["eventos"]
    assert gravado["fator"] is None and gravado["motivo_sem_fator"].startswith(motivo)


def test_falha_no_meio_nao_deixa_linha_parcial(conn, relacao, monkeypatch):
    chamadas = []

    def falhar_no_segundo(evento):
        chamadas.append(evento)
        if len(chamadas) == 2:
            raise OSError("disco")
        return 1.0, None

    monkeypatch.setattr(b3_proventos, "_fator_ou_motivo", falhar_no_segundo)
    with pytest.raises(OSError):
        b3_proventos.gravar_eventos(conn, relacao, 8133)
    assert conn.execute("SELECT COUNT(*) FROM eventos_societarios").fetchone() == (0,)
    assert conn.in_transaction is False


def test_so_insercao_e_dominios(conn, relacao):
    b3_proventos.gravar_eventos(conn, relacao, 8133)
    for sql in (
        "UPDATE eventos_societarios SET fator = 9",
        "DELETE FROM eventos_societarios",
    ):
        with pytest.raises(
            sqlite3.IntegrityError, match="eventos_societarios é só de inserção"
        ):
            conn.execute(sql)
    base = ("INSERT INTO eventos_societarios (emissor, linha_sha256, cd_cvm, rotulo, fator, "
            "motivo_sem_fator, linha_json, fonte, coleta, hash_sha256) VALUES ('E', ?, '1', 'X', ?, ?, '{}', 'f', 'c', 'h')")  # fmt: skip
    for linha, fator, motivo in (("a", None, None), ("b", 1.0, "m"), ("c", 0.0, None)):
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conn.execute(base, (linha, fator, motivo))
    linha = conn.execute("SELECT * FROM eventos_societarios LIMIT 1").fetchone()
    colunas = [c[1] for c in conn.execute("PRAGMA table_info(eventos_societarios)")]
    with pytest.raises(
        sqlite3.IntegrityError, match="eventos_societarios é só de inserção"
    ):
        conn.execute(
            f"INSERT INTO eventos_societarios ({', '.join(colunas)}) VALUES ({', '.join('?' * len(colunas))})",
            linha,
        )


def test_eventos_ate_recusa_instante(conn):
    with pytest.raises(
        TypeError,
        match=r"^eventos_ate recebe o dia local de D \(date\), não um instante$",
    ):
        b3_proventos.eventos_ate(conn, "LREN", datetime(2026, 1, 1, tzinfo=UTC))


def test_linha_identificada_pelo_conteudo(conn, relacao):
    b3_proventos.gravar_eventos(conn, relacao, 8133)
    texto, linha = conn.execute(
        "SELECT linha_json, linha_sha256 FROM eventos_societarios WHERE rotulo = 'GRUPAMENTO'"
    ).fetchone()
    assert json.loads(texto)["factor"] == "0,00395256920"
    import hashlib

    assert linha == hashlib.sha256(texto.encode("utf-8")).hexdigest()


def test_migracao_007_sobre_o_banco_da_006_sem_perda(tmp_path):
    import shutil

    ate_006, ate_007 = tmp_path / "ate_006", tmp_path / "ate_007"
    ate_006.mkdir()
    ate_007.mkdir()
    for _, arquivo in migracoes.listar():
        if arquivo.name < "007":
            shutil.copy(arquivo, ate_006 / arquivo.name)
        if arquivo.name < "008":
            shutil.copy(arquivo, ate_007 / arquivo.name)
    banco = tmp_path / "b.db"
    with closing(sqlite3.connect(banco)) as c:
        assert migracoes.aplicar(c, ate_006) == [1, 2, 3, 4, 5, 6]
        c.execute("INSERT INTO carteira_real VALUES ('TST3', 10, 9.5, '2026-01-02')")
        c.commit()
    with closing(sqlite3.connect(banco)) as c:
        assert migracoes.aplicar(c, ate_007) == [7]
        assert c.execute("SELECT COUNT(*) FROM carteira_real").fetchone() == (1,)


# --- Lacunas da mutação -------------------------------------------------------------------


def _evento(**campos):
    base = {"label": "DESDOBRAMENTO", "factor": "100,0", "isinCode": "BRTSTAACNOR1",
            "assetIssued": "BRTSTAACNOR2", "lastDatePrior": "01/02/2020", "approvedOn": "01/01/2020",
            "remarks": "ação nova"}  # fmt: skip
    base.update(campos)
    return base


def _gravar(conn, relacao, *eventos):
    return b3_proventos.gravar_eventos(
        conn,
        b3_proventos.Relacao(**{**relacao.__dict__, "eventos_acoes": eventos}),
        8133,
    )


def test_campos_do_evento_gravados_e_devolvidos(conn, relacao):
    _gravar(conn, relacao, _evento())
    (evento,) = b3_proventos.eventos_ate(conn, "LREN", date(2026, 1, 1))["eventos"]
    assert (evento["isin"], evento["ativo_emitido"]) == ("BRTSTAACNOR1", "BRTSTAACNOR2")
    assert conn.execute(
        "SELECT cd_cvm, rotulo FROM eventos_societarios"
    ).fetchone() == ("8133", "DESDOBRAMENTO")
    texto = conn.execute("SELECT linha_json FROM eventos_societarios").fetchone()[0]
    assert "ação nova" in texto  # legível, sem escape


def test_evento_sem_rotulo_fica_com_rotulo_vazio_e_sem_fator(conn, relacao):
    _gravar(conn, relacao, _evento(label=None))
    rotulo, fator = conn.execute(
        "SELECT rotulo, fator FROM eventos_societarios"
    ).fetchone()
    assert rotulo == "" and fator is None


def test_mesmo_evento_com_as_chaves_em_outra_ordem_e_repetido(conn, relacao):
    evento = _evento()
    _gravar(conn, relacao, evento)
    invertido = dict(reversed(list(evento.items())))
    assert _gravar(conn, relacao, invertido) == {
        "inseridos": 0,
        "repetidos": 1,
        "sem_fator": 0,
    }


def test_mesmo_evento_em_outra_forma_conta_uma_vez(conn, relacao):
    _gravar(conn, relacao, _evento(), _evento(remarks="outra observação"))
    lido = b3_proventos.eventos_ate(conn, "LREN", date(2026, 1, 1))
    assert len(lido["eventos"]) == 1 and lido["sem_prova"] == []


def test_mesma_data_com_e_fatores_diferentes_vao_para_sem_prova(conn, relacao):
    depois = _evento(lastDatePrior="01/03/2021", approvedOn="01/02/2021")
    _gravar(conn, relacao, _evento(), _evento(factor="200,0"), depois)
    lido = b3_proventos.eventos_ate(conn, "LREN", date(2026, 1, 1))
    assert [e["data_com"] for e in lido["eventos"]] == [
        "2021-03-01"
    ]  # o conflito não esconde o resto
    assert [e["motivo"] for e in lido["sem_prova"]] == [
        b3_proventos.MOTIVO_CONFLITO
    ] * 2


def test_aprovado_com_data_com_ilegivel_vai_para_sem_prova(conn, relacao):
    _gravar(conn, relacao, _evento(lastDatePrior="31/02/2020"))
    lido = b3_proventos.eventos_ate(conn, "LREN", date(2026, 1, 1))
    assert (
        lido["eventos"] == []
        and lido["sem_prova"][0]["motivo"] == b3_proventos.MOTIVO_SEM_DATAS
    )


def test_gravacao_exige_a_resposta_do_complemento_como_fonte(conn, relacao):
    outra = b3_proventos.Relacao(
        **{**relacao.__dict__, "fontes": (*relacao.fontes, {"url": "x", "sha256": "h"})}
    )
    with pytest.raises(
        ValueError, match="^a última fonte da coleta não é a resposta do complemento$"
    ):
        b3_proventos.gravar_eventos(conn, outra, 8133)


def test_evento_aprovado_e_ainda_nao_efetivado_tem_motivo_proprio(
    conn, relacao, tmp_path
):
    _precos(conn, tmp_path, "20241210", "20241211", "20241212")
    _gravar(conn, relacao, _evento(lastDatePrior="11/12/2024", approvedOn="01/12/2024"))
    (evento,) = b3_proventos.eventos_ate(conn, "LREN", date(2024, 12, 11))["eventos"]
    assert (
        evento["data_ex"] is None
        and evento["motivo_data_ex"] == b3_proventos.MOTIVO_NAO_EFETIVADO
    )
    (depois,) = b3_proventos.eventos_ate(conn, "LREN", date(2024, 12, 13))["eventos"]
    assert depois["data_ex"] == "2024-12-12" and depois["motivo_data_ex"] is None
