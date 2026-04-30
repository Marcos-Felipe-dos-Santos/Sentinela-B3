import pytest
from fundamentus_scraper import FundamentusScraper

@pytest.fixture
def scraper():
    return FundamentusScraper()

def test_scraper_numeric_parser(scraper):
    assert scraper._limpar_valor("1.234,56") == 1234.56
    assert scraper._limpar_valor("15,2%") == 15.2
    assert scraper._limpar_valor("-") is None
    assert scraper._limpar_valor("3.5") == 3.5
    assert scraper._limpar_valor("12.345.678") == 12345678.0
    assert scraper._limpar_valor("N/A") is None
    assert scraper._limpar_valor("") is None


def test_scraper_divida_liq_ebitda_parser(scraper):
    """O valor '2,34' deve ser parseado como 2.34 pelo limpar_valor."""
    assert scraper._limpar_valor("2,34") == 2.34
    assert scraper._limpar_valor("1.234,56") == 1234.56
    assert scraper._limpar_valor("-0,5") is None or isinstance(scraper._limpar_valor("-0,5"), float)

