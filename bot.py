import sqlite3
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- BANCO DE DADOS ---
conn = sqlite3.connect('financeiro_motoboy_turnos.db', check_same_thread=False)
cursor = conn.cursor()

def criar_tabelas():
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

    # Tabela de Teles
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS teles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        destino TEXT,
        valor_tele REAL,
        quantidade INTEGER DEFAULT 1,
        forma_pagamento TEXT,
        valor_dinheiro_recebido REAL DEFAULT 0.0
    )
    ''')

    # Tabela de Fechamentos Diários
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

    # Tabela de Transações e Gastos Gerais
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        tipo TEXT,
        categoria TEXT,
        valor REAL
    )
    ''')

    # Tabela Específica para Controle de Abastecimento
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS abastecimentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        km_atual REAL,
        litros REAL,
        valor_total REAL,
        km_rodados_desde_ultimo REAL,
        media_kml REAL
    )
    ''')
    conn.commit()

criar_tabelas()

CUSTO_MANUTENCAO_KM = 0.116  # Desgaste estimado Fan 150 (R$ 0,116/km)

TAXAS_TELES = {
    'Cidade': 8.00,
    'Passo da Cruz': 13.00,
    'Acacia': 14.00
}

FRASES_MOTIVACIONAIS = [
    "🚀 Excelente! Mais uma pra conta, acelera!",
    "💰 Dinheiro no bolso! O trabalho duro compensa!",
    "🏍️💨 Bora pra próxima que a noite tá só começando!",
    "🔥 Ritmo forte! Cada corrida te deixa mais perto do objetivo!",
    "🏆 Boa, monstro das entregas! Mantenha a atenção e o foco!",
    "💪 Mais uma concluída com sucesso! Pilote com segurança!",
    "📊 O faturamento não para de subir! Acelera!"
]

def menu_teclado_principal():
    keyboard = [
        [KeyboardButton("📦 Nova Tele"), KeyboardButton("📊 Fechar Acerto")],
        [KeyboardButton("🟢 Iniciar Turno"), KeyboardButton("🔴 Encerrar Turno")],
        [KeyboardButton("📈 Meus Ganhos (Dia/Sem/Mês)"), KeyboardButton("🗓️ Histórico de Acertos")],
        [KeyboardButton("💸 Registrar Gastos"), KeyboardButton("⛽ Média de Combustível")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def atualizar_tabela_diaria(hoje):
    cursor.execute("SELECT arrancada FROM turnos WHERE data=?", (hoje,))
    turno = cursor.fetchone()
    arrancada = turno[0] if turno else 30.0

    cursor.execute("SELECT valor_tele, quantidade FROM teles WHERE data=?", (hoje,))
    teles = cursor.fetchall()
    
    total_qtd = sum(t[1] for t in teles)
    total_valor = sum(t[0] * t[1] for t in teles)
    total_liquido = arrancada + total_valor

    cursor.execute('''
        INSERT INTO fechamentos_diarios (data, total_teles, valor_teles, arrancada, lucro_liquido_diario)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(data) DO UPDATE SET
            total_teles=excluded.total_teles,
            valor_teles=excluded.valor_teles,
            arrancada=excluded.arrancada,
            lucro_liquido_diario=excluded.lucro_liquido_diario
    ''', (hoje, total_qtd, total_valor, arrancada, total_liquido))
    conn.commit()
    
    return total_qtd, total_liquido

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🚀 **Controle Profissional de Teles & Moto**\n\n"
        "Use os botões abaixo para registrar entregas, gastos, médias de consumo e acertos!\n"
        "ℹ️ *Para apagar todo o banco de dados e recomeçar do zero, digite:* `/zerar`"
    )
    await update.message.reply_text(msg, reply_markup=menu_teclado_principal(), parse_mode="Markdown")

async def zerar_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⚠️ SIM, ZERAR TUDO!", callback_data='confirmar_zerar_sim')],
        [InlineKeyboardButton("❌ Cancelar", callback_data='confirmar_zerar_nao')]
    ]
    await update.message.reply_text(
        "🚨 **ATENÇÃO! VOCÊ ESTÁ PRESTES A ZERAR TUDO!** 🚨\n\n"
        "Isso apagar todos os registros de teles, acertos, turnos, gastos e abastecimentos do banco de dados.\n\n"
        "Tem certeza que deseja continuar?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def tele(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏙️ Cidade (R$ 8,00)", callback_data='tele_destino_Cidade')],
        [InlineKeyboardButton("🌾 Passo da Cruz (R$ 13,00)", callback_data='tele_destino_Passo da Cruz')],
        [InlineKeyboardButton("🌳 Acácia (R$ 14,00)", callback_data='tele_destino_Acacia')]
    ]
    await update.message.reply_text("📦 **Qual o destino da tele?**", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    prefixo = data[0]

    # Confirmação de Zerar Tudo
    if prefixo == 'confirmar':
        acao = data[2]
        if acao == 'sim':
            cursor.execute("DELETE FROM turnos")
            cursor.execute("DELETE FROM teles")
            cursor.execute("DELETE FROM fechamentos_diarios")
            cursor.execute("DELETE FROM transacoes")
            cursor.execute("DELETE FROM abastecimentos")
            conn.commit()
            
            await query.edit_message_text(
                "💥 **TODOS OS DADOS FORAM ZERADOS COM SUCESSO!**\n\nO banco de dados foi limpo e está pronto para novos registros.",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ **Operação cancelada.** Seus dados continuam salvos normalmente.")
        return

    if prefixo == 'tele':
        sub_tipo = data[1]
        
        if sub_tipo == 'destino':
            destino = data[2]
            context.user_data['tele_destino'] = destino
            context.user_data['tele_valor_taxa'] = TAXAS_TELES[destino]

            keyboard = [
                [InlineKeyboardButton("1 Tele", callback_data='tele_qtd_1'), InlineKeyboardButton("2 Teles", callback_data='tele_qtd_2')],
                [InlineKeyboardButton("3 Teles", callback_data='tele_qtd_3'), InlineKeyboardButton("4 Teles", callback_data='tele_qtd_4')],
                [InlineKeyboardButton("✏️ Outra Quantidade", callback_data='tele_qtd_custom')]
            ]
            await query.edit_message_text(
                text=f"📍 **{destino}** (Taxa R$ {TAXAS_TELES[destino]:.2f}/cada)\n\n**Quantas teles** você está levando para esse destino?",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )

        elif sub_tipo == 'qtd':
            qtd_str = data[2]
            if qtd_str == 'custom':
                await query.edit_message_text(text="✏️ Digite no chat **quantas teles** você está levando (ex: 5):")
                context.user_data['aguardando_qtd_custom'] = True
            else:
                qtd = int(qtd_str)
                context.user_data['tele_qtd'] = qtd
                await pedir_forma_pagamento(query, context)

        elif sub_tipo == 'pag':
            forma_pag = data[2]
            context.user_data['tele_forma_pag'] = forma_pag
            destino = context.user_data.get('tele_destino')
            valor_taxa = context.user_data.get('tele_valor_taxa')
            qtd = context.user_data.get('tele_qtd', 1)

            if forma_pag == 'Dinheiro':
                await query.edit_message_text(
                    text=f"💵 **{qtd}x Tele(s) em Dinheiro** ({destino}).\n\nDigite o **VALOR TOTAL** cobrado do cliente (Lanches + Taxas):",
                    parse_mode="Markdown"
                )
                context.user_data['aguardando_valor_dinheiro'] = True
            else:
                hoje = datetime.now().strftime('%Y-%m-%d')
                cursor.execute(
                    "INSERT INTO teles (data, destino, valor_tele, quantidade, forma_pagamento, valor_dinheiro_recebido) VALUES (?, ?, ?, ?, ?, 0.0)",
                    (hoje, destino, valor_taxa, qtd, forma_pag)
                )
                conn.commit()

                qtd_hoje, total_hoje = atualizar_tabela_diaria(hoje)
                frase = random.choice(FRASES_MOTIVACIONAIS)
                total_ganho_tele = valor_taxa * qtd

                await query.edit_message_text(
                    text=(
                        f"✅ **{qtd}x Tele(s) Registrada(s)! (+R$ {total_ganho_tele:.2f})**\n"
                        f"📍 Destino: {destino} | 💳 {forma_pag}\n\n"
                        f"📊 **PLACAR DO DIA:**\n"
                        f"📦 Teles Hoje: **{qtd_hoje} entregas**\n"
                        f"💰 Total Acumulado Hoje: **R$ {total_hoje:.2f}**\n\n"
                        f"{frase}"
                    ),
                    parse_mode="Markdown"
                )

    elif prefixo == 'gasto':
        cat = data[1]
        if cat == 'Gasolina':
            context.user_data['passo_combustivel'] = 'valor_pago'
            await query.edit_message_text(text="⛽ **Registro de Combustível**\n\nDigite quanto você **pagou em R$** no posto (ex: 30.00):", parse_mode="Markdown")
        else:
            context.user_data['cat_pendente'] = cat
            await query.edit_message_text(text=f"Digite o valor do gasto com **{cat}** (ex: 20.00):", parse_mode="Markdown")

async def pedir_forma_pagamento(query_or_update, context: ContextTypes.DEFAULT_TYPE):
    destino = context.user_data.get('tele_destino')
    valor_taxa = context.user_data.get('tele_valor_taxa')
    qtd = context.user_data.get('tele_qtd', 1)
    total_taxa = valor_taxa * qtd

    keyboard = [
        [InlineKeyboardButton("💳 Pix / Cartão", callback_data='tele_pag_Pix/Cartao')],
        [InlineKeyboardButton("💵 Dinheiro", callback_data='tele_pag_Dinheiro')]
    ]
    txt = f"📍 **{destino}** | 📦 **{qtd}x Tele(s)** (Total Taxa: R$ {total_taxa:.2f})\n\nComo foi o pagamento?"

    if hasattr(query_or_update, 'edit_message_text'):
        await query_or_update.edit_message_text(text=txt, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await query_or_update.reply_text(text=txt, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def processar_mensagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    hoje = datetime.now().strftime('%Y-%m-%d')
    hora_atual = datetime.now().strftime('%H:%M')

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
    elif texto == "🗓️ Histórico de Acertos":
        await historico_acertos(update, context)
        return
    elif texto == "💸 Registrar Gastos":
        await despesa(update, context)
        return
    elif texto == "⛽ Média de Combustível":
        await relatorio_combustivel(update, context)
        return

    # Processamento de Quantidade Customizada
    if context.user_data.get('aguardando_qtd_custom'):
        try:
            qtd = int(texto)
            if qtd <= 0:
                await update.message.reply_text("⚠️ Digite uma quantidade maior que zero.")
                return
            context.user_data['tele_qtd'] = qtd
            context.user_data.pop('aguardando_qtd_custom')
            await pedir_forma_pagamento(update.message, context)
            return
        except ValueError:
            await update.message.reply_text("⚠️ Digite apenas um número inteiro (ex: 5).")
            return

    # Entrada de valor em Dinheiro da Tele
    if context.user_data.get('aguardando_valor_dinheiro'):
        try:
            valor_dinheiro = float(texto.replace(',', '.'))
            destino = context.user_data.pop('tele_destino')
            valor_taxa = context.user_data.pop('tele_valor_taxa')
            qtd = context.user_data.pop('tele_qtd', 1)
            forma_pag = context.user_data.pop('tele_forma_pag')
            context.user_data.pop('aguardando_valor_dinheiro')

            cursor.execute(
                "INSERT INTO teles (data, destino, valor_tele, quantidade, forma_pagamento, valor_dinheiro_recebido) VALUES (?, ?, ?, ?, ?, ?)",
                (hoje, destino, valor_taxa, qtd, forma_pag, valor_dinheiro)
            )
            conn.commit()

            qtd_hoje, total_hoje = atualizar_tabela_diaria(hoje)
            frase = random.choice(FRASES_MOTIVACIONAIS)
            total_ganho_tele = valor_taxa * qtd

            await update.message.reply_text(
                f"✅ **{qtd}x Tele(s) Registrada(s)! (+R$ {total_ganho_tele:.2f})**\n"
                f"📍 Destino: {destino} | 💵 Recebido: R$ {valor_dinheiro:.2f}\n\n"
                f"📊 **PLACAR DO DIA:**\n"
                f"📦 Teles Hoje: **{qtd_hoje} entregas**\n"
                f"💰 Total Acumulado Hoje: **R$ {total_hoje:.2f}**\n\n"
                f"{frase}",
                parse_mode="Markdown",
                reply_markup=menu_teclado_principal()
            )
            return
        except ValueError:
            await update.message.reply_text("⚠️ Digite um valor válido (ex: 38.00).")
            return

    # Processamento de Abastecimento
    if context.user_data.get('passo_combustivel') == 'valor_pago':
        try:
            val = float(texto.replace(',', '.'))
            context.user_data['abast_valor'] = val
            context.user_data['passo_combustivel'] = 'litros'
            await update.message.reply_text("⛽ Quantos **LITROS** deu na bomba? (ex: 5.2):")
            return
        except ValueError:
            await update.message.reply_text("⚠️ Digite um valor numérico válido (ex: 30.00).")
            return

    if context.user_data.get('passo_combustivel') == 'litros':
        try:
            litros = float(texto.replace(',', '.'))
            context.user_data['abast_litros'] = litros
            context.user_data['passo_combustivel'] = 'km_atual'
            await update.message.reply_text("📏 Qual o **KM ATUAL DA MOTO** no painel? (ex: 45200):")
            return
        except ValueError:
            await update.message.reply_text("⚠️ Digite a quantidade de litros (ex: 5.2).")
            return

    if context.user_data.get('passo_combustivel') == 'km_atual':
        try:
            km_atual = float(texto.replace(',', '.'))
            val_pago = context.user_data.pop('abast_valor')
            litros = context.user_data.pop('abast_litros')
            context.user_data.pop('passo_combustivel')

            cursor.execute("INSERT INTO transacoes (data, tipo, categoria, valor) VALUES (?, 'gasto', 'Gasolina', ?)", (hoje, val_pago))

            cursor.execute("SELECT km_atual FROM abastecimentos ORDER BY id DESC LIMIT 1")
            ultimo = cursor.fetchone()

            km_rodados = 0.0
            media_kml = 0.0

            if ultimo and ultimo[0]:
                ultimo_km = ultimo[0]
                if km_atual > ultimo_km:
                    km_rodados = km_atual - ultimo_km
                    media_kml = km_rodados / litros if litros > 0 else 0.0

            cursor.execute('''
                INSERT INTO abastecimentos (data, km_atual, litros, valor_total, km_rodados_desde_ultimo, media_kml)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (hoje, km_atual, litros, val_pago, km_rodados, media_kml))
            conn.commit()

            msg = (
                f"⛽ **Abastecimento Registrado!**\n\n"
                f"💵 **Valor Pago:** R$ {val_pago:.2f}\n"
                f"⛽ **Litros:** {litros:.2f}L\n"
                f"📏 **KM Painel:** {km_atual:.1f} km\n"
            )

            if media_kml > 0:
                cost_per_km = val_pago / km_rodados if km_rodados > 0 else 0
                msg += (
                    f"------------------------------\n"
                    f"📊 **RESULTADO DESTE TANQUE:**\n"
                    f"🛣️ **KM Rodados no Tanque:** {km_rodados:.1f} km\n"
                    f"🔥 **Média de Consumo:** **{media_kml:.2f} KM/L**\n"
                    f"💸 **Custo por KM:** R$ {cost_per_km:.2f}/km"
                )
            else:
                msg += "\nℹ️ *Média será calculada automaticamente no próximo abastecimento!*"

            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=menu_teclado_principal())
            return
        except ValueError:
            await update.message.reply_text("⚠️ Digite apenas os números do KM (ex: 45200).")
            return

    # Entrada de KM Inicial
    if context.user_data.get('passo_turno') == 'km_inicio':
        try:
            km_in = float(texto.replace(',', '.'))
            cursor.execute("INSERT INTO turnos (data, hora_inicio, km_inicio, arrancada, status) VALUES (?, ?, ?, 30.0, 'ABERTO')", (hoje, hora_atual, km_in))
            conn.commit()
            context.user_data.pop('passo_turno')
            
            atualizar_tabela_diaria(hoje)
            
            await update.message.reply_text(f"🟢 **Turno Aberto!**\n⏰ {hora_atual} | KM: {km_in}\n💵 Arrancada: R$ 30,00 cadastrada!", reply_markup=menu_teclado_principal())
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

    # Tratamento de Outros Gastos
    if 'cat_pendente' in context.user_data:
        try:
            valor = float(texto.replace(',', '.'))
            cat = context.user_data.pop('cat_pendente')
            cursor.execute("INSERT INTO transacoes (data, tipo, categoria, valor) VALUES (?, 'gasto', ?, ?)", (hoje, cat, valor))
            conn.commit()

            await update.message.reply_text(f"🔴 **Despesa Registrada:** R$ {valor:.2f} ({cat})", reply_markup=menu_teclado_principal())
        except ValueError:
            await update.message.reply_text("⚠️ Digite um valor numérico válido.")

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

