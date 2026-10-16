# Auditoria externa da Fase 2A (D30)

**Escopo:** branch `v2/fase-2a` em `c05f4ed`, contra a tag `v2-fase-1`.
**Auditores** (família diferente da do executor, Claude Code):
- Codex, modo FASE, 15/10/2026, somente leitura. O pytest não rodou na sandbox dele (sem diretório temporário); o ruff passou.
- Gemini 4 Argon (app do Gemini), duas passadas: 14/10/2026 (`auditoria-gemini-completa.md`, com anexos cortados) e 15/10/2026 (código de `sentinela/**`, testes restantes e os itens F2A-13, F2A-14 e F2A-28).

**Push antes da auditoria:** decisão do Marcos de 14/10/2026, para auditar a partir do GitHub. Sem PR nem merge até o fechamento. CI #57 do GitHub verde em `c05f4ed` (ruff e pytest numa máquina limpa), o que supre a suíte que o Codex não rodou.

**Veredito dos dois auditores:** não pode seguir.

## Consolidação (conferida no código pelo Claude)

Todo bug confirmado vira teste de regressão em `tests/regressao/` (decisão do Marcos de 15/10/2026). A tabela completa, com teste e estado, fica em `tests/regressao/README.md` (F2A-40).

| Bug | Achado | Quem achou | Destino |
|---|---|---|---|
| BUG-2A-01 | valores ≤ 0 da CVM descartados no merge; prejuízo como dado ausente | Gemini 1ª, Codex (reproduziu) | **dispensa escrita:** xfail estrito → F2B-8 (comportamento da V1; mudar afeta a pontuação) |
| BUG-2A-02 | reserva com "sem correspondência", contra a D20 | Gemini 1ª e 2ª, Codex | corrigir na 2A (F2A-41) |
| BUG-2A-03 | linha dos controladores ausente devolve o total com minoritários no balanço | Codex (reproduziu: 100 aceito com 50 de minoritários), Gemini 2ª | F2A-41 |
| BUG-2A-04 | minoritários do balanço lidos só no modelo do setor | Gemini 1ª, Codex | F2A-41 |
| BUG-2A-05 | PL total inválido sem motivo | Gemini 2ª | F2A-41 |
| BUG-2A-06 | P/VP NaN ou infinito na saída do motor de FII (furo do F2A-24) | Gemini 1ª, Codex | F2A-42 |
| BUG-2A-07 | ativo fora do índice recebe métodos de ação (furo do F2A-29) | Gemini 1ª e 2ª, Codex | F2A-43 |
| BUG-2A-08 | rastreabilidade: "FII sem P/VP usa 1,0" | Gemini 2ª | F2A-44 |
| BUG-2A-09 | rastreabilidade: LPA da CVM descrito como lucro ÷ ações | Gemini 2ª | F2A-44 |
| BUG-2A-10 a 18 | TTM sem a regra 7.2; alerta do F2A-5 sobre divulgado bruto; FII sem `valores_por_fonte`; risco "fora da CVM" em FII; Informe sem desempate por versão; DY inválido sobrescrevendo válido; ZIP vazio do COTAHIST; `FiiNav` com P/VP ≤ 0; `Graham` com VPA < 0 | Gemini e Codex | **dispensa escrita:** xfail estrito → proposta da 2B |

## Correções da proposta da 2B (antes de ativar)

1. A fórmula do g real do Gordon (F2B-23 e F2B-1) foi decidida pelo texto e é incoerente com a conversão por Fisher do F2B-26; vira `[DECISÃO]` do Marcos na ficha do Gordon (Gemini 2ª, com o exemplo de −0,66% contra +2,46% e valor justo 37% maior).
2. F2B-27 vem antes do `[DECISÃO]` de que depende.
3. F2B-9 não lista `tests/test_market_engine_acoes_cvm.py::test_sem_linha_da_controladora_vale_o_lucro_total` (resolvido antes, no F2A-41).
4. F2B-5 junta mudança de golden num `chore:` e exige um `git grep` que falha em `scripts/dossie_fase2.py`.
5. F2B-4 exige golden inalterado que pode falhar conforme onde a limitação "sem setor" for gravada.
6. Cada BUG-2A aberto ganha item de destino; mais as ressalvas omitidas (tesouraria total × por espécie; filtro `GRUPO_DFP` e `VERSAO`; divergência de ações PNA/PNB; completude de bancos e FIIs; BTCI11 e TRPL11 no índice).
7. Também para a 2B ou 2C: IF.data sem a proveniência completa da D16; rótulo "QUALIDADE — AGUARDAR" inalcançável e testado com `math.exp` simulado; testes do Gordon e do Lynch com o valor esperado copiado do código; precedência de BTCI11 e TRPL11 sobre as listas conhecidas.

## Decisões em aberto (seguem para a 2B)

A (alavancagem com EBITDA ≤ 0), B (holdings financeiras), C (piso do ROE), D (base da margem): dados confirmados pelo Codex, sem decisão.

## Correções do resumo da fase

O "efeito nulo hoje" do F2A-13 não vale para o relatório de qualidade (confiança 40 → 10 em dado antigo com fonte fundamentus; Codex). "ROE negativo passa" depende da fonte (BUG-2A-01). A suíte tem 75 módulos, não 76 (Gemini 2ª). Entram no F2A-45.

## Relatório do Codex (modo FASE)

## Modo e escopo

**FASE** — branch `v2/fase-2a`, HEAD `c05f4ed65fb6f0fdfcc2922a48f1769e15ffa7d4`, contra `v2-fase-1`, usando o diff com três pontos e o histórico cronológico solicitado: 62 commits sem contar merges.

**Há bloqueios.** Os quatro principais achados do Gemini permanecem no HEAD. Também reproduzi uma reserva indevida de lucro mesmo com minoritários explícitos no balanço e refutei a alegação geral de efeito nulo do F2A-13.

Auditoria somente leitura; nenhum arquivo alterado. Ruff passou. O pytest falhou antes da coleta porque o sandbox não oferece diretório temporário gravável. Não regenerei o golden nem executei mutmut.

As evidências abaixo referem-se ao HEAD, salvo indicação de commit. “Sem achado adicional” não certifica números de levantamentos externos; os limites estão em **Não verificado**.

## F2A-3 — `882ef0c`

- **bloqueia** — `market_engine.py:130`, `market_engine.py:179`: o merge rejeita LPA, VPA, ROE, P/L e P/VP não positivos da CVM e preserva eventual valor positivo anterior; reproduzido em memória. Fechar distinguindo ausência de prejuízo/PL negativo e verificando a cascata completa.
- **ressalva** — `cvm_provider.py:215`, `sentinela/data/acoes_cvm.py:82`: o total de tesouraria governa o denominador, enquanto a divergência por espécie usa tesouraria ON/PN (`acoes_cvm.py:325`); inconsistências entre esses campos não são reconciliadas. Fechar com validação explícita de consistência.

## F2A-5 — `b83dde1`

- **ressalva** — `market_engine.py:234`, `cvm_provider.py:195`: o alerta usa o primeiro LPA bruto por espécie, antes da validação de sinal e conflito; pode comparar contra um divulgado rejeitado para os métodos. Fechar usando a referência coerente.
- **ressalva** — `market_engine.py:238`, `data_quality.py:282`: para unit, compara o recalculado por ação com uma espécie isolada; não reconcilia LPAs distintos dos componentes. Fechar conferindo a composição ponderada.
- **ressalva** — `sentinela/data/acoes_cvm.py:327`: a comparação PN agrega todas as preferenciais, sem distinguir PNA/PNB do ticker. Fechar declarando ou abstendo a comparação quando as bases diferem.

## F2A-36 — `31f3dec`

- **ressalva** — a seleção do divulgado coerente e a soma ponderada da unit estão implementadas em `sentinela/data/acoes_cvm.py:139` e `:224`, mas o bloqueio do merge do F2A-3 impede garantir sua chegada aos métodos.
- **ressalva** — `cvm_provider.py:171`: o parser aceita somente `ON` e `PN` com até uma letra adicional; descrições por extenso são ignoradas. O efeito potencial está confirmado; a frequência real não foi medida. Fechar medindo as descrições efetivamente publicadas.
- **ressalva** — `market_engine.py:938`, `market_engine.py:972`: a escala usa o divulgado coerente, mas o detalhe do documento registra a referência bruta. Fechar registrando exatamente o valor e a classe usados na inferência.

## F2A-37 — `f760897`

- **bloqueia** — `sentinela/data/controladores.py:44`: “par sem correspondência” equivale a linha ausente e autoriza reserva, contrariando a D20 (`docs/adr/0003-validade-dados-metodo-auditoria.md:57`). Os testes cimentam essa interpretação em `tests/test_controladores.py:58` e `tests/test_contas_cvm_consumidores.py:157`. Fechar alinhando implementação e testes à decisão.
- **bloqueia** — `sentinela/data/controladores.py:87`: quando a linha dos controladores está ausente, retorna o lucro consolidado antes de verificar minoritários no balanço. Reproduzi lucro total 100 aceito com PL de minoritários 50. Fechar exigindo ausência de evidência de minoritários também nesse ramo.
- **ressalva** — `cvm_provider.py:124`: minoritários do balanço são lidos somente no modelo escolhido pelo setor, enquanto os três argumentos anteriores procuram em todos os modelos. Fechar tornando a conferência consistente.

