> Editado só para remover caminhos locais do autor (23/11/2026).

# Levantamento de Cobertura de Dados Históricos — Fase 4

> **Data:** 21/11/2026
> **Executor:** gemini (Antigravity)
> **Modo:** somente leitura (`file:sentinela_store.db?mode=ro`, `PRAGMA query_only=ON`, sem consulta a `carteira_real`, `analises` ou `.env`).
> **Branch e commit-base:** `main` @ `c06899c`

---

## Passo 0 — Teste do Terminal

Script executado (`outputs/levantamento/passo0.py`):

```text
main
3.13.15 (main, Sep 29 2026, 15:01:28) [Clang 22.1.3 ]
(116,)
```

---

## Linha de Base da Sonda Final da Fase 3 (`outputs/c3-sonda/`)

- **Evidência factual:** [observacoes.json](/outputs/c3-sonda/sonda/observacoes.json) e [analise.txt](/outputs/c3-sonda/analise.txt).
- **Datas de análise ($D$):** `2018-06-29`, `2019-06-28`, `2020-06-30`, `2021-06-30`, `2022-06-30`, `2023-06-30`, `2024-06-28`, `2025-06-30` (8 datas anuais).
- **Horizontes:** 12m (8 datas), 24m (7 datas, `2018` a `2024`), 36m (6 datas, `2018` a `2023`).
- **Volume total de observações:** **15.292** (`5.976` em 12m, `5.101` em 24m, `4.215` em 36m), além de 12 registros `sem_lentes` (FIIs sem cotação de fechamento anterior em $D$). Em 12m, o universo é composto por `1.016` pares ativo-data de ações/units (`1.016 × 5 = 5.080` observações nas lentes `Gordon`, `Bazin`, `Graham`, `Lynch`, `Bancos`) e `896` pares ativo-data de FIIs (`896 × 1 = 896` observações na lente `Rendimento do FII`).
- **Observações com valor numérico e retorno total hoje na sonda final (`analise.txt:7-28`):**
  - `Gordon`: **194** com valor (**135** com retorno) em 12m; **165** (**114** c/ ret) em 24m; **142** (**100** c/ ret) em 36m.
  - `Bazin`: **206** com valor (**205** com retorno) em 12m; **180** (**179** c/ ret) em 24m; **142** (**142** c/ ret) em 36m.
  - `Graham`: **43** com valor (**21** com retorno) em 12m (todos em `2025-06-30`); **0** em 24m; **0** em 36m.
  - `Lynch`: **1** com valor (**1** com retorno) em 12m (em `2025-06-30`); **0** em 24m; **0** em 36m.
  - `Bancos`: **7** com valor (**4** com retorno) em 12m; **4** (**2** c/ ret) em 24m; **3** (**1** c/ ret) em 36m.
  - `Rendimento do FII`: **0** com valor em 12m, 24m e 36m.

---

## L1. Ações em circulação antes de 2020 (Graham, Lynch) — Conta `f` do FRE (`outputs/f3-8k/fre/`)

