import telebot
from telebot import types
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math
import random
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

# --- LISTA DE 105 FRASES MOTIVACIONAIS OPERACIONAIS (EQUATORIAL / CAMPO) ---
FRASES_MOTIVACIONAIS = [
    "Mais um pra conta na rua! 🚀",
    "Excelente atendimento e execução no cliente! 💪",
    "Foco na meta e na rota! 🎯",
    "Acelera com segurança que a vitória é certa! ⚡",
    "Trabalho impecável em campo! 🔥",
    "Menos uma OS no sistema, parabéns! 👏",
    "A constância na moto gera o resultado! 🏆",
    "Segue o plano e a rota operacional! 📈",
    "Cada serviço concluído aproxima a bonificação! 🥇",
    "Pra cima, rodando firme! 💥",
    "Determinação total na fiscalização e religue! ⚡",
    "Sua dedicação faz a diferença no sistema! 🌟",
    "Produtividade e agilidade no guidão! 🔝",
    "Nada segura quem tem foco e agilidade! 🏃‍♂️",
    "Mais uma missão de campo cumprida! ✅",
    "Mantendo o ritmo forte na rua! 🏍️",
    "Construindo o resultado quadra por quadra! 🛠️",
    "O esforço em cada medidor compensa! 💪",
    "Execução perfeita e dentro do padrão! ✨",
    "Mais um passo rumo à meta do mês! 🏁",
    "A recompensa do empenho vem no contracheque! 💰",
    "Respeito ao cliente e agilidade no serviço! 🤝",
    "Ritmo acelerado e postura profissional! ⚡",
    "Mantenha a pegada e a atenção na pilotagem! 🔥",
    "Trabalho duro e seguro sempre vence! 🤛",
    "Incrível agilidade no atendimento! ⚡",
    "Mais um cliente atendido com sucesso! 🎉",
    "Focado, produtivo e seguro! 📊",
    "Seu esforço garante a Faixa 3! 🏆",
    "Avançando firme nas ordens de serviço! 🎯",
    "Excelente desempenho no poste e no medidor! 👏",
    "Domínio total do percurso e das ordens! 🛠️",
    "Direto ao ponto, com padrão Equatorial! 🎯",
    "Não para! Cada corte e religue conta! 🚀",
    "Foco, força e produção no trecho! 💪",
    "Trabalho feito com padrão e segurança! 👑",
    "Superando os limites no trecho hoje! ⚡",
    "Garantindo a bonificação da semana! 💰",
    "Mais uma etapa concluída com sucesso! 🏁",
    "Orgulho do trabalho bem feito no campo! 🌟",
    "Organização, educação e agilidade! ⏱️",
    "Cada nota baixada é meta atingida! 🥇",
    "Mostrou como se faz no campo! 👌",
    "Eficiência e postura em primeiro lugar! ⚡",
    "Siga firme no propósito e na pilotagem! 🎯",
    "Sua garra no trecho é inspiradora! 🔥",
    "Mais um serviço registrado no sistema! 📝",
    "O topo do ranking de produção é seu! 🏔️",
    "Progresso contínuo em cada bairro! 📈",
    "Fazendo acontecer com a moto no campo! 💥",
    "Resultado garantido com muito trabalho! ✅",
    "Equatorial Energia em movimento no trecho! ⚡",
    "Atendimento ao cliente com respeito e precisão! 🤝",
    "Religue rápido, cliente satisfeito e meta batida! 🔌",
    "Capacete na cabeça, foco na OS e mão no acelerador! 🏍️",
    "Segurança em primeiro lugar, produção em alto nível! 🛡️",
    "Mais um Reaviso entregue em mãos! ✋",
    "Atendimento nota 10 no campo! 🌟",
    "Profissionalismo que se destaca no setor! 👔",
    "A rotina do campo é dura, mas a vitória é certa! 🏆",
    "Acelera na rota com responsabilidade! 🚦",
    "Agilidade no alicate e no aplicativo! 🛠️",
    "Cada medidor inspecionado é um passo à frente! 🔍",
    "Faixa 3 cada vez mais perto! 💰",
    "Postura firme e respeitosa com o cliente! 🤜🤛",
    "Rodando a cidade inteira com energia total! ⚡",
    "Comunicação clara com o cliente gera respeito! 🗣️",
    "Sem tempo a perder, produção a mil! ⏱️",
    "O trabalho em campo transforma dedicação em resultado! 📈",
    "Mais um serviço finalizado com excelência! 🎯",
    "Qualidade no atendimento e foco na meta! ✨",
    "Com sol ou chuva, a produção não para! 🌧️☀️",
    "Controle total da rota e das baixas! 📱",
    "Postura exemplar em campo! 🎖️",
    "A meta da semana já está no bolso! 💵",
    "Mais uma religação para trazer luz ao cliente! 💡",
    "Atenção aos detalhes e foco no padrão operacional! 📋",
    "O empenho diário constrói o sucesso no final do mês! 📅",
    "Agilidade sem abrir mão da segurança! 🛑",
    "Dia produtivo é dia de meta superada! 🚀",
    "A confiança do cliente se conquista com respeito! 🤝",
    "Mais uma OS baixada com perfeição! ✅",
    "Agente comercial em ação no campo! ⚡",
    "Sua agilidade no trecho faz a diferença! 🏍️",
    "Fazer o certo no padrão Equatorial é o caminho! 🎯",
    "Meta atingida é consequência do seu esforço! 🏆",
    "Religou, notificou e produziu! ⚡",
    "Respeito ao consumidor e agilidade na execução! 🤝",
    "Na moto ou no poste, o padrão é elevado! 🛡️",
    "O trabalho honesto no trecho rende frutos! 🍎",
    "Atendimento rápido é satisfação garantida! ⏱️",
    "Siga o roteiro e supere suas marcas! 🗺️",
    "Mais um Reaviso negociado e entregue! 📬",
    "Energia positiva no trabalho do dia a dia! ⚡",
    "Cada ordem concluída reflete sua competência! 🌟",
    "Resolução rápida e postura profissional! 🛠️",
    "O cliente percebe quando o serviço é bem feito! 👌",
    "Determinação no trecho para buscar a bonificação máxima! 💰",
    "Pilote com cuidado e produza com excelência! 🏍️",
    "Foco no processo, agilidade na execução! ⚡",
    "A rotina da rua exige garra, e você tem de sobra! 🔥",
    "Serviço prestado com padrão, agilidade e respeito! 🎖️",
    "A meta da Equatorial tá pequena pro seu ritmo! 🚀",
    "Trabalho impecável, rotina vencida! 🏆",
    "Na pegada da Faixa 3 do início ao fim! 💥"
]

