"""F3-4a: COTAHIST no banco único (`precos`) e liquidez numa data D sem olhar o futuro.

Ponta a ponta: arquivo oficial (recorte do COTAHIST de 09/2026, contrato do F2A) e linhas
sintéticas pelo layout oficial → `b3_cotahist.carregar` → `precos` → `cotacoes_ate(D)` →
`liquidez.metricas` e `liquidez.avaliar`, com as regras da 2B.
"""

import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, date, timedelta

import pytest
from test_contratos_provedores import _montar
from test_cotahist import _linha

from sentinela.data import liquidez
from sentinela.data.providers import b3_cotahist as cot
from sentinela.data.store import migracoes

COLETA = "2026-11-11T12:00:00+00:00"


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


@pytest.fixture
def oficial(tmp_path):
    caminho, fixture = _montar("cotahist_m092026_petrobras.json", tmp_path)
    return caminho, fixture["membros"]["COTAHIST_M092026.TXT"].splitlines()


def _carregar(conn, arquivo, coleta=COLETA):
    return cot.carregar(conn, arquivo, fonte=f"b3:{arquivo.name}", coleta=coleta)


def _zip(caminho, linhas):
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr(caminho.stem + ".TXT", ("\n".join(linhas) + "\n").encode("latin-1"))
    return caminho


def _contar(conn, tabela="precos"):
    return conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


# --- Arquivo oficial ----------------------------------------------------------------------


def test_arquivo_oficial_gravado_bruto_so_no_mercado_a_vista(conn, oficial):
    caminho, linhas = oficial
    resumo = _carregar(conn, caminho)
    a_vista = [l for l in linhas if l[:2] == "01" and l[24:27] == "010"]
    assert len(a_vista) == 4
    assert resumo["inseridas"] == 4 and resumo["total_recusadas"] == 0
    petr3 = conn.execute(
        "SELECT abertura_centavos, maxima_centavos, minima_centavos, media_centavos, "
        "fechamento_centavos, negocios, quantidade, volume_centavos, fator_cotacao, isin, "
        "especificacao, codbdi, prazo, fonte, coleta, hash_sha256 FROM precos "
        "WHERE codigo_negociacao = 'PETR3' AND data = '2026-09-01'"
    ).fetchone()
    linha = next(
        l for l in a_vista if l[12:24].strip() == "PETR3" and l[2:10] == "20260901"
    )
    esperado = tuple(int(linha[a:b]) for _, a, b in cot._NUMEROS)
    assert petr3[:9] == esperado
    assert (
        petr3[4] == 5237 and petr3[7] == 56836696800 and petr3[8] == 1
    )  # PREULT, VOLTOT, FATCOT
    assert petr3[9:13] == (linha[230:242].strip(), linha[39:49].strip(), "02", "")
    assert petr3[13:] == (
        "b3:COTAHIST_M092026.ZIP",
        COLETA,
        cot.proveniencia.hash_sha256(caminho),
    )
    registro = conn.execute(
        "SELECT arquivo, data_geracao, fonte FROM cargas_cotahist"
    ).fetchone()
    assert registro == ("COTAHIST_M092026.ZIP", "2026-09-30", "b3:COTAHIST_M092026.ZIP")


def test_cotacoes_do_banco_iguais_as_do_arquivo(conn, oficial):
    caminho, _ = oficial
    _carregar(conn, caminho)
    assert cot.cotacoes_ate(conn, date(2026, 9, 3)) == cot.ler_zip(caminho)


def test_cotacoes_ate_d_sem_o_proprio_dia_nem_o_futuro(conn, oficial):
    caminho, _ = oficial
    _carregar(conn, caminho)
    assert {c.data for c in cot.cotacoes_ate(conn, date(2026, 9, 2))} == {
        date(2026, 9, 1)
    }
    assert cot.cotacoes_ate(conn, date(2026, 9, 1)) == []


