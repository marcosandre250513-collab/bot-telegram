import telebot
from telebot import types
from datetime import datetime, timedelta, timezone
import math
from flask import Flask
from threading import Thread
import json
import os

# --- CONFIGURAÇÃO DO FUSO HORÁRIO NATIVO (SÃO PAULO / BRASÍLIA UTC-3) ---
FUSO_SP = timezone(timedelta(hours=-3))

def agora_sp():
    return datetime.now(FUSO_SP)

# --- SERVIDOR FLASK PARA MANTER O BOT ONLINE (RAILWAY) ---
app = Flask('')

@app.route('/')
def home():
    return "Sistema Operacional Online!"

def run():
    app.run(host='0.0.0.0', port=8080)

t = Thread(target=run)
t.start()

# --- CONFIGURAÇÃO DO BOT ---
TOKEN = os.getenv('BOT_TOKEN', '8804109455:AAHPqPuDSp2cB_VANRG4EsJOevrw9sydRf8')
bot = telebot.TeleBot(TOKEN)

PESO_SERVICO = 13.64
PESO_REAVISO = 7.80
ARQUIVO_BANCO = 'banco_producao.json'

DIAS_SEMANA = {
    0: 'SEG', 1: 'TERCA', 2: 'QUARTA',
    3: 'QUINTA', 4: 'SEXTA', 5: 'SAB'
}

