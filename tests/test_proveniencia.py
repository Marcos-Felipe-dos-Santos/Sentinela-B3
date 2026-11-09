"""Proveniência temporal dos dados coletados (F2A-32; ADR-0003, D16)."""

import dataclasses
import hashlib
import json
import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_core import SentinelaAI
from cvm_fii_provider import CVMFIIProvider
from cvm_provider import CVMProvider
from sentinela.data import proveniencia as prov
from sentinela.data.providers import b3_cotahist
from sentinela.data.referencia import fontes
from tests import test_referencia_fontes
from tests.test_market_engine import _engine, _historico

AGORA = test_referencia_fontes.AGORA
rede_simulada = test_referencia_fontes.rede_simulada

HASH = "a" * 64
CAMPOS = {
    "periodo_referencia",
    "data_entrega",
    "motivo_sem_entrega",
    "data_coleta",
    "documento",
    "versao",
    "fonte",
    "hash_sha256",
}


def _registro(**mudancas):
    base = {
        "periodo_referencia": "2025-12-31",
        "data_entrega": "2026-03-05",
        "motivo_sem_entrega": None,
        "data_coleta": "2026-10-08T12:00:00+00:00",
        "documento": "DFP",
        "versao": "1",
        "fonte": "https://dados.cvm.gov.br/x.zip",
        "hash_sha256": HASH,
    }
    return prov.Proveniencia(**{**base, **mudancas})


def _arquivo(
    caminho, conteudo=b"conteudo", instante=datetime(2026, 10, 8, 12, tzinfo=UTC)
):
    caminho.write_bytes(conteudo)
    os.utime(caminho, (instante.timestamp(), instante.timestamp()))
    return caminho


# ── o registro ───────────────────────────────────────────────────────────────


def test_registro_tem_todos_os_campos():
    registro = _registro()
    assert {f.name for f in dataclasses.fields(prov.Proveniencia)} == CAMPOS
    assert registro.para_dict() == {
        "periodo_referencia": "2025-12-31",
        "data_entrega": "2026-03-05",
        "motivo_sem_entrega": None,
        "data_coleta": "2026-10-08T12:00:00+00:00",
        "documento": "DFP",
        "versao": "1",
        "fonte": "https://dados.cvm.gov.br/x.zip",
        "hash_sha256": HASH,
    }
    assert prov.Proveniencia.de_dict(registro.para_dict()) == registro
    with pytest.raises(dataclasses.FrozenInstanceError):
        registro.versao = "2"


def test_hash_muda_com_o_conteudo(tmp_path):
    a = _arquivo(tmp_path / "a.zip", b"um")
    b = _arquivo(tmp_path / "b.zip", b"dois")
    assert prov.hash_sha256(a) == hashlib.sha256(b"um").hexdigest()
    assert prov.hash_sha256(a) != prov.hash_sha256(b)


def test_hash_le_arquivo_maior_que_o_bloco(tmp_path):
    conteudo = b"x" * (prov._BLOCO_HASH + 10)
    assert (
        prov.hash_sha256(_arquivo(tmp_path / "a", conteudo))
        == hashlib.sha256(conteudo).hexdigest()
    )


def test_entrega_ausente_fica_none_com_motivo():
    registro = _registro(data_entrega=None, motivo_sem_entrega="a fonte não informa")
    assert registro.data_entrega is None
    assert registro.motivo_sem_entrega == "a fonte não informa"
    with pytest.raises(ValueError, match="entrega"):
        _registro(data_entrega=None)


def test_entrega_e_motivo_juntos_sao_recusados():
    with pytest.raises(ValueError, match="não os dois"):
        _registro(motivo_sem_entrega="qualquer")


@pytest.mark.parametrize(
    "mudanca",
    [
        {"documento": "Balanço"},
        {"data_entrega": "05/03/2026"},
        {"data_coleta": ""},
        {"fonte": ""},
        {"hash_sha256": "A" * 64},
        {"hash_sha256": "a" * 63},
    ],
)
def test_registro_invalido_e_recusado(mudanca):
    with pytest.raises(ValueError):
        _registro(**mudanca)


