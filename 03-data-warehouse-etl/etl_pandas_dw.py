import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

def extract_load_dimensions():
    load_dotenv()
    
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        database=os.environ.get("DB_NAME", "postgres"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "postgres"),
        port=os.environ.get("DB_PORT", "5432")
    )
    
    # Exemplo: Extração da tabela curso para dim_curso
    query = "SELECT idCurso, nome, grau, turno, campus, nivel FROM universidade.curso"
    df_curso = pd.read_sql(query, conn)
    
    # Transformações
    df_curso['nome'] = df_curso['nome'].str.upper()
    
    # Carga no DW (exemplo salvando local ou carregando em outra tabela)
    os.makedirs('data/processed', exist_ok=True)
    df_curso.to_parquet('data/processed/dim_curso.parquet')
    
    print("ETL via Pandas finalizado com sucesso. Dados salvos em data/processed/")
    
    conn.close()

if __name__ == "__main__":
    extract_load_dimensions()
