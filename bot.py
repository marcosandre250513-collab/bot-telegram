import telebot
from telebot import types
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math
from flask import Flask
from threading import Thread
import os
import time
import psycopg2

# --- CONFIGURAÇÃO DO FUSO HORÁRIO (SÃO PAULO) ---
FUSO_SP = ZoneInfo('America/Sao_Paulo')

def agora_sp():
    return datetime.now(FUSO_SP)

MESES_NOME = {
    1: 'JANEIRO', 2: 'FEVEREIRO', 3: 'MARÇO', 4: 'ABRIL',
    5: 'MAIO', 6: 'JUNHO', 7: 'JULHO', 8: 'AGOSTO',
    9: 'SETEMBRO', 10: 'OUTUBRO', 11: 'NOVEMBRO', 12: 'DEZEMBRO'
}

DIAS_SEMANA = {
    0: 'SEG', 1: 'TERCA', 2: 'QUARTA',
    3: 'QUINTA', 4: 'SEXTA', 5: 'SAB'
}

# --- SERVIDOR WEB PARA MANTER O BOT ATIVO ---
app = Flask('')

@app.route('/')
def home():
    return "Sistema Operacional Online!"

def run():
    app.run(host='0.0.0.0', port=8080)

t = Thread(target=run)
t.start()

# --- CONFIGURAÇÃO DO BOT E BANCO POSTGRESQL ---
TOKEN = '8804109455:AAEW-Ofgrd0C9WrRWApDGd12rxz2oOHLhMc'
bot = telebot.TeleBot(TOKEN)

PESO_SERVICO = 13.64
PESO_REAVISO = 7.80

def get_db_connection():
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError("A variável DATABASE_URL não foi encontrada. Verifique se o PostgreSQL foi adicionado no Railway.")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url, sslmode='require')

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            user_id VARCHAR(50) PRIMARY KEY,
            nome VARCHAR(100)
        );
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS lancamentos (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50) REFERENCES usuarios(user_id),
            data_registro TIMESTAMP,
            dia_semana VARCHAR(10),
            tipo VARCHAR(50),
            quantidade INT,
            semana_ativa BOOLEAN DEFAULT TRUE
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

def inicializar_agente(user_id, nome):
    str_id = str(user_id)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO usuarios (user_id, nome)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE SET nome = EXCLUDED.nome;
    ''', (str_id, nome))
    conn.commit()
    cur.close()
    conn.close()

def processar_lancamento(user_id, tipo_id, quantidade, dia_especifico=None):
    str_id = str(user_id)
    agora = agora_sp()
    dia_nome = dia_especifico if dia_especifico else DIAS_SEMANA.get(agora.weekday(), 'SAB')
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO lancamentos (user_id, data_registro, dia_semana, tipo, quantidade, semana_ativa)
        VALUES (%s, %s, %s, %s, %s, TRUE)
    ''', (str_id, agora, dia_nome, tipo_id, quantidade))
    conn.commit()
    cur.close()
    conn.close()