## F2A-38 — `d4bdb11`

A leitura por código e descrição está implementada; permanece a violação posterior das reservas descrita no F2A-37. A diferença de base entre margem consolidada e ROE dos controladores está confirmada na decisão D abaixo.

## F2A-7 — `6f58193`

- **ressalva** — `cvm_provider.py:738`: o TTM lê diretamente as contas e não aplica a reserva validada do lucro dos controladores; linhas zeradas entram como zero e afetam a diferença trimestral. Fechar reutilizando a política aprovada ou registrando decisão específica.
- **ressalva** — `sentinela/data/series_cvm.py:265`: filtra encerramento do período, não disponibilidade pública até a data. Isso não comprova histórico estrito; fechar mantendo a distinção explícita da D17. O TTM hoje é informativo (`market_engine.py:880`).

## F2A-8 — `34dcfbf`

- **ressalva** — fórmula implementada em `sentinela/data/divida_liquida.py:94`: empréstimos circulantes + não circulantes − caixa − aplicações; EBITDA usa EBIT + módulo de D&A. A decisão A abaixo confirma o efeito favorável da abstenção no score.
- **ressalva** — `docs/decisoes/fontes-fase2a.md:60` registra arrendamentos fora dos grupos usados, sem esclarecer duplicidade; `divida_liquida.py:94` considera somente os grupos. A cobertura econômica de “arrendamento incluído” não está demonstrada para todos os emissores. Fechar reconciliando esses casos com documentos oficiais.

## F2A-9 — `aa8a2c5`

- **ressalva** — `sentinela/data/contas_cvm.py:26`, `:49`: somente setor normalizado exatamente como “bancos” seleciona o modelo bancário; holdings e intermediação financeira caem em empresa. Dados confirmados, escolha reservada ao Marcos.
- **ressalva** — `sentinela/data/providers/ifdata.py:51`, `:152`: IF.data guarda fonte/data-base, mas não o conjunto completo de proveniência da D16; o SHA no nome do cache identifica a requisição, não o conteúdo. Fechar completando ou delimitando expressamente o requisito.

## F2A-4 — `91335e7`

- **ressalva** — `brapi_provider.py:128`, `sentinela/data/normalizacao.py:126`, `market_engine.py:610`: DY finito, mas fora do intervalo dos motores, pode sobrescrever um DY válido anterior; só depois será rejeitado em `config.py:308`. Fechar definindo e testando a precedência diante de dado inválido.
- A conversão única por provedor e a retirada da conversão nos motores estão implementadas; a representação da brapi permanece uma inferência declarada.

## F2A-11 — `d0bd74f`

- **ressalva** — `market_engine.py:696`: o FII recebe VPA/P/VP da CVM, mas não registra `valores_por_fonte['CVM']`; a checagem cruzada pode continuar sendo uma identidade. Fechar registrando a entrega da fonte.
- **ressalva** — `cvm_fii_provider.py:152`: escolhe pela data de referência, sem desempatar por `Versao`. Informe reapresentado na mesma data pode produzir seleção errada. Fechar com ordenação determinística pela versão numérica.
- **ressalva** — `market_engine.py:745`: a etapa genérica acrescenta risco de falta de cobertura antes da consulta específica do FII; fechar emitindo o diagnóstico apropriado à classe.

## F2A-24 — `09150aa`

- **bloqueia** — `fii_engine.py:91`, `:156`: P/VP NaN ou infinito não passa pelo teste `<= 0`, a lente se abstém, mas o valor não finito permanece na saída. Contraria o aceite do item. Fechar saneando a saída e cobrindo esses dois valores.

## F2A-29 — `8e68a0c`

- **bloqueia** — `market_engine.py:490`, `:494` retorna sem preencher `classe_ativo` quando falta índice/registro; `valuation_engine.py:126` só aplica a guarda quando a chave existe. Ativo desconhecido pode receber métodos de ação. Fechar verificando o fluxo completo com índice ausente e ticker fora dele.

## F2A-13 — `b1322e1`

- **ressalva** — efeito nulo **refutado para a API de qualidade**: retirar `fundamentus` muda confiança de campo de **40 para 10**, não para zero; `data_quality.py:82` usa zero apenas para ordenar fontes, enquanto `:164` usa dez no relatório. Reproduzi score agregado 40 → 10 com dez campos presentes.
- **ressalva** — a mistura de limpeza, correções automáticas e comportamento está confirmada no diff; o resumo afirma “efeito nulo hoje” em `docs/loop/historico/fase-2a/pr-fase-2a.md:139` sem demonstrar todos os consumidores. Fechar corrigindo a alegação e isolando ou dispensando expressamente a mudança.
- As **185 remoções do golden são exatamente casos com `cvm`**; nenhum caso restante mudou nesse commit. As remoções estão previstas na fila (`fila.md:870`), portanto não as classifico, por si, como enfraquecimento indevido.

## F2A-15 — `8899611`

**ressalva** — `scripts/golden_diff.py:110`, `:132`: o predicado verifica somente mudanças de `saida` em IDs existentes; inclusões, remoções e alterações somente de entrada não reprovam automaticamente. Saída zero do comando não prova todo o aceite; fechar verificando também essas categorias.

## F2A-17 — `87a5a14`

Sem achado adicional na memoização inspecionada; a equivalência executada e as medições de desempenho não foram reproduzidas.

## F2A-18 — `0146785`

**ressalva** — `sentinela/data/providers/b3_cotahist.py:97`, `:246`: ZIP vazio gera `IndexError`, fora das exceções tratadas por mês; pode descartar toda a coleta em vez de registrar somente aquele mês ausente. Fechar com tratamento e regressão.

## F2A-16 — `0bb000b`

Sem achado adicional no vínculo declarado da amostra com mapas públicos; contagens e medições externas permanecem não verificadas.

## F2A-1 — `d31b207`

**ressalva** — `sentinela/data/referencia/registro.py:31`, `fontes.py:258`: índice antigo carrega campos novos com valores padrão e pode continuar válido pelo TTL; não há versão de esquema. Fechar demonstrando a reconstrução necessária ou invalidando esquemas incompatíveis.

## F2A-2 — `c1b0e70`

Sem achado adicional na propagação inspecionada de setor, segmento e controle; a classificação dos setores financeiros exige a decisão B.

## F2A-19 — `5499ef6`

Sem achado adicional na integração inspecionada; a cobertura real alegada do índice não foi reconstituída.

## F2A-20 — `486fb1e`

**ressalva** — `sentinela/services/asset_classifier.py:70`, `:73`: fora do índice, final 11 vira UNKNOWN e os demais códigos podem virar STOCK; o fallback não comprova classe oficial. Fechar em conjunto com a guarda do F2A-29.

## F2A-6 — `b2d5b56`

Sem achado adicional: `market_engine.py:478` preserva o retrato coletado e `data_quality.py:123` o sobrepõe aos campos alterados pelos motores.

## F2A-32 — `9a14e54`

**ressalva** — a estrutura temporal existe (`sentinela/data/proveniencia.py:38`), mas a cobertura não é universal: IF.data e métricas de liquidez não carregam todos os campos da D16 (`providers/ifdata.py:51`, `liquidez.py:76`). Fechar delimitando e completando os registros faltantes.

## F2A-33 — `212ee46`

Sem achado adicional no leitor: diferencia linha ausente, descrição divergente e valor inválido (`sentinela/data/contas_cvm.py:157`); o consumidor do F2A-37 desfaz essa distinção.

## F2A-34 — `9ed6af3` e revisões

A aritmética dos exemplos Petrobras/Taesa confere; autenticidade dos valores e documentos oficiais não foi novamente verificada.

## F2A-35 — `17603b6` e revisões

Sem achado adicional na origem pública declarada do universo; cobertura e situação atual de cada integrante não foram novamente verificadas.

## F2A-22 — `bbb5e12`

**ressalva** — `market_engine.py:471` usa a regra que considera prejuízo como ausência, acionando a penalização de fundamentos incompletos; o golden de motor isolado não cobre essa consequência da cascata. Fechar junto do bloqueio do F2A-3.

## F2A-30 — `b2518fe`

**ressalva** — `sentinela/data/normalizacao.py:121` impõe apenas teto superior; confirmei que −21 é aceito. O merge trata esse negativo de forma diferente conforme o caminho da fonte. A escolha do piso continua sendo a decisão C.

## F2A-21 — `08676ac`

Sem achado adicional: a ordem do motivo de abstenção do Bazin mudou, sem alteração da fórmula calculada.

## F2A-23 — `4092ef7`

**ressalva** — `fii_engine.py:95`, `:125`: retirada da vacância deixa de aplicar ajuste e penalidade, mas não acrescenta risco explícito de vacância indisponível; ausência pode favorecer a saída. Fechar com decisão documentada sobre sua apresentação.

## F2A-25 — `d173a12`

Sem achado adicional: Gordon exige LPA positivo, remove o payout padrão de 50% e registra versão 1.1.0; 217 casos existentes do golden mudam.

## F2A-12 — `399a408`

Sem achado adicional na validação inspecionada das entradas de cascata, URL da brapi e prompt; é validação de formato, não prova de existência do ativo.

