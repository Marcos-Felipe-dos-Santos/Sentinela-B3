"""COTAHIST: linhas sintéticas montadas pelo layout oficial da B3 (sem rede)."""

import os
import zipfile
from datetime import UTC, date, datetime

import pytest

from sentinela.data.providers import b3_cotahist as cot

# Layout oficial do registro 01: (campo, largura). Soma 245.
_LAYOUT = [
    ("TIPREG", 2), ("DATA", 8), ("CODBDI", 2), ("CODNEG", 12), ("TPMERC", 3),
    ("NOMRES", 12), ("ESPECI", 10), ("PRAZOT", 3), ("MODREF", 4),
    ("PREABE", 13), ("PREMAX", 13), ("PREMIN", 13), ("PREMED", 13),
    ("PREULT", 13), ("PREOFC", 13), ("PREOFV", 13),
    ("TOTNEG", 5), ("QUATOT", 18), ("VOLTOT", 18), ("PREEXE", 13),
    ("INDOPC", 1), ("DATVEN", 8), ("FATCOT", 7), ("PTOEXE", 13),
    ("CODISI", 12), ("DISMES", 3),
]  # fmt: skip


def _linha(**campos):
    base = {
        "TIPREG": "01", "DATA": "20260105", "CODBDI": "02", "CODNEG": "TST3",
        "TPMERC": "010", "NOMRES": "TESTE", "ESPECI": "ON", "PRAZOT": "",
        "MODREF": "R$", "PREULT": "0000000012345", "TOTNEG": "00042",
        "QUATOT": "000000000000001500", "VOLTOT": "000000000000987654",
        "FATCOT": "0000001", "CODISI": "BRTST3ACNOR0", "DISMES": "100",
    }  # fmt: skip
    base.update(campos)
    partes = []
    for nome, largura in _LAYOUT:
        valor = base.get(nome, "")
        if nome in ("CODNEG", "NOMRES", "ESPECI", "PRAZOT", "MODREF", "CODISI"):
            partes.append(valor.ljust(largura))
        else:
            partes.append(valor.rjust(largura, "0"))
    linha = "".join(partes)
    assert len(linha) == 245
    return linha


def test_registro_01_segue_o_layout_oficial():
    c = next(cot.parsear_linhas([_linha()]))
    assert c.data == date(2026, 1, 5)
    assert c.codigo_negociacao == "TST3"
    assert c.codbdi == "02"
    assert c.tipo_mercado == "010"
    assert c.especificacao == "ON"
    assert c.isin == "BRTST3ACNOR0"
    assert c.fechamento == pytest.approx(123.45)
    assert c.volume_financeiro == pytest.approx(9876.54)
    assert c.quantidade == 1500
    assert c.negocios == 42
    assert c.fator_cotacao == 1


def test_campos_vizinhos_nao_vazam_para_o_fechamento():
    linha = _linha(
        PREMED="9999999999999", PREOFC="8888888888888", PREABE="7777777777777"
    )
    assert next(cot.parsear_linhas([linha])).fechamento == pytest.approx(123.45)


def test_fator_de_cotacao_mil():
    c = next(cot.parsear_linhas([_linha(PREULT="0000000500000", FATCOT="0001000")]))
    assert c.fechamento == pytest.approx(5.0)  # R$ 5.000,00 por lote de 1.000
    assert c.fator_cotacao == 1000
    assert c.volume_financeiro == pytest.approx(9876.54)  # volume não leva o fator
    assert c.quantidade == 1500


def test_fator_zero_e_rejeitado():
    with pytest.raises(ValueError):
        cot.parsear_linha(_linha(FATCOT="0000000"))


def test_header_e_trailer_ignorados():
    header = "00COTAHIST.2026BOVESPA 20260131".ljust(245)
    trailer = "99COTAHIST.2026BOVESPA 20260131".ljust(245)
    assert list(cot.parsear_linhas([header, _linha(), trailer])) != []
    assert len(list(cot.parsear_linhas([header, trailer]))) == 0
    assert cot.parsear_linha("") is None
    assert cot.parsear_linha("01curta") is None


