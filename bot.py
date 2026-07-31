import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- BANCO DE DADOS ---
conn = sqlite3.connect('financeiro_motoboy_turnos.db', check_same_thread=False)
cursor = conn.cursor()

# Tabela de Turnos
cursor.execute('''
CREATE TABLE IF NOT EXISTS turnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT,
    hora_inicio TEXT,
    hora_fim TEXT,
    km_inicio REAL,
    km_fim REAL,
    arrancada REAL DEFAULT 30.0,
    status TEXT
)
''')

# Tabela de Transações Gerais
cursor.execute('''
CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT,
    tipo TEXT,
    categoria TEXT,
    valor REAL
)
''')

# Tabela Específica de Teles / Entregas da Lancheria
cursor.execute('''
CREATE TABLE IF NOT EXISTS teles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT,
    destino TEXT,
    valor_tele REAL,
    forma_pagamento TEXT,
    valor_dinheiro_recebido REAL DEFAULT 0.0
)
''')
conn.commit()

CUSTO_MANUTENCAO_KM = 0.116  # Desgaste estimado Fan 150 (R$ 0,116/km)

# --- VALORES DAS TELES ---
TAXAS_TELES = {
    'Cidade': 8.00,
    'Passo da Cruz': 13.00,
    'Acacia': 14.00
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🏍️ **Controle Financeiro & Tele-Entrega**\n\n"
        "🟢 /inicio - Iniciar turno (KM e Arrancada)\n"
        "🔴 /fim - Encerrar turno e calcular KM/Manutenção\n\n"
        "📦 /tele - Lançar nova tele-entrega (Cidade, Passo da Cruz, Acácia)\n"
        "📊 /acerto - Acerto de contas do dia com a Lancheria\n\n"
        "💰 /ganho - Registrar ganhos extras (iFood, Uber, etc.)\n"
        "💸 /despesa - Registrar pagamentos (Gasolina, Contas, Lanche)\n"
        "📈 /fluxo - Fluxo de caixa geral (Lucro Líquido Real)"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- TURNO ---
async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT id FROM turnos WHERE data=? AND status='ABERTO'", (hoje,))
    if cursor.fetchone():
        await update.message.reply_text("⚠️ Você já tem um turno aberto hoje! Use /fim para encerrar antes de abrir outro.")
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

# --- REGISTRO DE TELE-ENTREGAS ---
async def tele(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏙️ Cidade (R$ 8,00)", callback_data='tele_destino_Cidade')],
        [InlineKeyboardButton("🌾 Passo da Cruz (R$ 13,00)", callback_data='tele_destino_Passo da Cruz')],
        [InlineKeyboardButton("🌳 Acácia (R$ 14,00)", callback_data='tele_destino_Acacia')]
    ]
    await update.message.reply_text("📦 **Qual o destino da tele?**", reply_markup=InlineKeyboardMarkup(keyboard))

# --- GESTÃO DE BOTÕES (CALLBACKS) ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    prefixo = data[0]

    if prefixo == 'tele':
        sub_tipo = data[1]
        
        if sub_tipo == 'destino':
            destino = data[2]
            context.user_data['tele_destino'] = destino
            context.user_data['tele_valor_taxa'] = TAXAS_TELES[destino]

            keyboard = [
                [InlineKeyboardButton("💵 Dinheiro", callback_data='tele_pag_Dinheiro')],
                [InlineKeyboardButton("💳 Cartão", callback_data='tele_pag_Cartao')],
                [InlineKeyboardButton("📲 Pix", callback_data='tele_pag_Pix')]
            ]
            await query.edit_message_text(
                text=f"Destino: **{destino}** (Taxa: R$ {TAXAS_TELES[destino]:.2f})\n\nComo o cliente pagou a tele?",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )

        elif sub_tipo == 'pag':
            forma_pag = data[2]
            context.user_data['tele_forma_pag'] = forma_pag
            destino = context.user_data.get('tele_destino')
            valor_taxa = context.user_data.get('tele_valor_taxa')

            if forma_pag == 'Dinheiro':
                await query.edit_message_text(
                    text=f"💵 Tele em **Dinheiro** ({destino}).\n\nQual foi o **VALOR TOTAL** recebido do cliente em dinheiro (Lanche + Tele)?\n*(Ex: se o lanche foi 30 e a tele 8, digite `38`)*",
                    parse_mode="Markdown"
                )
                context.user_data['aguardando_valor_dinheiro'] = True
            else:
                hoje = datetime.now().strftime('%Y-%m-%d')
                cursor.execute(
                    "INSERT INTO teles (data, destino, valor_tele, forma_pagamento, valor_dinheiro_recebido) VALUES (?, ?, ?, ?, 0.0)",
                    (hoje, destino, valor_taxa, forma_pag)
                )
                conn.commit()

                # Também registra como ganho nas transações gerais
                cursor.execute("INSERT INTO transacoes (data, tipo, categoria, valor) VALUES (?, 'ganho', ?, ?)", (hoje, f"Tele_{destino}", valor_taxa))
                conn.commit()

                await query.edit_message_text(
                    text=f"✅ **Tele Registrada com Sucesso!**\n📍 Destino: {destino}\n💳 Pagamento: {forma_pag}\n💰 Sua Taxa: R$ {valor_taxa:.2f}",
                    parse_mode="Markdown"
                )

    elif prefixo in ['ganho', 'gasto']:
        tipo, cat = data[0], data[1]
        context.user_data['tipo_pendente'] = tipo
        context.user_data['cat_pendente'] = cat
        acao = "ganho em" if tipo == "ganho" else "pagamento de"
        await query.edit_message_text(text=f"Digite o valor do **{acao} {cat}** (ex: 25.50):", parse_mode="Markdown")

# --- ACERTO DE CONTAS COM A LANCHERIA ---
async def acerto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime('%Y-%m-%d')

    # Buscar arrancada
    cursor.execute("SELECT arrancada FROM turnos WHERE data=?", (hoje,))
    turno = cursor.fetchone()
    arrancada = turno[0] if turno else 30.0

    # Buscar Teles do Dia
    cursor.execute("SELECT destino, valor_tele, forma_pagamento, valor_dinheiro_recebido FROM teles WHERE data=?", (hoje,))
    teles = cursor.fetchall()

    if not teles:
        await update.message.reply_text("⚠️ Nenhuma tele registrada hoje para fazer acerto. Use /tele para registrar.")
        return

    total_teles_qtd = len(teles)
    total_taxas = sum(t[1] for t in teles)
    total_dinheiro_em_mao = sum(t[3] for t in teles)

    cidade_qtd = sum(1 for t in teles if t[0] == 'Cidade')
    passo_qtd = sum(1 for t in teles if t[0] == 'Passo da Cruz')
    acacia_qtd = sum(1 for t in teles if t[0] == 'Acacia')

    pix_cartao_qtd = sum(1 for t in teles if t[2] in ['Pix', 'Cartao'])
    dinheiro_qtd = sum(1 for t in teles if t[2] == 'Dinheiro')

    total_bruto_a_receber = arrancada + total_taxas
    diferenca = total_bruto_a_receber - total_dinheiro_em_mao

    msg = (
        f"📊 **ACERTO DE CONTAS - LANCHERIA ({datetime.now().strftime('%d/%m/%Y')})**\n\n"
        f"🏍️ **Arrancada (Diária):** R$ {arrancada:.2f}\n"
        f"📦 **Total de Teles Feitas:** {total_teles_qtd}\n"
        f"   • Cidade (R$ 8,00): {cidade_qtd}\n"
        f"   • Passo da Cruz (R$ 13,00): {passo_qtd}\n"
        f"   • Acácia (R$ 14,00): {acacia_qtd}\n\n"
        f"💳 **Pagamentos no Pix / Cartão:** {pix_cartao_qtd} teles\n"
        f"💵 **Pagamentos no Dinheiro:** {dinheiro_qtd} teles\n\n"
        f"----------------------------------\n"
        f"💰 **Sua Diária + Taxas (Total Bruto):** R$ {total_bruto_a_receber:.2f}\n"
        f"📥 **Dinheiro dos Lanches em sua Mão:** R$ {total_dinheiro_em_mao:.2f}\n"
        f"----------------------------------\n"
    )

    if diferenca > 0:
        msg += f"✅ **A LANCHERIA DEVE TE PAGAR:** **R$ {diferenca:.2f}**"
    elif diferenca < 0:
        msg += f"⚠️ **VOCÊ DEVE DEVOLVER DE TROCO:** **R$ {abs(diferenca):.2f}**"
    else:
        msg += f"🤝 **CONTA ZERADA!** O dinheiro em mão bateu exatamente com sua diária + taxas."

    await update.message.reply_text(msg, parse_mode="Markdown")

# --- GANHOS E DESPESAS GERAIS ---
async def ganho(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛵 iFood Extra", callback_data='ganho_iFood'), InlineKeyboardButton("📦 Uber/Apps", callback_data='ganho_Uber/Apps')],
        [InlineKeyboardButton("🏢 Particular", callback_data='ganho_Particular'), InlineKeyboardButton("💰 Gorjeta", callback_data='ganho_Gorjeta')]
    ]
    await update.message.reply_text("🟢 **O que você ganhou por fora?**", reply_markup=InlineKeyboardMarkup(keyboard))

async def despesa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⛽ Gasolina", callback_data='gasto_Gasolina'), InlineKeyboardButton("🛠️ Peças/Óleo", callback_data='gasto_Manutencao')],
        [InlineKeyboardButton("🍕 Alimentação", callback_data='gasto_Alimentacao'), InlineKeyboardButton("🏠 Contas/Outros", callback_data='gasto_Contas')]
    ]
    await update.message.reply_text("🔴 **O que você pagou?** Selecione a categoria:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- PROCESSAMENTO DE MENSAGENS ---
async def processar_mensagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    hoje = datetime.now().strftime('%Y-%m-%d')
    hora_atual = datetime.now().strftime('%H:%M')

    # Tratar valor da Tele em Dinheiro
    if context.user_data.get('aguardando_valor_dinheiro'):
        try:
            valor_dinheiro = float(texto.replace(',', '.'))
            destino = context.user_data.pop('tele_destino')
            valor_taxa = context.user_data.pop('tele_valor_taxa')
            forma_pag = context.user_data.pop('tele_forma_pag')
            context.user_data.pop('aguardando_valor_dinheiro')

            cursor.execute(
                "INSERT INTO teles (data, destino, valor_tele, forma_pagamento, valor_dinheiro_recebido) VALUES (?, ?, ?, ?, ?)",
                (hoje, destino, valor_taxa, forma_pag, valor_dinheiro)
            )
            conn.commit()

            cursor.execute("INSERT INTO transacoes (data, tipo, categoria, valor) VALUES (?, 'ganho', ?, ?)", (hoje, f"Tele_{destino}", valor_taxa))
            conn.commit()

            await update.message.reply_text(
                f"✅ **Tele em Dinheiro Registrada!**\n📍 Destino: {destino}\n💰 Sua Taxa: R$ {valor_taxa:.2f}\n💵 Recebido do Cliente: R$ {valor_dinheiro:.2f}",
                parse_mode="Markdown"
            )
            return
        except ValueError:
            await update.message.reply_text("⚠️ Digite um valor numérico válido (ex: 38 ou 45.50).")
            return

    # KM Inicial
    if context.user_data.get('passo_turno') == 'km_inicio':
        try:
            km_in = float(texto.replace(',', '.'))
            cursor.execute("INSERT INTO turnos (data, hora_inicio, km_inicio, arrancada, status) VALUES (?, ?, ?, 30.0, 'ABERTO')", (hoje, hora_atual, km_in))
            conn.commit()
            context.user_data.pop('passo_turno')
            await update.message.reply_text(f"🟢 **Turno Aberto!**\n⏰ Hora: {hora_atual}\n📏 KM Inicial: {km_in} km\n💵 Arrancada: R$ 30,00\n\nBoas entregas! 🏍️💨")
            return
        except ValueError:
            await update.message.reply_text("⚠️ Digite apenas o número do KM.")
            return

    # KM Final
    if context.user_data.get('passo_turno') == 'km_fim':
        try:
            km_fim = float(texto.replace(',', '.'))
            km_in = context.user_data.pop('km_inicio')
            turno_id = context.user_data.pop('turno_id')
            context.user_data.pop('passo_turno')

            if km_fim < km_in:
                await update.message.reply_text("⚠️ O KM final não pode ser menor que o inicial.")
                return

            km_rodados = km_fim - km_in
            reserva_manutencao = km_rodados * CUSTO_MANUTENCAO_KM

            cursor.execute("UPDATE turnos SET hora_fim=?, km_fim=?, status='FECHADO' WHERE id=?", (hora_atual, km_fim, turno_id))
            conn.commit()

            await update.message.reply_text(
                f"🔴 **Turno Encerrado!**\n⏰ Hora: {hora_atual}\n📏 Distância: **{km_rodados:.1f} km**\n🛠️ Reserva Manutenção Fan 150: **R$ {reserva_manutencao:.2f}**\n\nUse /acerto para fazer a conferência com a lancheria!",
                parse_mode="Markdown"
            )
            return
        except ValueError:
            await update.message.reply_text("⚠️ Digite apenas o número do KM.")
            return

    # Transações Gerais
    if 'tipo_pendente' in context.user_data:
        try:
            valor = float(texto.replace(',', '.'))
            tipo = context.user_data.pop('tipo_pendente')
            cat = context.user_data.pop('cat_pendente')

            cursor.execute("INSERT INTO transacoes (data, tipo, categoria, valor) VALUES (?, ?, ?, ?)", (hoje, tipo, cat, valor))
            conn.commit()

            msg_tipo = "🟢 **Entrada Registrada:** +" if tipo == "ganho" else "🔴 **Despesa Registrada:** -"
            await update.message.reply_text(f"{msg_tipo}R$ {valor:.2f} ({cat})", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("⚠️ Digite um valor válido.")

# --- FLUXO COMPLETO ---
async def fluxo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='ganho' AND data=?", (hoje,))
    ganhos = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='gasto' AND data=?", (hoje,))
    gastos = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT km_inicio, km_fim FROM turnos WHERE data=? AND status='FECHADO'", (hoje,))
    turnos_hoje = cursor.fetchall()
    km_total = sum([(t[1] - t[0]) for t in turnos_hoje]) if turnos_hoje else 0.0

    reserva_manut = km_total * CUSTO_MANUTENCAO_KM
    saldo_caixa = ganhos - gastos
    lucro_real = saldo_caixa - reserva_manut

    msg = (
        f"📈 **FLUXO DE CAIXA GERAL ({datetime.now().strftime('%d/%m/%Y')})**\n\n"
        f"🟢 Total de Taxas + Ganhos: R$ {ganhos:.2f}\n"
        f"🔴 Total de Gastos/Contas: R$ {gastos:.2f}\n"
        f"----------------------------------\n"
        f"💵 Saldo Bruto: R$ {saldo_caixa:.2f}\n"
        f"🛠️ Reserva de Manutenção ({km_total:.0f}km): R$ {reserva_manut:.2f}\n"
        f"⭐ **LÚCRO LÍQUIDO REAL:** **R$ {lucro_real:.2f}**"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

if __name__ == '__main__':
    TOKEN = "8899554735:AAE_eCvqX4zmcOP2EM5VaPo8cD1Ast_scWA"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("inicio", inicio))
    app.add_handler(CommandHandler("fim", fim))
    app.add_handler(CommandHandler("tele", tele))
    app.add_handler(CommandHandler("acerto", acerto))
    app.add_handler(CommandHandler("ganho", ganho))
    app.add_handler(CommandHandler("despesa", despesa))
    app.add_handler(CommandHandler("gasto", despesa))
    app.add_handler(CommandHandler("fluxo", fluxo))
    
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_mensagens))

    print("Bot de Finanças e Teles Rodando...")
    app.run_polling()
