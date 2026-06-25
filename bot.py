import os
import logging

from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# Importa as funções dos módulos que criamos nas etapas anteriores
from ia import extrair_gasto, corrigir_gasto
from sheets import salvar_gasto

# ── Configuração ──────────────────────────────────────────────────────────────

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

'''USUARIOS_PERMITIDOS = {
    int(os.environ["USER_ID_1"]),
    int(os.environ["USER_ID_2"]),
}'''

USUARIOS_PERMITIDOS = {
    int(os.environ["USER_ID_1"]),
}

# ── Estados da conversa ───────────────────────────────────────────────────────

# O ConversationHandler controla em qual estado a conversa está.
# Cada estado define quais funções respondem às mensagens do usuário.
# Temos dois estados possíveis:
AGUARDANDO_GASTO = 1          # esperando o usuário mandar um novo gasto
AGUARDANDO_CONFIRMACAO = 2    # esperando o usuário confirmar, corrigir ou cancelar

# ── Funções auxiliares ────────────────────────────────────────────────────────

def usuario_autorizado(user_id: int) -> bool:
    return user_id in USUARIOS_PERMITIDOS


def formatar_resumo(gasto: dict) -> str:
    """
    Monta a mensagem de resumo do gasto que o bot envia para confirmação.
    Separado em função para não repetir o mesmo bloco em dois lugares.
    """
    metodo = gasto.get("metodo_pagamento") or "não informado"
    return (
        f"📋 *Confira o gasto:*\n\n"
        f"📝 *Descrição:* {gasto.get('descricao', '')}\n"
        f"💰 *Valor:* R$ {gasto.get('valor', 0):.2f}\n"
        f"💳 *Método:* {metodo}\n"
        f"🏷️ *Categoria:* {gasto.get('categoria', '')}\n\n"
        f"Responda *ok* para salvar, *cancelar* para descartar "
        f"ou corrija o que estiver errado.\n"
        f"Exemplo de correção: _era lazer, não alimentação_"
    )

# ── Handlers ──────────────────────────────────────────────────────────────────

async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Boas vindas. Ponto de entrada quando o usuário abre o bot pela primeira vez."""
    if not usuario_autorizado(update.effective_user.id):
        await update.message.reply_text("⛔ Acesso não autorizado.")
        return ConversationHandler.END

    nome = update.effective_user.first_name
    await update.message.reply_text(
        f"Olá, {nome}! 👋\n\n"
        f"Me mande uma mensagem com o gasto e eu registro na planilha.\n\n"
        f"Exemplo: *café da padaria 12,50 débito nubank*",
        parse_mode="Markdown"
    )
    # Retorna o estado inicial — bot está pronto para receber um gasto
    return AGUARDANDO_GASTO


async def comando_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe instruções de uso."""
    if not usuario_autorizado(update.effective_user.id):
        return

    await update.message.reply_text(
        "*Como registrar um gasto:*\n\n"
        "Mande uma mensagem descrevendo o gasto. Pode ser informal:\n\n"
        "• `café da padaria 12,50 débito nubank`\n"
        "• `mercado 87 reais pix`\n"
        "• `uber 23,40 crédito nubank`\n\n"
        "*Métodos aceitos:*\n"
        "Débito Nubank · Crédito Nubank · Débito C6 · Crédito C6 · Pluxee · Pix\n\n"
        "*Categorias:*\n"
        "Alimentação · Transporte · Saúde · Lazer\n"
        "Casa · Educação · Vestuário · Outros",
        parse_mode="Markdown"
    )


