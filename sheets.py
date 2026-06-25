import os
import logging
from datetime import datetime

import gspread                                      # biblioteca para manipular Google Sheets
from google.oauth2.service_account import Credentials   # autenticação via conta de serviço
from dotenv import load_dotenv

# ── Configuração ──────────────────────────────────────────────────────────────

load_dotenv()

logger = logging.getLogger(__name__)

# Escopos de permissão que solicitamos ao Google
# Precisamos dos dois para o gspread funcionar corretamente
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",  # leitura e escrita nas planilhas
    "https://www.googleapis.com/auth/drive",          # acesso aos arquivos do Drive
]

# Caminho para o arquivo de credenciais JSON baixado do Google Cloud
# Fica na raiz do projeto junto com o bot.py
CREDENCIAIS_PATH = os.path.join(os.path.dirname(__file__), "credenciais.json")

# ID da planilha — lido do .env
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]

# Nome da aba onde os dados serão gravados
# Se quiser separar por mês no futuro, é só mudar esse valor dinamicamente
NOME_ABA = "Página1"

# ── Conexão com o Sheets ──────────────────────────────────────────────────────

def _conectar() -> gspread.Worksheet:
    """
    Cria e retorna a conexão com a aba da planilha.
    Chamada a cada gravação para evitar problemas com tokens expirados
    em bots que ficam rodando por dias sem reiniciar.
    """
    # Carrega as credenciais do arquivo JSON com os escopos definidos acima
    credenciais = Credentials.from_service_account_file(
        CREDENCIAIS_PATH,
        scopes=SCOPES
    )

    # Autoriza o cliente gspread com essas credenciais
    cliente = gspread.authorize(credenciais)

    # Abre a planilha pelo ID e retorna a aba pelo nome
    planilha = cliente.open_by_key(SPREADSHEET_ID)
    return planilha.worksheet(NOME_ABA)

# ── Funções públicas ──────────────────────────────────────────────────────────

def salvar_gasto(gasto: dict) -> bool:
    """
    Grava uma nova linha na planilha com os dados do gasto.

    Espera um dicionário com as chaves:
        descricao, valor, metodo_pagamento, categoria, usuario

    Retorna True se salvou com sucesso, False se houve erro.
    """
    try:
        aba = _conectar()

        # Captura o momento exato do registro
        agora = datetime.now()
        data = agora.strftime("%d/%m/%Y")   # formato brasileiro: 24/06/2025
        hora = agora.strftime("%H:%M:%S")   # formato 24h: 16:05:42

        # Monta a linha na mesma ordem dos cabeçalhos da planilha:
        # Data | Hora | Descrição | Valor | Método | Categoria | Usuário
        nova_linha = [
            data,
            hora,
            gasto.get("descricao", ""),
            gasto.get("valor", 0),
            gasto.get("metodo_pagamento", ""),
            gasto.get("categoria", ""),
            gasto.get("usuario", ""),
        ]

        # append_row adiciona a linha após a última linha preenchida
        # value_input_option="USER_ENTERED" faz o Sheets interpretar os valores
        # como se o usuário tivesse digitado — números ficam como número, não texto
        aba.append_row(nova_linha, value_input_option="USER_ENTERED")

        logger.info(f"Gasto salvo: {nova_linha}")
        return True

    except Exception as e:
        logger.error(f"Erro ao salvar no Sheets: {e}")
        return False


# ── Teste manual ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(message)s",
        level=logging.INFO
    )

    # Gasto de teste — simula o que viria do ia.py
    gasto_teste = {
        "descricao": "Café da padaria",
        "valor": 12.50,
        "metodo_pagamento": "Débito Nubank",
        "categoria": "Alimentação",
        "usuario": "Adriel",
    }

    print("Salvando gasto de teste na planilha...")
    sucesso = salvar_gasto(gasto_teste)

    if sucesso:
        print("✅ Linha gravada com sucesso! Confira a planilha.")
    else:
        print("❌ Erro ao gravar. Verifique o log acima.")