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
