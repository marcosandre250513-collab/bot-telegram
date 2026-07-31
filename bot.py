import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Configuração do Banco de Dados SQLite
conn = sqlite3.connect('financeiro_motoboy_turnos.db', check_same_thread=False)
cursor = conn.cursor()

# Tabela de Turnos (Início e Fim)
cursor.execute('''
CREATE TABLE IF NOT EXISTS turnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT,
    hora_inicio TEXT,
    hora_fim TEXT,
    km_inicio REAL,
    km_fim REAL,
    status TEXT
)
''')

# Tabela de Ganhos e Gastos
cursor.execute('''
CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT,
    tipo TEXT,
    categoria TEXT,
    valor REAL
)
''')
conn.commit()

CUSTO_MANUTENCAO_KM = 0.116  # Estimativa de desgaste por KM para Fan 150 2015

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🏍️ **Controle Profissional de Turnos & Ganhos**\n\n"
        "🟢 /inicio - Abrir turno (KM e Hora inicial)\n"
        "🔴 /fim - Fechar turno (KM e Hora final)\n"
        "💰 /ganho - Registrar entrada por categoria\n"
        "💸 /gasto - Registrar combustível/alimentação\n"
        "📊 /resumo - Ver balanço do dia e rendimento por KM\n"
        "📋 /tabela - Exibir histórico recente de ganhos"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- INÍCIO DE TURNO ---
async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT id FROM turnos WHERE data=? AND status='ABERTO'", (hoje,))
    if cursor.fetchone():
        await update.message.reply_text("⚠️ Você já tem um turno aberto hoje! Envie /fim para encerrar antes de abrir outro.")
        return

    await update.message.reply_text("🟢 **Iniciar Turno**\nEnvie o **KM INICIAL** da moto no painel (ex: `45200`):")
    context.user_data['passo_turno'] = 'km_inicio'

# --- FIM DE TURNO ---
async def fim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT id, km_inicio FROM turnos WHERE data=? AND status='ABERTO'", (hoje,))
    turno = cursor.fetchone()
    if not turno:
        await update.message.reply_text("⚠️ Nenhum turno aberto encontrado para hoje! Use /inicio para começar um.")
        return

    context.user_data['turno_id'] = turno[0]
    context.user_data['km_inicio'] = turno[1]
    context.user_data['passo_turno'] = 'km_fim'
    await update.message.reply_text("🔴 **Encerrar Turno**\nEnvie o **KM FINAL** do painel da moto (ex: `45330`):")

