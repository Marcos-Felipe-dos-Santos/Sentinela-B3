"""BUG-3-50 (Gemini A2): bloqueio do documento CVM pertence ao período.

GA2a corrige CSV antigo ilegível sem apagar exercício recente legível. Os
cenários ainda xfail estritos têm destino no GA2b: vigência pela última entrega,
sem recuo da versão ou do período, e seletor isolado por companhia.
O ZIP sintético reproduz o índice e as versões da CVM sem banco real.
"""

import io
import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pytest

from cvm_provider import CVMProvider
from market_engine import MarketEngine
from sentinela.data import janelas_fundamentais, series_cvm
from sentinela.data.pit import carga_cvm, remontagem
from sentinela.data.store import migracoes

CNPJ = "00.000.000/0001-00"
CD_CVM = 9999


@pytest.fixture(autouse=True)
def _somente_arquivos_da_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    """Falha localmente se um ano não foi preparado no teste."""
    def ausente(_provedor: CVMProvider, ano: int) -> Path:
        raise FileNotFoundError(f"ano {ano} fora da fixture")

    monkeypatch.setattr(CVMProvider, "baixar_dfp", ausente)
    monkeypatch.setattr(CVMProvider, "baixar_itr", ausente)


def _arquivo(
    pasta: Path, documento: str, referencia: str, anterior: str | None,
    entrega_v2: str | None = None,
) -> Path:
    ano = int(referencia[:4])
    prefixo = documento.lower()
    caminho = pasta / f"{prefixo}_cia_aberta_{ano}.zip"
    entregas = []
    if anterior:
        entregas.append({
            "CNPJ_CIA": CNPJ, "CD_CVM": CD_CVM, "DT_REFER": anterior,
            "VERSAO": "1", "DT_RECEB": f"{ano}-08-15" if anterior.endswith("06-30") else f"{ano}-04-15",
        })
    entregas.extend([
        {"CNPJ_CIA": CNPJ, "CD_CVM": CD_CVM, "DT_REFER": referencia,
         "VERSAO": "1", "DT_RECEB": f"{ano}-10-15" if documento == "ITR" else f"{ano}-05-15"},
        {"CNPJ_CIA": CNPJ, "CD_CVM": CD_CVM, "DT_REFER": referencia,
         "VERSAO": "2", "DT_RECEB": entrega_v2 or f"{ano + 1}-02-15"},
    ])

    def linha(ref: str, versao: str, demonstracao: str) -> dict:
        ano_inicio = int(ref[:4]) - (1 if ref.endswith("03-31") and documento == "DFP" else 0)
        inicio = f"{ano_inicio}-04-01" if documento == "DFP" and ref.endswith("03-31") else f"{ano_inicio}-01-01"
        conta = "3.11" if demonstracao == "DRE_con" else "2.03"
        return {
            "CNPJ_CIA": CNPJ, "DT_REFER": ref, "VERSAO": versao,
            "DENOM_CIA": "COMPANHIA SINTETICA", "CD_CVM": CD_CVM,
            "GRUPO_DFP": "DF Consolidado", "MOEDA": "REAL", "ESCALA_MOEDA": "MIL",
            "ORDEM_EXERC": "ÚLTIMO", "DT_INI_EXERC": inicio, "DT_FIM_EXERC": ref,
            "COLUNA_DF": "ÚLTIMO", "CD_CONTA": conta,
            "DS_CONTA": "Lucro/Prejuízo Consolidado do Período" if demonstracao == "DRE_con" else "Patrimônio Líquido Consolidado",
            "VL_CONTA": "100", "ST_CONTA_FIXA": "NÃO",
        }

    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr(
            f"{prefixo}_cia_aberta_{ano}.csv",
            pd.DataFrame(entregas).to_csv(sep=";", index=False).encode("latin-1"),
        )
        for demonstracao in ("BPA_con", "BPP_con", "DRE_con", "DVA_con"):
            linhas = []
            if demonstracao in ("BPP_con", "DRE_con"):
                if anterior:
                    linhas.append(linha(anterior, "1", demonstracao))
                linhas.append(linha(referencia, "2", demonstracao))
            texto = pd.DataFrame(linhas, columns=remontagem._cabecalho(demonstracao))
            z.writestr(
                f"{prefixo}_cia_aberta_{demonstracao}_{ano}.csv",
                texto.to_csv(sep=";", index=False).encode("latin-1"),
            )
    return caminho


def _provedor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, documento: str,
    referencia: str, anterior: str | None, as_of: datetime,
    entrega_v2: str | None = None,
) -> CVMProvider:
    arquivo = _arquivo(tmp_path, documento, referencia, anterior, entrega_v2)
    base = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(
        base, "baixar_dfp" if documento == "DFP" else "baixar_itr", lambda ano: arquivo
    )
    def ausente(ano: int) -> Path:
        raise FileNotFoundError(f"ano {ano} fora da fixture")

    monkeypatch.setattr(
        base, "baixar_itr" if documento == "DFP" else "baixar_dfp", ausente
    )
    return base.recorte_em(as_of)


