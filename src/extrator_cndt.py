
import glob
import importlib
import os, sys
import re
import shutil
import sqlite3
import time
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

try:
    PdfReader = importlib.import_module("pypdf").PdfReader
except ModuleNotFoundError:
    PdfReader = importlib.import_module("PyPDF2").PdfReader

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
 
# =============================================================================
# PASSO 1: Caminhos das pastas e do banco de dados
# =============================================================================
# Este arquivo fica dentro da pasta "src". A pasta do projeto é a pasta acima.
PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
 
PASTA_CERTIDOES = os.path.join(PASTA_PROJETO, "certidoes")             # PDFs finais
PASTA_TEMPORARIA = os.path.join(PASTA_PROJETO, "debug", "temporaria")  # downloads
PASTA_DEBUG = os.path.join(PASTA_PROJETO, "debug")                     # imagem do captcha
CAMINHO_BANCO = os.path.join(PASTA_PROJETO, "database", "monitor_fiscal.db")
 
SITE_TST = "https://cndt-certidao.tst.jus.br/gerarCertidao"
 
# Cria as pastas se elas ainda não existirem
os.makedirs(PASTA_CERTIDOES, exist_ok=True)
os.makedirs(PASTA_TEMPORARIA, exist_ok=True)
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
for coluna in ["status_cndt", "data_consulta_cndt", "validade_cndt", "detalhes_cndt", "pdf_cndt"]:
    if coluna not in colunas_existentes:
        banco.execute(f"ALTER TABLE empresas ADD COLUMN {coluna} TEXT")
conexao.commit()
 
# Pega a lista de CNPJs
banco.execute("SELECT cnpj FROM empresas")
lista_cnpjs = banco.fetchall()
print(f"{len(lista_cnpjs)} CNPJ(s) para consultar.")
 
# =============================================================================
# PASSO 3: Abrir o Chrome (configurado para baixar PDFs na pasta temporária)
# =============================================================================
opcoes_chrome = webdriver.ChromeOptions()
opcoes_chrome.add_experimental_option("prefs", {
    "download.default_directory": PASTA_TEMPORARIA,
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True,
})
 
navegador = webdriver.Chrome(options=opcoes_chrome)
espera = WebDriverWait(navegador, 20)  # espera até 20 segundos por um elemento
 
