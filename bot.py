import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Configuração do Banco de Dados
conn = sqlite3.connect('financeiro_fan150.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT,
    categoria TEXT,
    valor REAL,
    data TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS abastecimentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    km_atual REAL,
    litros REAL,
    valor REAL,
    data TEXT
)
''')
conn.commit()

# --- CONSTANTES FAN 150 ---
CUSTO_MANUTENCAO_KM = 0.116  # R$ 0,116 por km (óleo, pneu, relação, freios)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🏍️ **Controle Financeiro & Consumo - Fan 150**\n\n"
        "Comandos disponíveis:\n"
        "➡️ /ganho - Registrar entrada\n"
        "➡️ /gasto - Registrar saída\n"
        "➡️ /abastecer - Registrar combustível e KM\n"
        "➡️ /resumo - Balanço de hoje e custos"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def ganho(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛵 iFood", callback_data='ganho_iFood'), InlineKeyboardButton("📦 Uber/99", callback_data='ganho_App')],
        [InlineKeyboardButton("🏢 Particular", callback_data='ganho_Particular'), InlineKeyboardButton("💰 Gorjeta", callback_data='ganho_Gorjeta')]
    ]
    await update.message.reply_text("Selecione a origem do ganho:", reply_markup=InlineKeyboardMarkup(keyboard))

async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⛽ Gasolina", callback_data='gasto_Gasolina'), InlineKeyboardButton("🛠️ Óleo/Manutenção", callback_data='gasto_Manutencao')],
        [InlineKeyboardButton("🍕 Alimentação", callback_data='gasto_Alimentacao'), InlineKeyboardButton("📦 Outros", callback_data='gasto_Outros')]
    ]
    await update.message.reply_text("Selecione a categoria do gasto:", reply_markup=InlineKeyboardMarkup(keyboard))

async def abastecer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⛽ **Registro de Abastecimento**\n"
        "Envie os dados no formato: `KM_ATUAL LITROS VALOR`\n"
        "Exemplo: `45200 10.5 63.00`",
        parse_mode="Markdown"
    )
    context.user_data['aguardando_abastecimento'] = True

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    tipo, cat = data[0], data[1]
    
    context.user_data['tipo_pendente'] = tipo
    context.user_data['cat_pendente'] = cat
    
    await query.edit_message_text(text=f"Digite o valor de **{cat}** (ex: 25.50):", parse_mode="Markdown")

async def processar_mensagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()

    # Processar Registro de Abastecimento
    if context.user_data.get('aguardando_abastecimento'):
        try:
            partes = texto.split()
            km_atual = float(partes[0].replace(',', '.'))
            litros = float(partes[1].replace(',', '.'))
            valor = float(partes[2].replace(',', '.'))
            hoje = datetime.now().strftime('%Y-%m-%d')

            # Buscar último abastecimento para calcular a média
            cursor.execute("SELECT km_atual FROM abastecimentos ORDER BY id DESC LIMIT 1")
            ultimo = cursor.fetchone()

            media_str = ""
            if ultimo:
                km_rodados = km_atual - ultimo[0]
                if km_rodados > 0:
                    media = km_rodados / litros
                    custo_km_gasolina = valor / km_rodados
                    custo_total_km = custo_km_gasolina + CUSTO_MANUTENCAO_KM
                    media_str = (
                        f"\n📏 **Distância percorrida:** {km_rodados:.1f} km\n"
                        f"📊 **Média atual:** {media:.2f} km/l\n"
                        f"💸 **Custo total por km:** R$ {custo_total_km:.2f}/km"
                    )

            cursor.execute("INSERT INTO abastecimentos (km_atual, litros, valor, data) VALUES (?, ?, ?, ?)", (km_atual, litros, valor, hoje))
            cursor.execute("INSERT INTO transacoes (tipo, categoria, valor, data) VALUES ('gasto', 'Gasolina', ?, ?)", (valor, hoje))
            conn.commit()

            context.user_data['aguardando_abastecimento'] = False
            await update.message.reply_text(f"✅ **Abastecimento registrado!**{media_str}", parse_mode="Markdown")
            return
        except (IndexError, ValueError):
            await update.message.reply_text("⚠️ Formato incorreto! Use: `KM_ATUAL LITROS VALOR` (ex: `45200 10.5 63.00`)", parse_mode="Markdown")
            return

    # Processar Entradas/Saídas comuns
    if 'tipo_pendente' in context.user_data:
        try:
            valor = float(texto.replace(',', '.'))
            tipo = context.user_data.pop('tipo_pendente')
            cat = context.user_data.pop('cat_pendente')
            hoje = datetime.now().strftime('%Y-%m-%d')

            cursor.execute("INSERT INTO transacoes (tipo, categoria, valor, data) VALUES (?, ?, ?, ?)", (tipo, cat, valor, hoje))
            conn.commit()

            simbolo = "🟢" if tipo == "ganho" else "🔴"
            await update.message.reply_text(f"{simbolo} **Registrado:** R$ {valor:.2f} em {cat}", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("⚠️ Valor inválido. Digite apenas números (ex: 15 ou 15.50).")

async def resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='ganho' AND data=?", (hoje,))
    ganhos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='gasto' AND data=?", (hoje,))
    gastos = cursor.fetchone()[0] or 0.0

    lucro = ganhos - gastos

    msg = (
        f"📊 **Balanço Diário - Fan 150 ({datetime.now().strftime('%d/%m/%Y')})**\n\n"
        f"🟢 Bruto (Entradas): **R$ {ganhos:.2f}**\n"
        f"🔴 Despesas (Combustível/Manutenção): **R$ {gastos:.2f}**\n"
        f"💵 **Lucro Líquido Real: R$ {lucro:.2f}**\n"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")

if __name__ == '__main__':
    TOKEN = ""8804109455:AAHeMGTy2A12ePXD3fjS_n_MST8oVY7oN8k
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ganho", ganho))
    app.add_handler(CommandHandler("gasto", gasto))
    app.add_handler(CommandHandler("abastecer", abastecer))
    app.add_handler(CommandHandler("resumo", resumo))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_mensagens))

    print("Bot Fan 150 rodando...")
    app.run_polling()
