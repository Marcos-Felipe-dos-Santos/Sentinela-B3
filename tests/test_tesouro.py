"""CSV oficial do Tesouro: percentuais, datas e disponibilidade sem rede nos testes."""

import os
from datetime import UTC, date, datetime, timedelta

import pytest
import requests

from sentinela.data import proveniencia
from sentinela.data.providers import tesouro
from sentinela.domain.units import RateNominal, RateReal

CABECALHO = "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha\n"
CSV = CABECALHO + "Tesouro IPCA+;15/05/2035;15/10/2026;6,84;6,96;100;100\n"
INSTANTE = datetime(2026, 10, 19, 18, tzinfo=UTC)


def _cache(tmp_path, idade=timedelta(hours=2), conteudo=CSV):
    arquivo = tmp_path / "precotaxatesourodireto.csv"
    arquivo.write_text(conteudo, encoding="utf-8")
    coleta = (INSTANTE - idade).timestamp()
    os.utime(arquivo, (coleta, coleta))
    return arquivo


def _rede_fora(*args, **kwargs):
    raise requests.ConnectionError("rede fora")


def test_titulo_segue_o_layout_oficial():
    (titulo,) = tesouro.ler_csv(CSV, as_of=INSTANTE.date())
    assert titulo.nome == "Tesouro IPCA+"
    assert titulo.tipo == "NTN-B Principal"
    assert titulo.taxa_aplicacao == RateReal(0.0684)
    assert titulo.taxa_resgate == RateReal(0.0696)


@pytest.mark.parametrize(
    "nome,tipo,classe",
    [
        ("Tesouro IPCA+", "NTN-B Principal", RateReal),
        ("Tesouro IPCA+ com Juros Semestrais", "NTN-B", RateReal),
        ("Tesouro Prefixado", "prefixado", RateNominal),
        ("Tesouro Prefixado com Juros Semestrais", "prefixado", RateNominal),
    ],
)
def test_tipo_da_taxa_pelo_titulo(nome, tipo, classe):
    texto = CSV.replace("Tesouro IPCA+", nome)
    (titulo,) = tesouro.ler_csv(texto, as_of=INSTANTE.date())
    assert titulo.tipo == tipo
    assert isinstance(titulo.taxa_aplicacao, classe)
    assert isinstance(titulo.taxa_resgate, classe)


def test_vencimento_e_data_base():
    (titulo,) = tesouro.ler_csv(CSV, as_of=INSTANTE.date())
    assert titulo.vencimento == date(2035, 5, 15)
    assert titulo.data_base == date(2026, 10, 15)


def test_referencia_futura_e_recusada():
    assert tesouro.ler_csv(CSV, as_of=date(2026, 10, 14)) == ()


@pytest.mark.parametrize("taxa", ["", "texto", "NaN", "inf", "-100"])
def test_taxa_ilegivel_nao_finita_ou_fator_nao_positivo_e_recusada(taxa):
    with pytest.raises(ValueError):
        tesouro.ler_csv(CSV.replace("6,84", taxa), as_of=INSTANTE.date())


@pytest.mark.parametrize("taxa,esperado", [("0", 0.0), ("-1,5", -0.015)])
def test_taxas_reais_nulas_e_negativas_sao_dados(taxa, esperado):
    (titulo,) = tesouro.ler_csv(CSV.replace("6,84", taxa), as_of=INSTANTE.date())
    assert titulo.taxa_aplicacao == RateReal(esperado)


def test_conflito_na_mesma_chave_nao_muda_cesta_silenciosamente():
    linha = CSV.splitlines()[1]
    with pytest.raises(ValueError, match="conflitantes"):
        tesouro.ler_csv(
            CSV + linha.replace("6,84", "7,00") + "\n", as_of=INSTANTE.date()
        )
    assert len(tesouro.ler_csv(CSV + linha + "\n", as_of=INSTANTE.date())) == 1


def test_nao_escolhe_vertice_nem_transforma_selic_em_taxa_prefixada():
    texto = CSV + "Tesouro IPCA+;15/05/2029;15/10/2026;7,00;7,12\n"
    texto += "Tesouro Selic;01/03/2027;15/10/2026;0,01;0,02\n"
    titulos = tesouro.ler_csv(texto, as_of=INSTANTE.date())
    assert {t.vencimento.year for t in titulos} == {2029, 2035}
    assert all(isinstance(t.taxa_aplicacao, RateReal) for t in titulos)