async def acerto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime('%Y-%m-%d')

    cursor.execute("SELECT arrancada FROM turnos WHERE data=?", (hoje,))
    turno = cursor.fetchone()
    arrancada = turno[0] if turno else 30.0

    cursor.execute("SELECT destino, valor_tele, quantidade, forma_pagamento, valor_dinheiro_recebido FROM teles WHERE data=?", (hoje,))
    teles = cursor.fetchall()

    if not teles:
        await update.message.reply_text("⚠️ Nenhuma tele registrada hoje para fechar acerto!")
        return

    total_teles_qtd = sum(t[2] for t in teles)
    total_taxas = sum(t[1] * t[2] for t in teles)
    total_dinheiro_em_mao = sum(t[4] for t in teles)

    cidade_qtd = sum(t[2] for t in teles if t[0] == 'Cidade')
    passo_qtd = sum(t[2] for t in teles if t[0] == 'Passo da Cruz')
    acacia_qtd = sum(t[2] for t in teles if t[0] == 'Acacia')

    lucro_total_dia = arrancada + total_taxas
    diferenca = lucro_total_dia - total_dinheiro_em_mao

    atualizar_tabela_diaria(hoje)

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

    msg += "\n\n💾 *Acerto gravado com sucesso no seu histórico diário!*"

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=menu_teclado_principal())

