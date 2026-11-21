-- `proventos_complemento` só de inserção, como as outras tabelas de proventos da migração 009
-- (revisão do F3-8d-fix): o complemento com que a leitura refaz a parte (b) da decisão 33 não
-- muda depois da coleta. Migração própria porque a 011 já foi aplicada ao banco real.
CREATE TRIGGER proventos_complemento_sem_update BEFORE UPDATE ON proventos_complemento
BEGIN SELECT RAISE(ABORT, 'proventos_complemento é só de inserção'); END;
CREATE TRIGGER proventos_complemento_sem_delete BEFORE DELETE ON proventos_complemento
BEGIN SELECT RAISE(ABORT, 'proventos_complemento é só de inserção'); END;
CREATE TRIGGER proventos_complemento_sem_sobrescrita BEFORE INSERT ON proventos_complemento
WHEN EXISTS (
    SELECT 1 FROM proventos_complemento WHERE emissor = NEW.emissor AND coleta = NEW.coleta
)
BEGIN SELECT RAISE(ABORT, 'proventos_complemento é só de inserção'); END;
