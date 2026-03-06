# Skill: AWS Services for Data Science

## Visão Geral

Esta skill cobre os principais serviços da AWS utilizados em projetos de Data Science, desde ingestão e armazenamento de dados até treinamento e deploy de modelos de machine learning.

---

## Serviços Principais

### 1. Amazon S3 (Simple Storage Service)

Armazenamento de objetos altamente escalável. É o backbone de qualquer pipeline de dados na AWS.

**Usos em Data Science:**
- Armazenar datasets brutos, processados e features
- Repositório de modelos treinados (artefatos `.pkl`, `.joblib`, `.tar.gz`)
- Data lake centralizado

**Boas práticas:**
- Organizar por partições: `s3://bucket/projeto/ano=2024/mes=03/dia=06/`
- Usar prefixos consistentes para facilitar leitura com Spark e Athena
- Habilitar versionamento em buckets de produção
- Configurar lifecycle policies para mover dados frios para S3 Glacier

```bash
# Upload de dataset
aws s3 cp dataset.csv s3://meu-bucket/raw/dataset.csv

# Sync de diretório inteiro
aws s3 sync ./data/ s3://meu-bucket/raw/

# Listar arquivos com prefixo
aws s3 ls s3://meu-bucket/processed/ --recursive
```

---

### 2. AWS Glue

Serviço de ETL serverless e catálogo de metadados.

**Componentes principais:**
- **Glue Data Catalog:** Catálogo central de metadados (bancos, tabelas, esquemas). Integra diretamente com Athena e Spark
- **Glue ETL Jobs:** Jobs de transformação de dados em PySpark ou Python Shell
- **Glue Crawlers:** Varredura automática de dados no S3 para inferir e registrar esquemas no Catálogo

**Exemplo de Crawler:**
```python
# Configurar crawler via boto3
import boto3

client = boto3.client('glue', region_name='us-east-1')

client.create_crawler(
    Name='meu-crawler',
    Role='arn:aws:iam::123456789:role/GlueRole',
    DatabaseName='meu_database',
    Targets={'S3Targets': [{'Path': 's3://meu-bucket/processed/'}]},
    Schedule='cron(0 6 * * ? *)'  # Todo dia às 6h
)
```

**Exemplo de Glue Job (PySpark):**
```python
from awsglue.context import GlueContext
from pyspark.context import SparkContext

sc = SparkContext()
glueContext = GlueContext(sc)

datasource = glueContext.create_dynamic_frame.from_catalog(
    database="meu_database",
    table_name="raw_vendas"
)

# Transformação
df = datasource.toDF()
df_limpo = df.dropna(subset=["id", "valor"])

# Escrita particionada
df_limpo.write.partitionBy("ano", "mes").parquet("s3://meu-bucket/processed/vendas/")
```

---

### 3. Amazon Athena

Serviço de query interativa serverless sobre dados no S3 usando SQL padrão (Presto/Trino).

> Ver skill dedicada: `aws-spark-athena-queries.md`

---

### 4. Amazon SageMaker

Plataforma completa de Machine Learning gerenciada.

**Componentes mais usados:**

| Componente | Uso |
|---|---|
| **Studio** | IDE baseada em JupyterLab para desenvolvimento |
| **Notebooks** | Instâncias Jupyter gerenciadas |
| **Training Jobs** | Treinamento distribuído e escalável |
| **Endpoints** | Deploy de modelos como API REST |
| **Pipelines** | Orquestração de workflows de ML |
| **Feature Store** | Repositório centralizado de features |
| **Experiments** | Rastreamento de experimentos e métricas |

**Exemplo de Training Job:**
```python
import sagemaker
from sagemaker.sklearn.estimator import SKLearn

estimator = SKLearn(
    entry_point='train.py',
    role='arn:aws:iam::123456789:role/SageMakerRole',
    instance_type='ml.m5.xlarge',
    framework_version='1.2-1',
    hyperparameters={
        'n-estimators': 100,
        'max-depth': 5
    }
)

estimator.fit({'train': 's3://meu-bucket/train/', 'test': 's3://meu-bucket/test/'})
```

