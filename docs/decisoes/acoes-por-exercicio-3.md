# Ações por exercício antes de 2020 — levantamento (F3-8k)

**Situação em 16/11/2026:** levantamento, sem código de produção. Até a decisão do Marcos sobre a ligação, vale a regra do F2A-3: sem as ações do mesmo documento do lucro, Graham e Lynch abstêm. Pedido pela DD-72 e pela decisão 3 do Marcos (15/11/2026). Não é recomendação nem sugestão de carteira.

Saídas, fora do git: `outputs/f3-8k/` (`cobertura_banco.txt`, `levantamento.py` e `levantamento.txt`, `levantamento_sem_pit.txt`, `versoes.txt`; os ZIPs do FRE de 2010 a 2021 em `outputs/f3-8k/fre/`, com `sha256.txt` e `coleta.txt`).

## 1. O que os dados PIT guardados trazem (banco real, só leitura)

| Exercício | Companhias com DFP | Com Composição do Capital | Com BPP consolidado | Com a linha de LPA da DRE (3.99) |
|---|---|---|---|---|
| 2010 | 663 | 0 | 372 | 663 |
| 2013 | 650 | 0 | 352 | 649 |
| 2016 | 625 | 0 | 340 | 625 |
| 2019 | 670 | 0 | 385 | 669 |
| 2020 | 731 | 731 | 442 | 731 |
| 2023 | 732 | 732 | 474 | 732 |
| 2025 | 671 | 670 | 442 | 671 |

(Todos os anos em `outputs/f3-8k/cobertura_banco.txt`.)

- **Composição do Capital:** nenhuma companhia de 2010 a 2019, cobertura total de 2020 em diante. A ausência é da fonte: o ZIP oficial `dfp_cia_aberta_2019.zip` da CVM não tem o arquivo `composicao_capital`, e o de 2020 tem (conferido nos ZIPs guardados em `data/fontes/backfill/dfp/`). É por isso que Graham e Lynch abstêm em toda janela que inclui um exercício anterior a 2020.
- **BPP consolidado:** de 53% a 66% das companhias com DFP por ano. As demais só publicam o BPP individual, e o escopo exige o consolidado (F2B-4), o que explica "modelo da demonstração não demonstrado no BPP consolidado" em 2024 e 2025.
- **Linha de LPA da DRE (conta 3.99):** em praticamente toda DFP desde 2010. Ela dá o LPA divulgado por classe, mas não a quantidade de ações; tirar a quantidade dela (lucro ÷ LPA) seria regra nova, fora deste levantamento.

## 2. Fonte 1: Formulário de Referência (FRE) da CVM

- **Arquivos:** dados abertos `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FRE/DADOS/fre_cia_aberta_{ano}.zip`, de 6 a 10 MB por ano; os 12 anos de 2010 a 2021 somam 95 MB (medido com HEAD antes do download; 722 GB livres). Coleta em 16/11/2026, hashes em `outputs/f3-8k/fre/sha256.txt`.
- **O dado:** a seção `informacao_financeira` (item 3.1 do FRE) traz, por exercício social, a conta **f, "Número de Ações, Ex-Tesouraria"**, além de PL, resultado líquido (e) e resultado líquido por ação (h). A seção `capital_social` traz o capital emitido, subscrito e integralizado com as ações ON e PN na data da aprovação, sem a tesouraria; os eventos de desdobramento, grupamento, aumento e redução estão em seções próprias.
- **Ponto no tempo:** o arquivo principal tem `DT_RECEB` por versão, mas as seções detalhadas dos dados abertos trazem **só a última versão** de cada FRE (em 2012, 583 de 583 companhias; em 2015, 543 de 543; em 2019, 522 de 522; `versoes.txt`). O exercício X aparece, em geral, a partir do FRE do ano X+1, cuja última versão é entregue por volta de maio de X+2: atraso da primeira entrega disponível de 11, 16 e 16,3 meses depois do fim do exercício (quartis). Para os exercícios antigos da janela de cinco anos, usados em datas bem posteriores, esse atraso não pesa; para o último exercício, a DFP de 2020 em diante já tem a Composição do Capital.
- **Cobertura da conta f com entrega até 30/06 de dois anos depois do exercício**, entre as companhias com DFP no ano:

| Exercício | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Com DFP | 663 | 679 | 662 | 650 | 652 | 633 | 625 | 632 | 630 | 670 | 731 |
| Com a conta f | 485 | 515 | 515 | 489 | 485 | 442 | 451 | 459 | 388 | 487 | 547 |

- **Conferência com a Composição do Capital da DFP de 2020** (ações totais menos tesouraria, mesmo CNPJ e exercício), 539 pares: 305 iguais (±0,1%); 162 na razão de 1000, a escala em mil da DFP (armadilha 10); 20 a menos de 5%; 18 perto de 1000 (±5%); cerca de 34 divergentes. Em 2021 só há 64 pares, porque o FRE de 2022 não foi baixado.

## 3. Fonte 2: a linha de LPA da DRE

- **Cobertura:** a conta 3.99 está em praticamente toda DFP desde 2010 (seção 1); a 3.99.01.01 (LPA básico ON) em 554 DFPs de 2013, 555 de 2016 e 596 de 2019.
- **Conferência com o FRE (conta h, resultado líquido por ação):** só cerca de 25% dos pares batem a ±0,01 (98 de 457 em 2013, 115 de 403 em 2016, 118 de 439 em 2019). A conta h do FRE é o resultado por ação total da companhia, não o LPA básico por classe da DRE; as duas não medem a mesma coisa, e essa conferência não valida nenhuma das fontes.
- A linha de LPA dá o LPA divulgado, que os métodos já usam (D19). Para a quantidade de ações ela só serviria por divisão (lucro dos controladores ÷ LPA), que é regra nova e fica para a decisão do Marcos.

## 4. Proposta para a decisão do Marcos (sem efeito até lá)

1. **Fonte:** a conta f do FRE ("Número de Ações, Ex-Tesouraria") para os exercícios de 2010 a 2019, só fonte oficial.
2. **Disponibilidade:** pela `DT_RECEB` da versão publicada nos dados abertos (a última), antes do dia de D; sem versão entregue até D, abstém. Como só a última versão é publicada, essa data pode ser posterior à da primeira entrega real (mais abstenção, nunca dado do futuro). A tabela da §2 usa o corte de 30/06 de dois anos depois só para medir a cobertura; a regra final fica com um corte só, o do dia de D.
3. **Escala e conferência:** a mesma inferência pelo LPA divulgado da DRE do mesmo exercício (armadilha 10, faixa [0,1; 10]); sem escala demonstrada, abstém.
4. **O ponto de regra:** o F2A-3 exige as ações **do mesmo documento do lucro**, e o FRE é outro documento. Ligar o FRE é mudar essa regra, e a decisão é do Marcos; até lá, abstém.
5. **Ligação:** item seguinte, com a regra escrita, teste vermelho antes e a sonda mostrando quantas janelas de Graham e Lynch passam a ter valor.