### FATO (com evidência)
1. **Existência e estrutura da fonte:** Os pacotes anuais do Formulário de Referência da CVM (`https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FRE/DADOS/fre_cia_aberta_{ano}.zip`) de **2010 a 2021** já estão baixados em `outputs/f3-8k/fre/` (coletados em `2026-11-16T17:51:58Z`, conforme [coleta.txt](/outputs/f3-8k/fre/coleta.txt) e hashes em [sha256.txt](/outputs/f3-8k/fre/sha256.txt)).
2. **Conta e data de publicação:** Dentro de cada ZIP, o CSV `fre_cia_aberta_informacao_financeira_{ano}.csv` (item 3.1 do FRE) traz `Codigo_Conta == 'f'` (`"Número de Ações, Ex-Tesouraria"`) indexado por `(CNPJ_Companhia, Data_Referencia, Versao, Data_Fim_Exercicio_Social)`. A data oficial de recebimento (`DT_RECEB`) consta no arquivo de índice `fre_cia_aberta_{ano}.csv`, associada por `(CNPJ_CIA, DT_REFER, VERSAO)` ([levantamento.py](/outputs/f3-8k/levantamento.py#L9-L36) e [acoes-por-exercicio-3.md](/docs/decisoes/acoes-por-exercicio-3.md#L16-L31)).
3. **Limitação da fonte aberta (última versão):** Conforme medido em [versoes.txt](/outputs/f3-8k/versoes.txt#L1-L27), o portal de Dados Abertos da CVM preserva apenas **1 versão por `(CNPJ_CIA, DT_REFER)`** do FRE (a última reapresentação: `583/583` em 2012, `543/543` em 2015, `522/522` em 2019). Os quartis de atraso entre `Data_Fim_Exercicio_Social` e o primeiro `DT_RECEB` disponível nos ZIPs abertos são **`11,0 / 16,0 / 16,3` meses** ([levantamento.txt](/outputs/f3-8k/levantamento.txt#L38-L39)). Isso significa que a conta `f` do exercício $Y-1$ frequentemente só aparece numa versão do FRE cujo `DT_RECEB` é posterior a junho do ano $Y$ (mas anterior a junho de $Y+1$).
4. **Conferência de escala (`f` vs. DFP 2020 e `f` vs. LPA da DRE):**
   - No exercício de 2020 (onde DFP `composicao_capital` e FRE `f` coexistem para 539 companhias, [levantamento.txt](/outputs/f3-8k/levantamento.txt#L13-L18)), **305** batem 1:1 ($\pm 0,1\%$), **162** diferem por fator 1.000 (escala em mil ações), **38** ficam dentro de $\pm 5\%$ (1 ou 1.000) e **34** divergem mais de $5\%$.
   - Na simulação ponto-no-tempo sobre todos os exercícios $< 2020$ das companhias da sonda (`outputs/levantamento/complemento_l1_l4_l6.py`), a conferência `Lucro / ações_FRE` contra o LPA básico divulgado na DRE (`3.99`, via `acoes_cvm.inferir_escala` na faixa `[0,1; 10]`) demonstrou a escala em **1.561** exercícios-ativo, absteve **288** por `"escala das ações indeterminada"`, **258** por `"sem Composição do Capital na DFP nem conta f no FRE entregue até D"`, **232** em que a própria DFP do exercício não tinha números no corte PIT ou não tinha linha no FRE, e **5** por `"unit sem composição oficial"`.
5. **Simulação exata na sonda (`outputs/c3-sonda/sonda/observacoes.json`):**
   - Na sonda atual, `Graham` e `Lynch` têm **722** abstenções em 12m (`2018: 62, 2019: 71, 2020: 105, 2021: 90, 2022: 132, 2023: 139, 2024: 123`), **722** em 24m e **599** em 36m com motivo `"ações do exercício <2013..2019>: sem Composição do Capital no documento do lucro"` (além de 7 em 2025 para o exercício 2020).
   - **Ganho medido com corte estrito `DT_RECEB < D` e conferência pelo LPA da DRE (`complemento_l1_l4_l6.py`):**
     - **Lente `Graham` (só L1, com IPCA atual do banco $\ge$ 12/2016):**
       - **12m:** **+124** observações passam de abstenção para valor numérico (**+55** com `retorno_total`), distribuídas em: `2021-06-30`: **+22** (9 c/ ret); `2022-06-30`: **+31** (10 c/ ret); `2023-06-30`: **+32** (13 c/ ret); `2024-06-28`: **+39** (23 c/ ret). *(Eleva Graham 12m de 43 para **167** valores, e de 21 para **76** com retorno; destrava quintis $\ge 25$ em 2022, 2023 e 2024, somando-se a 2025).*
       - **24m:** **+124** observações com valor (**+54** com `retorno_total`), nas mesmas datas `2021` a `2024` (de 0 para **124** valores).
       - **36m:** **+85** observações com valor (**+31** com `retorno_total`), em `2021` (+22), `2022` (+31) e `2023` (+32) (de 0 para **85** valores).
       - **Total `Graham` (3 horizontes, só L1):** **+333** observações com valor (**+140** com retorno).
     - **Lente `Graham` (L1 combinado com L5 — IPCA pré-12/2016 via `DD-39`):**
       - Acrescenta `2018-06-29` (**+1** valor) e `2019-06-28` (**+1** valor); em `2018` a `2020`, a maior parte dos ativos continua abstendo porque o FRE que traz a conta `f` do último exercício ($D-1$: 2017 em 2018, 2018 em 2019, 2019 em 2020) teve sua última versão reapresentada após junho de $D$ (`43` ativos em 2018, `46` em 2019, `52` em 2020).
     - **Lente `Lynch` (só L1):**
       - **12m:** **+1** observação com valor (**+1** com retorno, em `2022-06-30`).
       - **24m:** **+1** observação com valor (**+1** com retorno, em `2022-06-30`).
       - **36m:** **+1** observação com valor (**+1** com retorno, em `2022-06-30`).
       - **Total `Lynch` (3 horizontes):** **+3** observações com valor (**+3** com retorno).
       - *Por que Lynch destrava apenas +1 por horizonte enquanto Graham destrava +124/+124/+85?* Conforme medido nos motivos residuais de `complemento_l1_l4_l6.py`, após destravar a série de 5 anos de LPA com o FRE, Lynch exige: (i) `DY comum` válido em `proventos_b3` para classificar o perfil da companhia (bloqueia **75** ativos em 12m entre 2021 e 2024 com `"perfil não demonstrado: DY comum ausente ou não confiável"` — ou seja, depende diretamente de **L3/L6**!), (ii) extremos positivos (`LPA_0 > 0` e `LPA_4 > 0`) e (iii) `crescimento_lpa >= 10%` (ou $\ge 15\%$ para cíclicas/crescimento).

### HIPÓTESE
- Se **L3** e **L6** (busca por `cd_cvm`) forem aplicadas em conjunto com **L1**, parte das **75** observações de `Lynch` em 12m (2021–2024) que já têm os 5 exercícios de LPA destravados pelo FRE, mas param em `"perfil não demonstrado: DY comum ausente ou não confiável"`, também passará a produzir valor numérico em `Lynch`, e parte das **69** observações de `Graham` em 12m que já ganharam valor (+124 val vs +55 c/ ret) também ganhará `retorno_total`.

### Respostas (a–e)
- **a) Fonte oficial:** Sim. CVM — Formulário de Referência (`fre_cia_aberta_{ano}.zip`, arquivo `fre_cia_aberta_informacao_financeira_{ano}.csv`, `Codigo_Conta = 'f'`), disponível desde **2010**, com data de publicação (`DT_RECEB`) no índice `fre_cia_aberta_{ano}.csv`.
- **b) Custo:** **0 MB** de download novo (os 12 ZIPs de 2010 a 2021 somam **95 MB** e já estão em `outputs/f3-8k/fre/`). Tempo de leitura/parse: **~1,0 s**. Esforço de código estimado: **baixo a médio** (~80–120 linhas em `cvm_provider.py` / `sentinela/data/acoes_cvm.py` + testes unitários e de mutação, já mapeado como item `F4-H04` em [fila-fase4-proposta.md](/docs/loop/fila-fase4-proposta.md#L64-L74)).
- **c) Ganho na sonda final:**
  - `Graham`: **+124** em 12m (+55 c/ retorno), **+124** em 24m (+54 c/ retorno), **+85** em 36m (+31 c/ retorno) = **+333** observações com valor (**+140** com retorno).
  - `Lynch`: **+1** em 12m (+1 c/ retorno), **+1** em 24m (+1 c/ retorno), **+1** em 36m (+1 c/ retorno) = **+3** observações com valor (**+3** com retorno) isoladamente (com mais **75** ativos em 12m destravados até a etapa do DY do perfil, dependentes de L3/L6).
  - **Total L1:** **+336** observações de lente passam de abstenção para número (**+143** com retorno total).
- **d) Exige mudança de regra ou ficha?** **Sim (decisão do Marcos).** As fichas [por-acao.md](/docs/metodologia/por-acao.md) (§1, §3, §4.1), [graham.md](/docs/metodologia/graham.md) e [lynch.md](/docs/metodologia/lynch.md) exigem que a quantidade de ações venha do **mesmo documento** do lucro (mesmo CNPJ, `DT_REFER` e `VERSAO` da DFP). A opção descrita em [acoes-por-exercicio-3.md](/docs/decisoes/acoes-por-exercicio-3.md#L97-L115) e em `F4-H04` consiste em autorizar, para exercícios de 2010 a 2019 sem `composicao_capital` na DFP, a conta `f` do FRE da mesma companhia para o mesmo `Data_Fim_Exercicio_Social`, com `DT_RECEB < D` e escala validada pelo LPA divulgado na DRE (`3.99`) na razão `[0,1; 10]`.
- **e) Riscos:**
  - *Vazamento de futuro:* Como a CVM guarda apenas a última versão de cada FRE, o filtro estrito `DT_RECEB < D` impede vazamento de futuro, mas sacrifica cobertura no exercício imediatamente anterior a $D$ quando houve reapresentação posterior do FRE (`2018` a `2020`). Usar a conta `f` sem filtrar `DT_RECEB < D` vazaria versões reenviadas anos depois.
  - *Escala:* 30% das linhas (162/539 em 2020) estão em mil ações; usar `f` sem a inferência de escala contra o LPA divulgado da DRE multiplicaria o LPA e o VPA por 1.000.
  - *Identidade / espécie:* A conta `f` traz apenas o total ex-tesouraria (`ON + PN`), não separado por espécie. Funciona para a conferência de escala, VPA e `fatores_da_base` (que usam `composicao.total`), mas não substitui a proporção `ON/PN` quando a DRE não divulga LPA por espécie em companhias com múltiplas classes.

---

## L2. FII no histórico — Detectar emissões pelo Informe Mensal da CVM (`Cotas_Emitidas`), sem o complemento da B3

### FATO (com evidência)
1. **Existência e cobertura da fonte no banco:** O Informe Mensal de FII da CVM (`https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{ano}.zip`, disponível desde **01/2016**) já está carregado na tabela `fii_informe_linhas` de `sentinela_store.db` para `1.743` CNPJs, cobrindo competências de `2016-09-01` a `2026-10-01`, com data de entrega (`Data_Entrega` na seção `geral`) e os campos `Cotas_Emitidas`, `Valor_Patrimonial_Cotas` e `Percentual_Dividend_Yield_Mes` na seção `complemento`.
2. **Onde e por que os FIIs param hoje na sonda:**
   - Na sonda final, a lente `Rendimento do FII` tem **0/896** valores em 12m (**0/746** em 24m, **0/590** em 36m).
   - Em `MotorHistorico._buscar_rendimento_fii` ([historico.py](/sentinela/services/historico.py#L283-L300)), o complemento da B3 (`b3_fundo` / `GetListedSupplementFunds`) é desabilitado no histórico (`MOTIVO_FONTE_CORRENTE`) porque não tem data de publicação histórica.
   - Em `rendimento_fii.avaliar` ([rendimento_fii.py](/sentinela/data/rendimento_fii.py#L317-L357)), a guarda `if not fii_elegibilidade.resposta_b3_valida(b3, codigo): return Abstencao(MOTIVO_EVENTOS_INDISPONIVEIS)` (linha 336) é verificada **depois** de todas as guardas do Informe Mensal (13 competências contíguas entregues até $D$, `VP > 0`, `Cotas_Emitidas > 0`, `DY >= 0`, `amortizacao == 0`, `tipo == "tijolo"`). Além disso, as linhas 349–357 de `rendimento_fii.py` **já detectam emissões mês a mês pelo próprio Informe** (`if cota_atual != cota_anterior: emissoes.append(competencia)`).
   - Exatamente **307** observações em 12m (**266** em 24m, **224** em 36m) chegam à linha 336 tendo passado em todas as guardas anteriores e são barradas exclusivamente por `"fonte de eventos de cota indisponível: continuidade não demonstrável"`.
3. **Medição exata das 307 (12m) / 266 (24m) / 224 (36m) observações pelo comportamento de `Cotas_Emitidas` e `Valor_Patrimonial_Cotas` nos 13 meses (`outputs/levantamento/medir_l2_fast.py`):**
   - **Todas as 307 (12m) / 266 (24m) / 224 (36m)** observações também passam nas guardas posteriores de `rendimento_fii.avaliar` (`rendimento_12m > 0`, `dy <= 0.25` e `ntnb_ate` disponível em `series_macro`)!
   - Decomposição das 307 (12m) / 266 (24m) / 224 (36m) observações:
     1. **`Cotas_Emitidas` estritamente constante nos 13 meses (zero emissões e zero desdobramentos/grupamentos na janela):**
        - **12m:** **192** observações (`2018: 15, 2019: 24, 2020: 18, 2021: 15, 2022: 35, 2023: 33, 2024: 24, 2025: 28`).
        - **24m:** **164** observações (`2018: 15, 2019: 24, 2020: 18, 2021: 15, 2022: 35, 2023: 33, 2024: 24`).
        - **36m:** **140** observações (`2018: 15, 2019: 24, 2020: 18, 2021: 15, 2022: 35, 2023: 33`).
        - **Subtotal (1):** **496** observações nos 3 horizontes.
     2. **`Cotas_Emitidas` variou (emissão de cotas), mas o `Valor_Patrimonial_Cotas` manteve continuidade ($|\Delta \text{VP}| \le 25\%$ mês a mês, sem salto inverso de split/inplit):**
        - **12m:** **109** observações (`2018: 1, 2019: 9, 2020: 18, 2021: 25, 2022: 14, 2023: 12, 2024: 17, 2025: 13`).
        - **24m:** **96** observações.
        - **36m:** **79** observações.
        - **Subtotal (2):** **284** observações nos 3 horizontes.
     3. **`Cotas_Emitidas` variou com salto inverso de `VP` ($|\Delta \text{VP}| > 25\%$, assinatura direta de desdobramento/grupamento ou reestruturação):**
        - Apenas **6** observações em 12m (**6** em 24m, **5** em 36m), todas corretamente identificadas pelo par `(Cotas_Emitidas, VP)` do próprio Informe:
          - `FFCI11` (`2018-06-29`): `2017-06 -> 2017-07` razão de cotas `0,01`, razão de VP `99,8065`, produto `0,9981` (grupamento 100:1).
          - `RBVA11` (`2020-06-30`): `2019-05 -> 2019-06` razão de cotas `10,0`, razão de VP `0,1001`, produto `1,0012` (desdobramento 1:10).
          - `FLMA11` (`2021-06-30`): `2021-04 -> 2021-05` razão de cotas `0,02`, razão de VP `49,9942`, produto `0,9999` (grupamento 50:1).
          - `VINO11` (`2024-06-28`): `2023-07 -> 2023-08` razão de cotas `5,0`, razão de VP `0,1997`, produto `0,9985` (desdobramento 1:5).
          - `BRCO11` (`2020-06-30`) e `MFII11` (`2020-06-30`): saltos de VP $> 25\%$ com emissão.

### HIPÓTESE
- A combinação de `Cotas_Emitidas` e `Valor_Patrimonial_Cotas` nos 13 meses do Informe Mensal (rejeitando variações de `VP` fora de uma banda como `(0,75; 1,25)` ou `(0,90; 1,10)` quando `Cotas_Emitidas` muda), somada à continuidade de preço no COTAHIST entre a última competência do Informe e $D$, é suficiente para detectar desdobramentos/grupamentos sem depender do endpoint corrente `GetListedSupplementFunds` da B3.

### Respostas (a–e)
- **a) Fonte oficial:** Sim. CVM — Informe Mensal de FII (`inf_mensal_fii_complemento_{ano}.csv`, campos `Cotas_Emitidas` e `Valor_Patrimonial_Cotas`), desde **01/2016**, com data de entrega oficial em `inf_mensal_fii_geral_{ano}.csv` (`Data_Entrega`), já integralmente no banco (`fii_informe_linhas`).
- **b) Custo:** **0 MB** de download, **0 s** de coleta (dados já no SQLite). Esforço de código estimado: **baixo** (~30–50 linhas em `sentinela/data/rendimento_fii.py` e `fii_elegibilidade.py` + testes).
- **c) Ganho na sonda final (lente `Rendimento do FII`):**
  - *Opção conservadora (aceitar no histórico apenas quando `Cotas_Emitidas` é constante nos 13 meses):* **+192** em 12m, **+164** em 24m, **+140** em 36m = **+496** observações com valor numérico.
  - *Opção completa da ficha (aceitar `Cotas_Emitidas` constante ou emissão com VP contínuo, conforme §3a de `fii.md`):* **+301** em 12m (`2018: 16, 2019: 33, 2020: 36, 2021: 40, 2022: 49, 2023: 45, 2024: 41, 2025: 41`, destravando quintis $\ge 25$ em **7 das 8 datas**!), **+260** em 24m, **+219** em 36m = **+780** observações de lente passando de abstenção para número!
  - *(Nota sobre o retorno de FII:* na sonda atual, todas as 896 observações de FII em 12m têm `abstencao_retorno = "sem coleta da relação de proventos do emissor"` porque `BacktestPIT._retornos` consulta a tabela `proventos` de companhias; o cálculo do retorno total do FII pelo Informe Mensal ou B3 é o item `F4-H14` da proposta da Fase 4).*
- **d) Exige mudança de regra ou ficha?** **Sim (decisão do Marcos).** A ficha [fii.md](/docs/metodologia/fii.md#L127-L162) (§3a) já define que emissão de cotas (`Cotas_Emitidas` crescente com VP contínuo) é aceita com aviso de contexto e que apenas desdobramento/grupamento ou salto incompatível de VP abstém. Porém, a operacionalização em §3a e `F2C-47` exigiu a resposta ao vivo da B3 (`stockDividends`). A opção para decisão do Marcos é: no modo histórico (`as_of < hoje`, onde `b3_fundo` não tem publicação datada), permitir comprovar a ausência de split/inplit pela compatibilidade conjunta de `Cotas_Emitidas` e `Valor_Patrimonial_Cotas` nos 13 meses do Informe Mensal (mais ausência de salto de split no COTAHIST até $D$).
- **e) Riscos:**
  - *Escala / diluição no mês da emissão:* Conforme documentado em [rendimentos-fii-retorno-3.md](/docs/decisoes/rendimentos-fii-retorno-3.md#L69-L90), no mês em que novas cotas são emitidas, o `DY_m` do Informe divide o caixa distribuído pelo total final de cotas (`Cotas_Emitidas`), subestimando o rendimento por cota antiga naquele mês quando as cotas novas não recebem rendimento integral (ex.: HGLG11 em 11/2025 e 04/2026). Nas **192** observações (12m) com `Cotas_Emitidas` constante, esse risco é zero.
  - *Defasagem entre último Informe e $D$:* Se um split ocorrer após a última competência entregue do Informe (defasagem de até 3 meses) e antes de $D$, ele não estará nos 13 Informes, exigindo checar também saltos de preço no COTAHIST entre a última competência e $D$.

---

## L3. Identidade dos proventos — Retornos sem identidade na sonda final, agrupados por causa

### FATO (com evidência)
1. **Contagem exata na sonda (`outputs/levantamento/medir_l3.py` e `medir_l3_detalhe.py`):**
   - As abstenções de **retorno** (`abstencao_retorno` começando por `"identidade do emissor não comprovada na coleta"`) somam exatamente:
     - **12m:** **1.845** observações (`369` pares ativo-data em `93` tickers distintos; **79** observações já têm valor numérico na lente: `57 Gordon`, `17 Graham`, `5 Bancos`).
     - **24m:** **1.565** observações (`313` pares ativo-data; **50** já têm valor numérico na lente: `48 Gordon`, `2 Bancos`).
     - **36m:** **1.280** observações (`256` pares ativo-data; **37** já têm valor numérico na lente: `36 Gordon`, `1 Bancos`).
     - **Total nos 3 horizontes (retorno):** **4.690** observações (**166** já com valor numérico na lente).
   - Além do retorno, a mesma falha de identidade em `b3_proventos.relacao_ate` / `proventos_b3.conferir_emissor` abstém as próprias **lentes** (`abstencao`):
     - `Bazin`: **310** observações em 12m, **263** em 24m, **216** em 36m (**789** nos 3 horizontes).
     - `Graham`: **16** observações em 12m (todas em `2025-06-30`, onde o fator de eventos B3 precisou da relação de proventos).
     - `Lynch`: **16** observações em 12m (em `2025-06-30`).
2. **Decomposição exata por causa (100% das 1.845 / 1.565 / 1.280 abstenções de retorno e das 310 / 263 / 216 abstenções da lente Bazin):**

| Causa raiz (mecanismo no código e na fonte B3) | Retorno 12m (c/ valor lente) | Retorno 24m (c/ valor lente) | Retorno 36m (c/ valor lente) | Total Retorno 3 horiz. | Bazin abstido (12m / 24m / 36m) | Ganho real em Bazin se destravada (12m / 24m / 36m) | Tickers afetados em 12m |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **C1. Complemento vazio** (`"complemento sem proventos para conferir"`, regra 33(c) em `proventos_b3.py:216`): `GetListedSupplementCompany` só traz dividendos recentes; cias sem dividendo recente têm `dinheiro_complemento = []` e falham na regra 33(c) mesmo com ISINs válidos no `GetDetail`. | **680** (14: 11 Gor, 3 Gra) | **565** (10 Gor) | **455** (8 Gor) | **1.700** (32 c/ val) | 118 / 97 / 77 | **+13 / +11 / +8** (+32 total) | 45 tickers (`AALR3`, `AMER3`, `ANIM3`, `AZUL4`, `BEEF3`, `BPAC11`, `BRKM3/5`, `BRPR3`, `CAML3`, `CBAV3`, `CSNA3`, `CVCB3`, `ECOR3`, `ENEV3`, `EVEN3`, `FHER3`, `GFSA3`, `HAPV3`, `HBOR3`, `HBRE3`, `HBSA3`, `LOGG3`, `LOGN3`, `LPSB3`, `LUPA3`, `LWSA3`, `MDNE3`, `MEAL3`, `MILS3`, `MRFG3`, `MRVE3`, `MTRE3`, `NATU3`, `ONCO3`, `OPCT3`, `ORVR3`, `PDGR3`, `PMAM3`, `PRIO3`, `RCSL3/4`, `RSID3`, `SEQL3`, `TCSA3`, `TPIS3`, `TRIS3`, `VIVR3`) |
| **C2. Espécie `PN` histórica sem ISIN `ACNPR` ativo hoje** (`"espécie PN da relação sem ISIN da companhia no GetDetail"`, regra 33(a) em `proventos_b3.py:209`): cias que hoje só negociam `ON` (ou `PNA`/`PNB`/`UNT`) pagaram dividendos `PN` nos anos 1990/2000. `conferir_emissor` exige ISIN no `GetDetail` atual para **todas** as espécies do histórico, e `isin_no_pregao` do ticker `ON` só adiciona `ACNOR`. | **550** (36: 26 Gor, 7 Gra, 3 Ban) | **470** (24: 22 Gor, 2 Ban) | **365** (15: 14 Gor, 1 Ban) | **1.385** (75 c/ val) | 97 / 82 / 65 | **+35 / +28 / +22** (+85 total) | 29 tickers (`BBAS3`, `BHIA3`, `BRBI11`, `BRSR6`, `CAMB3`, `CGAS5`, `COGN3`, `ETER3`, `FRAS3`, `KEPL3`, `LEVE3`, `LREN3`, `MYPK3`, `PCAR3`, `PNVL3`, `PTBL3`, `RAIL3`, `RANI3`, `ROMI3`, `TUPY3`, `UGPA3`, `USIM3`, `USIM5`, `VALE3`, `VBBR3`, `VIVT3`, `VULC3`, `WEGE3`, `YDUQ3`) |
| **C3. Units (`CDAM` ausente de `ESPECIE_DO_ISIN`)** (`"espécie UNT da relação sem ISIN da companhia no GetDetail"`): `ESPECIE_DO_ISIN` (`proventos_b3.py:53`) só mapeia `ACNOR/ACNPR/ACNPA/ACNPB` e não mapeia `CDAM* -> UNT` (`BRTAEECDAM10`, `BRKLBNCDAM18`, etc.). Qualquer emissor com 1 linha `UNT` na relação falha para a unit e também para as ações `ON`/`PN` da mesma companhia (`TAEE3/4`, `SAPR3/4`, `CSAN3`, `EQTL3`). Além disso, `BacktestPIT._retornos` (linha 582) não decompõe unit em `acoes_por_unit`. | **275** (11: 7 Gor, 4 Gra) | **220** (5 Gor) | **180** (4 Gor) | **675** (20 c/ val) | 40 / 33 / 28 | **+17 / +13 / +12** (+42 total) | 13 tickers (`ALUP11`, `CSAN3`, `ENGI11`, `EQTL3`, `IGTI11`, `KLBN11`, `SANB11`, `SAPR11`, `SAPR3`, `SAPR4`, `TAEE11`, `TAEE3`, `TAEE4`) |
| **C4. `GetDetail` atual sem ISIN (`otherCodes: []`)** (`"GetDetail sem ISIN da companhia"`): 8 cias incorporadas/deslistadas recentemente têm `isins = ()` na coleta. Em `_identidade_com_o_pregao` (`b3_proventos.py:508-510`), `isin[2:6] not in {i[2:6] for i in isins}` avalia como `True` quando `isins` é vazio, descartando o `isin_no_pregao` do COTAHIST! | **135** (4 Gor) | **135** (4 Gor) | **125** (4 Gor) | **395** (12 c/ val) | 27 / 27 / 25 | **+4 / +4 / +4** (+12 total) | 8 tickers (`BRFS3`, `BRML3`, `CIEL3`, `IGTA3`, `KRSA3`, `NEOE3`, `STBP3`, `ZAMP3`) |
| **C5. Classes `PNA` / `PNB` / `PND` históricas sem ISIN ativo no `GetDetail`** (`"espécie PNA/PNB/PND da relação sem ISIN"`): mesmo mecanismo de C2 (`EGIE3`, `RADL3`, `SMFT3`, `SUZB3`, `CPLE3` são `ON`; `CPLE6` é `PNB` mas a relação tem `PNA`; `CRPG5` tem `PND` e `ACNPD` não está em `ESPECIE_DO_ISIN`). | **135** (9: 7 Gor, 2 Gra) | **120** (6 Gor) | **105** (5 Gor) | **360** (20 c/ val) | 26 / 23 / 20 | **+3 / +3 / +2** (+8 total) | 7 tickers (`CPLE3`, `CPLE6`, `CRPG5`, `EGIE3`, `RADL3`, `SMFT3`, `SUZB3`) |
| **C6. Espécie `ON` na relação sem ISIN `ACNOR` no `GetDetail`** (`"espécie ON da relação sem ISIN"`): cias que só negociam `PN` em bolsa (`ABCB4`, `BMGB4`, `TFCO4`, com `ON` fechada fora do `GetDetail`/`COTAHIST`), mas a relação lista dividendos pagos às `ON`. | **60** (3: 2 Gor, 1 Gra) | **45** (1 Gor) | **40** (1 Gor) | **145** (5 c/ val) | 2 / 1 / 1 | **+0 / +0 / +0** | 3 tickers (`ABCB4`, `BMGB4`, `TFCO4`) |
| **C7. Defasagem complemento vs. relação** (`"provento do complemento JRS CAP PROPRIO 03/11/2026 ausente da relação"`): JCP mensal do `BBDC` com `lastDatePrior = 03/11/2026` presente no complemento antes de $T+1$ (`2026-07-01`) e ausente da relação. | **10** (2 Ban) | **10** (0 c/ val) | **10** (0 c/ val) | **30** (2 c/ val) | 0 / 0 / 0 | **+0 / +0 / +0** | 2 tickers (`BBDC3`, `BBDC4`) |
| **C8. Raiz reciclada (outro CNPJ com a mesma raiz de 4 letras)** | **0** | **0** | **0** | **0** | 0 / 0 / 0 | **0** | **0 tickers** (verificado em `medir_l3_detalhe.py`: nos 369 pares com erro de identidade, `cd_cvm(ativo) == cd_cvm(coleta)` em 100% dos casos; as raízes recicladas foram isoladas no `C3-03b` / `BUG-3-60`). |
| **TOTAL L3** | **1.845** (**79** c/ val) | **1.565** (**50** c/ val) | **1.280** (**37** c/ val) | **4.690** (**166** c/ val) | **310 / 263 / 216** (789) | **+72 / +59 / +48** (**+179** Bazin c/ valor e retorno) | **93 tickers distintos** |

### HIPÓTESE
- Se `conferir_emissor` validar a identidade da companhia (`cd_cvm` da coleta igual ao `cd_cvm` do ativo no índice histórico e ISIN do pregão `isin[2:6] == emissor` para a espécie/componentes do **ticker analisado**), sem exigir que classes extintas ou não negociadas (`PN` antiga de empresa `ON`, `ON` fechada de empresa `PN`, `UNT` de unit) tenham ISIN ativo hoje no `GetDetail`, e sem exigir cruzamento quando o complemento atual da B3 vem vazio (`[]`), quase todas as 4.690 abstenções de retorno e 789 abstenções de Bazin têm a identidade comprovada com segurança contra raiz reciclada.

### Respostas (a–e)
- **a) Fonte oficial:** Sim. B3 (`GetDetail`, `GetListedCashDividends`, `GetListedSupplementCompany`) + `COTAHIST` (`isin` no pregão) + CVM (`fca_linhas` / `cad_cia_aberta.csv` com `cd_cvm` e `CNPJ`), todos já coletados e armazenados em `sentinela_store.db`.
- **b) Custo:** **0 MB** de download, **0 s** de coleta. Esforço de código estimado: **baixo a médio** (~50–90 linhas em `sentinela/data/proventos_b3.py`, `sentinela/data/providers/b3_proventos.py` e `backtesting/backtest_pit.py`, correspondente aos itens `F4-H06`, `F4-H07` e `F4-H08` de [fila-fase4-proposta.md](/docs/loop/fila-fase4-proposta.md#L76-L99)).
- **c) Ganho na sonda final:**
  - **Na lente `Bazin` (de abstenção para valor numérico E retorno total):** **+72** em 12m, **+59** em 24m, **+48** em 36m = **+179** observações com valor e retorno! (As demais das 310 em 12m têm `DY = 0` [93] ou `0 < DY < 5%` [102] ou falta de provento anterior à janela [31]).
  - **Em `retorno_total` de observações que JÁ tinham valor numérico em outras lentes (`Gordon`, `Graham`, `Bancos`):** **+79** em 12m (`57 Gordon`, `17 Graham`, `5 Bancos`), **+50** em 24m (`48 Gordon`, `2 Bancos`), **+37** em 36m (`36 Gordon`, `1 Bancos`) = **+166** observações que passam a ter par completo `(valor, retorno_total)`.
  - **Em `retorno_total` de todas as observações da sonda (incluindo lentes abstidas):** até **+1.835** em 12m, **+1.555** em 24m e **+1.270** em 36m (**+4.660** retornos destravados, excetuando as 10/10/10 de C7 `BBDC`).
  - **Total direto de observações com `(valor, retorno_total)` completo destravadas por L3:** **+151** em 12m (`72 Bazin + 57 Gordon + 17 Graham + 5 Bancos`), **+109** em 24m (`59 Bazin + 48 Gordon + 2 Bancos`), **+85** em 36m (`48 Bazin + 36 Gordon + 1 Bancos`) = **+345** observações completas!
- **d) Exige mudança de regra ou ficha?** **Sim (decisão do Marcos).** As regras 33(a)–(c) de `F2B-54` ([identidade-preferenciais-3.md](/docs/decisoes/identidade-preferenciais-3.md)) definiram que toda espécie presente em qualquer linha histórica da relação precisa ter ISIN no `GetDetail` e que o complemento não pode ser vazio. As opções para decisão do Marcos são:
  1. Em `ESPECIE_DO_ISIN`, mapear `CDAM* -> UNT` (e `ACNPD -> PND`) e em `BacktestPIT._retornos` calcular proventos de units pela soma ponderada de `acoes_por_unit` (como `serie_12_meses` já faz em `proventos_b3.py:418-420`);
  2. Em `_identidade_com_o_pregao`, aceitar `isin_no_pregao` quando `isins == ()` desde que `cd_cvm` da coleta coincida com o `cd_cvm` do ativo no índice histórico e `isin[2:6] == emissor`;
  3. Em `conferir_emissor`, quando `cd_cvm` da coleta coincide com o `cd_cvm` do ativo, exigir ISIN apenas para a(s) espécie(s) componente(s) do ticker analisado, e permitir `complemento == []` quando a companhia não tem proventos recentes anunciados no suplemento.
- **e) Riscos:**
  - *Identidade (raiz reciclada):* Relaxar a regra 33(c) sem checar `cd_cvm(coleta) == cd_cvm(ativo_em_D)` poderia atribuir proventos do emissor atual a um emissor antigo de mesma raiz de 4 letras. Porém, como `proventos_coletas` grava `cd_cvm` e o índice histórico do universo resolve `cd_cvm` por ticker e data $D$, o vínculo explícito `cd_cvm(coleta) == cd_cvm(ativo)` elimina o risco de raiz reciclada.

---

## L4. BPP só individual — Companhias sem BPP consolidado e sem controladas

### FATO (com evidência)
1. **Existência da fonte e contagem anual na CVM (2010–2025):**
   - As demonstrações individuais (`BPP_ind`, `BPA_ind`, `DRE_ind`, `DVA_ind`) já existem nos ZIPs da CVM e já estão carregadas na tabela `demonstracoes` de `sentinela_store.db` (`tipo_dem IN ('BPP_ind', 'BPA_ind', 'DRE_ind', 'DVA_ind')`).
   - Medição exata ano a ano em todos os ZIPs de DFP de 2010 a 2025 (`outputs/levantamento/medir_l4_fast.py`, `ORDEM_EXERC == 'ÚLTIMO'`, `DT_REFER == YYYY-12-31`):

| Ano | Total Cias com DFP | Com `BPP_con` | **Só `BPP_ind` (sem `BPP_con`)** | Das quais: sem `DRE_con` e sem conta de Controladas $>0$ no `BPA_ind` | Das quais: conta `1.02.03` (Investimentos) inteira $= 0$ no `BPA_ind` |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **2010** | 663 | 372 | **291** | **291 (100%)** | 146 |
| **2011** | 668 | 359 | **309** | **309 (100%)** | 165 |
| **2012** | 653 | 354 | **299** | **299 (100%)** | 154 |
| **2013** | 643 | 345 | **297** | **297 (100%)** | 143 |
| **2014** | 644 | 339 | **305** | **305 (100%)** | 146 |
| **2015** | 626 | 335 | **291** | **291 (100%)** | 141 |
| **2016** | 616 | 333 | **283** | **283 (100%)** | 133 |
| **2017** | 623 | 333 | **290** | **290 (100%)** | 136 |
| **2018** | 621 | 333 | **287** | **287 (100%)** | 127 |
| **2019** | 662 | 377 | **285** | **285 (100%)** | 107 |
| **2020** | 721 | 432 | **289** | **289 (100%)** | 111 |
| **2021** | 753 | 452 | **301** | **301 (100%)** | 109 |
| **2022** | 716 | 463 | **253** | **253 (100%)** | 75 |
| **2023** | 721 | 464 | **257** | **257 (100%)** | 82 |
| **2024** | 700 | 458 | **242** | **242 (100%)** | 70 |
| **2025** | 661 | 432 | **229** | **229 (100%)** | 61 |

2. **Descoberta crítica sobre os 76 pares ativo-data da sonda (`380` observações em 12m, `335` em 24m, `280` em 36m) que se abstêm com `"modelo da demonstração não demonstrado no BPP consolidado"` (`medir_l4_fast.py` e `complemento_l1_l4_l6.py`):**
   - Dos **76** pares ativo-data em 12m:
     - **37 pares (48,7%)** são de companhias que **TÊM `BPP_con` normal na CVM**, mas naquela data $D$ o `ano_final` selecionado pelo recorte PIT estava no índice de entregas **sem números** (reapresentação posterior a $D$ na fonte aberta ou conflito, i.e., a limitação **`GA2b` / `BUG-3-50` / `F4-H01`**)! Quando `calcular_indicadores(anos=1)` roda sobre um documento sem números no recorte PIT, `ind["cvm_dt_refer"]` vem `None` e `modelo_do_documento` devolve `None`, gerando a mensagem `"modelo da demonstração não demonstrado no BPP consolidado"`.
     - **39 pares (51,3%)** são de companhias que realmente **só entregaram demonstrações individuais (`BPP_ind`, `DRE_ind`, `BPA_ind`, `DVA_ind`)** naquele exercício (ex.: `SBSP3` em 2018–2019, `CGAS5` em 2018–2020, `CESP6` em 2019–2020, `SAPR3/4/11` em 2023–2025, `ASAI3` em 2023 e 2025, `BRAP3/4` em 2025, `ABCB4` em 2025, `PGMN3` em 2021–2022, `COCE5` em 2021 e 2023, `CARD3` em 2018 e 2021).
3. **Diferença de nomenclatura de contas na demonstração individual (D20):**
   - Em `BPP_ind`, a conta `2.03` (ou `2.07`/`2.08` em bancos) chama-se **`"Patrimônio Líquido"`** (sem a palavra `"Consolidado"` exigida por `sentinela/data/referencia/contas_cvm.csv:6,15,16`), e em `DRE_ind` a conta `3.11` (ou `3.09`/`3.13`) chama-se **`"Lucro/Prejuízo do Período"`** ou **`"Lucro ou Prejuízo Líquido do Período"`** (sem `"Consolidado"` e sem a subconta `3.11.01` de controladores).
4. **Ganho medido na sonda (`complemento_l1_l4_l6.py`) para os 39 pares genuinamente individuais (normalizando as descrições de PL e Lucro individual):**
   - Dos 39 pares ativo-data: **32** são reconhecidos como `modelo_bpp = "empresa"`, **1** como `"banco"` (`ABCB4` em 2025) e **6** continuam `None` (`BIDI3/4/11` em 2020–2021, cujo BPP individual de banco usa outra estrutura).
   - **Ganho em número por lente e horizonte (L4 isolado):**
     - `Bazin`: **+2** em 12m (**+2** com retorno: `BRAP3` e `BRAP4` em `2025-06-30`), **+0** em 24m, **+0** em 36m. *(Nos outros 30 pares de `empresa`, 9 param em L3/Unit `SAPR3/4/11`, 5 em L6 sem coleta, 5 em `DY < 5%`, etc. Se combinado com L3, `SAPR3/4/11` em 2023–2025 destravam até **+9** observações adicionais em Bazin 12m!)*
     - `Graham`: **+4** em 12m (**+1** com retorno: `ASAI3` [c/ ret] e `SAPR3`, `SAPR4`, `SAPR11` em `2025-06-30`), **+0** em 24m, **+0** em 36m. *(Nos anos 2018–2024, os pares individuais param na falta de `composicao_capital` antes de 2020, i.e., dependem de L1).*
     - `Gordon`, `Lynch`, `Bancos`: **+0** isoladamente.
     - **Total L4 isolado:** **+6** observações em 12m (**+3** com retorno).

### HIPÓTESE
- Se a ausência de números no `ano_final` do recorte PIT (**`GA2b` / `F4-H01`**, que responde por **37 dos 76 pares**) for tratada com motivo próprio (ou recuo quando aplicável), metade das abstenções atribuídas na sonda a `"modelo da demonstração não demonstrado no BPP consolidado"` deixará de ser confundida com falta de BPP consolidado. E para os 39 pares genuinamente sem controladas, combinar L4 com L3 (identidade de `SAPR3/4/11`) e L1 (FRE) eleva o ganho de +6 para cerca de **+15 a +25** observações em 12m.

### Respostas (a–e)
- **a) Fonte oficial:** Sim. CVM DFP (`BPP_ind`, `BPA_ind`, `DRE_ind`, `DVA_ind`), desde **2010**, com `DT_RECEB` no índice da DFP, já no banco (`demonstracoes`) e nos ZIPs locais.
- **b) Custo:** **0 MB** de download, **0 s** de coleta. Esforço de código estimado: **médio** (~80–120 linhas em `cvm_provider.py`, `contas_cvm.csv` e `controladores.py`, além de exigir comprovação de ausência de controladas/consolidação).
- **c) Ganho na sonda final:**
  - Isoladamente: **+6** observações em 12m (`+2 Bazin` [+2 c/ ret] e `+4 Graham` [+1 c/ ret] em `2025-06-30`), **+0** em 24m, **+0** em 36m.
  - Combinado com L3 (`SAPR3/4/11`): até **+15** em 12m, **+6** em 24m, **+3** em 36m.