def converter_reaviso_para_maos(user_id, quantidade=1):
    str_id = str(user_id)
    agora = agora_sp()
    dia_nome = DIAS_SEMANA.get(agora.weekday(), 'SAB')
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO lancamentos (user_id, data_registro, dia_semana, tipo, quantidade, semana_ativa)
        VALUES (%s, %s, %s, 'reaviso_maos', %s, TRUE)
    ''', (str_id, agora, dia_nome, quantidade))
    cur.execute('''
        INSERT INTO lancamentos (user_id, data_registro, dia_semana, tipo, quantidade, semana_ativa)
        VALUES (%s, %s, %s, 'reaviso_outros', %s, TRUE)
    ''', (str_id, agora, dia_nome, -quantidade))
    conn.commit()
    cur.close()
    conn.close()

def obter_resumo_semana(user_id):
    str_id = str(user_id)
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT tipo, SUM(quantidade) 
        FROM lancamentos 
        WHERE user_id = %s AND semana_ativa = TRUE
        GROUP BY tipo;
    ''', (str_id,))
    rows = cur.fetchall()
    
    totais = {
        'corte': 0, 'religacao': 0, 'reaviso_maos': 0, 
        'reaviso_outros': 0, 'improdutivo': 0, 'negociacao': 0
    }
    for tipo, soma in rows:
        if tipo in totais:
            totais[tipo] = int(soma or 0)

    cur.execute('''
        SELECT dia_semana, tipo, SUM(quantidade)
        FROM lancamentos
        WHERE user_id = %s AND semana_ativa = TRUE
        GROUP BY dia_semana, tipo;
    ''', (str_id,))
    rows_diarios = cur.fetchall()
    
    producao_diaria = {
        dia: {
            'corte': 0, 'religacao': 0, 'reaviso_maos': 0, 
            'reaviso_outros': 0, 'improdutivo': 0, 'negociacao': 0
        } for dia in DIAS_SEMANA.values()
    }
    for dia, tipo, soma in rows_diarios:
        if dia in producao_diaria and tipo in producao_diaria[dia]:
            producao_diaria[dia][tipo] = int(soma or 0)

    cur.close()
    conn.close()
    return totais, producao_diaria

