"""BUG-3-49 (Gemini A1): versão indisponível não desloca a janela do FII.

ZIPs no layout CVM → carga real → remontagem → provedor e DY reais. A janela
anterior dá 12%; maio, com DY mensal de 2%, dá 13%. Não há mocks intermediários.
"""

import io
import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from cvm_fii_provider import CVMFIIProvider
from sentinela.data import fii_elegibilidade, rendimento_fii
from sentinela.data.pit import carga_cvm, leitura
from sentinela.data.store import migracoes
from sentinela.services.historico import FONTE_PRECO, MotorHistorico

CNPJ = "11.111.111/0001-11"
D = datetime(2023, 6, 30, 15, tzinfo=UTC)


def _fontes(pasta: Path, caso: str) -> list[Path]:
    pasta.mkdir(parents=True, exist_ok=True)
    por_ano: dict[int, dict[str, list[dict]]] = {}
    for indice in range(2022 * 12 + 3, 2023 * 12 + 5):
        ano, m = divmod(indice, 12)
        mes = m + 1
        ref = f"{ano:04d}-{mes:02d}-01"
        seguinte_ano, seguinte_mes = divmod(indice + 1, 12)
        entrega = f"{seguinte_ano:04d}-{seguinte_mes + 1:02d}-10"
        ultima = ref == "2023-05-01"
        versao = "2" if ultima and caso in ("reapresentacao", "sem_numeros") else "1"
        if ultima and caso in ("reapresentacao", "sem_numeros", "futuro"):
            entrega = "2023-08-15"
        if ultima and caso == "em_d":
            entrega = "2023-06-30"
        geral = {
            "CNPJ_Fundo_Classe": CNPJ,
            "Data_Referencia": ref,
            "Versao": versao,
            "Data_Entrega": entrega,
            "Codigo_ISIN": "BRTSTFCTF000",
        }
        comp = {
            "CNPJ_Fundo_Classe": CNPJ,
            "Data_Referencia": ref,
            "Versao": versao,
            "Patrimonio_Liquido": "2000" if ultima else "1000",
            "Cotas_Emitidas": "10",
            "Valor_Patrimonial_Cotas": "200" if ultima else "100",
            "Percentual_Dividend_Yield_Mes": "0.02" if ultima else "0.01",
            "Percentual_Amortizacao_Cotas_Mes": "0",
        }
        partes = por_ano.setdefault(ano, {"geral": [], "complemento": []})
        partes["geral"].append(geral)
        if ultima and caso == "exploratorio_sem_complemento":
            partes["geral"].append(geral | {"Versao": "2", "Data_Entrega": "2023-08-15"})
        if ultima and caso == "sem_numeros":
            partes["geral"].append(
                geral | {"Versao": "1", "Data_Entrega": "2023-06-10"}
            )
        if ultima and caso in ("pl_vazio", "pl_ilegivel"):
            comp["Patrimonio_Liquido"] = "" if caso == "pl_vazio" else "ilegivel"
        partes["complemento"].append(comp)
        if ultima and caso == "conflito_pl":
            partes["complemento"].append(comp | {"Patrimonio_Liquido": "3000"})
        if ultima and caso == "conflito_complemento":
            partes["complemento"].append(comp | {"Valor_Patrimonial_Cotas": "300"})
        if (ultima and caso == "conflito") or (
            ref == "2022-04-01" and caso == "conflito_antigo"
        ):
            partes["geral"].append(geral | {"Data_Entrega": entrega[:-2] + "11"})
    if caso == "mes_aberto":
        partes = por_ano[2023]
        partes["geral"].append(
            geral | {"Data_Referencia": "2023-06-01", "Data_Entrega": "2023-06-15"}
        )
        partes["complemento"].append(
            comp | {"Data_Referencia": "2023-06-01", "Valor_Patrimonial_Cotas": "900"}
        )
    arquivos = []
    for ano, partes in por_ano.items():
        caminho = pasta / f"inf_mensal_fii_{ano}.zip"
        with zipfile.ZipFile(caminho, "w") as z:
            for parte, linhas in partes.items():
                saida = io.StringIO()
                pd.DataFrame(linhas).to_csv(saida, sep=";", index=False)
                z.writestr(
                    f"inf_mensal_fii_{parte}_{ano}.csv",
                    saida.getvalue().encode("latin-1"),
                )
        arquivos.append(caminho)
    return arquivos