def _acumulado(
    documento: str, ano: int, trimestre: int, versao: int = 1
) -> series_cvm.Acumulado:
    fim = date(ano, (3, 6, 9, 12)[trimestre - 1], (31, 30, 30, 31)[trimestre - 1])
    valores = {campo: float(trimestre * 10) for campo in series_cvm.CAMPOS_TTM}
    proveniencia = {
        campo: {"perimetro": "companhia/empresa/consolidado", "evidencia_comparabilidade": "mesmo CNPJ e modelo"}
        for campo in valores
    }
    return series_cvm.Acumulado(
        documento, fim.isoformat(), versao, date(ano, 1, 1), fim,
        valores=valores, proveniencia=proveniencia,
    )


def _sem_dre(origem: Path, pasta: Path) -> Path:
    pasta.mkdir()
    destino = pasta / origem.name
    with zipfile.ZipFile(origem) as entrada, zipfile.ZipFile(destino, "w") as saida:
        for nome in entrada.namelist():
            if "DRE_con" not in nome:
                saida.writestr(nome, entrada.read(nome))
    return destino


def _entregas_invertidas(
    origem: Path, pasta: Path, entrega_v1: str, entrega_v2: str
) -> Path:
    """A versão numericamente menor chega depois; só ela é vigente na decisão 47."""
    pasta.mkdir()
    destino = pasta / origem.name
    with zipfile.ZipFile(origem) as entrada:
        membros = {nome: entrada.read(nome) for nome in entrada.namelist()}
    nome_indice = f"{origem.stem}.csv"
    indice = pd.read_csv(
        io.BytesIO(membros[nome_indice]), sep=";", encoding="latin-1", dtype=str
    )
    indice.loc[indice["VERSAO"] == "1", "DT_RECEB"] = entrega_v1
    indice.loc[indice["VERSAO"] == "2", "DT_RECEB"] = entrega_v2
    membros[nome_indice] = indice.to_csv(sep=";", index=False).encode("latin-1")
    with zipfile.ZipFile(destino, "w") as saida:
        for nome, conteudo in membros.items():
            saida.writestr(nome, conteudo)
    return destino


@pytest.mark.parametrize(
    ("fronteira", "documento", "referencia", "entrega_v1", "entrega_v2", "as_of"),
    [
        ("anual", "DFP", "2024-03-31", "2024-04-25", "2024-04-20", datetime(2024, 5, 1, 15, tzinfo=UTC)),
        ("indicadores", "DFP", "2023-12-31", "2024-03-25", "2024-03-20", datetime(2024, 4, 1, 15, tzinfo=UTC)),
        ("ttm", "ITR", "2023-09-30", "2023-11-15", "2023-10-15", datetime(2023, 11, 30, 15, tzinfo=UTC)),
    ],
)
@pytest.mark.xfail(strict=True, reason="BUG-3-50 / F3-AUD-GA2b: última DT_RECEB ainda não selecionada")
def test_versao_menor_recebida_depois_e_a_vigente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fronteira: str,
    documento: str, referencia: str, entrega_v1: str, entrega_v2: str,
    as_of: datetime,
) -> None:
    origem = _arquivo(tmp_path, documento, referencia, None, entrega_v2=entrega_v2)
    arquivo = _entregas_invertidas(origem, tmp_path / "invertida", entrega_v1, entrega_v2)
    base = CVMProvider(cache_dir=str(tmp_path / "cache"))
    baixar = "baixar_dfp" if documento == "DFP" else "baixar_itr"
    monkeypatch.setattr(base, baixar, lambda ano: arquivo)
    provedor = base.recorte_em(as_of)
    with pytest.raises(OSError, match="vigente"):
        if fronteira == "anual":
            provedor.exercicio_anual_mais_recente(CD_CVM, as_of.date())
        elif fronteira == "indicadores":
            provedor.calcular_indicadores(CD_CVM, anos=1, ano_final=2023)
        else:
            provedor.acumulados_ttm(CD_CVM, as_of.date())