@pytest.mark.parametrize("documento", sorted(prov.DOCUMENTOS))
def test_documentos_aceitos(documento):
    assert _registro(documento=documento).documento == documento


def test_coleta_nao_substitui_entrega(tmp_path):
    caminho = _arquivo(tmp_path / "dfp_2025.zip")
    registro = prov.registrar_arquivo(caminho, "https://x/dfp_2025.zip", "DFP", "2025")
    assert registro.data_coleta == "2026-10-08T12:00:00+00:00"
    assert registro.data_entrega is None
    assert registro.motivo_sem_entrega == prov.MOTIVO_ARQUIVO_AGREGADO
    documento = registro.do_documento(
        "2025-12-31", "2", None, prov.MOTIVO_DOCUMENTO_FORA_DO_INDICE
    )
    assert documento.data_entrega is None
    assert documento.motivo_sem_entrega == prov.MOTIVO_DOCUMENTO_FORA_DO_INDICE
    assert documento.data_coleta == registro.data_coleta


def test_do_documento_troca_periodo_versao_e_entrega():
    arquivo = _registro(
        periodo_referencia="2025",
        versao=None,
        data_entrega=None,
        motivo_sem_entrega="x",
    )
    documento = arquivo.do_documento("2025-12-31", "3", "2026-03-05", "ignorado")
    assert documento == dataclasses.replace(
        arquivo,
        periodo_referencia="2025-12-31",
        versao="3",
        data_entrega="2026-03-05",
        motivo_sem_entrega=None,
    )


# ── o arquivo lateral ────────────────────────────────────────────────────────


def test_registrar_grava_ao_lado_e_relê(tmp_path):
    caminho = _arquivo(tmp_path / "a.zip")
    registro = prov.registrar_arquivo(
        caminho, "https://x/a.zip", "COTAHIST", "2026-09", entrega="2026-09-30"
    )
    lateral = tmp_path / "a.zip.proveniencia.json"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.zip", lateral.name]
    bruto = json.loads(lateral.read_text(encoding="utf-8"))
    assert bruto["registro"] == registro.para_dict()
    assert bruto["tamanho"] == len(b"conteudo")
    assert prov.ler_registro(caminho) == registro
    assert registro.hash_sha256 == hashlib.sha256(b"conteudo").hexdigest()
    assert registro.data_entrega == "2026-09-30"
    assert registro.motivo_sem_entrega is None
    assert registro.versao is None


def test_registrar_reaproveita_o_registro_do_mesmo_arquivo(tmp_path, monkeypatch):
    caminho = _arquivo(tmp_path / "a.zip")
    primeiro = prov.registrar_arquivo(caminho, "https://x/a.zip", "DFP", "2025")

    def proibido(_):
        raise AssertionError("arquivo igual não é lido de novo")

    monkeypatch.setattr(prov, "hash_sha256", proibido)
    assert prov.registrar_arquivo(caminho, "https://x/a.zip", "DFP", "2025") == primeiro


@pytest.mark.parametrize(
    "outra",
    [
        ("https://y/a.zip", "DFP", "2025", None),
        ("https://x/a.zip", "ITR", "2025", None),
        ("https://x/a.zip", "DFP", "2024", None),
        ("https://x/a.zip", "DFP", "2025", "2026-01-01"),
    ],
)
def test_registrar_refaz_quando_a_descricao_muda(tmp_path, outra):
    caminho = _arquivo(tmp_path / "a.zip")
    prov.registrar_arquivo(caminho, "https://x/a.zip", "DFP", "2025")
    fonte, documento, periodo, entrega = outra
    novo = prov.registrar_arquivo(caminho, fonte, documento, periodo, entrega)
    assert (
        novo.fonte,
        novo.documento,
        novo.periodo_referencia,
        novo.data_entrega,
    ) == outra
    assert prov.ler_registro(caminho) == novo


def test_download_novo_gera_registro_novo(tmp_path):
    caminho = _arquivo(tmp_path / "a.zip", b"velho")
    velho = prov.registrar_arquivo(caminho, "https://x/a.zip", "DFP", "2025")
    _arquivo(caminho, b"novo!", datetime(2026, 10, 9, tzinfo=UTC))
    assert prov.ler_registro(caminho) is None
    novo = prov.registrar_arquivo(caminho, "https://x/a.zip", "DFP", "2025")
    assert novo.hash_sha256 != velho.hash_sha256
    assert novo.data_coleta == "2026-10-09T00:00:00+00:00"