def _motor(
    conn: sqlite3.Connection, tmp_path: Path, caso: str, modo: str = leitura.ESTRITO
) -> MotorHistorico:
    for arquivo in _fontes(tmp_path / "fontes", caso):
        carga_cvm.carregar(
            conn,
            arquivo,
            tipo="FII_INFORME",
            fonte="CVM sintética",
            coleta="2026-11-17T00:00:00+00:00",
        )
    return MotorHistorico(conn, D, tmp_path / "pit", pd.DataFrame(), modo=modo)


@pytest.mark.parametrize(
    "caso,motivo",
    [
        ("reapresentacao", leitura.MOTIVO_ENTREGA_POSTERIOR),
        ("conflito", leitura.MOTIVO_GERAL_EM_CONFLITO),
        ("sem_numeros", leitura.MOTIVO_SEM_NUMEROS),
        ("conflito_complemento", rendimento_fii.MOTIVO_CONFLITO),
    ],
)
def test_motor_abstem_sem_deslocar_janela(
    tmp_path: Path, caso: str, motivo: str
) -> None:
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        motor = _motor(conn, tmp_path, caso)
        dados = {
            "cnpj": CNPJ,
            "classe_ativo": "FII",
            "preco_atual": 100,
            "fonte_preco": FONTE_PRECO,
        }
        motor._buscar_rendimento_fii("TSTF11", dados, as_of=D)
        assert "dy" not in dados, dados.get("dy")
        assert dados["informe_fii"].get("abstencao") == motivo
        assert any(motivo in r for r in dados.get("riscos_dados", []))


@pytest.mark.parametrize(
    "caso,referencia,valor",
    [
        ("futuro", "2023-04-01", 100),
        ("em_d", "2023-04-01", 100),
        ("mes_aberto", "2023-05-01", 200),
    ],
)
def test_provedor_direto_corta_mes_e_entrega(
    tmp_path: Path, caso: str, referencia: str, valor: int
) -> None:
    pasta = tmp_path / "origem"
    _fontes(pasta, caso)
    provedor = CVMFIIProvider(cache_dir=str(pasta))
    resultado = provedor.obter_dados_fii(CNPJ, as_of=D)
    assert resultado["dt_referencia"] == referencia
    assert resultado["valor_cota"] == pytest.approx(valor)


def test_exploratorio_usa_reapresentacao_rotulada_sem_alterar_entrega(
    tmp_path: Path,
) -> None:
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        motor = _motor(conn, tmp_path, "reapresentacao", leitura.EXPLORATORIO)
        informe = motor.cvm_fii.obter_rendimentos_fii(CNPJ, as_of=D)
        recente = max(informe["registros"], key=lambda r: r["Data_Referencia"])
        assert recente["Data_Referencia"] == "2023-05-01"
        assert recente["Data_Entrega"] == "2023-08-15"
        assert leitura.AVISO_EXPLORATORIO in informe["avisos"]
        medida = rendimento_fii.dy_entregue_ate(informe["registros"], 100, D.date())
        assert medida["mes_final"] == "2023-05"
        assert medida["dy"] == pytest.approx(0.13)


@pytest.mark.parametrize("caso", ["normal", "conflito_antigo"])
def test_documento_antigo_fora_da_janela_nao_bloqueia_mes_vigente(
    tmp_path: Path, caso: str
) -> None:
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        motor = _motor(conn, tmp_path, caso)
        dados = {
            "cnpj": CNPJ,
            "classe_ativo": "FII",
            "preco_atual": 100,
            "fonte_preco": FONTE_PRECO,
        }
        motor._buscar_rendimento_fii("TSTF11", dados, as_of=D)
        assert dados["dy"] == pytest.approx(0.13)


@pytest.mark.parametrize(
    "caso,motivo",
    [
        ("reapresentacao", leitura.MOTIVO_ENTREGA_POSTERIOR),
        ("conflito", leitura.MOTIVO_GERAL_EM_CONFLITO),
        ("sem_numeros", leitura.MOTIVO_SEM_NUMEROS),
        ("conflito_complemento", rendimento_fii.MOTIVO_CONFLITO),
    ],
)
def test_vpa_historico_abstem_sem_recuar(
    tmp_path: Path, caso: str, motivo: str
) -> None:
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        motor = _motor(conn, tmp_path, caso)
        valor = motor.cvm_fii.obter_dados_fii(CNPJ, as_of=D)
        assert "valor_cota" not in valor
        assert valor.get("abstencao") == motivo


