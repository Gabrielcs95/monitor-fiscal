# 🏢 Monitor Fiscal & KYB (Know Your Business)

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite)
![RPA](https://img.shields.io/badge/RPA-Automation-success?style=for-the-badge)

Solução de RPA (Robotic Process Automation) desenvolvida em Python para automatizar a consulta, validação e extração de certidões de regularidade fiscal e trabalhista de empresas (KYB). O robô gerencia o status das consultas em um banco de dados local e salva os comprovantes em diretórios organizados.

## ⚙️ Arquitetura e Estrutura do Projeto

O projeto adota uma estrutura modular, separando banco de dados, arquivos gerados e código-fonte:

```text
monitor-fiscal-kyb/
├── certidoes/          # Diretório onde os PDFs/comprovantes extraídos são salvos
├── database/           # Contém o banco de dados SQLite (monitor_fiscal.db)
├── debug/              # Logs e evidências (screenshots) em caso de falhas na automação
├── src/                # Scripts principais de execução
│   ├── extrator_cndt.py  # Automação para consulta da Certidão Negativa de Débitos Trabalhistas
│   ├── extrator_fgts.py  # Automação para consulta de Regularidade do FGTS
│   └── popular_banco.py  # Script para carga inicial de CNPJs no banco de dados
├── venv/               # Ambiente virtual Python
├── .env                # Variáveis de ambiente (credenciais, caminhos, configurações)
├── .env.example        # Template seguro das variáveis de ambiente
├── .gitignore          # Ignora venv, banco de dados e certidões no repositório
└── requirements.txt    # Dependências do projeto


🚀 Como Funciona
Carga de Dados: O script src/popular_banco.py inicializa o SQLite (database/monitor_fiscal.db) com a lista de CNPJs das empresas que passarão pela auditoria KYB.

Extração FGTS: O src/extrator_fgts.py navega pelo portal da Caixa Econômica, consulta a situação de cada CNPJ e baixa o Certificado de Regularidade do FGTS para a pasta certidoes/.

Extração CNDT: O src/extrator_cndt.py realiza o mesmo procedimento no portal do TST, garantindo que a empresa não possui pendências trabalhistas.

Controle de Estado: O status de cada consulta (Sucesso, Falha, Certidão Positiva) é atualizado no banco de dados, evitando duplicidade de processamento.

🛠️ Instalação e Configuração
1. Clone o repositório:

Bash
git clone [https://github.com/SEU_USUARIO/monitor-fiscal-kyb.git](https://github.com/SEU_USUARIO/monitor-fiscal-kyb.git)
cd monitor-fiscal-kyb
2. Crie e ative o ambiente virtual:

Bash
python -m venv venv
# No Windows:
source venv/Scripts/activate
3. Instale as dependências:

Bash
pip install -r requirements.txt
4. Configure as variáveis de ambiente:
Duplique o arquivo .env.example, renomeie a cópia para .env e preencha as configurações necessárias (o arquivo .env já está no .gitignore e não será enviado ao GitHub).

💻 Execução
Sempre execute os scripts a partir da raiz do projeto, garantindo que o interpretador encontre os caminhos das pastas database e certidoes:

Bash
# 1. Alimente a base de dados
python src/popular_banco.py

# 2. Inicie as extrações
python src/extrator_fgts.py
python src/extrator_cndt.py
👨‍💻 Autor
Gabriel da Silva Costa

LinkedIn : https://LinkedIn.com/in/Gabriel-costa95

Tecnólogo em Gestão de Tecnologia da Informação (GTI)

Automação de Processos (RPA) e Extração de Dados.