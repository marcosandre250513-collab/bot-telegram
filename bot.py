import telebot
from telebot import types
from datetime import datetime, timedelta, timezone
import math
from flask import Flask
from threading import Thread
import io
import json
import os
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURAÇÃO DO FUSO HORÁRIO NATIVO (SÃO PAULO / BRASÍLIA UTC-3) ---
FUSO_SP = timezone(timedelta(hours=-3))

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
# GERADOR DE IMAGEM: RELATÓRIO DA SEMANA (TEMA CLARO)
# ==========================================
def gerar_imagem_relatorio(nome, totais, dias, pontos_total, status_msg):
    img = Image.new('RGB', (900, 1500), color='#f1f5f9')
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(32)
    font_sub = get_font(22)
    font_main = get_font(24)
    font_small = get_font(18)

    COR_FUNDO = '#f1f5f9'
    COR_CARD = '#ffffff'
    COR_BORDA = '#cbd5e1'
    COR_TEXTO = '#0f172a'
    COR_SUBTEXTO = '#475569'
    COR_DESTAQUE = '#0284c7' 
    COR_ALERTA = '#dc2626'   
    COR_TABELA_HDR = '#1e293b'
    COR_ZEBRA = '#f8fafc'

    # CABEÇALHO SUPERIOR (DARK SLATE PARA CONTRASTE EXECUTIVO)
    draw.rectangle([0, 0, 900, 130], fill='#0f172a')
    draw.text((40, 28), "MINHA PERFORMANCE", fill='#ffffff', font=font_title)
    
    hoje = agora_sp()
    data_emissao = hoje.strftime("%d/%m/%Y - %H:%M:%S")
    draw.text((40, 78), f"EMISSÃO: {data_emissao} | AGENTE: {nome.upper()}", fill='#38bdf8', font=font_sub)

    # CARD STATUS ATUAL
    draw.rectangle([40, 150, 860, 250], fill=COR_CARD, outline=COR_BORDA, width=2)
    draw.text((60, 170), f"STATUS ATUAL: {status_msg}", fill=COR_DESTAQUE, font=font_main)
    draw.text((60, 208), "📌 PAINEL DE AUTO-GESTÃO E PERFORMANCE", fill=COR_SUBTEXTO, font=font_sub)

    # CARD DETALHAMENTO COM TABELA FORMATADA
    draw.rectangle([40, 275, 860, 685], fill=COR_CARD, outline=COR_BORDA, width=2)
    draw.text((60, 292), "DETALHAMENTO DA PRODUÇÃO SEMANAL", fill=COR_TEXTO, font=font_main)

    # CABEÇALHO DA TABELA
    draw.rectangle([50, 330, 850, 375], fill=COR_TABELA_HDR)
    
    x_dia, x_corte, x_rel, x_rea, x_imp, x_tot = 65, 215, 345, 475, 605, 735
    draw.text((x_dia, 340), "DIA (DATA)", fill='#ffffff', font=font_sub)
    draw.text((x_corte, 340), "CORTE", fill='#ffffff', font=font_sub)
    draw.text((x_rel, 340), "RELIG", fill='#ffffff', font=font_sub)
    draw.text((x_rea, 340), "REAVISO", fill='#ffffff', font=font_sub)
    draw.text((x_imp, 340), "IMP.", fill='#fca5a5', font=font_sub)
    draw.text((x_tot, 340), "TOTAL", fill='#7dd3fc', font=font_sub)

    # LINHAS DA TABELA (COM ZEBRADO E GRADE)
    y_row = 375
    valores_dias = []
    
    segunda_feira = hoje - timedelta(days=hoje.weekday())
    dias_ordem = ['SEG', 'TERCA', 'QUARTA', 'QUINTA', 'SEXTA', 'SAB']
    
    # Colunas verticais da grade
    cols_x = [50, 200, 330, 460, 590, 720, 850]

    for idx, dia in enumerate(dias_ordem):
        d = dias.get(dia, {'corte': 0, 'religacao': 0, 'reaviso': 0, 'improdutivo': 0})
        total_prod = d['corte'] + d['religacao'] + d['reaviso']
        
        data_dia = (segunda_feira + timedelta(days=idx)).strftime("%d/%m")
        nome_exibicao = f"{dia[:3]} {data_dia}"
        valores_dias.append((nome_exibicao, total_prod))
        
        # Fundo zebrado
        cor_fundo_linha = COR_ZEBRA if idx % 2 == 0 else '#ffffff'
        draw.rectangle([50, y_row, 850, y_row + 45], fill=cor_fundo_linha)
        
        # Linha horizontal
        draw.line([50, y_row + 45, 850, y_row + 45], fill=COR_BORDA, width=1)
        
        # Textos das células
        y_text = y_row + 10
        draw.text((x_dia, y_text), nome_exibicao, fill=COR_TEXTO, font=font_main)
        draw.text((x_corte, y_text), f"{d['corte']}", fill=COR_TEXTO, font=font_main)
        draw.text((x_rel, y_text), f"{d['religacao']}", fill=COR_TEXTO, font=font_main)
        draw.text((x_rea, y_text), f"{d['reaviso']}", fill=COR_TEXTO, font=font_main)
        draw.text((x_imp, y_text), f"{d['improdutivo']}", fill=COR_ALERTA, font=font_main)
        draw.text((x_tot, y_text), f"{total_prod}", fill=COR_DESTAQUE, font=font_main)
        
        y_row += 45

    # Desenhar linhas verticais da grade
    for cx in cols_x:
        draw.line([cx, 330, cx, y_row], fill=COR_BORDA, width=1)

    # CARD 2: GRÁFICO DE COLUNAS (BARRAS VERTICAIS)
    draw.rectangle([40, 710, 860, 950], fill=COR_CARD, outline=COR_BORDA, width=2)
    draw.text((60, 728), "DESEMPENHO DIÁRIO (COLUNAS)", fill=COR_TEXTO, font=font_main)
    draw.line([40, 765, 860, 765], fill=COR_BORDA, width=1)

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
        
        # Barra do gráfico
        draw.rectangle([x1, y1, x2, y2], fill=COR_DESTAQUE, outline='#0369a1', width=1)
        draw.text((x_pos - 28, 912), dia_nome, fill=COR_SUBTEXTO, font=font_small)
        
        if valor > 0:
            draw.text((x_pos - 12, y1 - 25), str(valor), fill=COR_TEXTO, font=font_main)
            
        x_pos += espaco

    # CARD 3: STATUS DAS FAIXAS E PROGRESSÃO DE METAS
    draw.rectangle([40, 975, 860, 1370], fill=COR_CARD, outline=COR_BORDA, width=2)
    draw.text((60, 992), "STATUS DAS FAIXAS E PROGRESSÃO DE METAS", fill=COR_TEXTO, font=font_main)
    draw.line([40, 1030, 860, 1030], fill=COR_BORDA, width=1)

    hoje_idx = hoje.weekday()
    dias_restantes = max(1, 6 - hoje_idx)

    def text_meta(meta_qnt):
        meta_pontos = meta_qnt * PESO_SERVICO
        falta_pontos = meta_pontos - pontos_total
        if falta_pontos <= 0: 
            return "META ATINGIDA OK"
            
        faltam_servicos = math.ceil(falta_pontos / PESO_SERVICO)
        faltam_reavisos = math.ceil(falta_pontos / PESO_REAVISO)
        media_servicos = math.ceil(faltam_servicos / dias_restantes)
        
        return f"Faltam {faltam_servicos} Serviços ({media_servicos}/dia) ou {faltam_reavisos} Reavisos"

    total_servicos_brutos = totais['corte'] + totais['religacao'] + totais['reaviso']
    draw.text((60, 1048), f"VOLUME PRODUTIVO TOTAL: {total_servicos_brutos} Serviços", fill=COR_TEXTO, font=font_main)
    draw.text((60, 1083), f"VOLUME IMPRODUTIVO TOTAL: {totais['improdutivo']} Serviços", fill=COR_ALERTA, font=font_main)

    m_f1, m_f2, m_f3 = 250, 300, 350
    faixas = [(1, m_f1, "#d97706"), (2, m_f2, "#7c3aed"), (3, m_f3, "#059669")]
    y_faixa = 1135
    for num, meta_qnt, cor in faixas:
        meta_pontos = meta_qnt * PESO_SERVICO
        pct = min(1.0, pontos_total / meta_pontos) if meta_pontos > 0 else 0
        draw.text((60, y_faixa), f"FAIXA {num}: {text_meta(meta_qnt)} [{int(pct * 100)}%]", fill=COR_TEXTO, font=font_main)
        draw.rectangle([60, y_faixa + 32, 840, y_faixa + 45], fill='#e2e8f0', outline=COR_BORDA, width=1)
        if pct > 0: 
            draw.rectangle([60, y_faixa + 32, 60 + (780 * pct), y_faixa + 45], fill=cor)
        y_faixa += 70

    # CARD DE DESTAQUE NO RODAPÉ (TEMA CLARO COM ASSINATURA EXECUTIVA)
    draw.rectangle([40, 1395, 860, 1475], fill='#f0f9ff', outline=COR_DESTAQUE, width=2)
    draw.text((60, 1408), "📌 PAINEL DE AUTO-GESTÃO E PERFORMANCE - APOIO DE CAMPO", fill=COR_DESTAQUE, font=font_sub)
    draw.text((60, 1442), "⚡ Desenvolvido por Agente de Campo para controle e otimização de metas.", fill=COR_SUBTEXTO, font=font_small)

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