def test_estrito_nao_recebe_zip_exploratorio_do_mesmo_dia(tmp_path: Path) -> None:
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        estrito = _motor(conn, tmp_path, "reapresentacao")
        exploratorio = _motor(conn, tmp_path, "reapresentacao", leitura.EXPLORATORIO)
        assert (
            estrito.cvm_fii.obter_rendimentos_fii(CNPJ, as_of=D).get("abstencao")
            == leitura.MOTIVO_ENTREGA_POSTERIOR
        )
        assert exploratorio.cvm_fii.obter_rendimentos_fii(CNPJ, as_of=D)["registros"]
        assert (
            estrito.cvm_fii.obter_rendimentos_fii(CNPJ, as_of=D).get("abstencao")
            == leitura.MOTIVO_ENTREGA_POSTERIOR
        )


def test_disponibilidade_exploratoria_nao_vaza_para_outro_dia(tmp_path: Path) -> None:
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        motor = _motor(conn, tmp_path, "reapresentacao", leitura.EXPLORATORIO)
        informe = motor.cvm_fii.obter_rendimentos_fii(CNPJ, as_of=D)
        outro_dia = datetime(2023, 5, 30, 15, tzinfo=UTC).date()
        medida = rendimento_fii.dy_entregue_ate(informe["registros"], 100, outro_dia)
        assert medida["mes_final"] == "2023-04"
        assert medida["dy"] == pytest.approx(0.12)


@pytest.mark.parametrize("caso", ["pl_vazio", "pl_ilegivel", "conflito_pl"])
def test_consumidor_vpa_nao_recua_nem_escolhe_patrimonio_conflitante(
    tmp_path: Path, caso: str
) -> None:
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        motor = _motor(conn, tmp_path, caso)
        dados = {"cnpj": CNPJ, "classe_ativo": "FII", "preco_atual": 100}
        motor._buscar_cvm_fii("TSTF11", dados, as_of=D)
        assert "vpa" not in dados
        assert "pvp" not in dados
        assert any("Informe Mensal do FII não usado" in r for r in dados["riscos_dados"])


def test_composicao_direta_so_usa_documentos_selecionados(tmp_path: Path) -> None:
    arquivos = _fontes(tmp_path, "mes_aberto")
    caminho = next(p for p in arquivos if "2023" in p.name)
    linhas = [
        {**{c: "0" for c in (*fii_elegibilidade.TIJOLO, *fii_elegibilidade.PAPEL,
                              *fii_elegibilidade.FUNDO_DE_FUNDOS)},
         "CNPJ_Fundo_Classe": CNPJ, "Data_Referencia": ref, "Versao": versao,
         "Imoveis_Renda_Acabados": "100" if (ref, versao) == ("2023-05-01", "1") else "0",
         "CRI": "0" if (ref, versao) == ("2023-05-01", "1") else "100"}
        for ref, versao in (("2023-05-01", "1"), ("2023-06-01", "1"), ("2023-05-01", "2"))
    ]
    with zipfile.ZipFile(caminho, "a") as z:
        z.writestr("inf_mensal_fii_ativo_passivo_2023.csv", pd.DataFrame(linhas).to_csv(sep=";", index=False))
    informe = CVMFIIProvider(cache_dir=str(tmp_path)).obter_rendimentos_fii(CNPJ, as_of=D)
    assert [(r["Data_Referencia"], r["Versao"]) for r in informe["composicoes"]] == [
        ("2023-05-01", "1")
    ]
    resultado = rendimento_fii.entradas({
        "informe_fii": informe, "preco_atual": 100, "ticker": "TSTF11",
        "disponibilidade_por_publicacao": True,
        "b3_fundo": {"coleta": D.isoformat(), "resposta": {
            "code": "TSTF", "fund": "FII SINTETICO", "cashDividends": [], "stockDividends": []}},
        "taxa_real": {"as_of": D.isoformat(), "data_base": "2023-06-29", "dias_uteis": 1,
                      "ntnb": 0.06},
    }, D)
    assert isinstance(resultado, dict), resultado
    assert resultado["tipo"] == "tijolo"
    assert resultado["dy"] == pytest.approx(0.13)


@pytest.mark.parametrize("campo", ["Patrimonio_Liquido", "Valor_Patrimonial_Cotas", "Cotas_Emitidas"])
@pytest.mark.parametrize("valor", ["NaN", "inf"])
def test_informe_vigente_nao_aceita_numero_nao_finito(
    tmp_path: Path, campo: str, valor: str
) -> None:
    arquivos = _fontes(tmp_path, "normal")
    caminho = next(p for p in arquivos if "2023" in p.name)
    with zipfile.ZipFile(caminho) as z:
        membros = {n: z.read(n) for n in z.namelist()}
    nome = "inf_mensal_fii_complemento_2023.csv"
    tabela = pd.read_csv(io.BytesIO(membros[nome]), sep=";", dtype=str, keep_default_na=False)
    tabela.loc[tabela["Data_Referencia"] == "2023-05-01", campo] = valor
    membros[nome] = tabela.to_csv(sep=";", index=False).encode("latin-1")
    with zipfile.ZipFile(caminho, "w") as z:
        for nome, conteudo in membros.items():
            z.writestr(nome, conteudo)
    informe = CVMFIIProvider(cache_dir=str(tmp_path)).obter_dados_fii(CNPJ, as_of=D)
    assert campo in informe.get("abstencao", "")
    assert "valor_cota" not in informe


