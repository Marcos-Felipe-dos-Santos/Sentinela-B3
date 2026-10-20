# F2B-1 — verificação do Gordon real, 20/10/2026

Executor: Codex. Referência normativa: Gordon1.1 e taxa-real1.1 aprovadas;
nenhum parâmetro metodológico adicional foi escolhido nesta implementação.

## Contrato e exemplo

Gordon2.0.0 recebe k real, inflação do exercício, teto PIB real e proventos
DVA dos controladores. ROE usa PL inicial do comparativo da mesma DFP;
payout usa totais, não o denominador médio do LPA. Fisher antecede o teto.
O exemplo ABEV3 da ficha resulta em **6,161748819932701**. Para o mesmo
exemplo e NTN-B74,38/1100, prêmio4% resulta em6,755660360924625;
5%, em6,161748819932701; 7%, em5,24035614299109. Contas independentes
com Python padrão, sem importar o projeto e sem arredondamento intermediário:

```python
roe = 15503400 / 98642139
payout = 10903280 / 15503400
g = min((1 + roe * (1 - payout)) / 1.0426 - 1, .02)
d0 = 10903280 / 15616526
for premio in (.04, .05, .07):
    valor = d0 * (1 + g) / (74.38 / 1100 + premio - g)
```

São os dados e datas da ficha, inclusive preço de30/09/2026; valor condicional
às guardas de direitos/eventos da própria ficha, não certificação da sua vigência.

## Universo público: antes e depois

Amostra atual do universo inicial:76registros,51 STOCK/UNIT e25FIIs excluídos
pelo escopo. Fonte da comparação histórica: snapshot público do F2B-21,
`outputs/levantamento_cache/f2b21/retratos_publicos.json`, SHA256
`13ef523b7b0fa5f73397ceac5e7657b998dc8ee199f5f8cfbcd93ac39d245792`.
O corte dos proventos desse snapshot é30/09/2026; os preços são os valores
arquivados do cache yfinance, com coleta individual registrada no retrato.
O leitor legado do cache usa o último Close disponível em `history(period="6y")`,
sem selecionar exatamente30/09. Por isso não se atribui uma data exata de
fechamento a esses preços. Foram mantidos para reproduzir o retrato inicial e
isolar a troca do método, sem trocar também os preços. Exemplo da diferença:
ABEV3 no cache=15,420000076293945, enquanto o exemplo independente da ficha
usa o COTAHIST de30/09/2026=15,36. As contas da ficha continuam com este último.
Para isolar o prêmio,
a coluna anterior fixa Selic14,5% e varia o prêmio, conservando a fórmula
anterior, mínimos e truncamento anteriores. A linha7% reproduz a configuração
anterior; 4% e5% são sensibilidades, não configurações de produção.

| Prêmio | Antes: valores Gordon /51 | Mediana anterior de valor/preço−1 | Depois: valores elegíveis no diagnóstico /51 |
|---|---:|---:|---:|
|4%|17|−0,37030153112597985|12|
|5%|17|−0,41385823146507184|12|
|7%|17|−0,4850914307262679|12|

Sob a regra1.1 aprovada em20/10/2026, a mediana posterior de valor/preço−1
é −0,7184865446769405 (prêmio4%), −0,7423210842707291 (5%) e
−0,7792481388724899 (7%). O cenário posterior usa NTN-B74,38/1100,
IPCA2025=4,26% e teto PIB2%, com as_of20/10/2026 18:00UTC. O preço de
cada ativo permanece o valor arquivado no snapshot, sem tratá-lo como fechamento
comprovado de30/09 nem como cotação de20/10.
Não se atribui toda a diferença somente ao desconto: perímetro DVA, PL inicial,
payout, janela e elegibilidade também mudaram.

Releitura local de DFP2025, ITR2025 e ITR2026, com seleção da referência/versão
entregue antes do corte:12cenários elegíveis;10modelo banco;9sem estrutura DVA;
6sem LPA/escala demonstrados;4base recente/DFP fora do intervalo;4units sem
atribuição compatível por componente demonstrada;3payout fora do domínio;
1documento/identidade histórica indisponível;1lucro/PL inicial não positivo;
1provento negativo/inválido. Total51. FII continua fora do escopo.

