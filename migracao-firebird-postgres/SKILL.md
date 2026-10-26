---
name: migracao-firebird-postgres
description: Converte stored procedures, triggers e blocos PSQL do Firebird para PL/pgSQL do PostgreSQL, apontando diferenças de comportamento. Use sempre que o usuário colar código Firebird/Interbase ou falar em migrar procedures, SUSPEND, EXECUTE PROCEDURE, generators, exceptions ou isql para Postgres, mesmo que não use a palavra "migração".
---

# Migração de procedures Firebird (PSQL) para PostgreSQL (PL/pgSQL)

O objetivo é produzir código PostgreSQL que **se comporte igual** ao original, não apenas que compile. A maioria dos bugs de migração vem de diferenças semânticas silenciosas, como SELECT INTO sem linhas, comparação de strings com espaços e maiúsculas em identificadores. Por isso, sinalizar essas diferenças é parte tão importante da entrega quanto o código.

Não "melhore" a lógica durante a conversão. Se enxergar uma melhoria (ex.: trocar um loop por um UPDATE em lote), entregue a versão fiel e sugira a melhoria separadamente. Assim a migração continua auditável e testável lado a lado.

## Antes de converter: confirme o contexto

Se algo abaixo não estiver claro na conversa, assuma o padrão indicado e diga que assumiu, sem travar a resposta esperando:

- **Versão do PostgreSQL**: assuma 14+. Procedures com parâmetros OUT existem desde o 14; `MERGE`, só a partir do 15.
- **Versão/dialeto do Firebird**: assuma Firebird 2.5/3.0, dialeto 3. No dialeto 1, `DATE` contém hora (vira `timestamp`) e aspas duplas delimitam strings.
- **Nomes das tabelas no Postgres**: assuma que foram migradas em minúsculas e sem aspas. Se a ferramenta de migração manteve nomes em maiúsculas entre aspas (`"CLIENTES"`), todo o código precisa seguir esse padrão. Pergunte se houver indício disso.
- **Como a aplicação chama a procedure** (`SELECT * FROM SP(...)` ou `EXECUTE PROCEDURE`): isso define se ela vira FUNCTION ou PROCEDURE.

Se faltar a DDL das tabelas e o tipo de uma coluna for relevante, peça ou marque como ponto a confirmar. Nunca invente colunas.

## Passo 1: classificar a procedure

| Tipo no Firebird | Como reconhecer | Destino no PostgreSQL |
|---|---|---|
| Selecionável | Tem `RETURNS (...)` e usa `SUSPEND` | `FUNCTION ... RETURNS TABLE(...)` ou `RETURNS SETOF`, chamada com `SELECT * FROM f(...)` |
| Executável com saída | Tem `RETURNS (...)` sem `SUSPEND` | `FUNCTION` com parâmetros `OUT` (retorna uma linha) |
| Executável sem saída | Sem `RETURNS` | `FUNCTION ... RETURNS void` (padrão) ou `PROCEDURE`, se a aplicação vai usar `CALL` |

Prefira FUNCTION por padrão. Procedures do Firebird não fazem controle de transação, então a única vantagem de `PROCEDURE` no Postgres (COMMIT/ROLLBACK interno) não se aplica. Além disso, funções são mais fáceis de chamar a partir de SELECT e de outras funções.

## Passo 2: converter a estrutura

