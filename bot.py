import telebot
from telebot import types
from datetime import datetime, timedelta
import math
from flask import Flask
from threading import Thread
import io
import json
import os
import random
import string
from PIL import Image, ImageDraw, ImageFont

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

TOKEN = '8804109455:AAHeMGTy2A12ePXD3fjS_n_MST8oVY7oN8k'
bot = telebot.TeleBot(TOKEN)

PESO_SERVICO = 13.64
PESO_REAVISO = 7.80
ARQUIVO_BANCO = 'banco_producao.json'
# DIAS ÚTEIS E SÁBADO (SEG A SAB)
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
            'totais_semana': {'corte': 0, 'religacao': 0, 'reaviso': 0, 'improdutivo': 0},
            'producao_diaria': {
                dia: {'corte': 0, 'religacao': 0, 'reaviso': 0, 'improdutivo': 0} for dia in DIAS_SEMANA.values()
            },
            'historico_permanente': []
        }
        salvar_banco(usuarios)

def gerar_codigo_controle():
    chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    agora = datetime.now().strftime("%Y%m%d")
    return f"SYS-{agora}-{chars}"

# --- BUSCADOR DE FONTES ---
def get_font(size):
    try:
        return ImageFont.truetype("/system/fonts/Roboto-Regular.ttf", size)
    except:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except:
            try:
                return ImageFont.truetype("arial.ttf", size)
            except:
                try:
                    return ImageFont.load_default(size=size)
                except:
                    return ImageFont.load_default()

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
# GERADOR DE IMAGEM: RELATÓRIO DA SEMANA
# ==========================================
def gerar_imagem_relatorio(nome, totais, dias, pontos_total, status_msg, codigo_controle):
    img = Image.new('RGB', (900, 1500), color='#0f172a')
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(32)
    font_sub = get_font(22)
    font_main = get_font(24)
    font_small = get_font(16)

    COR_FUNDO = '#0f172a'
    COR_CARD = '#1e293b'
    COR_BORDA = '#334155'
    COR_TEXTO = '#f1f5f9'
    COR_SUBTEXTO = '#94a3b8'
    COR_DESTAQUE = '#38bdf8' 
    COR_ALERTA = '#f87171'   

    draw.rectangle([0, 0, 900, 130], fill='#020617')
    draw.text((40, 30), "MINHA PERFORMANCE", fill=COR_TEXTO, font=font_title)
    data_emissao = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
    draw.text((40, 80), f"EMISSAO: {data_emissao} | AGENTE: {nome.upper()}", fill=COR_DESTAQUE, font=font_sub)

    draw.rectangle([40, 160, 860, 260], fill=COR_CARD, outline=COR_BORDA, width=2)
    draw.text((60, 180), f"ID DE CONTROLE: {codigo_controle}", fill=COR_DESTAQUE, font=font_main)
    draw.text((60, 215), f"STATUS ATUAL: {status_msg}", fill=COR_TEXTO, font=font_main)

    draw.rectangle([40, 290, 860, 680], fill=COR_CARD, outline=COR_BORDA, width=2)
    draw.text((60, 310), "DETALHAMENTO DA PRODUCAO SEMANAL", fill=COR_TEXTO, font=font_main)
    draw.line([40, 350, 860, 350], fill=COR_BORDA, width=2)

    x_dia, x_corte, x_rel, x_rea, x_imp, x_tot = 60, 210, 330, 460, 600, 740
    draw.text((x_dia, 370), "DIA (DATA)", fill=COR_SUBTEXTO, font=font_main)
    draw.text((x_corte, 370), "CORTE", fill=COR_SUBTEXTO, font=font_main)
    draw.text((x_rel, 370), "RELIG", fill=COR_SUBTEXTO, font=font_main)
    draw.text((x_rea, 370), "REAVISO", fill=COR_SUBTEXTO, font=font_main)
    draw.text((x_imp, 370), "IMP.", fill=COR_ALERTA, font=font_main)
    draw.text((x_tot, 370), "TOTAL", fill=COR_DESTAQUE, font=font_main)
    draw.line([40, 410, 860, 410], fill=COR_BORDA, width=2)

    y = 430
    valores_dias = []
    
    # Cálculo das datas de Segunda a Sábado
    hoje = datetime.now()
    segunda_feira = hoje - timedelta(days=hoje.weekday())
    
    dias_ordem = ['SEG', 'TERCA', 'QUARTA', 'QUINTA', 'SEXTA', 'SAB']
    for idx, dia in enumerate(dias_ordem):
        d = dias.get(dia, {'corte': 0, 'religacao': 0, 'reaviso': 0, 'improdutivo': 0})
        total_prod = d['corte'] + d['religacao'] + d['reaviso']
        
        data_dia = (segunda_feira + timedelta(days=idx)).strftime("%d/%m")
        nome_exibicao = f"{dia[:3]} {data_dia}"
        valores_dias.append((nome_exibicao, total_prod))
        
        draw.text((x_dia, y), nome_exibicao, fill=COR_TEXTO, font=font_main)
        draw.text((x_corte, y), f"{d['corte']}", fill=COR_TEXTO, font=font_main)
        draw.text((x_rel, y), f"{d['religacao']}", fill=COR_TEXTO, font=font_main)
        draw.text((x_rea, y), f"{d['reaviso']}", fill=COR_TEXTO, font=font_main)
        draw.text((x_imp, y), f"{d['improdutivo']}", fill=COR_ALERTA, font=font_main)
        draw.text((x_tot, y), f"{total_prod}", fill=COR_DESTAQUE, font=font_main)
        y += 40  

    # CARD 2: GRÁFICO DE COLUNAS (BARRAS)
    draw.rectangle([40, 710, 860, 950], fill=COR_CARD, outline=COR_BORDA, width=2)
    draw.text((60, 730), "DESEMPENHO DIARIO (COLUNAS)", fill=COR_TEXTO, font=font_main)
    draw.line([40, 770, 860, 770], fill=COR_BORDA, width=2)

    max_valor = max([v[1] for v in valores_dias] + [1])
    x_pos = 100
    espaco = 130
    y_base = 900

    for dia_nome, valor in valores_dias:
        altura = (valor / max_valor) * 100 if max_valor > 0 else 0
        x1 = x_pos - 25
        x2 = x_pos + 25
        y1 = y_base - altura
        y2 = y_base
        
        draw.rectangle([x1, y1, x2, y2], fill=COR_DESTAQUE, outline=COR_BORDA, width=1)
        draw.text((x_pos - 28, 912), dia_nome, fill=COR_SUBTEXTO, font=font_small)
        
        if valor > 0:
            draw.text((x_pos - 12, y1 - 25), str(valor), fill=COR_TEXTO, font=font_main)
            
        x_pos += espaco

    # CARD 3: STATUS DAS FAIXAS
    draw.rectangle([40, 980, 860, 1380], fill=COR_CARD, outline=COR_BORDA, width=2)
    draw.text((60, 1000), "STATUS DAS FAIXAS E PROGRESSAO DE METAS", fill=COR_TEXTO, font=font_main)
    draw.line([40, 1040, 860, 1040], fill=COR_BORDA, width=2)

    hoje_idx = datetime.now().weekday()
    dias_restantes = max(1, 6 - hoje_idx)

    def text_meta(meta_qnt):
        meta_pontos = meta_qnt * PESO_SERVICO
        falta_pontos = meta_pontos - pontos_total
        if falta_pontos <= 0: 
            return "META ATINGIDA OK"
            
        faltam_servicos = math.ceil(falta_pontos / PESO_SERVICO)
        faltam_reavisos = math.ceil(falta_pontos / PESO_REAVISO)
        media_servicos = math.ceil(faltam_servicos / dias_restantes)
        
        return f"Faltam {faltam_servicos} Servicos ({media_servicos}/dia) ou {faltam_reavisos} Reavisos"

    total_servicos_brutos = totais['corte'] + totais['religacao'] + totais['reaviso']
    draw.text((60, 1060), f"VOLUME PRODUTIVO TOTAL: {total_servicos_brutos} Servicos", fill=COR_TEXTO, font=font_main)
    draw.text((60, 1095), f"VOLUME IMPRODUTIVO TOTAL: {totais['improdutivo']} Servicos", fill=COR_ALERTA, font=font_main)

    m_f1, m_f2, m_f3 = 250, 300, 350
    faixas = [(1, m_f1, "#f59e0b"), (2, m_f2, "#8b5cf6"), (3, m_f3, "#10b981")]
    y_faixa = 1150
    for num, meta_qnt, cor in faixas:
        meta_pontos = meta_qnt * PESO_SERVICO
        pct = min(1.0, pontos_total / meta_pontos) if meta_pontos > 0 else 0
        draw.text((60, y_faixa), f"FAIXA {num}: {text_meta(meta_qnt)} [{int(pct * 100)}%]", fill=COR_TEXTO, font=font_main)
        draw.rectangle([60, y_faixa + 35, 840, y_faixa + 50], fill=COR_FUNDO, outline=COR_BORDA, width=1)
        if pct > 0: 
            draw.rectangle([60, y_faixa + 35, 60 + (780 * pct), y_faixa + 50], fill=cor)
        y_faixa += 75

    draw.text((40, 1420), f"TRACKING SYSTEM {datetime.now().year} - TELEMETRIA DE CAMPO", fill=COR_SUBTEXTO, font=font_small)
    draw.text((40, 1445), f"ID DE AUDITORIA: {codigo_controle}", fill=COR_SUBTEXTO, font=font_small)

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

