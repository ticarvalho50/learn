# Skill: Queries com Spark SQL e Amazon Athena

## Visão Geral

Esta skill cobre como escrever e otimizar queries SQL tanto no **Apache Spark (PySpark/Spark SQL)** quanto no **Amazon Athena**, destacando as diferenças, boas práticas e casos de uso de cada um.

---

## Comparativo Rápido

| Característica | Spark SQL | Amazon Athena |
|---|---|---|
| Engine | Apache Spark | Presto / Trino |
| Onde roda | EMR, Glue, Databricks, local | Serverless (AWS gerenciado) |
| Custo | Por cluster (tempo ligado) | Por dado escaneado ($5/TB) |
| Velocidade | Muito rápido para grandes volumes | Rápido para queries ad-hoc |
| Integração | DataFrames, MLlib | Glue Catalog, S3 |
| Dialeto SQL | SQL ANSI + extensões Spark | SQL ANSI + extensões Presto |
| Ideal para | ETL pesado, ML pipelines | Análise ad-hoc, BI, data discovery |

---

## Parte 1: Spark SQL

### Configuração do Ambiente

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("MeuProjeto") \
    .config("spark.sql.shuffle.partitions", "200") \
    .config("spark.sql.adaptive.enabled", "true") \
    .getOrCreate()
```

### Criando Views Temporárias para usar SQL

```python
# Carregar dados
df_vendas = spark.read.parquet("s3://meu-bucket/processed/vendas/")
df_clientes = spark.read.parquet("s3://meu-bucket/processed/clientes/")

# Registrar como views SQL
df_vendas.createOrReplaceTempView("vendas")
df_clientes.createOrReplaceTempView("clientes")
```

---

### Queries Fundamentais no Spark SQL

**Seleção e Filtro:**
```sql
-- Via spark.sql()
resultado = spark.sql("""
    SELECT
        v.id_venda,
        v.data_venda,
        v.valor,
        c.nome,
        c.cidade
    FROM vendas v
    INNER JOIN clientes c ON v.id_cliente = c.id_cliente
    WHERE v.data_venda >= '2024-01-01'
      AND v.valor > 100.0
    ORDER BY v.data_venda DESC
""")

resultado.show(20)
```

**Agregações:**
```sql
SELECT
    c.cidade,
    DATE_FORMAT(v.data_venda, 'yyyy-MM') AS mes,
    COUNT(*)                              AS total_vendas,
    SUM(v.valor)                          AS receita_total,
    AVG(v.valor)                          AS ticket_medio,
    MAX(v.valor)                          AS maior_venda