- Remova `SET TERM ^ ;` e `SET TERM ; ^`. Use dollar quoting (`AS $$ ... $$;`) e `LANGUAGE plpgsql`.
- `CREATE OR ALTER PROCEDURE` vira `CREATE OR REPLACE FUNCTION`. Atenção: o REPLACE não pode mudar o tipo de retorno nem os parâmetros OUT. Nesse caso, faça antes `DROP FUNCTION nome(tipos)`. Como o Postgres permite sobrecarga, a função é identificada por nome + tipos dos parâmetros, e o DROP exige a assinatura.
- Os vários `DECLARE VARIABLE x INTEGER;` viram um bloco único `DECLARE x integer; ...` antes do `BEGIN`.
- Valor inicial: `DECLARE VARIABLE x INTEGER = 0;` vira `x integer := 0;`.
- Atribuição: `x = 1;` vira `x := 1;`.
- Remova os dois-pontos (`:var`) das variáveis dentro de SQL. **Isso cria risco de ambiguidade** entre variável e coluna (erro `column reference "id" is ambiguous`), que o Firebird resolvia com o `:`. Para evitar:
  - Sempre qualifique colunas com alias de tabela (`p.id`).
  - Se nomes de parâmetros coincidirem com colunas, renomeie com prefixos `p_` (parâmetro) e `v_` (variável).
  - Em `RETURNS TABLE(id ...)`, `id` também é variável, então qualifique as colunas homônimas nas queries.

### Controle de fluxo

| Firebird | PostgreSQL |
|---|---|
| `IF (c) THEN ... ELSE ...` | `IF c THEN ... ELSE ... END IF;` |
| `WHILE (c) DO BEGIN ... END` | `WHILE c LOOP ... END LOOP;` |
| `FOR SELECT a, b FROM t INTO :x, :y DO BEGIN ... END` | `FOR x, y IN SELECT a, b FROM t LOOP ... END LOOP;` (ou variável `record`) |
| `FOR EXECUTE STATEMENT s INTO :x DO` | `FOR x IN EXECUTE s LOOP ... END LOOP;` |
| `SUSPEND;` | `RETURN NEXT;` (depois de atribuir as colunas de saída) |
| `EXIT;` | `RETURN;` |
| `LEAVE;` / `BREAK;` | `EXIT;` |
| `LEAVE rotulo;` | `EXIT rotulo;` (rótulo declarado como `<<rotulo>>`) |
| `CONTINUE;` | `CONTINUE;` |
| `EXECUTE PROCEDURE p(a) RETURNING_VALUES :x` | `x := p(a);` ou `SELECT * INTO x, y FROM p(a);` |
| `EXECUTE PROCEDURE p(a)` (sem saída) | `PERFORM p(a);` (função) ou `CALL p(a);` (procedure) |
| `EXECUTE STATEMENT s;` | `EXECUTE s;` (use `USING` ou `format()` com `%I`/`%L`, nunca concatenação crua) |
| `EXECUTE STATEMENT s INTO :x` | `EXECUTE s INTO x;` |
| `POST_EVENT 'X';` | `PERFORM pg_notify('x', '');` (nos dois bancos a entrega é no commit) |
| `IN AUTONOMOUS TRANSACTION DO` | Sem equivalente nativo. Sinalize como **alto risco**. Alternativas: `dblink`, extensão `pg_background` ou redesenho (ex.: log gravado pela aplicação). |

Se uma procedure selecionável só faz `FOR SELECT ... DO SUSPEND`, sem lógica no meio, use `RETURN QUERY SELECT ...;`, que é mais simples e mais rápido.

### Cursores

- `DECLARE c CURSOR FOR (SELECT ...);` vira `c CURSOR FOR SELECT ...;` no DECLARE.
- `OPEN c; FETCH c INTO :x; ... CLOSE c;` continua igual, mas o teste de fim muda. O Firebird usa `ROW_COUNT = 0`; o Postgres usa `IF NOT FOUND THEN EXIT; END IF;`.
- `FOR SELECT ... AS CURSOR c DO ... UPDATE t ... WHERE CURRENT OF c` vira um cursor declarado com `FOR UPDATE` na query, mais `FOR rec IN c LOOP ... UPDATE t ... WHERE CURRENT OF c; END LOOP;`.

## Passo 3: SELECT INTO e ROW_COUNT (diferença crítica)

