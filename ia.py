import os
import json
import logging

from groq import Groq           # cliente oficial do Groq
from dotenv import load_dotenv

# ── Configuração ──────────────────────────────────────────────────────────────

load_dotenv()

logger = logging.getLogger(__name__)

# O cliente lê GROQ_API_KEY automaticamente do ambiente
client = Groq()

# Modelo usado — llama-3.3-70b é potente, gratuito e ótimo para extração de texto
MODELO = "llama-3.3-70b-versatile"

# ── Constantes do domínio ─────────────────────────────────────────────────────

METODOS_PAGAMENTO = [
    "Débito Nubank",
    "Crédito Nubank",
    "Débito C6",
    "Crédito C6",
    "Pluxee",
    "Caju",
    "Pix",
]

CATEGORIAS = [
    "Alimentação",
    "Transporte",
    "Saúde",
    "Lazer",
    "Casa",
    "Educação",
    "Vestuário",
    "Outros",
]

# ── System prompt ─────────────────────────────────────────────────────────────

# O system prompt define as regras fixas para todas as chamadas.
# O Groq usa o padrão de mensagens do OpenAI: lista com role "system" e "user".
SYSTEM_PROMPT = f"""Você é um assistente especializado em extrair dados de gastos financeiros \
de mensagens informais em português brasileiro.

Métodos de pagamento válidos (use exatamente esses valores):
{chr(10).join(f"- {m}" for m in METODOS_PAGAMENTO)}

Categorias válidas (use exatamente esses valores):
{chr(10).join(f"- {c}" for c in CATEGORIAS)}

Regras:
1. Responda APENAS com JSON válido. Sem texto antes ou depois, sem blocos de código.
2. O campo "valor" deve ser um número decimal (float), nunca string.
3. Se o método de pagamento não for mencionado, use null.
4. Escolha a categoria mais adequada com base na descrição do gasto.
5. A descrição deve ser legível e capitalizada. Exemplo: "Café da padaria".
6. Se a mensagem não contiver um gasto financeiro, retorne: {{"erro": "nao_identificado"}}
"""

# ── Função auxiliar ───────────────────────────────────────────────────────────

def _chamar_groq(mensagem: str) -> dict | None:
    """
    Função base que faz a chamada à API do Groq e retorna o dicionário parseado.
    Centraliza o tratamento de erros para não repetir código nas outras funções.
    """
    try:
        resposta = client.chat.completions.create(
            model=MODELO,
            temperature=0,        # zero = respostas mais determinísticas e consistentes
            max_tokens=300,       # gastos são curtos, 300 tokens é mais que suficiente
            messages=[
                {
                    "role": "system",   # regras fixas — a IA segue isso em todas as chamadas
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",     # a mensagem variável que muda a cada chamada
                    "content": mensagem
                }
            ]
        )

        # A resposta fica em choices[0].message.content
        # É uma lista porque o modelo pode gerar múltiplas respostas — pegamos a primeira
        texto_resposta = resposta.choices[0].message.content
        logger.info(f"Resposta da IA: {texto_resposta}")

        # O Groq raramente adiciona blocos de código, mas limpamos por segurança
        texto_limpo = (
            texto_resposta
            .strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )

        return json.loads(texto_limpo)

    except json.JSONDecodeError as e:
        logger.error(f"IA retornou JSON inválido: {e}")
        return None

    except Exception as e:
        logger.error(f"Erro ao chamar a API do Groq: {e}")
        return None

# ── Funções públicas ──────────────────────────────────────────────────────────

def extrair_gasto(texto: str) -> dict | None:
    """
    Recebe texto livre e retorna dicionário com os dados do gasto.
    Retorna None se a mensagem não for reconhecida como gasto.
    """
    logger.info(f"Extraindo gasto de: '{texto}'")

    dados = _chamar_groq(f"Extraia os dados deste gasto: {texto}")

    # Retorna None tanto se a chamada falhou quanto se a IA não identificou gasto
    if dados is None or "erro" in dados:
        logger.info("IA não identificou um gasto na mensagem.")
        return None

    return dados


def corrigir_gasto(gasto_atual: dict, correcao: str) -> dict | None:
    """
    Aplica uma correção do usuário sobre um gasto já extraído.
    Retorna o dicionário atualizado ou None se não entender a correção.
    """
    logger.info(f"Aplicando correção: '{correcao}'")

    # Enviamos o JSON atual + a instrução de correção numa única mensagem
    # A IA devolve o JSON inteiro com a correção já aplicada
    mensagem = (
        f"Gasto atual:\n{json.dumps(gasto_atual, ensure_ascii=False)}\n\n"
        f"Correção do usuário: {correcao}\n\n"
        f"Aplique a correção e retorne o JSON completo atualizado."
    )

    dados = _chamar_groq(mensagem)

    if dados is None or "erro" in dados:
        return None

    return dados


# ── Teste manual ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(message)s",
        level=logging.INFO
    )

    casos_de_teste = [
        "café da padaria 12,50 débito nubank",
        "uber 23 reais pix",
        "mercado 87,30 pluxee",
        "boa tarde",                        # não é gasto — deve retornar None
        "remédio farmácia 45 crédito",
    ]

    print("\n" + "="*50)
    for texto in casos_de_teste:
        print(f"\nEntrada : {texto}")
        resultado = extrair_gasto(texto)
        if resultado:
            print(f"Saída   : {json.dumps(resultado, ensure_ascii=False, indent=2)}")
        else:
            print(f"Saída   : None (não identificado como gasto)")
    print("="*50)