@pytest.mark.parametrize(
    "texto", ["", CABECALHO, CSV.replace("Data Base;", "Outra Coluna;")]
)
def test_layout_ou_cesta_vazia_e_recusado(texto):
    with pytest.raises(ValueError):
        tesouro.ler_csv(texto, as_of=INSTANTE.date())


def test_rede_fora_usa_o_cache_com_aviso(tmp_path, monkeypatch):
    arquivo = _cache(tmp_path, timedelta(days=2))
    monkeypatch.setattr(tesouro.requests, "get", _rede_fora)
    snapshot = tesouro.TesouroProvider(tmp_path).baixar(INSTANTE)
    assert snapshot.caminho == arquivo
    assert snapshot.avisos and "cache" in snapshot.avisos[0]
    assert snapshot.proveniencia.documento == "Tesouro Direto"
    assert snapshot.proveniencia.data_entrega is None
    assert snapshot.proveniencia.motivo_sem_entrega
    assert tesouro.ler_snapshot(snapshot, as_of=INSTANTE)[0].data_base == date(
        2026, 10, 15
    )


def test_cache_fresco_nao_chama_rede_e_ttl_nao_usa_relogio(tmp_path, monkeypatch):
    _cache(tmp_path)
    monkeypatch.setattr(
        tesouro.requests, "get", lambda *a, **kw: pytest.fail("cache fresco")
    )
    snapshot = tesouro.TesouroProvider(tmp_path).baixar(INSTANTE)
    assert snapshot.avisos == ()


def test_cache_coletado_depois_da_analise_nao_prova_disponibilidade(tmp_path):
    arquivo = _cache(tmp_path, -timedelta(hours=1))
    prov = proveniencia.registrar_arquivo(arquivo, tesouro.URL, "Tesouro Direto", None)
    snapshot = tesouro.ArquivoTesouro(arquivo, prov)
    with pytest.raises(ValueError, match="posterior"):
        tesouro.ler_snapshot(snapshot, as_of=INSTANTE)


def test_download_atomico_preserva_fonte_e_hash(tmp_path, monkeypatch):
    class Resposta:
        content = CSV.encode("utf-8")

        def raise_for_status(self):
            pass

    def get(url, timeout):
        assert url == tesouro.URL and timeout > 0
        return Resposta()

    monkeypatch.setattr(tesouro.requests, "get", get)
    snapshot = tesouro.TesouroProvider(tmp_path).baixar(INSTANTE)
    assert snapshot.caminho.read_text(encoding="utf-8") == CSV
    assert snapshot.proveniencia.fonte == tesouro.URL
    assert len(snapshot.proveniencia.hash_sha256) == 64
    assert proveniencia.ler_registro(snapshot.caminho) == snapshot.proveniencia
    assert not list(tmp_path.glob("*.tmp"))


def test_rede_fora_sem_cache_nao_inventa_taxa(tmp_path, monkeypatch):
    monkeypatch.setattr(tesouro.requests, "get", _rede_fora)
    with pytest.raises(requests.RequestException):
        tesouro.TesouroProvider(tmp_path).baixar(INSTANTE)


def test_snapshot_sem_proveniencia_nao_prova_disponibilidade(tmp_path):
    arquivo = _cache(tmp_path)
    with pytest.raises(ValueError, match="proveniência"):
        tesouro.ler_snapshot(tesouro.ArquivoTesouro(arquivo, None), as_of=INSTANTE)


def test_instante_de_analise_exige_fuso(tmp_path):
    with pytest.raises(ValueError, match="fuso"):
        tesouro.TesouroProvider(tmp_path).baixar(INSTANTE.replace(tzinfo=None))


def test_snapshot_preserva_nomes_das_colunas_da_fonte(tmp_path, monkeypatch):
    _cache(tmp_path)
    monkeypatch.setattr(tesouro.requests, "get", _rede_fora)
    arquivo = tesouro.TesouroProvider(tmp_path).baixar(INSTANTE)
    assert arquivo.colunas_taxas == {
        "taxa_aplicacao": "Taxa Compra Manha",
        "taxa_resgate": "Taxa Venda Manha",
    }
    arquivo.colunas_taxas.clear()
    assert len(arquivo.colunas_taxas) == 2


def test_resposta_invalida_preserva_cache_anterior(tmp_path, monkeypatch):
    arquivo = _cache(tmp_path, timedelta(days=2))

    class Resposta:
        content = b"<html>indisponivel</html>"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(tesouro.requests, "get", lambda *a, **kw: Resposta())
    snapshot = tesouro.TesouroProvider(tmp_path).baixar(INSTANTE)
    assert arquivo.read_text() == CSV
    assert snapshot.avisos