## F2A-26 — `97fe57e`

- **ressalva** — `market_engine.py:462`, `cvm_download.py:29`: coleta síncrona pode esperar quatro meses × três tentativas × 60 segundos, aproximadamente **12 minutos**, além de processamento e backoff. Fechar medindo e limitando o impacto na interface.
- **ressalva** — `sentinela/data/liquidez.py:70`: meses ausentes podem coexistir com `incompleta=False` se houver datas suficientes nos outros meses. Fechar deixando explícita a diferença entre quantidade e continuidade da janela.

## F2A-31 — `c827920`

Sem achado adicional na retirada dos mapas da cascata; permanecem a guarda sem classe e o diagnóstico genérico aplicado a FII.

## F2A-27 — `c97453c`

**ressalva** — a documentação promete fechamento D−1, mas `market_engine.py:540` aceita `currentPrice` como reserva sem comprovar essa data-base. Fechar qualificando a promessa ou verificando o preço utilizado.

## F2A-28 — `1cd4bcf`

Sem achado adicional na condição de proposta; encaminhar bloqueios à 2B não os resolve nem equivale à dispensa escrita exigida pela D30.

## F2A-14 — `c05f4ed`

**ressalva** — o resumo confere nas contagens do golden, mas “ROE negativo passa” e “efeito nulo hoje” precisam das qualificações apontadas nos F2A-3/30 e F2A-13 (`pr-fase-2a.md:108`, `:139`).

## F2A-10 e F2A-39 — adiados

Sem implementação a aprovar nesta fase; o adiamento do BTG mantém exposição ao bloqueio de classificação fora do índice.

## Tickets incorporados e commits auxiliares

- **ressalva** — `108c406` tem mensagem de aumento de testes/mutação, mas **nenhum diff**; os testes aparecem em `eadbcf1`. A alegação do primeiro commit é falsa isoladamente; fechar corrigindo a rastreabilidade.
- `0ae9af8` altera temporariamente configuração do mutmut, restaurada em `c322bd3`; `0807395` adiciona `pr_description.md`, removido em `40da470`. Esses resíduos não permanecem no HEAD.
- O diff final de `tests/test_financeiro_pre_refactor.py` confirma somente as mudanças descritas nas seções B e C; a seção A permanece intacta.
- Não confirmei retrospectivamente que cada correção teve teste vermelho pelo motivo correto antes da implementação; mensagens e diário não bastam para provar isso.

## Nove achados do Gemini

| # | Resultado no HEAD | Evidência e limite |
|---|---|---|
| 1 | **Confirmado — bloqueia** | `market_engine.py:130`, `:179`, `:464`: valores não positivos descartados, possível preservação de fonte anterior e tratamento como ausência. |
| 2 | **Confirmado — bloqueia** | `controladores.py:44`, `:87`: descrição divergente autoriza reserva; reproduzido. |
| 3 | **Confirmado — bloqueia** | `fii_engine.py:91`, `:156`: NaN/inf de P/VP permanece na saída. |
| 4 | **Confirmado — bloqueia** | `market_engine.py:494`, `valuation_engine.py:126`: falta de classe contorna a guarda. O caso real BPAC11 depende do índice usado. |
| 5 | **Confirmado — ressalva** | `cvm_provider.py:738`: TTM lê conta diretamente, sem regra 7.2; consumidor atual informativo em `market_engine.py:880`. |
| 6 | **Confirmado — ressalva** | `market_engine.py:234`, `cvm_provider.py:195`: alerta usa divulgado anterior ao filtro de coerência. |
| 7 | **Confirmado — ressalva** | `market_engine.py:696`, `data_quality.py:246`: falta o registro por fonte necessário para identificar a identidade do FII. |
| 8 | **Confirmado com qualificação — ressalva** | `market_engine.py:745`: ocorre com provedor genérico presente e FII sem CD_CVM; “todo FII” é absoluto demais. |
| 9 | **Confirmado — ressalva** | `cvm_provider.py:120`: três leituras abrangem todos os modelos; minoritários do balanço usam somente o escolhido. |

## Dados das decisões A a D

Não decido nenhuma delas.

| Decisão | Dados confirmados |
|---|---|
| **A** | `divida_liquida.py:114` abstém a razão com EBITDA ≤ 0; `valuation_engine.py:279` converte ausência em zero para a penalização. Assim, não aplica os −15 de dívida elevada. |
| **B** | `contas_cvm.py:49` reconhece somente “bancos”; “Emp. Adm. Part. - Bancos” e “Intermediação Financeira” recebem modelo empresa. A adequação por emissor não foi demonstrada. |
| **C** | `normalizacao.py:121` não impõe piso: −21 permanece −21, equivalente a −2.100%. Sua chegada ao motor depende da fonte e do merge. |
| **D** | `cvm_provider.py:650` calcula margem com lucro consolidado; `:643` entrega ROE dos controladores. A saída não identifica explicitamente essa diferença de base. |

## Privacidade — checklist 8

Nas árvores de **todos os commits do intervalo**, não encontrei caminhos versionados em `data/` ou `outputs/`, `.env` real, bancos `.db`/`.sqlite*` ou arquivos `.pem`/`.key`. **`.env.example` está versionado e foi alterado**; seu conteúdo não foi lido.

A busca por formatos reconhecíveis de credenciais no HEAD, excluindo `.env*`, não encontrou ocorrências. Não encontrei evidência explícita de carteira privada nas buscas textuais; as amostras examinadas remetem a mapas públicos ou tickers sintéticos.

Isso não certifica ausência de qualquer segredo ou lista privada: formatos não reconhecidos, valores isolados e a origem pessoal de listas exigem outra forma de comprovação. Não li carteira, banco local ou credenciais para tentar estabelecer essa correspondência.

## Outros pontos do checklist

- **Vocabulário — ressalva:** o ramo novo de abstenção mantém `recomendacao: NEUTRO` (`fii_engine.py:118`), e o golden continua registrando rótulos direcionais. Há continuidade da interface antiga, mas não conformidade literal de todo código novo; fechar com exceção explícita ou adequação.
- **Testes — bloqueia no F2A-37:** há testes que afirmam comportamento contrário à D20. Mutation score elevado não corrige essa especificação errada.
- **Dependências:** o diff final remove `beautifulsoup4`; não encontrei nova dependência em `requirements.txt`.
- **SQL:** não identifiquei nova query SQL nos trechos alterados inspecionados.

## Recalculado por mim

Cálculos em memória, sem usar os resultados das funções como referência aritmética:

- **Petrobras**, números transcritos da ficha:  
  110.129.000.000 ÷ 12.888.732.761 = **8,544594883** de LPA recalculado;  
  415.786.000.000 ÷ 12.888.732.761 = **32,259649394** de VPA.
- **Taesa:** 1,52866 × 3 = **4,58598** de LPA divulgado por unit; 7.608.982.000 ÷ 1.033.497.000 × 3 = **22,087094592** de VPA.
- **Klabin:** 0,2286 × (1 + 4) = **1,1430** por unit. Isso confirma a multiplicação, não a autenticidade do insumo.
- **Alavancagem sintética:** 100 + 300 − 50 − 30 = **320**; EBITDA 100 + |−60| = **160**; razões **2,0** e **0,5** contra PL 640.
- **Merge:** suplementar cinco campos com −1 preservou todos os cinco valores positivos anteriores.
- **Confiança Fundamentus:** mesma entrada completa, código anterior/posterior ao F2A-13: **40 → 10**.
- **Reserva:** controladores ausentes, minoritários na DRE zero, consolidado 100 e minoritários no balanço 50 retornaram **100 com reserva**.

Conferência independente dos objetos Git do golden:

| Commit/item | Alterados | Incluídos | Removidos |
|---|---:|---:|---:|
| F2A-22 | 246 | 4 IDs renomeados | 4 IDs renomeados |
| F2A-4 | 236 | 0 | 0 |
| F2A-29 | 0 | 10 | 0 |
| F2A-11 | 6 | 0 | 0 |
| F2A-23 | 75 | 0 | 0 |
| F2A-24 | 0 | 7 | 0 |
| F2A-25 | 217 | 0 | 0 |
| F2A-13 | 0 | 0 | 185 |

Total: **2.247 → 2.079 linhas**, **1.015.082 → 927.404 bytes**. Todas as 185 remoções finais têm chave `cvm`. Essas contagens conferem com o resumo.

## Não verificado

- **Suíte verde:** pytest não coletou testes; falhou com `No usable temporary directory`. Ruff selecionado passou pela venv, sem cache.
- Mutation scores, execuções anteriores e sequência histórica vermelho → correção → PASS.
- Autenticidade e atualidade dos números oficiais transcritos nas fichas e fixtures; refiz a aritmética, não uma nova coleta externa.
- Contagens integrais de cobertura do índice, distribuição de liquidez e resultados das análises reais.
- Divergência **+402% da SBSP3**, valores reais do ROE da **CSAN3** e classificação efetiva de **BTCI11/TRPL11** no snapshot usado.
- Efeito nulo do F2A-13 em todos os consumidores reais. Para `DataQualityReport`, o efeito não é nulo.
- Ausência universal de segredos ou dados privados, especialmente em formatos não reconhecidos e conteúdos históricos intermediários.
- Equivalência integral de todos os caminhos de execução em cada commit intermediário; a inspeção mais profunda concentrou-se nas prioridades indicadas.

