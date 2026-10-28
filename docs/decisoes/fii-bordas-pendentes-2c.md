# Bordas do Informe e da taxa do FII — F2C-47

**Status: levantamento; seis decisões pendentes e duas confirmações provisórias para ratificação do Marcos.** Executor: Codex, 27/10/2026. Nenhuma produção, ficha aprovada, parâmetro ou comportamento é alterado. Confirmar ou reverter uma hipótese exige decisão explícita; a correção decorrente ganha item `fix:` próprio e regressão antes da implementação. A simples descrição do comportamento não o promove a especificação.

## Fontes conferidas e limites

- [Dicionário oficial do Informe Mensal da CVM](https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/META/meta_inf_mensal_fii.zip), coletado em **27/10/2026, 17:30:28 UTC**, 3.162 bytes, SHA256 `4db505e637e21676dc4408d51ba1dc78dabacb79087e6a8d8acd3751bb48ef55`. É o mesmo conteúdo registrado na aprovação da ficha em 25/10, não uma revisão nova inferida pela data do diretório. Contém os dicionários `geral`, `complemento` e `ativo_passivo`.
- [Página oficial do conjunto](https://dados.cvm.gov.br/dataset/fii-doc-inf_mensal): informa atualização semanal com reapresentações. Isso não é um arquivo histórico imutável por instante de conhecimento.
- [Ficha FII 1.3](../metodologia/fii.md), especialmente §§3, 3a e 3c; [ficha de taxa real](../metodologia/taxa-real.md) para o registro da taxa. São contratos do projeto, não texto da CVM.
- Comportamento verificado em `cvm_fii_provider.py` (`_linhas_do_fundo`, `obter_rendimentos_fii`), `rendimento_fii.py` (`_versao`, `_por_mes`, `avaliar`, `ntnb_ate`, `entradas`), `fii_elegibilidade.py` (`forma`) e `gordon_cvm.py` (`entradas`).

O dicionário descreve campos, tipos e domínio. Não fixa política de conflito entre duplicatas, semântica de vazio para cálculo, reconciliação de fontes, cache da NTN-B ou instante histórico da coleta. `Data_Entrega` é uma data, sem horário, presente no `geral`; as três tabelas têm referência e versão. `Versao` tem domínio numérico, tipo `tinyint`, precisão 3 e escala 0; isso não autoriza o sentinela interno `-inf` como versão documental. Não se inventa neste levantamento um domínio adicional, limiar econômico ou regra de desempate.

Arquivos, extrações e observações locais estão em `outputs/validacao-fase2c/f2c47-*`, ignorados. Controles abaixo são artificiais, não observações de um fundo real nem prova de frequência no universo.

## 1. Vazio e zero na mesma versão

**Hoje:** `forma("")` produz a categoria vazio; `forma("0")`, número zero. Por isso duas linhas de mesma referência/maior versão, iguais nos demais campos, mas com amortização vazia contra zero explícito entram em conflito. A leitura individual de amortização vazia, dentro de registro válido, vale zero pela ficha 1.3. Portanto, equivalência para a conta e equivalência para detectar conflito não são atualmente a mesma coisa. A distinção também alcança posições da composição comparadas por `forma`; não generalizar vazio para DY/VP/cotas.

**Fonte:** o dicionário do complemento descreve amortização como percentual numérico, sem convenção de vazio. A ficha §3c aprovou vazio como ausência de evento e conflitos em campos usados, mas não eliminou expressamente essa distinção na comparação de duplicatas. Controle local: vazio/zero no mês 2026-03 gerou conflito; duplicata apenas de formato numérico é outra situação, já coberta no F2C-41.

**DECISÃO PENDENTE PARA O MARCOS:** manter a distinção conservadora no conflito ou normalizar vazio/zero somente nos campos cujo contrato permite vazio como zero. Se normalizar, enumerar os campos e preservar as abstenções por registro ausente, todas as posições vazias, NaN declarado, inválido e valor negativo. Não implementar equivalência genérica de células.

## 2. Versões ilegíveis nos dois lados

**Hoje:** `_versao` converte uma versão ilegível/não finita em `-inf`. Uma numérica válida vence essa sentinela, mas duas ilegíveis comparam iguais. Se forem as únicas disponíveis, complemento e composição podem casar por `-inf`, sem evidência de igualdade documental real. Controle artificial com 13 meses, entrega válida e ambas versões ilegíveis chegou ao resultado de rendimento 12. Esse mínimo, com todos os candidatos explicitamente ilegíveis, viola a exigência de versão numérica: **BUG-2C-27**, regressão estrita no mesmo dia, destino proposto F2C-55 na 2C-b, não ativado. Não é esperado normativo aprovado.

**Fonte:** o dicionário de cada tabela define `Versao` como número inteiro documental, não como sentinela. A ficha §3 exige maior versão numérica elegível e a §3c exige a mesma versão para composição/complemento. Não há uma regra aprovada neste item que transforme duas ausências de versão em identidade documental.

**DECISÃO PENDENTE PARA O MARCOS:** definir motivos e política para ausência legada ou coexistência de versões válidas e ilegíveis. O mínimo de não produzir rendimento quando todos os candidatos são explicitamente ilegíveis já fundamenta o BUG-2C-27; não se amplia esse predicado para qualquer ausência sem especificação. Não converter ausência em versão zero nem em igualdade por conveniência. A correção futura terá regressões para ilegível nos dois lados, só em um lado e controles de versões válidas.

## 3. Entrega da composição implícita na do complemento

**Hoje:** o provedor associa `Data_Entrega` do `geral` ao complemento pela referência/versão do fundo. `avaliar` filtra complementos pela entrega; depois escolhe a composição do mês final com a mesma versão. Não verifica uma entrega própria da composição: a elegibilidade temporal dela fica implícita no documento casado. Uma reapresentação da composição não pode usar outra versão, mas a igualdade de versão é o elo temporal adotado.

**Fonte:** o dicionário oficial tem `Data_Entrega` no `geral`, não no `ativo_passivo` ou complemento. Referência/versão existem nas três tabelas. A ficha §3 pede o mesmo corte/idade da composição, e §3c a mesma versão. O layout sustenta a ligação pelo documento; não fornece horário nem um segundo carimbo de entrega para a composição.

**DECISÃO PENDENTE PARA O MARCOS:** confirmar a entrega do `geral` como evidência compartilhada do documento completo, com vínculo fundo/referência/versão explícito, ou exigir outra evidência quando o vínculo não puder ser demonstrado. Não inventar uma data própria nem assumir que composição de versão distinta é contemporânea. Falta de vínculo precisa de motivo e regressão no futuro item.

## 4. Coleta: somente a proveniência do registro mais recente chega ao consumidor

**Hoje:** o provedor lê o ano corrente e anterior, podendo incluir o terceiro ano quando faltar o corrente. Retém todas as linhas/versões, mas entrega um campo `proveniencia`, obtido da linha com maior referência/versão. `entradas` confere a coleta desse registro contra o instante `as_of`. Não percorre a coleta de cada arquivo/linha que compõe os 13 meses. Podem existir registros laterais de proveniência dos ZIPs; a afirmação aqui é sobre o pacote e a verificação efetivamente usados pela lente, não sobre a inexistência desses registros.

**Fonte:** a CVM publica arquivos anuais atualizados e reapresentações; `Data_Entrega` é do documento, não a coleta local nem prova de todos os arquivos terem sido conhecidos em um instante histórico. A ficha §3 exige versões elegíveis até o corte; D16/D17 e a ficha taxa-real distinguem referência, disponibilidade e coleta. O dicionário não fornece o relógio de coleta do consumidor.

**DECISÃO PENDENTE PARA O MARCOS:** exigir prova por arquivo/documento usado, preservar snapshots para consultas históricas ou declarar a impossibilidade de atender aquele `as_of`. Definir identidade/hashes e o destino no histórico estrito da Fase 3. Não afirmar vazamento observado nem cobertura point-in-time só pela presença do campo atual; também não descartar dados antigos silenciosamente para formar uma janela aparente.

## 5. Motivo “idade da NTN-B” reúne situações diferentes

**Hoje:** em `ntnb_ate`, idade booleana, não inteira, negativa ou acima de cinco dias úteis produz o mesmo sufixo de motivo, “idade da NTN-B”. Todas essas condições abstêm. A mensagem não distingue idade indeterminada/inválida de idade válida porém vencida.

**Fonte:** o dicionário do Informe não define NTN-B. A ficha FII §3 e a ficha taxa-real fixam a janela de cinco dias úteis e o registro de disponibilidade; tipo inválido não é evidência de taxa vencida. Não é decisão nova de largura da janela.

**DECISÃO PENDENTE PARA O MARCOS:** separar os motivos diagnósticos mantendo exatamente o predicado atual ou especificar outra política. A eventual separação textual exige regressões de cada causa e prova de que nenhum número/elegibilidade muda. Este levantamento mantém o motivo vigente.

## 6. `as_of` obrigatório no FII, opcional no consumidor do Gordon

**Hoje:** FII exige `as_of` legível/com fuso no registro da taxa, até o instante consultado, no mesmo dia local; também exige data-base anterior ao dia local, idade válida até cinco dias úteis e NTN-B finita. Gordon, em `gordon_cvm.entradas`, só verifica o corte da taxa se `macro.as_of` estiver presente; se presente, exige fuso e recusa futuro. Não exige ali mesmo dia local e não transforma a ausência dessa chave, sozinha, em abstenção. Outras guardas da taxa, janela IPCA, documento e método continuam aplicáveis: opcionalidade não significa aceitar qualquer entrada.

**Fonte:** a ficha FII e o contrato taxa-real tratam corte/disponibilidade; o dicionário CVM do Informe não é fonte para essa política macro. A diferença foi conferida nos dois consumidores, não inferida pela suíte nem pela fixture de Selic. O produtor normal pode fornecer o corte; isso não elimina a assimetria nas fronteiras públicas.

**DECISÃO PENDENTE PARA O MARCOS:** harmonizar a exigência temporal entre consumidores ou documentar justificativa e escopo da diferença. Antes de mudar comportamento, definir disponibilidade por instante, registro sem corte, cache de outro dia e compatibilidade de dados antigos. Regressões separadas devem demonstrar os predicados; nenhuma ficha anual do Gordon é alterada aqui.

## 7. Provisória do F2B-58: registro da taxa no mesmo dia local

**Hoje:** o FII só usa registro cujo `as_of` cai no mesmo dia de Brasília do instante consultado; o registro também não pode ser posterior ao instante. Um registro do dia anterior pode conter data-base ainda dentro de cinco dias úteis e, mesmo assim, abster por outro dia. Datas iguais em UTC não bastam: F2C-41 cobre a meia-noite local e o controle inverso.

**Fonte:** a cesta de taxa-real tem validade em dias úteis e o registro/cache é feito por dia. A igualdade de dia do registro é hipótese operacional adicional; não decorre do dicionário CVM, nem é equivalente a idade da data-base. O código não calcula novamente a idade para reutilizar registro de outro dia.

**DECISÃO PENDENTE PARA O MARCOS — confirmar ou reverter a provisória:** manter igualdade de dia local ou permitir registro anterior sob uma regra demonstrável de disponibilidade/idade recalculada/calendário. Não confundir validade do título/observação com validade do snapshot. O comportamento existente permanece; o levantamento não confirma definitivamente nem reverte a hipótese em nome do mantenedor.

## 8. Provisória do F2B-58: sem resposta da B3, motivo de eventos indisponíveis

**Hoje:** se os outros guardas passam, mas falta resposta da B3, `avaliar` abstém por fonte de eventos de cota indisponível. Não interpreta ausência de resposta como lista vazia de eventos. Uma resposta válida com lista vazia pode demonstrar ausência de evento; resposta ausente/inválida não. Em `entradas`, resposta não nula com coleta não demonstrada pode ser recusada antes, pelo motivo de coleta da B3; “sem resposta” não abrange qualquer falha indistintamente. A conferência de rendimento da B3, quando apenas incompleta, continua sendo aviso segundo a ficha, não a mesma guarda de eventos.

**Fonte:** ficha FII §3a distingue conferência de rendimentos e eventos de base de cotas; a CVM não define disponibilidade do serviço B3. O dicionário do Informe não converte erro de coleta em evento inexistente. O resultado depende também da ordem das guardas, não só do texto final do motivo.

**DECISÃO PENDENTE PARA O MARCOS — confirmar ou reverter a provisória:** manter o motivo atual ou distinguir fonte ausente, formato inesperado e falta de evidência temporal, preservando a abstenção enquanto continuidade não for demonstrável. Especificar a precedência quando houver mais de uma falha; não usar um aviso de conferência como autorização para ignorar a fonte de eventos. Nada é implementado neste item.

## Confirmação das provisórias do F2B-58

Pela regra de continuidade §9 / plano final §1.3, confirmam-se provisoriamente as duas escolhas operacionais pelo lado da abstenção, sem alteração de produção:

- **decisão provisória: registro da taxa em outro dia local → manter a abstenção vigente até existir prova de idade recalculada e disponibilidade no corte.** A janela da data-base não demonstra, sozinha, atualidade do registro.
- **decisão provisória: sem resposta da B3 para eventos → manter abstenção com motivo de eventos indisponíveis.** Ausência de resposta não demonstra continuidade da base de cotas.

Isso atende à confirmação operacional deste levantamento; as alternativas das seções 7 e 8 ficam para ratificação ou reversão pelo Marcos na auditoria final. Não se declara aprovação definitiva de regra metodológica e não se abre um fix sem decisão posterior.

## Destino e auditoria

Seis decisões pendentes e duas confirmações provisórias sujeitas à ratificação; nenhuma alteração de regra aprovada definitivamente. A regressão estrita BUG-2C-27 cobre somente a exigência já externa de versão numérica quando todos os candidatos são explicitamente ilegíveis; não fixa a política para versão ausente, coexistência com versão válida ou outros empates. A correção foi destinada ao F2C-55 proposto na 2C-b, conforme a regra de bugs novos, sem modificar produção neste levantamento. O auditor deve conferir primeiro versão ilegível e identidade documental, depois entrega/coleta histórica e a assimetria temporal FII/Gordon. Uma decisão posterior pode autorizar correção na 2C-b ou na Fase 3, mas precisa de item próprio e D27; este documento não ativa esses itens nem declara ratificadas definitivamente as provisórias.
