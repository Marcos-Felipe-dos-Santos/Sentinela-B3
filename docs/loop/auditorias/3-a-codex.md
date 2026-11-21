> Cópia do relatório `auditoria-fase-3-codex-2-relatorio.md` (Downloads do Marcos), checkpoint da 3-a, 11/11/2026, pelo passo 6 do `/goal`. Única mudança: links com caminho absoluto local trocados pelo caminho relativo à raiz.

## Modo e escopo

**FASE**, branch `v2/fase-3`, tag `v2-fase-2c` até `cf764159`. Auditei os **26 commits indicados**, agrupados abaixo por item. Os demais commits foram usados apenas como contexto.

**Encontrei um defeito novo no gate e uma decisão de aceite que contesto.** Nas amostras recalculadas, não encontrei novo erro financeiro. Isso não certifica toda a fase: o pytest não conseguiu iniciar neste sandbox.

## F3-1a — `f4af8fd`

Sem achado novo: o construtor deixou de consultar a Selic; BUG-3-01 tem regressão sem xfail. A correção está demonstrada no diff; o PASS não foi reexecutado aqui.

## F3-1b — `a27b0f6`

**Confirmadas nas amostras:** conversão percentual → razão, anualização composta do CDI em 252 dias e acumulação multiplicativa do IPCA. Os três hashes SGS conferem com `tests/fixtures/sgs/FONTE.md`. A vigência exclui observações posteriores ao corte.

**Ressalva:** a disponibilidade histórica do IPCA continua sendo a aproximação M+2 ratificada provisoriamente, não a data efetiva de divulgação. O destino F3-1c está escrito; não classifico isso como novo bug.

## F3-P05 — `8891765`

Sem achado novo: o literal duplica apóstrofos antes da codificação percentual, conforme OData 4.01, Parte 2, §2.2; capital e carteira usam a correção. BUG-2C-13 está sem marca.

## F3-P01 — `f2ed7c4`, `2860508`, `554f6fe`

**Confirmada:** a fixture passa pelo provedor real com nome `AMBEV SA`, 40 registros, ISIN `BRABEVACNOR1` e identidade aceita. O hash da resposta principal confere.

**Confirmada a implementação da decisão 33:** a cascata transforma falha de identidade em abstenção, em [market_engine.py:886](market_engine.py:886). BUG-2B-29 está sem marca.

**Ressalva:** os efeitos registrados para espécies extintas e proventos de units permanecem consequências da leitura literal aprovada, não erros novos de fórmula. DD-05 e DD-06 **conferem com o código**; a conveniência desse alcance continua sendo decisão do Marcos.

## F3-P04 — `cb93c6f`

Sem achado novo: falhas totais do Informe chegam à abstenção e aos riscos; erros de programação deixam de ser engolidos naquele bloco. BUG-2C-12 e BUG-3-02 estão sem marca. BUG-3-03 continua aberto, com destino escrito em F3-3c-fix.

## F3-P03 — `76be92e`

**Confirmada:** a comparação usa a média ponderada dos componentes na mesma base por ação: `(1×1 + 2×2)/3 = 5/3`. O chamador fornece a composição; o LPA usado pelos métodos não foi alterado por esse commit.

A referência pertinente é CPC 41/IAS 33, §§9–10, 19–20 e 66, reproduzida na ficha por ação: resultado por classe e distinção entre denominadores finais e médios.

**Ressalva anterior, DD-03:** permanece. A regressão protegida chama a função sem composição e recebe `None`; portanto, seu resultado sem alertas não demonstra a soma ponderada. Os testes adicionais verificam explicitamente `5/3` e a divergência. Não atribuo um novo ID ao achado já registrado.

## F3-P08 — `d5556d8`

Sem achado novo: a guarda impede o casamento de versões explicitamente ilegíveis no mês final; BUG-2C-27 está sem marca. BUG-3-04 e BUG-3-05 continuam abertos, com destino escrito em F3-3c-fix.

## Registros de decisões e regressões — `f9af84f`, `418fc15`

Sem achado novo: os registros correspondem às regressões adicionadas; os três casos ainda abertos conservam `strict=True` e destino explícito. Não identifiquei troca dessas marcas por skip ou xfail não estrito.

## F3-P02 — `291971b`

Sem achado novo: redução parcial mantém o custo médio; compras continuam usando média ponderada. BUG-2B-51 perdeu somente a marca correspondente. A conta independente está abaixo.

## F3-2a — `9dd62d8`

Sem achado novo após considerar a correção posterior: usa a API de backup do SQLite, leitura transacional, hash e comparação de esquema/contagens na restauração. BUG-3-09 e BUG-3-10 foram tratados no item seguinte.