## Perguntas para o Marcos

1. Nas decisões **A a D**, qual política deve reger abstenção de alavancagem, modelos das financeiras, piso do ROE e declaração das bases da margem/ROE?
2. Os bloqueios serão corrigidos nesta fase ou haverá dispensa escrita individual, conforme D30? A proposta da 2B não substitui essa dispensa.
3. A reconstrução do índice e invalidação de fundamentos antigos serão condições de publicação/uso, já que esquemas antigos ainda carregam?
4. A ausência de vacância deve aparecer como limitação explícita na análise do FII?
5. Qual evidência oficial fechará os arrendamentos fora dos grupos de empréstimos e os casos SBSP3, BTCI11 e TRPL11?

## Dez maiores riscos

1. Prejuízo da CVM ser substituído por fundamento positivo de outra fonte.
2. Reserva consolidada ignorar evidência de minoritários e contrariar a D20.
3. Ativo sem classe oficial receber métodos de ação.
4. NaN/infinito de P/VP sair no resultado do FII.
5. Informe reapresentado ser escolhido sem considerar versão.
6. TTM usar lucro zerado sem a política aprovada de controladores.
7. Índice antigo continuar carregando sem classes preferenciais.
8. DY inválido de fonte posterior apagar DY válido anterior.
9. Alavancagem omitida ou incompleta favorecer silenciosamente a classificação.
10. Alegações de efeito nulo, proveniência e suíte verde excederem a evidência disponível.

**Veredito: não pode seguir.**

## Relatório do Gemini 4 Argon (2ª passada)