@pytest.mark.xfail(strict=True, reason="BUG-3-50 / F3-AUD-GA2b: DRE de outra companhia apaga série legível")
def test_zip_corrente_sem_dre_de_outra_companhia_preserva_ano_anterior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    as_of = datetime(2024, 6, 30, 15, tzinfo=UTC)
    anterior = _arquivo(
        tmp_path, "DFP", "2023-12-31", None, entrega_v2="2024-05-15"
    )
    corrente = tmp_path / "dfp_cia_aberta_2024.zip"
    with zipfile.ZipFile(corrente, "w") as z:
        z.writestr(
            "dfp_cia_aberta_2024.csv",
            pd.DataFrame([{
                "CNPJ_CIA": "11.111.111/0001-11", "CD_CVM": 1111,
                "DT_REFER": "2024-03-31", "VERSAO": "1", "DT_RECEB": "2024-05-15",
            }]).to_csv(sep=";", index=False).encode("latin-1"),
        )
    base = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(base, "baixar_dfp", lambda ano: corrente if ano == 2024 else anterior)
    provedor = base.recorte_em(as_of)
    dados = {"classe_ativo": "STOCK", "especie": "ON"}
    MarketEngine.__new__(MarketEngine)._serie_cvm(
        "TST3", dados, provedor, CD_CVM, "empresa", as_of=as_of
    )
    assert [item["exercicio"] for item in dados["serie_cvm"]["exercicios"]] == [2023]


@pytest.mark.xfail(strict=True, reason="BUG-3-50 / F3-AUD-GA2b: seleção por entrega e guarda por período pendentes")
def test_exercicio_vigente_sem_numeros_abstem_em_vez_de_recuar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    as_of = datetime(2024, 6, 30, 15, tzinfo=UTC)
    provedor = _provedor(tmp_path, monkeypatch, "DFP", "2024-03-31", None, as_of)
    with pytest.raises(OSError, match="vigente"):
        provedor.exercicio_anual_mais_recente(CD_CVM, as_of.date())