# ==========================================
# GERADOR DE IMAGEM: LOG HISTÓRICO (ÚLTIMOS 180)
# ==========================================
def gerar_imagem_historico(nome, historico, codigo_controle):
    img = Image.new('RGB', (900, 1300), color='#0f172a')
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(32)
    font_sub = get_font(22)
    font_main = get_font(26)
    font_small = get_font(16)

    COR_FUNDO, COR_CARD, COR_BORDA = '#0f172a', '#1e293b', '#334155'
    COR_TEXTO, COR_SUBTEXTO, COR_DESTAQUE = '#f1f5f9', '#94a3b8', '#38bdf8' 
    COR_ALERTA = '#f87171'

    draw.rectangle([0, 0, 900, 130], fill='#020617')
    draw.text((40, 30), "AUDITORIA DE DADOS - LOG PERMANENTE", fill=COR_TEXTO, font=font_title)
    draw.text((40, 80), f"AGENTE: {nome.upper()} | ID: {codigo_controle}", fill=COR_DESTAQUE, font=font_sub)

    historico_180 = historico[-180:]
    total_geral = sum(item['quantidade'] for item in historico_180 if item['tipo'] != 'Improdutivo')
    
    agrupado = {}
    for item in historico_180:
        data_dia = item['data'].split()[0][:5] 
        if data_dia not in agrupado: agrupado[data_dia] = 0
        if item['tipo'] in ['Corte', 'Religação', 'Reaviso']:
            agrupado[data_dia] += item['quantidade']
            
    ultimos_dias = list(agrupado.keys())[-7:]
    valores_grafico = [(d, agrupado[d]) for d in ultimos_dias]

    draw.rectangle([40, 160, 860, 260], fill=COR_CARD, outline=COR_BORDA, width=2)
    draw.text((60, 180), f"VOLUME HISTORICO TOTAL: {total_geral} servicos (Ativos)", fill=COR_DESTAQUE, font=font_main)
    draw.text((60, 215), f"TOTAL DE EVENTOS: {len(historico_180)} registros (ultimos 180)", fill=COR_TEXTO, font=font_main)

    draw.rectangle([40, 290, 860, 640], fill=COR_CARD, outline=COR_BORDA, width=2)
    draw.text((60, 310), "CURVA DE EVOLUCAO HISTORICA (Ultimos dias ativos)", fill=COR_TEXTO, font=font_main)
    draw.line([40, 350, 860, 350], fill=COR_BORDA, width=2)

    if valores_grafico:
        max_valor = max([v[1] for v in valores_grafico] + [1])
        pontos_grafico = []
        largura_disponivel = 760
        espaco = largura_disponivel // max(len(valores_grafico), 2)
        x_pos = 100
        
        for dia_nome, valor in valores_grafico:
            altura = (valor / max_valor) * 180 if max_valor > 0 else 0
            y_pos = 580 - altura
            pontos_grafico.append((x_pos, y_pos))
            
            draw.text((x_pos - 20, 600), dia_nome, fill=COR_SUBTEXTO, font=font_sub)
            if valor > 0:
                draw.text((x_pos - 10, y_pos - 35), str(valor), fill=COR_DESTAQUE, font=font_main)
            x_pos += espaco

        if len(pontos_grafico) > 1: draw.line(pontos_grafico, fill=COR_DESTAQUE, width=4)
        for p in pontos_grafico: draw.ellipse([p[0]-6, p[1]-6, p[0]+6, p[1]+6], fill=COR_CARD, outline=COR_DESTAQUE, width=3)

    draw.rectangle([40, 670, 860, 1220], fill=COR_CARD, outline=COR_BORDA, width=2)
    draw.text((60, 690), "ULTIMOS LANCAMENTOS SALVOS NO BANCO", fill=COR_TEXTO, font=font_main)
    draw.line([40, 730, 860, 730], fill=COR_BORDA, width=2)
    
    y_log = 750
    ultimos_logs = historico_180[-10:]
    for item in reversed(ultimos_logs):
        cor_log = COR_ALERTA if item['tipo'] == 'Improdutivo' else COR_SUBTEXTO
        draw.text((60, y_log), f">> {item['data']} | {item['tipo'].upper()}: +{item['quantidade']}", fill=cor_log, font=font_main)
        y_log += 45

    draw.text((40, 1250), f"TRACKING SYSTEM {datetime.now().year} - TELEMETRIA DE CAMPO", fill=COR_SUBTEXTO, font=font_small)
    draw.text((40, 1275), f"ID DE AUDITORIA: {codigo_controle} - BASE 180 REGISTROS", fill=COR_SUBTEXTO, font=font_small)

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

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
# 🤫 COMANDO OCULTO: ADICIONAR CORTE EM DIA ESPECÍFICO
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
        agora = datetime.now()
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