- **Nenhuma linha**: no Firebird, as variáveis alvo mantêm o valor anterior. No Postgres (sem STRICT), elas viram NULL. Um padrão comum é `x = 0; SELECT ... INTO :x;` esperando que `x` continue 0. Para preservar, use `IF NOT FOUND THEN x := 0; END IF;`.
- **Mais de uma linha**: o Firebird gera erro (`multiple rows in singleton select`); o Postgres pega a primeira silenciosamente. Se o erro fazia parte da regra, use `SELECT ... INTO STRICT` e trate `no_data_found` / `too_many_rows`. Avise que blocos EXCEPTION criam subtransação e custam desempenho dentro de loops.
- `ROW_COUNT` após INSERT/UPDATE/DELETE vira `GET DIAGNOSTICS v_qtd = ROW_COUNT;` ou o teste `IF FOUND`.
- `INSERT ... RETURNING id INTO :x` vira `INSERT ... RETURNING id INTO x;`.
- `UPDATE OR INSERT INTO t (...) VALUES (...) MATCHING (k)` vira `INSERT ... ON CONFLICT (k) DO UPDATE SET ...` (exige constraint unique ou PK em `k`; confirme que existe) ou `MERGE`, no PG 15+.

## Passo 4: exceções

Exceções nomeadas do Firebird (`CREATE EXCEPTION`) não existem no Postgres. Converta cada uma para `RAISE EXCEPTION` com um SQLSTATE próprio, para que os handlers e a aplicação continuem conseguindo distingui-las. Entregue uma tabela de mapeamento (nome da exceção → SQLSTATE → mensagem). Use códigos de 5 caracteres que não colidam com os do Postgres, como `FB001` e `FB002`.

```sql
-- Firebird
CREATE EXCEPTION E_SALDO_INSUFICIENTE 'Saldo insuficiente';
IF (SALDO < :P_VALOR) THEN EXCEPTION E_SALDO_INSUFICIENTE;
EXCEPTION E_SALDO_INSUFICIENTE 'Saldo insuficiente na conta ' || :P_CONTA;

-- PostgreSQL
IF v_saldo < p_valor THEN
  RAISE EXCEPTION 'Saldo insuficiente' USING ERRCODE = 'FB001';
END IF;
RAISE EXCEPTION 'Saldo insuficiente na conta %', p_conta USING ERRCODE = 'FB001';
```

Os handlers `WHEN ... DO` (no fim do bloco) viram a seção `EXCEPTION WHEN ... THEN` do bloco. Nos dois bancos, as alterações feitas dentro do bloco são desfeitas quando a exceção é capturada.

| Firebird | PostgreSQL |
|---|---|
| `WHEN ANY DO` | `WHEN OTHERS THEN` |
| `WHEN EXCEPTION E_X DO` | `WHEN SQLSTATE 'FB001' THEN` |
| `WHEN GDSCODE unique_key_violation` / `SQLCODE -803` | `WHEN unique_violation THEN` |
| `WHEN GDSCODE foreign_key` / `SQLCODE -530` | `WHEN foreign_key_violation THEN` |
| `WHEN GDSCODE not_valid` / `SQLCODE -625` | `WHEN not_null_violation` ou `check_violation` (confirme qual) |
| `WHEN GDSCODE arith_except` / `SQLCODE -802` | `WHEN numeric_value_out_of_range OR division_by_zero OR string_data_right_truncation THEN` |
| `WHEN GDSCODE lock_conflict` / `deadlock` / `SQLCODE -913` | `WHEN lock_not_available OR deadlock_detected OR serialization_failure THEN` |
| `EXCEPTION;` (relançar dentro do handler) | `RAISE;` |
| variáveis `SQLCODE`, `GDSCODE`, `SQLSTATE` | `SQLSTATE`, `SQLERRM` ou `GET STACKED DIAGNOSTICS` |

## Passo 5: tipos, funções e operadores

### Tipos

| Firebird | PostgreSQL |
|---|---|
| `SMALLINT`, `INTEGER`, `BIGINT`, `NUMERIC(p,s)`, `DECIMAL`, `DOUBLE PRECISION`, `CHAR`, `VARCHAR(n)`, `DATE`, `TIME`, `TIMESTAMP`, `BOOLEAN` | iguais |
| `FLOAT` | `real` |
| `BLOB SUB_TYPE TEXT` / `SUB_TYPE 1` | `text` |
| `BLOB SUB_TYPE 0` / `BINARY` | `bytea` |
| `DATE` no dialeto 1 | `timestamp` |
| Domínios (`TYPE OF D_VALOR` ou `D_VALOR` em parâmetros) | domínio equivalente criado no PG, ou o tipo base |
| `TYPE OF COLUMN t.c` | `t.c%TYPE` |

