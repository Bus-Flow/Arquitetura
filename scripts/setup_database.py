#!/usr/bin/env python3
"""
===============================================================================
BusFlow - Script de Inicialização e Migração do Banco de Dados RDS PostgreSQL
===============================================================================
Objetivo:
    Executar de forma controlada, segura e idempotente o script DDL oficial:
    src/database/schema_busflow_rds.sql

Uso:
    python scripts/setup_database.py \
        --host <rds_endpoint> \
        --port 5432 \
        --dbname busflowdb \
        --user postgres \
        --password <sua_senha>

Ou configurando as variáveis de ambiente:
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
===============================================================================
"""

import os
import sys
import argparse
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description="Inicializador do Esquema do Banco de Dados BusFlow (RDS PostgreSQL)")
    parser.add_argument("--host", default=os.getenv("DB_HOST", "localhost"), help="Endpoint do RDS PostgreSQL")
    parser.add_argument("--port", type=int, default=int(os.getenv("DB_PORT", "5432")), help="Porta do banco (padrao: 5432)")
    parser.add_argument("--dbname", default=os.getenv("DB_NAME", "busflowdb"), help="Nome do banco de dados (padrao: busflowdb)")
    parser.add_argument("--user", default=os.getenv("DB_USER", "postgres"), help="Usuario do banco (padrao: postgres)")
    parser.add_argument("--password", default=os.getenv("DB_PASSWORD", ""), help="Senha do banco de dados")
    parser.add_argument(
        "--sql-file", 
        default=str(Path(__file__).resolve().parent.parent / "src" / "database" / "schema_busflow_rds.sql"),
        help="Caminho para o arquivo SQL de definicao do schema"
    )
    return parser.parse_args()

def executar_migracao():
    args = parse_args()
    
    sql_path = Path(args.sql_file)
    if not sql_path.exists():
        print(f"[ERRO] Arquivo SQL nao encontrado em: {sql_path}")
        sys.exit(1)
        
    print("=" * 70)
    print("🚌 BUSFLOW — INICIALIZADOR DE BANCO DE DADOS & AUDITORIA")
    print("=" * 70)
    print(f"Host:       {args.host}")
    print(f"Porta:      {args.port}")
    print(f"Database:   {args.dbname}")
    print(f"Usuario:    {args.user}")
    print(f"Script DDL: {sql_path.name}")
    print("=" * 70)
    
    # Tentativa com psycopg2
    try:
        import psycopg2
        print("[1/3] Conectando ao RDS PostgreSQL via psycopg2...")
        conn = psycopg2.connect(
            host=args.host,
            port=args.port,
            dbname=args.dbname,
            user=args.user,
            password=args.password,
            connect_timeout=15
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print("[2/3] Lendo arquivo DDL e executando comandos SQL...")
        with open(sql_path, "r", encoding="utf-8") as f:
            sql_script = f.read()
            
        cur.execute(sql_script)
        
        print("[3/3] Validando entidades criadas...")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tabelas = [r[0] for r in cur.fetchall()]
        
        cur.execute("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        views = [r[0] for r in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        print("-" * 70)
        print("✅ SUCESSO: Esquema do banco de dados provisionado com perfeição!")
        print(f"📊 Tabelas ({len(tabelas)}): {', '.join(tabelas)}")
        print(f"👁️ Views ({len(views)}):   {', '.join(views)}")
        print("=" * 70)
        return
        
    except ImportError:
        print("[AVISO] Driver psycopg2 nao encontrado no ambiente.")
        print("Tentando executar via utilitario 'psql' do sistema operacional...")
        import subprocess
        
        env = os.environ.copy()
        if args.password:
            env["PGPASSWORD"] = args.password
            
        cmd = [
            "psql",
            "-h", args.host,
            "-p", str(args.port),
            "-U", args.user,
            "-d", args.dbname,
            "-f", str(sql_path)
        ]
        
        try:
            res = subprocess.run(cmd, env=env, check=True)
            print("✅ SUCESSO: DDL executado via psql com codigo de retorno 0!")
        except Exception as e:
            print(f"[ERRO] Falha ao executar via psql: {e}")
            print("\nDica: Instale o driver psycopg2 com:")
            print("    pip install psycopg2-binary")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ [ERRO] Falha ao conectar ou aplicar o script no banco:")
        print(f"Detalhes: {e}")
        print("\nVerifique se:")
        print("1. O Security Group do RDS autoriza conexoes da sua maquina ou da EC2.")
        print("2. O endpoint e a senha informados estao corretos.")
        sys.exit(1)

if __name__ == "__main__":
    executar_migracao()
