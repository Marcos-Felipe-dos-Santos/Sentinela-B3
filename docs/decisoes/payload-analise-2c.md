# F2C-27 — limites do snapshot de análise

Levantamento em 26/10/2026; sem alteração de produção ou SQLite. Decisão do pacote §5: adaptação de leitura em F2C-4, migração em F3-6 com D29. Esta proposta não autoriza remover evidência.

## Medição com fontes públicas

Ensaio local sem rede, sem banco do mantenedor, em SQLite temporário novo. `DatabaseManager.salvar_analise` e `buscar_analise` reais; JSON padrão atual (`default=str`, separadores/espaços padrão, ensure_ascii padrão). Tickers sintéticos TSTF11/TSTG11/TSTA3. São payloads parciais de insumos, não análises completas nem distribuição estatística do universo. Não incluem saída dos motores, técnica, IA ou preço. O roundtrip foi conferido contra `json.loads(json.dumps(..., default=str))`, sem pressupor preservação de tipos Python arbitrários.

| Controle público | Conteúdo | Linhas | Bytes UTF-8 JSON do campo | Bytes payload parcial |
|---|---|---:|---:|---:|
| HGLG, CNPJ 11.728.688/0001-47 | informe_fii | 21 complemento + 21 composição | 65.097 | 65.152 |
| KNRI, CNPJ 09.072.017/0001-29 | informe_fii | 21 + 21 | 65.044 | 65.099 |
| CD_CVM 9512 | serie_cvm | 1 exercício disponível (2025) | 766 | 818 |

Os dois Informes têm 32 campos por registro de complemento e 52 por composição; incluem distribuição de cotistas, despesas, ativos e passivos além dos insumos da lente. Conservam versões e entrega; o custo não é só a quantidade de meses. A série tem 18 campos por exercício, incluindo valores, origem do LPA e motivos. O ensaio de série deixou os quatro arquivos anuais anteriores indisponíveis de propósito: não extrapola cinco anos a partir de um. A coleta do provedor do Informe consulta ano corrente/anterior; se não houver registro corrente, tenta também o terceiro ano. Não se mediu aqui o terceiro ano nem o tamanho máximo.

Fontes: [Informe CVM](https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/), [DFP CVM](https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/). Hashes dos ZIPs públicos locais usados:

- Informe 2025: `0413308766b306a557bc19fa00fb5dd0ed63f8f3dffe760ee59c59682b0750ca`.
- Informe 2026: `eac25b77664933c8b79a19056ea51c591f23e7fdc1c0c101a978d83d87f22fbb`.
- DFP 2025: `d7aec54e7c67998e4cd3ef94c463ab247f09a6baaa2254878d1e431f28130e2a`.

Script e resultado locais: `/tmp/2c27-medida.py` e `/tmp/2c27-medida.json`. Para repetir: ler os dois ZIPs pelo `CVMFIIProvider.obter_rendimentos_fii` dos CNPJs acima; ler `CVMProvider.indicadores_da_serie(9512, 2025, 'empresa')` com só a DFP 2025 disponível e passar por `series_cvm.serie_anual(..., especie='ON', classe='ON')`; envolver cada campo com ticker sintético e score_final 0; salvar/ler em banco novo explicitamente localizado em /tmp; medir `len(json.dumps(payload, default=str).encode('utf-8'))`. Registrar nova proveniência pode alterar tamanho, portanto os números são observações deste ensaio, não limites normativos.

## Leitores e fronteiras atuais