async def historico_acertos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT data, total_teles, valor_teles, arrancada, lucro_liquido_diario FROM fechamentos_diarios ORDER BY data DESC LIMIT 15")
    registros = cursor.fetchall()

    if not registros:
        await update.message.reply_text("⚠️ Nenhum acerto gravado ainda.")
        return

    total_geral_teles = sum(r[1] for r in registros)
    total_geral_faturado = sum(r[4] for r in registros)

    msg = "🗓️ **HISTÓRICO DE ACERTOS DIÁRIOS**\n\n"
    for r in registros:
        dt_fmt = datetime.strptime(r[0], '%Y-%m-%d').strftime('%d/%m/%Y')
        msg += f"📅 **{dt_fmt}**:\n   📦 {r[1]} teles | 💰 R$ {r[4]:.2f}\n"

    msg += (
        f"----------------------------------\n"
        f"📊 **TOTAL ACUMULADO NOS DIAS:**\n"
        f"📦 Total Teles: **{total_geral_teles} entregas**\n"
        f"💰 Faturamento Total: **R$ {total_geral_faturado:.2f}**"
    )

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=menu_teclado_principal())

async def relatorio_combustivel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT data, km_atual, litros, valor_total, km_rodados_desde_ultimo, media_kml FROM abastecimentos ORDER BY id DESC LIMIT 5")
    abast = cursor.fetchall()

    if not abast:
        await update.message.reply_text("⛽ **Controle de Combustível**\n\nNenhum abastecimento gravado ainda.\nPara começar, acesse **💸 Registrar Gastos** -> **⛽ Gasolina**.")
        return

    msg = "⛽ **RELATÓRIO DE COMBUSTÍVEL & MÉDIAS**\n\n"
    
    medias_validas = [a[5] for a in abast if a[5] > 0]
    total_litros = sum(a[2] for a in abast)
    total_gasto = sum(a[3] for a in abast)
    total_km = sum(a[4] for a in abast)

    for a in abast:
        dt_fmt = datetime.strptime(a[0], '%Y-%m-%d').strftime('%d/%m')
        if a[5] > 0:
            msg += f"📅 **{dt_fmt}** - {a[2]:.1f}L (R$ {a[3]:.2f})\n   🛣️ {a[4]:.1f} km rodados | 🔥 **{a[5]:.2f} KM/L**\n\n"
        else:
            msg += f"📅 **{dt_fmt}** - {a[2]:.1f}L (R$ {a[3]:.2f}) - *Início da medição*\n\n"

    if medias_validas:
        media_geral = sum(medias_validas) / len(medias_validas)
        custo_medio_km = total_gasto / total_km if total_km > 0 else 0
        msg += (
            f"----------------------------------\n"
            f"📊 **RESUMO GERAL:**\n"
            f"⭐ **Sua Média Geral:** **{media_geral:.2f} KM/1L**\n"
            f"🛣️ Total KM Rodados Medidos: **{total_km:.1f} km**\n"
            f"⛽ Total Litros Consumidos: **{total_litros:.2f} L**\n"
            f"💸 Custo de Gasolina/KM: **R$ {custo_medio_km:.2f}/km**"
        )

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=menu_teclado_principal())