def test_ttl_exatamente_um_dia_revalida_na_rede(tmp_path, monkeypatch):
    _cache(tmp_path, timedelta(days=1))
    monkeypatch.setattr(tesouro.requests, "get", _rede_fora)
    assert tesouro.TesouroProvider(tmp_path).baixar(INSTANTE).avisos


def test_cache_futuro_nao_e_reutilizado(tmp_path, monkeypatch):
    _cache(tmp_path, -timedelta(seconds=1))
    monkeypatch.setattr(
        tesouro.requests, "get", lambda *a, **kw: pytest.fail("cache futuro")
    )
    with pytest.raises(ValueError, match="posterior"):
        tesouro.TesouroProvider(tmp_path).baixar(INSTANTE)


def test_snapshot_alterado_depois_do_registro_e_recusado(tmp_path):
    arquivo = _cache(tmp_path)
    prov = proveniencia.registrar_arquivo(arquivo, tesouro.URL, "Tesouro Direto", None)
    arquivo.write_text(CSV.replace("6,84", "8,00"))
    coleta = (INSTANTE - timedelta(hours=2)).timestamp()
    os.utime(arquivo, (coleta, coleta))
    with pytest.raises(ValueError, match="diverge"):
        tesouro.ler_snapshot(tesouro.ArquivoTesouro(arquivo, prov), as_of=INSTANTE)


def test_publicacao_futura_e_recusada_mesmo_com_coleta_anterior(tmp_path):
    from dataclasses import replace

    arquivo = _cache(tmp_path)
    prov = proveniencia.registrar_arquivo(arquivo, tesouro.URL, "Tesouro Direto", None)
    prov = replace(prov, data_entrega="2026-10-20", motivo_sem_entrega=None)
    with pytest.raises(ValueError, match="publicação posterior"):
        tesouro.ler_snapshot(tesouro.ArquivoTesouro(arquivo, prov), as_of=INSTANTE)


def test_taxa_de_resgate_invalida_nao_fica_oculta():
    (titulo,) = tesouro.ler_csv(CSV.replace("6,96", "inf"), as_of=INSTANTE.date())
    assert titulo.taxa_resgate is None
    assert "par de resgate inválido" in titulo.motivo_resgate
    assert titulo.taxa_aplicacao.valor == 0.0684


def test_bom_utf8_preservado_e_base_no_mesmo_dia_ainda_nao_elegivel():
    assert tesouro.ler_csv("\ufeff" + CSV, as_of=date(2026, 10, 15)) == ()
    assert len(tesouro.ler_csv("\ufeff" + CSV, as_of=date(2026, 10, 16))) == 1


def test_familia_fora_do_contrato_nao_interrompe_leitura():
    texto = CABECALHO + "Tesouro Selic;01/03/2027;15/10/2026;0,01;0,02\n"
    texto += CSV.splitlines()[1] + "\n"
    assert len(tesouro.ler_csv(texto, as_of=INSTANTE.date())) == 1


@pytest.mark.parametrize("taxa", ["-inf", "-101"])
def test_taxa_sem_fator_positivo_e_recusada(taxa):
    with pytest.raises(ValueError):
        tesouro.ler_csv(CSV.replace("6,84", taxa), as_of=INSTANTE.date())


def test_disponibilidade_inclui_coleta_exata_com_publicacao_anterior(tmp_path):
    from dataclasses import replace

    arquivo = _cache(tmp_path, timedelta(0))
    prov = proveniencia.registrar_arquivo(arquivo, tesouro.URL, "Tesouro Direto", None)
    prov = replace(prov, data_entrega="2026-10-18", motivo_sem_entrega=None)
    assert (
        len(tesouro.ler_snapshot(tesouro.ArquivoTesouro(arquivo, prov), as_of=INSTANTE))
        == 1
    )


def test_fuso_nao_utc_compara_instantes_e_nao_horarios_locais(tmp_path, monkeypatch):
    from datetime import timezone

    _cache(tmp_path, timedelta(0))
    monkeypatch.setattr(tesouro.requests, "get", _rede_fora)
    local = INSTANTE.astimezone(timezone(timedelta(hours=-3)))
    snapshot = tesouro.TesouroProvider(tmp_path).baixar(local)
    assert snapshot.avisos == ()
    assert len(tesouro.ler_snapshot(snapshot, as_of=local)) == 1


def test_download_cria_diretorio_de_cache_aninhado(tmp_path, monkeypatch):
    class Resposta:
        content = CSV.encode()

        def raise_for_status(self):
            pass

    monkeypatch.setattr(tesouro.requests, "get", lambda *a, **kw: Resposta())
    destino = tmp_path / "data" / "tesouro"
    snapshot = tesouro.TesouroProvider(destino).baixar(INSTANTE)
    assert snapshot.caminho.parent == destino
    assert snapshot.caminho.read_text() == CSV


