"""
EXTRATOR DO FGTS (CAIXA) - VERSÃO SIMPLES

O que este robô faz:
    1. Lê os CNPJs que estão no banco de dados
    2. Consulta cada um no site da Caixa 
    3. Lê a mensagem que o site mostra e decide o status
    4. Salva no banco: status, data da consulta e detalhes
"""

import os
import re, sys
import sqlite3
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
sys.stdout.reconfigure(encoding='utf-8')


# =============================================================================
# PASSO 1: Caminhos das pastas e do banco de dados
# =============================================================================
# Este arquivo fica dentro da pasta "src". 
PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_DEBUG = os.path.join(PASTA_PROJETO, "debug")  # prints de tela quando der erro
CAMINHO_BANCO = os.path.join(PASTA_PROJETO, "database", "monitor_fiscal.db")

SITE_FGTS = "https://consulta-crf.caixa.gov.br/consultacrf/pages/consultaEmpregador.jsf"

# Cria a pasta debug se ela ainda não existir
os.makedirs(PASTA_DEBUG, exist_ok=True)

# =============================================================================
# PASSO 2: Conectar no banco e preparar as colunas
# =============================================================================
conexao = sqlite3.connect(CAMINHO_BANCO)
banco = conexao.cursor()

# Descobre quais colunas a tabela "empresas" já tem
banco.execute("PRAGMA table_info(empresas)")
colunas_existentes = [linha[1] for linha in banco.fetchall()]

# Cria as colunas que estiverem faltando
for coluna in ["status_fgts", "data_consulta_fgts", "detalhes_fgts"]:
    if coluna not in colunas_existentes:
        banco.execute(f"ALTER TABLE empresas ADD COLUMN {coluna} TEXT")
conexao.commit()

# Pega a lista de CNPJs
banco.execute("SELECT cnpj FROM empresas")
lista_cnpjs = banco.fetchall()
print(f"{len(lista_cnpjs)} CNPJ(s) para consultar.")

# =============================================================================
# PASSO 3: Abrir o Chrome
# =============================================================================
navegador = webdriver.Chrome()
espera = WebDriverWait(navegador, 20)  # espera até 20 segundos por um elemento

# =============================================================================
# PASSO 4: Repetir para cada CNPJ
# =============================================================================
for linha in lista_cnpjs:
    cnpj = linha[0]
    print(f"\n[>] Consultando o CNPJ: {cnpj}")

    # Valores iniciais. Se nada der certo, o resultado final será ERRO.
    status = "ERRO"
    detalhes = "Não foi possível consultar"

    try:
        # ---------------------------------------------------------
        # 4.1 Abre o site e preenche o CNPJ
        # ---------------------------------------------------------
        navegador.get(SITE_FGTS)
        campo_cnpj = espera.until(EC.presence_of_element_located((By.CLASS_NAME, "field-d")))
        campo_cnpj.clear()
        campo_cnpj.send_keys(cnpj)

        # ---------------------------------------------------------
        # 4.2 Clica em "Consultar"
        # ---------------------------------------------------------
        navegador.find_element(By.ID, "mainForm:btnConsultar").click()

        # ---------------------------------------------------------
        # 4.3 Espera a mensagem aparecer e junta todo o texto dela
        # ---------------------------------------------------------
        espera.until(EC.presence_of_element_located((By.CLASS_NAME, "feedback-text")))
        mensagens = navegador.find_elements(By.CLASS_NAME, "feedback-text")

        texto_da_tela = ""
        for mensagem in mensagens:
            texto_da_tela += mensagem.text + " "
        texto_da_tela = texto_da_tela.replace("\n", " ").strip()
        texto_minusculo = texto_da_tela.lower()

        # ---------------------------------------------------------
        # 4.4 Decide o status lendo o texto
        # ---------------------------------------------------------
        # Atenção: a palavra "irregular" CONTÉM a palavra "regular".
        # Por isso testamos a pendência PRIMEIRO.
        if "impediment" in texto_minusculo or "irregular" in texto_minusculo:
            status = "IRREGULAR"
            detalhes = texto_da_tela

        elif re.search(r"\bregular\b", texto_minusculo):
            # \b garante que estamos achando a palavra "regular" sozinha
            status = "REGULAR"
            detalhes = texto_da_tela

            # Tenta ler os detalhes do certificado (validade etc.).
            # Se não conseguir, mantém a mensagem simples.
            try:
                navegador.find_element(By.PARTIAL_LINK_TEXT, "Certificado de Regularidade").click()
                bloco = espera.until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="mainForm"]/fieldset[3]/div'))
                )
                detalhes = bloco.get_attribute("innerText").replace("\n", " ").strip()
            except Exception:
                pass

        else:
            # O site respondeu algo que o robô não conhece
            status = "ERRO"
            detalhes = "Resposta inesperada do site: " + texto_da_tela[:200]

    except Exception as erro:
        # Se qualquer coisa quebrar, o status continua ERRO e guardamos o motivo
        status = "ERRO"
        detalhes = f"Falha no robô: {str(erro)[:200]}"
        print(f"    [ERRO] {erro}")

        # Tira um print da tela para você ver o que aconteceu
        so_numeros = re.sub(r"\D", "", cnpj)
        navegador.save_screenshot(os.path.join(PASTA_DEBUG, f"fgts_erro_{so_numeros}.png"))

    # =========================================================================
    # PASSO 5: Salvar o resultado deste CNPJ no banco
    # =========================================================================
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    banco.execute(
        """
        UPDATE empresas
           SET status_fgts = ?, data_consulta_fgts = ?, detalhes_fgts = ?
         WHERE cnpj = ?
        """,
        (status, agora, detalhes, cnpj),
    )
    conexao.commit()
    print(f"    Status: {status}")
    print(f"    Detalhes: {detalhes}")

# =============================================================================
# PASSO 6: Fechar tudo
# =============================================================================
navegador.quit()
conexao.close()
print("\n=== TRABALHO CONCLUÍDO ===")