def test_filtra_mercado_a_vista():
    linhas = [
        _linha(CODNEG="VISTA3", TPMERC="010"),
        _linha(CODNEG="FRAC3F", TPMERC="020"),
        _linha(CODNEG="OPC3", TPMERC="070"),
    ]
    assert [c.codigo_negociacao for c in cot.parsear_linhas(linhas)] == ["VISTA3"]
    todos = cot.parsear_linhas(linhas, mercados=("010", "020"))
    assert [c.codigo_negociacao for c in todos] == ["VISTA3", "FRAC3F"]


def test_quebra_de_linha_e_aceita():
    assert len(list(cot.parsear_linhas([_linha() + "\r\n", _linha() + "\n"]))) == 2


def test_ler_zip(tmp_path):
    caminho = tmp_path / "COTAHIST_M012026.ZIP"
    conteudo = "\r\n".join(
        ["00COTAHIST".ljust(245), _linha(), _linha(TPMERC="020"), "99".ljust(245)]
    )
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("COTAHIST_M012026.TXT", conteudo.encode("latin-1"))
    assert [c.tipo_mercado for c in cot.ler_zip(caminho)] == ["010"]


def _zip_vazio(caminho, marca="x"):
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("a.txt", marca)


AGORA = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def _baixado_em(caminho, instante):
    os.utime(caminho, (instante.timestamp(), instante.timestamp()))


def _envelhecer(caminho, dias):
    t = AGORA.timestamp() - dias * 86400
    os.utime(caminho, (t, t))


@pytest.fixture
def baixador(monkeypatch):
    chamadas = []

    def falso(url, destino):
        chamadas.append((url, destino.name))
        _zip_vazio(destino, "novo")
        return destino

    monkeypatch.setattr(cot, "baixar_arquivo", falso)
    return chamadas


def test_mes_fechado_nunca_expira(tmp_path, baixador):
    existente = tmp_path / "COTAHIST_M122025.ZIP"
    _zip_vazio(existente)
    _baixado_em(existente, datetime(2026, 1, 10, 12, tzinfo=UTC))
    assert cot.baixar_mes(2025, 12, AGORA, tmp_path) == existente
    assert baixador == []


def test_mes_fechado_ausente_baixa_pela_url_oficial(tmp_path, baixador):
    cot.baixar_mes(2025, 12, AGORA, tmp_path)
    assert baixador == [
        (
            "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_M122025.ZIP",
            "COTAHIST_M122025.ZIP",
        )
    ]


def test_mes_corrente_expira_em_um_dia(tmp_path, baixador):
    existente = tmp_path / "COTAHIST_M012026.ZIP"
    _zip_vazio(existente)
    _envelhecer(existente, 0.9)
    cot.baixar_mes(2026, 1, AGORA, tmp_path)
    assert baixador == []
    _envelhecer(existente, 1.1)
    cot.baixar_mes(2026, 1, AGORA, tmp_path)
    assert len(baixador) == 1
    assert not existente.with_suffix(".old").exists()
    with zipfile.ZipFile(existente) as zf:
        assert zf.read("a.txt") == b"novo"


def test_falha_de_rede_mantem_a_copia_antiga(tmp_path, monkeypatch, caplog):
    existente = tmp_path / "COTAHIST_M012026.ZIP"
    _zip_vazio(existente, "antigo")
    _envelhecer(existente, 3)

    def quebrado(url, destino):
        raise ConnectionError("sem rede")

    monkeypatch.setattr(cot, "baixar_arquivo", quebrado)
    with caplog.at_level("WARNING"):
        assert cot.baixar_mes(2026, 1, AGORA, tmp_path) == existente
    with zipfile.ZipFile(existente) as zf:
        assert zf.read("a.txt") == b"antigo"
    assert "cópia antiga" in caplog.text


def test_mes_corrente_ausente_baixa(tmp_path, baixador):
    cot.baixar_mes(2026, 1, AGORA, tmp_path)
    assert len(baixador) == 1


def test_mes_futuro_do_mesmo_ano_nao_e_tratado_como_fechado(tmp_path, baixador):
    existente = tmp_path / "COTAHIST_M022026.ZIP"
    _zip_vazio(existente)
    _envelhecer(existente, 5)
    cot.baixar_mes(2026, 2, AGORA, tmp_path)
    assert len(baixador) == 1


