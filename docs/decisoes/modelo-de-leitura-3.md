# Modelo de leitura das contas e fonte não demonstrada (F3-P11, F2C-45(ii))

Levantamento de 12/11/2026, feito só com leitura do banco único (DFP de 2010 a 2025) e do índice público `data/referencia/indice.json`, sem rede. A regra continua a mesma:
- a leitura das contas segue pelo setor (`contas_cvm.modelo_do_setor`);
- o escopo, pelo BPP consolidado (`modelo_do_documento`, F2B-4);
- sem modelo do BPP, os métodos de ação se abstêm.

Não há contingência "padrão empresa".

## 1. Os sete tickers divergentes, no histórico

O critério do BPP foi aplicado a cada DFP de 2010 a 2025 (maior versão guardada; a data de entrega de cada mudança está em `docs/decisoes/escopo-saude-beneficios-3.md` §2). "emp" é empresa e "seg" é seguradora.

| Ticker | Setor no índice | Modelo de leitura pelo setor | Modelo do BPP por DFP |
|---|---|---|---|
| CXSE3 | Seguradoras e Corretoras (holding) | seguradora | emp de 2015 a 2025 (as DFPs guardadas) |
| WIZC3 | Seguradoras e Corretoras | seguradora | emp de 2014 a 2025 |
| HAPV3 | Serviços Médicos | empresa | seg de 2017 a 2025 |
| PEAB3, PEAB4 | Holding sem setor principal | empresa | emp de 2010 a 2023; seg em 2024 e 2025 |
| RDOR3 | Serviços Médicos | empresa | emp de 2018 a 2022; seg de 2023 a 2025 |
| SAUD3 | Serviços Médicos | empresa | emp de 2010 a 2019; seg de 2020 a 2025 |

No histórico, as divergências se dividem em dois grupos:
- **CXSE3 e WIZC3 divergem em todos os anos.** A leitura é de seguradora e o escopo é de empresa, então os métodos de ação rodam sobre contas lidas pela tabela de seguradora.
- **PEAB, RDOR3 e SAUD3 só divergem depois da mudança do BPP** (2024, 2023 e 2020). Antes disso, leitura e escopo concordavam (empresa). HAPV3 diverge desde a primeira DFP guardada.

No modo estrito, o modelo documental que existe antes da leitura em D é o do BPP da última DFP entregue antes de D. Para cada um desses tickers, essa data é a de entrega da DFP da mudança.

## 2. Sem modelo demonstrado

Contagem por ano: DFPs com números entregues (`entregas.valores_na_fonte = 1`), DFPs com BPP consolidado guardado, e a diferença, que são as que não têm modelo demonstrado.

| DFP | Com números | Com BPP consolidado | Sem modelo demonstrado |
|---|---:|---:|---:|
| 2010 | 663 | 372 | 291 |
| 2013 | 642 | 345 | 297 |
| 2016 | 616 | 333 | 283 |
| 2019 | 662 | 377 | 285 |
| 2021 | 753 | 452 | 301 |
| 2023 | 721 | 464 | 257 |
| 2025 | 661 | 432 | 229 |

Nos anos fora da tabela, a contagem fica entre 242 e 309.

Entre as DFPs com BPP consolidado, a regra sempre demonstra um modelo:
- banco: 13 a 22 por ano;
- seguradora: 7 a 13 por ano;
- empresa: o restante.

Nenhuma delas cai em "sem par" nem em "conflito". O "não demonstrado" é sempre a falta do consolidado: companhia sem controladas, que só publica a individual. Não medi quantas dessas companhias têm ação negociada. O levantamento da 2C contou 99 tickers do índice de 2025 nessa situação.

## 3. Caminhos para a decisão (nenhum escolhido)

1. **Manter** a leitura pelo setor e o escopo pelo BPP. As divergências da seção 1 seguem como limitação documentada.
2. **Leitura pelo modelo do BPP da última DFP entregue antes de D.** Os mesmos sete casos, mais controles concordantes, teriam regressão própria. A série e o TTM só são comparáveis enquanto o modelo não muda. Na troca (PEAB em 2024, RDOR3 em 2023, SAUD3 em 2020), a janela é cortada, como numa ruptura (`docs/decisoes/reorganizacoes-3.md` §3).
3. **Modelo pelo BPP individual,** quando não houver o consolidado. Exige conferir a tabela de contas da individual, que ainda não foi medida, e ficha própria. Sem ela, a abstenção continua.

Qualquer caminho exige `fix:` com regressão antes da mudança. O caminho 2 muda a leitura de contas dos métodos, o que é caso do §3 da política (método).