# --- REGISTRO DE GANHOS ---
async def ganho(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛵 iFood", callback_data='ganho_iFood'), InlineKeyboardButton("📦 Uber/99", callback_data='ganho_Uber/Apps')],
        [InlineKeyboardButton("🏢 Particular", callback_data='ganho_Particular'), InlineKeyboardButton("💰 Gorjeta", callback_data='ganho_Gorjeta')]
    ]
    await update.message.reply_text("Selecione a origem do ganho:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- REGISTRO DE GASTOS ---
async def gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⛽ Gasolina", callback_data='gasto_Gasolina'), InlineKeyboardButton("🍕 Alimentação", callback_data='gasto_Alimentacao')],
        [InlineKeyboardButton("🛠️ Manutenção", callback_data='gasto_Manutencao'), InlineKeyboardButton("📦 Outros", callback_data='gasto_Outros')]
    ]
    await update.message.reply_text("Selecione a categoria da despesa:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    tipo, cat = data[0], data[1]
    
    context.user_data['tipo_pendente'] = tipo
    context.user_data['cat_pendente'] = cat
    await query.edit_message_text(text=f"Digite o valor de **{cat}** (ex: 35.50):", parse_mode="Markdown")

# --- PROCESSAMENTO DE MENSAGENS ---
async def processar_mensagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    hoje = datetime.now().strftime('%Y-%m-%d')
    hora_atual = datetime.now().strftime('%H:%M')

    # Tratar Início de Turno
    if context.user_data.get('passo_turno') == 'km_inicio':
        try:
            km_in = float(texto.replace(',', '.'))
            cursor.execute("INSERT INTO turnos (data, hora_inicio, km_inicio, status) VALUES (?, ?, ?, 'ABERTO')", (hoje, hora_atual, km_in))
            conn.commit()
            context.user_data.pop('passo_turno')
            await update.message.reply_text(f"🟢 **Turno Aberto!**\n⏰ Hora: {hora_atual}\n📏 KM Inicial: {km_in} km\n\nBoa rodagem e boas entregas! 🏍️💨")
            return
        except ValueError:
            await update.message.reply_text("⚠️ KM inválido. Digite apenas o número (ex: 45200).")
            return

    # Tratar Fim de Turno
    if context.user_data.get('passo_turno') == 'km_fim':
        try:
            km_fim = float(texto.replace(',', '.'))
            km_in = context.user_data.pop('km_inicio')
            turno_id = context.user_data.pop('turno_id')
            context.user_data.pop('passo_turno')

            if km_fim < km_in:
                await update.message.reply_text("⚠️ O KM final não pode ser menor que o KM inicial. Tente novamente.")
                return

            km_rodados = km_fim - km_in
            reserva_manutencao = km_rodados * CUSTO_MANUTENCAO_KM

            cursor.execute("UPDATE turnos SET hora_fim=?, km_fim=?, status='FECHADO' WHERE id=?", (hora_atual, km_fim, turno_id))
            conn.commit()

            msg = (
                f"🔴 **Turno Encerrado com Sucesso!**\n\n"
                f"⏰ Horário: até {hora_atual}\n"
                f"📏 KM Rodados: **{km_rodados:.1f} km**\n"
                f"🛠️ Reserva de Manutenção estimada (Fan 150): **R$ {reserva_manutencao:.2f}**"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
            return
        except ValueError:
            await update.message.reply_text("⚠️ KM inválido. Digite apenas o número.")
            return

    # Tratar Lançamento de Ganhos / Gastos
    if 'tipo_pendente' in context.user_data:
        try:
            valor = float(texto.replace(',', '.'))
            tipo = context.user_data.pop('tipo_pendente')
            cat = context.user_data.pop('cat_pendente')

            cursor.execute("INSERT INTO transacoes (data, tipo, categoria, valor) VALUES (?, ?, ?, ?)", (hoje, tipo, cat, valor))
            conn.commit()

            simbolo = "🟢" if tipo == "ganho" else "🔴"
            await update.message.reply_text(f"{simbolo} **Registrado:** R$ {valor:.2f} em {cat} na data {datetime.now().strftime('%d/%m/%Y')}", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("⚠️ Digite um valor numérico válido (ex: 20.50).")

# --- GERAR TABELA DE GANHOS NO TELEGRAM ---
async def tabela(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("""
        SELECT data, categoria, SUM(valor) 
        FROM transacoes 
        WHERE tipo='ganho' 
        GROUP BY data, categoria 
        ORDER BY data DESC LIMIT 10
    """)
    registros = cursor.fetchall()

    if not registros:
        await update.message.reply_text("Nenhum ganho registrado ainda.")
        return

    texto_tabela = "📋 **Tabela de Ganhos Recentes**\n\n"
    texto_tabela += "`Data       | Origem     | Valor`\n"
    texto_tabela += "`----------------------------------`\n"

    for reg in registros:
        dt_fmt = datetime.strptime(reg[0], '%Y-%m-%d').strftime('%d/%m')
        cat = reg[1].ljust(10)
        val = f"R$ {reg[2]:.2f}".rjust(9)
        texto_tabela += f"`{dt_fmt}      | {cat} | {val}`\n"

    await update.message.reply_text(texto_tabela, parse_mode="Markdown")

# --- RESUMO COMPLETO ---
async def resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='ganho' AND data=?", (hoje,))
    ganhos = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='gasto' AND data=?", (hoje,))
    gastos = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT km_inicio, km_fim FROM turnos WHERE data=? AND status='FECHADO'", (hoje,))
    turnos_hoje = cursor.fetchall()
    km_total_hoje = sum([(t[1] - t[0]) for t in turnos_hoje]) if turnos_hoje else 0.0

    reserva_manut = km_total_hoje * CUSTO_MANUTENCAO_KM
    lucro_liquido = ganhos - gastos - reserva_manut

    msg = (
        f"📊 **Balanço Diário ({datetime.now().strftime('%d/%m/%Y')})**\n\n"
        f"🟢 Total Bruto: **R$ {ganhos:.2f}**\n"
        f"🔴 Despesas Diretas: **R$ {gastos:.2f}**\n"
        f"🛠️ Reserva Manutenção ({km_total_hoje:.0f}km): **R$ {reserva_manut:.2f}**\n"
        f"----------------------------------\n"
        f"💵 **Lucro Líquido Real: R$ {lucro_liquido:.2f}**"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

if __name__ == '__main__':
    TOKEN = "8804109455:AAHeMGTy2A12ePXD3fjS_n_MST8oVY7oN8k"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("inicio", inicio))
    app.add_handler(CommandHandler("fim", fim))
    app.add_handler(CommandHandler("ganho", ganho))
    app.add_handler(CommandHandler("gasto", gasto))
    app.add_handler(CommandHandler("tabela", tabela))
    app.add_handler(CommandHandler("resumo", resumo))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_mensagens))

    print("Bot de Turnos & Controle Rodando...")
    app.run_polling()
