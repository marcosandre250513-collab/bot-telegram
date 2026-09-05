import telebot
from telebot import types
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math
from flask import Flask
from threading import Thread
import json
import os

# --- CONFIGURAÇÃO DO FUSO HORÁRIO (SÃO PAULO) ---
FUSO_SP = ZoneInfo('America/Sao_Paulo')

def agora_sp():
    """Retorna a data e hora atual no fuso oficial de São Paulo (UTC-3)."""
    return datetime.now(FUSO_SP)

# --- CONFIGURAÇÃO DO SERVIDOR ---
app = Flask('')

@app.route('/')
def home():
    return "Sistema Operacional Online!"

def run():
    app.run(host='0.0.0.0', port=8080)

t = Thread(target=run)
t.start()
# --------------------------------

TOKEN = '8804109455:AAHPqPuDSp2cB_VANRG4EsJOevrw9sydRf8'
bot = telebot.TeleBot(TOKEN)

PESO_SERVICO = 13.64
PESO_REAVISO = 7.80
ARQUIVO_BANCO = 'banco_producao.json'

DIAS_SEMANA = {
    0: 'SEG', 1: 'TERCA', 2: 'QUARTA',
    3: 'QUINTA', 4: 'SEXTA', 5: 'SAB'
}

# --- FUNÇÕES DE BANCO DE DADOS PERMANENTE ---
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
# MENUS E TECLADOS INTERATIVOS
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
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✂️ Corte (Pergunta Qnt)", callback_data="prompt_corte"),
        types.InlineKeyboardButton("🔌 Religação (Pergunta Qnt)", callback_data="prompt_religacao")
    )
    markup.add(
        types.InlineKeyboardButton("Corte +1", callback_data="add_corte_1"),
        types.InlineKeyboardButton("Religue +1", callback_data="add_religacao_1")
    )
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
# HANDLERS DE RESPOSTA (NEXT STEP HANDLERS)
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