- **d) Exige mudança de regra ou ficha?** **Sim (decisão do Marcos).** As fichas de metodologia e `AGENTS.md` ("Escopo pelo modelo do BPP consolidado (F2B-4)") exigem demonstrações consolidadas (`*_con`) e os pares `(código, descrição)` de `contas_cvm.csv` com a palavra `"Consolidado"`. Para usar `*_ind`, Marcos precisaria autorizar o fallback para `*_ind` quando a companhia não entrega `*_con` e o `BPA_ind` comprova ausência de investimentos em controladas (ou quando a companhia é pura sem consolidação), adicionando os pares de descrição individual (`"Patrimônio Líquido"`, `"Lucro/Prejuízo do Período"`) em `contas_cvm.csv`.
- **e) Riscos:**
  - *Perímetro econômico (holdings sem consolidação):* Algumas companhias que só entregam `*_ind` em determinado exercício (como `BRAP3/4` — Bradespar, que é holding pura de `VALE3` por equivalência patrimonial, sem controladas) têm `1.02.03` (Investimentos em coligadas) relevante, mas zero controladas; já outras podem ter deixado de consolidar controladas por exceção contábil. Verificar `Investimentos em Controladas == 0` no `BPA_ind` mitiga o risco de misturar controladora individual com grupo econômico não consolidado.

