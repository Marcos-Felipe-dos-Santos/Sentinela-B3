# Checkpoint da Fase 0 — decisões

**Data:** 2026-10-02
**Quem decidiu:** Marcos, no checkpoint `[DECISÃO]` da Fase 0.
**Entradas:** `docs/adr/0002-loop-tempo-dados.md`, `docs/decisoes/scraper-fundamentus.md` (F0-4), `docs/decisoes/dossie-fase2.md` (F0-6), `docs/limpeza/inventario.md` e `docs/jules-backlog.md`.

Este arquivo é a fonte das decisões abaixo. A proposta da fila da 2A (F1-19) precisa lê-lo.

---

## 1. ADR-0002

D5 a D13 **aceitas**. Com D1–D4, D14 e D15, já aceitas, o ADR-0002 fica com D1 a D15 aceitas.

## 2. Scraper do Fundamentus (F0-4)

- O scraper **sai na Fase 2A**, depois do F2A-1 e do F2A-8.
- O `cloudscraper` **não é declarado** no `requirements.txt`.
- `erro_scraper` vira uma checagem genérica de campos obrigatórios faltando, sem citar o scraper.
- `roic` e `margem_bruta`, se fizerem falta, saem da DFP no F2C-2.

## 3. Itens *investigar* do inventário

| Item | Decisão |
|---|---|
| `buscar_noticias` (`market_engine.py`) | sai no F2A-13 |
| `get_quote` (`brapi_provider.py`) | sai no F2A-13, só depois de confirmar que o preço reserva da brapi passa pelo `get_fundamentals` |
| `reportlab` | sai no F1-13 |
| `openpyxl` | sai no F1-13 |
| `docs/cleanup_report.md` | sai no F1-13 |

## 4. Dossiê da Fase 2

1. **Quantidade de ações.** Usar sempre a Composição do Capital. Divergência acima de 5% com o yfinance vira alerta de qualidade; abstenção só quando a própria CVM falha. LPA = lucro ÷ (ON + PN − tesouraria), e o P/L de cada classe usa o preço da própria classe. O LPA das units é multiplicado pelas ações que cada unit contém.
2. **Taxa de desconto.** Regime real, prêmio-base de 5%, com 4% e 7% como sensibilidade. O prêmio só é fixado no começo da 2B, depois de repetir a coleta da NTN-B com o Tesouro respondendo.
3. **FII.** Comparado com NTN-B + spread, com o spread tirado da mediana histórica. Selic líquida e P/VP entram como contexto.
4. **Janela por método.**

   | Método | Janela |
   |---|---|
   | Bazin | dividendos médios de 5 anos |
   | Graham | LPA médio de 5 anos |
   | Lynch | CAGR de 5 anos |
   | Gordon | dividendo dos últimos 12 meses |

5. **Bancos.** Lente própria com P/VP justificado pelo ROE. Basileia e inadimplência são opcionais; quando faltarem, a limitação é declarada.
6. **Mapa dos FIIs.** Junção do ISIN do COTAHIST com o do Informe Mensal; a regra do ISIN fica como reserva.
7. **Escopo.** Units entram com o ajuste de ações por unit. ETFs e BDRs ficam fora dos métodos, com abstenção e motivo, mas entram na camada de risco.

## 5. E-8 (ticket B4.2 do Jules)

Usar a maior `VERSAO` de cada (CNPJ, `DT_REFER`), sem misturar contas de versões diferentes.

## 6. PR

Um PR por fase.

## 7. Bug novo para o F2A-8

Hoje `divida_liq_ebitda` ausente vira 0,0. Sem o dado, a penalidade de alavancagem se abstém.