@pytest.mark.parametrize("campo", ["vpa", "dy"])
def test_exploratorio_nao_recua_quando_maior_versao_nao_tem_complemento(
    tmp_path: Path, campo: str
) -> None:
    with closing(sqlite3.connect(":memory:")) as conn:
        migracoes.aplicar(conn)
        motor = _motor(conn, tmp_path, "exploratorio_sem_complemento", leitura.EXPLORATORIO)
        if campo == "vpa":
            informe = motor.cvm_fii.obter_dados_fii(CNPJ, as_of=D)
        else:
            dados = {"cnpj": CNPJ, "classe_ativo": "FII", "preco_atual": 100}
            motor._buscar_rendimento_fii("TSTF11", dados, as_of=D)
            assert "dy" not in dados
            informe = dados["informe_fii"]
        assert informe.get("abstencao") == leitura.MOTIVO_SEM_NUMEROS


@pytest.mark.parametrize("consumidor", ["vpa", "rendimento"])
@pytest.mark.parametrize("posterior_primeira", [True, False])
def test_proveniencia_igual_a_entrega_selecionada(
    tmp_path: Path, consumidor: str, posterior_primeira: bool
) -> None:
    arquivos = _fontes(tmp_path, "normal")
    caminho = next(p for p in arquivos if "2023" in p.name)
    with zipfile.ZipFile(caminho) as z:
        membros = {n: z.read(n) for n in z.namelist()}
    nome = "inf_mensal_fii_geral_2023.csv"
    tabela = pd.read_csv(io.BytesIO(membros[nome]), sep=";", dtype=str, keep_default_na=False)
    selecionada = tabela[tabela["Data_Referencia"] == "2023-05-01"].iloc[0].to_dict()
    posterior = selecionada | {"Data_Entrega": "2023-08-15"}
    outras = tabela[tabela["Data_Referencia"] != "2023-05-01"].to_dict("records")
    entregas = [posterior, selecionada] if posterior_primeira else [selecionada, posterior]
    membros[nome] = pd.DataFrame(outras + entregas).to_csv(sep=";", index=False).encode("latin-1")
    with zipfile.ZipFile(caminho, "w") as z:
        for nome, conteudo in membros.items():
            z.writestr(nome, conteudo)
    provedor = CVMFIIProvider(cache_dir=str(tmp_path))
    informe = provedor.obter_rendimentos_fii(CNPJ, as_of=D)
    usada = max(informe["registros"], key=lambda r: r["Data_Referencia"])
    assert {k: usada[k] for k in ("Data_Referencia", "Versao", "Data_Entrega")} == {
        k: selecionada[k] for k in ("Data_Referencia", "Versao", "Data_Entrega")
    }
    resultado = informe if consumidor == "rendimento" else provedor.obter_dados_fii(CNPJ, as_of=D)
    if consumidor == "vpa":
        assert resultado["dt_referencia"] == usada["Data_Referencia"]
        assert resultado["valor_cota"] == pytest.approx(float(usada["Valor_Patrimonial_Cotas"]))
    assert {k: resultado["proveniencia"][k] for k in (
        "periodo_referencia", "versao", "data_entrega"
    )} == {"periodo_referencia": usada["Data_Referencia"], "versao": usada["Versao"],
          "data_entrega": usada["Data_Entrega"]}


