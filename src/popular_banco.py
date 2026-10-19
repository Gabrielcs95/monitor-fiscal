import os
import sqlite3

# 1. Acha o caminho oficial do banco de dados
PASTA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO_BANCO = os.path.join(PASTA_RAIZ, "database", "monitor_fiscal.db")

print(f"Conectando ao banco oficial em: {CAMINHO_BANCO}")

conexao = sqlite3.connect(CAMINHO_BANCO)
banco = conexao.cursor()

# =================================================================
# A MÁGICA AQUI: Deleta a tabela antiga que estava com problema
# =================================================================
banco.execute('DROP TABLE IF EXISTS empresas')

# 2. Cria a tabela novinha em folha com TODAS as colunas certas
banco.execute('''
    CREATE TABLE empresas (
        cnpj TEXT UNIQUE,
        razao_social TEXT,
        status_cndt TEXT,
        data_consulta_cndt TEXT,
        status_fgts TEXT,
        data_consulta_fgts TEXT,
        status_federal TEXT,
        data_consulta_federal TEXT
    )
''')

# 3. Nossos CNPJs de teste
clientes = [
    ('06990590000123', 'PETROLEO BRASILEIRO S A PETROBRAS'),
    ('11111111000191', 'GOOGLE BRASIL INTERNET LTDA'),
    ('33000167000101', 'EMPRESA FICTICIA PARA TESTE DE ERRO LTDA'),
    ('07526557000100', 'AMBEV S.A.'),
    ('33592510000154', 'VALE S.A.'),
    ('47960950000121', 'MAGAZINE LUIZA S.A.')
]

# 4. Insere os clientes lá dentro
for cnpj, razao in clientes:
    try:
        banco.execute("INSERT INTO empresas (cnpj, razao_social) VALUES (?, ?)", (cnpj, razao))
        print(f"[+] Empresa cadastrada: {razao}")
    except sqlite3.IntegrityError:
        print(f"[-] A empresa {razao} já estava cadastrada.")

conexao.commit()
conexao.close()
print("\nBanco de dados populado com sucesso! Tabela corrigida.")