1. Modo e escopoModo: FASE (segunda passada complementar, combinada com modo DOCUMENTO sobre docs/loop/fila-fase2b-proposta.md e docs/loop/historico/fase-2a/pr-fase-2a.md).   Escopo: Branch v2/fase-2a em c05f4ed, cobrindo: (1) valuation_engine.py e todos os módulos de sentinela/** ausentes no corte da primeira passada; (2) tests/golden_motores.py e os testes de tests/test_liquidez.py até tests/test_valuation_escopo.py; (3) os três itens finais da Fase 2A (F2A-28 em 1cd4bcf, F2A-13 em b1322e1 e F2A-14 em c05f4ed); e (4) o delta sobre os achados da primeira passada (docs/loop/historico/fase-2a/auditoria-gemini-completa.md).   2. Tarefa 1 — Auditoria de valuation_engine.py e sentinela/**valuation_engine.pybloqueia — valuation_engine.py:274-320 e tests/test_valuation_engine.py:48-90: o rótulo "QUALIDADE — AGUARDAR" (elif score >= MACRO.REC_SCORE_FORTE and upside <= 0:) é matematicamente inalcançável em execução real porque, para $\text{upside} \le 0$, o termo sigmoide em valuation_engine.py:274 é sempre $\le 50$ e o único bônus positivo de qualidade é $+10$ (roe > MACRO.ROE_BONUS_MIN na linha 297), limitando score ao teto matemático de $60 < 75$ (REC_SCORE_FORTE), o que obrigou os testes em tests/test_valuation_engine.py:61, 83 a adulterarem math.exp com patch('valuation_engine.math.exp', return_value=0.2) (violando $e^x \ge 1$ para $x \ge 0$) para simular que a linha funciona; o que fecharia: decidir na Fase 2C (F2C-2/F2C-3) a regra real de "QUALIDADE — AGUARDAR" (separando qualidade de upside) e remover o mock artificial de math.exp.   ressalva — valuation_engine.py:48-70, 160-162, 175, 269, 297-298: float(dados.get('roe', 0) or 0), float(dados.get('pl', 0) or 0) e float(dados.get('pvp', 0) or 0) convertem None (campo abstido na cascata) em 0.0 (que entra tipado em MethodInputs como Ratio(0.0) / BRL(0.0) em vez de None, impedindo ValuationMethod.calcular de registrar "insumo ausente" e aplicando a penalidade de -15 no score por roe < ROE_PENALIDADE_MAX), ao passo que roe = float('nan') ou pl = float('nan') em dados avaliam nan < ROE_PENALIDADE_MAX e nan <= 0 como False, escapando das penalidades das linhas 269 e 298; o que fecharia: preservar None quando o insumo está ausente ou não finito antes de montar MethodInputs e tratar ausência de insumo separadamente de desempenho ruim no score (F2C-3).   ressalva — valuation_engine.py:55, 175: o motor ignora dados.get('lpa') e dados.get('vpa') já calculados pela CVM e sempre recalcula lpa = p / pl e vpa = p / pvp, perdendo precisão ou misturando fontes quando pl e pvp vêm de origens distintas na cascata; o que fecharia: ler lpa e vpa diretamente quando presentes e consistentes com a fonte do múltiplo, ou alimentar MethodInputs a partir dos valores por ação oficiais.   sentinela/data/acoes_cvm.pyressalva — sentinela/data/acoes_cvm.py:164-178: divulgados_coerentes não valida math.isfinite(valor) nem valor != 0; se a lista de uma classe contiver 0.0 ou float('nan') quando referencia < 0 (prejuízo), a comparação (referencia > 0) != (valor > 0) avalia False != False (False) e devolve LpaDivulgado(0.0) ou LpaDivulgado(nan), o que causaria ZeroDivisionError em market_engine.py:963 (preco / lpa); o que fecharia: rejeitar not math.isfinite(valor) or valor == 0 no início do laço de divulgados_coerentes.   ressalva — sentinela/data/acoes_cvm.py:196-256 e sentinela/data/referencia/montagem.py:42-67: parsear_acoes_por_unit normaliza qualquer componente preferencial ("2 PNA") para a chave "PN", e lpa_dos_metodos chama _lpa_da_classe(componente, componente, ...) passando classe="PN" e especie="PN"; isso faz (i) uma unit com varias_preferenciais=True aceitar a linha "PN" da DRE enquanto a ação avulsa PNA se abstém pela regra 3 da D19, e (ii) uma unit de companhia com classe única "PNA" (varias_preferenciais=False) procurar só ["PN", "PN"] em divulgados, ignorando o LPA divulgado em "PNA" e caindo no recalculado; o que fecharia: preservar a sigla da classe preferencial em parsear_acoes_por_unit (ou mapear para a classe única de classes_preferenciais) e alinhar a regra 3 entre ações avulsas e componentes de unit.   sugestão — sentinela/data/acoes_cvm.py:117-128 e 212: em inferir_escala, se lucro = float('nan') e lpa_divulgado < 0, (lucro > 0) != (lpa_divulgado > 0) dá False e só falha no fim por razao = nan; e em _lpa_da_classe (linha 212), preferencial = especie != "ON" trata especie = None como ação preferencial; o que fecharia: checar math.isfinite na entrada de inferir_escala e definir preferencial = bool(especie and especie != "ON").   sentinela/data/controladores.pybloqueia — sentinela/data/controladores.py:6, 44, 55, 66-116 e tests/test_market_engine_acoes_cvm.py:448-459: confirma diretamente o Achado 2 da primeira passada (_AUSENTE = (MOTIVO_LINHA_AUSENTE, MOTIVO_SEM_CORRESPONDENCIA) libera o lucro/PL consolidado total quando 3.11.01, 3.11.02 ou 2.03.09 têm outra descrição, violando a D20 do ADR-0003), e revela ainda que pl_dos_controladores (sentinela/data/controladores.py:106-107) retorna Resultado(None, motivo=None) mesmo quando pl_total falha por MOTIVO_VALOR_INVALIDO (NaN) ou MOTIVO_LINHAS_DIVERGENTES, ocultando o erro sob MOTIVO_ROE_SEM_PL; o que fecharia: restringir _AUSENTE a (MOTIVO_LINHA_AUSENTE,), propagar MOTIVO_PL_INVALIDO quando _invalida(pl_total) for verdadeiro e incluir tests/test_market_engine_acoes_cvm.py:448-459 nos testes a atualizar no F2B-9.   ressalva — sentinela/data/controladores.py:87-93: quando controladores e nao_controladores são zero e pl_nao_controladores é Abstencao(MOTIVO_VALOR_INVALIDO) (NaN na conta 2.03.09), a linha 91 (if not _ausente_ou_zerada(pl_nao_controladores):) devolve MOTIVO_LUCRO_NAO_SEPARADO ("com não controladores no balanço") em vez de MOTIVO_LUCRO_INVALIDO, além de a linha 87-88 (if _ausente(controladores):) não checar pl_nao_controladores; o que fecharia: testar if _invalida(pl_nao_controladores): return Resultado(None, motivo=MOTIVO_LUCRO_INVALIDO) antes da linha 87 e exigir _ausente_ou_zerada(pl_nao_controladores) também quando _ausente(controladores).   sentinela/data/contas_cvm.py e sentinela/data/referencia/contas_cvm.csvressalva — sentinela/data/referencia/contas_cvm.csv:40-41 e sentinela/data/contas_cvm.py:145-165: as linhas 40 e 41 cadastram 3.09.01 e 3.09.02 no modelo empresa (usando o BANCO NACIONAL S.A. como evidência, contradizendo o próprio diario.md:259 que vedava pares de banco no modelo de empresa); num emissor não financeiro (empresa) em que 3.11.01 esteja ausente e 3.09.01 exista como subconta de 3.09 Resultado Líquido das Operações Continuadas com outra descrição, ler_conta registra 3.09.01 em divergentes e devolve MOTIVO_SEM_CORRESPONDENCIA em vez de MOTIVO_LINHA_AUSENTE; o que fecharia: remover 3.09.01 e 3.09.02 do modelo empresa em contas_cvm.csv e tratar emissores bancários sem setor via detecção de plano contábil ou na tabela de correções.   ressalva — sentinela/data/contas_cvm.py:145-163 e sentinela/data/referencia/contas_cvm.csv:15-24, 32-39: em modelos com múltiplos códigos candidatos para o mesmo campo (banco com 2.07/2.08 e 3.11/3.09; seguradora com 3.05/3.07 e 3.11/3.13), quando o código do primeiro submodelo existe no documento com a descrição normal de outra conta daquele submodelo (ex.: 3.05 é "Outras Receitas e Despesas Operacionais" na BBSE3, ou 2.07 é passivo no ITUB4) e o código do segundo submodelo (3.07 ou 2.08) está ausente no documento, divergentes acumula o primeiro código e ler_conta retorna MOTIVO_SEM_CORRESPONDENCIA em vez de MOTIVO_LINHA_AUSENTE; o que fecharia: separar submodelos ou só classificar como MOTIVO_SEM_CORRESPONDENCIA quando a descrição divergente não for uma conta conhecida de outro campo do mesmo modelo.   sugestão — sentinela/data/referencia/contas_cvm.csv:11-12, 21-24, 34-35: a variação "atribuido aos socios..." (com "aos") só está cadastrada em banco (3.11.01/3.11.02), mas não em empresa nem em seguradora (inclusive um teste em tests/test_market_engine_acoes_cvm.py:442 usa "Atribuído aos Sócios não Controladores" em uma empresa); o que fecharia: aceitar a preposição "a"/"aos" na normalização ou cadastrar o par nos modelos caso ocorra nas DFPs.   sentinela/data/series_cvm.pyressalva — sentinela/data/series_cvm.py:219-220, 253: _meses(inicio, fim) calcula (fim.year - inicio.year) * 12 + fim.month - inicio.month + 1 ignorando inicio.day e fim.day; um intervalo de 37 dias (2025-01-25 a 2025-03-02) dá _meses == 3 e vira um trimestre válido, enquanto um trimestre fiscal de 3 meses fora do dia 1º (2025-01-15 a 2025-04-14) dá _meses == 4 e é descartado; o que fecharia: validar a duração real do trimestre (ou relativedelta / janela de dias compatível com um trimestre contábil) além da diferença de meses civis.   ressalva — sentinela/data/series_cvm.py:85-89, 283: proventos(dividendos, jcp) retorna None se dividendos is None or jcp is None; se uma companhia declarar apenas dividendos na DVA e não tiver a linha de JCP (ou vice-versa) em qualquer um dos documentos da série ou do TTM, proventos inteiros ficam None; o que fecharia: somar a parcela presente quando a outra estiver ausente por MOTIVO_LINHA_AUSENTE (sem erro de leitura/correspondência).   sugestão — sentinela/data/series_cvm.py:102-106, 148-149: _por_acao não usa o fallback _linhas_de_lpa do market_engine.py e sobrescreve o motivo específico de abstenção do PL dos controladores (MOTIVO_PL_COM_MINORITARIOS / MOTIVO_PL_INVALIDO) com MOTIVO_ROE_SEM_PL; o que fecharia: propagar o motivo de pl_controladores vindo de ind.   sentinela/data/divida_liquida.pyressalva — sentinela/data/divida_liquida.py:83-99: medir exige Leitura presente nas 4 contas de CAMPOS_DA_DIVIDA (2.01.04, 2.02.01, 1.01.01, 1.01.02) e acessa contas[campo] diretamente na linha 85 (levantando KeyError se a chave faltar no dicionário); se uma companhia sem dívida bancária ou sem aplicações financeiras omitir uma dessas subcontas de 3º nível no balanço (MOTIVO_LINHA_AUSENTE), a alavancagem inteira se abstém em vez de tratar subconta ausente (com grupo pai presente) como zero; o que fecharia: usar contas.get(campo) com segurança e verificar na DFP quantas companhias omitem 1.01.02, 2.01.04 ou 2.02.01 quando o saldo é zero.   sentinela/data/liquidez.py e sentinela/data/providers/b3_cotahist.pyressalva — sentinela/data/liquidez.py:48-75: if not volume: return Abstencao(MOTIVO_TICKER_AUSENTE) testa volume em todo o iterável de 4 meses antes do recorte ordenados[-tamanho:]; se um papel mudou de código ou deixou de negociar há 64 pregões (tendo 1 negócio no 1º mês da coleta e 0 nos últimos 63 pregões), ele não se abstém e sai com volume_mediano = 0.0 e presenca = 0.0 nas janelas de 21 e 63 pregões; o que fecharia: definir na decisão [LIQUIDEZ] se ausência total de negócios dentro da janela (presenca == 0) é abstenção ou liquidez zero.   ressalva — sentinela/data/providers/b3_cotahist.py:96-100, 146-149, 246-251: ler_zip faz zf.namelist()[0] sem tratar ZIP vazio (IndexError escapa do try/except de HistoricoRecente.coletar nas linhas 246-251), e baixar_mes retorna sem validação qualquer arquivo já existente em disco se _completo for True (mesmo que o ZIP tenha sido corrompido); o que fecharia: incluir IndexError no except de coletar (ou validar namelist() em ler_zip levantando BadZipFile).   sentinela/data/normalizacao.py, sentinela/data/proveniencia.py e sentinela/data/providers/ifdata.pybloqueia — sentinela/data/providers/ifdata.py:51-58, 152-178: o IFDataProvider (criado no F2A-9, após o ADR-0003) viola dois requisitos obrigatórios do projeto: (i) não registra a proveniência temporal da D16 (ADR-0003: data_coleta, data_entrega/motivo_sem_entrega, hash_sha256 e arquivo lateral .proveniencia.json) para os arquivos JSON baixados em data/ifdata/ nem no objeto Capital, e (ii) chama time.time() diretamente na linha 159 em vez de usar a data_referencia recebida por parâmetro, além de gravar em cache por 7 dias respostas vazias [] de trimestres ainda não publicados pelo BCB (09/2026); o que fecharia: registrar a proveniência de D16 nos arquivos de data/ifdata/, medir o TTL contra o instante de referência recebido e não cachear resposta vazia de cadastro como definitiva por 7 dias.   ressalva — sentinela/data/proveniencia.py:157-170, 207: registrar_arquivo usa arquivo temporário fixo (lateral.name + ".tmp") que sofre condição de corrida entre threads do peers_engine, e entrega_no_indice compara str(linha.get(k)) == str(v) sem .strip(), falhando se o CSV contiver espaços em CNPJ_CIA, DT_REFER ou VERSAO; o que fecharia: aplicar .strip() em entrega_no_indice e incluir sufixo por thread/PID ou trava em registrar_arquivo.   sentinela/data/referencia/** e sentinela/services/asset_classifier.pyressalva — sentinela/data/referencia/montagem.py:321-351, 429 e sentinela/services/asset_classifier.py:61-73: montar_outros grava qualquer cota de fundo (ESPECI começando por "CI") sem Informe Mensal recente como classe = "UNKNOWN" (regra = "cotahist:cota_de_fundo"), e AssetClassifier.classify retorna esse UNKNOWN na linha 63 antes de consultar UNITS_CONHECIDAS e FIIS_CONHECIDOS (tirando BTCI11 do motor de FII); além disso, conhecidos na linha 429 inclui apenas exc_repetidos, deixando de fora exc_companhias e exc_fiis (um FII sem ISIN válido no Informe entra tanto em excecoes quanto em registros como UNKNOWN via montar_outros); o que fecharia: incluir os códigos de exc_companhias e exc_fiis em conhecidos e decidir se cotahist:cota_de_fundo (UNKNOWN) deve prevalecer sobre FIIS_CONHECIDOS/UNITS_CONHECIDAS.   sugestão — sentinela/data/referencia/montagem.py:150-165, 221 e sentinela/data/referencia/correcoes.py:39-52: montar_companhias não aplica .upper() em classe_preferencial na linha 221 (enquanto classes_preferenciais_por_cnpj aplica na linha 164), e validar_correcoes não valida FORMATO_TICKER.match(correcao.ticker) nem unicidade de ticker entre linhas de correcoes.csv; o que fecharia: aplicar .upper() em classe_preferencial e validar formato e unicidade de ticker em validar_correcoes.   sentinela/methods/**ressalva — sentinela/methods/graham.py:42, 58-73 e sentinela/methods/fii_nav.py:39-54: quando os métodos são chamados diretamente (fora dos motores da V1), Graham._calcular valida pl > 0 and pvp > 0 mas não valida inputs.vpa.valor > 0 nem inputs.preco.valor > 0 (se vpa < 0 e preco > 0, (... * vpa) ** 0.5 gera um complex e math.isfinite(valor) lança TypeError: must be real number, not complex), e FiiNav._calcular classifica pvp <= 0 como FAIXA_DESCONTO ("desconto sobre o patrimônio") porque a abstenção do F2A-11 foi colocada apenas em fii_engine.py e não no método FiiNav; o que fecharia: validar preco > 0 e vpa > 0 em Graham._calcular (e preco > 0 em Bazin, Gordon, Lynch, FiiYield) e abster FiiNav._calcular quando pvp <= 0.   sentinela/reports/rastreabilidade.pybloqueia — sentinela/reports/rastreabilidade.py:66-72, 233-250, 390-395 e tests/test_rastreabilidade.py:230-232: o relatório de rastreabilidade afirma duas inverdades factuais sobre o que o código da Fase 2A faz: (i) nas linhas 390-395 (e no teste test_pvp_ausente_do_fii_e_sinalizado), declara para FII sem P/VP que "; ausente: o motor usa P/VP = 1,0 (sem CVMFIIProvider injetado)", quando o F2A-11 trocou 1,0 por abstenção (None) e o F2A-13 removeu a injeção de CVMFIIProvider de FIIEngine; e (ii) nas linhas 66-72 e 233-250, declara para ações com P/L da CVM que o LPA e o P/L foram calculados por "lucro dos controladores ÷ N ações da Composição do Capital (...; ações do fim do período)", quando desde o F2A-36 (D19) o LPA dos métodos e o P/L vêm do LPA básico divulgado na DRE (3.99.01.x, média ponderada) e, quando a escala é indeterminada (acoes_cvm ausente), _proveniencia_derivada omite que o LPA veio da CVM; o que fecharia: atualizar rastreabilidade.py:66-72, 233-250, 390-395 e tests/test_rastreabilidade.py:230-232 para refletirem o F2A-11, o F2A-13 e o F2A-36 (dados['lpa_cvm']).   3. Tarefa 2 — Auditoria dos testes (tests/golden_motores.py e tests/test_liquidez.py em diante)bloqueia — tests/test_valuation_engine.py:48-90 (test_recomendacao_compra_forte_exige_upside e test_recomendacao_qualidade_aguardar): ambos os testes usam patch('valuation_engine.math.exp', return_value=0.2) para forçar um score $\ge 75$ com $\text{upside} < 0$, mascarando o fato de que o ramo "QUALIDADE — AGUARDAR" em valuation_engine.py:319-320 é código morto matematicamente inalcançável; o que fecharia: remover o patch de math.exp e corrigir a regra de score/classificação na Fase 2C.   ressalva — tests/test_macro_context.py:95-100, 114-119 (test_ipca_12m_fallback_on_error e test_ntnb_fallback_on_error): ambos são mocks que testam o próprio mock (item 3 do checklist) — substituem _fetch_ipca_acumulado e _fetch_ntnb por lambda: IPCA_12M_FALLBACK e lambda: NTNB_LONGA_FALLBACK e afirmam que a propriedade devolve a constante, sem nunca exercitar o tratamento de exceção dentro dos fetchers; o que fecharia: simular falha em requests.get (ex.: ConnectionError) e verificar que _fetch_ipca_acumulado e _fetch_ntnb capturam o erro e devolvem o fallback.   ressalva — tests/test_technical_engine.py:12-27 (test_technical_engine_valid_history) e tests/test_valuation_engine.py:184-232 (test_divida_liq_ebitda_brazilian_format etc.): asserts triviais — test_technical_engine_valid_history apenas checa presença de chaves e se tendencia pertence à lista de todas as 5 strings possíveis (inclusive 'Baixa' e 'Indefinida' para uma reta crescente), e test_divida_liq_ebitda_brazilian_format passa "1.234,56" mas só checa 0 <= result['score_final'] <= 100 (passaria mesmo se o parser falhasse e zerasse a dívida); o que fecharia: afirmar os valores numéricos calculados e a presença de "Dívida elevada" em result['riscos'] quando divida_liq_ebitda = "1.234,56".   ressalva — tests/test_methods_gordon.py:39-70 e tests/test_methods_lynch.py:42-67: test_formula_igual_a_da_v1 e test_mesma_ordem_de_operacoes_da_v1 calculam o valor esperado chamando uma função local _v1(...) copiada linha por linha do próprio método (em test_methods_gordon.py:41, _v1 ainda conserva o fallback else 0.5 removido no F2A-25); o que fecharia: substituir _v1 por valores esperados calculados de forma independente na ficha metodológica (previsto para F2B-1 e F2C-1, D28).   ressalva — tests/test_market_engine.py:517-595 e tests/test_rastreabilidade.py:230-232: test_manual_fii_fallback_never_overwrites_fresh_provider_values ficou inócuo após o F2A-23 (pois a cascata não chama mais _aplicar_fallback_manual_fii), test_market_engine_manual_fii_fallback_does_not_apply_to_known_unit chama diretamente o método morto _aplicar_fallback_manual_fii, e test_pvp_ausente_do_fii_e_sinalizado exige o texto obsoleto "o motor usa P/VP = 1,0"; o que fecharia: limpar os testes de fallback manual no F2C-10 e atualizar test_pvp_ausente_do_fii_e_sinalizado.   4. Tarefa 3 — Auditoria dos três itens novos (F2A-13, F2A-14 e F2A-28)F2A-13 · b1322e1 · chore: clean up phase 2A residueressalva — docs/loop/historico/fase-2a/diario.md:860-900, docs/loop/historico/fase-2a/pr-fase-2a.md:139 e docs/limpeza/inventario.md:299-326: o commit b1322e1 misturou 82 correções automáticas de estilo/tipagem (ruff UP045, UP006, I001) com remoções de contrato/comportamento (MethodInputs sem erro_scraper, FIIEngine sem cvm_provider, remoção de "fundamentus": 40 em data_quality.py e remoção de 185 casos do golden), seguindo o próprio texto prescrito em fila.md:867-892; sobre a pergunta se o efeito é nulo: em execuções novas de produção via app.py após limpar o cache, o efeito nos números dos motores é nulo (pois FIIEngine() já rodava sem provedor no app.py, VACANCIA_CONHECIDA já fora desligada no F2A-23 e fundamentus saiu no F2A-22), mas não é nulo se DataQualityReport.confianca() avaliar um registro do fundamentals_cache gravado antes do F2A-22 ou uma análise histórica salva com fonte_fundamentos = "fundamentus" (cuja nota de confiança da fonte cai de 40 para 0), além de F2A-13 ter deixado para trás a referência a "sem CVMFIIProvider injetado" em sentinela/reports/rastreabilidade.py:394; o que fecharia: limpar o fundamentals_cache no checkpoint (passo 4 do [DECISÃO]), remover o texto obsoleto de rastreabilidade.py:390-395, 411 e, nas próximas fases (F2B-5), não incluir mudanças de golden/comportamento em commits chore:.   F2A-14 · c05f4ed · docs: add phase 2A summary and archive loop files (pr-fase-2a.md)ressalva — docs/loop/historico/fase-2a/pr-fase-2a.md:54 e AGENTS.md:11: pr-fase-2a.md:54 afirma "1.343 passed + 1 skipped + 1 xfailed no fim, em 76 módulos de teste", e AGENTS.md:11 afirma "Suíte: ~1.360 testes, 76 módulos em tests/", mas o F2A-13 removeu o arquivo tests/test_cvm_ticker_map.py (diario.md:882), reduzindo o total de módulos de teste de 76 para 75 (e a contagem de testes de 1.362 para 1.343, que ficou desatualizada no AGENTS.md:11); o que fecharia: corrigir "76 módulos" para "75 módulos" em pr-fase-2a.md:54 e AGENTS.md:11 (e atualizar ~1.360 para ~1.340 em AGENTS.md:11).   F2A-28 · 1cd4bcf · Proposta da fila da Fase 2B (docs/loop/fila-fase2b-proposta.md)bloqueia — docs/loop/fila-fase2b-proposta.md:385-386, 496 e docs/loop/historico/fase-2a/diario.md:849: F2B-23 e F2B-1 decidem pelo texto a fórmula de crescimento real do Gordon como g real = (1 + g nominal) ÷ (1 + inflação) − 1 com g nominal = ROE × retenção (sem deflacionar o ROE por Fisher e sem colocá-lo como opção em [TAXA]), enquanto F2B-26 (:417, lente de bancos) exige converter também o ROE por Fisher ($\text{ROE}_{\text{real}} = (1 + \text{ROE}_{\text{nom}}) / (1 + \pi) - 1$); além da incoerência entre F2B-23 e F2B-26, deflacionar $g_{\text{nom}} = \text{ROE} \times b$ pela inflação inteira produz $g_{\text{real}} < 0$ sempre que $\text{ROE} \times b < \pi$ (ex.: $-0,66\%$ a.a. perpétuo para uma empresa lucrativa que retém $40\%$ do lucro com $\text{ROE} = 12\%$ e $\pi = 5,5\%$); o que fecharia: transformar a definição de $g_{\text{real}}$ no Gordon em decisão explícita do Marcos na ficha F2B-23 / [TAXA] (comparando: (i) $(1 + \text{ROE} \cdot b)/(1+\pi) - 1$, (ii) $\text{ROE}_{\text{real}} \cdot b$ mantendo o poder de compra dos ativos existentes, ou (iii) crescimento real limitado/ancorado).   ressalva — docs/loop/fila-fase2b-proposta.md:142, 187, 428, 455, 570-573, 661, 663, 678: cinco problemas estruturais/de aceite verificável na proposta da 2B:   F2B-27 (:428) vem antes do marcador [DECISÃO] (:455), mas depende da decisão sobre os nomes "taxa de compra" / "taxa de venda" que está em [TAXA] no próprio marcador (:142), garantindo bloqueio [!];   F2B-9 (:187) omite tests/test_market_engine_acoes_cvm.py::test_sem_linha_da_controladora_vale_o_lucro_total (tests/test_market_engine_acoes_cvm.py:448-459) da lista de "Testes que mudam", o que fará a suíte quebrar na lacuna 1;   F2B-5 (:663) inclui mudança de comportamento com regeneração de golden (**[golden]**, remoção do parser de divida_liq_ebitda em texto no valuation_engine.py:278-291) dentro de um commit chore: de limpeza, contrariando o item 7 do checklist;   F2B-5 (:661, 678) exige git grep vazio fora de docs/ para GORDON_PREMIO_RISCO, BAZIN_TAXA_MIN e ntnb_longa, mas scripts/dossie_fase2.py lê os três nomes e não está listado para edição/remoção no item;   F2B-4 (:570-573) exige --onde "False" no golden (zero casos existentes alterados), o que falhará se a limitação "sem setor" for gravada em riscos pelo ValuationEngine em vez da cascata;
o que fecharia: corrigir esses cinco pontos em docs/loop/fila-fase2b-proposta.md antes de ativar a Fase 2B.   ressalva — docs/loop/fila-fase2b-proposta.md:745-762, 815-821 vs docs/loop/historico/fase-2a/auditoria-gemini-completa.md:34: a proposta da 2B omitiu (tanto dos itens da 2B quanto da lista de pendências para a 2C nas linhas 815-821) cinco ressalvas da primeira passada: (i) QT_ACAO_TOTAL_TESOURO = 0 ignorando tesouraria_on + tesouraria_pn em cvm_provider.py:209-212; (ii) falta de filtro GRUPO_DFP e guarda de VERSAO em cvm_provider._dados_por_acao; (iii) divergencia_acoes comparando PN total (PNA + PNB) com classe única do yfinance em companhias com múltiplas preferenciais (USIM5, BRSR5, BRSR6); (iv) DataQualityReport.completude() penalizando bancos e FIIs por campos proibidos pelo próprio modelo (receita_liquida, margem_liquida, divida_liq_ebitda); e (v) BTCI11/TRPL11 dentro do índice como UNKNOWN/FII via montar_outros (que o F2B-15 não resolve porque só atua fora do índice); o que fecharia: registrar explicitamente o destino dessas cinco ressalvas na tabela [AUDITORIA] ou nas pendências da 2C em fila-fase2b-proposta.md.   5. Tarefa 4 — Achados da primeira passada que mudam à luz do código agora visívelAchado 2 (controladores.py e reserva em MOTIVO_SEM_CORRESPONDENCIA): confirmado diretamente e ampliado — sentinela/data/controladores.py:44 define _AUSENTE = (MOTIVO_LINHA_AUSENTE, MOTIVO_SEM_CORRESPONDENCIA), tests/test_market_engine_acoes_cvm.py:448-459 também fixa esse comportamento (além dos dois arquivos de teste citados na 1ª passada), e sentinela/data/controladores.py:106-107 descarta o motivo de erro quando pl_total é inválido (NaN).   Achado 4 (Ativos fora do escopo recebendo métodos de ação): confirmado diretamente e ampliado — valuation_engine.py:125-138 só lê dados.get('classe_ativo'); sentinela/services/asset_classifier.py:61-73 devolve STOCK para qualquer ticker não terminado em "11" quando o índice está ausente (ex.: BDR AAPL34), e devolve UNKNOWN para cotas de fundo presentes em montar_outros (sentinela/data/referencia/montagem.py:342-350, como BTCI11), bloqueando o fallback para FIIS_CONHECIDOS.   Achado 1 (Indicadores <= 0 ou abstidos na cascata): ampliado no motor — valuation_engine.py:160-162, 269, 297-298 converte roe = None (abstido) em 0.0 e penaliza o score em -15, enquanto roe = float('nan') e pl = float('nan') escapam das penalidades de ROE baixo e de "Dados incompletos".   Itens não verificados na 1ª passada (F2A-12, F2A-21, F2A-25, b3_cotahist.py, ifdata.py, rastreabilidade.py): F2A-12 (sentinela/domain/ticker.py), F2A-21 (sentinela/methods/bazin.py) e F2A-25 (sentinela/methods/gordon.py) estão confirmados sem ressalvas novas; já ifdata.py e rastreabilidade.py apresentaram os dois bloqueios novos reportados na Tarefa 1 acima.   6. Recalculado por mimTaesa (TAEE11) — Exemplo independente da ficha (docs/metodologia/por-acao.md:105-123 e tests/test_market_engine_acoes_cvm.py:772-790):   Lucro dos controladores (3.11.01, escala MIL): $1.579.863 \times 1.000 = \text{R\$ } 1.579.863.000$.   Total de ações na Composição do Capital: $590.714\ (\text{ON}) + 442.783\ (\text{PN}) - 0 = 1.033.497$.   Inferência de escala contra LPA básico divulgado ($\text{ON} = \text{PN} = 1,52866$):
   $$\text{LPA}_{\text{unidade}} = \frac{1.579.863.000}{1.033.497} = 1.528,65756 \implies \text{Razão} = 999,998 \notin [0,1;\ 10]$$$$\text{LPA}_{\text{mil}} = \frac{1.579.863.000}{1.033.497.000} = 1,52865756 \implies \text{Razão} = 0,9999984 \in [0,1;\ 10] \implies \text{Escala MIL}$$LPA da unit (1 ON + 2 PN, regra 4 da D19): $1 \times 1,52866 + 2 \times 1,52866 = \text{R\$ } 4,58598$ (confere com 4,58598).   VPA por ação e VPA da unit (2.03 = 7.608.982 mil, 2.03.09 = 0):
   $$\text{VPA}_{\text{ação}} = \frac{7.608.982.000}{1.033.497.000} = \text{R\$ } 7,36236486 \implies \text{VPA}_{\text{unit}} = 3 \times 7,36236486 = \text{R\$ } 22,0870946 \approx \text{R\$ } 22,087$$
Confere com por-acao.md:121 e test_market_engine_acoes_cvm.py:789.   Inacessibilidade matemática de "QUALIDADE — AGUARDAR" (valuation_engine.py:274-320):   Para qualquer $\text{upside } u \le 0$, com $A = \text{SCORE\_SIGMOID\_AMPLITUDE} > 0$ e $k = \text{SCORE\_SIGMOID\_INCLINACAO} > 0$:$$-u \cdot k \ge 0 \implies e^{-u \cdot k} \ge 1 \implies \frac{2}{1 + e^{-u \cdot k}} - 1 \le 0 \implies \text{score}_{\text{base}} = 50 + A \cdot \left(\frac{2}{1 + e^{-u \cdot k}} - 1\right) \le 50$$Como o único ajuste positivo em valuation_engine.py:292-309 é $+10$ (roe > MACRO.ROE_BONUS_MIN), tem-se $\text{score}_{\text{final}} \le 50 + 10 = 60 < 75 = \text{REC\_SCORE\_FORTE}$ para todo $u \le 0$.   Gordon no regime real — verificação da conta do diário do F2A-28 (diario.md:849) e sensibilidade à definição de $g_{\text{real}}$:   Com $P = 100$, $\text{LPA} = 10$, $\text{DY} = 0,06 \implies D_0 = 6$, $\text{payout} = 60\%$, $\text{retenção } b = 40\%$, $\text{ROE} = 12\%$, $\text{NTN-B} = 7\%$, $\text{prêmio} = 5\% \implies k_{\text{real}} = 12\%$, $\text{IPCA } \pi = 5,5\%$:   Fórmula pré-fixada em F2B-23/F2B-1 ($g_{\text{nom}} = 0,12 \times 0,40 = 4,8\%$, deflacionando $g_{\text{nom}}$ pela inflação total):$$g_{\text{real}} = \frac{1,048}{1,055} - 1 = -0,006635\ (-0,6635\%) \implies D_1 = 6 \times \frac{1,048}{1,055} = 5,96019$$$$\text{Valor} = \frac{5,96019}{0,12 - (-0,006635)} = \frac{5,96019}{0,126635} = \text{R\$ } 47,0659$$
(Equivalente por Fisher a descontar dividendos nominais crescendo a $4,8\%$ por $k_{\text{nom}} = 1,12 \times 1,055 - 1 = 18,16\%$: $\frac{6 \times 1,048}{0,1816 - 0,048} = \text{R\$ } 47,0659$ ✓).   Fórmula alternativa consistente com F2B-26 (convertendo $\text{ROE}$ por Fisher, $\text{ROE}_{\text{real}} = \frac{1,12}{1,055} - 1 = 6,1611\%$, e aplicando a retenção $b = 40\%$):$$g_{\text{real}} = 0,061611 \times 0,40 = +0,024645\ (+2,4645\%) \implies \text{Valor} = \frac{6 \times 1,024645}{0,12 - 0,024645} = \text{R\$ } 64,4734\ (+37,0\%)$$7. Não verificadoArtefatos locais fora do git e execução ao vivo: arquivos brutos em data/cvm/, data/cotahist/, data/ifdata/ e data/referencia/indice.json, scripts temporários em outputs/, banco SQLite local e execução de comandos (pytest, mutmut, ruff, vulture, deptry) não puderam ser rodados diretamente por se tratar de auditoria estática somente leitura sobre os arquivos anexados.   Código-fonte de scripts/levantamento_fase2a.py e scripts/golden_diff.py: embora listados no histórico, seus corpos não constam em 2-codigo.txt (que começa em valuation_engine.py e sentinela/**).   8. Perguntas para o MarcosDefinição de $g_{\text{real}}$ no Gordon em regime real (docs/loop/fila-fase2b-proposta.md:385-386, 496):   Contexto: A proposta da 2B fixa no texto de F2B-23 e F2B-1 que $g_{\text{real}} = \frac{1 + \text{ROE} \times (1 - \text{payout})}{1 + \text{inflação}} - 1$. Isso abate a inflação inteira sobre a parcela retida do lucro, gerando crescimento real negativo perpétuo sempre que $\text{ROE} \times b < \text{IPCA}$ (ex.: $-0,66\%$ a.a. no caso A1, valor justo $\text{R\$ } 47,07$), enquanto na ficha de bancos (F2B-26, :417) o ROE é convertido por Fisher ($\text{ROE}_{\text{real}} = \frac{1+\text{ROE}}{1+\pi}-1$), o que daria $g_{\text{real}} = \text{ROE}_{\text{real}} \times b = +2,46\%$ ($\text{R\$ } 64,47$).   Opções: (a) Colocar as duas formulações de $g_{\text{real}}$ (e o teto de $g_{\text{real}}$) como decisão aberta [DECISÃO] na ficha docs/metodologia/gordon.md (F2B-23) antes de implementar o F2B-1; ou (b) manter apenas a fórmula já escrita em F2B-23.   Rótulo "QUALIDADE — AGUARDAR" inalcançável no ValuationEngine (valuation_engine.py:274-320 e tests/test_valuation_engine.py:48-90):   Contexto: Com a curva sigmoide atual, todo ativo com $\text{upside} \le 0$ tem $\text{score} \le 60 < 75$ (REC_SCORE_FORTE), tornando "QUALIDADE — AGUARDAR" código morto em produção.   Opções: (a) Tratar na Fase 2C (F2C-2 / F2C-3, quando qualidade e valuation forem separados pela D24); ou (b) ajustar a condição já na Fase 2B.   Pares 3.09.01 e 3.09.02 cadastrados no modelo empresa (sentinela/data/referencia/contas_cvm.csv:40-41):   Contexto: Em companhias não financeiras (empresa), 3.09 é Resultado Líquido das Operações Continuadas, mas 3.09.01 e 3.09.02 foram incluídos no modelo empresa por causa do BANCO NACIONAL S.A. (banco sem setor no FCA).   Opções: (a) Remover 3.09.01 e 3.09.02 do modelo empresa em contas_cvm.csv e identificar bancos sem setor pelo plano contábil (2.07/2.08) na decisão [FINANCEIRAS] (opção c); ou (b) mantê-los no modelo empresa.   Cotas de fundo em montar_outros (UNKNOWN) sobrepondo FIIS_CONHECIDOS e UNITS_CONHECIDAS (sentinela/data/referencia/montagem.py:321-351 e sentinela/services/asset_classifier.py:61-70):   Contexto: BTCI11 (FII sem Informe em 2025/2026) entra no índice por montar_outros como UNKNOWN (cotahist:cota_de_fundo), o que impede AssetClassifier de usar o fallback FIIS_CONHECIDOS.   Opções: (a) Permitir que UNITS_CONHECIDAS e FIIS_CONHECIDOS tenham precedência sobre a regra residual cotahist:cota_de_fundo (UNKNOWN), ou incluir BTCI11/TRPL11 na tabela de correções com evidência do cadastro de fundos/FCA; ou (b) manter BTCI11 como UNKNOWN (abstendo-se nos motores).   9. Os 10 maiores riscos (combinando a 1ª e a 2ª passadas, do mais grave ao menos grave)merge_if_valid descarta valores $\le 0$ da CVM (market_engine.py:130-133, 179, 800): prejuízos (lpa <= 0, roe <= 0) e PL negativo (vpa <= 0) apurados na CVM são descartados no merge, mantendo múltiplos positivos velhos do yfinance/brapi ou do cache de 7 dias e aplicando -30 de confiança como "dados ausentes" (endereçado pelo F2B-8 na proposta da 2B).   Reserva de controladores ativada em MOTIVO_SEM_CORRESPONDENCIA e perda de motivo inválido em pl_total (sentinela/data/controladores.py:44, 106-107 e tests/test_market_engine_acoes_cvm.py:448-459): variação na descrição de 3.11.01, 3.11.02 ou 2.03.09 é tratada como linha ausente e autoriza usar 100% do lucro/PL consolidado contra a D20 (endereçado pelo F2B-9, mas falta incluir test_market_engine_acoes_cvm.py:448-459 na lista de testes que mudam).   Relatório de rastreabilidade (sentinela/reports/rastreabilidade.py:66-72, 233-250, 390-395) contradizendo o código da Fase 2A: afirma que o motor de FII usa P/VP = 1,0 (sem CVMFIIProvider injetado) quando pvp está ausente (invertido no F2A-11/F2A-13) e que o P/L da CVM vem de lucro ÷ ações da Composição do Capital mesmo quando vem do LPA divulgado na DRE (F2A-36).   IFDataProvider sem proveniência temporal da D16, lendo time.time() e cacheando resposta vazia por 7 dias (sentinela/data/providers/ifdata.py:51-58, 152-175): descumpre a D16 do ADR-0003 e a regra de tempo como parâmetro para dados de Basileia de bancos.   Fórmula de $g_{\text{real}}$ pré-decidida no texto de F2B-23/F2B-1 e inconsistente com F2B-26 (docs/loop/fila-fase2b-proposta.md:385-386, 417, 496): deflaciona $\text{ROE}_{\text{nom}} \times b$ pelo IPCA inteiro sem converter o ROE por Fisher, gerando crescimento real negativo perpétuo para empresas lucrativas e mudando o valor justo em ~37% sem decisão metodológica aberta.   Ramo "QUALIDADE — AGUARDAR" matematicamente inalcançável em valuation_engine.py:274-320 e mascarado por mock de math.exp (tests/test_valuation_engine.py:48-90): para $\text{upside} \le 0$, o score máximo possível é $60 < 75$, tornando a classificação impossível sem adulterar a função exponencial.   pvp não finito (NaN/inf) escapando na saída de FIIEngine.analisar e preço negativo aceito nos dois motores (fii_engine.py:122-130, 204, valuation_engine.py:113-120): quebram o invariante do F2A-24 e produzem valor justo positivo no Graham com preço negativo (endereçados por F2B-19 e F2B-20).   Ativos fora do índice (UNKNOWN, como BPAC11) ou em montar_outros (BTCI11) e classes preferenciais em units (sentinela/data/acoes_cvm.py:196-256, montagem.py:42-67, 321-351): BPAC11 sem classe_ativo escapa da guarda do F2A-29 (endereçado pelo F2B-15), BTCI11 fica UNKNOWN no índice bloqueando FIIS_CONHECIDOS, e parsear_acoes_por_unit reduz "PNA" a "PN".   lucro_controladores no TTM sem a regra 7.2 (cvm_provider.py:732-734) e _meses ignorando dias em sentinela/data/series_cvm.py:219-220: nas 105 empresas com 3.11.01 = 0,0 na DFP 2025, o TTM lê 0,0 literal em vez de abster ou aplicar a reserva, distorcendo o 4º trimestre (DFP - 9M).   Bloqueios operacionais na proposta da fila da 2B (docs/loop/fila-fase2b-proposta.md:142, 187, 428, 570-573, 661-678): F2B-27 posicionado antes da decisão [TAXA] de que depende, F2B-9 sem test_market_engine_acoes_cvm.py:448-459 na lista de testes que mudam, e F2B-5 misturando mudança de golden em commit chore: e exigindo git grep que falha em scripts/dossie_fase2.py.   10. Vereditonão pode seguir (além dos bloqueios da 1ª passada que o resumo pr-fase-2a.md postergou para a fila da 2B sem ainda resolvê-los no branch v2/fase-2a, a segunda passada identificou 4 bloqueios novos nos arquivos agora visíveis — inverdades factuais em sentinela/reports/rastreabilidade.py:66-72, 233-250, 390-395 sobre o F2A-11/F2A-13/F2A-36, ausência de proveniência D16 e uso de time.time() em sentinela/data/providers/ifdata.py:51-58, 159, código morto matematicamente inalcançável em valuation_engine.py:319-320 mascarado por patch('math.exp') em tests/test_valuation_engine.py:61, 83, e decisão metodológica de $g_{\text{real}}$ tomada pelo texto em F2B-23/F2B-1 de docs/loop/fila-fase2b-proposta.md:385-386, 496 junto com 5 falhas de pré-condição/aceite na proposta da 2B).