Contas posteriores refeitas em script com Python padrão a partir da extração
pública local, sem importar método de cálculo. Extração e resultados locais:
`outputs/f2b1-11-extracao.json` e `outputs/f2b1-11-universo.json`.
A comparação é diagnóstico sobre os arquivos arquivados indicados, não garante
cobertura de arquivo que não estava no acervo. A versão anterior deste relatório
usava a exigência de prova manual e resultava em30abstenções adicionais;
a decisão1.1 substituiu essa exigência pela regra quantitativa operacional.

**Limite declarado:** a compatibilidade agora é produzida automaticamente pela
ponte CVM, com proveniência do documento recente e razão entre quantidades
líquidas. Yfinance só avisa acima de5%. O aviso fixo informa que evento posterior
ao último documento entregue não é detectado. Units com mais de um componente
continuam exigindo atribuição compatível do fluxo por direito; uma composição
quantitativamente válida não demonstra essa atribuição. A ponte conservadora
abstém quando essa informação falta, em vez de presumir direitos iguais.

## Golden

1.221saídas anteriores alteradas,36inclusões da grade real, nenhuma remoção
e nenhuma alteração fora do predicado autorizado do F2B-1. IDs anteriores
preservados, inclusive o componente Selic, que deixou de mover Gordon.
Arquivo:926.957→1.045.043bytes. A grade nova combina NTN-B4/6/8%, IPCA2/4/6%
e margens k−g−0,001/0/0,00001/0,001. O teto sintético15% dessa grade serve
apenas para alcançar a fronteira, sem afirmar uma projeção Focus de15%.


## Comparação do motor e classificações agrupadas

O [CSV público da comparação](f2b1-universo.csv) contém os51ativos em cada
prêmio,153linhas com preço de referência do cache, preço justo do motor,
upside em pontos percentuais e
classificação agrupada antes/depois. Esta tabela é saída do motor integral,
com os demais métodos vigentes; difere da tabela da lente Gordon isolada.

| Prêmio | Mediana preço justo antes/depois (R$) | Mediana upside antes/depois (p.p.) | Grupos antes: positivo/neutro/negativo | Grupos depois: positivo/neutro/negativo |
|---|---|---|---|---|
|4%|15,82 /11,76|−14,7 /−2,5|3 /22 /26|7 /19 /25|
|5%|14,44 /11,30|−16,2 /−2,5|3 /21 /27|7 /19 /25|
|7%|12,30 /11,26|−22,6 /−9,9|3 /19 /29|7 /19 /25|

Escopo da reprodução: mesmo snapshot público de preços arquivados, conforme as datas de coleta
individuais do retrato, as_of20/10/2026 18:00UTC; Selic14,5% fixa para os leitores nominais remanescentes;
NTN-B74,38/1100, IPCA4,26%, teto PIB2% no Gordon novo. A comparação varia o
prêmio4/5/7% e mantém os demais inputs iguais entre motores. Dívida/EBITDA vem
da leitura da DFP2025 arquivada pela CVM (mesmo arquivo da extração):36valores
válidos,15ausências/não aplicáveis, discriminados em
`outputs/f2b1-11-divida.json`. O CSV deixa o campo vazio nestes15casos; o
tratamento vigente de ausência do motor é preservado igualmente antes/depois,
sem afirmar dívida zero. Não houve preenchimento por um valor inventado.
PL e P/VP são derivados do preço/LPA/VPA do snapshot. Campos de confiabilidade
seguem os padrões vigentes do motor. Fonte: motor anterior72f37a5 e atual,
sem rede, com o contexto fixado. Os números são os valores arredondados pela
saída V1, e não arredondamentos intermediários da conta independente da ficha.

O agrupamento preserva as classes de saída vigentes: classes positivas no grupo
“sinal positivo”, negativas e risco alto em “sinal negativo”, demais em “neutro”.
Não foi criado limiar novo. A confirmação da recorrência não é deduzida da
contabilidade: a hipótese explícita da ficha §1 usa DVA anual como aproximação;
a guarda §3 exclui extraordinário ou mudança estrutural sem reconciliação
identificados. O provedor registra esse fundamento e os eventos identificados;
não certifica a ausência de evento nem a sustentabilidade futura.