| Local | Contrato atual e risco da retirada |
|---|---|
| app.py, bloco de persistência | Exclui somente historico; entrega todo o restante a salvar_analise. Não conecta o serviço alternativo. |
| services/analyze_asset.py | Mesmo filtro; usa save_run quando explícito, senão salvar_analise. É orquestração separada ainda não conectada à UI. |
| database.py | INSERT OR REPLACE por ticker; não é arquivo histórico de execuções. buscar_analise devolve JSON inteiro. Nenhum leitor de buscar_analise localizado fora do próprio método e testes nesta busca. |
| repositories/analysis_repository.py | save_run grava AnalysisResult.to_dict completo em analysis_runs append-only; list_runs/get_latest decodificam payload_json. Serialização com sort_keys/ensure_ascii=False difere do DatabaseManager; tamanhos acima não medem este caminho. Não conectar nem migrar os dois bancos implicitamente. |
| reports/rastreabilidade.py | Lê serie_cvm para expor exercícios e base dos proventos; reduzi-la a um agregado perde a evidência do relatório. |
| data/rendimento_fii.py | entradas lê informe_fii, composição, identidade B3 e proveniência e chama avaliar; não basta conservar só rendimento final. |
| ai_core.py | Exclui serie_cvm/informe_fii e outros blocos da entrada de IA; a exclusão do prompt não autoriza exclusão do armazenamento. |
| auditoria.py | Examina dados_completos diretamente por SQL/JSON e imprime extras da coleta; F2C-8 deve resumir a apresentação sem apagar dados. A rotina geral também lê carteira: não foi executada neste ensaio. |
| limpar_banco.py | Lê JSON e campos escalares diretamente; adaptador precisa preservar seus contratos antes de qualquer migração. Não foi executado. |

Busca por `informe_fii`, `serie_cvm`, `dados_completos`, `buscar_analise`, `salvar_analise`, `save_run` nos módulos Python, excluindo testes/mutantes; testes são consumidores adicionais a manter. Não se inferiu que leitores externos não existam.

## Snapshot proposto e compatibilidade

Separar três camadas, sem reduzir o contrato econômico:

1. **Bruto imutável:** ZIP/resposta oficial com hash, URL, bytes, coleta e, quando conhecido, entrega/publicação; arquivo endereçado por conteúdo e política de retenção. Duplicatas idênticas compartilham bytes. Hash sem arquivo retido ou recuperável não reproduz análise.
2. **Referência da observação:** identificador do emissor/classe, documento/período/versão, linhas e campos selecionados, unidade/escala, entrega, motivos, índice de referência versionado, calendário/corte e ligação ao bruto. Seleção deve ser reexecutável pelo parser versionado. Não substituir série por sua média nem filtrar versões antes de registrar a regra de escolha.
3. **Saída da execução:** entradas efetivamente usadas por lente e abstenções, parâmetros/versionamento das fichas e código, as_of com fuso, classificação e avisos; técnica/IA com versão e proveniência próprias. Guardar resultados não dispensa insumos e bruto.

Não impor teto em bytes por truncamento silencioso. Medir p50/p95/máximo e retenção em amostra pública maior antes de escolher limite operacional em F3-6. Estes dois FIIs não justificam um limite universal. Registro excedente deve produzir diagnóstico, nunca perder meses/versões necessários.

F2C-4 deve especificar adaptador que leia o dict legado e o snapshot novo, preserve chaves consumidas e devolva motivo explícito quando faltarem dados. Não recalcular silenciosamente uma execução antiga com ficha atual; diferenciar exibição da saída salva de nova análise. Validar roundtrip dos campos usados, motivos, datas, NaN declarado/vazio e identidades; testes de compatibilidade independentes do parser. A migração D29 requer inventário, cópia de segurança, ensaio em cópia pública, validação de contagens/conteúdo e reversão. Não alterar schema nem registros existentes nesta fase.

## Destinos

- F2C-4 / 2C-b: contrato e adaptador de leitura aprovado, sem antecipar nesta etapa.
- F3-6 / D29: schema, retenção dos brutos e deduplicação persistente; F3-1: corte temporal e reprodução histórica.
- F2C-8: resumo dos extras da auditoria, mantendo caminhos de evidência.

Nenhum bug novo confirmado neste levantamento; `default=str` é limitação do contrato atual a tratar explicitamente na especificação futura, sem afirmar preservação de DataFrame ou dataclass.
