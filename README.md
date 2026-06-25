# Bot Controle de Gastos

Bot de Telegram para controle de gastos financeiros familiares com registro automático no Google Sheets. Basta enviar uma mensagem de texto descrevendo o gasto — a IA extrai os dados, pede confirmação e registra na planilha.

---

## Funcionalidades

- Recebe mensagens informais em português: `"café 12,50 débito nubank"`
- Extrai automaticamente descrição, valor, método de pagamento e categoria via IA
- Pede confirmação antes de salvar
- Aceita correções antes de confirmar: `"era lazer, não alimentação"`
- Registra data, hora e nome do usuário na planilha
- Acesso restrito a usuários autorizados
- Roda 24/7 em produção no Railway

---

## Demonstração

```
Você:  café da padaria 12,50 débito nubank
Bot:   ⏳ Processando...

Bot:   📋 Confira o gasto:
       📝 Descrição: Café da padaria
       💰 Valor: R$ 12,50
       💳 Método: Débito Nubank
       🏷️ Categoria: Alimentação

       Responda ok para salvar, cancelar para descartar
       ou corrija o que estiver errado.

Você:  ok
Bot:   ✅ Gasto registrado na planilha!
```

---

## Tecnologias

| Tecnologia | Uso |
|---|---|
| Python 3.11+ | Linguagem principal |
| python-telegram-bot | Interface com o Telegram |
| Groq API (LLaMA 3.3) | Extração de dados com IA |
| gspread + google-auth | Integração com Google Sheets |
| Railway | Hospedagem 24/7 |

---

## Estrutura do Projeto

```
gastos-bot/
├── bot.py              # Fluxo da conversa e handlers do Telegram
├── ia.py               # Extração de dados com IA (Groq)
├── sheets.py           # Gravação no Google Sheets
├── requirements.txt    # Dependências do projeto
├── Procfile            # Configuração de execução no Railway
├── .env                # Variáveis de ambiente (não vai pro Git)
├── .gitignore          # Arquivos ignorados pelo Git
└── credenciais.json    # Credenciais do Google (não vai pro Git)
```

---

## Configuração e Instalação

### Pré-requisitos