@bot.message_handler(func=lambda m: m.text == '📊 Relatório Semanal' or m.text in ['/relatorio', '/status'])
def relatorio(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)
    
    dados = usuarios[str_id]
    t, dias = dados['totais_semana'], dados['producao_diaria']
    pontos_total = (t['corte'] + t['religacao']) * PESO_SERVICO + (t['reaviso'] * PESO_REAVISO)
    m_f1, m_f2, m_f3 = 250, 300, 350

    if pontos_total >= (m_f3 * PESO_SERVICO): status_msg = "PERFORMANCE MAXIMA (NIVEL 3)"
    elif pontos_total >= (m_f2 * PESO_SERVICO): status_msg = "PERFORMANCE ELEVADA (NIVEL 2)"
    elif pontos_total >= (m_f1 * PESO_SERVICO): status_msg = "PERFORMANCE PADRAO (NIVEL 1)"
    else: status_msg = "FRENTE OPERACIONAL (ABAIXO N1)"

    codigo = gerar_codigo_controle()
    bot.send_chat_action(message.chat.id, 'upload_photo')
    bot.send_photo(message.chat.id, photo=gerar_imagem_relatorio(nome, t, dias, pontos_total, status_msg, codigo), 
                   caption=f"📈 *DASHBOARD DA SEMANA*\n`ID: {codigo}`", parse_mode="Markdown")