def test_mesmo_tamanho_com_outro_mtime_invalida(tmp_path):
    caminho = _arquivo(tmp_path / "a.zip", b"abc")
    prov.registrar_arquivo(caminho, "https://x/a.zip", "DFP", "2025")
    _arquivo(caminho, b"xyz", datetime(2026, 10, 9, tzinfo=UTC))
    assert prov.ler_registro(caminho) is None


def test_mesmo_mtime_com_outro_tamanho_invalida(tmp_path):
    caminho = _arquivo(tmp_path / "a.zip", b"abc")
    prov.registrar_arquivo(caminho, "https://x/a.zip", "DFP", "2025")
    _arquivo(caminho, b"abcd")
    assert prov.ler_registro(caminho) is None


@pytest.mark.parametrize("lateral", ["{", "[]", '{"mtime_ns": 1}', None])
def test_lateral_ausente_ou_ilegivel_nao_vale(tmp_path, lateral):
    caminho = _arquivo(tmp_path / "a.zip")
    if lateral is not None:
        prov.caminho_lateral(caminho).write_text(lateral, encoding="utf-8")
    assert prov.ler_registro(caminho) is None


def test_arquivo_ausente_nao_tem_registro(tmp_path):
    assert prov.ler_registro(tmp_path / "nao_existe.zip") is None
    with pytest.raises(OSError):
        prov.registrar_arquivo(tmp_path / "nao_existe.zip", "https://x", "DFP", "2025")


def test_registrar_nao_deixa_temporario(tmp_path):
    caminho = _arquivo(tmp_path / "a.zip")
    prov.registrar_arquivo(caminho, "https://x/a.zip", "DFP", "2025")
    assert not any(p.name.endswith(".tmp") for p in tmp_path.iterdir())


# ── data de entrega nos índices ──────────────────────────────────────────────

INDICE = [
    {
        "CNPJ_CIA": "1",
        "DT_REFER": "2025-12-31",
        "VERSAO": "1",
        "DT_RECEB": "2026-03-01",
    },
    {
        "CNPJ_CIA": "1",
        "DT_REFER": "2025-12-31",
        "VERSAO": "2",
        "DT_RECEB": " 2026-04-02 ",
    },
    {
        "CNPJ_CIA": "2",
        "DT_REFER": "2025-12-31",
        "VERSAO": "1",
        "DT_RECEB": "31/03/2026",
    },
    {"CNPJ_CIA": "3", "DT_REFER": "2025-12-31", "VERSAO": "1", "DT_RECEB": None},
]


@pytest.mark.parametrize(
    ("cnpj", "versao", "esperado"),
    [
        ("1", "1", "2026-03-01"),
        ("1", "2", "2026-04-02"),
        ("1", "3", None),
        ("2", "1", None),
        ("3", "1", None),
        ("9", "1", None),
    ],
)
def test_entrega_no_indice_da_cvm(cnpj, versao, esperado):
    documento = {"CNPJ_CIA": cnpj, "DT_REFER": "2025-12-31", "VERSAO": versao}
    assert prov.entrega_no_indice(INDICE, documento) == esperado


def test_entrega_no_indice_confere_todas_as_colunas():
    documento = {"CNPJ_CIA": "1", "DT_REFER": "2024-12-31", "VERSAO": "1"}
    assert prov.entrega_no_indice(INDICE, documento) is None


def test_entrega_no_informe_usa_a_coluna_pedida():
    linhas = [{"CNPJ_Fundo_Classe": "1", "Data_Entrega": "2026-02-13", "DT_RECEB": "x"}]
    assert (
        prov.entrega_no_indice(
            linhas, {"CNPJ_Fundo_Classe": "1"}, coluna="Data_Entrega"
        )
        == "2026-02-13"
    )


# ── COTAHIST: data de geração do header ──────────────────────────────────────