**Deploy de modelo:**
```python
predictor = estimator.deploy(
    initial_instance_count=1,
    instance_type='ml.t2.medium'
)

# Inferência
resultado = predictor.predict([[1.5, 2.3, 0.8]])
```

---

### 5. Amazon EMR (Elastic MapReduce)

Cluster gerenciado para processamento distribuído com Spark, Hive, Hadoop.

**Usos em Data Science:**
- Processar datasets muito grandes (TBs) que não cabem em memória
- ETL pesado antes de treinar modelos
- Feature engineering em escala

**Exemplo de submissão de job Spark no EMR:**
```bash
aws emr add-steps \
  --cluster-id j-XXXXXXXXXXXXX \
  --steps Type=Spark,Name="Feature Engineering",\
ActionOnFailure=CONTINUE,\
Args=[--deploy-mode,cluster,s3://meu-bucket/scripts/features.py,\
--input,s3://meu-bucket/raw/,--output,s3://meu-bucket/features/]
```

---

### 6. AWS Lambda

Funções serverless para automação e integração de pipelines.

**Usos em Data Science:**
- Trigger de pipelines ao chegar novos dados no S3
- Pré-processamento leve e chamadas a endpoints SageMaker
- Agendamento de jobs via EventBridge

**Exemplo de trigger S3 → Lambda → SageMaker:**
```python
import boto3
import json

sagemaker_runtime = boto3.client('sagemaker-runtime')

def lambda_handler(event, context):
    # Arquivo chegou no S3
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    payload = json.dumps({'s3_path': f's3://{bucket}/{key}'})

    response = sagemaker_runtime.invoke_endpoint(
        EndpointName='meu-modelo-endpoint',
        ContentType='application/json',
        Body=payload
    )

    resultado = json.loads(response['Body'].read())
    return resultado
```

---

### 7. Amazon Redshift

Data warehouse gerenciado para análise de dados em larga escala.

**Usos em Data Science:**
- Queries analíticas sobre dados estruturados e históricos
- Integração com SageMaker para treinamento direto via Redshift ML
- BI e exploração de dados com ferramentas como QuickSight

```sql
-- Redshift ML: criar modelo diretamente no Redshift
CREATE MODEL churn_model
FROM (SELECT age, tenure, monthly_charges, churn FROM clientes WHERE split = 'train')
TARGET churn
FUNCTION predict_churn
IAM_ROLE 'arn:aws:iam::123456789:role/RedshiftMLRole'
SETTINGS (S3_BUCKET 's3://meu-bucket/redshift-ml/');

-- Usar o modelo para predição
SELECT customer_id, predict_churn(age, tenure, monthly_charges) AS churn_prob
FROM clientes
WHERE split = 'test';
```

---

## Arquitetura Típica de Pipeline de Data Science na AWS

```
[Fontes de dados]
       │
       ▼
[S3 - Raw Layer] ──► [Glue Crawler] ──► [Glue Data Catalog]
       │                                        │
       ▼                                        ▼
[Glue ETL / EMR]                          [Athena Queries]
       │
       ▼
[S3 - Processed / Feature Layer]
       │
       ├──► [SageMaker Training Job]
       │           │
       │           ▼
       │    [SageMaker Model Registry]
       │           │
       │           ▼
       │    [SageMaker Endpoint]
       │
       └──► [Redshift / QuickSight] ──► [BI / Dashboards]
```

---

## IAM: Permissões Essenciais

Roles mínimas necessárias para um projeto de Data Science:

| Role | Permissões |
|---|---|
| `GlueRole` | S3 read/write, Glue full, CloudWatch logs |
| `SageMakerRole` | S3 read/write, SageMaker full, ECR read, CloudWatch logs |
| `LambdaRole` | S3 read, SageMaker invoke endpoint, CloudWatch logs |
| `AthenaRole` | S3 read/write (output), Glue read, Athena full |

---

## Referências

- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [AWS Glue Documentation](https://docs.aws.amazon.com/glue/)
- [Amazon SageMaker Documentation](https://docs.aws.amazon.com/sagemaker/)
- [Amazon EMR Documentation](https://docs.aws.amazon.com/emr/)
- [Amazon Athena Documentation](https://docs.aws.amazon.com/athena/)
