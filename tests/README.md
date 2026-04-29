# 🧪 Sentinela B3 Test Suite

This folder contains the automated test suite for the **Sentinela B3** platform.

The tests are designed to validate core financial logic and ensure the robustness of the system against edge cases (like missing data, malformed inputs, or API failures) without making real network requests or relying on the internet.

## 🎯 What is Tested?

- **Valuation Engine (`test_valuation_engine.py`)**: Checks boundary handling, safe parsing of malformed numeric data (e.g. debt formats), and verifies no logic crashes during recommendations.
- **FII Engine (`test_fii_engine.py`)**: Validates missing optional data handling and expected output structures.
- **Technical Engine (`test_technical_engine.py`)**: Tests indicator logic (RSI, MA) with varying lengths of price history.
- **Portfolio Engine (`test_portfolio_engine.py`)**: Validates the Markowitz optimization against edge cases like empty portfolios or NaN data handling.
- **Scraper (`test_fundamentus_scraper.py`)**: Ensures robust numeric formatting specific to Brazilian numbers (e.g., `1.234,56` -> `1234.56`).
- **Database (`test_database.py`)**: Checks DB initialization and state management using isolated temporary environments.
- **AI Core (`test_ai_core.py`)**: Verifies the fallback chain (Groq -> Gemini -> Ollama) by mocking clients.

## 🚀 How to Run

To execute the test suite, ensure you have the required testing dependencies installed (`pytest` and `pytest-cov`), then run:

```bash
python -m pytest
```

To run with coverage, use:

```bash
python -m pytest --cov=.
```