@pytest.mark.parametrize("ticker", ["PETR3", "PETR4"])
def test_liquidez_em_d_pelo_banco_igual_a_do_arquivo_cortado_em_d(
    conn, oficial, ticker
):
    caminho, _ = oficial
    _carregar(conn, caminho)
    d = date(2026, 9, 2)
    do_arquivo = [c for c in cot.ler_zip(caminho) if c.data < d]
    assert liquidez.metricas(cot.cotacoes_ate(conn, d), ticker) == liquidez.metricas(
        do_arquivo, ticker
    )


# --- Janela de 63 pregões -----------------------------------------------------------------


def _pregoes(inicio, quantos):
    dias, dia = [], inicio
    while len(dias) < quantos:
        if dia.weekday() < 5:
            dias.append(dia)
        dia += timedelta(days=1)
    return dias


def _historico(tmp_path, dias, volume_depois=None, corte=None):
    linhas = []
    for dia in dias:
        volume = "000000000100000000"  # R$ 1.000.000,00 por pregão
        if corte is not None and dia >= corte and volume_depois is not None:
            volume = volume_depois
        linhas.append(_linha(DATA=dia.strftime("%Y%m%d"), CODNEG="TST3", VOLTOT=volume))
        if dia.day % 2:  # o outro código só negocia nos dias ímpares
            linhas.append(_linha(DATA=dia.strftime("%Y%m%d"), CODNEG="OUT3"))
    return _zip(tmp_path / "COTAHIST_A2025.ZIP", linhas)


def test_janela_de_63_pregoes_ate_d_sem_olhar_o_futuro(conn, tmp_path):
    dias = _pregoes(date(2025, 1, 2), 80)
    corte = dias[70]
    _carregar(
        conn,
        _historico(tmp_path, dias, volume_depois="000000000000000001", corte=corte),
    )
    janela = cot.cotacoes_ate(conn, corte)
    assert sorted({c.data for c in janela}) == dias[7:70]
    bloco = liquidez.metricas(janela, "TST3")
    assert (
        bloco["janelas"]["63"]["pregoes"] == 63
        and bloco["janelas"]["63"]["incompleta"] is False
    )
    assert (
        bloco["janelas"]["63"]["volume_mediano"] == 1_000_000.0
    )  # o volume depois de D não entra
    assert bloco["data_final"] == dias[69].isoformat()
    # as regras da 2B sobre o bloco: presença de 100% e R$ 1 milhão passam o mínimo das ações
    assert (
        liquidez.avaliar(bloco, janela=63, presenca_min=0.8, volume_min=500_000) is None
    )
    meio = liquidez.metricas(janela, "OUT3")["janelas"]["63"]
    assert 0 < meio["presenca"] < 1  # dia sem negócio no código conta zero


def test_menos_de_63_pregoes_antes_de_d_janela_incompleta(conn, tmp_path):
    dias = _pregoes(date(2025, 1, 2), 30)
    _carregar(conn, _historico(tmp_path, dias))
    bloco = liquidez.metricas(
        cot.cotacoes_ate(conn, dias[-1] + timedelta(days=1)), "TST3"
    )
    assert bloco["janelas"]["63"]["incompleta"] is True
    assert liquidez.avaliar(bloco, janela=63, presenca_min=0.8, volume_min=500_000) == {
        "aviso": "liquidez não medida: janela incompleta"
    }


# --- Idempotência, conflitos, recusas e atomicidade --------------------------------------


def test_mesmo_arquivo_nao_e_lido_de_novo(conn, oficial):
    caminho, _ = oficial
    primeiro = _carregar(conn, caminho)
    segundo = _carregar(conn, caminho, coleta="2026-11-12T12:00:00+00:00")
    assert segundo == {"hash_sha256": primeiro["hash_sha256"], "ja_carregado": True}
    assert _contar(conn) == 4 and _contar(conn, "cargas_cotahist") == 1


