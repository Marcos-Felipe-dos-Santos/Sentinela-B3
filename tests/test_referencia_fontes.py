"""Download e construção do índice (F2A-1): rede e arquivos simulados, nada de rede real."""

import io
import json
import os
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pytest
import requests

from sentinela.data.providers.b3_cotahist import Cotacao
from sentinela.data.referencia import __main__ as principal
from sentinela.data.referencia import carregar_indice, fontes, salvar_indice
from sentinela.data.referencia.montagem import montar_indice

AGORA = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
TTL = 7 * 24 * 3600


class _Resposta:
    def __init__(self, conteudo=b"a;b\n1;2\n", erro=None):
        self.content = conteudo
        self._erro = erro

    def raise_for_status(self):
        if self._erro:
            raise self._erro


def _zip_com(nome, linhas, sep=";"):
    buffer = io.BytesIO()
    texto = "\n".join(sep.join(linha) for linha in linhas)
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(nome, texto.encode("latin-1"))
    return buffer.getvalue()


DIAS = {
    "cadastro": datetime(2026, 10, 2, 12, tzinfo=UTC),
    "fca": datetime(2026, 10, 3, 12, tzinfo=UTC),
    "informe": datetime(2026, 10, 4, 12, tzinfo=UTC),
    "cotahist9": datetime(2026, 10, 1, 12, tzinfo=UTC),
    "cotahist8": datetime(2026, 9, 1, 12, tzinfo=UTC),
    "cotahist7": datetime(2026, 8, 1, 12, tzinfo=UTC),
}


def _baixado_em(caminho, instante):
    os.utime(caminho, (instante.timestamp(), instante.timestamp()))


def _http(status):
    resposta = requests.Response()
    resposta.status_code = status
    return requests.HTTPError(str(status), response=resposta)


def _envelhecer(caminho, segundos):
    t = AGORA.timestamp() - segundos
    os.utime(caminho, (t, t))


# ── baixar_csv ───────────────────────────────────────────────────────────────


def test_baixar_csv_grava_e_nao_deixa_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(
        fontes.requests, "get", lambda url, timeout: _Resposta(b"x;y\n")
    )
    destino = fontes.baixar_csv("http://x/a.csv", tmp_path / "pasta" / "a.csv", AGORA)
    assert destino.read_bytes() == b"x;y\n"
    assert [p.name for p in destino.parent.iterdir()] == ["a.csv"]


def test_baixar_csv_dentro_do_ttl_nao_baixa(tmp_path, monkeypatch):
    destino = tmp_path / "a.csv"
    destino.write_bytes(b"velho")
    _envelhecer(destino, TTL - 60)

    def proibido(url, timeout):
        raise AssertionError("não devia baixar")

    monkeypatch.setattr(fontes.requests, "get", proibido)
    assert fontes.baixar_csv("http://x", destino, AGORA).read_bytes() == b"velho"


def test_baixar_csv_vencido_baixa_de_novo(tmp_path, monkeypatch):
    destino = tmp_path / "a.csv"
    destino.write_bytes(b"velho")
    _envelhecer(destino, TTL + 60)
    monkeypatch.setattr(fontes.requests, "get", lambda url, timeout: _Resposta(b"novo"))
    assert fontes.baixar_csv("http://x", destino, AGORA).read_bytes() == b"novo"


def test_baixar_csv_com_rede_fora_usa_a_copia_antiga(tmp_path, monkeypatch, caplog):
    destino = tmp_path / "a.csv"
    destino.write_bytes(b"velho")
    _envelhecer(destino, TTL + 60)

    def quebrado(url, timeout):
        raise requests.ConnectionError("sem rede")

    monkeypatch.setattr(fontes.requests, "get", quebrado)
    with caplog.at_level("WARNING"):
        assert fontes.baixar_csv("http://x", destino, AGORA).read_bytes() == b"velho"
    assert "cópia antiga" in caplog.text
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.csv"]


def test_baixar_csv_com_rede_fora_e_sem_copia_levanta(tmp_path, monkeypatch):
    def quebrado(url, timeout):
        raise requests.ConnectionError("sem rede")

    monkeypatch.setattr(fontes.requests, "get", quebrado)
    with pytest.raises(requests.ConnectionError):
        fontes.baixar_csv("http://x", tmp_path / "a.csv", AGORA)
    assert list(tmp_path.iterdir()) == []


