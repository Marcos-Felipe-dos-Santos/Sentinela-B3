This PR adds test coverage for the portfolio ledger specific to `database.adicionar_posicao`, following the rules of weighted average arithmetic calculation for added positions, partial sales, exact sellouts, and exceeding total quantity.

All tests utilize a temporary mocked SQLite DB without external calls. No structural logic code was changed.

### Tests Included:
- `test_primeira_compra_insere_com_data_de_hoje`
- `test_aporte_adicional_media_ponderada`
- `test_venda_parcial_preserva_preco_medio` (XFAIL)
- `test_zeragem_remove_posicao`
- `test_ticker_normalizado`
- `test_venda_de_ticker_inexistente_nao_insere`
- Extra scenarios: selling more than existing position (implicitly documented via test_venda_maior_que_posicao to evaluate current behavior natively scaling over bounds logic), purchasing zero value logic `test_compra_quantidade_zero_nao_insere`, and minor bounds variables edge cases.

### Divergences List
- **Partial sale calculation:** The test `test_venda_parcial_preserva_preco_medio` expects the average purchase price to remain untouched upon a partial sell, mimicking standard capital gains practice. However, `database.py` recalculates the average using the sell price into the position's weight formula, which directly violates this specification. Thus, the test has been explicitly marked as strictly failing (`@pytest.mark.xfail(strict=True, raises=AssertionError)`).

### Mutation Coverage
The function `database.adicionar_posicao` achieved a final coverage score of approximately **81.4%** across `mutmut` generated tests (surviving 10/54 mutants).
The mutants covered exclusively by the failing partial sale test (`test_venda_parcial_preserva_preco_medio`) fall onto algebraic variations within the inner `novo_pm` calculation block such as turning the division into subtraction or multiplication, meaning:
- `database.xǁDatabaseManagerǁadicionar_posicao__mutmut_23`
- `database.xǁDatabaseManagerǁadicionar_posicao__mutmut_24`
- `database.xǁDatabaseManagerǁadicionar_posicao__mutmut_25`
- `database.xǁDatabaseManagerǁadicionar_posicao__mutmut_26`
- `database.xǁDatabaseManagerǁadicionar_posicao__mutmut_27`