def _zip_cotahist(caminho, primeira_linha):
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("COTAHIST_M092026.TXT", primeira_linha + "\r\n")
    return caminho


def test_cotahist_entrega_e_a_data_de_geracao(tmp_path):
    caminho = _zip_cotahist(
        tmp_path / "c.zip", "00COTAHIST.2026BOVESPA 20260930" + " " * 214
    )
    assert b3_cotahist.data_de_geracao(caminho) == "2026-09-30"


@pytest.mark.parametrize(
    "linha",
    ["01COTAHIST.2026BOVESPA 20260930", "00COTAHIST.2026BOVESPA 2026XX30", "00"],
)
def test_cotahist_sem_header_valido_nao_tem_entrega(tmp_path, linha):
    assert b3_cotahist.data_de_geracao(_zip_cotahist(tmp_path / "c.zip", linha)) is None


def test_cotahist_ilegivel_nao_tem_entrega(tmp_path):
    assert (
        b3_cotahist.data_de_geracao(_arquivo(tmp_path / "c.zip", b"nao e zip")) is None
    )
    assert b3_cotahist.data_de_geracao(tmp_path / "nao_existe.zip") is None


# ── provedores ───────────────────────────────────────────────────────────────


def _zip(caminho, membros):
    with zipfile.ZipFile(caminho, "w") as zf:
        for nome, linhas in membros.items():
            zf.writestr(
                nome, "\n".join(";".join(linha) for linha in linhas).encode("latin-1")
            )
    return caminho


INDICE_DFP = [
    ["CNPJ_CIA", "DT_REFER", "VERSAO", "DT_RECEB"],
    ["11.111.111/0001-11", "2025-12-31", "1", "2026-03-01"],
    ["11.111.111/0001-11", "2025-12-31", "2", "2026-04-20"],
]


def test_provedor_cvm_registra_o_documento_usado(tmp_path):
    caminho = _zip(tmp_path / "dfp_2025.zip", {"dfp_cia_aberta_2025.csv": INDICE_DFP})
    registro = CVMProvider(str(tmp_path / "c")).proveniencia_do_documento(
        caminho, 2025, "11.111.111/0001-11", "2025-12-31", "2"
    )
    assert registro["documento"] == "DFP"
    assert registro["periodo_referencia"] == "2025-12-31"
    assert registro["versao"] == "2"
    assert registro["data_entrega"] == "2026-04-20"
    assert registro["motivo_sem_entrega"] is None
    assert registro["fonte"].endswith("/DFP/DADOS/dfp_cia_aberta_2025.zip")
    assert registro["hash_sha256"] == prov.hash_sha256(caminho)
    assert prov.caminho_lateral(caminho).exists()


def test_provedor_cvm_sem_indice_de_entregas_registra_o_motivo(tmp_path):
    caminho = _zip(tmp_path / "dfp_2025.zip", {"outro.csv": [["A"], ["1"]]})
    registro = CVMProvider(str(tmp_path / "c")).proveniencia_do_documento(
        caminho, 2025, "11.111.111/0001-11", "2025-12-31", "1"
    )
    assert registro["data_entrega"] is None
    assert registro["motivo_sem_entrega"] == prov.MOTIVO_DOCUMENTO_FORA_DO_INDICE


def test_provedor_cvm_sem_arquivo_nao_tem_proveniencia(tmp_path):
    provider = CVMProvider(str(tmp_path / "c"))
    assert (
        provider.proveniencia_do_documento(
            tmp_path / "x.zip", 2025, "1", "2025-12-31", "1"
        )
        is None
    )


def test_provedor_cvm_le_o_indice_uma_vez_por_arquivo(tmp_path, monkeypatch):
    import cvm_provider

    monkeypatch.setattr(cvm_provider, "_cache_entregas", {})
    caminho = _zip(tmp_path / "itr_2026.zip", {"itr_cia_aberta_2026.csv": INDICE_DFP})
    provider = CVMProvider(str(tmp_path / "c"))
    primeiro = provider._entregas(caminho)
    assert provider._entregas(caminho) is primeiro
    assert [linha["DT_RECEB"] for linha in primeiro] == ["2026-03-01", "2026-04-20"]