def test_baixar_csv_http_404_conta_como_falha(tmp_path, monkeypatch):
    erro = requests.HTTPError("404")
    monkeypatch.setattr(
        fontes.requests, "get", lambda url, timeout: _Resposta(erro=erro)
    )
    with pytest.raises(requests.HTTPError):
        fontes.baixar_csv("http://x", tmp_path / "a.csv", AGORA)


# ── meses e zips ─────────────────────────────────────────────────────────────


def test_meses_recentes_atravessa_o_ano():
    assert fontes._meses_recentes(datetime(2026, 2, 10, tzinfo=UTC), 3) == [
        (2026, 1),
        (2025, 12),
        (2025, 11),
    ]
    assert fontes._meses_recentes(AGORA, 0) == []


def test_meses_recentes_sao_os_fechados_e_comecam_no_anterior():
    assert fontes._meses_recentes(AGORA, 3) == [(2026, 9), (2026, 8), (2026, 7)]
    assert fontes._meses_recentes(datetime(2026, 10, 31, 23, 59, tzinfo=UTC), 1) == [
        (2026, 9)
    ]


# ── baixar_zip e _zip_do_ano ─────────────────────────────────────────────────


def test_baixar_zip_valida_o_conteudo(tmp_path, monkeypatch):
    monkeypatch.setattr(
        fontes.requests, "get", lambda url, timeout: _Resposta(b"nao e zip")
    )
    with pytest.raises(zipfile.BadZipFile):
        fontes.baixar_zip("http://x", tmp_path / "a.zip", AGORA)
    assert list(tmp_path.iterdir()) == []


def test_baixar_zip_grava_e_respeita_o_ttl_do_agora(tmp_path, monkeypatch):
    conteudo = _zip_com("a.csv", [["A"], ["1"]])
    monkeypatch.setattr(
        fontes.requests, "get", lambda url, timeout: _Resposta(conteudo)
    )
    destino = fontes.baixar_zip("http://x", tmp_path / "a.zip", AGORA)
    assert destino.read_bytes() == conteudo

    def proibido(url, timeout):
        raise AssertionError("dentro do TTL do `agora`, não baixa")

    monkeypatch.setattr(fontes.requests, "get", proibido)
    assert fontes.baixar_zip("http://x", destino, AGORA) == destino


def test_baixar_zip_com_zip_ruim_usa_a_copia_antiga(tmp_path, monkeypatch, caplog):
    destino = tmp_path / "a.zip"
    destino.write_bytes(_zip_com("a.csv", [["A"], ["1"]]))
    _envelhecer(destino, TTL + 60)
    monkeypatch.setattr(fontes.requests, "get", lambda url, timeout: _Resposta(b"lixo"))
    with caplog.at_level("WARNING"):
        assert fontes.baixar_zip("http://x", destino, AGORA) == destino
    assert "cópia antiga" in caplog.text
    assert zipfile.is_zipfile(destino)


def test_zip_do_ano_le_o_csv(tmp_path, monkeypatch):
    def baixar(url, destino, agora):
        destino.write_bytes(_zip_com("dados_2026.csv", [["A", "B"], ["1", "2"]]))
        return destino

    monkeypatch.setattr(fontes, "baixar_zip", baixar)
    caminho, df = fontes._zip_do_ano(
        "http://x/f_{ano}.zip", "dados_{ano}.csv", 2026, tmp_path, AGORA
    )
    assert caminho.name == "f_2026.zip"
    assert list(df.columns) == ["A", "B"]


def test_zip_do_ano_404_quer_dizer_nao_entregue(tmp_path, monkeypatch):
    def baixar(url, destino, agora):
        raise _http(404)

    monkeypatch.setattr(fontes, "baixar_zip", baixar)
    assert (
        fontes._zip_do_ano("http://x/f_{ano}.zip", "d_{ano}.csv", 2026, tmp_path, AGORA)
        is None
    )


@pytest.mark.parametrize(
    "erro",
    [
        _http(500),
        _http(503),
        requests.ConnectionError("sem rede"),
        requests.Timeout("lento"),
    ],
)
def test_zip_do_ano_com_outra_falha_de_rede_sobe(tmp_path, monkeypatch, erro):
    def baixar(url, destino, agora):
        raise erro

    monkeypatch.setattr(fontes, "baixar_zip", baixar)
    with pytest.raises(requests.RequestException):
        fontes._zip_do_ano("http://x/f_{ano}.zip", "d_{ano}.csv", 2026, tmp_path, AGORA)


