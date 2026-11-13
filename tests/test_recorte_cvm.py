"""F3-3d (DD-61): `CVMProvider.recorte_em`, o ZIP baixado visto no dia de D.

ZIPs pequenos no leiaute oficial: índice com duas versões de um documento e a DRE com
linhas das duas (fica só a da versão vigente em D) e de um documento com entrega ilegível.
"""

import os
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

import cvm_provider
from sentinela.data import proveniencia

CNPJ = "11.111.111/0001-11"
INDICE = (
    "CNPJ_CIA;DT_REFER;VERSAO;DT_RECEB\n"
    f"{CNPJ};2023-12-31;1;2024-03-01\n"
    f"{CNPJ};2023-12-31;2;2024-04-10\n"
    "22.222.222/0001-22;2023-12-31;1;data ilegível\n"
)
DRE = (
    "CNPJ_CIA;DT_REFER;VERSAO;CD_CONTA;VL_CONTA\n"
    f"{CNPJ};2023-12-31;2;3.11;10\n"
    f"{CNPJ};2023-12-31;1;3.11;9\n"
    "22.222.222/0001-22;2023-12-31;1;3.11;5\n"
)


def _zip(caminho: Path, indice: str | None = INDICE) -> Path:
    with zipfile.ZipFile(caminho, "w") as z:
        if indice is not None:
            z.writestr("dfp_cia_aberta_2023.csv", indice)
        z.writestr("dfp_cia_aberta_DRE_con_2023.csv", DRE)
        z.writestr("dfp_cia_aberta_parecer_2023.csv", "OUTRA;COLUNA\n1;2\n")
    os.utime(caminho, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))
    return caminho


def _provedor(tmp_path, original):
    p = cvm_provider.CVMProvider(cache_dir=str(tmp_path / "cache"))
    p.baixar_dfp = lambda ano: original
    p.baixar_itr = lambda ano: original
    return p


def _membro(caminho, nome):
    with zipfile.ZipFile(caminho) as z:
        return z.read(nome).decode("latin-1").splitlines()


def _sp(ano, mes, dia):
    return datetime(ano, mes, dia, 15, tzinfo=UTC)  # meio-dia em São Paulo


@pytest.mark.parametrize(
    ("d", "versoes", "dre"),
    [
        (_sp(2024, 3, 1), [], []),  # entregue no próprio dia de D: ainda não
        (_sp(2024, 3, 2), ["1"], ["1"]),  # vigente a 1: só as linhas dela
        (_sp(2024, 4, 10), ["1"], ["1"]),
        (_sp(2024, 4, 11), ["1", "2"], ["2"]),
    ],
)
def test_indice_e_numeros_pela_entrega_antes_do_dia(tmp_path, d, versoes, dre):
    original = _zip(tmp_path / "dfp.zip")
    recortado = _provedor(tmp_path, original).recorte_em(d).baixar_dfp(2023)
    indice = _membro(recortado, "dfp_cia_aberta_2023.csv")
    assert indice[0] == "CNPJ_CIA;DT_REFER;VERSAO;DT_RECEB"
    assert [linha.split(";")[2] for linha in indice[1:]] == versoes
    linhas = _membro(recortado, "dfp_cia_aberta_DRE_con_2023.csv")
    assert linhas[0] == "CNPJ_CIA;DT_REFER;VERSAO;CD_CONTA;VL_CONTA"
    assert [linha.split(";")[2] for linha in linhas[1:]] == dre
    assert _membro(recortado, "dfp_cia_aberta_parecer_2023.csv") == [
        "OUTRA;COLUNA",
        "1;2",
    ]


def test_sem_indice_nenhum_numero(tmp_path):
    original = _zip(tmp_path / "dfp.zip", indice=None)
    recortado = (
        _provedor(tmp_path, original).recorte_em(_sp(2025, 1, 1)).baixar_itr(2023)
    )
    with zipfile.ZipFile(recortado) as z:
        assert "dfp_cia_aberta_2023.csv" not in z.namelist()
    assert _membro(recortado, "dfp_cia_aberta_DRE_con_2023.csv") == [
        "CNPJ_CIA;DT_REFER;VERSAO;CD_CONTA;VL_CONTA"
    ]