# --- BANCO DE DADOS LOCAL ---
def carregar_banco():
    if os.path.exists(ARQUIVO_BANCO):
        try:
            with open(ARQUIVO_BANCO, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_banco(dados):
    with open(ARQUIVO_BANCO, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

usuarios = carregar_banco()

def inicializar_agente(user_id, nome):
    str_id = str(user_id)
    if str_id not in usuarios:
        usuarios[str_id] = {
            'nome': nome,
            'totais_semana': {'corte': 0, 'religacao': 0, 'reaviso': 0, 'improdutivo': 0, 'negociacao': 0},
            'producao_diaria': {
                dia: {'corte': 0, 'religacao': 0, 'reaviso': 0, 'improdutivo': 0, 'negociacao': 0} for dia in DIAS_SEMANA.values()
            },
            'historico_permanente': []
        }
        salvar_banco(usuarios)

# ==========================================
# MENUS E TECLADOS OTIMIZADOS PARA A RUA
# ==========================================
def menu_principal_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_relatorio = types.KeyboardButton('📊 Relatório Semanal')
    btn_registrar = types.KeyboardButton('⚡ Registrar Produção')
    btn_reset_semana = types.KeyboardButton('🔄 Resetar Semana')
    markup.add(btn_relatorio, btn_registrar)
    markup.add(btn_reset_semana)
    return markup

def teclado_registro_rapido():
    markup = types.InlineKeyboardMarkup(row_width=3)
    
    # Linha de atalho rápido (+1 com aviso no meio da tela)
    markup.add(
        types.InlineKeyboardButton("✂️ Corte +1", callback_data="add_corte_1"),
        types.InlineKeyboardButton("🔌 Religue +1", callback_data="add_religacao_1"),
        types.InlineKeyboardButton("📄 Reaviso +1", callback_data="add_reaviso_1")
    )
    
    # Linha para digitar quantidade específica
    markup.add(
        types.InlineKeyboardButton("✂️ Corte (Vários)", callback_data="prompt_corte"),
        types.InlineKeyboardButton("🔌 Religue (Vários)", callback_data="prompt_religacao"),
        types.InlineKeyboardButton("📄 Reaviso (Vários)", callback_data="prompt_reaviso")
    )
    
    # Conversões para improdutivos
    markup.add(
        types.InlineKeyboardButton("🔄 Corte -> Improdutivo", callback_data="convert_corte_1"),
        types.InlineKeyboardButton("🔄 Religue -> Improdutivo", callback_data="convert_religacao_1")
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
# HANDLERS DE ENTRADA DE TEXTO
# ==========================================
def receber_qnt_corte(message):
    try:
        qnt = int(message.text)
        user_id = str(message.from_user.id)
        processar_lancamento(user_id, 'corte', 'Corte', qnt)
        bot.reply_to(message, f"✅ *+ {qnt} Corte(s)* adicionado(s) com sucesso!", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠️ Valor inválido. Digite apenas números inteiros.", parse_mode="Markdown")

def receber_qnt_religacao(message):
    try:
        qnt = int(message.text)
        user_id = str(message.from_user.id)
        processar_lancamento(user_id, 'religacao', 'Religação', qnt)
        bot.reply_to(message, f"✅ *+ {qnt} Religação(ões)* adicionada(s) com sucesso!", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠️ Valor inválido. Digite apenas números inteiros.", parse_mode="Markdown")

def receber_qnt_reaviso(message):
    try:
        qnt = int(message.text)
        user_id = str(message.from_user.id)
        processar_lancamento(user_id, 'reaviso', 'Reaviso', qnt)
        bot.reply_to(message, f"✅ *+ {qnt} Reaviso(s)* adicionado(s) com sucesso!", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠️ Valor inválido. Digite apenas números inteiros.", parse_mode="Markdown")

# ==========================================
# COMANDOS DE AJUSTE POR DIA (CORTE E REAVISO)
# ==========================================
@bot.message_handler(commands=['addcorte', 'cortedia'])
def add_corte_dia_especifico(message):
    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    processar_ajuste_dia(message, str_id, 'corte', 'Corte')

@bot.message_handler(commands=['addreaviso', 'reavisodia'])
def add_reaviso_dia_especifico(message):
    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    processar_ajuste_dia(message, str_id, 'reaviso', 'Reaviso')

def processar_ajuste_dia(message, str_id, tipo_id, tipo_nome):
    try:
        partes = message.text.split()
        if len(partes) < 3:
            return bot.reply_to(
                message, 
                f"⚠️ *SINTAXE INCORRETA*\nUse: `/{message.text.split()[0][1:]} [dia] [qnt]`\nEx: `/{message.text.split()[0][1:]} seg 10`\n\nDias: `SEG`, `TERCA`, `QUARTA`, `QUINTA`, `SEXTA`, `SAB`",
                parse_mode="Markdown"
            )

        dia_input = partes[1].upper().strip()
        quantidade = int(partes[2])

        mapa_dias = {
            'SEG': 'SEG', 'SEGUNDA': 'SEG',
            'TER': 'TERCA', 'TERCA': 'TERCA',
            'QUA': 'QUARTA', 'QUARTA': 'QUARTA',
            'QUI': 'QUINTA', 'QUINTA': 'QUINTA',
            'SEX': 'SEXTA', 'SEXTA': 'SEXTA',
            'SAB': 'SAB', 'SABADO': 'SAB'
        }

        if dia_input not in mapa_dias:
            return bot.reply_to(message, "⚠️ *DIA INVÁLIDO*\nDias aceitos: `SEG`, `TERCA`, `QUARTA`, `QUINTA`, `SEXTA`, `SAB`", parse_mode="Markdown")

        dia_chave = mapa_dias[dia_input]
        data_str = agora_sp().strftime("%d/%m/%Y %H:%M")

        usuarios[str_id]['producao_diaria'][dia_chave][tipo_id] += quantidade
        usuarios[str_id]['totais_semana'][tipo_id] += quantidade
        usuarios[str_id]['historico_permanente'].append({
            'data': data_str, 'dia': dia_chave, 'tipo': tipo_nome, 'quantidade': quantidade
        })

        salvar_banco(usuarios)
        bot.reply_to(message, f"🤫 *AJUSTE REALIZADO*\n+{quantidade} {tipo_nome}(s) lançados em *{dia_chave}*!", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "⚠️ A quantidade deve ser um número inteiro.", parse_mode="Markdown")

# ==========================================
# MENUS E COMANDOS PRINCIPAIS
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def start(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)
    texto = (
        f"🌐 *SISTEMA DE PERFORMANCE DE CAMPO*\n"
        f"Bem-vindo(a), {nome}!\n\n"
        "Selecione uma opção no menu abaixo para operar o sistema:"
    )
    bot.reply_to(message, texto, parse_mode="Markdown", reply_markup=menu_principal_keyboard())

@bot.message_handler(func=lambda m: m.text == '⚡ Registrar Produção')
def menu_registro(message):
    bot.reply_to(message, "⚡ *REGISTRO RÁPIDO DE CAMPO*\nToque em um botão para lançar:", 
                 parse_mode="Markdown", reply_markup=teclado_registro_rapido())

@bot.message_handler(func=lambda m: m.text == '📊 Relatório Semanal' or m.text in ['/relatorio', '/status'])
def relatorio(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name.upper()
    if message.from_user.last_name:
        nome += f" {message.from_user.last_name.upper()}"
        
    inicializar_agente(str_id, nome)
    
    dados = usuarios[str_id]
    t, dias = dados['totais_semana'], dados['producao_diaria']
    
    cr_total = t['corte'] + t['religacao']
    rv_total = t['reaviso']
    en_total = t.get('improdutivo', 0)
    ng_total = t.get('negociacao', 0)

    pontos_total = cr_total * PESO_SERVICO + rv_total * PESO_REAVISO
    
    m_f1, m_f2, m_f3 = 250, 300, 350
    p_f1, p_f2, p_f3 = m_f1 * PESO_SERVICO, m_f2 * PESO_SERVICO, m_f3 * PESO_SERVICO

    if pontos_total >= p_f3:
        faixa_nome = "Faixa 3"
        faltam_str = "Meta máxima atingida!"
        bonificacao = 450.00
    elif pontos_total >= p_f2:
        faixa_nome = "Faixa 2"
        falta_pts = p_f3 - pontos_total
        faltam_cr = math.ceil(falta_pts / PESO_SERVICO)
        faltam_rv = math.ceil(falta_pts / PESO_REAVISO)
        faltam_str = f"Faltaram {faltam_cr} Cortes ou {faltam_rv} Reavisos para Faixa 3"
        bonificacao = 300.00
    elif pontos_total >= p_f1:
        faixa_nome = "Faixa 1"
        falta_pts = p_f2 - pontos_total
        faltam_cr = math.ceil(falta_pts / PESO_SERVICO)
        faltam_rv = math.ceil(falta_pts / PESO_REAVISO)
        faltam_str = f"Faltaram {faltam_cr} Cortes ou {faltam_rv} Reavisos para Faixa 1"
        bonificacao = 150.00
    else:
        faixa_nome = "Nenhuma Faixa"
        falta_pts = p_f1 - pontos_total
        faltam_cr = math.ceil(falta_pts / PESO_SERVICO)
        faltam_rv = math.ceil(falta_pts / PESO_REAVISO)
        faltam_str = f"Faltam {faltam_cr} Cortes ou {faltam_rv} Reavisos para Faixa 1"
        bonificacao = 0.00

    hoje = agora_sp()
    segunda = hoje - timedelta(days=hoje.weekday())
    sabado = segunda + timedelta(days=5)

    msg_bonificacao = (
        f"👋 Olá *{nome}*, segue abaixo a sua parcial da bonificação semanal:\n\n"
        f"📅 *Semana Atual ({segunda.strftime('%d/%m')} a {sabado.strftime('%d/%m')}):*\n"
        f"• Cortes/Religações: {cr_total}\n"
        f"• Reavisos: {rv_total}\n"
        f"• Entregas: {en_total}\n"
        f"• Negociações: {ng_total}\n"
        f"• Faixa: {faixa_nome}\n"
        f"• {faltam_str}\n"
        f"💰 *Bonificação parcial: R$ {bonificacao:,.2f}*\n\n"
        f"🏆 *Total da bonificação até agora: R$ {bonificacao:,.2f}*\n\n"
        f"⚠️ *Atenção:* Esta é uma parcial da sua bonificação semanal."
    )

    dias_ordem = ['SEG', 'TERCA', 'QUARTA', 'QUINTA', 'SEXTA', 'SAB']
    linhas_tabela = []

    for idx, dia_chave in enumerate(dias_ordem):
        d = dias.get(dia_chave, {'corte': 0, 'religacao': 0, 'reaviso': 0, 'improdutivo': 0, 'negociacao': 0})
        dt_dia = (segunda + timedelta(days=idx)).strftime("%d/%m/%Y")
        cr = d['corte'] + d['religacao']
        rv = d['reaviso']
        en = d.get('improdutivo', 0)
        ng = d.get('negociacao', 0)
        linhas_tabela.append(f"{dt_dia} | {cr:2d} | {rv:2d} | {en:2d} | {ng:2d}")

    msg_tabela = (
        f"📅 *Serviços executados por dia:*\n\n"
        f"📌 *Legenda:*\nCR = Cortes/Religações\nRV = Reavisos\nEN = Entregas\nNG = Negociações\n\n"
        f"```text\nData       | CR | RV | EN | NG\n-------------------------------\n"
        + "\n".join(linhas_tabela) +
        f"\n```"
    )

    bot.send_message(message.chat.id, msg_bonificacao, parse_mode="Markdown")
    bot.send_message(message.chat.id, msg_tabela, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == '🔄 Resetar Semana' or m.text == '/resetar')
def solicitar_reset_semana(message):
    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    bot.reply_to(message, "⚠️ *Deseja zerar a contagem desta semana?*", parse_mode="Markdown", reply_markup=teclado_confirmacao_reset_semana())

# ==========================================
# PROCESSAMENTO DOS BOTÕES (POP-UPS NO MEIO DA TELA)
# ==========================================
def processar_lancamento(user_id, tipo_id, tipo_nome, quantidade):
    agora = agora_sp()
    dia_nome = DIAS_SEMANA.get(agora.weekday(), 'SAB')
    data_str = agora.strftime("%d/%m/%Y %H:%M")
    
    usuarios[user_id]['producao_diaria'][dia_nome][tipo_id] += quantidade
    usuarios[user_id]['totais_semana'][tipo_id] += quantidade
    usuarios[user_id]['historico_permanente'].append({'data': data_str, 'dia': dia_nome, 'tipo': tipo_nome, 'quantidade': quantidade})
    salvar_banco(usuarios)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)
    inicializar_agente(user_id, call.from_user.first_name)

    # Lançamentos rápidos +1 com Alerta POP-UP no centro do celular
    if call.data == 'add_corte_1':
        processar_lancamento(user_id, 'corte', 'Corte', 1)
        bot.answer_callback_query(call.id, text="⚡ +1 Corte Registrado!", show_alert=True)

    elif call.data == 'add_religacao_1':
        processar_lancamento(user_id, 'religacao', 'Religação', 1)
        bot.answer_callback_query(call.id, text="⚡ +1 Religação Registrada!", show_alert=True)

    elif call.data == 'add_reaviso_1':
        processar_lancamento(user_id, 'reaviso', 'Reaviso', 1)
        bot.answer_callback_query(call.id, text="⚡ +1 Reaviso Registrado!", show_alert=True)

    # Entradas por digitação
    elif call.data == 'prompt_corte':
        msg = bot.send_message(call.message.chat.id, "✂️ *Quantos Cortes deseja adicionar?*", parse_mode="Markdown")
        bot.register_next_step_handler(msg, receber_qnt_corte)
        bot.answer_callback_query(call.id)

    elif call.data == 'prompt_religacao':
        msg = bot.send_message(call.message.chat.id, "🔌 *Quantas Religações deseja adicionar?*", parse_mode="Markdown")
        bot.register_next_step_handler(msg, receber_qnt_religacao)
        bot.answer_callback_query(call.id)

    elif call.data == 'prompt_reaviso':
        msg = bot.send_message(call.message.chat.id, "📄 *Quantos Reavisos deseja adicionar?*", parse_mode="Markdown")
        bot.register_next_step_handler(msg, receber_qnt_reaviso)
        bot.answer_callback_query(call.id)

    elif call.data == 'convert_corte_1':
        dia_nome = DIAS_SEMANA.get(agora_sp().weekday(), 'SAB')
        if usuarios[user_id]['totais_semana']['corte'] > 0:
            usuarios[user_id]['producao_diaria'][dia_nome]['corte'] -= 1
            usuarios[user_id]['totais_semana']['corte'] -= 1
            usuarios[user_id]['producao_diaria'][dia_nome]['improdutivo'] += 1
            usuarios[user_id]['totais_semana']['improdutivo'] += 1
            salvar_banco(usuarios)
            bot.answer_callback_query(call.id, text="🔄 1 Corte convertido em Improdutivo!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, text="⚠️ Sem cortes para converter!", show_alert=True)

    elif call.data == 'convert_religacao_1':
        dia_nome = DIAS_SEMANA.get(agora_sp().weekday(), 'SAB')
        if usuarios[user_id]['totais_semana']['religacao'] > 0:
            usuarios[user_id]['producao_diaria'][dia_nome]['religacao'] -= 1
            usuarios[user_id]['totais_semana']['religacao'] -= 1
            usuarios[user_id]['producao_diaria'][dia_nome]['improdutivo'] += 1
            usuarios[user_id]['totais_semana']['improdutivo'] += 1
            salvar_banco(usuarios)
            bot.answer_callback_query(call.id, text="🔄 1 Religação convertida em Improdutivo!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, text="⚠️ Sem religações para converter!", show_alert=True)

    elif call.data == 'confirm_reset_semana':
        usuarios[user_id]['totais_semana'] = {'corte': 0, 'religacao': 0, 'reaviso': 0, 'improdutivo': 0, 'negociacao': 0}
        for dia in DIAS_SEMANA.values():
            usuarios[user_id]['producao_diaria'][dia] = {'corte': 0, 'religacao': 0, 'reaviso': 0, 'improdutivo': 0, 'negociacao': 0}
        salvar_banco(usuarios)
        bot.edit_message_text("🔄 *CICLO SEMANAL ZERADO!*", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, text="Semana zerada!", show_alert=True)

    elif call.data == 'cancel_reset_semana':
        bot.edit_message_text("❌ *OPERAÇÃO CANCELADA.*", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

print("Sistema Global Online. Aguardando conexão...")
bot.infinity_polling()