---

## L5. Agenda de divulgação do IPCA antes de 12/2016

### FATO (com evidência)
1. **Limite da API de calendário do IBGE:** A API oficial do calendário do IBGE (`https://servicodados.ibge.gov.br/api/v3/calendario/9256`, armazenada em `series_macro` sob `serie = 'ipca_divulgacao'`, 242 linhas) começa na referência **`2016-12-01`** (divulgada em **`2017-01-11`**). Não existe endpoint de calendário estruturado no IBGE para as datas de divulgação anteriores a `12/2016` (fato já documentado na `DD-39` e em [macro_por_data.py](/sentinela/data/macro_por_data.py#L46-L78)).
2. **Como o código atual trata `ipca_sidra` e `ipca_divulgacao` no banco (`sentinela/data/providers/macro.py`):**
   - Na tabela `series_macro` de `sentinela_store.db` (`outputs/levantamento/medir_l5_l6_l7.py`), a série `ipca_sidra` tem apenas **119 linhas, de `2016-12-01` a `2026-10-01`**, porque `gravar_series._ipca` ([macro.py](/sentinela/data/providers/macro.py#L778-L795)) só grava no banco os meses presentes em `agenda["publicacoes"]` ($\ge$ `201612`), embora a API SIDRA 1737 (`https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2266/p/all`) forneça o número-índice desde **12/1979**.
   - Além disso, `indices_ipca` ([macro.py](/sentinela/data/providers/macro.py#L154-L187)), usada por `Graham` para corrigir os 5 LPAs anuais, exige `if mes not in publicacoes or publicacoes[mes] >= dia: continue`, ao passo que `ipca_publicado_em` ([macro_por_data.py](/sentinela/data/macro_por_data.py#L69-L77), usada pela inflação de 12m da taxa real de Gordon/Bancos, `DD-39`) aplica a monotonicidade cronológica: se a referência $M$ é anterior à primeira referência da agenda (`2016-12`) e `2016-12` já havia sido divulgada antes de $D$ (`2017-01-11 < D`), então $M$ **comprovadamente já estava publicada em $D$**!
3. **Impacto medido na sonda (`medir_l5_l6_l7.py` e `complemento_l1_l4_l6.py`):**
   - Na sonda atual, **0 observações** falham por IPCA porque todas asdatas da sonda são $\ge$ `2018-06-29` (logo a janela de 12 meses de Gordon/Bancos é $\ge$ `2017`, já coberta por `2016-12..2026-10`), e em `Graham` todas as observações de `2018` a `2021` falham antes, na etapa de ações (`L1`).
   - Quando **L1 (FRE)** é ativada (`complemento_l1_l4_l6.py`), estender a regra de monotonicidade da `DD-39` (`M < 2016-12` tem `publicacao <= 2017-01-11 < D` para qualquer $D \ge \text{2017-01-12}$) e gravar `ipca_sidra` de `2012-12` a `2016-11` no banco destrava em `Graham`:
     - **12m:** **+1** em `2018-06-29` e **+1** em `2019-06-28` (**+2** observações em 2018–2019; no total 12m o saldo líquido fica em 124 porque em 2021/2024 2 empresas com exercício não-dezembro mudam de guarda, mas em **36m** o total de `Graham` sobe de **+85 para +87** observações com valor e de **+31 para +32** com retorno).

### HIPÓTESE
- Para qualquer data de análise $D \ge \text{2017-01-12}$ (inclui todas as 8 datas da sonda, 2018 a 2025), **não é necessário nenhum calendário histórico anterior a 12/2016**: a própria `DD-39` já prova que qualquer mês $M < \text{2016-12}$ foi divulgado até `2017-01-11 < D`. Basta gravar no `series_macro` as linhas do SIDRA 1737 anteriores a `2016-12` (desde `2009-12`) e aplicar em `macro.indices_ipca` a mesma regra da `DD-39` já usada em `macro_por_data.ipca_publicado_em`.

### Respostas (a–e)
- **a) Fonte oficial:** A série histórica do índice IPCA existe oficialmente no IBGE SIDRA (tabela 1737, variável 2266, desde **12/1979**). O calendário de divulgação por API do IBGE só existe desde **12/2016** (`2017-01-11`), mas para qualquer corte $D \ge \text{2017-01-12}$ a publicação de todos os meses $\le \text{2016-11}$ até `2017-01-11` é um fato matemático decorrente da divulgação em `2017-01-11` (`DD-39`).
- **b) Custo:** **< 0,1 MB** (a resposta completa da API SIDRA 1737 tem ~35 KB e já é baixada pelo coletor de macro; falta apenas não descartar no `_ipca` os meses $< \text{201612}$). Esforço de código estimado: **muito baixo** (~15 linhas em `sentinela/data/providers/macro.py`).
- **c) Ganho na sonda final:**
  - Isoladamente (sem L1): **0** observações.
  - Combinado com L1 (e necessário caso `GA2b` / `F4-H01` ou versões anteriores do FRE destravem mais ativos em `2018–2020`): habilita `Graham` em `2018`, `2019` e `2020` (**+2** observações imediatas em 2018–2019 em cada horizonte = **+6** observações nos 3 horizontes, e destrava o IPCA para todas as companhias de `2018–2021`).
- **d) Exige mudança de regra ou ficha?** **Não.** A regra já foi aprovada na `DD-39` para a inflação da taxa real (`macro_por_data.py:69-77`); trata-se apenas de aplicá-la também em `macro.indices_ipca` e `gravar_series._ipca`.
- **e) Riscos:**
  - *Vazamento de futuro:* **Zero** para qualquer data de corte $D \ge \text{2017-01-12}$, pois `2016-12` foi divulgado em `2017-01-11` e o IBGE nunca revisa o número-índice mensal publicado do IPCA. (Só haveria risco se o backtest rodasse em uma data $D < \text{2017-01-12}$, onde o mês imediatamente anterior a $D$ precisaria do dia exato de divulgação dentro daquele mês).

---

## L6. Proventos de empresas deslistadas — Fonte oficial com data ex

### FATO (com evidência)
1. **Verificação das fontes oficiais para empresas deslistadas:**
   - **B3 (`GetDetail` / `GetListedCashDividends`):** Conforme já verificado em [l1-fontes-historicas.md](/docs/decisoes/l1-fontes-historicas.md#L76-L90), para companhias cujo registro na B3 foi cancelado, o endpoint `GetDetail` retorna vazio e a B3 retira a relação estruturada de proventos.
   - **CVM (`DFP`, `ITR`, `FRE`):** Possuem dividendos e JCP totais distribuídos no exercício (`DVA`, `DMPL`, `DFC`, e `fre_cia_aberta_distribuicao_dividendos_{ano}.csv`), **mas não possuem a `data ex` (nem a `data com`) por evento**, o que impede seu uso para o retorno total em `[T, T+1]` ou para a janela móvel de 12 meses de Bazin por pregão.
   - **CVM (`IPE` — `dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/ipe_cia_aberta_{ano}.zip`):** Traz o índice de entregas de "Aviso aos Acionistas" e "Ata de RCA/AGO" com `Data_Entrega` e `Link_Download`, mas o conteúdo (data com/ex e valor por ação) está em PDFs/HTMLs não estruturados.
   - **B3 (`COTAHIST`):** A coluna `especificacao` da tabela `precos` (posições 40–49 do arquivo `COTAHIST_A{ano}.ZIP`) marca no dia ex os sufixos `ED` (ex-dividendo), `EJ` (ex-JCP), `EDJ`, `ER`, etc., identificando **quais pregões foram data ex**, mas **não traz o valor em R$ do provento**.
2. **Decomposição factual das observações com `"sem coleta da relação de proventos do emissor"` na sonda (`outputs/levantamento/medir_l3_l6_ganho.py`):**
   - Na sonda atual, esse motivo aparece em **1.681** retornos em 12m (**1.501** em 24m, **1.295** em 36m) e em **122** lentes `Bazin` em 12m (**117** em 24m, **109** em 36m).
   - Primeiro filtro factual: **896** (12m), **746** (24m) e **590** (36m) desses retornos são de **FIIs** (cujo retorno virá do Informe Mensal CVM no item `F4-H14`, não de relação de companhias!).
   - Restam **785** observações de retorno de **ações/units (`STOCK`/`UNIT`)** em 12m (**755** em 24m, **705** em 36m), correspondentes a `157` pares ativo-data em `67` tickers distintos (e as **122 / 117 / 109** abstenções de `Bazin`).
   - **Crucial — Decomposição dos 67 tickers de ações/units (`medir_l3_l6_ganho.py`):**

| Categoria real dos 67 tickers sem coleta pelo prefixo `ticker[:4]` | Tickers distintos (12m) | Retorno abstido (12m / 24m / 36m) | Dos quais JÁ têm valor na lente (12m / 24m / 36m) | Lente `Bazin` abstida (12m / 24m / 36m) | Evidência / Como destravar |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Subgrupo L6-A: Companhias ATIVAS que mudaram de raiz de ticker e JÁ ESTÃO COLETADAS no banco sob o mesmo `cd_cvm`!** (`proventos_coletas` guarda o `emissor` atual da B3, ex. `MOTV`, `VBBR`, `YDUQ`, `ISAE`, `AXIA`, `DXCO`, `AZZA`, `ALOS`, enquanto `relacao_ate` e `proventos_ate` buscam `WHERE emissor = ticker[:4]` antigo, ex. `CCRO`, `BRDT`, `ESTC`, `TRPL`, `ELET`, `DTEX`, `ARZZ`, `ALSO`!) | **26 tickers** (`ALSO3`, `ARZZ3`, `ATMP3`, `BKBR3`, `BRDT3`, `BTOW3`, `CARD3`, `CCRO3`, `CNTO3`, `DTEX3`, `ELET3`, `ELET6`, `EMBR3`, `ESTC3`, `GUAR3`, `GUAR4`, `JPSA3`, `LLIS3`, `MBLY3`, `MEGA3`, `ODPV3`, `OMGE3`, `RRRP3`, `SSBR3`, `TRPL4`, `WIZS3`) | **295 / 285 / 275** (855 total) | **8 / 6 / 5** (19 total) | **51 / 50 / 49** (150 total) | **0 MB de download!** A coleta já está em `proventos_coletas` com o mesmo `cd_cvm`! Basta buscar por `cd_cvm` quando `emissor = ticker[:4]` não existir. |
| **Subgrupo L6-B: Companhias com `SIT = ATIVO` na CVM sem coleta no banco** (`AESB3`, `CESP6`, `ENBR3`, `JBSS3`, `OIBR3` — incorporadas em cias ativas ou mudaram de listagem) | **5 tickers** | **70 / 70 / 60** (200 total) | **4 / 4 / 4** (12 total) | **10 / 10 / 9** (29 total) | Testar coleta na B3 por `cd_cvm` (`OIBR3`/`JBSS3`); as incorporadas (`AESB3`, `CESP6`, `ENBR3`) caem no caso L6-C. |
| **Subgrupo L6-C: Companhias efetivamente DESLISTADAS na CVM (`SIT = CANCELADA` ou `SUSPENSO`)** | **36 tickers** (`ALSC3`, `BIDI3/4/11`, `BOAS3`, `BPAN4`, `BRIT3`, `CLSA3`, `CRFB3`, `ELMD3`, `ENAT3`, `GNDI3`, `GOLL4`, `HGTX3`, `IGBR3`, `LAME3/4`, `LCAM3`, `MODL3`, `MPLU3`, `NGRD3`, `NTCO3`, `PARD3`, `PETZ3`, `PORT3`, `POWE3`, `QGEP3`, `RLOG3`, `SGPS3`, `SHOW3`, `SLED4`, `SOMA3`, `SQIA3`, `SULA11`, `TIET11`, `TIMP3`) | **420 / 400 / 370** (1.190 total) | **7 / 7 / 6** (20 total) | **61 / 57 / 51** (169 total) | Sem fonte oficial estruturada com `data ex` e valor em R$. |
| **TOTAL AÇÕES/UNITS SEM COLETA** | **67 tickers** | **785 / 755 / 705** (2.245) | **19 / 17 / 15** (51) | **122 / 117 / 109** (348) | — |

### HIPÓTESE
- Para as **36 companhias genuinamente deslistadas (Subgrupo L6-C)**, nos períodos de 12 meses em que o `COTAHIST` (`precos.especificacao`) **não apresenta nenhum marcador `ED`/`EJ`/`EDJ`** (ou quando a DVA/DFC da DFP do exercício comprova proventos distribuídos $= 0$), é possível demonstrar que o provento na janela foi zero (`R$ 0,00`), destravando o `retorno_total` sem precisar de fonte externa. Já quando houve pagamento (`ED`/`EJ`), não há fonte oficial estruturada (CSV/API) na CVM ou B3 que traga simultaneamente a `data ex` e o valor por ação em R$.
- Em contrapartida, **38% de todas as abstenções "sem coleta" de ações/units (Subgrupo L6-A: 295 em 12m, 285 em 24m, 275 em 36m, além de 51/50/49 em Bazin)** **NÃO são empresas sem dados no banco**: são empresas ativas que mudaram de código de 4 letras (`CCRO -> MOTV`, `BRDT -> VBBR`, `ELET -> AXIA`, `EMBR -> EMBJ`, `ESTC -> YDUQ`, `TRPL -> ISAE`, `ARZZ -> AZZA`, `ALSO/SSBR -> ALOS`, `DTEX -> DXCO`, `CNTO -> SBFG`, `CARD -> CSUD`, `ODPV -> SAUD`, `GUAR -> RIAA`, `WIZS -> WIZC`) e cuja coleta **já está gravada em `proventos_coletas` sob o mesmo `cd_cvm`**!

### Respostas (a–e)
- **a) Fonte oficial:**
  - *Para empresas genuinamente deslistadas (Subgrupo L6-C):* **Não existe** fonte oficial estruturada (CSV/JSON da B3 ou CVM) que forneça os proventos por espécie com `data ex` (na CVM só existem totais anuais em DFP/FRE sem `data ex`, ou PDFs não estruturados de Aviso aos Acionistas no IPE; no COTAHIST existe a flag `ED`/`EJ` na data ex, sem o valor em R$).
  - *Para empresas que mudaram de raiz de ticker (Subgrupo L6-A):* **Sim**, a fonte oficial é a própria B3 (`GetListedCashDividends`) **já coletada e armazenada em `proventos_coletas` / `proventos`** sob o `cd_cvm` da companhia!
- **b) Custo:**
  - *Subgrupo L6-A (busca por `cd_cvm` no banco):* **0 MB** de download, **0 s** de coleta, esforço de código **muito baixo** (~20 linhas em `b3_proventos.proventos_ate` e `relacao_ate` para buscar a coleta por `cd_cvm` quando `emissor = ticker[:4]` não retornar linha, validando o ISIN pela espécie/classe).
  - *Subgrupo L6-C (deslistadas via parser de PDFs do IPE/CVM):* Centenas de MB de PDFs e esforço **muito alto**, com baixa confiabilidade de parse textual (inviável pelo contrato de dados).
