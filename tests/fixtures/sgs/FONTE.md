# Séries do SGS (Banco Central do Brasil) — fixtures do F3-1b

Recortes no formato oficial da API do SGS, baixados sem alteração em 2026-11-10T03:33Z (D18).

| Arquivo | Série | URL | SHA256 |
|---|---|---|---|
| `bcdata_sgs_432.json` | 432, meta Selic (% a.a.), diária, inclui datas futuras até a próxima reunião do Copom | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial=01/01/2025&dataFinal=31/12/2026` | `7339865da1b9c53ef7450309310bda5453356e8fdae2743fade5283eb7149a97` |
| `bcdata_sgs_12.json` | 12, CDI (% a.d.), diária | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json&dataInicial=01/01/2025&dataFinal=31/12/2026` | `b900ef6136236118f2511b9ed90709afa7f21d793625d38fb7aa8e1feae37799` |
| `bcdata_sgs_433.json` | 433, IPCA (% no mês), mensal, data = primeiro dia do mês de referência | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial=01/01/2024&dataFinal=31/12/2026` | `e5c8bd8701c1b69e3dc5f38f627ac02ad9d8904451b4abed5d3e5db30a2f6e53` |

Observado na coleta: séries diárias recusam janela de mais de 10 anos e consulta sem datas (HTTP 406); a 433 aceita consulta sem datas. Primeiras observações: 432 em 05/03/1999, 12 em 06/03/1986.
