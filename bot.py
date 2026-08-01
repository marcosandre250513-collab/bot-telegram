import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
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

# Tabela de Fechamentos Diários (Soma da Semana e Mês)
cursor.execute('''
CREATE TABLE IF NOT EXISTS fechamentos_diarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT UNIQUE,
    total_teles INTEGER,
    valor_teles REAL,
    arrancada REAL,
    lucro_liquido_diario REAL
)
''')

# Tabela de Transações Gerais (Gasto/Outros)
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

TAXAS_TELES = {
    'Cidade': 8.00,
    'Passo da Cruz': 13.00,
    'Acacia': 14.00
}

# --- MENU COM BOTÕES RÁPIDOS NA TELA ---
def menu_teclado_principal():
    keyboard = [
        [KeyboardButton("📦 Nova Tele"), KeyboardButton("📊 Fechar Acerto")],
        [KeyboardButton("🟢 Iniciar Turno"), KeyboardButton("🔴 Encerrar Turno")],
        [KeyboardButton("📈 Meus Ganhos (Dia/Sem/Mês)"), KeyboardButton("💸 Registrar Gastos")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🚀 **Controle Rápido de Teles & Ganhos**\n\n"
        "Use os botões na tela para registrar rapidamente suas entregas e acompanhar seus ganhos!"
    )
    await update.message.reply_text(msg, reply_markup=menu_teclado_principal(), parse_mode="Markdown")

# --- REGISTRO DE TELE-ENTREGAS ---
async def tele(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏙️ Cidade (R$ 8,00)", callback_data='tele_destino_Cidade')],
        [InlineKeyboardButton("🌾 Passo da Cruz (R$ 13,00)", callback_data='tele_destino_Passo da Cruz')],
        [InlineKeyboardButton("🌳 Acácia (R$ 14,00)", callback_data='tele_destino_Acacia')]
    ]
    await update.message.reply_text("📦 **Qual o destino da tele?**", reply_markup=InlineKeyboardMarkup(keyboard))

# --- GESTÃO DE BOTÕES INTERATIVOS (INLINE) ---
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
                [InlineKeyboardButton("💳 Pix / Cartão", callback_data='tele_pag_Pix/Cartao')],
                [InlineKeyboardButton("💵 Dinheiro", callback_data='tele_pag_Dinheiro')]
            ]
            await query.edit_message_text(
                text=f"📍 **{destino}** (Taxa R$ {TAXAS_TELES[destino]:.2f})\n\nComo o cliente pagou?",
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
                    text=f"💵 Tele em **Dinheiro** ({destino}).\n\nDigite o **VALOR TOTAL** cobrado do cliente (Lanche + Tele):",
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

                await query.edit_message_text(
                    text=f"✅ **Tele Registrada!**\n📍 Destino: {destino}\n💳 Pagamento: {forma_pag}\n💰 Sua Taxa: R$ {valor_taxa:.2f}",
                    parse_mode="Markdown"
                )

    elif prefixo == 'gasto':
        cat = data[1]
        context.user_data['cat_pendente'] = cat
        await query.edit_message_text(text=f"Digite o valor do gasto com **{cat}** (ex: 20.00):", parse_mode="Markdown")

# --- PROCESSAMENTO DE RESPOSTAS E TEXTOS ---
async def processar_mensagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    hoje = datetime.now().strftime('%Y-%m-%d')
    hora_atual = datetime.now().strftime('%H:%M')

    # Tratar cliques nos Botões do Teclado Principal
    if texto == "📦 Nova Tele":
        await tele(update, context)
        return
    elif texto == "📊 Fechar Acerto":
        await acerto(update, context)
        return
    elif texto == "🟢 Iniciar Turno":
        await inicio(update, context)
        return
    elif texto == "🔴 Encerrar Turno":
        await fim(update, context)
        return
    elif texto == "📈 Meus Ganhos (Dia/Sem/Mês)":
        await meus_ganhos(update, context)
        return
    elif texto == "💸 Registrar Gastos":
        await despesa(update, context)
        return

    # Entrada de valor em Dinheiro da Tele
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

            await update.message.reply_text(
                f"✅ **Tele Registrada!**\n📍 Destino: {destino}\n💰 Sua Taxa: R$ {valor_taxa:.2f}\n💵 Recebido em Dinheiro: R$ {valor_dinheiro:.2f}",
                parse_mode="Markdown",
                reply_markup=menu_teclado_principal()
            )
            return
        except ValueError:
            await update.message.reply_text("⚠️ Digite um valor válido (ex: 38.00).")
            return

    # Entrada de KM Inicial
    if context.user_data.get('passo_turno') == 'km_inicio':
        try:
            km_in = float(texto.replace(',', '.'))
            cursor.execute("INSERT INTO turnos (data, hora_inicio, km_inicio, arrancada, status) VALUES (?, ?, ?, 30.0, 'ABERTO')", (hoje, hora_atual, km_in))
            conn.commit()
            context.user_data.pop('passo_turno')
            await update.message.reply_text(f"🟢 **Turno Aberto!**\n⏰ {hora_atual} | KM: {km_in}\n💵 Arrancada: R$ 30,00", reply_markup=menu_teclado_principal())
            return
        except ValueError:
            await update.message.reply_text("⚠️ Digite apenas números para o KM.")
            return

    # Entrada de KM Final
    if context.user_data.get('passo_turno') == 'km_fim':
        try:
            km_fim = float(texto.replace(',', '.'))
            km_in = context.user_data.pop('km_inicio')
            turno_id = context.user_data.pop('turno_id')
            context.user_data.pop('passo_turno')

            km_rodados = km_fim - km_in
            reserva_manut = km_rodados * CUSTO_MANUTENCAO_KM

            cursor.execute("UPDATE turnos SET hora_fim=?, km_fim=?, status='FECHADO' WHERE id=?", (hora_atual, km_fim, turno_id))
            conn.commit()

            await update.message.reply_text(
                f"🔴 **Turno Encerrado!**\n📏 Distância: **{km_rodados:.1f} km**\n🛠️ Reserva Manutenção Fan 150: **R$ {reserva_manut:.2f}**",
                reply_markup=menu_teclado_principal(),
                parse_mode="Markdown"
            )
            return
        except ValueError:
            await update.message.reply_text("⚠️ Digite apenas números para o KM.")
            return

    # Tratamento de Gastos
    if 'cat_pendente' in context.user_data:
        try:
            valor = float(texto.replace(',', '.'))
            cat = context.user_data.pop('cat_pendente')
            cursor.execute("INSERT INTO transacoes (data, tipo, categoria, valor) VALUES (?, 'gasto', ?, ?)", (hoje, cat, valor))
            conn.commit()

            await update.message.reply_text(f"🔴 **Despesa Registrada:** R$ {valor:.2f} ({cat})", reply_markup=menu_teclado_principal())
        except ValueError:
            await update.message.reply_text("⚠️ Digite um valor numérico válido.")

# --- COMANDOS AUXILIARES ---
async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT id FROM turnos WHERE data=? AND status='ABERTO'", (hoje,))
    if cursor.fetchone():
        await update.message.reply_text("⚠️ Turno já está aberto hoje!")
        return

    await update.message.reply_text("🟢 **Iniciar Turno**\nDigite o **KM INICIAL** da moto:")
    context.user_data['passo_turno'] = 'km_inicio'

async def fim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT id, km_inicio FROM turnos WHERE data=? AND status='ABERTO'", (hoje,))
    turno = cursor.fetchone()
    if not turno:
        await update.message.reply_text("⚠️ Nenhum turno aberto hoje!")
        return

    context.user_data['turno_id'] = turno[0]
    context.user_data['km_inicio'] = turno[1]
    context.user_data['passo_turno'] = 'km_fim'
    await update.message.reply_text("🔴 **Encerrar Turno**\nDigite o **KM FINAL** da moto:")

async def despesa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⛽ Gasolina", callback_data='gasto_Gasolina'), InlineKeyboardButton("🛠️ Manutenção", callback_data='gasto_Manutencao')],
        [InlineKeyboardButton("🍕 Lanche/Comida", callback_data='gasto_Alimentacao'), InlineKeyboardButton("🏠 Outros", callback_data='gasto_Outros')]
    ]
    await update.message.reply_text("🔴 **Qual a categoria da despesa?**", reply_markup=InlineKeyboardMarkup(keyboard))