Booleans antigos (`SMALLINT` 0/1, `CHAR(1)` 'S'/'N') mantêm o tipo que a tabela tiver no Postgres. Não converta para boolean por conta própria.

### Funções e sintaxe

| Firebird | PostgreSQL |
|---|---|
| `GEN_ID(g, 1)` / `NEXT VALUE FOR g` | `nextval('g')` |
| `GEN_ID(g, 0)` | `(SELECT last_value FROM g)`. Não use `currval`, que é por sessão e falha se a sessão ainda não chamou nextval. |
| `GEN_ID(g, n)` | `setval('g', nextval('g') + n - 1)` ou repense o código; sinalize |
| `IIF(c, a, b)` | `CASE WHEN c THEN a ELSE b END` |
| `DECODE(x, a, r1, b, r2, def)` | `CASE x WHEN a THEN r1 WHEN b THEN r2 ELSE def END` |
| `MAXVALUE(a, b)` / `MINVALUE(a, b)` | `greatest` / `least`. **Atenção**: o Firebird retorna NULL se algum argumento for NULL; o Postgres ignora os NULLs. |
| `LIST(x, ',')` | `string_agg(x::text, ',')` |
| `SELECT FIRST 10 SKIP 20 ...` / `ROWS 21 TO 30` | `LIMIT 10 OFFSET 20` |
| `DATEADD(n DAY TO d)` / `DATEADD(DAY, n, d)` | `d + n * interval '1 day'` |
| `DATEDIFF(DAY, a, b)` | `(b::date - a::date)` |
| `DATEDIFF(MINUTE, a, b)` etc. | `extract(epoch FROM (b - a)) / 60` com arredondamento explícito; sinalize para confirmar |
| `EXTRACT(WEEKDAY FROM d)` | `extract(dow FROM d)` (nos dois, 0 = domingo) |
| `EXTRACT(YEARDAY FROM d)` | `extract(doy FROM d) - 1` (no Firebird começa em 0) |
| `'NOW'`, `CAST('NOW' AS TIMESTAMP)` | `clock_timestamp()` se mede tempo real; `now()` se basta o início da transação |
| `'TODAY'` / `'TOMORROW'` / `'YESTERDAY'` | `current_date` / `current_date + 1` / `current_date - 1` |
| `CONTAINING 'x'` | `ILIKE '%' || 'x' || '%'` (case-insensitive) |
| `STARTING WITH 'x'` | `LIKE 'x' || '%'` |
| `ASCII_CHAR(n)` / `ASCII_VAL(c)` | `chr(n)` / `ascii(c)` |
| `BIN_AND` / `BIN_OR` / `BIN_XOR` / `BIN_SHL` | `&` / `|` / `#` / `<<` |
| `GEN_UUID()` | `gen_random_uuid()` |
| `HASH(x)` | sem equivalente que dê o mesmo resultado; sinalize se o valor é persistido |
| `RDB$GET_CONTEXT('USER_SESSION', 'X')` | `current_setting('app.x', true)` |
| `RDB$SET_CONTEXT('USER_SESSION', 'X', v)` | `set_config('app.x', v, false)` (`true` para `USER_TRANSACTION`) |
| `CURRENT_CONNECTION` / `CURRENT_TRANSACTION` | `pg_backend_pid()` / `txid_current()` |
| `RDB$DB_KEY` | evite; use a PK (`ctid` não é estável) |
| `SELECT ... FROM RDB$DATABASE` | `SELECT ...` sem FROM |
| `WITH LOCK` | `FOR UPDATE` |
| UDFs de `ib_udf`/`rfunc`/UDR (`F_...`, `STRLEN` etc.) | função nativa equivalente; se não houver, crie uma função auxiliar e liste na entrega |
| `SUBSTRING(x FROM a FOR b)`, `COALESCE`, `NULLIF`, `TRIM`, `UPPER`, `LPAD`, `REPLACE`, `POSITION`, `CHAR_LENGTH`, `IS DISTINCT FROM`, `||`, `MOD`, `ROUND`, `TRUNC` | iguais |