async def receber_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Estado: AGUARDANDO_GASTO
    Recebe a mensagem do usuário, chama a IA para extrair os dados
    e pede confirmação. Muda para o estado AGUARDANDO_CONFIRMACAO.
    """
    if not usuario_autorizado(update.effective_user.id):
        return AGUARDANDO_GASTO

    texto = update.message.text
    logger.info(f"Gasto recebido de {update.effective_user.first_name}: '{texto}'")

    # Avisa que está processando — a chamada à IA pode levar 1-2 segundos
    await update.message.reply_text("⏳ Processando...")

    # Chama o ia.py para extrair os dados estruturados
    gasto = extrair_gasto(texto)

    if gasto is None:
        # A IA não identificou um gasto na mensagem
        await update.message.reply_text(
            "❌ Não consegui identificar um gasto nessa mensagem.\n\n"
            "Tente algo como:\n`café 12,50 débito nubank`",
            parse_mode="Markdown"
        )
        # Continua no mesmo estado aguardando uma nova tentativa
        return AGUARDANDO_GASTO

    # Salva o gasto extraído no contexto do usuário
    # context.user_data persiste entre mensagens do mesmo usuário durante a sessão
    context.user_data["gasto_pendente"] = gasto

    # Envia o resumo e muda para o estado de confirmação
    await update.message.reply_text(
        formatar_resumo(gasto),
        parse_mode="Markdown"
    )
    return AGUARDANDO_CONFIRMACAO


async def processar_confirmacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Estado: AGUARDANDO_CONFIRMACAO
    Trata três situações:
      - "ok" / "sim"  → salva no Sheets e volta para AGUARDANDO_GASTO
      - "cancelar"    → descarta e volta para AGUARDANDO_GASTO
      - qualquer outra coisa → trata como correção, reprocessa com IA
                               e continua em AGUARDANDO_CONFIRMACAO
    """
    if not usuario_autorizado(update.effective_user.id):
        return AGUARDANDO_CONFIRMACAO

    resposta = update.message.text.strip().lower()
    gasto = context.user_data.get("gasto_pendente")

    # Segurança: se por algum motivo não houver gasto pendente, reinicia o fluxo
    if gasto is None:
        await update.message.reply_text(
            "⚠️ Não há gasto pendente. Me mande um novo gasto."
        )
        return AGUARDANDO_GASTO

    # ── Confirmação ───────────────────────────────────────────────────────────
    if resposta in ("ok", "sim", "s", "confirmar", "salvar"):

        # Adiciona o nome do usuário ao gasto antes de salvar
        gasto["usuario"] = update.effective_user.first_name

        sucesso = salvar_gasto(gasto)

        if sucesso:
            await update.message.reply_text("✅ Gasto registrado na planilha!")
        else:
            await update.message.reply_text(
                "❌ Erro ao salvar na planilha. Tente novamente."
            )

        # Limpa o gasto pendente e volta ao estado inicial
        context.user_data.clear()
        return AGUARDANDO_GASTO

    # ── Cancelamento ──────────────────────────────────────────────────────────
    if resposta in ("cancelar", "não", "nao", "n", "descartar"):
        await update.message.reply_text("🗑️ Gasto descartado.")
        context.user_data.clear()
        return AGUARDANDO_GASTO

    # ── Correção ──────────────────────────────────────────────────────────────
    # Qualquer outra mensagem é interpretada como uma instrução de correção
    await update.message.reply_text("🔄 Aplicando correção...")

    gasto_corrigido = corrigir_gasto(gasto, resposta)

    if gasto_corrigido is None:
        await update.message.reply_text(
            "❌ Não entendi a correção. Tente descrever o que mudar.\n"
            "Exemplo: _era lazer, não alimentação_",
            parse_mode="Markdown"
        )
        # Continua em AGUARDANDO_CONFIRMACAO com o gasto original
        return AGUARDANDO_CONFIRMACAO

    # Atualiza o gasto pendente com os dados corrigidos
    context.user_data["gasto_pendente"] = gasto_corrigido

    # Mostra o resumo atualizado para nova confirmação
    await update.message.reply_text(
        "✏️ Gasto atualizado:\n\n" + formatar_resumo(gasto_corrigido),
        parse_mode="Markdown"
    )
    return AGUARDANDO_CONFIRMACAO


async def comando_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /cancelar — disponível a qualquer momento.
    Descarta qualquer gasto pendente e reinicia o fluxo.
    """
    context.user_data.clear()
    await update.message.reply_text(
        "🗑️ Operação cancelada. Me mande um novo gasto quando quiser."
    )
    return AGUARDANDO_GASTO

# ── Função principal ──────────────────────────────────────────────────────────

def main():
    logger.info("Iniciando o bot...")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # ConversationHandler gerencia o fluxo de estados da conversa
    conversa = ConversationHandler(
        # entry_points: por onde a conversa pode começar
        # Aceita tanto o comando /start quanto uma mensagem de texto direta
        entry_points=[
            CommandHandler("start", comando_start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, receber_gasto),
        ],
        # states: qual função responde em cada estado
        states={
            AGUARDANDO_GASTO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_gasto),
            ],
            AGUARDANDO_CONFIRMACAO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, processar_confirmacao),
            ],
        },
        # fallbacks: comandos que funcionam em qualquer estado
        fallbacks=[
            CommandHandler("cancelar", comando_cancelar),
            CommandHandler("ajuda", comando_ajuda),
        ],
    )

    app.add_handler(conversa)

    logger.info("Bot rodando. Pressione Ctrl+C para parar.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()