## F3-2a-fix — `2380f4d`

Sem achado novo: origem ausente é recusada antes de conectar; cada execução recebe pasta exclusiva; relatórios usam criação exclusiva. As alterações dos testes de backup acompanham o contrato expressamente mudado, preservando a conferência dos arquivos anteriores. BUG-3-09 e BUG-3-10 estão sem marca.

## F3-2b — `4701c1e`

Sem achado novo no estado final: confirmei em SQLite **em memória** aplicação, segunda execução sem reaplicação e recusa de versão desconhecida. A ressalva anterior DD-02 foi implementada pelo F3-2c.

## F3-1d — `83e83d3`, `be7a33d`

Sem achado novo: proveniência acompanha valor e abstenção calculada; booleanos SGS são recusados; overflow e resultados não finitos de CDI/IPCA produzem abstenção. BUG-3-06/07/08 estão sem marca. `be7a33d` altera somente a docstring.

## F3-2c — `82984cd`

**Confirmada por inspeção:** exige backup compatível com o conteúdo atual, compara tabelas linha a linha, preserva o contador AUTOINCREMENT e publica o arquivo final após a conferência. DD-11 **confere**.

**Não verificável nesta auditoria:** a alegação de migração dos bancos reais “sem perda”. Não abri bancos nem os relatórios privados em `outputs/`; o código e os testes sintéticos não comprovam aquela execução operacional.

## F3-P06 — `89fcaa6`

**Confirmada por inspeção:** o contexto distingue fonte oficial, inferência e UNKNOWN, com um único montador; BUG-2C-14 está sem marca.

**Bloqueia — DD-23 contestada:** a decisão troca a aferição do módulo por duas funções depois de o diário registrar `ai_core` inteiro em **237/345 = 68,7%**. O gate escrito exige mutação nos **módulos** novos ou alterados de cálculo ou fronteira; a exceção expressa é para scripts de processo. A apresentação de texto externo não confiável é justamente uma fronteira relevante aqui. Não considero demonstrado que a redução seja uma regra derivada mais restritiva. Evidências: [fila.md:120](docs/loop/fila.md:120) e [pendencias.md:50](docs/loop/pendencias.md:50). **Para fechar:** cumprir o alcance original ou obter exceção explícita do Marcos, sem apresentar score por função como score do módulo.

Não contesto a correção funcional por esse motivo; contesto seu aceite pelo gate.

## F3-0d — `9f952f7`

**Bloqueia — BUG-3-14 proposto: golden diferente no stage pode receber gate verde.** [scripts/gate.py:125](scripts/gate.py:125) consulta `HEAD:arquivo` e `git hash-object arquivo`, que lê a árvore de trabalho. Não consulta o blob do índice. Assim, um golden alterado e staged, seguido da restauração apenas da cópia de trabalho, passa pela verificação sem autorização. O aviso de arquivo fora do item não reprova.

Confirmei a independência em relação ao índice por simulação das respostas git em memória: índice igual e diferente de HEAD produziram `gate_ok=True`; nenhuma consulta ao índice ocorreu. Não modifiquei o stage real.

**Para fechar:** verificar também o conteúdo que será commitado.

**Regressão requerida:** `tests/regressao/test_bug_3_14_golden_stage_diferente.py` deve afirmar que golden alterado no índice, com cópia de trabalho igual a HEAD, reprova sem autorização; o caso integralmente inalterado passa. Executar em repositório temporário.

## F3-0e — `966c4d6`, `0d57094`, `d1aac6e`

Sem defeito novo confirmado: os dois primeiros commits registram bloqueios; a entrega final exporta o commit, restringe ferramentas, gera evidências e remove a cópia no `finally`.

**Não verificado:** o isolamento efetivo do CLI Claude nesta máquina. Os testes inspecionados não executam o CLI; as sondas relatadas no diário continuam alegações operacionais para esta auditoria.

## F3-0f — `4cdd991`

Sem achado novo: simula por padrão e verifica merge, tag e estado antes de tentar excluir o branch. DD-26 **confere**: consultar especificamente a seção “Fase atual” preserva a finalidade da guarda. A comparação por substring pode recusar fases com prefixos semelhantes, pelo lado seguro.

## F3-0g — `d7043fc`

Sem achado novo: o diff incorpora produtor→consumidor, teste integrado e pacote de decisões, mantendo a auditoria FICHA independente.

## F3-A-R — `cf76415`

**Ressalva — alegação contradita:** [resumo-3a.md:57](docs/loop/resumo-3a.md:57) diz que a equivalência roda “sem `as_of` explícito” e representa hoje. O harness passa explicitamente `AS_OF_GORDON` nos dois motores, em [golden_motores.py:65](tests/golden_motores.py:65) e linha 73; essa constante é **20/10/2026**, não hoje. **Para fechar:** corrigir a descrição e citar evidência específica para o gate da data atual. Golden imutável, isoladamente, não prova esse caminho.