def test_zip_do_ano_sem_o_csv_esperado_sobe(tmp_path, monkeypatch):
    def baixar(url, destino, agora):
        destino.write_bytes(_zip_com("outro_nome.csv", [["A"], ["1"]]))
        return destino

    monkeypatch.setattr(fontes, "baixar_zip", baixar)
    with pytest.raises(KeyError):
        fontes._zip_do_ano(
            "http://x/f_{ano}.zip", "dados_{ano}.csv", 2026, tmp_path, AGORA
        )


def test_zip_do_ano_com_zip_estragado_no_cache_sobe(tmp_path, monkeypatch):
    def baixar(url, destino, agora):
        destino.write_bytes(b"nao e zip")
        return destino

    monkeypatch.setattr(fontes, "baixar_zip", baixar)
    with pytest.raises(zipfile.BadZipFile):
        fontes._zip_do_ano(
            "http://x/f_{ano}.zip", "dados_{ano}.csv", 2026, tmp_path, AGORA
        )


# ── falha parcial: não grava índice incompleto ───────────────────────────────


def test_falha_de_rede_num_dos_fca_nao_gera_indice_parcial(
    tmp_path, rede_simulada, monkeypatch
):
    original = fontes.baixar_zip

    def so_o_de_2026_cai(url, destino, agora):
        if "fca" in url and "2026" in url:
            raise requests.ConnectionError("timeout")
        return original(url, destino, agora)

    monkeypatch.setattr(fontes, "baixar_zip", so_o_de_2026_cai)
    with pytest.raises(requests.ConnectionError):
        fontes.carregar_fontes(AGORA, tmp_path)


@pytest.mark.parametrize(
    "conteudo",
    [b"nao e zip", _zip_com("outro_nome.csv", [["A"], ["1"]])],
    ids=["zip_estragado", "sem_o_csv"],
)
def test_zip_ilegivel_num_dos_fca_nao_gera_indice_parcial(
    tmp_path, rede_simulada, monkeypatch, conteudo
):
    caminho = _salvo(tmp_path)
    _envelhecer(caminho, TTL + 60)
    original = fontes.baixar_zip

    def o_de_2026_ilegivel(url, destino, agora):
        if "fca" in url and "2026" in url:
            destino.write_bytes(conteudo)
            return destino
        return original(url, destino, agora)

    monkeypatch.setattr(fontes, "baixar_zip", o_de_2026_ilegivel)
    with pytest.raises((zipfile.BadZipFile, KeyError)):
        fontes.carregar_fontes(AGORA, tmp_path)
    assert fontes.obter_indice(AGORA, tmp_path).gerado_em == "2026-10-01"
    assert carregar_indice(tmp_path / "referencia").gerado_em == "2026-10-01"


def test_falha_parcial_mantem_o_indice_salvo(tmp_path, rede_simulada, monkeypatch):
    caminho = _salvo(tmp_path)
    _envelhecer(caminho, TTL + 60)

    def cai(url, destino, agora):
        raise requests.ConnectionError("timeout")

    monkeypatch.setattr(fontes, "baixar_zip", cai)
    assert fontes.obter_indice(AGORA, tmp_path).gerado_em == "2026-10-01"
    assert carregar_indice(tmp_path / "referencia").gerado_em == "2026-10-01"


def test_falha_de_rede_no_cotahist_que_nao_e_404_sobe(
    tmp_path, rede_simulada, monkeypatch
):
    def cai(ano, mes, agora, pasta):
        raise requests.ConnectionError("timeout")

    monkeypatch.setattr(fontes.b3_cotahist, "baixar_mes", cai)
    with pytest.raises(requests.ConnectionError):
        fontes.carregar_fontes(AGORA, tmp_path)


def test_sem_nenhum_fca_levanta(tmp_path, rede_simulada, monkeypatch):
    def sem_fca(url, destino, agora):
        raise _http(404)

    monkeypatch.setattr(fontes, "baixar_zip", sem_fca)
    with pytest.raises(FileNotFoundError, match="FCA"):
        fontes.carregar_fontes(AGORA, tmp_path)


def test_sem_nenhum_informe_levanta(tmp_path, rede_simulada, monkeypatch):
    original = fontes.baixar_zip

    def sem_informe(url, destino, agora):
        if "inf_mensal" in url:
            raise _http(404)
        return original(url, destino, agora)

    monkeypatch.setattr(fontes, "baixar_zip", sem_informe)
    with pytest.raises(FileNotFoundError, match="Informe"):
        fontes.carregar_fontes(AGORA, tmp_path)