@pytest.mark.xfail(strict=True, reason="BUG-3-50 / F3-AUD-GA2b: seleção por entrega e guarda por período pendentes")
def test_consumidor_registra_abstencao_da_serie_anual(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    as_of = datetime(2024, 6, 30, 15, tzinfo=UTC)
    provedor = _provedor(tmp_path, monkeypatch, "DFP", "2024-03-31", None, as_of)
    motor = MarketEngine.__new__(MarketEngine)
    dados = {"classe_ativo": "STOCK", "especie": "ON"}
    motor._serie_cvm("TST3", dados, provedor, CD_CVM, "empresa", as_of=as_of)
    assert "vigente" in dados["serie_cvm"]["abstencao"]


@pytest.mark.xfail(strict=True, reason="BUG-3-50 / F3-AUD-GA2b: seleção por entrega e guarda por período pendentes")
def test_indicadores_nao_usam_referencia_anterior_do_mesmo_ano(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    as_of = datetime(2024, 11, 30, 15, tzinfo=UTC)
    provedor = _provedor(tmp_path, monkeypatch, "DFP", "2024-06-30", "2024-03-31", as_of)
    with pytest.raises(OSError, match="vigente"):
        provedor.calcular_indicadores(CD_CVM, anos=1, ano_final=2024)


@pytest.mark.xfail(strict=True, reason="BUG-3-50 / F3-AUD-GA2b: seleção por entrega e guarda por período pendentes")
def test_ttm_nao_descarta_itr_vigente_sem_numeros(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    as_of = datetime(2023, 11, 30, 15, tzinfo=UTC)
    provedor = _provedor(tmp_path, monkeypatch, "ITR", "2023-09-30", "2023-06-30", as_of)
    with pytest.raises(OSError, match="vigente"):
        provedor.acumulados_ttm(CD_CVM, as_of.date())


@pytest.mark.xfail(strict=True, reason="BUG-3-50 / F3-AUD-GA2b: seleção por entrega e guarda por período pendentes")
def test_consumidor_registra_abstencao_do_ttm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    as_of = datetime(2023, 11, 30, 15, tzinfo=UTC)
    provedor = _provedor(tmp_path, monkeypatch, "ITR", "2023-09-30", "2023-06-30", as_of)
    monkeypatch.setattr(provedor, "exercicio_anual_mais_recente", lambda codigo, dia: 2022)
    monkeypatch.setattr(provedor, "indicadores_da_serie", lambda codigo, ano, modelo: {})
    motor = MarketEngine.__new__(MarketEngine)
    dados = {"classe_ativo": "STOCK", "especie": "ON"}
    motor._serie_cvm("TST3", dados, provedor, CD_CVM, "empresa", as_of=as_of)
    assert "vigente" in dados["ttm_cvm"]["abstencao"]


def test_versao_vigente_com_numeros_nao_abstem_o_exercicio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    as_of = datetime(2024, 6, 30, 15, tzinfo=UTC)
    provedor = _provedor(
        tmp_path, monkeypatch, "DFP", "2024-03-31", None, as_of,
        entrega_v2="2024-05-15",
    )
    assert provedor.exercicio_anual_mais_recente(CD_CVM, as_of.date()) == 2024


def test_versao_vigente_com_numeros_mantem_ttm_e_indicadores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    as_of = datetime(2023, 11, 30, 15, tzinfo=UTC)
    provedor = _provedor(
        tmp_path, monkeypatch, "ITR", "2023-09-30", "2023-06-30", as_of,
        entrega_v2="2023-10-15",
    )
    assert any(
        acumulado.dt_refer == "2023-09-30"
        for acumulado in provedor.acumulados_ttm(CD_CVM, as_of.date())
    )
    as_of_dfp = datetime(2024, 11, 30, 15, tzinfo=UTC)
    dfp = _provedor(
        tmp_path, monkeypatch, "DFP", "2024-06-30", "2024-03-31", as_of_dfp,
        entrega_v2="2024-10-15",
    )
    assert dfp.calcular_indicadores(CD_CVM, anos=1, ano_final=2024)[2024]["cvm_dt_refer"] == "2024-06-30"


@pytest.mark.xfail(strict=True, reason="BUG-3-50 / F3-AUD-GA2b: seleção por entrega e guarda por período pendentes")
def test_ttm_nao_recua_quando_dfp_posterior_mascara_itr_bloqueado(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O 4T posterior existe, mas sem o ITR de 9 meses não forma trimestre."""
    as_of = datetime(2024, 2, 1, 15, tzinfo=UTC)
    itr_2023 = _arquivo(tmp_path, "ITR", "2023-09-30", "2023-06-30")
    dfp_2023 = _arquivo(
        tmp_path, "DFP", "2023-12-31", None, entrega_v2="2024-01-15"
    )
    vazios = {}
    for documento in ("ITR", "DFP"):
        caminho = tmp_path / f"{documento.lower()}_cia_aberta_2022.zip"
        with zipfile.ZipFile(caminho, "w"):
            pass
        vazios[documento] = caminho
    base = CVMProvider(cache_dir=str(tmp_path / "cache"))

    def baixar(documento: str, ano: int) -> Path:
        if ano == 2023:
            return itr_2023 if documento == "ITR" else dfp_2023
        if ano == 2022:
            return vazios[documento]
        raise FileNotFoundError(f"ano {ano} fora da fixture")

    monkeypatch.setattr(base, "baixar_itr", lambda ano: baixar("ITR", ano))
    monkeypatch.setattr(base, "baixar_dfp", lambda ano: baixar("DFP", ano))
    provedor = base.recorte_em(as_of)

    por_fonte = {
        ("ITR", 2022): [_acumulado("ITR", 2022, q) for q in (1, 2, 3)],
        ("DFP", 2022): [_acumulado("DFP", 2022, 4)],
        ("ITR", 2023): [_acumulado("ITR", 2023, q) for q in (1, 2)],
        ("DFP", 2023): [_acumulado("DFP", 2023, 4, versao=2)],
    }

    def ler(arquivo: Path, documento: str, codigo: int, modelo: str):
        ano = int(arquivo.name.split("_")[3])
        return por_fonte[(documento, ano)]

    monkeypatch.setattr(provedor, "_acumulados_do_arquivo", ler)
    todos = [item for fonte in por_fonte.values() for item in fonte]
    assert series_cvm.ttm(todos, as_of.date())["fim"] == "2023-06-30"
    with pytest.raises(OSError, match="vigente"):
        provedor.acumulados_ttm(CD_CVM, as_of.date())


@pytest.mark.xfail(strict=True, reason="BUG-3-50 / F3-AUD-GA2b: seleção por entrega e guarda por período pendentes")
def test_conflito_da_versao_vigente_passa_pela_remontagem_e_abstem_consumidor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    as_of = datetime(2024, 11, 30, 15, tzinfo=UTC)
    origem = _arquivo(tmp_path, "DFP", "2024-06-30", "2024-03-31")
    pasta = tmp_path / "conflito"
    pasta.mkdir()
    conflitante = pasta / origem.name
    with zipfile.ZipFile(origem) as z:
        membros = {nome: z.read(nome) for nome in z.namelist()}
    nome_dre = "dfp_cia_aberta_DRE_con_2024.csv"
    dre = pd.read_csv(
        io.BytesIO(membros[nome_dre]), sep=";", encoding="latin-1", dtype=str
    )
    corrente = dre[dre["DT_REFER"] == "2024-06-30"].iloc[0]
    versao_1 = corrente.copy()
    versao_1["VERSAO"] = "1"
    versao_2 = versao_1.copy()
    versao_2["VL_CONTA"] = "200"
    dre = pd.concat([dre, pd.DataFrame([versao_1, versao_2])], ignore_index=True)
    membros[nome_dre] = dre.to_csv(sep=";", index=False).encode("latin-1")
    with zipfile.ZipFile(conflitante, "w") as z:
        for nome, conteudo in membros.items():
            z.writestr(nome, conteudo)

    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        carga_cvm.carregar(
            conn, conflitante, tipo="DFP", fonte="fixture", coleta="2024-11-29T12:00:00+00:00"
        )
        remontado, motivos = remontagem.zip_cia_em(
            conn, "DFP", 2024, as_of, tmp_path / "remontado"
        )
    assert (CNPJ, "2024-06-30") in motivos
    base = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(base, "baixar_dfp", lambda ano: remontado)

    def itr_ausente(ano: int) -> Path:
        raise FileNotFoundError(f"ITR {ano} fora da fixture")

    monkeypatch.setattr(base, "baixar_itr", itr_ausente)
    motor = MarketEngine.__new__(MarketEngine)
    dados = {"classe_ativo": "STOCK", "especie": "ON"}
    motor._serie_cvm("TST3", dados, base, CD_CVM, "empresa", as_of=as_of)
    assert "vigente" in dados["serie_cvm"]["abstencao"]


def test_ttm_ignora_bloqueio_antigo_fora_dos_quatro_trimestres(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provedor = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(provedor, "baixar_itr", lambda ano: tmp_path / f"itr_{ano}.zip")
    monkeypatch.setattr(provedor, "baixar_dfp", lambda ano: tmp_path / f"dfp_{ano}.zip")

    def ler(arquivo: Path, documento: str, codigo: int, modelo: str):
        ano = int(arquivo.stem.split("_")[1])
        if ano != 2023:
            return []
        return (
            [_acumulado("ITR", 2023, q) for q in (1, 2, 3)]
            if documento == "ITR" else [_acumulado("DFP", 2023, 4)]
        )

    monkeypatch.setattr(provedor, "_acumulados_do_arquivo", ler)
    with zipfile.ZipFile(tmp_path / "itr_2022.zip", "w") as z:
        z.writestr(
            "itr_cia_aberta_2022.csv",
            pd.DataFrame([{
                "CNPJ_CIA": CNPJ, "CD_CVM": CD_CVM,
                "DT_REFER": "2022-09-30", "VERSAO": "1", "DT_RECEB": "2022-10-15",
            }]).to_csv(sep=";", index=False).encode("latin-1"),
        )
    acumulados = provedor.acumulados_ttm(CD_CVM, date(2024, 2, 1))
    assert series_cvm.ttm(acumulados, date(2024, 2, 1))["fim"] == "2023-12-31"


def test_ttm_ignora_referencia_futura_no_indice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    futuro = tmp_path / "itr_cia_aberta_2024.zip"
    with zipfile.ZipFile(futuro, "w") as z:
        z.writestr(
            "itr_cia_aberta_2024.csv",
            pd.DataFrame([{
                "CNPJ_CIA": CNPJ, "CD_CVM": CD_CVM,
                "DT_REFER": "2024-03-31", "VERSAO": "1", "DT_RECEB": "2024-01-15",
            }]).to_csv(sep=";", index=False).encode("latin-1"),
        )
    provedor = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(
        provedor, "baixar_itr",
        lambda ano: futuro if ano == 2024 else tmp_path / f"itr_{ano}.zip",
    )
    monkeypatch.setattr(provedor, "baixar_dfp", lambda ano: tmp_path / f"dfp_{ano}.zip")

    def ler(arquivo: Path, documento: str, codigo: int, modelo: str):
        if "2023" not in arquivo.name:
            return []
        return (
            [_acumulado("ITR", 2023, q) for q in (1, 2, 3)]
            if documento == "ITR" else [_acumulado("DFP", 2023, 4)]
        )

    monkeypatch.setattr(provedor, "_acumulados_do_arquivo", ler)
    acumulados = provedor.acumulados_ttm(CD_CVM, date(2024, 2, 1))
    assert series_cvm.ttm(acumulados, date(2024, 2, 1))["fim"] == "2023-12-31"


@pytest.mark.xfail(strict=True, reason="BUG-3-50 / F3-AUD-GA2b: seleção por entrega e guarda por período pendentes")
def test_ttm_nao_recua_se_trimestre_bloqueado_precede_outro_no_mesmo_itr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    as_of = datetime(2024, 2, 1, 15, tzinfo=UTC)
    itr_2023 = tmp_path / "itr_cia_aberta_2023.zip"
    indice = pd.DataFrame([
        {"CNPJ_CIA": CNPJ, "CD_CVM": CD_CVM, "DT_REFER": referencia,
         "VERSAO": versao, "DT_RECEB": entrega}
        for referencia, versao, entrega in (
            ("2023-03-31", "1", "2023-04-15"),
            ("2023-06-30", "1", "2023-08-15"),
            ("2023-06-30", "2", "2024-02-15"),
            ("2023-09-30", "1", "2023-10-15"),
        )
    ])
    with zipfile.ZipFile(itr_2023, "w") as z:
        z.writestr(
            "itr_cia_aberta_2023.csv",
            indice.to_csv(sep=";", index=False).encode("latin-1"),
        )
    antigos = {}
    for documento in ("ITR", "DFP"):
        caminho = tmp_path / f"{documento.lower()}_cia_aberta_2022.zip"
        with zipfile.ZipFile(caminho, "w"):
            pass
        antigos[documento] = caminho
    base = CVMProvider(cache_dir=str(tmp_path / "cache"))

    def baixar(documento: str, ano: int) -> Path:
        if ano == 2023 and documento == "ITR":
            return itr_2023
        if ano == 2022:
            return antigos[documento]
        raise FileNotFoundError(f"ano {ano} fora da fixture")

    monkeypatch.setattr(base, "baixar_itr", lambda ano: baixar("ITR", ano))
    monkeypatch.setattr(base, "baixar_dfp", lambda ano: baixar("DFP", ano))
    provedor = base.recorte_em(as_of)
    por_fonte = {
        ("ITR", 2022): [_acumulado("ITR", 2022, q) for q in (1, 2, 3)],
        ("DFP", 2022): [_acumulado("DFP", 2022, 4)],
        ("ITR", 2023): [_acumulado("ITR", 2023, q) for q in (1, 3)],
    }

    def ler(arquivo: Path, documento: str, codigo: int, modelo: str):
        ano = int(arquivo.name.split("_")[3])
        return por_fonte[(documento, ano)]

    monkeypatch.setattr(provedor, "_acumulados_do_arquivo", ler)
    todos = [item for fonte in por_fonte.values() for item in fonte]
    assert series_cvm.ttm(todos, as_of.date())["fim"] == "2023-03-31"
    with pytest.raises(OSError, match="vigente"):
        provedor.acumulados_ttm(CD_CVM, as_of.date())


@pytest.mark.xfail(strict=True, reason="BUG-3-50 / F3-AUD-GA2b: seleção por entrega e guarda por período pendentes")
def test_indice_distingue_versao_vigente_bloqueada_de_referencia_legivel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    as_of = datetime(2023, 11, 30, 15, tzinfo=UTC)
    provedor = _provedor(
        tmp_path, monkeypatch, "ITR", "2023-09-30", "2023-06-30", as_of
    )
    # A versão 1 de setembro está no índice, mas só a versão 2 futura tem números.
    # O ITR legível de junho não pode ocupar o lugar de setembro no TTM.
    with pytest.raises(OSError, match="vigente"):
        provedor.acumulados_ttm(CD_CVM, as_of.date())


@pytest.mark.xfail(strict=True, reason="BUG-3-50 / F3-AUD-GA2b: seleção por entrega e guarda por período pendentes")
def test_ttm_nao_recua_se_csv_dre_vigente_esta_ausente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    as_of = datetime(2023, 11, 30, 15, tzinfo=UTC)
    itr_2023 = _sem_dre(
        _arquivo(tmp_path, "ITR", "2023-09-30", "2023-06-30"),
        tmp_path / "sem_dre",
    )
    antigos = {}
    for documento in ("ITR", "DFP"):
        caminho = tmp_path / f"{documento.lower()}_cia_aberta_2022.zip"
        with zipfile.ZipFile(caminho, "w"):
            pass
        antigos[documento] = caminho
    base = CVMProvider(cache_dir=str(tmp_path / "cache"))

    def baixar(documento: str, ano: int) -> Path:
        if ano == 2023 and documento == "ITR":
            return itr_2023
        if ano == 2022:
            return antigos[documento]
        raise FileNotFoundError(f"ano {ano} fora da fixture")

    monkeypatch.setattr(base, "baixar_itr", lambda ano: baixar("ITR", ano))
    monkeypatch.setattr(base, "baixar_dfp", lambda ano: baixar("DFP", ano))
    provedor = base.recorte_em(as_of)
    original = provedor._acumulados_do_arquivo

    def ler(arquivo: Path, documento: str, codigo: int, modelo: str):
        if "2023" in arquivo.name:
            return original(arquivo, documento, codigo, modelo)
        return (
            [_acumulado("ITR", 2022, q) for q in (1, 2, 3)]
            if documento == "ITR" else [_acumulado("DFP", 2022, 4)]
        )

    monkeypatch.setattr(provedor, "_acumulados_do_arquivo", ler)
    with pytest.raises(OSError, match="vigente"):
        provedor.acumulados_ttm(CD_CVM, as_of.date())


def test_indicadores_nao_omitem_indice_vigente_com_csv_dre_ausente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    as_of = datetime(2024, 11, 30, 15, tzinfo=UTC)
    dfp_2024 = _sem_dre(
        _arquivo(tmp_path, "DFP", "2024-06-30", "2024-03-31"),
        tmp_path / "sem_dre",
    )
    base = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(base, "baixar_dfp", lambda ano: dfp_2024)
    provedor = base.recorte_em(as_of)
    with pytest.raises(OSError, match="vigente"):
        provedor.calcular_indicadores(CD_CVM, anos=1, ano_final=2024)


def test_dfp_antiga_ilegivel_nao_apaga_exercicio_recente_legivel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Decisão 47: bloqueio pertence ao período; só a janela que o inclui fica incompleta."""
    recente = _arquivo(
        tmp_path, "DFP", "2023-12-31", None, entrega_v2="2024-05-15"
    )
    antiga = _sem_dre(
        _arquivo(tmp_path, "DFP", "2022-12-31", None, entrega_v2="2023-05-15"),
        tmp_path / "antiga_sem_dre",
    )
    base = CVMProvider(cache_dir=str(tmp_path / "cache"))

    def baixar(ano: int) -> Path:
        if ano == 2023:
            return recente
        if ano == 2022:
            return antiga
        raise FileNotFoundError(f"ano {ano} fora da fixture")

    monkeypatch.setattr(base, "baixar_dfp", baixar)
    provedor = base.recorte_em(datetime(2024, 6, 30, 15, tzinfo=UTC))
    indicadores = provedor.calcular_indicadores(CD_CVM, anos=2, ano_final=2023)
    assert 2023 in indicadores
    assert indicadores[2023]["lucro_liquido"] is not None
    assert 2022 not in indicadores
    serie = series_cvm.serie_anual(indicadores, 2023)
    assert [item["exercicio"] for item in serie] == [2023]


def test_api_legada_conserva_anos_anteriores_se_csv_final_falha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    anterior = _arquivo(
        tmp_path, "DFP", "2023-12-31", None, entrega_v2="2024-05-15"
    )
    final = _sem_dre(
        _arquivo(tmp_path, "DFP", "2024-03-31", None, entrega_v2="2024-05-15"),
        tmp_path / "final_sem_dre",
    )
    provedor = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(
        provedor, "baixar_dfp", lambda ano: final if ano == 2024 else anterior
    )
    indicadores = provedor.calcular_indicadores(CD_CVM, anos=2, ano_final=2024)
    assert 2024 not in indicadores
    assert indicadores[2023]["lucro_liquido"] is not None


def test_dfp_antiga_bloqueia_apenas_a_janela_de_cinco_que_a_contem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    as_of = datetime(2024, 6, 30, 15, tzinfo=UTC)
    arquivos = {
        ano: _arquivo(
            tmp_path, "DFP", f"{ano}-12-31", None,
            entrega_v2=f"{ano + 1}-05-15",
        )
        for ano in range(2019, 2024)
    }
    arquivos[2022] = _sem_dre(arquivos[2022], tmp_path / "antiga_sem_dre")
    base = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(base, "baixar_dfp", lambda ano: arquivos[ano])
    provedor = base.recorte_em(as_of)
    monkeypatch.setattr(provedor, "exercicio_anual_mais_recente", lambda codigo, dia: 2023)
    monkeypatch.setattr(provedor, "acumulados_ttm", lambda codigo, dia, modelo: [])
    dados = {"classe_ativo": "STOCK", "especie": "ON"}
    MarketEngine.__new__(MarketEngine)._serie_cvm(
        "TST3", dados, provedor, CD_CVM, "empresa", as_of=as_of
    )
    assert [item["exercicio"] for item in dados["serie_cvm"]["exercicios"]] == [
        2019, 2020, 2021, 2023
    ]
    assert dados["serie_cvm"]["cobertura"]["anos_ausentes"] == [2022]
    janela = janelas_fundamentais.entradas(dados, as_of)
    assert "cinco exercícios completos" in janela["graham"]["abstencao"]
    assert "cinco exercícios completos" in janela["lynch"]["abstencao"]


def test_ttm_bloqueio_antigo_nao_abstem_quatro_trimestres_posteriores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Um ITR bloqueado de 2023 está fora dos quatro trimestres de 2024."""
    antigo = tmp_path / "itr_2023.zip"
    with zipfile.ZipFile(antigo, "w") as z:
        z.writestr(
            "itr_cia_aberta_2023.csv",
            pd.DataFrame([{
                "CNPJ_CIA": CNPJ, "CD_CVM": CD_CVM,
                "DT_REFER": "2023-06-30", "VERSAO": "1", "DT_RECEB": "2023-08-15",
            }]).to_csv(sep=";", index=False).encode("latin-1"),
        )
    provedor = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(
        provedor, "baixar_itr",
        lambda ano: antigo if ano == 2023 else tmp_path / f"itr_{ano}.zip",
    )
    monkeypatch.setattr(provedor, "baixar_dfp", lambda ano: tmp_path / f"dfp_{ano}.zip")

    def ler(arquivo: Path, documento: str, codigo: int, modelo: str):
        if arquivo.name == "itr_2024.zip":
            return [_acumulado("ITR", 2024, q) for q in (1, 2, 3)]
        if arquivo.name == "dfp_2024.zip":
            return [_acumulado("DFP", 2024, 4)]
        return []

    monkeypatch.setattr(provedor, "_acumulados_do_arquivo", ler)
    data_referencia = date(2025, 2, 1)
    acumulados = provedor.acumulados_ttm(CD_CVM, data_referencia)
    assert series_cvm.ttm(acumulados, data_referencia)["fim"] == "2024-12-31"


def _indice_criptografado(origem: Path, pasta: Path) -> Path:
    """Cópia do ZIP com o índice de entregas marcado como criptografado (bit 0 do cabeçalho)."""
    pasta.mkdir()
    destino = pasta / origem.name
    indice = origem.name.replace(".zip", ".csv")
    dados = bytearray(origem.read_bytes())
    with zipfile.ZipFile(origem) as entrada:
        local = entrada.getinfo(indice).header_offset
    dados[local + 6] |= 0x1  # cabeçalho local: flag de uso geral
    nome = indice.encode()
    central = dados.find(b"PK\x01\x02")
    while central != -1:
        tamanho = int.from_bytes(dados[central + 28 : central + 30], "little")
        if bytes(dados[central + 46 : central + 46 + tamanho]) == nome:
            dados[central + 8] |= 0x1  # diretório central: a mesma flag
        central = dados.find(b"PK\x01\x02", central + 4)
    destino.write_bytes(bytes(dados))
    return destino


def test_api_legada_com_indice_criptografado_avisa_e_conserva_anos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Sem recorte PIT, o índice não é consultado: índice ilegível não derruba a API legada."""
    anterior = _arquivo(
        tmp_path, "DFP", "2023-12-31", None, entrega_v2="2024-05-15"
    )
    final = _indice_criptografado(
        _sem_dre(
            _arquivo(tmp_path, "DFP", "2024-03-31", None, entrega_v2="2024-05-15"),
            tmp_path / "final_sem_dre",
        ),
        tmp_path / "final_criptografado",
    )
    with zipfile.ZipFile(final) as zf, pytest.raises(RuntimeError, match="encrypted"):
        zf.open("dfp_cia_aberta_2024.csv")
    provedor = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(
        provedor, "baixar_dfp", lambda ano: final if ano == 2024 else anterior
    )
    with caplog.at_level("WARNING", logger="cvm_provider"):
        indicadores = provedor.calcular_indicadores(CD_CVM, anos=2, ano_final=2024)
    assert 2024 not in indicadores
    assert indicadores[2023]["lucro_liquido"] is not None
    assert any("ano=2024" in r.getMessage() for r in caplog.records)


def test_erro_depois_dos_csvs_lidos_nao_vira_bloqueio_do_periodo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Só a falha de leitura dos CSVs bloqueia o período; erro posterior segue como aviso."""
    dfp_2024 = _arquivo(tmp_path, "DFP", "2024-06-30", "2024-03-31")
    base = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(base, "baixar_dfp", lambda ano: dfp_2024)

    def falha(*_args: object, **_kwargs: object) -> dict:
        raise KeyError("proveniência indisponível")

    monkeypatch.setattr(CVMProvider, "proveniencia_do_documento", falha)
    provedor = base.recorte_em(datetime(2024, 11, 30, 15, tzinfo=UTC))
    with caplog.at_level("WARNING", logger="cvm_provider"):
        indicadores = provedor.calcular_indicadores(CD_CVM, anos=1, ano_final=2024)
    assert indicadores == {}
    assert any("ano=2024" in r.getMessage() for r in caplog.records)


@pytest.mark.xfail(strict=True, reason="BUG-3-50 / F3-AUD-GA2b: linha ilegível de outra companhia anula a abstenção")
def test_linha_ilegivel_de_outra_companhia_nao_anula_a_abstencao(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cada linha do índice é lida sozinha: a da própria companhia decide, a ordem não."""
    dfp_2024 = _sem_dre(
        _arquivo(tmp_path, "DFP", "2024-06-30", "2024-03-31"),
        tmp_path / "sem_dre",
    )
    with zipfile.ZipFile(dfp_2024) as zf:
        membros = {nome: zf.read(nome) for nome in zf.namelist()}
    indice = pd.read_csv(io.BytesIO(membros["dfp_cia_aberta_2024.csv"]), sep=";", dtype=str)
    outra = {coluna: "" for coluna in indice.columns}
    outra.update({
        "CNPJ_CIA": "11.111.111/0001-11", "DT_REFER": "2024-06-30",
        "VERSAO": "1", "DT_RECEB": "2024-08-01",
    })  # CD_CVM vazio: ilegível
    indice = pd.concat([pd.DataFrame([outra]), indice], ignore_index=True)
    membros["dfp_cia_aberta_2024.csv"] = indice.to_csv(sep=";", index=False).encode("latin-1")
    with zipfile.ZipFile(dfp_2024, "w") as zf:
        for nome, conteudo in membros.items():
            zf.writestr(nome, conteudo)
    base = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(base, "baixar_dfp", lambda ano: dfp_2024)
    provedor = base.recorte_em(datetime(2024, 11, 30, 15, tzinfo=UTC))
    with pytest.raises(OSError, match="vigente"):
        provedor.calcular_indicadores(CD_CVM, anos=1, ano_final=2024)