def obter_historico_mensal(user_id):
    str_id = str(user_id)
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT 
            TO_CHAR(data_registro, 'YYYY-MM') AS mes_ano,
            SUM(CASE WHEN tipo IN ('corte', 'religacao') THEN quantidade ELSE 0 END) AS cr,
            SUM(CASE WHEN tipo LIKE 'reaviso%%' THEN quantidade ELSE 0 END) AS rv,
            SUM(CASE WHEN tipo = 'improdutivo' THEN quantidade ELSE 0 END) AS imp,
            SUM(CASE WHEN tipo = 'negociacao' THEN quantidade ELSE 0 END) AS neg
        FROM lancamentos
        WHERE user_id = %s
        GROUP BY TO_CHAR(data_registro, 'YYYY-MM')
        ORDER BY mes_ano DESC;
    ''', (str_id,))
    
    resumo_meses = cur.fetchall()
    cur.close()
    conn.close()
    return resumo_meses

# ==========================================
# MENUS E TECLADOS INTERATIVOS
# ==========================================
def menu_principal_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True, row_width=2)
    btn_relatorio = types.KeyboardButton('📊 Relatório Semanal')
    btn_mensal = types.KeyboardButton('📅 Histórico Mensal')
    btn_registrar = types.KeyboardButton('⚡ Registrar Produção')
    btn_comandos = types.KeyboardButton('📜 Lista de Comandos')
    btn_reset_semana = types.KeyboardButton('🔄 Resetar Semana')
    
    markup.add(btn_relatorio, btn_mensal)
    markup.add(btn_registrar, btn_comandos)
    markup.add(btn_reset_semana)
    return markup

def teclado_registro_rapido():
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("🔌 Religue +1", callback_data="add_religacao_1"),
        types.InlineKeyboardButton("✋ +1 em Mãos", callback_data="convert_maos_1"),
        types.InlineKeyboardButton("🚫 Imp +1", callback_data="add_improdutivo_1")
    )
    markup.add(
        types.InlineKeyboardButton("✂️ Corte (Digitar Qnt)", callback_data="prompt_corte"),
        types.InlineKeyboardButton("🔌 Religação (Digitar Qnt)", callback_data="prompt_religacao")
    )
    markup.add(
        types.InlineKeyboardButton("📬 Add Reavisos (Digitar Qnt)", callback_data="prompt_reaviso_outros")
    )
    return markup

def teclado_confirmacao_reset_semana():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚠️ SIM, ZERAR SEMANA", callback_data="confirm_reset_semana"),
        types.InlineKeyboardButton("❌ CANCELAR", callback_data="cancel_reset_semana")
    )
    return markup

def teclado_confirmacao_zerar():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚠️ APAGAR HISTÓRICO", callback_data="confirm_zerar_hist"),
        types.InlineKeyboardButton("❌ CANCELAR", callback_data="cancel_zerar_hist")
    )
    return markup

# ==========================================
# HANDLERS DE ENTRADA MANUAL (NEXT STEP)
# ==========================================
def receber_qnt_corte(message):
    try:
        qnt = int(message.text)
        processar_lancamento(message.from_user.id, 'corte', qnt)
        bot.reply_to(message, f"✅ *+ {qnt} Corte(s)* adicionado(s) com sucesso!", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠️ Valor inválido. Digite apenas números inteiros.", parse_mode="Markdown")

def receber_qnt_religacao(message):
    try:
        qnt = int(message.text)
        processar_lancamento(message.from_user.id, 'religacao', qnt)
        bot.reply_to(message, f"✅ *+ {qnt} Religação(ões)* adicionada(s) com sucesso!", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠️ Valor inválido. Digite apenas números inteiros.", parse_mode="Markdown")

def receber_qnt_reaviso_outros(message):
    try:
        qnt = int(message.text)
        processar_lancamento(message.from_user.id, 'reaviso_outros', qnt)
        bot.reply_to(message, f"✅ *+ {qnt} Reaviso(s)* adicionado(s) à sua carga!", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠️ Valor inválido. Digite apenas números inteiros.", parse_mode="Markdown")

# ==========================================
# COMANDOS E CONVERSÃO
# ==========================================
@bot.message_handler(commands=['maos'])
def converter_maos_manual(message):
    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    try:
        partes = message.text.split()
        qnt = int(partes[1]) if len(partes) > 1 else 1
        converter_reaviso_para_maos(str_id, qnt)
        bot.reply_to(message, f"✋ *{qnt} Reaviso(s) ajustado(s) para EM MÃOS!*", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠️ Sintaxe: `/maos` para 1 ou `/maos 5` para vários.", parse_mode="Markdown")

@bot.message_handler(commands=['addcorte', 'cortedia'])
def add_corte_dia_especifico(message):
    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    try:
        partes = message.text.split()
        if len(partes) < 3:
            return bot.reply_to(message, "⚠️ *SINTAXE INCORRETA*\nUse: `/addcorte [dia] [qnt]`", parse_mode="Markdown")

        dia_input = partes[1].upper().strip()
        quantidade = int(partes[2])

        mapa_dias = {
            'SEG': 'SEG', 'SEGUNDA': 'SEG', 'TER': 'TERCA', 'TERCA': 'TERCA',
            'QUA': 'QUARTA', 'QUARTA': 'QUARTA', 'QUI': 'QUINTA', 'QUINTA': 'QUINTA',
            'SEX': 'SEXTA', 'SEXTA': 'SEXTA', 'SAB': 'SAB', 'SABADO': 'SAB'
        }

        if dia_input not in mapa_dias:
            return bot.reply_to(message, "⚠️ *DIA INVÁLIDO*\nDias: `SEG`, `TERCA`, `QUARTA`, `QUINTA`, `SEXTA`, `SAB`", parse_mode="Markdown")

        dia_chave = mapa_dias[dia_input]
        processar_lancamento(str_id, 'corte', quantidade, dia_especifico=dia_chave)
        bot.reply_to(message, f"🤫 *AJUSTE MANUAL REALIZADO*\n+{quantidade} Corte(s) em *{dia_chave}*", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Erro ao processar: {str(e)}", parse_mode="Markdown")

# ==========================================
# HISTÓRICO MENSAL
# ==========================================
@bot.message_handler(func=lambda m: m.text == '📅 Histórico Mensal' or m.text in ['/mensal', '/meses', '/historico'])
def relatorio_mensal(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)
    
    dados_meses = obter_historico_mensal(str_id)
    
    if not dados_meses:
        return bot.reply_to(message, "📂 *Nenhum histórico mensal encontrado no banco ainda.*", parse_mode="Markdown")
    
    texto = f"📅 *HISTÓRICO MENSAL DE PRODUÇÃO*\n👤 Agente: *{nome.upper()}*\n\n"
    
    for row in dados_meses:
        mes_ano_str, cr, rv, imp, neg = row
        ano, mes = mes_ano_str.split('-')
        nome_mes = MESES_NOME.get(int(mes), mes)
        
        mes_pag_num = int(mes) + 2
        ano_pag = int(ano)
        if mes_pag_num > 12:
            mes_pag_num -= 12
            ano_pag += 1
        nome_mes_pag = MESES_NOME.get(mes_pag_num, str(mes_pag_num))
        
        pts_est = (cr * PESO_SERVICO) + (rv * PESO_REAVISO)
        
        texto += (
            f"🗓️ *{nome_mes} / {ano}*\n"
            f"• Cortes / Religações: *{cr}*\n"
            f"• Reavisos Atendidos: *{rv}*\n"
            f"• Improdutivos (Visitas): *{imp}*\n"
            f"• Pontuação Total Acumulada: *{pts_est:.2f} pts*\n"
            f"💰 *Pagamento Previsto Em:* *{nome_mes_pag} / {ano_pag}*\n"
            f"----------------------------------------\n"
        )
    
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

# ==========================================
# ZERAR HISTÓRICO MENSAL (COM CONFIRMAÇÃO)
# ==========================================
@bot.message_handler(commands=['zerar_mensal', 'resetarmensal'])
def solicitar_zerar_mensal(message):
    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚠️ SIM, ZERAR MENSAL", callback_data="confirm_zerar_mensal"),
        types.InlineKeyboardButton("❌ CANCELAR", callback_data="cancel_zerar_mensal")
    )
    
    bot.reply_to(
        message, 
        "🚨 *ATENÇÃO: EXCLUSÃO DO HISTÓRICO MENSAL*\n\n"
        "Esta ação irá **apagar permanentemente todos os registros do histórico mensal** salvos no banco de dados PostgreSQL.\n\n"
        "Tem certeza absoluta de que deseja zerar seu histórico mensal?", 
        parse_mode="Markdown", 
        reply_markup=markup
    )

# ==========================================
# HANDLERS DE COMANDOS E AJUDA
# ==========================================
@bot.message_handler(commands=['comandos', 'ajuda', 'help'])
@bot.message_handler(func=lambda m: m.text == '📜 Lista de Comandos')
def listar_comandos(message):
    texto = (
        "📜 *LISTA DE COMANDOS DO BOT*\n\n"
        "📊 *Relatórios e Histórico:*\n"
        "• `/relatorio` ou `/prod` - Exibe a parcial da semana atual\n"
        "• `/mensal` ou `/historico` - Consulta total acumulado de meses passados\n"
        "• `/comandos` - Exibe esta lista de comandos\n"
        "• `/resetar` - Zera a contagem da semana atual\n"
        "• `/zerar_mensal` - Zera todo o histórico mensal acumulado\n\n"
        "⚡ *Lançamentos Diretos por Texto:*\n"
        "• `/corte [qnt]` - Registra cortes (Ex: `/corte 10`)\n"
        "• `/rel [qnt]` - Registra religações (Ex: `/rel 5`)\n"
        "• `/rea [qnt]` - Registra carga de reavisos (Ex: `/rea 30`)\n"
        "• `/imp [qnt]` - Registra improdutivos (Ex: `/imp 2`)\n"
        "• `/maos [qnt]` - Converte reavisos para em mãos (Ex: `/maos 1` ou `/maos 5`)\n\n"
        "⚙️ *Ajustes Específicos:*\n"
        "• `/addcorte [dia] [qnt]` - Adiciona cortes em dia específico (Ex: `/addcorte seg 10`)"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def start(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)
    texto = (
        f"🌐 *MEU SISTEMA DE PERFORMANCE*\n"
        f"Bem-vindo, {nome}.\n\n"
        "Menu fixo ativado. Selecione uma opção para operar:"
    )
    bot.reply_to(message, texto, parse_mode="Markdown", reply_markup=menu_principal_keyboard())

@bot.message_handler(func=lambda m: m.text == '⚡ Registrar Produção')
def menu_registro(message):
    bot.reply_to(message, "⚡ *REGISTRO RÁPIDO DE CAMPO*\nToque nos botões para lançar sua produção:", 
                 parse_mode="Markdown", reply_markup=teclado_registro_rapido())

# ==========================================
# RELATÓRIO FORMATADO SEMANAL
# ==========================================
@bot.message_handler(func=lambda m: m.text == '📊 Relatório Semanal' or m.text in ['/relatorio', '/status', '/prod', '/dds'])
def relatorio(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)
    
    totais, dias = obter_resumo_semana(str_id)
    
    hoje = agora_sp()
    segunda = hoje - timedelta(days=hoje.weekday())
    sabado = segunda + timedelta(days=5)
    
    data_inicio = segunda.strftime("%d/%m")
    data_fim = sabado.strftime("%d/%m")
    
    mes_producao = hoje.month
    mes_pagamento_num = mes_producao + 2
    if mes_pagamento_num > 12:
        mes_pagamento_num -= 12
    nome_mes_pagamento = MESES_NOME[mes_pagamento_num]

    cr = totais.get('corte', 0) + totais.get('religacao', 0)
    rv_maos = totais.get('reaviso_maos', 0)
    rv_outros = totais.get('reaviso_outros', 0)
    rv_total = rv_maos + rv_outros
    
    en = totais.get('improdutivo', 0)
    ng = totais.get('negociacao', 0)
    
    if rv_total > 0:
        pct_maos = (rv_maos / rv_total) * 100
        pct_outros = (rv_outros / rv_total) * 100
        detalhe_reaviso = f"{rv_total} (✋ Mãos: {rv_maos} [{pct_maos:.1f}%] | 📬 Outros: {rv_outros} [{pct_outros:.1f}%])"
    else:
        detalhe_reaviso = "0 (✋ Mãos: 0 [0%] | 📬 Outros: 0 [0%])"

    pontos = (cr * PESO_SERVICO) + (rv_total * PESO_REAVISO)
    
    m_f1, m_f2, m_f3 = 250, 300, 350
    m_f1_pts, m_f2_pts = m_f1 * PESO_SERVICO, m_f2 * PESO_SERVICO
    
    if pontos >= (m_f3 * PESO_SERVICO):
        faixa_str = "Faixa 3"
        falta_str = "Meta máxima atingida!"
        bonificacao = 300.00
    elif pontos >= m_f2_pts:
        faixa_str = "Faixa 2"
        falta_str = "Atingiu a Faixa 2"
        bonificacao = 200.00
    elif pontos >= m_f1_pts:
        faixa_str = "Faixa 1"
        falta_pts = m_f2_pts - pontos
        faltam_c = math.ceil(falta_pts / PESO_SERVICO)
        faltam_r = math.ceil(falta_pts / PESO_REAVISO)
        falta_str = f"Faltaram {faltam_c} Cortes ou {faltam_r} Reavisos para Faixa 2"
        bonificacao = 150.00
    else:
        faixa_str = "Nenhuma Faixa"
        falta_pts = m_f1_pts - pontos
        faltam_c = math.ceil(falta_pts / PESO_SERVICO)
        faltam_r = math.ceil(falta_pts / PESO_REAVISO)
        falta_str = f"Faltam {faltam_c} Cortes ou {faltam_r} Reavisos para Faixa 1"
        bonificacao = 0.00

    bonif_str = f"{bonificacao:,.2f}".replace('.', ',')
    msg_bonif = (
        f"👋 Olá {nome.upper()}, segue abaixo a sua parcial da bonificação semanal:\n\n"
        f"📅 Semana ({data_inicio} a {data_fim}):\n"
        f"• Cortes/Religações: {cr}\n"
        f"• Reavisos: {detalhe_reaviso}\n"
        f"• Entregas / Improdutivos: {en}\n"
        f"• Negociações: {ng}\n"
        f"• Faixa: {faixa_str}\n"
        f"• {falta_str}\n"
        f"💰 Bonificação parcial: R$ {bonif_str}\n\n"
        f"🗓️ *MÊS DE PAGAMENTO DESTA PRODUÇÃO:*\n"
        f"➡️ *{nome_mes_pagamento}*"
    )
    
    bot.send_message(message.chat.id, msg_bonif, parse_mode="Markdown")

    dias_ordem = ['SEG', 'TERCA', 'QUARTA', 'QUINTA', 'SEXTA', 'SAB']
    linhas_tabela = []
    
    for idx, dia_chave in enumerate(dias_ordem):
        dt = (segunda + timedelta(days=idx)).strftime("%d/%m/%Y")
        d_dados = dias.get(dia_chave, {})
        
        d_cr = d_dados.get('corte', 0) + d_dados.get('religacao', 0)
        d_rv = d_dados.get('reaviso_maos', 0) + d_dados.get('reaviso_outros', 0)
        d_en = d_dados.get('improdutivo', 0)
        d_ng = d_dados.get('negociacao', 0)
        
        linhas_tabela.append(f"{dt} | {d_cr:2d} | {d_rv:2d} | {d_en:2d} | {d_ng:2d}")

    tabela_formatada = "\n".join(linhas_tabela)

    msg_diario = (
        "📅 *Serviços executados por dia:*\n\n"
        "📌 *Legenda:*\n"
        "CR = Cortes/Religações\n"
        "RV = Reavisos Total\n"
        "EN = Entregas/Improdutivos\n"
        "NG = Negociações\n\n"
        "```\n"
        "Data       | CR | RV | EN | NG\n"
        "--------------------------------\n"
        f"{tabela_formatada}\n"
        "```"
    )

    bot.send_message(message.chat.id, msg_diario, parse_mode="Markdown")

# --- COMANDOS DIGITADOS MANUAIS ---
@bot.message_handler(commands=['corte', 'rel', 'rea', 'imp', 'religacao', 'improdutivo'])
def registrar_servico_manual(message):
    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    
    comando = message.text.split()[0].lower()
    
    if comando == '/corte': tipo_id, tipo_nome = 'corte', 'Corte'
    elif comando in ['/rel', '/religacao']: tipo_id, tipo_nome = 'religacao', 'Religação'
    elif comando in ['/rea']: tipo_id, tipo_nome = 'reaviso_outros', 'Reaviso'
    elif comando in ['/imp', '/improdutivo']: tipo_id, tipo_nome = 'improdutivo', 'Improdutivo'
    else: return

    try:
        quantidade = int(message.text.split()[1])
        processar_lancamento(str_id, tipo_id, quantidade)
        bot.reply_to(message, f"✅ *INPUT ACEITO*\nVolume processado: +{quantidade} {tipo_nome}(s)", parse_mode="Markdown")
    except:
        bot.reply_to(message, f"⚠️ *SINTAXE INCORRETA*\nEx: `{comando} 10`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == '🔄 Resetar Semana' or m.text == '/resetar')
def solicitar_reset_semana(message):
    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    bot.reply_to(
        message, 
        "⚠️ *CONFIRMAÇÃO DE RESET SEMANAL*\n\n"
        "Você tem certeza de que deseja **zerar a contagem desta semana**?\n"
        "(Seu histórico permanente NÃO será apagado).", 
        parse_mode="Markdown", 
        reply_markup=teclado_confirmacao_reset_semana()
    )

@bot.message_handler(commands=['zerar_historico'])
def solicitar_zerar_historico(message):
    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    bot.reply_to(
        message, 
        "⚠️ *ATENÇÃO: AÇÃO IRREVERSÍVEL!*\n\n"
        "Você está prestes a **apagar permanentemente todo o seu Histórico de Produção**.\n"
        "Tem certeza de que deseja continuar?", 
        parse_mode="Markdown", 
        reply_markup=teclado_confirmacao_zerar()
    )

# ==========================================
# PROCESSAMENTO DE BOTÕES E CALLBACKS
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)
    inicializar_agente(user_id, call.from_user.first_name)

    if call.data == 'prompt_corte':
        msg = bot.send_message(call.message.chat.id, "✂️ *Quantos Cortes você deseja adicionar?*", parse_mode="Markdown")
        bot.register_next_step_handler(msg, receber_qnt_corte)
        bot.answer_callback_query(call.id)

    elif call.data == 'prompt_religacao':
        msg = bot.send_message(call.message.chat.id, "🔌 *Quantas Religações você deseja adicionar?*", parse_mode="Markdown")
        bot.register_next_step_handler(msg, receber_qnt_religacao)
        bot.answer_callback_query(call.id)

    elif call.data == 'prompt_reaviso_outros':
        msg = bot.send_message(call.message.chat.id, "📬 *Quantos Reavisos deseja adicionar à sua carga?*", parse_mode="Markdown")
        bot.register_next_step_handler(msg, receber_qnt_reaviso_outros)
        bot.answer_callback_query(call.id)

    elif call.data == 'add_religacao_1':
        processar_lancamento(user_id, 'religacao', 1)
        bot.answer_callback_query(call.id, "🔌 +1 Religação Registrada!", show_alert=True)

    elif call.data == 'convert_maos_1':
        converter_reaviso_para_maos(user_id, 1)
        bot.answer_callback_query(call.id, "✋ +1 Reaviso ajustado para EM MÃOS!", show_alert=True)

    elif call.data == 'add_improdutivo_1':
        processar_lancamento(user_id, 'improdutivo', 1)
        bot.answer_callback_query(call.id, "🚫 +1 Improdutivo Registrado!", show_alert=True)

    elif call.data == 'confirm_reset_semana':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE lancamentos SET semana_ativa = FALSE WHERE user_id = %s AND semana_ativa = TRUE;", (user_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        bot.edit_message_text("🔄 *CICLO SEMANAL ZERADO!*\nA contagem da semana foi zerada com sucesso.", 
                              chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Semana zerada!", show_alert=True)

    elif call.data == 'cancel_reset_semana':
        bot.edit_message_text("❌ *OPERAÇÃO CANCELADA.*\nSua produção semanal continua mantida.", 
                              chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Cancelado!")

    elif call.data == 'confirm_zerar_hist':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM lancamentos WHERE user_id = %s;", (user_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        bot.edit_message_text("🗑️ *HISTÓRICO PERMANENTE ZERADO!*\nTodos os registros antigos foram apagados com sucesso.", 
                              chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Histórico apagado!", show_alert=True)

    elif call.data == 'cancel_zerar_hist':
        bot.edit_message_text("❌ *OPERAÇÃO CANCELADA.*\nSeu histórico permanece gravado com segurança.", 
                              chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Cancelado!")

    elif call.data == 'confirm_zerar_mensal':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM lancamentos WHERE user_id = %s;", (user_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        bot.edit_message_text(
            "🗑️ *HISTÓRICO MENSAL ZERADO COM SUCESSO!*\n\n"
            "Todos os lançamentos acumulados foram permanentemente removidos. "
            "Seu relatório em `/mensal` agora começará limpo.", 
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id, "Histórico mensal zerado!", show_alert=True)

    elif call.data == 'cancel_zerar_mensal':
        bot.edit_message_text(
            "❌ *OPERAÇÃO CANCELADA.*\n"
            "Seu histórico mensal permanece intacto no banco de dados.", 
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id, "Cancelado!")

# --- INICIALIZAÇÃO DO BANCO E DO BOT (COM TRATAMENTO DE CONFLITO) ---
print("Inicializando tabelas do PostgreSQL...")
init_db()

try:
    bot.delete_webhook(drop_pending_updates=True)
    time.sleep(2)
except Exception as e:
    print(f"Aviso ao limpar webhook: {e}")

print("Sistema Global Online no PostgreSQL. Aguardando conexão...")

while True:
    try:
        bot.infinity_polling(skip_pending=True, timeout=20)
    except Exception as e:
        print(f"Erro de conexão ({e}). Tentando reconectar em 5 segundos...")
        time.sleep(5)