def test_outro_arquivo_com_as_mesmas_linhas_so_conta_repetidas(conn, oficial, tmp_path):
    caminho, linhas = oficial
    _carregar(conn, caminho)
    copia = _zip(tmp_path / "COTAHIST_A2026.ZIP", linhas)
    resumo = _carregar(conn, copia, coleta="2026-11-12T12:00:00+00:00")
    assert (
        resumo["inseridas"] == 0
        and resumo["repetidas"] == 4
        and resumo["total_conflitos"] == 0
    )
    assert _contar(conn) == 4 and _contar(conn, "cargas_cotahist") == 2


def test_mesma_linha_com_numero_diferente_e_conflito_e_fica_a_gravada(
    conn, oficial, tmp_path
):
    caminho, linhas = oficial
    _carregar(conn, caminho)
    alvo = next(i for i, l in enumerate(linhas) if l[:2] == "01" and l[24:27] == "010")
    mudada = list(linhas)
    mudada[alvo] = linhas[alvo][:108] + "0000000009999" + linhas[alvo][121:]
    resumo = _carregar(conn, _zip(tmp_path / "x.ZIP", mudada))
    assert resumo["total_conflitos"] == 1
    chave = resumo["conflitos"][0]
    assert (
        chave["codigo_negociacao"] == linhas[alvo][12:24].strip()
        and chave["data"] == "2026-09-01"
    )
    fechamento = conn.execute(
        "SELECT fechamento_centavos FROM precos WHERE data = ? AND codigo_negociacao = ?",
        (chave["data"], chave["codigo_negociacao"]),
    ).fetchone()
    assert fechamento == (int(linhas[alvo][108:121]),)


@pytest.mark.parametrize(
    ("campo", "valor", "motivo"),
    [
        ("DATA", "20251399", "campo ilegível"),
        ("FATCOT", "0000000", "fator de cotação inválido"),
        ("VOLTOT", "00000000000000000x", "campo ilegível"),
    ],
)
def test_registro_ilegivel_recusado_e_o_resto_entra(
    conn, tmp_path, campo, valor, motivo
):
    linhas = [_linha(), _linha(CODNEG="OUT3"), _linha(**{campo: valor}, CODNEG="RUI3")]
    resumo = _carregar(conn, _zip(tmp_path / "x.ZIP", linhas))
    assert resumo["total_recusadas"] == 1
    assert resumo["recusadas"][0]["linha"] == 3 and resumo["recusadas"][0][
        "motivo"
    ].startswith(motivo)
    assert {c for (c,) in conn.execute("SELECT codigo_negociacao FROM precos")} == {
        "TST3",
        "OUT3",
    }


def test_falha_no_meio_nao_deixa_linha_parcial(conn, oficial, monkeypatch):
    caminho, _ = oficial

    def falhar(*args):
        raise OSError("disco")

    monkeypatch.setattr(cot, "data_de_geracao", falhar)
    with pytest.raises(OSError):
        _carregar(conn, caminho)
    assert _contar(conn) == 0 and _contar(conn, "cargas_cotahist") == 0
    assert conn.in_transaction is False


def test_zip_sem_arquivo_e_recusado_sem_gravar(conn, tmp_path):
    caminho = tmp_path / "vazio.ZIP"
    with zipfile.ZipFile(caminho, "w"):
        pass
    with pytest.raises(zipfile.BadZipFile, match="ZIP sem arquivo"):
        _carregar(conn, caminho)
    assert _contar(conn, "cargas_cotahist") == 0


@pytest.mark.parametrize(("fonte", "coleta"), [("", COLETA), ("f", "")])
def test_fonte_e_coleta_obrigatorias(conn, oficial, fonte, coleta):
    with pytest.raises(ValueError, match="^fonte e coleta são obrigatórias$"):
        cot.carregar(conn, oficial[0], fonte=fonte, coleta=coleta)


@pytest.mark.parametrize("tabela", ["precos", "cargas_cotahist"])
def test_so_insercao(conn, oficial, tabela):
    _carregar(conn, oficial[0])
    antes = conn.execute(f"SELECT * FROM {tabela}").fetchall()
    for sql in (f"UPDATE {tabela} SET fonte = 'x'", f"DELETE FROM {tabela}"):
        with pytest.raises(sqlite3.IntegrityError, match=f"{tabela} é só de inserção"):
            conn.execute(sql)
    colunas = [c[1] for c in conn.execute(f"PRAGMA table_info({tabela})")]
    with pytest.raises(sqlite3.IntegrityError, match=f"{tabela} é só de inserção"):
        conn.execute(
            f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES ({', '.join('?' * len(colunas))})",
            antes[0],
        )
    assert conn.execute(f"SELECT * FROM {tabela}").fetchall() == antes