### Diferenças silenciosas para sempre verificar

1. **Espaços à direita em strings**: o Firebird ignora espaços à direita ao comparar, inclusive em VARCHAR (`'abc' = 'abc  '` é verdadeiro). No Postgres, em `varchar`/`text`, é falso. Se os dados podem ter espaços à direita (comum em sistemas legados com CHAR), use `rtrim` nas comparações ou limpe os dados.
2. **Maiúsculas em identificadores**: o Firebird converte nomes sem aspas para MAIÚSCULAS; o Postgres, para minúsculas. Nomes que estavam entre aspas no Firebird (`"Nome"`) precisam ser revistos.
3. **Comparações case-sensitive**: collations case-insensitive do Firebird (ex.: `PT_BR` com `_CI`) não se replicam automaticamente, e no Postgres `=` e `LIKE` diferenciam maiúsculas. Use `ILIKE`, `lower()`, `citext` ou collation não determinística, conforme o caso.
4. **SELECT INTO** sem linhas ou com várias linhas (ver Passo 3).
5. **Escala de NUMERIC** em multiplicações e divisões: o Firebird fixa a escala do resultado, o Postgres não. Onde o valor é gravado ou comparado, use `round(..., n)` ou cast explícito.
6. **CURRENT_TIMESTAMP**: é constante durante a procedure no Firebird e durante a transação no Postgres. Se o código mede duração, use `clock_timestamp()`.

## Triggers (quando vierem junto)

No Postgres, um trigger tem duas partes: uma função `RETURNS trigger` e o `CREATE TRIGGER` que liga essa função à tabela.

- `NEW.campo` e `OLD.campo` são usados sem dois-pontos.
- Um `BEFORE INSERT` que altera NEW precisa terminar com `RETURN NEW;`. Triggers AFTER retornam `NULL`.
- `ACTIVE BEFORE INSERT OR UPDATE POSITION 0` vira `BEFORE INSERT OR UPDATE ... FOR EACH ROW`. No Postgres a ordem de disparo é alfabética pelo nome do trigger, então, se a ordem (`POSITION`) importar, renomeie com prefixo numérico.
- `INSERTING` / `UPDATING` / `DELETING` viram `TG_OP = 'INSERT'` / `'UPDATE'` / `'DELETE'`.
- O clássico trigger de autoincremento com generator pode ser trocado por `DEFAULT nextval('g')` ou por coluna `GENERATED ... AS IDENTITY`. Proponha a troca, mas confirme com o usuário.
- Triggers de banco (`ON CONNECT`, `ON TRANSACTION COMMIT`) não têm equivalente direto, porque os event triggers do PG cobrem só DDL. Sinalize.

## Migração em lote

Quando o usuário quiser migrar o banco inteiro:

1. **Extraia o código.** `isql -x -user SYSDBA -password *** banco.fdb > ddl.sql` traz toda a DDL. Para pegar só os corpos: `SELECT RDB$PROCEDURE_NAME, RDB$PROCEDURE_SOURCE FROM RDB$PROCEDURES WHERE COALESCE(RDB$SYSTEM_FLAG, 0) = 0;`.
2. **Ordene por dependência** com `RDB$DEPENDENCIES`: procedures que chamam outras vêm depois. Como o PL/pgSQL só valida dependências na execução, a ordem importa menos para compilar, mas importa para testar.
3. **Crie primeiro a base compartilhada**: a tabela de mapeamento de exceções e as funções auxiliares que substituem UDFs, porque todas as procedures dependem delas.
4. **Converta em blocos pequenos**, mantendo um arquivo por procedure.