FROM vendas v
JOIN clientes c ON v.id_cliente = c.id_cliente
GROUP BY c.cidade, DATE_FORMAT(v.data_venda, 'yyyy-MM')
HAVING COUNT(*) > 10
ORDER BY mes DESC, receita_total DESC
```

**Window Functions:**
```sql
SELECT
    id_cliente,
    data_venda,
    valor,
    SUM(valor)  OVER (PARTITION BY id_cliente ORDER BY data_venda
                      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS acumulado,
    LAG(valor, 1, 0) OVER (PARTITION BY id_cliente ORDER BY data_venda) AS venda_anterior,
    RANK()      OVER (PARTITION BY id_cliente ORDER BY valor DESC)       AS rank_valor
FROM vendas
```

**CTEs (Common Table Expressions):**
```sql
WITH receita_mensal AS (
    SELECT
        DATE_FORMAT(data_venda, 'yyyy-MM') AS mes,
        SUM(valor) AS receita
    FROM vendas
    GROUP BY DATE_FORMAT(data_venda, 'yyyy-MM')
),
crescimento AS (
    SELECT
        mes,
        receita,
        LAG(receita) OVER (ORDER BY mes) AS receita_anterior
    FROM receita_mensal
)
SELECT
    mes,
    receita,
    receita_anterior,
    ROUND((receita - receita_anterior) / receita_anterior * 100, 2) AS crescimento_pct
FROM crescimento
WHERE receita_anterior IS NOT NULL
ORDER BY mes
```

---

### Funções Específicas do Spark SQL

**Manipulação de Arrays e Structs:**
```sql
-- Explodir array em linhas
SELECT id_pedido, explode(itens) AS item
FROM pedidos

-- Coletar valores em array
SELECT id_cliente, collect_list(produto) AS produtos_comprados
FROM vendas
GROUP BY id_cliente

-- Acessar campos de struct
SELECT id, endereco.cidade, endereco.estado
FROM clientes
```

**Manipulação de Datas:**
```sql
SELECT
    data_venda,
    year(data_venda)                                   AS ano,
    month(data_venda)                                  AS mes,
    dayofweek(data_venda)                              AS dia_semana,
    datediff(current_date(), data_venda)               AS dias_atras,
    date_trunc('month', data_venda)                    AS inicio_mes,
    date_add(data_venda, 30)                           AS data_mais_30_dias
FROM vendas
```

**Tratamento de Nulos:**
```sql
SELECT
    id,
    coalesce(email, telefone, 'sem_contato')  AS contato,
    nvl(valor, 0)                              AS valor_seguro,
    nullif(desconto, 0)                        AS desconto_real
FROM clientes
```

---

### Leitura e Escrita com SQL no Spark

```python
# Ler tabela do Glue Catalog (com Spark no EMR/Glue)
spark.sql("USE meu_database")
df = spark.sql("SELECT * FROM tabela_vendas WHERE ano = 2024")

# Criar tabela externa no S3
spark.sql("""
    CREATE TABLE IF NOT EXISTS vendas_processadas
    USING PARQUET
    PARTITIONED BY (ano, mes)
    LOCATION 's3://meu-bucket/processed/vendas/'
    AS SELECT * FROM vendas_raw
""")

# Inserir com partição
spark.sql("""
    INSERT INTO vendas_processadas PARTITION (ano=2024, mes=3)
    SELECT id, valor, id_cliente FROM vendas_raw
    WHERE year(data_venda) = 2024 AND month(data_venda) = 3
""")
```

---

## Parte 2: Amazon Athena

### Configuração Inicial

**Pré-requisitos:**
1. Dados no S3 organizados e, preferencialmente, catalogados no AWS Glue
2. Bucket S3 configurado para receber os resultados das queries
3. Permissões IAM adequadas (Athena, S3, Glue)

**Configuração no Console:**
- Acesse Athena → Settings
- Defina o Query result location: `s3://meu-bucket/athena-results/`

---

### DDL: Criando Tabelas no Athena

**Tabela simples com CSV:**
```sql
CREATE EXTERNAL TABLE IF NOT EXISTS meu_database.clientes (
    id_cliente  INT,
    nome        STRING,
    email       STRING,
    cidade      STRING,
    estado      STRING,
    data_cadastro DATE
)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY ','
    LINES TERMINATED BY '\n'
STORED AS TEXTFILE
LOCATION 's3://meu-bucket/raw/clientes/'
TBLPROPERTIES ('skip.header.line.count'='1');
```

**Tabela com Parquet e particionamento:**
```sql
CREATE EXTERNAL TABLE IF NOT EXISTS meu_database.vendas (
    id_venda    BIGINT,
    id_cliente  INT,
    valor       DOUBLE,
    produto     STRING,
    data_venda  TIMESTAMP
)
PARTITIONED BY (
    ano  INT,
    mes  INT
)
STORED AS PARQUET
LOCATION 's3://meu-bucket/processed/vendas/'
TBLPROPERTIES ('parquet.compression'='SNAPPY');

-- Carregar partições existentes no S3
MSCK REPAIR TABLE meu_database.vendas;

-- Ou adicionar partição manualmente
ALTER TABLE meu_database.vendas ADD PARTITION (ano=2024, mes=3)
LOCATION 's3://meu-bucket/processed/vendas/ano=2024/mes=3/';
```

---

### Queries no Athena

**Consultas básicas:**
```sql
-- Athena usa o dialeto Presto/Trino
SELECT
    v.id_venda,
    v.valor,
    c.nome,
    c.cidade,
    date_format(v.data_venda, '%Y-%m') AS mes
FROM meu_database.vendas v
JOIN meu_database.clientes c ON v.id_cliente = c.id_cliente
WHERE v.ano = 2024
  AND v.mes = 3
  AND v.valor > 50.0
ORDER BY v.valor DESC
LIMIT 100;
```

**Funções de data no Athena (Presto):**
```sql
SELECT
    data_venda,
    year(data_venda)                                     AS ano,
    month(data_venda)                                    AS mes,
    day_of_week(data_venda)                              AS dia_semana,
    date_diff('day', data_venda, current_date)           AS dias_atras,
    date_trunc('month', data_venda)                      AS inicio_mes,
    date_add('day', 30, data_venda)                      AS data_mais_30_dias,
    format_datetime(data_venda, 'yyyy-MM-dd HH:mm:ss')   AS data_formatada
FROM meu_database.vendas
WHERE ano = 2024
```

**Agregações e análise:**
```sql
WITH metricas_cidade AS (
    SELECT
        c.cidade,
        c.estado,
        COUNT(DISTINCT v.id_cliente)  AS clientes_ativos,
        COUNT(v.id_venda)             AS total_pedidos,
        SUM(v.valor)                  AS receita_total,
        AVG(v.valor)                  AS ticket_medio
    FROM meu_database.vendas v
    JOIN meu_database.clientes c ON v.id_cliente = c.id_cliente
    WHERE v.ano = 2024
    GROUP BY c.cidade, c.estado
)
SELECT
    *,
    RANK() OVER (PARTITION BY estado ORDER BY receita_total DESC) AS rank_no_estado
FROM metricas_cidade
ORDER BY receita_total DESC;
```

**Trabalhando com JSON no Athena:**
```sql
-- Extrair campo de coluna JSON
SELECT
    id,
    json_extract_scalar(metadata, '$.fonte')      AS fonte,
    json_extract_scalar(metadata, '$.categoria')  AS categoria,
    CAST(json_extract_scalar(metadata, '$.preco') AS DOUBLE) AS preco
FROM meu_database.eventos
WHERE json_extract_scalar(metadata, '$.tipo') = 'compra'
```

**Trabalhando com Arrays no Athena:**
```sql
-- Explodir array
SELECT id_pedido, item
FROM meu_database.pedidos
CROSS JOIN UNNEST(itens) AS t(item)

-- Verificar se elemento está no array
SELECT *
FROM meu_database.pedidos
WHERE contains(tags, 'urgente')

-- Tamanho do array
SELECT id, cardinality(itens) AS qtd_itens
FROM meu_database.pedidos
```

---

### Otimização de Queries no Athena

O Athena cobra por dado escaneado. Reduzir o escaneamento = reduzir custo e aumentar performance.

**1. Usar particionamento:**
```sql
-- MAU: escaneia toda a tabela
SELECT * FROM vendas WHERE year(data_venda) = 2024;

-- BOM: usa a partição diretamente (sem escanear outras partições)
SELECT * FROM vendas WHERE ano = 2024;
```

**2. Usar formatos colunares (Parquet/ORC):**
```sql
-- Só escaneia as colunas necessárias, não a linha inteira
SELECT id_cliente, SUM(valor)
FROM vendas  -- armazenado como Parquet
WHERE ano = 2024
GROUP BY id_cliente;
```

**3. Projetar apenas colunas necessárias:**
```sql
-- MAU: traz tudo
SELECT * FROM clientes;

-- BOM: só o que precisa
SELECT id_cliente, nome, cidade FROM clientes;
```

**4. Usar LIMIT para exploração:**
```sql
-- Durante desenvolvimento/exploração
SELECT * FROM vendas WHERE ano = 2024 LIMIT 100;
```

**5. Compressão dos dados no S3:**
- Preferir Parquet com compressão SNAPPY ou GZIP
- Evitar arquivos muito pequenos (usar Glue para consolidar)
- Tamanho ideal por arquivo: 128MB a 1GB

---

### Usando Athena via boto3 (Python)

```python
import boto3
import time
import pandas as pd

athena_client = boto3.client('athena', region_name='us-east-1')

def executar_query_athena(query: str, database: str, output_bucket: str) -> pd.DataFrame:
    """Executa query no Athena e retorna resultado como DataFrame.

    Args:
        query: Query SQL a ser executada.
        database: Nome do banco de dados no Glue Catalog.
        output_bucket: Bucket S3 para armazenar resultados.

    Returns:
        DataFrame com os resultados da query.
    """
    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': database},
        ResultConfiguration={
            'OutputLocation': f's3://{output_bucket}/athena-results/'
        }
    )

    execution_id = response['QueryExecutionId']

    # Aguardar conclusão
    while True:
        status = athena_client.get_query_execution(QueryExecutionId=execution_id)
        state = status['QueryExecution']['Status']['State']

        if state == 'SUCCEEDED':
            break
        elif state in ('FAILED', 'CANCELLED'):
            reason = status['QueryExecution']['Status']['StateChangeReason']
            raise RuntimeError(f"Query falhou: {reason}")

        time.sleep(2)

    # Buscar resultados
    result_path = (
        status['QueryExecution']['ResultConfiguration']['OutputLocation']
    )
    df = pd.read_csv(result_path, storage_options={'anon': False})
    return df


# Uso
df = executar_query_athena(
    query="""
        SELECT cidade, SUM(valor) AS receita
        FROM meu_database.vendas
        WHERE ano = 2024
        GROUP BY cidade
        ORDER BY receita DESC
    """,
    database="meu_database",
    output_bucket="meu-bucket"
)

print(df.head())
```

---

## Diferenças de Sintaxe: Spark SQL vs Athena (Presto)

| Operação | Spark SQL | Athena (Presto) |
|---|---|---|
| Data atual | `current_date()` | `current_date` |
| Diferença de datas | `datediff(data2, data1)` | `date_diff('day', data1, data2)` |
| Adicionar dias | `date_add(data, 30)` | `date_add('day', 30, data)` |
| Formatar data | `date_format(data, 'yyyy-MM')` | `format_datetime(data, 'yyyy-MM')` |
| Explodir array | `explode(col)` | `CROSS JOIN UNNEST(col) AS t(elem)` |
| Posição em array | `col[0]` (base 0) | `col[1]` (base 1) |
| Regex | `regexp_extract(col, pattern, 1)` | `regexp_extract(col, pattern, 1)` |
| Cast | `CAST(col AS INT)` | `CAST(col AS INTEGER)` |
| Nullif | `nullif(a, b)` | `nullif(a, b)` |
| String → Array | `split(col, ',')` | `split(col, ',')` |

---

## Quando Usar Cada Um?

```
Tamanho do dado pequeno/médio + análise ad-hoc + custo baixo
    → Use Athena

Processamento pesado + ETL + Feature Engineering + integração com MLlib
    → Use Spark SQL (EMR ou Glue)

Precisa de resultado em DataFrame Python rapidamente
    → Athena (boto3 + pandas) ou Spark local

Pipeline automatizado e recorrente com muito dado
    → Spark no EMR ou Glue ETL
```

---

## Referências

- [Spark SQL Documentation](https://spark.apache.org/docs/latest/sql-programming-guide.html)
- [Amazon Athena SQL Reference](https://docs.aws.amazon.com/athena/latest/ug/ddl-sql-reference.html)
- [Presto Functions Reference](https://prestodb.io/docs/current/functions.html)
- [Athena Performance Tuning](https://docs.aws.amazon.com/athena/latest/ug/performance-tuning.html)
- [AWS Glue Data Catalog](https://docs.aws.amazon.com/glue/latest/dg/components-overview.html)