def test_primeiro_e_ultimo_digito_de_cada_campo_numerico():
    linha = _linha(
        DATA="20261231",
        PREULT="9999999999999",
        TOTNEG="98765",
        QUATOT="987654321098765432",
        VOLTOT="987654321098765432",
        FATCOT="1000000",
        ESPECI="ABCDEFGHIJ",
        PRAZOT="123",
    )
    c = cot.parsear_linha(linha)
    assert c.data == date(2026, 12, 31)
    assert c.fechamento == pytest.approx(99999999999.99 / 1000000)
    assert c.negocios == 98765
    assert c.quantidade == 987654321098765432
    assert c.volume_financeiro == pytest.approx(9876543210987654.32)
    assert c.especificacao == "ABCDEFGHIJ"


def test_data_com_mes_e_dia_de_dois_digitos():
    assert cot.parsear_linha(_linha(DATA="20261121")).data == date(2026, 11, 21)


def test_linha_sem_o_preenchimento_final_ainda_vale_ate_o_isin():
    linha = _linha()
    assert cot.parsear_linha(linha[:242]).isin == "BRTST3ACNOR0"
    assert cot.parsear_linha(linha[:241]) is None


def test_fator_invalido_traz_o_valor_na_mensagem():
    with pytest.raises(ValueError, match="0000000"):
        cot.parsear_linha(_linha(FATCOT="0000000"))
    with pytest.raises(ValueError, match="fator de cotação"):
        cot.parsear_linha(_linha(FATCOT="0000000"))


def test_espaco_no_inicio_da_linha_nao_e_removido():
    assert cot.parsear_linha(" " + _linha()) is None
    assert list(cot.parsear_linhas([" " + _linha()])) == []


def test_ler_zip_decodifica_latin1(tmp_path):
    caminho = tmp_path / "c.zip"
    linha = _linha(NOMRES="AÇÃO", CODNEG="TST3")
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("c.txt", linha.encode("latin-1") + b"\n")
    assert cot.ler_zip(caminho, mercados=("010",))[0].codigo_negociacao == "TST3"
    assert cot.ler_zip(caminho, mercados=("999",)) == []


def test_mes_corrente_com_exatamente_um_dia_expira(tmp_path, baixador):
    existente = tmp_path / "COTAHIST_M012026.ZIP"
    _zip_vazio(existente)
    _envelhecer(existente, 1.0)
    cot.baixar_mes(2026, 1, AGORA, tmp_path)
    assert len(baixador) == 1


def test_cria_o_diretorio_de_cache_aninhado(tmp_path, baixador):
    cot.baixar_mes(2025, 12, AGORA, tmp_path / "a" / "b")
    assert (tmp_path / "a" / "b").is_dir()


