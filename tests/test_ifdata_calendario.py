"""F2C-37: elegibilidade temporal por evidência fornecida, sem inventar fonte/feed."""

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from sentinela.data.providers import ifdata
from tests.apoio_ifdata_calendario import calendario_sintetico
from tests.test_cvm_bancos import CADASTRO_BB, CAPITAL_BB, _buscar_falso
from tests.test_ifdata_inadimplencia import CARTEIRA_BB

CORTE = date(2026, 10, 13)
INSTANTE = datetime(2026, 10, 13, 12, tzinfo=UTC)


def _ler(calendario, *, corte=CORTE, instante=None):
    buscar, pedidos = _buscar_falso(
        {
            "@AnoMes=202606&$filter=Cnpj": CADASTRO_BB,
            "@AnoMes=202606&@TipoInstituicao=1&@Relatorio='5'": CAPITAL_BB,
            "@AnoMes=202606&@TipoInstituicao=1&@Relatorio='16'": CARTEIRA_BB,
        }
    )
    resultado = ifdata.ler_capital(
        "00.000.000/0001-91", corte, buscar, calendario=calendario, as_of=instante
    )
    return resultado, pedidos


def test_publicacao_anterior_com_prova_preserva_razao_e_proveniencia() -> None:
    cal = calendario_sintetico()
    resultado, pedidos = _ler(cal, instante=INSTANTE)
    assert resultado.inadimplencia == pytest.approx(65383226229.8 / 1115404849436.43)
    assert resultado.proveniencia == (cal.proveniencia.para_dict(),)
    assert resultado.motivos == {}
    assert "@Relatorio='16'" in pedidos[-1]


@pytest.mark.parametrize(
    "publicada",
    [
        date(2026, 10, 13),
        date(2026, 10, 14),
        None,
        datetime(2026, 8, 31, tzinfo=UTC),
        "2026-08-31",
    ],
)
def test_publicacao_nao_admissivel_nao_consulta_carteira(publicada) -> None:
    cal = replace(calendario_sintetico(), publicacoes={"202606": publicada})
    resultado, pedidos = _ler(cal)
    assert resultado.inadimplencia is None
    assert resultado.basileia == pytest.approx(0.151297835513664)
    assert "publicação" in resultado.motivos["inadimplencia"]
    assert not any("@Relatorio='16'" in p for p in pedidos)


@pytest.mark.parametrize(
    "campo,valor,motivo",
    [
        ("fonte", "https://bcb.gov.br.exemplo.invalid/calendario", "fonte oficial"),
        ("fonte", "https://exemplo.invalid/calendario", "fonte oficial"),
        ("documento", "Cadastro", "fonte oficial"),
        ("data_coleta", "2026-09-01T12:00:00", "sem fuso"),
        ("data_coleta", "não é data", "inválida"),
        ("data_coleta", "2026-10-13T12:00:01+00:00", "posterior ao corte"),
        ("data_coleta", "2026-10-14T00:00:00-03:00", "posterior ao corte"),
    ],
)
def test_prova_nao_elegivel_nao_inventa_publicacao(campo, valor, motivo: str) -> None:
    cal = calendario_sintetico()
    cal = replace(cal, proveniencia=replace(cal.proveniencia, **{campo: valor}))
    resultado, pedidos = _ler(cal, instante=INSTANTE)
    assert resultado.inadimplencia is None
    assert motivo in resultado.motivos["inadimplencia"]
    assert not any("@Relatorio='16'" in p for p in pedidos)


def test_asof_efetivo_limita_data_referencia_fornecida() -> None:
    resultado, _ = _ler(
        calendario_sintetico(), instante=datetime(2026, 8, 20, 12, tzinfo=UTC)
    )
    assert resultado.inadimplencia is None
    assert "posterior ao corte" in resultado.motivos["inadimplencia"]


def test_coleta_por_dia_local_e_nao_dia_utc() -> None:
    cal = calendario_sintetico()
    # 01/09UTC ainda31/08Brasília: não prova publicação efetiva de01/09.
    cal = replace(
        cal,
        publicacoes={"202606": date(2026, 9, 1)},
        proveniencia=replace(cal.proveniencia, data_coleta="2026-09-01T01:00:00+00:00"),
    )
    resultado, _ = _ler(cal)
    assert resultado.inadimplencia is None
    assert "coletado antes" in resultado.motivos["inadimplencia"]


def test_coleta_futura_sem_instante_e_recusada_pelo_dia_local() -> None:
    cal = calendario_sintetico()
    cal = replace(
        cal,
        proveniencia=replace(cal.proveniencia, data_coleta="2026-10-14T12:00:00+00:00"),
    )
    resultado, _ = _ler(cal)
    assert resultado.inadimplencia is None
    assert "coleta posterior" in resultado.motivos["inadimplencia"]


def test_fonte_raiz_oficial_e_coleta_no_instante_sao_admissiveis() -> None:
    cal = calendario_sintetico()
    cal = replace(
        cal,
        proveniencia=replace(
            cal.proveniencia,
            fonte="https://bcb.gov.br/calendario-sintetico",
            data_coleta=INSTANTE.isoformat(),
        ),
    )
    resultado, _ = _ler(cal, instante=INSTANTE)
    assert resultado.inadimplencia is not None


def test_provedor_conserva_evidencia_do_calendario_junto_dos_relatorios(
    tmp_path, monkeypatch
) -> None:
    cal = calendario_sintetico()
    p = ifdata.IFDataProvider(str(tmp_path), calendario=cal)
    buscar, _ = _buscar_falso(
        {
            "@AnoMes=202606&$filter=Cnpj": CADASTRO_BB,
            "@AnoMes=202606&@TipoInstituicao=1&@Relatorio='5'": CAPITAL_BB,
            "@AnoMes=202606&@TipoInstituicao=1&@Relatorio='16'": CARTEIRA_BB,
        }
    )
    monkeypatch.setattr(p, "_buscar", lambda caminho, **kw: buscar(caminho))
    monkeypatch.setattr(
        p,
        "_registrar",
        lambda caminho: replace(cal.proveniencia, fonte=f"{ifdata.URL_BASE}/{caminho}"),
    )
    resultado = p.capital("00.000.000/0001-91", CORTE, as_of=INSTANTE)
    assert resultado.inadimplencia == pytest.approx(65383226229.8 / 1115404849436.43)
    assert len(resultado.proveniencia) == 4
    assert resultado.proveniencia[-1] == cal.proveniencia.para_dict()