@bot.message_handler(commands=['historico'])
def ver_historico(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)

    historico = usuarios[str_id].get('historico_permanente', [])
    if not historico:
        return bot.reply_to(message, "📂 *LOG VAZIO.* Nenhum registro salvo no banco.", parse_mode="Markdown")

    codigo = gerar_codigo_controle()
    bot.send_chat_action(message.chat.id, 'upload_photo')
    bot.send_photo(message.chat.id, photo=gerar_imagem_historico(nome, historico, codigo), 
                   caption=f"🗄️ *AUDITORIA DE DADOS - LOG PERMANENTE*\n`ID: {codigo}`", parse_mode="Markdown")

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

@bot.message_handler(commands=['retira', 'remover'])
def retirar_servico(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)

    try:
        partes = message.text.split()
        if len(partes) != 3: return bot.reply_to(message, "⚠️ Ex: `/retira corte 3`", parse_mode="Markdown")

        tipo_input, quantidade = partes[1].lower(), int(partes[2])
        dia_nome = DIAS_SEMANA.get(datetime.now().weekday(), 'SAB')

        if tipo_input in ['corte']:
            qnt_atual_dia = usuarios[str_id]['producao_diaria'][dia_nome]['corte']
            qnt_atual_total = usuarios[str_id]['totais_semana']['corte']
            real_remover = min(quantidade, qnt_atual_total)

            usuarios[str_id]['producao_diaria'][dia_nome]['corte'] = max(0, qnt_atual_dia - real_remover)
            usuarios[str_id]['totais_semana']['corte'] = max(0, qnt_atual_total - real_remover)
            usuarios[str_id]['producao_diaria'][dia_nome]['improdutivo'] += real_remover
            usuarios[str_id]['totais_semana']['improdutivo'] += real_remover
            salvar_banco(usuarios)

            bot.reply_to(message, f"🔄 *CONVERSÃO EXECUTADA*\n-{real_remover} Corte(s)\n+{real_remover} Improdutivo(s)", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "⚠️ Valores devem ser inteiros.", parse_mode="Markdown")