- **c) Ganho na sonda final:**
  - *Subgrupo L6-A (buscar coleta já existente por `cd_cvm`):* Destrava a coleta para **295** observações em 12m (**285** em 24m, **275** em 36m = **855** observações de retorno, das quais **19** já têm valor numérico em Gordon/Graham) e para **51** observações da lente `Bazin` em 12m (**50** em 24m, **49** em 36m = **150** observações de Bazin, gerando cerca de **+15 a +35** novos valores numéricos em Bazin quando combinada com L3).
  - *Subgrupo L6-C (deslistadas reais):* **0** por fonte estruturada direta (apenas7 observações em 12m, 7 em 24m e 6 em 36m têm valor numérico na lente e estão sem retorno por deslistagem real).
- **d) Exige mudança de regra ou ficha?**
  - *Subgrupo L6-A (vínculo por `cd_cvm` quando a companhia mudou de raiz de 4 letras):* Apenas ajuste na regra de conferência de ISIN (`conferir_emissor` / `_identidade_com_o_pregao`), pois o `isin_no_pregao` antigo tem os 4 caracteres da raiz antiga (`BRCCRO...`) e o `GetDetail` atual tem a raiz nova (`BRMOTV...`), ambos pertencentes ao mesmo `cd_cvm` e `CNPJ` oficial da CVM.
