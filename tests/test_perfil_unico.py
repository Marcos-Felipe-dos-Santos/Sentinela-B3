"""Perfil único por ativo pelo DY da relação B3 (F2B-52; decisão do Marcos de 20/10/2026)."""

from apoio_bazin import enriquecer_bazin
from apoio_escopo import de_empresa
from apoio_gordon import AS_OF_GORDON

from valuation_engine import ValuationEngine


def _acao(roe, dy_cascata, dy_b3):
    dados = enriquecer_bazin(
        {
            "ticker": "TST3",
            "preco_atual": 100.0,
            "roe": roe,
            "pl": 10.0,
            "pvp": 1.0,
            "dy": dy_b3,
            "classe_ativo": "STOCK",
        }
    )
    dados["dy"] = dy_cascata
    return de_empresa(dados)


def _processar(dados):
    return ValuationEngine().processar(dados, as_of=AS_OF_GORDON)


def test_caso_beef3_perfil_unico_pelo_dy_da_b3():
    # BEEF3 no universo inicial: ROE de 61,9%, DY da cascata de 2,87%, DY da B3 de 4,51%.
    # Pela B3 o perfil é renda: o Lynch não roda, e o Bazin fica abaixo do gate de 5%.
    r = _processar(_acao(0.619, 0.0287, 0.0451))
    assert r["perfil"] == "RENDA/VALOR"
    assert "Lynch" not in r["metodos_usados"]
    assert "Bazin" not in r["metodos_usados"]


def test_caso_inverso_nao_perde_os_dois_metodos():
    # ROE de 30%, DY da cascata de 5% (renda) e DY da B3 de 3% (crescimento): com um perfil
    # só, o Lynch roda.
    r = _processar(_acao(0.30, 0.05, 0.03))
    assert r["perfil"] == "CRESCIMENTO"
    assert "Lynch: R$" in r["metodos_usados"]


def test_sem_serie_b3_o_perfil_usa_a_cascata_com_aviso():
    dados = _acao(0.30, 0.03, 0.03)
    dados["proventos_b3"] = {"abstencao": "fora do escopo do Bazin: modelo banco"}
    r = _processar(dados)
    assert r["perfil"] == "CRESCIMENTO"
    assert dados["perfil_fonte"] == {
        "fonte": "cascata",
        "aviso": "perfil pelo DY da cascata: fora do escopo do Bazin: modelo banco",
    }
    # o aviso não entra em `riscos`, onde rebaixaria a classificação
    assert not any(a.startswith("perfil pelo DY") for a in r["riscos"])


def test_com_serie_b3_valida_o_perfil_registra_a_fonte():
    dados = _acao(0.30, 0.05, 0.03)
    _processar(dados)
    assert dados["perfil_fonte"]["fonte"] == "relação de proventos da B3"


def test_relatorio_mostra_a_fonte_do_perfil():
    from fii_engine import FIIEngine
    from sentinela.reports import rastreabilidade

    dados = _acao(0.30, 0.03, 0.03)
    dados["proventos_b3"] = {"abstencao": "x"}
    motor = ValuationEngine()
    original = motor.processar
    motor.processar = lambda d: original(d, as_of=AS_OF_GORDON)
    contexto = rastreabilidade.construir_contexto(
        dados, False, AS_OF_GORDON.date(), motor, FIIEngine()
    )
    assert dict(contexto["fontes"])["DY do perfil (F2B-52)"] == (
        "perfil pelo DY da cascata: x"
    )


def test_serie_b3_valida_com_dy_acima_de_25_por_cento_nao_e_crescimento():
    # DY da B3 de 30% não é confiável: o perfil não é crescimento, mesmo com o DY da
    # cascata (1%) confiável e abaixo de 4%.
    dados = _acao(0.30, 0.01, 0.30)
    r = _processar(dados)
    assert r["perfil"] == "RENDA/VALOR"
    assert dados["perfil_fonte"]["fonte"] == "relação de proventos da B3"