# =============================================================================
# PASSO 4: Repetir para cada CNPJ
# =============================================================================
for linha in lista_cnpjs:
    cnpj = linha[0]
    print(f"\n[>] Consultando o CNPJ: {cnpj}")
 
    # Valores iniciais. Se nada der certo, o resultado final será ERRO.
    status = "ERRO"
    validade = None
    detalhes = "Não foi possível consultar"
    caminho_pdf = None
 
    try:
        # O captcha pode dar errado, então damos até 3 chances
        for tentativa in range(1, 4):
            print(f"    Tentativa {tentativa} de 3")
 
            # Apaga qualquer PDF que tenha sobrado na pasta temporária
            for arquivo in glob.glob(os.path.join(PASTA_TEMPORARIA, "*")):
                os.remove(arquivo)
 
            # ---------------------------------------------------------
            # 4.1 Abre o site e preenche o CNPJ
            # ---------------------------------------------------------
            navegador.get(SITE_TST)
            campo_cnpj = espera.until(EC.presence_of_element_located((By.ID, "cpfCnpj")))
            campo_cnpj.clear()
            campo_cnpj.send_keys(cnpj)
 
            # ---------------------------------------------------------
            
            texto_captcha = input("    Digite o captcha (ou aperte Enter para pular): ").strip()
            if texto_captcha == "":
                detalhes = "Consulta pulada pelo usuário"
                break  # sai das tentativas e vai para o próximo CNPJ
 
            campo_captcha = espera.until(EC.presence_of_element_located((By.ID, "captcha-resposta")))
            campo_captcha.clear()
            campo_captcha.send_keys(texto_captcha)
 
            # ---------------------------------------------------------
            # 4.3 Clica em "Emitir Certidão"
            # ---------------------------------------------------------
            botao_emitir = espera.until(EC.element_to_be_clickable((By.ID, "botao-emitir")))
            botao_emitir.click()
 
            # ---------------------------------------------------------
            # 4.4 Espera até 30 segundos: ou o PDF baixa, ou o site avisa erro
            # ---------------------------------------------------------
            resultado = "demorou"
            for segundo in range(30):
                time.sleep(1)
 
                pdfs = glob.glob(os.path.join(PASTA_TEMPORARIA, "*.pdf"))
                downloads_incompletos = glob.glob(os.path.join(PASTA_TEMPORARIA, "*.crdownload"))
                if pdfs and not downloads_incompletos:
                    resultado = "baixou"
                    break
 
                texto_da_tela = navegador.find_element(By.TAG_NAME, "body").text.lower()
                if "inválido" in texto_da_tela or "incorreto" in texto_da_tela or "não confere" in texto_da_tela:
                    resultado = "captcha_errado"
                    break
 
            # Se o captcha estava errado, volta para o começo e tenta de novo
            if resultado == "captcha_errado":
                print("    [!] Captcha recusado. Vamos tentar de novo.")
                detalhes = "Captcha recusado pelo site"
                continue
 
            # Se não baixou e não deu aviso, algo estranho aconteceu
            if resultado == "demorou":
                detalhes = "O site não devolveu o PDF a tempo"
                break
 
            # ---------------------------------------------------------
            # 4.5 Deu certo! Move o PDF para a pasta final com um nome organizado
            # ---------------------------------------------------------
            pdf_baixado = pdfs[0]
            cnpj_so_numeros = re.sub(r"\D", "", cnpj)  # tira pontos, barra e traço
            data_arquivo = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho_pdf = os.path.join(PASTA_CERTIDOES, f"CNDT_{cnpj_so_numeros}_{data_arquivo}.pdf")
            shutil.move(pdf_baixado, caminho_pdf)
 
            # ---------------------------------------------------------
            # 4.6 Lê o texto do PDF para descobrir se é NEGATIVA ou POSITIVA
            # ---------------------------------------------------------
            leitor_pdf = PdfReader(caminho_pdf)
            texto_pdf = ""
            for pagina in leitor_pdf.pages:
                texto_pdf += pagina.extract_text() or ""
            texto_pdf = texto_pdf.lower()
 
            # Importante: testamos "positiva" ANTES de "negativa", porque o texto
            # da certidão positiva também pode citar a palavra "negativa".
            if "positiva" in texto_pdf:
                if "mesmos efeitos" in texto_pdf:
                    status = "ATENCAO"
                else:
                    status = "IRREGULAR"
            elif "negativa" in texto_pdf:
                status = "REGULAR"
            else:
                status = "ERRO"
                detalhes = "PDF baixado, mas não reconheci o tipo da certidão"
 
            # Procura a data de validade, por exemplo: "Validade: 25/03/2027"
            achou = re.search(r"validade\D{0,10}(\d{2}/\d{2}/\d{4})", texto_pdf)
            if achou:
                validade = achou.group(1)
 
            if status != "ERRO":
                detalhes = f"Certidão classificada como {status}"
 
            break  # terminou este CNPJ, sai das tentativas
 
    except Exception as erro:
        # Se qualquer coisa quebrar, o status continua ERRO e guardamos o motivo
        status = "ERRO"
        detalhes = f"Falha no robô: {str(erro)[:200]}"
        print(f"    [ERRO] {erro}")
 
    # =========================================================================
    # PASSO 5: Salvar o resultado deste CNPJ no banco
    # =========================================================================
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    banco.execute(
        """
        UPDATE empresas
           SET status_cndt = ?, data_consulta_cndt = ?, validade_cndt = ?,
               detalhes_cndt = ?, pdf_cndt = ?
         WHERE cnpj = ?
        """,
        (status, agora, validade, detalhes, caminho_pdf, cnpj),
    )
    conexao.commit()
    print(f"    Status: {status} | Validade: {validade} | {detalhes}")
 
# =============================================================================
# PASSO 6: Fechar tudo
# =============================================================================
navegador.quit()
conexao.close()
print("\n=== TRABALHO CONCLUÍDO ===")
 