- **e) Riscos:**
  - *Identidade em fusões por incorporação:* Quando uma companhia muda apenas de denominação/ticker mantendo o mesmo `cd_cvm` e `CNPJ` (`CCRO3 -> MOTV3`, `BRDT3 -> VBBR3`, `ESTC3 -> YDUQ3`, `TRPL4 -> ISAE4`, `DTEX3 -> DXCO3`, `CNTO3 -> SBFG3`, `CARD3 -> CSUD3`, `ELET3 -> AXIA3`, `EMBR3 -> EMBJ3`), a relação da B3 no `cd_cvm` pertence exatamente à mesma pessoa jurídica e mesma base acionária. Deve-se apenas confirmar `cd_cvm` idêntico no FCA/cadastro da CVM.

---

## L7. IF.data (bancos) — Calendário oficial de publicação do BCB

### FATO (com evidência)
1. **Inexistência de calendário oficial por observação no BCB:** Conforme verificado em [calendario-ifdata-2c.md](/docs/decisoes/calendario-ifdata-2c.md#L1-L34) sobre `https://www3.bcb.gov.br/ifdata/index.html` e `https://www3.bcb.gov.br/ifdata/rest/relatorios2025a2030`, o Banco Central informa apenas prazos gerais de divulgação (**até 60 dias** após março, junho e setembro e **até 90 dias** após dezembro, com reprocessamento anual em abril) e não disponibiliza carimbo oficial de data de publicação por trimestre/instituição.
2. **Efeito nulo sobre os valores e abstenções da sonda (`outputs/levantamento/medir_l5_l6_l7.py`):**
   - Pela ficha [bancos.md](/docs/metodologia/bancos.md) (§2, §3, §4, §7.4, §7.5) e por `AGENTS.md` ("Basileia e inadimplência do IF.data só como contexto"), **nenhum dado do IF.data entra na fórmula nem nas guardas de elegibilidade da lente `Bancos`** ($P_0 / B_0 = (\text{ROE} - g)/(k - g)$, que usa apenas BPP/DRE/DVA consolidados da CVM e `series_macro`).
   - Em `MotorHistorico._buscar_ifdata` ([historico.py](/sentinela/services/historico.py#L257-L259)), o IF.data já fica desabilitado no histórico apenas com aviso em `riscos_dados`, **sem bloquear a lente `Bancos`** (tanto que a lente `Bancos` já produz **7** valores numéricos em 12m, **4** em 24m e **3** em 36m na sonda atual).
   - Das **64** observações de companhias com `modelo_bpp == "banco"` em 12m na sonda (`medir_l5_l6_l7.py`), **7** produzem valor e as **57** abstenções ocorrem por:
     - `28`: `"base de ações incompatível ou sem evidência vigente"` (falta de `composicao_capital` na DFP antes de 2020 ou variação fora de `(0,9; 1,1)` — escopo de L1);
     - `13`: `"estrutura da DVA não permite atribuir proventos aos controladores"`;
     - `9`: `"Empresa em situação especial/distressed"`;
     - `4`: `"classes com direitos distintos na fase 2B"`;
     - `3`: `"payout fora de (0,1]"`.
     - **`0` (ZERO)** observações se abstêm por falta do IF.data!

### HIPÓTESE
- Nenhuma hipótese necessária: o código e a ficha já tratam o IF.data exclusivamente como contexto descritivo opcional na apresentação corrente.

### Respostas (a–e)
- **a) Fonte oficial:** **Não existe** calendário oficial de publicação por data-base no IF.data do BCB (apenas prazos máximos regulamentares de +60/+90 dias).
- **b) Custo:** N/A (0 MB).
- **c) Ganho na sonda final:** **0 observações (ZERO)** em todas as lentes e em todos os horizontes (12m, 24m e 36m), pois o IF.data é apenas contexto e não bloqueia a lente `Bancos`.
- **d) Exige mudança de regra ou ficha?** **Não.**
- **e) Riscos:** Adotar a regra heurística de `+60/+90 dias` sem data oficial violaria o contrato histórico estrito (`D36`/`DD-40`) sem destravar nenhuma observação.

