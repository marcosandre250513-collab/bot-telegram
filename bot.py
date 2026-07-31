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

# Tabela de Transações (Ganhos e Gastos/Despesas)
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

CUSTO_MANUTENCAO_KM = 0.116  # Desgaste estimado Fan 150 (R$ 0,116/km)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🏍️ **Controle Financeiro Profissional - Fan 150**\n\n"
        "🟢 /inicio - Iniciar turno (KM inicial)\n"
        "🔴 /fim - Encerrar turno (KM final e cálculo de manutenção)\n\n"
        "💰 /ganho - Registrar o que ENTROU (iFood, Uber, Particular, Gorjeta)\n"
        "💸 /despesa - Registrar o que SAIU (Gasolina, Manutenção, Lanche, Contas)\n\n"
        "📈 /fluxo - Fluxo de Caixa (Total Ganho - Total Pago = Saldo Real)\n"
        "📋 /tabela_ganhos - Ver histórico recente de entradas\n"
        "📑 /tabela_gastos - Ver histórico recente de pagamentos/despesas"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- CONTROLE DE TURNOS ---
async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT id FROM turnos WHERE data=? AND status='ABERTO'", (hoje,))
    if cursor.fetchone():
        await update.message.reply_text("⚠️ Você já tem um turno aberto hoje! Envie /fim para encerrar antes de abrir outro.")
        return

    await update.message.reply_text("🟢 **Iniciar Turno**\nEnvie o **KM INICIAL** do painel da Fan 150 (ex: `45200`):")
    context.user_data['passo_turno'] = 'km_inicio'

async def fim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT id, km_inicio FROM turnos WHERE data=? AND status='ABERTO'", (hoje,))
    turno = cursor.fetchone()
    if not turno:
        await update.message.reply_text("⚠️ Nenhum turno aberto encontrado para hoje! Use /inicio para começar.")
        return

    context.user_data['turno_id'] = turno[0]
    context.user_data['km_inicio'] = turno[1]
    context.user_data['passo_turno'] = 'km_fim'
    await update.message.reply_text("🔴 **Encerrar Turno**\nEnvie o **KM FINAL** do painel (ex: `45330`):")