def test_informe_junta_os_dois_anos_e_vale_o_mais_recente_do_fundo(
    tmp_path, rede_simulada, monkeypatch
):
    antigo = [
        INFORME_CSV[0],
        ["44.444.444/0001-44", "2025-12-01", "1", "FUNDO ANTIGO", "BRANTGCTF001", "S"],
    ]

    def dois_anos(url, destino, agora):
        if "inf_mensal" in url and "2025" in url:
            destino.write_bytes(_zip_com("inf_mensal_fii_geral_2025.csv", antigo))
            return destino
        if "2025" in url:
            raise _http(404)
        destino.write_bytes(
            _zip_com(
                "inf_mensal_fii_geral_2026.csv"
                if "inf_mensal" in url
                else "fca_cia_aberta_valor_mobiliario_2026.csv",
                INFORME_CSV if "inf_mensal" in url else FCA_CSV,
            )
        )
        return destino

    monkeypatch.setattr(fontes, "baixar_zip", dois_anos)
    f = fontes.carregar_fontes(AGORA, tmp_path)
    assert sorted(f.informe["Codigo_ISIN"]) == ["BRANTGCTF001", "BRTSTFCTF001"]
    assert (
        f.meta["informe_fii"]["arquivo"]
        == "inf_mensal_fii_2025.zip, inf_mensal_fii_2026.zip"
    )


def test_indice_salvo_corrompido_e_reconstruido(tmp_path, rede_simulada):
    caminho = _salvo(tmp_path)
    caminho.write_text("{ nao e json", encoding="utf-8")
    assert fontes.obter_indice(AGORA, tmp_path).gerado_em == "2026-10-08"


def test_indice_salvo_corrompido_sem_rede_levanta(tmp_path, monkeypatch):
    caminho = _salvo(tmp_path)
    caminho.write_text("{ nao e json", encoding="utf-8")

    def cai(agora, pasta):
        raise requests.ConnectionError("sem rede")

    monkeypatch.setattr(fontes, "construir_indice", cai)
    with pytest.raises(requests.ConnectionError):
        fontes.obter_indice(AGORA, tmp_path)


# ── carregar_fontes / construir_indice ───────────────────────────────────────

FCA_CSV = [
    ["CNPJ_Companhia", "Data_Referencia", "Versao", "Nome_Empresarial", "Valor_Mobiliario", "Codigo_Negociacao", "Composicao_BDR_Unit", "Mercado", "Data_Fim_Negociacao"],
    ["11.111.111/0001-11", "2026-01-01", "1", "EMPRESA A", "Ações Ordinárias", "TSTA3", "", "Bolsa", ""],
]  # fmt: skip
CAD_CSV = [
    ["CNPJ_CIA", "CD_CVM", "SIT", "DENOM_SOCIAL"],
    ["11.111.111/0001-11", "100", "ATIVO", "EMPRESA A S.A."],
]
INFORME_CSV = [
    ["CNPJ_Fundo_Classe", "Data_Referencia", "Versao", "Nome_Fundo_Classe", "Codigo_ISIN", "Mercado_Negociacao_Bolsa"],
    ["33.333.333/0001-33", "2026-01-01", "1", "FUNDO TESTE", "BRTSTFCTF001", "S"],
]  # fmt: skip


def _cotacao(codigo="TSTF11"):
    return Cotacao(
        data=date(2026, 9, 30), codigo_negociacao=codigo, codbdi="12", tipo_mercado="010",
        especificacao="CI", isin="BRTSTFCTF001", fechamento=1.0, volume_financeiro=1.0,
        quantidade=1, negocios=1, fator_cotacao=1,
    )  # fmt: skip