def test_cache_de_entregas_tem_teto(tmp_path, monkeypatch):
    import cvm_provider

    monkeypatch.setattr(cvm_provider, "_cache_entregas", {})
    provider = CVMProvider(str(tmp_path / "c"))
    for i in range(cvm_provider._CACHE_ENTREGAS_MAX + 3):
        provider._entregas(
            _zip(tmp_path / f"dfp{i}.zip", {"dfp_cia_aberta_2025.csv": INDICE_DFP})
        )
    assert len(cvm_provider._cache_entregas) == cvm_provider._CACHE_ENTREGAS_MAX


def test_provedor_fii_registra_mes_versao_e_entrega(tmp_path, monkeypatch):
    cnpj = "11.728.688/0001-47"
    caminho = _zip(
        tmp_path / "inf.zip",
        {
            "inf_mensal_fii_complemento_2026.csv": [
                [
                    "CNPJ_Fundo_Classe",
                    "Data_Referencia",
                    "Versao",
                    "Patrimonio_Liquido",
                ],
                [cnpj, "2026-08-01", "2", "100"],
            ],
            "inf_mensal_fii_geral_2026.csv": [
                ["CNPJ_Fundo_Classe", "Data_Referencia", "Versao", "Data_Entrega"],
                [cnpj, "2026-08-01", "1", "2026-09-10"],
                [cnpj, "2026-08-01", "2", "2026-09-23"],
            ],
        },
    )
    provider = CVMFIIProvider(str(tmp_path / "c"))
    monkeypatch.setattr(provider, "baixar_informe", lambda ano: caminho)
    registro = provider.obter_dados_fii(cnpj)["proveniencia"]
    assert registro["documento"] == "Informe Mensal"
    assert registro["periodo_referencia"] == "2026-08-01"
    assert registro["versao"] == "2"
    assert registro["data_entrega"] == "2026-09-23"
    assert registro["fonte"].endswith("inf_mensal_fii_2026.zip")


def test_provedor_fii_sem_geral_registra_o_motivo(tmp_path, monkeypatch):
    cnpj = "11.728.688/0001-47"
    caminho = _zip(
        tmp_path / "inf.zip",
        {
            "inf_mensal_fii_complemento_2026.csv": [
                [
                    "CNPJ_Fundo_Classe",
                    "Data_Referencia",
                    "Versao",
                    "Patrimonio_Liquido",
                ],
                [cnpj, "2026-08-01", "1", "100"],
            ]
        },
    )
    provider = CVMFIIProvider(str(tmp_path / "c"))
    monkeypatch.setattr(provider, "baixar_informe", lambda ano: caminho)
    registro = provider.obter_dados_fii(cnpj)["proveniencia"]
    assert registro["data_entrega"] is None
    assert registro["motivo_sem_entrega"] == prov.MOTIVO_DOCUMENTO_FORA_DO_INDICE


def test_provedor_fii_sem_arquivo_legivel_nao_tem_proveniencia(tmp_path):
    provider = CVMFIIProvider(str(tmp_path / "c"))
    assert provider._proveniencia(tmp_path / "x.zip", 2026, {}) is None


# ── cascata ──────────────────────────────────────────────────────────────────

REGISTRO_CVM = _registro().para_dict()


class _CVM:
    def __init__(self, registro):
        self.registro = registro

    def calcular_indicadores(self, cd_cvm, anos=1):
        return {
            2025: {"roe": 0.12, "margem_liquida": 0.2, "proveniencia": self.registro}
        }


INFO = {"currentPrice": 20.0, "quoteType": "EQUITY", "trailingPE": 10.0}


def test_cascata_expoe_a_proveniencia_por_campo_da_cvm(monkeypatch):
    engine = _engine(
        monkeypatch, info=INFO, historico=_historico(20.0), cvm=_CVM(REGISTRO_CVM)
    )
    dados = engine.buscar_dados_ticker("PETR4")
    assert dados["proveniencia"] == {
        "roe": REGISTRO_CVM,
        "margem_liquida": REGISTRO_CVM,
    }