def test_recorte_guarda_a_coleta_do_download_com_o_proprio_hash(tmp_path):
    original = _zip(tmp_path / "dfp.zip")
    provedor = _provedor(tmp_path, original)
    recorte = provedor.recorte_em(_sp(2024, 4, 11))
    caminho = recorte.baixar_dfp(2023)
    assert caminho.stat().st_mtime_ns == original.stat().st_mtime_ns
    assert (
        caminho.parent.name == "2024-04-11" and caminho.parent.parent.name == "recorte"
    )
    assert not proveniencia.caminho_lateral(caminho).exists()
    registro = proveniencia.registrar_arquivo(
        caminho, "https://cvm/dfp.zip", "DFP", "2023"
    )
    assert registro.data_coleta == proveniencia.data_da_coleta(original)
    assert registro.hash_sha256 == proveniencia.hash_sha256(caminho)
    assert not list(caminho.parent.glob("*.tmp"))
    antes = caminho.read_bytes()
    caminho.write_bytes(b"marcador")  # o segundo pedido reaproveita o recorte do disco
    assert recorte.baixar_dfp(2023).read_bytes() == b"marcador"
    caminho.write_bytes(antes)
    assert recorte.recorte_em(_sp(2024, 3, 2)).dia == date(2024, 3, 2)
    assert recorte.cache_dir == provedor.cache_dir


def test_linha_so_quebra_em_cr_e_lf():
    conteudo = (
        "CNPJ_CIA;DT_REFER;VERSAO;DS_CONTA\r\nA;B;1;Outras\x85 receitas\r\n".encode(
            "latin-1"
        )
    )
    assert cvm_provider._linhas(conteudo) == [
        "CNPJ_CIA;DT_REFER;VERSAO;DS_CONTA\r\n",
        "A;B;1;Outras\x85 receitas\r\n",
    ]
    assert cvm_provider._so_vigentes(conteudo, {("A", "B"): 1}) == conteudo


def test_recorte_exige_fuso_e_usa_o_dia_de_sao_paulo(tmp_path):
    provedor = _provedor(tmp_path, _zip(tmp_path / "dfp.zip"))
    with pytest.raises(ValueError, match="fuso"):
        provedor.recorte_em(datetime(2024, 4, 11))  # noqa: DTZ001
    assert provedor.recorte_em(datetime(2024, 4, 11, 2, 59, tzinfo=UTC)).dia == date(
        2024, 4, 10
    )


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("2024-03-01", False), ("2024-02-29", True), (" 2024-02-29 10:00", True), ("", False),
     (None, False), ("29/02/2024", False)],
)  # fmt: skip
def test_recebido_antes(texto, esperado):
    assert cvm_provider._recebido_antes(texto, date(2024, 3, 1)) is esperado


@pytest.mark.parametrize(
    ("texto", "esperado"), [("2", 2), (" 3 ", 3), ("²", -1), ("x", -1)]
)
def test_inteiro(texto, esperado):
    assert cvm_provider._inteiro(texto) == esperado


def test_so_vigentes_linha_curta_e_vazio():
    assert cvm_provider._so_vigentes(b"", {}) == b""
    conteudo = "CNPJ_CIA;DT_REFER;VERSAO\r\nA;B\r\nA;B;1\r\n".encode("latin-1")
    assert cvm_provider._so_vigentes(conteudo, {("A", "B"): 1}) == (
        "CNPJ_CIA;DT_REFER;VERSAO\r\nA;B;1\r\n".encode("latin-1")
    )