# --- ACERTO E SALVAMENTO DIÁRIO ---
async def acerto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime('%Y-%m-%d')

    cursor.execute("SELECT arrancada FROM turnos WHERE data=?", (hoje,))
    turno = cursor.fetchone()
    arrancada = turno[0] if turno else 30.0

    cursor.execute("SELECT destino, valor_tele, forma_pagamento, valor_dinheiro_recebido FROM teles WHERE data=?", (hoje,))
    teles = cursor.fetchall()

    if not teles:
        await update.message.reply_text("⚠️ Nenhuma tele registrada hoje para fechar acerto!")
        return

    total_teles_qtd = len(teles)
    total_taxas = sum(t[1] for t in teles)
    total_dinheiro_em_mao = sum(t[3] for t in teles)

    cidade_qtd = sum(1 for t in teles if t[0] == 'Cidade')
    passo_qtd = sum(1 for t in teles if t[0] == 'Passo da Cruz')
    acacia_qtd = sum(1 for t in teles if t[0] == 'Acacia')

    lucro_total_dia = arrancada + total_taxas
    diferenca = lucro_total_dia - total_dinheiro_em_mao

    # Salva ou atualiza a soma na tabela acumuladora do dia
    cursor.execute('''
        INSERT INTO fechamentos_diarios (data, total_teles, valor_teles, arrancada, lucro_liquido_diario)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(data) DO UPDATE SET
            total_teles=excluded.total_teles,
            valor_teles=excluded.valor_teles,
            arrancada=excluded.arrancada,
            lucro_liquido_diario=excluded.lucro_liquido_diario
    ''', (hoje, total_teles_qtd, total_taxas, arrancada, lucro_total_dia))
    conn.commit()

    msg = (
        f"📊 **ACERTO DE CONTAS - LANCHERIA ({datetime.now().strftime('%d/%m/%Y')})**\n\n"
        f"🏍️ **Arrancada:** R$ {arrancada:.2f}\n"
        f"📦 **Total de Teles:** {total_teles_qtd}\n"
        f"   • Cidade (R$ 8,00): {cidade_qtd}\n"
        f"   • Passo da Cruz (R$ 13,00): {passo_qtd}\n"
        f"   • Acácia (R$ 14,00): {acacia_qtd}\n\n"
        f"💰 **Total a Receber (Arrancada + Taxas):** R$ {lucro_total_dia:.2f}\n"
        f"📥 **Dinheiro em Mão dos Lanches:** R$ {total_dinheiro_em_mao:.2f}\n"
        f"----------------------------------\n"
    )

    if diferenca > 0:
        msg += f"✅ **LANCHERIA TE DEVE:** **R$ {diferenca:.2f}**"
    elif diferenca < 0:
        msg += f"⚠️ **VOCÊ DEVE DEVOLVER:** **R$ {abs(diferenca):.2f}**"
    else:
        msg += f"🤝 **CONTA ZERADA!** (Valores bateram exato)"

    msg += "\n\n💾 *Valores somados automaticamente no seu acumulado da semana e mês!*"
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=menu_teclado_principal())