def test_cascata_sem_registro_nao_cria_o_bloco(monkeypatch):
    engine = _engine(monkeypatch, info=INFO, historico=_historico(20.0), cvm=_CVM(None))
    assert "proveniencia" not in engine.buscar_dados_ticker("PETR4")


def test_bloco_fica_fora_do_prompt():
    texto = SentinelaAI.__new__(SentinelaAI)._formatar_dados(
        {"ticker": "TST3", "roe": 0.12, "proveniencia": {"roe": REGISTRO_CVM}}
    )
    assert "roe: 0.12" in texto
    assert "proveniencia" not in texto
    assert HASH not in texto


# ── índice do F2A-1 ──────────────────────────────────────────────────────────


def test_indice_registra_cada_arquivo_baixado(tmp_path, rede_simulada):
    f = fontes.carregar_fontes(AGORA, tmp_path)
    por_arquivo = {r["arquivo"]: r for r in f.proveniencia}
    assert sorted(por_arquivo) == [
        "COTAHIST_M072026.ZIP",
        "COTAHIST_M082026.ZIP",
        "COTAHIST_M092026.ZIP",
        "cad_cia_aberta.csv",
        "fca_cia_aberta_2026.zip",
        "inf_mensal_fii_2026.zip",
    ]
    cadastro = por_arquivo["cad_cia_aberta.csv"]
    assert cadastro["documento"] == "Cadastro"
    assert cadastro["periodo_referencia"] is None
    assert cadastro["motivo_sem_entrega"] == prov.MOTIVO_SEM_ENTREGA_NA_FONTE
    assert cadastro["fonte"] == fontes.URL_CADASTRO
    fca = por_arquivo["fca_cia_aberta_2026.zip"]
    assert (fca["documento"], fca["periodo_referencia"]) == ("FCA", "2026")
    assert fca["motivo_sem_entrega"] == prov.MOTIVO_ARQUIVO_AGREGADO
    assert fca["fonte"] == fontes.URL_FCA.format(ano=2026)
    informe = por_arquivo["inf_mensal_fii_2026.zip"]
    assert (informe["documento"], informe["periodo_referencia"]) == (
        "Informe Mensal",
        "2026",
    )
    assert informe["fonte"] == fontes.URL_INFORME.format(ano=2026)
    cotahist = por_arquivo["COTAHIST_M082026.ZIP"]
    assert (cotahist["documento"], cotahist["periodo_referencia"]) == (
        "COTAHIST",
        "2026-08",
    )
    # O COTAHIST simulado não é um ZIP legível: sem header, sem data de entrega.
    assert cotahist["motivo_sem_entrega"] == prov.MOTIVO_ENTREGA_ILEGIVEL
    assert cotahist["fonte"] == b3_cotahist.URL_MENSAL.format(ano=2026, mes=8)
    caminho = tmp_path / "fontes" / "fca_cia_aberta_2026.zip"
    assert prov.ler_registro(caminho).para_dict() == {
        k: v for k, v in fca.items() if k != "arquivo"
    }


def test_indice_salvo_leva_a_proveniencia_das_fontes(tmp_path, rede_simulada):
    f = fontes.carregar_fontes(AGORA, tmp_path)
    assert f.meta_com_proveniencia() == {**f.meta, "proveniencia": f.proveniencia}
    indice = fontes.construir_indice(AGORA, tmp_path)
    assert len(indice.fontes["proveniencia"]) == 6
    assert indice.fontes["fca"] == f.meta["fca"]


@pytest.mark.parametrize(
    ("metodo", "documento", "trecho"),
    [("baixar_dfp", "DFP", "/DFP/DADOS/dfp_cia_aberta_2025.zip"),
     ("baixar_itr", "ITR", "/ITR/DADOS/itr_cia_aberta_2025.zip")],
)  # fmt: skip
def test_download_da_cvm_grava_a_proveniencia(
    tmp_path, monkeypatch, metodo, documento, trecho
):
    import cvm_provider

    def baixar(url, destino):
        _arquivo(destino, url.encode())
        return destino

    monkeypatch.setattr(cvm_provider, "baixar_arquivo", baixar)
    caminho = getattr(CVMProvider(str(tmp_path)), metodo)(2025)
    registro = prov.ler_registro(caminho)
    assert (registro.documento, registro.periodo_referencia) == (documento, "2025")
    assert registro.fonte.endswith(trecho)
    assert registro.hash_sha256 == hashlib.sha256(registro.fonte.encode()).hexdigest()