def test_migracao_006_sobre_o_banco_da_005_sem_perda(tmp_path):
    import shutil

    ate_005, ate_006 = tmp_path / "ate_005", tmp_path / "ate_006"
    ate_005.mkdir()
    ate_006.mkdir()
    for _, arquivo in migracoes.listar():
        if arquivo.name < "006":
            shutil.copy(arquivo, ate_005 / arquivo.name)
        if arquivo.name < "007":
            shutil.copy(arquivo, ate_006 / arquivo.name)
    banco = tmp_path / "b.db"
    with closing(sqlite3.connect(banco)) as c:
        assert migracoes.aplicar(c, ate_005) == [1, 2, 3, 4, 5]
        c.execute("INSERT INTO carteira_real VALUES ('TST3', 10, 9.5, '2026-01-02')")
        c.commit()
        antes = c.execute("SELECT * FROM carteira_real").fetchall()
    with closing(sqlite3.connect(banco)) as c:
        assert migracoes.aplicar(c, ate_006) == [6]
        assert c.execute("SELECT * FROM carteira_real").fetchall() == antes


def test_outro_mercado_nao_e_gravado(conn, tmp_path):
    linhas = [_linha(), _linha(CODNEG="TST3F", TPMERC="020")]
    resumo = _carregar(conn, _zip(tmp_path / "x.ZIP", linhas))
    assert resumo["inseridas"] == 1
    assert [c for (c,) in conn.execute("SELECT codigo_negociacao FROM precos")] == [
        "TST3"
    ]


# --- Lacunas da mutação -------------------------------------------------------------------


def test_registro_bruto_campos_vizinhos_e_dezembro():
    linha = _linha(DATA="20251230", ESPECI="ON", PRAZOT="030", CODBDI="02")
    registro = cot.registro_bruto(linha)
    assert registro["data"] == "2025-12-30"
    assert registro["especificacao"] == "ON" and registro["prazo"] == "030"
    with pytest.raises(
        cot.LinhaRecusada, match="^registro 01 truncado: 241 caracteres$"
    ):
        cot.registro_bruto(linha[:241])
    assert cot.registro_bruto(linha[:242]) is not None
    assert cot.registro_bruto("00" + linha[2:]) is None  # header


def test_fator_invalido_com_o_texto_do_campo():
    with pytest.raises(
        cot.LinhaRecusada, match=r"^fator de cotação inválido: '0000000'$"
    ):
        cot.registro_bruto(_linha(FATCOT="0000000"))


def test_varios_conflitos_e_recusas_contados_com_listas_limitadas(
    conn, tmp_path, monkeypatch
):
    monkeypatch.setattr(cot, "LIMITE_REGISTROS", 1)
    base = [_linha(CODNEG="AAA3"), _linha(CODNEG="BBB3")]
    _carregar(conn, _zip(tmp_path / "a.ZIP", base))
    linhas = [
        _linha(CODNEG="AAA3", PREULT="0000000099999"),
        _linha(DATA="20251399", CODNEG="RUI3"),
        _linha(CODNEG="BBB3", PREULT="0000000099999"),
        _linha(FATCOT="0000000", CODNEG="RUI4"),
        _linha(CODNEG="CCC3"),
    ]
    resumo = _carregar(
        conn, _zip(tmp_path / "b.ZIP", linhas), coleta="2026-11-12T12:00:00+00:00"
    )
    assert resumo["ja_carregado"] is False
    assert resumo["total_conflitos"] == 2 and len(resumo["conflitos"]) == 1
    assert resumo["total_recusadas"] == 2 and len(resumo["recusadas"]) == 1
    assert resumo["inseridas"] == 1  # a linha depois das recusadas também entra
    import json

    gravado = json.loads(
        conn.execute(
            "SELECT resumo_json FROM cargas_cotahist WHERE arquivo = 'b.ZIP'"
        ).fetchone()[0]
    )
    assert gravado == resumo