# --- REGISTRO DE GANHOS (ENTRADAS) ---
async def ganho(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛵 iFood", callback_data='ganho_iFood'), InlineKeyboardButton("📦 Uber/Apps", callback_data='ganho_Uber/Apps')],
        [InlineKeyboardButton("🏢 Particular", callback_data='ganho_Particular'), InlineKeyboardButton("💰 Gorjeta", callback_data='ganho_Gorjeta')]
    ]
    await update.message.reply_text("🟢 **O que você ganhou?** Selecione a origem:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- REGISTRO DE DESPESAS (SAÍDAS / PAGAMENTOS) ---
async def despesa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⛽ Gasolina", callback_data='gasto_Gasolina'), InlineKeyboardButton("🛠️ Peças/Óleo", callback_data='gasto_Manutencao')],
        [InlineKeyboardButton("🍕 Alimentação", callback_data='gasto_Alimentacao'), InlineKeyboardButton("🏠 Contas/Outros", callback_data='gasto_Contas')]
    ]
    await update.message.reply_text("🔴 **O que você pagou?** Selecione a categoria da despesa:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    tipo, cat = data[0], data[1]
    
    context.user_data['tipo_pendente'] = tipo
    context.user_data['cat_pendente'] = cat
    
    acao = "ganho em" if tipo == "ganho" else "pagamento de"
    await query.edit_message_text(text=f"Digite o valor do **{acao} {cat}** (ex: 25.50):", parse_mode="Markdown")

# --- PROCESSAMENTO DE MENSAGENS ---
async def processar_mensagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    hoje = datetime.now().strftime('%Y-%m-%d')
    hora_atual = datetime.now().strftime('%H:%M')

    # Tratar KM Inicial
    if context.user_data.get('passo_turno') == 'km_inicio':
        try:
            km_in = float(texto.replace(',', '.'))
            cursor.execute("INSERT INTO turnos (data, hora_inicio, km_inicio, status) VALUES (?, ?, ?, 'ABERTO')", (hoje, hora_atual, km_in))
            conn.commit()
            context.user_data.pop('passo_turno')
            await update.message.reply_text(f"🟢 **Turno Aberto!**\n⏰ Hora: {hora_atual}\n📏 KM Inicial: {km_in} km\n\nBoas entregas! 🏍️💨")
            return
        except ValueError:
            await update.message.reply_text("⚠️ Digite apenas o número do KM (ex: 45200).")
            return

    # Tratar KM Final
    if context.user_data.get('passo_turno') == 'km_fim':
        try:
            km_fim = float(texto.replace(',', '.'))
            km_in = context.user_data.pop('km_inicio')
            turno_id = context.user_data.pop('turno_id')
            context.user_data.pop('passo_turno')

            if km_fim < km_in:
                await update.message.reply_text("⚠️ O KM final não pode ser menor que o inicial. Tente novamente.")
                return

            km_rodados = km_fim - km_in
            reserva_manutencao = km_rodados * CUSTO_MANUTENCAO_KM

            cursor.execute("UPDATE turnos SET hora_fim=?, km_fim=?, status='FECHADO' WHERE id=?", (hora_atual, km_fim, turno_id))
            conn.commit()

            msg = (
                f"🔴 **Turno Encerrado!**\n\n"
                f"⏰ Horário: até {hora_atual}\n"
                f"📏 Distância percorrida: **{km_rodados:.1f} km**\n"
                f"🛠️ Reserva de Manutenção estimada: **R$ {reserva_manutencao:.2f}**"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
            return
        except ValueError:
            await update.message.reply_text("⚠️ Digite apenas o número do KM.")
            return

    # Tratar Lançamento de Valores
    if 'tipo_pendente' in context.user_data:
        try:
            valor = float(texto.replace(',', '.'))
            tipo = context.user_data.pop('tipo_pendente')
            cat = context.user_data.pop('cat_pendente')

            cursor.execute("INSERT INTO transacoes (data, tipo, categoria, valor) VALUES (?, ?, ?, ?)", (hoje, tipo, cat, valor))
            conn.commit()

            if tipo == "ganho":
                await update.message.reply_text(f"🟢 **Entrada Registrada:** +R$ {valor:.2f} ({cat})", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"🔴 **Despesa Registrada:** -R$ {valor:.2f} ({cat})", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("⚠️ Digite um valor válido (ex: 30.00).")

# --- TABELA DE GANHOS ---
async def tabela_ganhos(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    texto = "📋 **Tabela de Ganhos Recentes**\n\n"
    texto += "`Data       | Origem     | Valor`\n"
    texto += "`----------------------------------`\n"

    for reg in registros:
        dt_fmt = datetime.strptime(reg[0], '%Y-%m-%d').strftime('%d/%m')
        cat = reg[1].ljust(10)
        val = f"R$ {reg[2]:.2f}".rjust(9)
        texto += f"`{dt_fmt}      | {cat} | {val}`\n"

    await update.message.reply_text(texto, parse_mode="Markdown")

# --- TABELA DE DESPESAS ---
async def tabela_gastos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("""
        SELECT data, categoria, SUM(valor) 
        FROM transacoes 
        WHERE tipo='gasto' 
        GROUP BY data, categoria 
        ORDER BY data DESC LIMIT 10
    """)
    registros = cursor.fetchall()

    if not registros:
        await update.message.reply_text("Nenhuma despesa registrada ainda.")
        return

    texto = "📑 **Tabela de Despesas Pagas**\n\n"
    texto += "`Data       | Categoria  | Valor`\n"
    texto += "`----------------------------------`\n"

    for reg in registros:
        dt_fmt = datetime.strptime(reg[0], '%Y-%m-%d').strftime('%d/%m')
        cat = reg[1].ljust(10)
        val = f"R$ {reg[2]:.2f}".rjust(9)
        texto += f"`{dt_fmt}      | {cat} | {val}`\n"

    await update.message.reply_text(texto, parse_mode="Markdown")

# --- FLUXO DE CAIXA COMPLETO ---
async def fluxo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='ganho' AND data=?", (hoje,))
    ganhos = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='gasto' AND data=?", (hoje,))
    gastos = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT km_inicio, km_fim FROM turnos WHERE data=? AND status='FECHADO'", (hoje,))
    turnos_hoje = cursor.fetchall()
    km_total_hoje = sum([(t[1] - t[0]) for t in turnos_hoje]) if turnos_hoje else 0.0

    reserva_manut = km_total_hoje * CUSTO_MANUTENCAO_KM
    saldo_caixa = ganhos - gastos
    lucro_real = saldo_caixa - reserva_manut

    msg = (
        f"📈 **Fluxo de Caixa do Dia ({datetime.now().strftime('%d/%m/%Y')})**\n\n"
        f"🟢 **O que Entrou (Ganhos):** R$ {ganhos:.2f}\n"
        f"🔴 **O que Saiu (Pagamentos):** R$ {gastos:.2f}\n"
        f"----------------------------------\n"
        f"💵 **Saldo Atual em Mão:** R$ {saldo_caixa:.2f}\n"
        f"🛠️ **Guardar p/ Manutenção ({km_total_hoje:.0f}km):** R$ {reserva_manut:.2f}\n\n"
        f"⭐ **LÚCRO LÍQUIDO LIMPO:** **R$ {lucro_real:.2f}**"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

if __name__ == '__main__':
    # SEU NOVO TOKEN CONFIGURADO:
    TOKEN = "8899554735:AAE_eCvqX4zmcOP2EM5VaPo8cD1Ast_scWA"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("inicio", inicio))
    app.add_handler(CommandHandler("fim", fim))
    app.add_handler(CommandHandler("ganho", ganho))
    app.add_handler(CommandHandler("despesa", despesa))
    app.add_handler(CommandHandler("gasto", despesa))  # Atalho /gasto também funciona
    app.add_handler(CommandHandler("fluxo", fluxo))
    app.add_handler(CommandHandler("tabela_ganhos", tabela_ganhos))
    app.add_handler(CommandHandler("tabela_gastos", tabela_gastos))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_mensagens))

    print("Bot de Finanças e Turnos Rodando...")
    app.run_polling()