def test_falha_de_rede_remove_o_arquivo_auxiliar(tmp_path, monkeypatch):
    existente = tmp_path / "COTAHIST_M012026.ZIP"
    _zip_vazio(existente)
    _envelhecer(existente, 3)
    monkeypatch.setattr(
        cot, "baixar_arquivo", lambda u, d: (_ for _ in ()).throw(OSError("x"))
    )
    cot.baixar_mes(2026, 1, AGORA, tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["COTAHIST_M012026.ZIP"]


def test_url_recebida_pelo_download_do_mes_corrente(tmp_path, baixador):
    existente = tmp_path / "COTAHIST_M012026.ZIP"
    _zip_vazio(existente)
    _envelhecer(existente, 3)
    cot.baixar_mes(2026, 1, AGORA, tmp_path)
    assert baixador[0][0].endswith("/COTAHIST_M012026.ZIP")


def test_mes_fechado_baixado_com_o_mes_em_curso_e_rebaixado(tmp_path, baixador):
    parcial = tmp_path / "COTAHIST_M012026.ZIP"
    _zip_vazio(parcial, "metade dos pregoes")
    _baixado_em(parcial, datetime(2026, 1, 15, 12, tzinfo=UTC))
    agora = datetime(2026, 2, 2, 12, tzinfo=UTC)
    cot.baixar_mes(2026, 1, agora, tmp_path)
    assert len(baixador) == 1
    with zipfile.ZipFile(parcial) as zf:
        assert zf.read("a.txt") == b"novo"


def test_mes_fechado_baixado_dentro_da_folga_ainda_e_rebaixado(tmp_path, baixador):
    existente = tmp_path / "COTAHIST_M012026.ZIP"
    _zip_vazio(existente)
    _baixado_em(existente, datetime(2026, 2, 2, 12, tzinfo=UTC))  # 1 dia após o fim
    cot.baixar_mes(2026, 1, datetime(2026, 2, 10, 12, tzinfo=UTC), tmp_path)
    assert len(baixador) == 1


def test_mes_fechado_baixado_apos_a_folga_nao_expira(tmp_path, baixador):
    existente = tmp_path / "COTAHIST_M012026.ZIP"
    _zip_vazio(existente)
    _baixado_em(existente, datetime(2026, 2, 5, 12, tzinfo=UTC))
    cot.baixar_mes(2026, 1, datetime(2026, 6, 1, 12, tzinfo=UTC), tmp_path)
    assert baixador == []


def test_virada_de_dezembro_para_janeiro(tmp_path, baixador):
    existente = tmp_path / "COTAHIST_M122025.ZIP"
    _zip_vazio(existente)
    _baixado_em(existente, datetime(2025, 12, 31, 12, tzinfo=UTC))
    cot.baixar_mes(2025, 12, datetime(2026, 1, 20, 12, tzinfo=UTC), tmp_path)
    assert len(baixador) == 1


def test_mes_calculado_no_fuso_da_b3(tmp_path, baixador):
    existente = tmp_path / "COTAHIST_M012026.ZIP"
    _zip_vazio(existente)
    # 01/02 01:00 UTC ainda é 31/01 em Brasília: janeiro é o mês em curso, vale o TTL.
    agora = datetime(2026, 2, 1, 1, tzinfo=UTC)
    _baixado_em(existente, datetime(2026, 1, 31, 23, tzinfo=UTC))
    cot.baixar_mes(2026, 1, agora, tmp_path)
    assert baixador == []


def test_excecao_inesperada_devolve_a_copia_antiga(tmp_path, monkeypatch):
    existente = tmp_path / "COTAHIST_M012026.ZIP"
    _zip_vazio(existente, "antigo")
    _envelhecer(existente, 3)

    def quebrado(url, destino):
        raise ValueError("inesperado")

    monkeypatch.setattr(cot, "baixar_arquivo", quebrado)
    with pytest.raises(ValueError):
        cot.baixar_mes(2026, 1, AGORA, tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["COTAHIST_M012026.ZIP"]


def test_zip_vazio_nao_conta_como_completo(tmp_path, baixador):
    # F2B-40 (BUG-2A-16): um ZIP sem arquivo, mesmo de mês fechado baixado depois da folga,
    # não é a cópia definitiva: segue o caminho do arquivo corrompido e é baixado de novo.
    existente = tmp_path / "COTAHIST_M122025.ZIP"
    with zipfile.ZipFile(existente, "w"):
        pass
    _envelhecer(
        existente, 2
    )  # baixado em 13/01/2026, depois do fim de dezembro e da folga
    assert cot.baixar_mes(2025, 12, AGORA, tmp_path) == existente
    assert len(baixador) == 1
    with pytest.raises(zipfile.BadZipFile):
        vazio = tmp_path / "vazio.zip"
        with zipfile.ZipFile(vazio, "w"):
            pass
        cot.ler_zip(vazio)


def test_so_zip_que_abre_e_traz_arquivo_conta_como_completo(tmp_path):
    # F2B-40: o fechamento do mês só vale para a cópia legível com o arquivo do mês.
    baixado_depois = datetime(2026, 1, 13, 12, tzinfo=UTC)
    com_arquivo = tmp_path / "COTAHIST_M122025.ZIP"
    _zip_vazio(com_arquivo)  # traz "a.txt"
    _baixado_em(com_arquivo, baixado_depois)
    assert cot._completo(com_arquivo, 2025, 12) is True
    corrompido = tmp_path / "COTAHIST_M112025.ZIP"
    corrompido.write_bytes(b"isto nao e um zip")
    _baixado_em(corrompido, baixado_depois)
    assert cot._completo(corrompido, 2025, 11) is False
