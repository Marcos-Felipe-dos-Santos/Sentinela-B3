Auditoria Externa — Fase 3 (3-a + commits até HEAD 419f010)

Escopo auditado: 284165f..419f010 (25 commits após o fechamento da 2C, mais o diff em stage de F3-3a), em modo estritamente somente leitura. Exclusões: achados já registrados em 3-a-claude-code.md, 3-a-codex.md, pendencias.md e tests/regressao/README.md não foram repetidos abaixo.

1. Verificações de Fronteira (Golden, Testes Protegidos e Regras Econômicas)
Golden e testes protegidos: git diff 284165f..419f010 e git diff --cached confirmam zero alterações em golden_motores.jsonl, test_financeiro_pre_refactor.py, test_equivalencia_motores.py, golden_motores.py, sentinela/methods/**, portfolio_engine.py e backtesting/**.
Regras econômicas mudadas sem ficha: nenhuma fórmula ou critério de valuation (Graham, Lynch, Bazin, Gordon, Qualidade, FII, Bancos) foi alterado sem ficha. As mudanças em valuation_engine.py e fii_engine.py limitaram-se à resolução de as_of (F3-6c) e à leitura da Selic pelo registro de MacroContext (F3-1b).
2. Novos Achados
Achado 1 — sgs_432 gravada em series_macro com proveniência/hash só da 1ª janela decenal, teste que prova só o mock e desconexão produtor→consumidor
item: F3-1c (com reflexo na ligação com F3-1b / F3-6c)
commit: 419f010
arquivo:linha: macro.py:755-775, test_series_macro.py:42-47, test_series_macro.py:135-175, test_series_macro.py:235-239, config.py:347-395
problema:
Proveniência e hash incorretos em series_macro: em gravar_series._selic, provedor.serie_sgs(macro_por_data.SELIC_META, fim, coleta) consulta o SGS 432 em 3 janelas de 10 anos (1999–2009, 2009–2019, 2019–2026) e devolve dados["proveniencia"] com 3 dicionários (cada um com sua URL dataInicial/dataFinal e seu hash_sha256). Porém, a linha 759 faz prov = dados["proveniencia"][0] if dados["proveniencia"] else {} e grava todas as observações de 1999 a 2026 com a URL e o SHA-256 da primeira janela (1999–2009).
Teste que prova só o mock: test_selic_com_fonte_e_hash_da_coleta usa a fixture fontes, que substitui provedor.baixar para devolver o mesmo hash constante "b" * 64 em todas as chamadas ao SGS e só verifica "bcdata.sgs.432" in linha[5] and linha[6] == "b" * 64.
Desconexão produtor→consumidor: F3-1c grava sgs_432 em series_macro, mas nenhum consumidor lê sgs_432 do banco — MacroContext.registro_por_data chama apenas provedor.serie_sgs(...) para "selic". Além disso, em test_get_taxa_real_de_data_passada_le_do_banco_ate_gordon_e_fii, FIIEngine executa sob a fixture autouse _macro_fii_cenario_temporal, que injeta get_selic_atual() fixo no MacroContext, não a Selic histórica gravada no banco.
cenário de falha: Ao auditar ou reconstruir uma série Selic de 2024 em series_macro, a coluna fonte aponta para dataInicial=05/03/1999&dataFinal=04/03/2009 e hash_sha256 contém o hash do arquivo de 1999–2009, invalidando a verificação de integridade documental. E quando MacroContext.registro_por_data("selic", as_of) é chamado em produção para data passada, ele bate na rede do BCB em vez de ler series_macro.
severidade: Alta
correção sugerida: Associar cada ponto (data, valor) da Selic à proveniência/hash da janela decenal que o retornou; conectar a leitura de sgs_432 em series_macro quando db_path existir para data passada; e no teste usar hashes distintos por janela do SGS.
Achado 2 — gravar_series._tesouro vaza sqlite3.IntegrityError não tratado em linhas duplicadas/conflitantes do CSV do Tesouro e faz parse de títulos fora de _TIPOS
item: F3-1c
commit: 419f010
arquivo:linha: macro.py:587-621, macro.py:815-825, 003_series_macro.sql:15-40, tesouro.py:113-114, tesouro.py:168-193
problema:
Em tesouro.ler_csv (validar_aplicacao=False), linhas duplicadas ou conflitantes para o mesmo (Tipo Titulo, Data Vencimento, Data Base) não levantam exceção global: marcam motivo_aplicacao="linhas conflitantes no par de aplicação" para vetar apenas a cesta daquela data-base (BUG-2B-22). Já em gravar_series._tesouro, cada linha do CSV gera um INSERT INTO series_macro com PRIMARY KEY (serie, data, coleta). Duas linhas com mesmo (serie, data, coleta) disparam sqlite3.IntegrityError (pela PK ou pelo trigger series_macro_sem_sobrescrita).
Em familia, apenas FALHAS_DA_FONTE (RequestException, OSError, ValueError) e ERROS_DO_CODIGO (KeyError, TypeError) são capturados; sqlite3.IntegrityError não é capturado e aborta gravar_series inteiro antes de gravar anbima, focus, ipca e selic.
Além disso, _tesouro executa _data_br e _decimal_virgula em todas as linhas do CSV antes de filtrar tesouro._TIPOS, ao contrário de tesouro.ler_csv, de modo que qualquer linha malformada ou duplicada de título fora da cesta (ex.: Tesouro Selic, Tesouro Educa+) derruba a carga.
cenário de falha: O CSV histórico do Tesouro Transparente contém uma linha duplicada ou um título fora de _TIPOS com taxa vazia/malformada; gravar_series quebra com exceção não tratada ou descarta todo o histórico do Tesouro, divergindo do comportamento de F3-1c-a (tesouro.ler_csv).
severidade: Alta
correção sugerida: Filtrar tesouro._TIPOS antes de converter campos em _tesouro e tratar pares (tipo, vencimento, data_base) conflitantes com o mesmo contrato de tesouro.ler_csv (marcador de conflito na referência, sem IntegrityError).
Achado 3 — gravar_series._ipca quebra se o SIDRA trouxer mês não divulgado ("...") ou lista vazia, e registro_do_banco omite proveniencia e calendario em inflacao e pib
item: F3-1c
commit: 419f010
arquivo:linha: macro.py:725-752, macro.py:875-928 (comparado a macro.py:95-103, macro.py:283-286, macro.py:385-388) e test_series_macro.py:86-91
problema:
Em ipca_da_janela, meses cujo código D3C não está em publicacoes são filtrados antes de chamar _numero(linha.get("V"), "IPCA") (no SIDRA, meses ainda não divulgados vêm com V = "..." ou "-", que levantam ValueError em _numero). Já em gravar_series._ipca, valores = {str(l.get("D3C")): _numero(l.get("V"), "IPCA") for l in bruto[1:]} avalia _numero em todas as linhas antes de filtrar publicacoes. Além disso, em macro.py:732-737, se publicados for vazio, max(publicados) levanta ValueError: max() iterable argument is empty antes do if not valores:.
Enquanto MacroProvider.registro inclui "proveniencia" e "calendario" dentro de resultado["inflacao"] e resultado["pib"], registro_do_banco omite ambas as chaves nos sub-blocos inflacao e pib. O teste test_banco_da_o_mesmo_resultado_do_caminho_historico não percebeu a diferença porque comparou apenas ["valor"] e ["pesquisa"].
cenário de falha: Quando o SIDRA expõe a linha do mês corrente ainda fechado com V = "...", gravar_series._ipca falha com ValueError("IPCA inválido") e não grava nenhuma observação de sidra_1737_v63. E consumidores que inspecionam taxa_real["inflacao"]["proveniencia"] ou taxa_real["pib"]["proveniencia"] recebem KeyError/None quando a leitura vem de series_macro.
severidade: Média
correção sugerida: Em _ipca, validar if not publicados: antes de max(publicados) e filtrar str(l.get("D3C")) in publicacoes antes de chamar _numero(l.get("V"), "IPCA"). Em registro_do_banco, preencher proveniencia e calendario em inflacao e pib a partir das linhas lidas de series_macro.
Achado 4 — Calendário Focus do ano anterior (ano - 1) não é consultado nem aceito para as_of no início de janeiro
item: F3-1c-a e F3-1c
commit: eb83075 e 419f010
arquivo:linha: macro.py:348-376, macro.py:665-691, macro.py:901-912
problema: Para feriados/pregões ANBIMA, gravar_series._anbima busca {ano for d in datas for ano in (d.year - 1, d.year)} justamente porque os primeiros dias de janeiro dependem do fim do ano anterior. Porém, para o calendário Focus:
MacroProvider.pib baixa apenas f"{_URL_CALENDARIO_ANBIMA}/{dia.year}" e filtra edicao["divulgacao"].year == dia.year;
gravar_series._focus baixa apenas {d.year for d in datas};
_pib_do_banco filtra date.fromisoformat(d).year == dia.year.
cenário de falha: Em qualquer as_of nos primeiros dias úteis de janeiro antes da primeira divulgação Focus do ano (ex.: 2026-01-02 quando o primeiro Focus de 2026 sai em 2026-01-05), a edição Focus vigente foi divulgada na última semana de dezembro de 2025. Como dia.year - 1 não é consultado nem aceito no filtro, devidas fica vazia e get_taxa_real se abstém indevidamente com "edição Focus devida ausente".
severidade: Média
correção sugerida: Incluir (dia.year - 1, dia.year) na consulta e no filtro do calendário Focus em MacroProvider.pib, gravar_series._focus e _pib_do_banco.
Achado 5 — MarketEngine.buscar_dados_ticker(..., as_of=...) ignora as_of ao buscar taxa_real (e o teste da cascata mocka _buscar_taxa_real)
item: F3-6c
commit: 93bbdd4
arquivo:linha: market_engine.py:532, market_engine.py:570-571, market_engine.py:864-866, test_as_of_cascata.py:127-156
problema: Em F3-6c, MarketEngine.buscar_dados_ticker passou a receber as_of: datetime | None = None e repassá-lo a _buscar_cvm, _buscar_ifdata, _buscar_cvm_fii, _buscar_rendimento_fii, _buscar_proventos_b3 e _contexto_janelas. Contudo, na linha 571 chama self._buscar_taxa_real(dados) sem as_of, e _buscar_taxa_real chama get_taxa_real(as_of=datetime.now(UTC), janela=janela) usando o relógio em vez do as_of explícito. O teste test_cascata_passagem_de_referencia_sem_retroagir_a_coleta substituiu _buscar_taxa_real por Mock(), ocultando que taxa_real não recebe as_of.
cenário de falha: Quando buscar_dados_ticker("HGLG11", as_of=...) é chamado com um as_of explícito (ou próximo à virada de dia em America/Sao_Paulo), dados["taxa_real"]["as_of"] reflete datetime.now(UTC) em vez de as_of, fazendo FIIEngine abster a avaliação de tijolo por "taxa real com as_of diferente da análise" (BUG-2B-46).
severidade: Baixa (na 3-a o F3-6c proíbe as_of passado na cascata, mas quebra na virada de dia ou assim que as_of explícito diferir do relógio)
correção sugerida: Repassar referencia (as_of or datetime.now(UTC)) para _buscar_taxa_real(dados, as_of=referencia) e verificar no teste que get_taxa_real recebe o as_of passado a buscar_dados_ticker.
3. Verificação das Decisões Delegadas (DD-01 a DD-42)

Todas as decisões delegadas registradas em pendencias.md (e DD-42 em stage no F3-3a) foram confrontadas com politica-decisao-autonoma.md e decisoes-fase3.md:

ID	Item	Veredito	Motivo
DD-01 a DD-11	F3-0	Confere	Classes 1 e 3 (governança/scripts de fila, gate, auditoria e fecho de fase); sem impacto em cálculo econômico ou fontes.
DD-12	F3-1a	Confere	Classe 2: cache por processo em get_selic_atual com limpar_cache_selic; elimina rede no import de config (BUG-3-01).
DD-13	F3-2a	Confere	Classe 2: sanitização e rejeição de ' no filtro OData do IF.data (BUG-3-02); fica do lado da abstenção.
DD-14	F3-2b	Confere	Classe 2: versão não inteira em Versao do Informe FII levanta ValueError em vez de virar 0 (BUG-3-03); fica do lado da abstenção.
DD-15	F3-2c	Confere	Classe 2: exige CNPJ_CIA igual ao emissor esperado nos proventos B3 (BUG-3-04); evita contaminação entre emissores.
DD-16, DD-17	F3-2d	Confere	Classe 2: corte explícito dt_receb <= as_of em cvm_provider, sem filtro silencioso por date.today() (BUG-3-05).
DD-18, DD-19	F3-2e	Confere	Classe 1/2: LPA da unit ponderado pela composição do pacote quando todas as classes têm LPA na DFP; abstém se faltar classe (BUG-3-06).
DD-20, DD-21	F3-5a	Confere	Classe 1/2: data_preco extraída do índice do histórico de fechamento do provedor vencedor (yfinance/brapi), sem usar date.today().
DD-22, DD-23	F3-6a	Confere	Classe 1/2: remoção de caminhos mortos em ai_core.py e validação estrita das chaves obrigatórias do dicionário  Valuation.
DD-24, DD-25	F3-6b	Confere	Classe 2: classe_origem explícita em AssetInput, recusando inferência por sufixo de ticker quando dados_mercado existe.
DD-26	F3-6c	Confere	Classe 1/2: as_of explícito nos motores e cascata (com a ressalva técnica de implementação apontada no Achado 5 sobre _buscar_taxa_real).
DD-27, DD-28	F3-6d	Confere	Classe 2: transporte de AnalysisService preserva todos os blocos de Presentation e a UI consome AnalysisService.
DD-29, DD-30	F3-6e	Confere	Classe 1: testes de contrato textual para ai_core sobre o shape real dos motores, sem alterar método econômico.
DD-31, DD-32	F3-1b	Confere	Classe 1/2: MacroContext expõe registro_por_data e o FII consome a Selic com data_base/proveniencia do registro, abstendo quando indisponível (BUG-3-07).
DD-33, DD-34	F3-3b	Confere	Classe 2: backup atômico + manifesto SHA-256 validado antes de migrar banco existente.
DD-35, DD-36	F3-3c	Confere	Classe 2: runner de migrações SQL numeradas com hash de versão e restauração automática do backup em caso de erro.
DD-37, DD-38	F3-3d	Confere	Classe 2: store único com migração idempotente do legado e depreciação de CACHE_DB_PATH.
DD-39	F3-3e	Confere	Classe 2: migração 002 recria analises_cache com PRIMARY KEY (ticker, as_of, versao_metodologia) e preserva legado com sentinela legado-pre-3a.
DD-40	F3-1c-a	Confere	Classe 1/2: janelas estritas documentadas para Tesouro, Focus, IPCA e SGS 432 sem fallback silencioso (com a ressalva de borda em janeiro apontada no Achado 4).
DD-41	F3-1c	Contesta parcialmente	A decisão de persistir as séries em series_macro com triggers append-only é adequada (Classe 2), mas a execução: (1) incluiu sgs_432 gravando todas as janelas de 10 anos com a proveniência/hash apenas da 1ª janela (proveniencia[0]) e sem leitor conectado em MacroContext (Achado 1); e (2) omitiu proveniencia e calendario de inflacao e pib em registro_do_banco, divergindo do retorno de F3-1c-a (Achado 3).
DD-42	F3-3a (em stage)	Confere	Classe 2: migração 004_tabelas_pit.sql cria as 7 tabelas ponto-no-tempo com chaves naturais, proveniencia e hash_sha256 obrigatórios e triggers que bloqueiam sobrescrita silenciosa.