**Ressalva — contagem contradita:** “+587 testes” é a diferença de **PASS**, não do total de casos. Pelas próprias tabelas: `3599+1+8=3608` e `4186+1+3=4190`, diferença **582**. Corrigir a distinção; os totais executados permanecem não verificados aqui.

## Transversal

- **Regressão:** nos commits selecionados, não encontrei enfraquecimento de asserções protegidas nem alteração de `pytest.ini`, métodos, harness ou golden. As marcas herdadas foram retiradas; os três casos restantes têm destino escrito. O PASS integral e a contraprova executável contra cada pai **não foram certificados**.
- **Privacidade:** não encontrei caminhos sensíveis adicionados ou alterados nos 26 commits — `.env`, bancos, logs, `data/` ou `outputs/`. Não abri esses conteúdos. Isso não equivale a certificar todo o histórico público.
- **Economia:** as contas conferidas preservam razão versus percentual e base por ação versus unit. Não identifiquei alteração de fórmula, taxa ou regime em `sentinela/methods/`.
- **Histórico:** os limites provisórios documentados não constituem prova de disponibilidade histórica estrita; a 3-b e a 3-c continuam pendentes.
- O arquivo solicitado `docs/loop/historico/fase-2c/auditoria-externa.md` **não existe neste checkout**. Usei o README de regressões e as pendências para evitar duplicação; a deduplicação contra aquele parecer ficou incompleta.

## Recalculado por mim

| Alegação | Método independente | Resultado |
|---|---|---|
| CDI de 03/01/2025 | Decimal: `(1+0,045513/100)^252−1` | **12,14995434156% a.a.**, compatível com o código |
| IPCA disponível no corte provisório de 15/10/2025 | Produto dos 12 fatores, set/2024–ago/2025 | **5,130500777504%**, compatível |
| Proventos da fixture Ambev | `0,0713+0,0449+0,269+0,4612` | **R$ 0,8464** |
| Critério Bazin dessa soma | `0,8464/0,06` | **R$ 14,10666667** |
| Unit de 1 ON e 2 PN | `(1×1+2×2)/3` | **1,66666667 por ação**, compatível |
| Redução parcial | 100 a R$10, redução de 50 | **50 restantes, PM R$10** |
| Compra posterior | 50 a R$10 mais 50 a R$20 | **PM R$15** |

O golden atual tem SHA256 `500645a3263ad25e492bff56e00c9b3552b84a243136d3397f520d4a79c24bcc` e é **byte a byte igual ao da tag**.

## Não verificado

- **Suíte:** o comando autorizado parou antes da coleta por ausência de diretório temporário gravável. Não houve teste executado.
- **Ruff CI:** executado sem cache; **passou**.
- Scores de mutação, quebras manuais e cronologia teste→correção: não reexecutados; mutmut foi expressamente proibido.
- Migração/restauração dos bancos reais e sondas do Claude: não conferidas.
- Autenticidade das coletas perante os serviços oficiais: sem rede; confirmei hashes locais e processamento das fixtures.
- Entregas exclusivas do Codex, fora da seleção: não recebem parecer nesta resposta.

## Perguntas para o Marcos

1. **DD-23:** exigir ≥80% no módulo `ai_core` ou ratificar exceção expressa para o código alterado? O dado separador é **68,7% no módulo versus 97,9% nas duas funções**, segundo o diário.
2. **Decisão 33:** manter a conferência sobre toda a relação/complemento ou abrir item para restringi-la à janela/direito relevante e reconciliar units? Os controles documentados mostram abstenção por espécies antigas e por proventos identificados como unit. Não alterei essa escolha.

## Dez maiores riscos

1. Gate aceitar golden staged diferente do conteúdo verificado.
2. DD-23 encerrar item por interpretação de aceite ainda contestada.
3. Resumo atribuir ao golden uma prova de data atual que ele não realiza.
4. PASS integral e contraprovas por commit não certificados nesta auditoria.
5. Migração real “sem perda” depender de evidência operacional não conferida.
6. Regressão BUG-2C-11 continuar sem demonstrar a comparação ponderada.
7. Alcance literal da decisão 33 reduzir a cobertura do Bazin.
8. Aproximação M+2 ser confundida com divulgação efetivamente comprovada.
9. BUG-3-03/04/05 continuarem abertos até o destino registrado.
10. Isolamento do auditor Claude depender de comportamento do CLI não revalidado aqui.

**Veredito: não pode seguir.**