- Python 3.11 ou superior
- Conta no Telegram
- Conta Google
- Conta no [Groq](https://console.groq.com)
- Conta no [Railway](https://railway.app) (para deploy)

---

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/gastos-bot.git
cd gastos-bot
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

---

### 4. Crie o bot no Telegram

1. Abra o Telegram e pesquise por `@BotFather`
2. Envie `/newbot` e siga as instruções
3. Guarde o **token** gerado (formato: `123456:ABC-DEF...`)

Para descobrir seu `user_id`, pesquise `@userinfobot` no Telegram e envie qualquer mensagem.

---

### 5. Crie a chave da API do Groq

1. Acesse [console.groq.com](https://console.groq.com)
2. Vá em **API Keys** → **Create API Key**
3. Guarde a chave gerada (começa com `gsk_...`)

---

### 6. Configure o Google Sheets

#### 6.1 Criar o projeto no Google Cloud

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Crie um novo projeto chamado `gastos-bot`
3. Ative as APIs:
   - **Google Sheets API**
   - **Google Drive API**

#### 6.2 Criar a conta de serviço

1. Vá em **APIs e serviços** → **Credenciais**
2. Clique em **Criar credenciais** → **Conta de serviço**
3. Nome: `gastos-bot-sheets` → papel: **Editor**
4. Na aba **Chaves**, clique em **Adicionar chave** → **JSON**
5. Renomeie o arquivo baixado para `credenciais.json` e mova para a raiz do projeto

#### 6.3 Criar a planilha

1. Acesse [sheets.google.com](https://sheets.google.com) e crie uma planilha chamada `Gastos da Família`
2. Na primeira linha, crie os cabeçalhos:

| A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|
| Data | Hora | Descrição | Valor | Método | Categoria | Usuário |

3. Copie o **ID da planilha** da URL:
```
https://docs.google.com/spreadsheets/d/SEU_ID_AQUI/edit
```

#### 6.4 Compartilhar com a conta de serviço

1. Abra o `credenciais.json` e copie o valor de `client_email`
2. Compartilhe a planilha com esse e-mail como **Editor**

---

### 7. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
TELEGRAM_TOKEN=seu_token_aqui
GROQ_API_KEY=gsk_sua_chave_aqui
SPREADSHEET_ID=id_da_sua_planilha
USER_ID_1=seu_user_id
USER_ID_2=user_id_do_segundo_usuario
```

> ⚠️ Nunca compartilhe o `.env` nem o `credenciais.json`. Eles já estão no `.gitignore`.

---

### 8. Execute localmente

```bash
python bot.py
```

Se aparecer no terminal:
```
Bot rodando. Pressione Ctrl+C para parar.
```

Abra o Telegram, encontre seu bot e envie `/start`.

---

## 🚀 Deploy no Railway

### 1. Suba o projeto para o GitHub

```bash
git add .
git commit -m "primeiro commit"
git push origin main
```

> Confirme antes que `.env` e `credenciais.json` **não aparecem** no `git status`.

### 2. Crie o projeto no Railway

1. Acesse [railway.app](https://railway.app) e faça login com GitHub
2. Clique em **New Project** → **Deploy from GitHub repo**
3. Selecione o repositório `gastos-bot`

### 3. Configure as variáveis de ambiente

No painel do Railway, vá em **Variables** e adicione:

```
TELEGRAM_TOKEN
GROQ_API_KEY
SPREADSHEET_ID
USER_ID_1
USER_ID_2
GOOGLE_CREDENTIALS
```

Para a variável `GOOGLE_CREDENTIALS`, converta o `credenciais.json` para uma única linha e cole o resultado:

```bash
python -c "import json; f=open('credenciais.json'); print(json.dumps(json.load(f)))"
```

### 4. Acompanhe o deploy

Em **Deployments** → clique no deploy → **View Logs**. Quando aparecer:

```
Bot rodando. Pressione Ctrl+C para parar.
```

O bot está no ar 24/7.

> ⚠️ Com o bot rodando no Railway, encerre o processo local (`Ctrl+C`) para evitar conflito entre duas instâncias.

---

## Comandos disponíveis

| Comando | Descrição |
|---|---|
| `/start` | Inicia o bot e exibe boas-vindas |
| `/ajuda` | Exibe instruções de uso e métodos aceitos |
| `/cancelar` | Cancela o gasto em andamento |

---

## Categorias e Métodos

**Categorias reconhecidas automaticamente pela IA:**

`Alimentação` · `Transporte` · `Saúde` · `Lazer` · `Casa` · `Educação` · `Vestuário` · `Outros`

**Métodos de pagamento** (configure no `ia.py` conforme seus métodos reais):

`Débito Nubank` · `Crédito Nubank` · `VA Pluxee` · `Pix`

Para adicionar ou alterar métodos, edite a lista `METODOS_PAGAMENTO` em `ia.py`.

---

## Personalização

### Adicionar métodos de pagamento

Em `ia.py`, edite a lista:

```python
METODOS_PAGAMENTO = [
    "Débito Nubank",
    "Crédito Nubank",
    "VA Pluxee",
    "Pix",
    "Dinheiro",       # adicione aqui
]
```

### Adicionar categorias

```python
CATEGORIAS = [
    "Alimentação",
    "Transporte",
    # ...
    "Pet",            # adicione aqui
]
```

### Adicionar mais usuários autorizados

Em `bot.py`, adicione os `user_id` na lista e inclua as variáveis no `.env`:

```python
USUARIOS_PERMITIDOS = {
    int(os.environ["USER_ID_1"]),
    int(os.environ["USER_ID_2"]),
    int(os.environ["USER_ID_3"]),   # adicione aqui
}
```

---

## Licença

MIT License — sinta-se livre para usar, modificar e distribuir.