# ==========================================
# PROCESSAMENTO DE BOTÕES E CALLBACKS
# ==========================================
def processar_lancamento(user_id, tipo_id, tipo_nome, quantidade):
    agora = datetime.now()
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

    elif call.data == 'convert_corte_1':
        dia_nome = DIAS_SEMANA.get(datetime.now().weekday(), 'SAB')
        qnt_atual_dia = usuarios[user_id]['producao_diaria'][dia_nome]['corte']
        qnt_atual_total = usuarios[user_id]['totais_semana']['corte']
        
        if qnt_atual_total > 0:
            usuarios[user_id]['producao_diaria'][dia_nome]['corte'] = max(0, qnt_atual_dia - 1)
            usuarios[user_id]['totais_semana']['corte'] = max(0, qnt_atual_total - 1)
            usuarios[user_id]['producao_diaria'][dia_nome]['improdutivo'] += 1
            usuarios[user_id]['totais_semana']['improdutivo'] += 1
            salvar_banco(usuarios)
            bot.answer_callback_query(call.id, "🔄 1 Corte convertido em Improdutivo!", show_alert=False)
        else:
            bot.answer_callback_query(call.id, "⚠️ Você não possui cortes nesta semana para converter!", show_alert=True)

    elif call.data == 'convert_religacao_1':
        dia_nome = DIAS_SEMANA.get(datetime.now().weekday(), 'SAB')
        qnt_atual_dia = usuarios[user_id]['producao_diaria'][dia_nome]['religacao']
        qnt_atual_total = usuarios[user_id]['totais_semana']['religacao']
        
        if qnt_atual_total > 0:
            usuarios[user_id]['producao_diaria'][dia_nome]['religacao'] = max(0, qnt_atual_dia - 1)
            usuarios[user_id]['totais_semana']['religacao'] = max(0, qnt_atual_total - 1)
            usuarios[user_id]['producao_diaria'][dia_nome]['improdutivo'] += 1
            usuarios[user_id]['totais_semana']['improdutivo'] += 1
            salvar_banco(usuarios)
            bot.answer_callback_query(call.id, "🔄 1 Religação convertida em Improdutivo!", show_alert=False)
        else:
            bot.answer_callback_query(call.id, "⚠️ Você não possui religações nesta semana para converter!", show_alert=True)

    elif call.data == 'confirm_reset_semana':
        usuarios[user_id]['totais_semana'] = {'corte': 0, 'religacao': 0, 'reaviso': 0, 'improdutivo': 0}
        for dia in DIAS_SEMANA.values():
            usuarios[user_id]['producao_diaria'][dia] = {'corte': 0, 'religacao': 0, 'reaviso': 0, 'improdutivo': 0}
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