@pytest.fixture
def rede_simulada(monkeypatch):
    chamadas = {"csv": [], "zip": [], "cotahist": []}

    def baixar_csv(url, destino, agora):
        chamadas["csv"].append(url)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(
            "\n".join(";".join(linha) for linha in CAD_CSV).encode("latin-1")
        )
        _baixado_em(destino, DIAS["cadastro"])
        return destino

    def baixar_zip(url, destino, agora):
        chamadas["zip"].append(url)
        if "2025" in url:
            raise _http(404)
        if "fca" in url:
            conteudo = _zip_com("fca_cia_aberta_valor_mobiliario_2026.csv", FCA_CSV)
        else:
            conteudo = _zip_com("inf_mensal_fii_geral_2026.csv", INFORME_CSV)
        destino.write_bytes(conteudo)
        _baixado_em(destino, DIAS["fca" if "fca" in url else "informe"])
        return destino

    def baixar_mes(ano, mes, agora, pasta):
        chamadas["cotahist"].append((ano, mes))
        arquivo = Path(pasta) / f"COTAHIST_M{mes:02d}{ano}.ZIP"
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_bytes(b"x")
        _baixado_em(arquivo, DIAS[f"cotahist{mes}"])
        return arquivo

    monkeypatch.setattr(fontes, "baixar_csv", baixar_csv)
    monkeypatch.setattr(fontes, "baixar_zip", baixar_zip)
    monkeypatch.setattr(fontes.b3_cotahist, "baixar_mes", baixar_mes)
    monkeypatch.setattr(fontes.b3_cotahist, "ler_zip", lambda caminho: [_cotacao()])
    return chamadas


def test_carregar_fontes_junta_tudo(tmp_path, rede_simulada):
    f = fontes.carregar_fontes(AGORA, tmp_path)
    assert [ano for ano, _ in f.fcas] == [2026]
    assert list(f.cadastro["CD_CVM"]) == ["100"]
    assert list(f.informe["Codigo_ISIN"]) == ["BRTSTFCTF001"]
    assert len(f.cotacoes) == 3  # setembro, agosto e julho: os três meses fechados
    assert f.data == "2026-10-08"
    assert f.meta == {
        "fca": {"2026": {"arquivo": "fca_cia_aberta_2026.zip", "data": "2026-10-03"}},
        "cadastro": {"arquivo": "cad_cia_aberta.csv", "data": "2026-10-02"},
        "informe_fii": {"arquivo": "inf_mensal_fii_2026.zip", "data": "2026-10-04"},
        "cotahist": {
            "arquivo": "COTAHIST_M092026.ZIP, COTAHIST_M082026.ZIP, COTAHIST_M072026.ZIP",
            "data": "2026-10-01",
        },
    }
    assert rede_simulada["cotahist"] == [(2026, 9), (2026, 8), (2026, 7)]


def test_cotahist_de_um_mes_ainda_nao_publicado_fica_de_fora(
    tmp_path, rede_simulada, monkeypatch
):
    original = fontes.b3_cotahist.baixar_mes

    def julho_404(ano, mes, agora, pasta):
        if (ano, mes) == (2026, 7):
            raise _http(404)
        return original(ano, mes, agora, pasta)

    monkeypatch.setattr(fontes.b3_cotahist, "baixar_mes", julho_404)
    f = fontes.carregar_fontes(AGORA, tmp_path)
    assert len(f.cotacoes) == 2
    assert f.meta["cotahist"]["arquivo"] == "COTAHIST_M092026.ZIP, COTAHIST_M082026.ZIP"


def test_construir_indice_monta_a_partir_das_fontes(tmp_path, rede_simulada):
    indice = fontes.construir_indice(AGORA, tmp_path)
    assert indice.registros["TSTA3"].cd_cvm == 100
    assert indice.registros["TSTF11"].regra == "fii:informe+cotahist_isin"
    assert indice.gerado_em == "2026-10-08"


def test_sem_nenhum_cotahist_levanta(tmp_path, rede_simulada, monkeypatch):
    def sem_cotahist(ano, mes, agora, pasta):
        raise _http(404)

    monkeypatch.setattr(fontes.b3_cotahist, "baixar_mes", sem_cotahist)
    with pytest.raises(FileNotFoundError, match="COTAHIST"):
        fontes.carregar_fontes(AGORA, tmp_path)


# ── obter_indice ─────────────────────────────────────────────────────────────


def _salvo(tmp_path, gerado_em="2026-10-01"):
    indice = montar_indice(
        [(2026, pd.DataFrame(FCA_CSV[1:], columns=FCA_CSV[0]))],
        pd.DataFrame(CAD_CSV[1:], columns=CAD_CSV[0]),
        pd.DataFrame(INFORME_CSV[1:], columns=INFORME_CSV[0]).iloc[0:0],
        [],
        {
            "fca": {"2026": {"arquivo": "fca", "data": gerado_em}},
            **{
                k: {"arquivo": k, "data": gerado_em}
                for k in ("cadastro", "informe_fii", "cotahist")
            },
        },
        gerado_em,
    )
    salvar_indice(indice, tmp_path / "referencia")
    return tmp_path / "referencia" / "indice.json"