def test_download_do_informe_grava_a_proveniencia(tmp_path, monkeypatch):
    import cvm_fii_provider

    def baixar(url, destino):
        _arquivo(destino, b"zip")
        return destino

    monkeypatch.setattr(cvm_fii_provider, "baixar_arquivo", baixar)
    caminho = CVMFIIProvider(str(tmp_path)).baixar_informe(2026)
    registro = prov.ler_registro(caminho)
    assert (registro.documento, registro.periodo_referencia) == (
        "Informe Mensal",
        "2026",
    )
    assert registro.fonte.endswith("/INF_MENSAL/DADOS/inf_mensal_fii_2026.zip")


def test_registrar_refaz_quando_o_motivo_muda(tmp_path):
    caminho = _arquivo(tmp_path / "a.zip")
    prov.registrar_arquivo(caminho, "https://x/a.zip", "COTAHIST", "2026-09")
    novo = prov.registrar_arquivo(
        caminho, "https://x/a.zip", "COTAHIST", "2026-09", motivo="outro motivo"
    )
    assert novo.motivo_sem_entrega == "outro motivo"
    assert prov.ler_registro(caminho) == novo


def test_registrar_sem_falhar_devolve_o_registro(tmp_path):
    caminho = _arquivo(tmp_path / "a.zip")
    registro = prov.registrar_sem_falhar(
        caminho, "https://x/a.zip", "FCA", "2026", motivo="m"
    )
    assert registro == prov.ler_registro(caminho)
    assert registro.motivo_sem_entrega == "m"


def test_falha_de_disco_no_registro_nao_derruba_o_download(tmp_path, caplog):
    with caplog.at_level("WARNING"):
        registro = prov.registrar_sem_falhar(
            tmp_path / "nao_existe.zip", "https://x", "DFP", "2025"
        )
    assert registro is None
    assert "não gravada" in caplog.text


def test_documento_sem_identificacao_completa_nao_casa():
    linhas = [{"CNPJ_CIA": "1", "DT_REFER": "2025-12-31", "DT_RECEB": "2026-03-01"}]
    documento = {"CNPJ_CIA": "1", "DT_REFER": "2025-12-31", "VERSAO": None}
    assert prov.entrega_no_indice(linhas, documento) is None


def test_multiplos_com_preco_ficam_fora_do_registro_da_dfp(monkeypatch):
    engine = _engine(
        monkeypatch, info=INFO, historico=_historico(20.0), cvm=_CVM(REGISTRO_CVM)
    )
    engine._por_acao_cvm = lambda ticker, dados, ind: {
        "lpa": 2.0,
        "vpa": 13.0,
        "pl": 10.0,
        "pvp": 1.5,
    }
    dados = engine.buscar_dados_ticker("PETR4")
    assert sorted(dados["proveniencia"]) == ["lpa", "margem_liquida", "roe", "vpa"]
    assert dados["pl"] == 10.0


@pytest.mark.parametrize("etapa", ["escrita", "troca"])
def test_falha_de_registro_limpa_seu_temporario(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, etapa: str
) -> None:
    """F2C-18: falha antes da troca preserva o registro completo anterior e limpa resíduo."""
    origem = _arquivo(tmp_path / "a.zip")
    prov.registrar_arquivo(origem, "fonte anterior", "DFP", "2025")
    lateral = prov.caminho_lateral(origem)
    anterior = lateral.read_bytes()

    def falhar(*args: object, **kwargs: object) -> None:
        raise OSError("falha sintética")

    if etapa == "escrita":
        monkeypatch.setattr(prov.json, "dumps", falhar)
    else:
        monkeypatch.setattr(Path, "replace", falhar)
    with pytest.raises(OSError, match="falha sintética"):
        prov.registrar_arquivo(origem, "fonte nova", "DFP", "2025")
    assert lateral.read_bytes() == anterior
    assert not any(caminho.suffix == ".tmp" for caminho in tmp_path.iterdir())