def test_leitura_com_especificacao_vazia_e_fator_mil(conn, tmp_path):
    linhas = [_linha(ESPECI="", CODISI="", FATCOT="0001000", PREULT="0000000012345")]
    _carregar(conn, _zip(tmp_path / "x.ZIP", linhas))
    (cotacao,) = cot.cotacoes_ate(conn, date(2026, 1, 6))
    assert cotacao.especificacao == "" and cotacao.isin == ""
    assert cotacao.fechamento == pytest.approx(123.45 / 1000)
    assert cotacao == next(cot.parsear_linhas(linhas))


def test_mesmo_codigo_e_dia_com_outro_codbdi_ou_prazo_e_outra_linha(conn, tmp_path):
    linhas = [_linha(), _linha(CODBDI="96"), _linha(PRAZOT="030")]
    resumo = _carregar(conn, _zip(tmp_path / "x.ZIP", linhas))
    assert resumo["inseridas"] == 3 and _contar(conn) == 3


def test_fator_de_cotacao_positivo_no_banco(conn):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        conn.execute(
            "INSERT INTO precos (data, codigo_negociacao, tipo_mercado, codbdi, abertura_centavos, "
            "maxima_centavos, minima_centavos, media_centavos, fechamento_centavos, negocios, "
            "quantidade, volume_centavos, fator_cotacao, fonte, coleta, hash_sha256) "
            "VALUES ('2026-01-05', 'X', '010', '02', 1, 1, 1, 1, 1, 1, 1, 1, 0, 'f', 'c', 'h')"
        )


@pytest.mark.parametrize(
    ("campo", "valor", "coluna"),
    [
        ("VOLTOT", "-00000000000000001", "volume_centavos"),
        ("PREULT", "+000000012345", "fechamento_centavos"),
        ("TOTNEG", " 0042", "negocios"),
        ("QUATOT", "0_0000000000001500", "quantidade"),
        ("DATA", "2026-105", "DATA"),
        ("DATA", "X0260105", "DATA"),
        ("VOLTOT", "²" + "0" * 17, "volume_centavos"),
    ],
)
def test_numero_com_sinal_espaco_ou_sublinhado_e_recusado(campo, valor, coluna):
    with pytest.raises(cot.LinhaRecusada, match=f"^campo ilegível: {coluna} "):
        cot.registro_bruto(_linha(**{campo: valor}))


def test_registro_truncado_no_arquivo_e_recusado(conn, tmp_path):
    linhas = [_linha(), _linha(CODNEG="OUT3")[:200]]
    resumo = _carregar(conn, _zip(tmp_path / "x.ZIP", linhas))
    assert resumo["total_recusadas"] == 1
    assert resumo["recusadas"][0]["motivo"].startswith("registro 01 truncado")


def test_codbdi_com_letra_nao_e_campo_numerico():
    assert cot.registro_bruto(_linha(CODBDI="A1"))["codbdi"] == "A1"


def test_cotacoes_ate_recusa_instante_e_janela_vazia(conn):
    from datetime import datetime

    with pytest.raises(
        TypeError,
        match=r"^cotacoes_ate recebe o dia local de D \(date\), não um instante$",
    ):
        cot.cotacoes_ate(conn, datetime(2026, 9, 2, 10, tzinfo=UTC))
    with pytest.raises(ValueError, match="^pregoes deve ser positivo: 0$"):
        cot.cotacoes_ate(conn, date(2026, 9, 2), pregoes=0)


def test_janela_de_um_pregao(conn, oficial):
    _carregar(conn, oficial[0])
    assert {c.data for c in cot.cotacoes_ate(conn, date(2026, 9, 3), pregoes=1)} == {
        date(2026, 9, 2)
    }
