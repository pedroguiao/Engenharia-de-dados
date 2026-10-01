# Data Engineering & Analytics Modernization

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Data Warehouse](https://img.shields.io/badge/Data_Warehouse-FF6F00?style=for-the-badge&logo=amazon-redshift&logoColor=white)

## Sobre o Projeto

O projeto simula um ciclo completo de dados: uma base transacional relacional (PostgreSQL), a migração para um modelo orientado a documentos (MongoDB) e a criação de um Data Warehouse analítico (Star Schema) via processos ETL em Python.

## Diagrama de Arquitetura

```mermaid
flowchart LR
    subgraph OLTP ["1. Fontes Transacionais (OLTP)"]
        direction TB
        PG["🐘 PostgreSQL<br><i>(Relacional / Normalizado)</i>"]
        MDB["🍃 MongoDB<br><i>(NoSQL / Documentos)</i>"]
    end

    subgraph ETL ["2. Ingestão & Processamento"]
        direction TB
        HOP["🔄 Apache Hop<br><i>(Workflows .hpl)</i>"]
        PY["🐍 Python & Pandas<br><i>(Scripts ETL / Upsert)</i>"]
    end

    subgraph OLAP ["3. Camada Analítica (OLAP)"]
        direction TB
        DW[("🏛️ Data Warehouse<br><i>(Star Schema)</i>")]
        BI["📊 Consultas OLAP & BI"]
    end

    PG -->|Batch| HOP
    PG -->|CDC / Extração| PY
    MDB -->|Extração| PY

    HOP -->|Fatos| DW
    PY -->|Dimensões| DW
    DW -->|Leitura| BI

    classDef default fill:#161b22,stroke:#30363d,stroke-width:1px,color:#c9d1d9;
    classDef source fill:#1c2128,stroke:#58a6ff,stroke-width:1.5px,color:#f0f6fc;
    classDef proc fill:#1c2128,stroke:#a371f7,stroke-width:1.5px,color:#f0f6fc;
    classDef dest fill:#1c2128,stroke:#3fb950,stroke-width:1.5px,color:#f0f6fc;

    class PG,MDB source;
    class HOP,PY proc;
    class DW,BI dest;
```

## Estrutura e Camadas do Projeto

### `01-relational-postgres/` (Camada Transacional OLTP)
Opera sobre PostgreSQL na 3ª Forma Normal (3FN), focado em consistência ACID. Inclui a aplicação Flask original do portal universitário. O modelo normalizado protege a integridade dos dados durante a escrita, mas exige múltiplos JOINs que lentificam a leitura de agregados.

### `02-nosql-mongodb/` (Migração e Operação NoSQL)
Implementa a versão orientada a documentos (MongoDB) do banco de dados. A desnormalização acelera o acesso conjunto às informações, porém introduz a necessidade de atualizações múltiplas. Como o MongoDB não assegura chaves estrangeiras, a integridade referencial é delegada para a aplicação, sendo gerida no Flask e validada via JSON Schema.

### `03-data-warehouse-etl/` (Camada Analítica DW & OLAP)
Centraliza a estrutura dimensional (Star/Snowflake Schema) otimizada para leitura agregada. O isolamento no Data Warehouse previne que consultas pesadas de relatórios consumam recursos da base de produção. A carga é realizada por pipelines extraindo da base relacional e do MongoDB usando Pandas (`etl_pandas_dw.py`) e Apache Hop (`.hpl`).

### `docs/`
Mapeamentos de esquema, diagramas e relatórios de implementação técnica.

## Execução

### 1. Clonar o Repositório
```bash
git clone https://github.com/seu-usuario/Engenharia-de-dados.git
cd Engenharia-de-dados
```

### 2. Configurar o Ambiente Virtual
```bash
python3 -m venv venv
source venv/bin/activate  # No Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurar as Variáveis de Ambiente
Copie o modelo de variáveis para criar o arquivo `.env`. Edite-o informando os URIs locais ou em nuvem para o PostgreSQL e o MongoDB:
```bash
cp .env.example .env
```

### 4. Executando os Módulos

**Módulo Relacional (PostgreSQL):**
```bash
cd 01-relational-postgres
# Certifique-se de que o banco PostgreSQL está rodando
python app2.py
```

**Módulo NoSQL (MongoDB):**
```bash
cd 02-nosql-mongodb
# Realiza carga/upsert no banco
python ETL.py --apply
# Inicia a aplicação web
python app.py
```

**Módulo Data Warehouse:**
```bash
cd 03-data-warehouse-etl
# Roda a extração em Pandas
python etl_pandas_dw.py
```
