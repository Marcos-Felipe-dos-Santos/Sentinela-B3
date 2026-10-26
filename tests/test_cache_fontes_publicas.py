"""F2C-26: cache não muda o snapshot, a proveniência nem a ausência de dado."""

import json
import zipfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from cvm_fii_provider import CVMFIIProvider
from cvm_provider import CVMProvider
from sentinela.data.providers import b3_fundos, b3_proventos
from tests.test_b3_proventos import AGORA, _B3Falsa

CNPJ = "00.000.000/0001-00"
OUTRO = "11.111.111/0001-11"


def _zip(caminho: Path, valor: str = "100") -> Path:
    with zipfile.ZipFile(caminho, "w") as arquivo:
        arquivo.writestr(
            "itr_cia_aberta_DRE_con_2026.csv",
            "VL_CONTA;CNPJ_CIA\n" + valor + ";" + CNPJ,
        )
        arquivo.writestr(
            "inf_mensal_fii_complemento_2026.csv",
            "CNPJ_Fundo_Classe;Data_Referencia;Versao;Valor_Patrimonial_Cotas\n"
            + CNPJ
            + ";2026-09-30;1;NaN\n"
            + OUTRO
            + ";2026-09-30;1;10",
        )
        arquivo.writestr(
            "inf_mensal_fii_geral_2026.csv",
            "CNPJ_Fundo_Classe;Data_Referencia;Versao;Data_Entrega;Codigo_ISIN\n"
            + CNPJ
            + ";2026-09-30;1;2026-10-10;BRTSTA000001\n"
            + OUTRO
            + ";2026-09-30;1;2026-10-11;BRTSTB000001",
        )
        arquivo.writestr(
            "inf_mensal_fii_ativo_passivo_2026.csv",
            "CNPJ_Fundo_Classe;Data_Referencia;Versao;Imoveis\n"
            + CNPJ
            + ";2026-09-30;1;90\n"
            + OUTRO
            + ";2026-09-30;1;80",
        )
    return caminho


def test_read_raw_reusa_csv_e_devolve_copia(tmp_path: Path) -> None:
    caminho = _zip(tmp_path / "fontes.zip")
    provedor = CVMProvider(cache_dir=str(tmp_path / "cvm"))
    with patch.object(pd, "read_csv", wraps=pd.read_csv) as ler:
        primeiro = provedor._read_raw(caminho, "DRE_con")
        primeiro.loc[0, "VL_CONTA"] = "alterado"
        segundo = provedor._read_raw(caminho, "DRE_con")
    assert segundo.loc[0, "VL_CONTA"] == "100"
    assert ler.call_count == 1


def test_informe_compartilha_tabelas_entre_fundos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caminho = _zip(tmp_path / "fontes.zip")
    provedor = CVMFIIProvider(cache_dir=str(tmp_path / "fii"))
    monkeypatch.setattr(provedor, "baixar_informe", lambda ano: caminho)
    with patch.object(pd, "read_csv", wraps=pd.read_csv) as ler:
        primeiro = provedor._linhas_do_fundo(CNPJ, 2026)
        segundo = provedor._linhas_do_fundo(OUTRO, 2026)
        primeiro[1][0]["Valor_Patrimonial_Cotas"] = "alterado"
        repetido = provedor._linhas_do_fundo(CNPJ, 2026)
    assert ler.call_count == 3
    assert repetido[1][0]["Valor_Patrimonial_Cotas"] == "NaN"
    assert repetido[1][0]["Data_Entrega"] == "2026-10-10"
    assert repetido[1][0]["Codigo_ISIN"] == "BRTSTA000001"
    assert segundo[1][0]["Valor_Patrimonial_Cotas"] == "10"
    assert segundo[2][0]["Imoveis"] == "80"


def test_literal_e_na_padrao_nao_compartilham_projecao(tmp_path: Path) -> None:
    caminho = _zip(tmp_path / "fontes.zip")
    provedor = CVMFIIProvider(cache_dir=str(tmp_path / "fii"))
    with patch.object(pd, "read_csv", wraps=pd.read_csv) as ler:
        for _ in range(2):
            literal = provedor._parsear_complemento(caminho, 2026, literal=True)
            padrao = provedor._parsear_complemento(caminho, 2026)
    assert literal.loc[0, "Valor_Patrimonial_Cotas"] == "NaN"
    assert pd.isna(padrao.loc[0, "Valor_Patrimonial_Cotas"])
    assert ler.call_count == 2


def test_b3_reusa_tres_chamadas_so_na_mesma_coleta() -> None:
    obter = _B3Falsa([[{"n": 1}]])
    primeiro = b3_proventos.coletar(8133, AGORA, obter)
    segundo = b3_proventos.coletar(8133, AGORA, obter)
    assert primeiro == segundo
    assert len(obter.urls) == 3
    segundo.registros[0]["n"] = "alterado"
    assert b3_proventos.coletar(8133, AGORA, obter).registros[0]["n"] == 1
    outra_coleta = b3_proventos.coletar(8133, AGORA + timedelta(seconds=1), obter)
    assert outra_coleta.coleta != primeiro.coleta
    assert len(obter.urls) == 6