# --- AVISO INSTITUCIONAL INDEPENDENTE ---
AVISO_INDEPENDENTE = (
    "⚠️ *AVISO IMPORTANTE DE USO*\n\n"
    "Este bot *NÃO é um sistema oficial da empresa* e não possui qualquer vínculo com a concessionária.\n"
    "Trata-se de uma ferramenta independente desenvolvida por um funcionário para auxílio e controle pessoal de suas metas e bonificações.\n\n"
    "📌 *Nota:* Todas as informações e números registrados são inseridos manualmente pelo próprio usuário e são totalmente manipuláveis, "
    "servindo exclusivamente como um painel pessoal de acompanhamento."
)

# --- SERVIDOR WEB DE MANUTENÇÃO DE STATUS (RAILWAY) ---
app = Flask('')

@app.route('/')
def home():
    return "Sistema Operacional Online!"

def run():
    app.run(host='0.0.0.0', port=8080)

t = Thread(target=run)
t.start()

# --- CONFIGURAÇÃO DO BOT E BANCO POSTGRESQL ---
TOKEN = os.environ.get('BOT_TOKEN', '8804109455:AAE9YoV5_kEH5v2pCck6JNi5Ni_gIseQOpA')
bot = telebot.TeleBot(TOKEN)

PESO_SERVICO = 13.64
PESO_REAVISO = 7.80

def get_db_connection():
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError("A variável DATABASE_URL não foi encontrada no ambiente.")
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

# --- TECLADOS E INTERFACES (BOTÕES EXPANDIDOS PARA USO RÁPIDO NO CAMPO) ---
def menu_principal_keyboard():
    # resize_keyboard=False faz os botões ficarem grandes na tela e is_persistent=True fixa o menu
    markup = types.ReplyKeyboardMarkup(resize_keyboard=False, is_persistent=True, row_width=2)
    btn_relatorio = types.KeyboardButton('📊 Relatório Semanal')
    btn_mensal = types.KeyboardButton('📅 Histórico Mensal')
    btn_registrar = types.KeyboardButton('⚡ Registrar Produção')
    btn_comandos = types.KeyboardButton('📜 Comandos & Termos')
    btn_reset_semana = types.KeyboardButton('🔄 Resetar Semana')
    
    markup.add(btn_relatorio, btn_mensal)
    markup.add(btn_registrar, btn_comandos)
    markup.add(btn_reset_semana)
    return markup