def test_coleta_na_fracao_futura_do_mesmo_segundo_e_recusada(tmp_path):
    arquivo = _cache(tmp_path, -timedelta(microseconds=500000))
    prov = proveniencia.registrar_arquivo(arquivo, tesouro.URL, "Tesouro Direto", None)
    with pytest.raises(ValueError, match="posterior"):
        tesouro.ler_snapshot(tesouro.ArquivoTesouro(arquivo, prov), as_of=INSTANTE)


@pytest.mark.parametrize(
    "coluna,valor", [("Data Base", ""), ("Data Vencimento", "31/02/2035")]
)
def test_data_ausente_ou_impossivel_e_recusada(coluna, valor):
    campos = CSV.splitlines()[1].split(";")
    campos[CABECALHO.strip().split(";").index(coluna)] = valor
    with pytest.raises(ValueError):
        tesouro.ler_csv(CABECALHO + ";".join(campos), as_of=INSTANTE.date())


@pytest.mark.parametrize("linha", ["Tesouro IPCA+", "Tesouro IPCA+;15/05/2035"])
def test_csv_truncado_rejeita_data_ausente_com_value_error(linha):
    with pytest.raises(ValueError):
        tesouro.ler_csv(CABECALHO + linha + "\n", as_of=INSTANTE.date())


@pytest.mark.parametrize(
    "instante,aceito",
    [
        (datetime(2026, 10, 20, 2, 59, 59, tzinfo=UTC), False),
        (datetime(2026, 10, 20, 3, tzinfo=UTC), True),
    ],
)
def test_publicacao_so_com_data_espera_fim_do_dia_em_sao_paulo(
    tmp_path, instante, aceito
):
    from dataclasses import replace

    arquivo = _cache(tmp_path)
    prov = proveniencia.registrar_arquivo(arquivo, tesouro.URL, "Tesouro Direto", None)
    prov = replace(prov, data_entrega="2026-10-19", motivo_sem_entrega=None)
    snapshot = tesouro.ArquivoTesouro(arquivo, prov)
    if aceito:
        assert len(tesouro.ler_snapshot(snapshot, as_of=instante)) == 1
    else:
        with pytest.raises(ValueError, match="publicação"):
            tesouro.ler_snapshot(snapshot, as_of=instante)


@pytest.mark.parametrize("com_cache", [True, False])
def test_download_preserva_csv_mas_filtra_referencia_futura_local(
    tmp_path, monkeypatch, com_cache
):
    if com_cache:
        _cache(tmp_path, timedelta(days=2))

    class Resposta:
        content = CSV.replace("15/10/2026", "20/10/2026").encode()

        def raise_for_status(self):
            pass

    monkeypatch.setattr(tesouro.requests, "get", lambda *a, **kw: Resposta())
    instante = datetime(2026, 10, 20, 2, tzinfo=UTC)
    snapshot = tesouro.TesouroProvider(tmp_path).baixar(instante)
    assert snapshot.avisos == ()
    assert tesouro.ler_snapshot(snapshot, as_of=instante) == ()
    assert "20/10/2026" in snapshot.caminho.read_text()


@pytest.mark.parametrize("pu", ["NaN", "inf", "-1", "texto", ""])
def test_pu_de_aplicacao_invalido_e_recusado(pu):
    texto = CSV.replace(";100;100\n", f";{pu};100\n")
    with pytest.raises(ValueError):
        tesouro.ler_csv(texto, as_of=INSTANTE.date())


def test_reuso_de_cache_preserva_instante_da_observacao(tmp_path, monkeypatch):
    class Resposta:
        content = CSV.encode()

        def raise_for_status(self):
            pass

    monkeypatch.setattr(tesouro.requests, "get", lambda *a, **k: Resposta())
    p = tesouro.TesouroProvider(tmp_path)
    primeiro = p.baixar(INSTANTE)
    segundo = p.baixar(INSTANTE + timedelta(hours=1))
    assert segundo.proveniencia.data_coleta == primeiro.proveniencia.data_coleta
    assert segundo.caminho.stat().st_mtime == INSTANTE.timestamp()


def test_linha_futura_invalida_nao_contamina_recorte_elegivel():
    texto = CSV + "Tesouro IPCA+;invalido;20/10/2026;NaN;inf\n"
    assert len(tesouro.ler_csv(texto, as_of=date(2026, 10, 19))) == 1