def test_b3_fundos_reusa_snapshot_completo_sem_mudar_proveniencia() -> None:
    fixture = json.loads(
        (
            Path(__file__).parent / "fixtures/contratos/b3_fundos_hglg_2026.json"
        ).read_text()
    )
    corpo = json.loads(fixture["membros"]["GetListedSupplementFunds"])
    chamadas: list[str] = []

    def obter(endereco: str) -> tuple[dict, dict]:
        chamadas.append(endereco)
        return corpo, {"url": endereco, "sha256": fixture["sha256_original"]}

    primeiro = b3_fundos.coletar("11.728.688/0001-47", "HGLG11", AGORA, obter)
    segundo = b3_fundos.coletar("11.728.688/0001-47", "HGLG11", AGORA, obter)
    assert primeiro == segundo
    assert len(chamadas) == 1
    segundo["resposta"]["cashDividends"].clear()
    assert b3_fundos.coletar("11.728.688/0001-47", "HGLG11", AGORA, obter)["resposta"][
        "cashDividends"
    ]
    assert len(chamadas) == 1


def test_arquivo_modificado_invalida_leitura_por_mtime_ns(tmp_path: Path) -> None:
    import os

    caminho = _zip(tmp_path / "fontes.zip")
    provedor = CVMProvider(cache_dir=str(tmp_path / "cvm"))
    with patch.object(pd, "read_csv", wraps=pd.read_csv) as ler:
        assert provedor._read_raw(caminho, "DRE_con").loc[0, "VL_CONTA"] == "100"
        stat = caminho.stat()
        _zip(caminho, "250")
        os.utime(caminho, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))
        assert provedor._read_raw(caminho, "DRE_con").loc[0, "VL_CONTA"] == "250"
    assert ler.call_count == 2


def test_cache_de_copias_e_limitado_e_isolado() -> None:
    from sentinela.data.cache_leitura import CacheCopia

    cache: CacheCopia[dict] = CacheCopia(limite=2)
    original = {"valores": [1]}
    cache.guardar("a", original)
    original["valores"].append(2)
    assert cache.buscar("a") == {"valores": [1]}
    cache.guardar("b", {"valores": [2]})
    copia = cache.buscar("a")
    copia["valores"].clear()
    cache.guardar("c", {"valores": [3]})
    assert cache.buscar("a") == {"valores": [1]}
    assert cache.buscar("b") is None
    assert cache.buscar("c") == {"valores": [3]}


@pytest.mark.parametrize("total_incompleto", [None, 2])
def test_b3_falha_ou_paginacao_incompleta_nao_vira_snapshot(
    total_incompleto: int | None,
) -> None:
    b3 = _B3Falsa([[{"n": 1}]])
    b3.total = total_incompleto
    primeiro = b3_proventos.coletar(8133, AGORA, b3)
    assert primeiro.total == total_incompleto
    b3.total = 1
    segundo = b3_proventos.coletar(8133, AGORA, b3)
    assert segundo.total == 1
    assert len(b3.urls) == 6


def test_b3_nao_usa_snapshot_anterior_quando_outra_coleta_falha() -> None:
    b3 = _B3Falsa([[{"n": 1}]])
    falhar = False

    def obter(endereco: str) -> tuple[object, dict]:
        if falhar:
            raise OSError("fonte indisponível")
        return b3(endereco)

    primeiro = b3_proventos.coletar(8133, AGORA, obter)
    falhar = True
    with pytest.raises(OSError, match="indisponível"):
        b3_proventos.coletar(8133, AGORA + timedelta(seconds=1), obter)
    assert primeiro.coleta == AGORA.isoformat()


def test_b3_fundo_generico_nao_e_reutilizado_como_snapshot() -> None:
    corpo = {
        "code": "HGLG",
        "fund": "ISIN GENERIC",
        "cashDividends": [],
        "stockDividends": [],
    }
    chamadas: list[str] = []

    def obter(endereco: str) -> tuple[dict, dict]:
        chamadas.append(endereco)
        return corpo, {"url": endereco}

    b3_fundos.coletar("11.728.688/0001-47", "HGLG11", AGORA, obter)
    corpo["fund"] = "FII TESTE"
    segundo = b3_fundos.coletar("11.728.688/0001-47", "HGLG11", AGORA, obter)
    assert segundo["resposta"]["fund"] == "FII TESTE"
    assert len(chamadas) == 2


def test_callback_nao_hashable_reusa_pela_identidade_sem_avaliar_hash() -> None:
    class SemHash(_B3Falsa):
        __hash__ = None

    b3 = SemHash([[{"n": 1}]])
    primeiro = b3_proventos.coletar(8133, AGORA, b3)
    segundo = b3_proventos.coletar(8133, AGORA, b3)
    assert primeiro == segundo
    assert len(b3.urls) == 3


def test_fundo_e_coleta_diferentes_nao_compartilham_snapshot() -> None:
    import base64

    chamadas: list[str] = []

    def obter(endereco: str) -> tuple[dict, dict]:
        chamadas.append(endereco)
        parametros = json.loads(base64.b64decode(endereco.rsplit("/", 1)[-1]))
        return {
            "code": parametros["identifierFund"],
            "fund": "FII SINTÉTICO",
            "cashDividends": [],
            "stockDividends": [],
        }, {"url": endereco}

    primeiro = b3_fundos.coletar(CNPJ, "TSTA11", AGORA, obter)
    outro = b3_fundos.coletar(OUTRO, "TSTB11", AGORA, obter)
    mais_recente = b3_fundos.coletar(
        CNPJ, "TSTA11", AGORA + timedelta(seconds=1), obter
    )
    assert primeiro["codigo"] == "TSTA"
    assert outro["codigo"] == "TSTB"
    assert outro["resposta"]["code"] == "TSTB"
    assert mais_recente["coleta"] == (AGORA + timedelta(seconds=1)).isoformat()
    assert len(chamadas) == 3