# ==========================================
# COMANDO DE AJUSTE MANUAL
# ==========================================
@bot.message_handler(commands=['addcorte', 'cortedia'])
def add_corte_dia_especifico(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)

    try:
        partes = message.text.split()
        if len(partes) < 3:
            return bot.reply_to(
                message, 
                "⚠️ *SINTAXE INCORRETA*\nUse: `/addcorte [dia] [qnt]`\nEx: `/addcorte seg 10` ou `/addcorte terca 5`\n\nDias aceitos: `SEG`, `TERCA`, `QUARTA`, `QUINTA`, `SEXTA`, `SAB`",
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
            return bot.reply_to(
                message, 
                "⚠️ *DIA INVÁLIDO*\nDias válidos: `SEG`, `TERCA`, `QUARTA`, `QUINTA`, `SEXTA`, `SAB`", 
                parse_mode="Markdown"
            )

        dia_chave = mapa_dias[dia_input]
        agora = agora_sp()
        data_str = agora.strftime("%d/%m/%Y %H:%M")

        usuarios[str_id]['producao_diaria'][dia_chave]['corte'] += quantidade
        usuarios[str_id]['totais_semana']['corte'] += quantidade
        usuarios[str_id]['historico_permanente'].append({
            'data': data_str,
            'dia': dia_chave,
            'tipo': 'Corte',
            'quantidade': quantidade
        })

        salvar_banco(usuarios)
        bot.reply_to(
            message, 
            f"🤫 *AJUSTE MANUAL REALIZADO*\n+{quantidade} Corte(s) adicionados em *{dia_chave}* com sucesso!", 
            parse_mode="Markdown"
        )
    except ValueError:
        bot.reply_to(message, "⚠️ A quantidade deve ser um número inteiro.", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Erro ao processar: {str(e)}", parse_mode="Markdown")

# ==========================================
# HANDLERS DE COMANDOS E TEXTO
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def start(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)
    texto = (
        f"🌐 *MEU SISTEMA DE PERFORMANCE*\n"
        f"Bem-vindo, {nome}.\n\n"
        "Selecione uma opção no menu abaixo para operar o sistema:"
    )
    bot.reply_to(message, texto, parse_mode="Markdown", reply_markup=menu_principal_keyboard())

@bot.message_handler(func=lambda m: m.text == '⚡ Registrar Produção')
def menu_registro(message):
    bot.reply_to(message, "⚡ *REGISTRO RÁPIDO DE CAMPO*\nToque nos botões para lançar sua produção:", 
                 parse_mode="Markdown", reply_markup=teclado_registro_rapido())

# ==========================================
# RELATÓRIO FORMATADO IGUAL ÀS IMAGENS
# ==========================================
@bot.message_handler(func=lambda m: m.text == '📊 Relatório Semanal' or m.text in ['/relatorio', '/status', '/prod', '/dds'])
def relatorio(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)
    
    dados = usuarios[str_id]
    totais = dados['totais_semana']
    dias = dados['producao_diaria']
    
    hoje = agora_sp()
    segunda = hoje - timedelta(days=hoje.weekday())
    sabado = segunda + timedelta(days=5)
    
    data_inicio = segunda.strftime("%d/%m")
    data_fim = sabado.strftime("%d/%m")
    
    cr = totais.get('corte', 0) + totais.get('religacao', 0)
    rv = totais.get('reaviso', 0)
    en = totais.get('improdutivo', 0)
    ng = totais.get('negociacao', 0)
    
    pontos = (cr * PESO_SERVICO) + (rv * PESO_REAVISO)
    
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

    # MENSAGEM 1: RESUMO DE BONIFICAÇÃO
    msg_bonif = (
        f"👋 Olá {nome.upper()}, segue abaixo a sua parcial da bonificação semanal:\n\n"
        f"📅 Semana 1 ({data_inicio} a {data_fim}):\n"
        f"• Cortes/Religações: {cr}\n"
        f"• Reavisos: {rv}\n"
        f"• Entregas: {en}\n"
        f"• Negociações: {ng}\n"
        f"• Faixa: {faixa_str}\n"
        f"• {falta_str}\n"
        f"💰 Bonificação parcial: R$ {bonificacao:,.2f}".replace('.', ',') + "\n\n"
        f"🏆 Total da bonificação até agora: R$ {bonificacao:,.2f}".replace('.', ',')
    )
    
    bot.send_message(message.chat.id, msg_bonif)

    # MENSAGEM 2: DETALHAMENTO DIÁRIO EM TABELA
    dias_ordem = ['SEG', 'TERCA', 'QUARTA', 'QUINTA', 'SEXTA', 'SAB']
    linhas_tabela = []
    
    for idx, dia_chave in enumerate(dias_ordem):
        dt = (segunda + timedelta(days=idx)).strftime("%d/%m/%Y")
        d_dados = dias.get(dia_chave, {'corte': 0, 'religacao': 0, 'reaviso': 0, 'improdutivo': 0, 'negociacao': 0})
        
        d_cr = d_dados.get('corte', 0) + d_dados.get('religacao', 0)
        d_rv = d_dados.get('reaviso', 0)
        d_en = d_dados.get('improdutivo', 0)
        d_ng = d_dados.get('negociacao', 0)
        
        linhas_tabela.append(f"{dt} | {d_cr:2d} | {d_rv:2d} | {d_en:2d} | {d_ng:2d}")

    tabela_formatada = "\n".join(linhas_tabela)

    msg_diario = (
        "📅 *Serviços executados por dia:*\n\n"
        "📌 *Legenda:*\n"
        "CR = Cortes/Religações\n"
        "RV = Reavisos\n"
        "EN = Entregas\n"
        "NG = Negociações\n\n"
        "```\n"
        "Data       | CR | RV | EN | NG\n"
        "--------------------------------\n"
        f"{tabela_formatada}\n"
        "```"
    )

    bot.send_message(message.chat.id, msg_diario, parse_mode="Markdown")

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

# --- COMANDOS DIGITADOS MANUAIS (/corte 10, /rel 5, etc) ---
@bot.message_handler(commands=['corte', 'rel', 'rea', 'imp', 'religacao', 'reaviso', 'improdutivo'])
def registrar_servico_manual(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)
    
    comando = message.text.split()[0].lower()
    
    if comando == '/corte': tipo_id, tipo_nome = 'corte', 'Corte'
    elif comando in ['/rel', '/religacao']: tipo_id, tipo_nome = 'religacao', 'Religação'
    elif comando in ['/rea', '/reaviso']: tipo_id, tipo_nome = 'reaviso', 'Reaviso'
    elif comando in ['/imp', '/improdutivo']: tipo_id, tipo_nome = 'improdutivo', 'Improdutivo'
    else: return

    try:
        quantidade = int(message.text.split()[1])
        processar_lancamento(str_id, tipo_id, tipo_nome, quantidade)
        bot.reply_to(message, f"✅ *INPUT ACEITO*\nVolume processado: +{quantidade} {tipo_nome}(s)", parse_mode="Markdown")
    except:
        bot.reply_to(message, f"⚠️ *SINTAXE INCORRETA*\nEx: `{comando} 10`", parse_mode="Markdown")

# ==========================================
# PROCESSAMENTO DE BOTÕES E CALLBACKS
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

    if call.data == 'prompt_corte':
        msg = bot.send_message(call.message.chat.id, "✂️ *Quantos Cortes você deseja adicionar?*", parse_mode="Markdown")
        bot.register_next_step_handler(msg, receber_qnt_corte)
        bot.answer_callback_query(call.id)

    elif call.data == 'prompt_religacao':
        msg = bot.send_message(call.message.chat.id, "🔌 *Quantas Religações você deseja adicionar?*", parse_mode="Markdown")
        bot.register_next_step_handler(msg, receber_qnt_religacao)
        bot.answer_callback_query(call.id)

    elif call.data == 'add_corte_1':
        processar_lancamento(user_id, 'corte', 'Corte', 1)
        bot.answer_callback_query(call.id, "✅ +1 Corte registrado!", show_alert=False)

    elif call.data == 'add_religacao_1':
        processar_lancamento(user_id, 'religacao', 'Religação', 1)
        bot.answer_callback_query(call.id, "✅ +1 Religação registrada!", show_alert=False)

    elif call.data == 'confirm_reset_semana':
        usuarios[user_id]['totais_semana'] = {'corte': 0, 'religacao': 0, 'reaviso': 0, 'improdutivo': 0, 'negociacao': 0}
        for dia in DIAS_SEMANA.values():
            usuarios[user_id]['producao_diaria'][dia] = {'corte': 0, 'religacao': 0, 'reaviso': 0, 'improdutivo': 0, 'negociacao': 0}
        salvar_banco(usuarios)
        
        bot.edit_message_text("🔄 *CICLO SEMANAL ZERADO!*\nA contagem da semana foi zerada com sucesso.", 
                              chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Semana zerada!")

    elif call.data == 'cancel_reset_semana':
        bot.edit_message_text("❌ *OPERAÇÃO CANCELADA.*\nSua produção semanal continua mantida.", 
                              chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Cancelado!")

    elif call.data == 'confirm_zerar_hist':
        usuarios[user_id]['historico_permanente'] = []
        salvar_banco(usuarios)
        bot.edit_message_text("🗑️ *HISTÓRICO PERMANENTE ZERADO!*\nTodos os registros antigos foram apagados com sucesso.", 
                              chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Histórico apagado!")

    elif call.data == 'cancel_zerar_hist':
        bot.edit_message_text("❌ *OPERAÇÃO CANCELADA.*\nSeu histórico permanece gravado com segurança.", 
                              chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Cancelado!")

print("Sistema Global Online. Aguardando conexão...")
bot.infinity_polling()