---

## Tabela Resumo Ordenada pelo Ganho por Esforço

A tabela abaixo ordena as lacunas (e a subdivisão descoberta em L6 e L2) da maior para a menor relação **ganho verificável na sonda final (`outputs/c3-sonda/`) ÷ esforço de implementação e coleta**:

| Ordem | Lacuna / Item | Fonte Oficial e Disponibilidade | Download e Coleta | Esforço de Código | Ganho de Lente (Abstenção $\to$ Número: 12m / 24m / 36m = **Total**) | Ganho de Retorno em Obs. já c/ Valor (12m / 24m / 36m = **Total**) | Total de Obs. Desbloqueadas (Valor novo ou Par Valor+Retorno) | Exige Decisão / Mudança de Ficha? |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1º** | **L2 — FII no histórico via Informe Mensal CVM** (`Cotas_Emitidas` + continuidade de `VP` nos 13 meses) | **Sim.** CVM Informe Mensal (`fii_informe_linhas`, desde 01/2016, com `Data_Entrega`). Já no banco. | **0 MB** / **0 s** (já no SQLite) | **Baixo** (~30–50 linhas em `rendimento_fii.py`) | **+301 / +260 / +219 = +780** na lente `Rendimento do FII` *(ou +192 / +164 / +140 = +496 se exigir `Cotas_Emitidas` estritamente constante)* | Depende de `F4-H14` (retorno de FII via Informe) | **+780** valores de lente *(destrava quintis $\ge 25$ em 7 das 8 datas!)* | **Sim** (autorizar `Cotas_Emitidas` + `VP` do Informe sem `b3_fundo` quando `as_of < hoje`) |
| **2º** | **L3 — Identidade dos proventos B3** (`CDAM -> UNT`, `isins == ()` c/ COTAHIST, espécie do ticker analisado, complemento vazio c/ `cd_cvm` igual) | **Sim.** B3 (`proventos_coletas`, `proventos`) + COTAHIST (`isin`) + CVM (`cd_cvm`). Já no banco. | **0 MB** / **0 s** (já no SQLite) | **Baixo a Médio** (~50–90 linhas; itens `F4-H06` a `F4-H08`) | **+72 / +59 / +48 = +179** na lente `Bazin` (todas já com retorno!) | **+79 / +50 / +37 = +166** pares `(valor, retorno)` em `Gordon` (+141), `Graham` (+17) e `Bancos` (+8) *(além de +4.494 retornos em obs. sem valor)* | **+345** observações completas `(valor, retorno)` (**+4.839** somando todos os retornos destravados) | **Sim** (ajustar regras 33(a)–(c) de `conferir_emissor` quando `cd_cvm` da coleta = `cd_cvm` do ativo) |
| **3º** | **L1 — Ações antes de 2020 via Conta `f` do FRE** (`outputs/f3-8k/fre/`, 2010–2021, `DT_RECEB < D` e escala via LPA da DRE) | **Sim.** CVM FRE (`fre_cia_aberta_2010..2021.zip`, item 3.1 conta `f`, com `DT_RECEB`). Já baixado em disco. | **0 MB novos** (95 MB já em `outputs/f3-8k/fre/`) / **~1 s** | **Baixo a Médio** (~80–120 linhas; item `F4-H04`) | `Graham`: **+124 / +124 / +85 = +333**<br>`Lynch`: **+1 / +1 / +1 = +3** *(+75 em 12m aguardando DY de L3/L6)*<br>**Total: +336** | **+56 / +55 / +32 = +143** dos novos valores já nascem com `retorno_total` | **+336** valores de lente (**+143** já com retorno; destrava quintis $\ge 25$ em Graham de 2022 a 2024) | **Sim** (autorizar conta `f` do FRE quando DFP $<2020$ não tem composição, c/ escala pelo LPA da DRE) |
| **4º** | **L6-A (descoberta em L6) — Busca de `proventos_coletas` por `cd_cvm` para cias que mudaram de raiz de ticker** (`CCRO->MOTV`, `BRDT->VBBR`, `ELET->AXIA`, etc.) | **Sim.** B3 `proventos_coletas` já gravada no banco sob o `cd_cvm` da companhia (26 tickers). | **0 MB** / **0 s** (já no SQLite) | **Muito Baixo** (~20 linhas em `b3_proventos.py`) | Destrava a coleta para **51 / 50 / 49 = 150** obs. de `Bazin` (gerando **~+15 a +35** valores c/ L3) | **+8 / +6 / +5 = +19** obs. que já têm valor em `Gordon`/`Graham` *(e **+855** retornos totais)* | **+19** pares `(valor, retorno)` imediatos + **855** coletas de retorno + **150** coletas p/ Bazin | **Sim** (permitir vínculo por `cd_cvm` quando a raiz de 4 letras mudou sem troca de CNPJ/CVM) |
| **5º** | **L5 — IPCA antes de 12/2016 via monotonicidade da `DD-39`** (gravar `ipca_sidra` `< 201612` e aplicar `DD-39` em `indices_ipca`) | **Sim.** IBGE SIDRA 1737 (desde 1979) + `DD-39` (`2016-12` divulgado em `2017-01-11 < D`). | **< 0,1 MB** (~35 KB já baixados no coletor) | **Muito Baixo** (~15 linhas em `macro.py`) | **+0** isolado; **+2 / +2 / +2 = +6** combinados com L1 em 2018–2019 (e habilita IPCA para todo `2018–2021`) | **+0 / +0 / +1 = +1** | **+6** valores em `Graham` (2018–2019) e remove o bloqueio de IPCA de `2013..2016` | **Não** (estende a `DD-39` já aprovada em `macro_por_data.py` para `indices_ipca`) |
| **6º** | **L4 — BPP só individual sem controladas** (`BPP_ind` / `DRE_ind` quando não há `BPP_con` e sem controladas no `BPA_ind`) | **Sim.** CVM DFP (`*_ind`, desde 2010, já em `demonstracoes`). *(Nota: 37 dos 76 pares da sonda são `GA2b`/`F4-H01`, não L4).* | **0 MB** / **0 s** (já no SQLite e ZIPs) | **Médio** (~80–120 linhas + pares individuais em `contas_cvm.csv`) | **+6 / +0 / +0 = +6** isolado (`+2 Bazin`, `+4 Graham` em 2025) *(até **+24** nos 3 horiz. se combinado c/ L3 para `SAPR`)* | **+3 / +0 / +0 = +3** (`BRAP3/4` em Bazin e `ASAI3` em Graham) | **+6** valores de lente isoladamente (até **+24** combinado com L3) | **Sim** (autorizar `*_ind` quando sem `*_con` e sem controladas, e descrições sem `"Consolidado"`) |
| **7º** | **L6-C — Proventos de empresas efetivamente deslistadas** (`SIT = CANCELADA`, 36 tickers) | **Não existe** fonte oficial estruturada (CSV/JSON) com `data ex` e valor em R$ (só PDFs no IPE/CVM ou flag `ED`/`EJ` sem valor no COTAHIST). | Centenas de MB (PDFs IPE) | **Muito Alto** (parser de PDFs não estruturados) | **0** (inviável por fonte estruturada) | Apenas **7 / 7 / 6 = 20** obs. na sonda inteira têm valor de lente e estão sem retorno por deslistagem real | **0** por fonte estruturada | **Sim** (se quisesse usar DVA anual sem data ex ou `ED/EJ` vazio = 0) |
| **8º** | **L7 — Calendário oficial de publicação do IF.data (BCB)** | **Não existe** data de publicação por observação no BCB (apenas prazo de +60/+90 dias). | **0 MB** | **Nenhum** | **0 / 0 / 0 = 0** (IF.data é apenas contexto descritivo e não entra na fórmula nem abstém a lente `Bancos`) | **0 / 0 / 0 = 0** | **0** | **Não** |