# ==========================================
# GERADOR DE IMAGEM: LOG HISTÓRICO (ÚLTIMOS 180 - TEMA CLARO)
# ==========================================
def gerar_imagem_historico(nome, historico):
    img = Image.new('RGB', (900, 1300), color='#f1f5f9')
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(32)
    font_sub = get_font(22)
    font_main = get_font(26)
    font_small = get_font(18)

    COR_FUNDO, COR_CARD, COR_BORDA = '#f1f5f9', '#ffffff', '#cbd5e1'
    COR_TEXTO, COR_SUBTEXTO, COR_DESTAQUE = '#0f172a', '#475569', '#0284c7' 
    COR_ALERTA = '#dc2626'

    draw.rectangle([0, 0, 900, 130], fill='#0f172a')
    draw.text((40, 28), "AUDITORIA DE DADOS - LOG PERMANENTE", fill='#ffffff', font=font_title)
    draw.text((40, 78), f"AGENTE: {nome.upper()} | PAINEL DE AUTO-GESTÃO", fill='#38bdf8', font=font_sub)

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

    draw.rectangle([40, 150, 860, 250], fill=COR_CARD, outline=COR_BORDA, width=2)
    draw.text((60, 170), f"VOLUME HISTÓRICO TOTAL: {total_geral} serviços (Ativos)", fill=COR_DESTAQUE, font=font_main)
    draw.text((60, 208), f"TOTAL DE EVENTOS: {len(historico_180)} registros (últimos 180)", fill=COR_TEXTO, font=font_main)

    draw.rectangle([40, 275, 860, 625], fill=COR_CARD, outline=COR_BORDA, width=2)
    draw.text((60, 292), "CURVA DE EVOLUÇÃO HISTÓRICA (Últimos dias ativos)", fill=COR_TEXTO, font=font_main)
    draw.line([40, 330, 860, 330], fill=COR_BORDA, width=1)

    if valores_grafico:
        max_valor = max([v[1] for v in valores_grafico] + [1])
        pontos_grafico = []
        largura_disponivel = 760
        espaco = largura_disponivel // max(len(valores_grafico), 2)
        x_pos = 100
        
        for dia_nome, valor in valores_grafico:
            altura = (valor / max_valor) * 180 if max_valor > 0 else 0
            y_pos = 560 - altura
            pontos_grafico.append((x_pos, y_pos))
            
            draw.text((x_pos - 20, 580), dia_nome, fill=COR_SUBTEXTO, font=font_sub)
            if valor > 0:
                draw.text((x_pos - 10, y_pos - 35), str(valor), fill=COR_DESTAQUE, font=font_main)
            x_pos += espaco

        if len(pontos_grafico) > 1: draw.line(pontos_grafico, fill=COR_DESTAQUE, width=4)
        for p in pontos_grafico: draw.ellipse([p[0]-6, p[1]-6, p[0]+6, p[1]+6], fill=COR_CARD, outline=COR_DESTAQUE, width=3)

    draw.rectangle([40, 650, 860, 1180], fill=COR_CARD, outline=COR_BORDA, width=2)
    draw.text((60, 668), "ÚLTIMOS LANÇAMENTOS SALVOS NO BANCO", fill=COR_TEXTO, font=font_main)
    draw.line([40, 705, 860, 705], fill=COR_BORDA, width=1)
    
    y_log = 725
    ultimos_logs = historico_180[-9:]
    for item in reversed(ultimos_logs):
        cor_log = COR_ALERTA if item['tipo'] == 'Improdutivo' else COR_SUBTEXTO
        draw.text((60, y_log), f">> {item['data']} | {item['tipo'].upper()}: +{item['quantidade']}", fill=cor_log, font=font_main)
        y_log += 45

    # CARD DE DESTAQUE NO RODAPÉ
    draw.rectangle([40, 1205, 860, 1285], fill='#f0f9ff', outline=COR_DESTAQUE, width=2)
    draw.text((60, 1218), "📌 PAINEL DE AUTO-GESTÃO E PERFORMANCE - APOIO DE CAMPO", fill=COR_DESTAQUE, font=font_sub)
    draw.text((60, 1252), "⚡ Desenvolvido por Agente de Campo para controle e otimização de metas.", fill=COR_SUBTEXTO, font=font_small)

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
        f"🌐 *SISTEMA DE PERFORMANCE DE CAMPO*\n"
        f"Bem-vindo(a), {nome}!\n\n"
        "⚠️ *AVISO DE APOIO OPERACIONAL*\n"
        "_Esta é uma ferramenta independente desenvolvida por Agente de Campo para auxílio no controle diário de produção e acompanhamento de metas._\n\n"
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

    if pontos_total >= (m_f3 * PESO_SERVICO): status_msg = "PERFORMANCE MÁXIMA (NÍVEL 3)"
    elif pontos_total >= (m_f2 * PESO_SERVICO): status_msg = "PERFORMANCE ELEVADA (NÍVEL 2)"
    elif pontos_total >= (m_f1 * PESO_SERVICO): status_msg = "PERFORMANCE PADRÃO (NÍVEL 1)"
    else: status_msg = "FRENTE OPERACIONAL (ABAIXO N1)"

    bot.send_chat_action(message.chat.id, 'upload_photo')
    bot.send_photo(message.chat.id, photo=gerar_imagem_relatorio(nome, t, dias, pontos_total, status_msg), 
                   caption="📈 *DASHBOARD DA SEMANA*", parse_mode="Markdown")

@bot.message_handler(commands=['historico'])
def ver_historico(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)

    historico = usuarios[str_id].get('historico_permanente', [])
    if not historico:
        return bot.reply_to(message, "📂 *LOG VAZIO.* Nenhum registro salvo no banco.", parse_mode="Markdown")

    bot.send_chat_action(message.chat.id, 'upload_photo')
    bot.send_photo(message.chat.id, photo=gerar_imagem_historico(nome, historico), 
                   caption="🗄️ *AUDITORIA DE DADOS - LOG PERMANENTE*", parse_mode="Markdown")

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
        dia_nome = DIAS_SEMANA.get(agora_sp().weekday(), 'SAB')

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

    elif call.data == 'convert_corte_1':
        dia_nome = DIAS_SEMANA.get(agora_sp().weekday(), 'SAB')
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
        dia_nome = DIAS_SEMANA.get(agora_sp().weekday(), 'SAB')
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