## Formato da entrega

Para cada procedure convertida, entregue nesta ordem:

1. **Código PostgreSQL** completo, pronto para rodar no psql, em bloco `sql`.
2. **Pontos de atenção**: lista curta das diferenças de comportamento encontradas *neste* código, cada uma marcada como Alto / Médio / Baixo risco e com o trecho afetado. Cite só o que se aplica, sem repetir a lista genérica inteira.
3. **Mudança na chamada**: como a aplicação chamava antes e como deve chamar agora (ex.: `EXECUTE PROCEDURE SP_X(1)` → `SELECT * FROM sp_x(1)`). É o que o desenvolvedor da aplicação mais precisa.
4. **Teste sugerido**: uma ou duas consultas para rodar nos dois bancos, com os mesmos dados, e comparar o resultado. Cubra principalmente os pontos de risco (caso sem linhas, NULLs, strings com espaços).

Se algo não puder ser convertido com segurança, entregue o restante e deixe no código um comentário `-- TODO MIGRACAO:` explicando o que falta decidir.

## Exemplos

### Selecionável com lógica

```sql
-- Firebird
SET TERM ^ ;
CREATE OR ALTER PROCEDURE SP_PEDIDOS_CLIENTE (P_CLIENTE INTEGER)
RETURNS (ID INTEGER, TOTAL NUMERIC(15,2), STATUS VARCHAR(10))
AS
BEGIN
  FOR SELECT P.ID, P.TOTAL FROM PEDIDOS P
      WHERE P.CLIENTE_ID = :P_CLIENTE
      INTO :ID, :TOTAL
  DO
  BEGIN
    STATUS = IIF(TOTAL > 1000, 'GRANDE', 'NORMAL');
    SUSPEND;
  END
END^
SET TERM ; ^
```

```sql
-- PostgreSQL
CREATE OR REPLACE FUNCTION sp_pedidos_cliente(p_cliente integer)
RETURNS TABLE (id integer, total numeric(15,2), status varchar(10))
LANGUAGE plpgsql
AS $$
BEGIN
  FOR id, total IN
    SELECT p.id, p.total FROM pedidos p WHERE p.cliente_id = p_cliente
  LOOP
    status := CASE WHEN total > 1000 THEN 'GRANDE' ELSE 'NORMAL' END;
    RETURN NEXT;
  END LOOP;
END;
$$;
-- Chamada: SELECT * FROM sp_pedidos_cliente(10);
```

As colunas da query estão qualificadas (`p.id`) porque `id` e `total` também são variáveis de saída.

### Executável com saída e SELECT INTO

```sql
-- Firebird
CREATE PROCEDURE SP_SALDO (P_CONTA INTEGER) RETURNS (SALDO NUMERIC(15,2)) AS
BEGIN
  SALDO = 0;
  SELECT SUM(VALOR) FROM LANCAMENTOS WHERE CONTA_ID = :P_CONTA INTO :SALDO;
END
```

```sql
-- PostgreSQL (conversão fiel)
CREATE OR REPLACE FUNCTION sp_saldo(p_conta integer, OUT saldo numeric(15,2))
LANGUAGE plpgsql
AS $$
BEGIN
  saldo := 0;
  SELECT sum(l.valor) INTO saldo
  FROM lancamentos l WHERE l.conta_id = p_conta;
END;
$$;
-- Antes: EXECUTE PROCEDURE SP_SALDO(5) RETURNING_VALUES :X
-- Agora: x := sp_saldo(5);   ou   SELECT saldo FROM sp_saldo(5);
```

Ponto de atenção (Médio): `SUM` sempre retorna uma linha, com NULL quando não há lançamentos. Por isso o `SALDO = 0` inicial é sobrescrito, e o original já devolvia NULL para conta sem movimento; a conversão mantém esse comportamento. Se a intenção era devolver 0, sugira à parte usar `coalesce(sum(l.valor), 0)` e confirme com o usuário antes de mudar. Faça esse tipo de raciocínio, linha a linha, em cada conversão.