def test_obter_indice_dentro_do_ttl_nao_reconstroi(tmp_path, monkeypatch):
    caminho = _salvo(tmp_path)
    _envelhecer(caminho, TTL - 60)

    def proibido(agora, pasta):
        raise AssertionError("não devia reconstruir")

    monkeypatch.setattr(fontes, "construir_indice", proibido)
    assert fontes.obter_indice(AGORA, tmp_path).gerado_em == "2026-10-01"


def test_obter_indice_vencido_reconstroi_e_grava(tmp_path, rede_simulada):
    caminho = _salvo(tmp_path)
    _envelhecer(caminho, TTL + 60)
    indice = fontes.obter_indice(AGORA, tmp_path)
    assert indice.gerado_em == "2026-10-08"
    assert carregar_indice(tmp_path / "referencia").gerado_em == "2026-10-08"


def test_obter_indice_sem_arquivo_constroi(tmp_path, rede_simulada):
    assert fontes.obter_indice(AGORA, tmp_path).gerado_em == "2026-10-08"
    assert (tmp_path / "referencia" / "indice.json").exists()


def test_obter_indice_com_rede_fora_usa_o_salvo(tmp_path, monkeypatch, caplog):
    caminho = _salvo(tmp_path)
    _envelhecer(caminho, TTL + 60)

    def quebrado(agora, pasta):
        raise requests.ConnectionError("sem rede")

    monkeypatch.setattr(fontes, "construir_indice", quebrado)
    with caplog.at_level("WARNING"):
        assert fontes.obter_indice(AGORA, tmp_path).gerado_em == "2026-10-01"
    assert "usando o salvo" in caplog.text


def test_obter_indice_sem_rede_e_sem_salvo_levanta(tmp_path, monkeypatch):
    def quebrado(agora, pasta):
        raise requests.ConnectionError("sem rede")

    monkeypatch.setattr(fontes, "construir_indice", quebrado)
    with pytest.raises(requests.ConnectionError):
        fontes.obter_indice(AGORA, tmp_path)


# ── linha de comando ─────────────────────────────────────────────────────────


def test_linha_de_comando_grava_o_indice_e_mostra_a_cobertura(
    tmp_path, rede_simulada, capsys
):
    assert principal.main(["--pasta", str(tmp_path), "--cobertura"]) == 0
    saida = capsys.readouterr().out
    assert "índice: 2 registros, 0 exceções" in saida
    cobertura = json.loads(saida[saida.index("{") :])
    assert cobertura["companhias"] == {"codigos_ativos_no_fca": 1, "mapeados": 1}
    assert cobertura["fiis"]["mapeados_pela_juncao"] == 1
    assert (tmp_path / "referencia" / "indice.json").exists()


def test_linha_de_comando_sem_cobertura_nao_imprime_o_json(
    tmp_path, rede_simulada, capsys
):
    principal.main(["--pasta", str(tmp_path)])
    assert "{" not in capsys.readouterr().out


def test_obter_indice_com_arquivo_ilegivel_usa_o_salvo(tmp_path, monkeypatch):
    caminho = _salvo(tmp_path)
    _envelhecer(caminho, TTL + 60)

    def sem_coluna(agora, pasta):
        raise KeyError("coluna")

    monkeypatch.setattr(fontes, "construir_indice", sem_coluna)
    assert fontes.obter_indice(AGORA, tmp_path).gerado_em == "2026-10-01"


def test_obter_indice_com_erro_de_leitura_do_pandas_usa_o_salvo(
    tmp_path, monkeypatch, caplog
):
    caminho = _salvo(tmp_path)
    _envelhecer(caminho, TTL + 60)

    def csv_quebrado(agora, pasta):
        raise ValueError("Error tokenizing data")

    monkeypatch.setattr(fontes, "construir_indice", csv_quebrado)
    with caplog.at_level("WARNING"):
        assert fontes.obter_indice(AGORA, tmp_path).gerado_em == "2026-10-01"
    assert "usando o salvo" in caplog.text
    assert carregar_indice(tmp_path / "referencia").gerado_em == "2026-10-01"


def test_data_do_arquivo_e_a_do_download(tmp_path):
    arquivo = tmp_path / "a"
    arquivo.write_bytes(b"x")
    _baixado_em(arquivo, datetime(2026, 3, 4, 23, 59, tzinfo=UTC))
    assert fontes._data_do_arquivo(arquivo) == "2026-03-04"
