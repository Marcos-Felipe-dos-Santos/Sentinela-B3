"""Setor, segmento do FII e espécie de controle no índice (F2A-2): arquivos sintéticos, sem rede.

Colunas pelo layout da CVM: `SETOR_ATIV` e `CONTROLE_ACIONARIO` do cadastro de companhias
abertas (`cad_cia_aberta.csv`) e `Segmento_Atuacao` do Informe Mensal de FII.
"""

import json

from sentinela.data.referencia import carregar_indice, salvar_indice
from sentinela.data.referencia.registro import Registro
from tests.test_referencia import _cadastro, _fca, _indice, _informe, _sem_fii


def test_setor_do_cadastro():
    cadastro = _cadastro(
        {"SETOR_ATIV": "Bancos", "CONTROLE_ACIONARIO": "PRIVADO"},
    )
    registro = _indice(cadastro=cadastro, informe=_sem_fii()).registros["TSTA3"]
    assert registro.setor == "Bancos"


def test_segmento_do_informe_mensal():
    informe = _informe().assign(Segmento_Atuacao="Logística")
    indice = _indice(fca=_fca().iloc[0:0], informe=informe)
    assert indice.registros["TSTF11"].segmento == "Logística"


def test_especie_de_controle():
    cadastro = _cadastro(
        {"SETOR_ATIV": "Energia Elétrica", "CONTROLE_ACIONARIO": "ESTATAL"}
    )
    registro = _indice(cadastro=cadastro, informe=_sem_fii()).registros["TSTA3"]
    assert registro.controle_acionario == "ESTATAL"


def test_atributos_vem_da_mesma_linha_do_cd_cvm():
    cadastro = _cadastro(
        {"CD_CVM": "1", "SIT": "CANCELADA", "SETOR_ATIV": "Velho", "CONTROLE_ACIONARIO": "ESTATAL"},
        {"CD_CVM": "2", "SIT": "ATIVO", "SETOR_ATIV": "Novo", "CONTROLE_ACIONARIO": "PRIVADO"},
    )  # fmt: skip
    registro = _indice(cadastro=cadastro, informe=_sem_fii()).registros["TSTA3"]
    assert (registro.cd_cvm, registro.setor, registro.controle_acionario) == (
        2,
        "Novo",
        "PRIVADO",
    )


def test_valores_vazios_ou_com_espaco():
    cadastro = _cadastro({"SETOR_ATIV": "  Bancos ", "CONTROLE_ACIONARIO": None})
    informe = _informe().assign(Segmento_Atuacao="   ")
    indice = _indice(cadastro=cadastro, informe=informe)
    assert indice.registros["TSTA3"].setor == "Bancos"
    assert indice.registros["TSTA3"].controle_acionario is None
    assert indice.registros["TSTF11"].segmento is None


def test_celula_vazia_do_csv_vira_none():
    cadastro = _cadastro(
        {"SETOR_ATIV": float("nan"), "CONTROLE_ACIONARIO": float("nan")}
    )
    informe = _informe().assign(Segmento_Atuacao=float("nan"))
    indice = _indice(cadastro=cadastro, informe=informe)
    acao, fii = indice.registros["TSTA3"], indice.registros["TSTF11"]
    assert (acao.setor, acao.controle_acionario, fii.segmento) == (None, None, None)


def test_arquivos_sem_as_colunas_deixam_os_campos_vazios():
    indice = _indice(cadastro=_cadastro(), informe=_informe())
    acao, fii = indice.registros["TSTA3"], indice.registros["TSTF11"]
    assert (acao.setor, acao.controle_acionario, acao.segmento) == (None, None, None)
    assert (fii.setor, fii.controle_acionario, fii.segmento) == (None, None, None)


def test_companhia_fora_do_cadastro_fica_sem_atributos():
    cadastro = _cadastro({"CNPJ_CIA": "99.999.999/0001-99", "SETOR_ATIV": "Bancos"})
    registro = _indice(cadastro=cadastro, informe=_sem_fii()).registros["TSTA3"]
    assert registro.setor is None
    assert registro.controle_acionario is None


def test_atributos_gravam_e_leem_igual(tmp_path):
    cadastro = _cadastro({"SETOR_ATIV": "Bancos", "CONTROLE_ACIONARIO": "PRIVADO"})
    informe = _informe().assign(Segmento_Atuacao="Híbrido")
    indice = _indice(cadastro=cadastro, informe=informe)
    caminho = salvar_indice(indice, tmp_path)
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    assert bruto["registros"]["TSTA3"]["setor"] == "Bancos"
    assert bruto["registros"]["TSTF11"]["segmento"] == "Híbrido"
    assert carregar_indice(tmp_path) == indice


def test_indice_salvo_antes_dos_atributos_ainda_e_lido():
    antigo = {
        "ticker": "TSTA3",
        "classe": "STOCK",
        "regra": "fca:codigo_ativo",
        "fonte": {},
    }
    registro = Registro.de_dict(antigo)
    assert (registro.setor, registro.controle_acionario, registro.segmento) == (
        None,
        None,
        None,
    )