@pytest.mark.parametrize("conteudo", [b"", b'CNPJ_Fundo_Classe;Data_Referencia;Versao\n"sem fim'])
def test_composicao_ilegivel_nao_oculta_conflito_do_documento_vigente(
    tmp_path: Path, conteudo: bytes
) -> None:
    arquivos = _fontes(tmp_path, "conflito")
    for caminho in arquivos:
        ano = 2023 if "2023" in caminho.name else 2022
        with zipfile.ZipFile(caminho, "a") as z:
            legivel = pd.DataFrame([{
                "CNPJ_Fundo_Classe": CNPJ, "Data_Referencia": "2022-12-01", "Versao": "1",
                "Imoveis_Renda_Acabados": "100",
            }]).to_csv(sep=";", index=False).encode("latin-1")
            z.writestr(f"inf_mensal_fii_ativo_passivo_{ano}.csv", conteudo if ano == 2023 else legivel)
    motor = MotorHistorico.__new__(MotorHistorico)
    motor.cvm_fii = CVMFIIProvider(cache_dir=str(tmp_path))
    dados = {"cnpj": CNPJ, "classe_ativo": "FII", "preco_atual": 100}
    motor._buscar_cvm_fii("TSTF11", dados, as_of=D)
    assert "vpa" not in dados
    assert "pvp" not in dados
    assert any(leitura.MOTIVO_GERAL_EM_CONFLITO in r for r in dados["riscos_dados"])


@pytest.mark.parametrize("valor", ["", "ilegivel"])
def test_vpa_vigente_ilegivel_nao_recua_ao_mes_anterior(tmp_path: Path, valor: str) -> None:
    arquivos = _fontes(tmp_path, "normal")
    caminho = next(p for p in arquivos if "2023" in p.name)
    with zipfile.ZipFile(caminho) as z:
        membros = {nome: z.read(nome) for nome in z.namelist()}
    nome = "inf_mensal_fii_complemento_2023.csv"
    tabela = pd.read_csv(io.BytesIO(membros[nome]), sep=";", dtype=str, keep_default_na=False)
    assert tabela.loc[tabela["Data_Referencia"] == "2023-04-01", "Valor_Patrimonial_Cotas"].iloc[0] == "100"
    tabela.loc[tabela["Data_Referencia"] == "2023-05-01", "Valor_Patrimonial_Cotas"] = valor
    membros[nome] = tabela.to_csv(sep=";", index=False).encode("latin-1")
    with zipfile.ZipFile(caminho, "w") as z:
        for nome, conteudo in membros.items():
            z.writestr(nome, conteudo)
    motor = MotorHistorico.__new__(MotorHistorico)
    motor.cvm_fii = CVMFIIProvider(cache_dir=str(tmp_path))
    dados = {"cnpj": CNPJ, "classe_ativo": "FII", "preco_atual": 100}
    motor._buscar_cvm_fii("TSTF11", dados, as_of=D)
    assert "vpa" not in dados
    assert "pvp" not in dados
    assert any("Valor_Patrimonial_Cotas" in r for r in dados["riscos_dados"])


@pytest.mark.xfail(strict=True, reason="BUG-3-49/GA1b: seção vigente ilegível recua ao ano anterior")
@pytest.mark.parametrize("parte", ["complemento", "geral"])
@pytest.mark.parametrize("conteudo", [b"", b'CNPJ_Fundo_Classe;Data_Referencia;Versao\n"sem fim'])
@pytest.mark.parametrize("consumidor", ["vpa", "dy"])
def test_secao_vigente_ilegivel_nao_recua_ao_ano_anterior(
    tmp_path: Path, parte: str, conteudo: bytes, consumidor: str
) -> None:
    arquivos = _fontes(tmp_path, "normal")
    caminho = next(p for p in arquivos if "2023" in p.name)
    with zipfile.ZipFile(caminho) as z:
        membros = {nome: z.read(nome) for nome in z.namelist()}
    nome = f"inf_mensal_fii_{parte}_2023.csv"
    membros[nome] = conteudo
    with zipfile.ZipFile(caminho, "w") as z:
        for membro, dados_membro in membros.items():
            z.writestr(membro, dados_membro)
    # A janela de rendimento pode pedir 2021; arquivo local impede rede no teste.
    with zipfile.ZipFile(tmp_path / "inf_mensal_fii_2021.zip", "w") as z:
        z.writestr("inf_mensal_fii_complemento_2021.csv", "CNPJ_Fundo_Classe;Data_Referencia\n")
    motor = MotorHistorico.__new__(MotorHistorico)
    motor.cvm_fii = CVMFIIProvider(cache_dir=str(tmp_path))
    motor.dia = D.date()
    dados = {"cnpj": CNPJ, "classe_ativo": "FII", "preco_atual": 100,
             "fonte_preco": FONTE_PRECO}
    if consumidor == "vpa":
        motor._buscar_cvm_fii("TSTF11", dados, as_of=D)
        assert "vpa" not in dados
        assert "pvp" not in dados
    else:
        motor._buscar_rendimento_fii("TSTF11", dados, as_of=D)
        assert "dy" not in dados
    assert any("ilegível" in risco for risco in dados["riscos_dados"])