@pytest.mark.parametrize(("dia", "recorta"), [(12, True), (13, False)])
def test_cascata_so_recorta_data_passada(monkeypatch, dia, recorta):
    """F3-3d: com as_of de hoje (São Paulo), a cascata lê os arquivos como antes."""
    import market_engine
    from market_engine import MarketEngine

    monkeypatch.setattr(market_engine, "_hoje_sp", lambda: date(2026, 10, 13))
    cvm = Mock()
    motor = MarketEngine.__new__(MarketEngine)
    motor.cvm = cvm
    motor._buscar_cvm(
        "TSTA3", {"riscos_dados": []}, as_of=datetime(2026, 10, dia, 15, tzinfo=UTC)
    )
    assert cvm.recorte_em.called is recorta


@pytest.fixture
def relogio_em_utc():
    """O relógio do sistema em UTC, como num CI; o fuso volta ao do processo no fim."""
    import time

    antes = os.environ.get("TZ")
    os.environ["TZ"] = "UTC"
    time.tzset()
    try:
        yield
    finally:
        if antes is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = antes
        time.tzset()


def test_hoje_e_o_dia_de_sao_paulo_e_nao_o_do_sistema(relogio_em_utc):
    import market_engine

    # 22h de 13/10 em São Paulo é 14/10 em UTC: o hoje continua 13/10
    assert market_engine._hoje_sp(datetime(2026, 10, 14, 1, 0, tzinfo=UTC)) == date(
        2026, 10, 13
    )
    assert market_engine._hoje_sp(datetime(2026, 10, 14, 3, 0, tzinfo=UTC)) == date(
        2026, 10, 14
    )
    assert isinstance(market_engine._hoje_sp(), date)


def test_cascata_com_versao_vigente_sem_numeros_no_arquivo_abstem(
    tmp_path, monkeypatch
):
    """DD-34 no recorte: a versão 1 foi entregue antes de D, mas o arquivo só guarda os
    números da 2 (entregue depois). A cascata não lê os números da 2 nem volta a 2022 no
    snapshot: o exercício de 2023 fica sem valores e o snapshot se abstém."""
    from apoio_escopo import de_empresa

    from market_engine import MarketEngine
    from tests.regressao.test_bug_2c_62_qualidade_produtor import CNPJ as CIA_SINTETICA
    from tests.regressao.test_bug_2c_62_qualidade_produtor import fonte_anual

    p = fonte_anual(tmp_path, monkeypatch)
    novo = tmp_path / "dfp_2023_v2.zip"
    with zipfile.ZipFile(p.baixar_dfp(2023)) as zi, zipfile.ZipFile(novo, "w") as zo:
        for nome in zi.namelist():
            texto = zi.read(nome).decode("latin-1")
            if nome == "dfp_cia_aberta_2023.csv":
                texto = (
                    "CNPJ_CIA;DT_REFER;VERSAO;DT_RECEB\n"
                    f"{CIA_SINTETICA};2023-12-31;1;2024-03-01\n"
                    f"{CIA_SINTETICA};2023-12-31;2;2024-04-10\n"
                )
            else:
                texto = texto.replace(";2023-12-31;1;", ";2023-12-31;2;")
            zo.writestr(nome, texto.encode("latin-1"))
    base = p.baixar_dfp
    monkeypatch.setattr(p, "baixar_dfp", lambda ano: novo if ano == 2023 else base(ano))
    import market_engine

    monkeypatch.setattr(market_engine, "_hoje_sp", lambda: date(2026, 10, 13))
    motor = MarketEngine.__new__(MarketEngine)
    motor.cvm = p
    dados = de_empresa(
        {"ticker": "TSTA3", "cd_cvm": 9999, "preco_atual": 100, "especie": "ON"}
    )
    assert motor._buscar_cvm("TSTA3", dados, as_of=_sp(2024, 3, 15)) is False
    exercicios = {e["exercicio"]: e for e in dados["serie_cvm"]["exercicios"]}
    assert exercicios[2022]["versao"] == "1"
    assert (
        exercicios[2023].get("versao") is None
        and exercicios[2023].get("dt_refer") is None
    )
    assert dados.get("lucro_liquido") is None  # nem o −2 da versão 2, nem o 12 de 2022