def teclado_registro_rapido():
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("🔌 Religue +1", callback_data="add_religacao_1"),
        types.InlineKeyboardButton("✋ Reaviso em Mãos +1", callback_data="convert_maos_1"),
        types.InlineKeyboardButton("🚫 Improdutivo +1", callback_data="add_improdutivo_1")
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

# --- FUNÇÕES DE CAPTURA CONTINUA (NEXT STEP) ---
def receber_qnt_corte(message):
    try:
        qnt = int(message.text)
        processar_lancamento(message.from_user.id, 'corte', qnt)
        frase = random.choice(FRASES_MOTIVACIONAIS)
        bot.reply_to(message, f"✅ *+ {qnt} Corte(s)* adicionado(s) com sucesso!\n\n💬 _{frase}_", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠️ Valor inválido. Digite apenas números inteiros.", parse_mode="Markdown")

def receber_qnt_religacao(message):
    try:
        qnt = int(message.text)
        processar_lancamento(message.from_user.id, 'religacao', qnt)
        frase = random.choice(FRASES_MOTIVACIONAIS)
        bot.reply_to(message, f"✅ *+ {qnt} Religação(ões)* adicionada(s) com sucesso!\n\n💬 _{frase}_", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠️ Valor inválido. Digite apenas números inteiros.", parse_mode="Markdown")

def receber_qnt_reaviso_outros(message):
    try:
        qnt = int(message.text)
        processar_lancamento(message.from_user.id, 'reaviso_outros', qnt)
        bot.reply_to(message, f"✅ *+ {qnt} Reaviso(s)* adicionado(s) à sua carga!", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠️ Valor inválido. Digite apenas números inteiros.", parse_mode="Markdown")

# --- HANDLERS DE COMANDOS DE TEXTO E MENUS ---
@bot.message_handler(commands=['start'])
def start(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)
    texto = (
        f"🌐 *SISTEMA OPERACIONAL ATIVO*\n"
        f"Bem-vindo, {nome}.\n\n"
        f"{AVISO_INDEPENDENTE}\n\n"
        "Selecione uma das opções no menu abaixo:"
    )
    bot.reply_to(message, texto, parse_mode="Markdown", reply_markup=menu_principal_keyboard())

@bot.message_handler(commands=['comandos', 'ajuda', 'help', 'aviso'])
@bot.message_handler(func=lambda m: m.text == '📜 Comandos & Termos')
def listar_comandos(message):
    texto = (
        "📜 *LISTA DE COMANDOS DISPONÍVEIS*\n\n"
        "📊 *Relatórios e Histórico:*\n"
        "• `/relatorio` ou `/prod` - Exibe o resumo da semana atual\n"
        "• `/mensal` ou `/historico` - Consulta o histórico mês a mês e valores acumulados\n"
        "• `/resetar` - Zera a contagem da semana mantendo o histórico salvo\n"
        "• `/zerar_mensal` - Zera permanentemente todo o histórico\n\n"
        "⚡ *Lançamentos Rápidos por Texto:*\n"
        "• `/corte [qnt]` - Registra cortes (Ex: `/corte 10`)\n"
        "• `/rel [qnt]` - Registra religações (Ex: `/rel 5`)\n"
        "• `/rea [qnt]` - Registra carga de reavisos (Ex: `/rea 30`)\n"
        "• `/imp [qnt]` - Registra improdutivos (Ex: `/imp 2`)\n"
        "• `/maos [qnt]` - Transfere reavisos para 'em mãos' (Ex: `/maos 2`)\n\n"
        "⚙️ *Ajustes de Dia Específico:*\n"
        "• `/addcorte [dia] [qnt]` - Lança cortes em dia específico (Ex: `/addcorte seg 10`)\n\n"
        f"----------------------------------------\n"
        f"{AVISO_INDEPENDENTE}"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == '⚡ Registrar Produção')
def menu_registro(message):
    bot.reply_to(message, "⚡ *PAINEL DE REGISTRO RÁPIDO*\nToque abaixo para registrar:", 
                 parse_mode="Markdown", reply_markup=teclado_registro_rapido())

@bot.message_handler(commands=['maos'])
def converter_maos_manual(message):
    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    try:
        partes = message.text.split()
        qnt = int(partes[1]) if len(partes) > 1 else 1
        converter_reaviso_para_maos(str_id, qnt)
        frase = random.choice(FRASES_MOTIVACIONAIS)
        bot.reply_to(message, f"✋ *{qnt} Reaviso(s) ajustado(s) para EM MÃOS!*\n\n💬 _{frase}_", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠️ Sintaxe: `/maos` para 1 ou `/maos 5` para vários.", parse_mode="Markdown")

@bot.message_handler(commands=['addcorte', 'cortedia'])
def add_corte_dia_especifico(message):
    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    try:
        partes = message.text.split()
        if len(partes) < 3:
            return bot.reply_to(message, "⚠️ Use: `/addcorte [dia] [qnt]`", parse_mode="Markdown")

        dia_input = partes[1].upper().strip()
        quantidade = int(partes[2])

        mapa_dias = {
            'SEG': 'SEG', 'SEGUNDA': 'SEG', 'TER': 'TERCA', 'TERCA': 'TERCA',
            'QUA': 'QUARTA', 'QUARTA': 'QUARTA', 'QUI': 'QUINTA', 'QUINTA': 'QUINTA',
            'SEX': 'SEXTA', 'SEXTA': 'SEXTA', 'SAB': 'SAB', 'SABADO': 'SAB'
        }

        if dia_input not in mapa_dias:
            return bot.reply_to(message, "⚠️ Dias válidos: `SEG`, `TERCA`, `QUARTA`, `QUINTA`, `SEXTA`, `SAB`", parse_mode="Markdown")

        dia_chave = mapa_dias[dia_input]
        processar_lancamento(str_id, 'corte', quantidade, dia_especifico=dia_chave)
        frase = random.choice(FRASES_MOTIVACIONAIS)
        bot.reply_to(message, f"✅ +{quantidade} Corte(s) lançado(s) no dia *{dia_chave}*\n\n💬 _{frase}_", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Erro ao processar: {str(e)}", parse_mode="Markdown")

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
        
        frase_extra = f"\n\n💬 _{random.choice(FRASES_MOTIVACIONAIS)}_" if tipo_id in ['corte', 'religacao'] else ""
        bot.reply_to(message, f"✅ *+{quantidade} {tipo_nome}(s)* registrado(s)!{frase_extra}", parse_mode="Markdown")
    except:
        bot.reply_to(message, f"⚠️ Sintaxe: `{comando} 10`", parse_mode="Markdown")

# --- RELATÓRIOS E CONSULTAS COM VALOR PARCIAL MENSAL SALVO ---
@bot.message_handler(func=lambda m: m.text == '📅 Histórico Mensal' or m.text in ['/mensal', '/meses', '/historico'])
def relatorio_mensal(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)
    
    dados_meses = obter_historico_mensal(str_id)
    
    if not dados_meses:
        return bot.reply_to(message, "📂 *Nenhum histórico mensal registrado no momento.*", parse_mode="Markdown")
    
    texto = f"📅 *HISTÓRICO MENSAL DE PRODUÇÃO SALVO*\n👤 Agente: *{nome.upper()}*\n\n"
    
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
        
        # Cálculo de pontos do mês para determinar valor estimado e faixa atingida
        pts_mes = (cr * PESO_SERVICO) + (rv * PESO_REAVISO)
        m_f1_pts, m_f2_pts, m_f3_pts = 250 * PESO_SERVICO, 300 * PESO_SERVICO, 350 * PESO_SERVICO
        
        if pts_mes >= m_f3_pts:
            valor_bonif = 300.00
            faixa_nome = "Faixa 3"
        elif pts_mes >= m_f2_pts:
            valor_bonif = 200.00
            faixa_nome = "Faixa 2"
        elif pts_mes >= m_f1_pts:
            valor_bonif = 150.00
            faixa_nome = "Faixa 1"
        else:
            valor_bonif = 0.00
            faixa_nome = "Sem Faixa"
            
        bonif_str = f"{valor_bonif:,.2f}".replace('.', ',')
        
        texto += (
            f"🗓️ *{nome_mes} / {ano}*\n"
            f"• Cortes / Religações: *{cr}*\n"
            f"• Reavisos Atendidos: *{rv}*\n"
            f"• Improdutivos: *{imp}*\n"
            f"• Faixa Atingida: *{faixa_nome}*\n"
            f"💰 *Valor parcial estimado:* *R$ {bonif_str}*\n"
            f"🗓️ *Pagamento Previsto:* *{nome_mes_pag} / {ano_pag}*\n"
            f"----------------------------------------\n"
        )
    
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

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
        f"👋 Olá {nome.upper()}, segue o resumo da sua produção na semana:\n\n"
        f"📅 Semana ({data_inicio} a {data_fim}):\n"
        f"• Cortes/Religações: {cr}\n"
        f"• Reavisos: {detalhe_reaviso}\n"
        f"• Entregas / Improdutivos: {en}\n"
        f"• Negociações: {ng}\n"
        f"• Faixa: {faixa_str}\n"
        f"• {falta_str}\n"
        f"💰 Bonificação estimada: R$ {bonif_str}\n\n"
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
        "```\n"
        "Data       | CR | RV | EN | NG\n"
        "--------------------------------\n"
        f"{tabela_formatada}\n"
        "```"
    )

    bot.send_message(message.chat.id, msg_diario, parse_mode="Markdown")

# --- COMANDOS DE RESET E ZERAR ---
@bot.message_handler(func=lambda m: m.text == '🔄 Resetar Semana' or m.text == '/resetar')
def solicitar_reset_semana(message):
    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    bot.reply_to(
        message, 
        "⚠️ *CONFIRMAÇÃO DE RESET SEMANAL*\n\n"
        "Deseja zerar a contagem ativa da semana atual? (Os dados continuarão salvos no histórico mensal).", 
        parse_mode="Markdown", 
        reply_markup=teclado_confirmacao_reset_semana()
    )

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
        "🚨 *ATENÇÃO: EXCLUSÃO TOTAL DO HISTÓRICO MENSAL*\n\n"
        "Esta ação apagará permanentemente todos os lançamentos do banco de dados.\n\n"
        "Deseja zerar o histórico do `/mensal`?", 
        parse_mode="Markdown", 
        reply_markup=markup
    )

# --- RESPOSTAS DOS BOTÕES INLINE COM ALERTA EM POP-UP (MEIO DA TELA) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)
    inicializar_agente(user_id, call.from_user.first_name)

    if call.data == 'prompt_corte':
        msg = bot.send_message(call.message.chat.id, "✂️ *Digite a quantidade de Cortes:*", parse_mode="Markdown")
        bot.register_next_step_handler(msg, receber_qnt_corte)
        bot.answer_callback_query(call.id)

    elif call.data == 'prompt_religacao':
        msg = bot.send_message(call.message.chat.id, "🔌 *Digite a quantidade de Religações:*", parse_mode="Markdown")
        bot.register_next_step_handler(msg, receber_qnt_religacao)
        bot.answer_callback_query(call.id)

    elif call.data == 'prompt_reaviso_outros':
        msg = bot.send_message(call.message.chat.id, "📬 *Digite a quantidade de Reavisos:*", parse_mode="Markdown")
        bot.register_next_step_handler(msg, receber_qnt_reaviso_outros)
        bot.answer_callback_query(call.id)

    # Lançamentos Rápidos: show_alert=True força a mensagem abrir no meio da tela como Pop-Up
    elif call.data == 'add_religacao_1':
        processar_lancamento(user_id, 'religacao', 1)
        frase = random.choice(FRASES_MOTIVACIONAIS)
        bot.answer_callback_query(call.id, f"🔌 +1 RELIGUE REGISTRADO!\n\n{frase}", show_alert=True)

    elif call.data == 'convert_maos_1':
        converter_reaviso_para_maos(user_id, 1)
        frase = random.choice(FRASES_MOTIVACIONAIS)
        bot.answer_callback_query(call.id, f"✋ +1 REAVISO EM MÃOS!\n\n{frase}", show_alert=True)

    elif call.data == 'add_improdutivo_1':
        processar_lancamento(user_id, 'improdutivo', 1)
        bot.answer_callback_query(call.id, "🚫 +1 IMPRODUTIVO REGISTRADO!", show_alert=True)

    elif call.data == 'confirm_reset_semana':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE lancamentos SET semana_ativa = FALSE WHERE user_id = %s AND semana_ativa = TRUE;", (user_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        bot.edit_message_text("🔄 *CICLO SEMANAL ZERADO! DADOS GUARDADOS NO MENSAL.*", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Semana zerada com sucesso!", show_alert=True)

    elif call.data == 'cancel_reset_semana':
        bot.edit_message_text("❌ *OPERAÇÃO CANCELADA.*", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Cancelado!")

    elif call.data == 'confirm_zerar_mensal':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM lancamentos WHERE user_id = %s;", (user_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        bot.edit_message_text("🗑️ *HISTÓRICO MENSAL ZERADO COM SUCESSO!*", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Histórico zerado!", show_alert=True)

    elif call.data == 'cancel_zerar_mensal':
        bot.edit_message_text("❌ *OPERAÇÃO CANCELADA.*", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Cancelado!")

# --- INICIALIZAÇÃO SEGURA DO SERVIÇO ---
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