async def meus_ganhos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoje_dt = datetime.now()
    hoje_str = hoje_dt.strftime('%Y-%m-%d')
    
    inicio_semana = (hoje_dt - timedelta(days=hoje_dt.weekday())).strftime('%Y-%m-%d')
    inicio_mes = hoje_dt.strftime('%Y-%m-01')

    cursor.execute("SELECT total_teles, lucro_liquido_diario FROM fechamentos_diarios WHERE data=?", (hoje_str,))
    hoje_dados = cursor.fetchone()
    teles_hoje = hoje_dados[0] if hoje_dados else 0
    ganho_hoje = hoje_dados[1] if hoje_dados else 0.0

    cursor.execute("SELECT SUM(total_teles), SUM(lucro_liquido_diario) FROM fechamentos_diarios WHERE data >= ?", (inicio_semana,))
    sem_dados = cursor.fetchone()
    teles_sem = sem_dados[0] or 0
    ganho_sem = sem_dados[1] or 0.0

    cursor.execute("SELECT SUM(total_teles), SUM(lucro_liquido_diario) FROM fechamentos_diarios WHERE data >= ?", (inicio_mes,))
    mes_dados = cursor.fetchone()
    teles_mes = mes_dados[0] or 0
    ganho_mes = mes_dados[1] or 0.0

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
    app.add_handler(CommandHandler("zerar", zerar_comando))
    
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_mensagens))

    print("Bot Motivacional de Teles & Ganhos Rodando...")
    app.run_polling()