def test_relatorio_com_serie_valida_e_sem_perfil():
    from fii_engine import FIIEngine
    from sentinela.reports.rastreabilidade import construir_contexto

    def fonte(dados):
        motor = ValuationEngine()
        original = motor.processar
        motor.processar = lambda d: original(d, as_of=AS_OF_GORDON)
        contexto = construir_contexto(
            dados, False, AS_OF_GORDON.date(), motor, FIIEngine()
        )
        return dict(contexto["fontes"])["DY do perfil (F2B-52)"]

    assert fonte(_acao(0.30, 0.05, 0.03)) == (
        "pela relação de proventos da B3; aviso: proventos de 12 meses podem incluir "
        "distribuição extraordinária, não identificada nesta versão"
    )
    fora = _acao(0.30, 0.05, 0.03)
    fora["classe_ativo"] = "ETF"
    assert fonte(fora) == "não calculado (sem detecção de perfil)"


def test_perfil_fonte_de_analise_anterior_nao_fica():
    dados = _acao(0.30, 0.05, 0.03)
    _processar(dados)
    dados["classe_ativo"] = "ETF"
    _processar(dados)
    assert "perfil_fonte" not in dados


def _motivo_do_bazin(dados, monkeypatch):
    import valuation_engine

    resultados = []
    original = valuation_engine._BAZIN.calcular

    def espiao(inputs, params):
        resultados.append(original(inputs, params))
        return resultados[-1]

    monkeypatch.setattr(valuation_engine._BAZIN, "calcular", espiao)
    r = _processar(dados)
    return r, resultados[-1].motivo


def test_serie_b3_sem_provento_da_perfil_pela_b3(monkeypatch):
    # ROE de 30%, sem provento na janela pela B3 (DY = 0) e DY da cascata de 5% (renda):
    # o perfil é crescimento pela B3; o Bazin testa o perfil antes do DY mínimo e se
    # abstém por "perfil crescimento".
    dados = _acao(0.30, 0.05, 0.0)
    r, motivo = _motivo_do_bazin(dados, monkeypatch)
    assert dados["perfil_fonte"]["fonte"] == "relação de proventos da B3"
    assert r["perfil"] == "CRESCIMENTO"
    assert "Lynch: R$" in r["metodos_usados"]
    assert motivo == "perfil crescimento"


def test_serie_b3_sem_provento_com_roe_baixo_e_renda(monkeypatch):
    # ROE de 12%: com DY = 0 pela B3 o perfil é renda, e o Bazin se abstém pelo DY mínimo.
    dados = _acao(0.12, 0.05, 0.0)
    r, motivo = _motivo_do_bazin(dados, monkeypatch)
    assert dados["perfil_fonte"]["fonte"] == "relação de proventos da B3"
    assert r["perfil"] == "RENDA/VALOR"
    assert motivo == "DY abaixo do mínimo"


def test_especie_sem_registro_na_relacao_cai_no_perfil_da_cascata():
    # A relação só tem a PN; o ticker é ON: a série se abstém e o perfil usa a cascata.
    dados = _acao(0.30, 0.03, 0.0)
    for registro in dados["proventos_b3"]["registros"]:
        registro["typeStock"] = "PN"
    r = _processar(dados)
    assert dados["perfil_fonte"] == {
        "fonte": "cascata",
        "aviso": "perfil pelo DY da cascata: série B3 sem nenhum registro da espécie: ON",
    }
    assert r["perfil"] == "CRESCIMENTO"


AVISO_FIXO = (
    "proventos de 12 meses podem incluir distribuição extraordinária, "
    "não identificada nesta versão"
)


def test_serie_valida_leva_o_aviso_fixo_fora_de_riscos():
    # Ficha Bazin 1.2, §3 (decisão do Marcos de 20/10/2026): com o Bazin calculando, o aviso
    # fixo fica no perfil e no relatório, não em `riscos`.
    dados = _acao(0.12, 0.06, 0.06)
    r = _processar(dados)
    assert "Bazin: R$" in r["metodos_usados"]
    assert AVISO_FIXO in dados["perfil_fonte"]["avisos"]
    assert AVISO_FIXO not in r["riscos"]


def test_avisos_da_serie_aparecem_com_o_bazin_abstendo():
    # Decisão (c) do F2B-54: o Bazin abaixo do gate não mostra a conferência em `riscos`,
    # mas a série que decide o perfil a mostra no perfil.
    dados = _acao(0.12, 0.06, 0.03)
    dados["proventos_b3"]["conferencia_yfinance"] = None
    r = _processar(dados)
    assert "Bazin" not in r["metodos_usados"]
    assert dados["perfil_fonte"]["avisos"] == [
        "conferência dos proventos no yfinance indisponível",
        AVISO_FIXO,
    ]
    assert not any(a in r["riscos"] for a in dados["perfil_fonte"]["avisos"])