# --- GANHOS ACUMULADOS (HOJE, SEMANA, MÊS) ---
async def meus_ganhos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje_dt = datetime.now()
    hoje_str = hoje_dt.strftime('%Y-%m-%d')
    
    # Calcular início da semana (segunda-feira)
    inicio_semana = (hoje_dt - timedelta(days=hoje_dt.weekday())).strftime('%Y-%m-%d')
    inicio_mes = hoje_dt.strftime('%Y-%m-01')

    # Ganho de Hoje
    cursor.execute("SELECT total_teles, lucro_liquido_diario FROM fechamentos_diarios WHERE data=?", (hoje_str,))
    hoje_dados = cursor.fetchone()
    teles_hoje = hoje_dados[0] if hoje_dados else 0
    ganho_hoje = hoje_dados[1] if hoje_dados else 0.0

    # Ganho da Semana
    cursor.execute("SELECT SUM(total_teles), SUM(lucro_liquido_diario) FROM fechamentos_diarios WHERE data >= ?", (inicio_semana,))
    sem_dados = cursor.fetchone()
    teles_sem = sem_dados[0] or 0
    ganho_sem = sem_dados[1] or 0.0

    # Ganho do Mês
    cursor.execute("SELECT SUM(total_teles), SUM(lucro_liquido_diario) FROM fechamentos_diarios WHERE data >= ?", (inicio_mes,))
    mes_dados = cursor.fetchone()
    teles_mes = mes_dados[0] or 0
    ganho_mes = mes_dados[1] or 0.0

    # Gastos do Mês
    cursor.execute("SELECT SUM(valor) FROM transacoes WHERE tipo='gasto' AND data >= ?", (inicio_mes,))
    gastos_mes = cursor.fetchone()[0] or 0.0

    msg = (
        f"📈 **RESUMO DE GANHOS ACUMULADOS**\n\n"
        f"📅 **Hoje ({hoje_dt.strftime('%d/%m')}):**\n"
        f"   • Teles: {teles_hoje} entregas\n"
        f"   • Ganho Total: **R$ {ganho_hoje:.2f}**\n\n"
        f"🗓️ **Esta Semana (Desde Seg):**\n"
        f"   • Teles: {teles_sem} entregas\n"
        f"   • Ganho Total: **R$ {ganho_sem:.2f}**\n\n"
        f"🗓️ **Este Mês ({hoje_dt.strftime('%m/%Y')}):**\n"
        f"   • Teles Totais: {teles_mes} entregas\n"
        f"   • Faturamento Bruto: **R$ {ganho_mes:.2f}**\n"
        f"   • Gastos/Despesas: R$ {gastos_mes:.2f}\n"
        f"   ⭐ **LÚCRO LÍQUIDO MÊS:** **R$ {(ganho_mes - gastos_mes):.2f}**"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=menu_teclado_principal())

if __name__ == '__main__':
    TOKEN = "8899554735:AAE_eCvqX4zmcOP2EM5VaPo8cD1Ast_scWA"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tele", tele))
    app.add_handler(CommandHandler("acerto", acerto))
    app.add_handler(CommandHandler("meus_ganhos", meus_ganhos))
    app.add_handler(CommandHandler("inicio", inicio))
    app.add_handler(CommandHandler("fim", fim))
    app.add_handler(CommandHandler("despesa", despesa))
    
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_mensagens))

    print("Bot Prático de Teles & Ganhos Rodando...")
    app.run_polling()
