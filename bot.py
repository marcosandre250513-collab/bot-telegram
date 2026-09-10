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
from PIL import Image, ImageDraw, ImageFont
import io

# --- CONFIGURAÇÃO DO ADMINISTRADOR DO BOT ---
ADMIN_ID = os.environ.get('ADMIN_ID', '8581499778') 

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

# --- LISTA DE FRASES MOTIVACIONAIS OPERACIONAIS ---
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

# --- LISTA DE 50 FRASES PARA TENTATIVAS IMPRODUTIVAS ---
FRASES_IMPRODUTIVO = [
    "🚫 Cliente ausente no local. Ocorrência salva!",
    "🚫 Portão fechado e sem campainha operacional.",
    "🚫 Cão solto no quintal! Segurança em primeiro lugar. 🐕",
    "🚫 Sem acesso à caixa de medição/padrão trancado.",
    "🚫 Endereço não localizado no roteiro.",
    "🚫 Local de difícil acesso ou área de risco.",
    "🚫 Padrão interno sem autorização de entrada.",
    "🚫 Medidor ausente ou retirado anteriormente.",
    "🚫 Imóvel desocupado e fechado.",
    "🚫 Impedimento do consumidor no local.",
    "🚫 Choveu forte, sem condições de acesso ao poste/caixa.",
    "🚫 Ramal inacessível no momento.",
    "🚫 Caixa com abelhas/insetos, risco operacional! 🐝",
    "🚫 Padrão energizado/risco de choque elétrico.",
    "🚫 Incompatibilidade de endereço na Ordem de Serviço.",
    "🚫 Imóvel em reforma, medidor inacessível.",
    "🚫 Morador recusou o atendimento no local.",
    "🚫 Disjuntor desligado internamente sem acesso.",
    "🚫 Cerca elétrica impedindo acesso seguro ao padrão.",
    "🚫 Medidor obstruído por entulho ou vegetação.",
    "🚫 Lacre violado com divergência, pendente de inspeção.",
    "🚫 Visita improdutiva registrada no sistema!",
    "🚫 Rota interrompida devido a obras na via.",
    "🚫 Imóvel comercial fechado fora do horário.",
    "🚫 Medidor muito alto sem espaço para escada.",
    "🚫 Cliente alega conta paga mas sem comprovante.",
    "🚫 Chave da caixa de medição indisponível.",
    "🚫 Animal feroz guardando o padrão. Ocorrência gerada! 🐶",
    "🚫 Fachada em construção sem número visível.",
    "🚫 Medidor queimado ou danificado, encaminhado.",
    "🚫 Sem resposta ao chamar no portão.",
    "🚫 Tensão irregular detectada, serviço suspenso.",
    "🚫 Padrão em altura fora da norma de segurança.",
    "🚫 Tapume/muro cobrindo o visor do medidor.",
    "🚫 Veículo estacionado bloqueando o poste/caixa.",
    "🚫 Solicitação de religue com fiação interna danificada.",
    "🚫 Consumidor ausente, reaviso deixado sob a porta.",
    "🚫 Morador não possui a chave do cadeado do padrão.",
    "🚫 Local sem iluminação adequada para manobra.",
    "🚫 Padrão inundado ou com água acumulada.",
    "🚫 Ramal clandestino identificado, repassado à fiscalização.",
    "🚫 Risco de queda em estrutura fragilizada.",
    "🚫 Vizinho informou que o imóvel está abandonado.",
    "🚫 Sem acesso ao condomínio/portaria não autorizou.",
    "🚫 Erro de cadastro da unidade consumidora.",
    "🚫 Discrepância na numeração da rua.",
    "🚫 Medidor instalado dentro da residência sem morador.",
    "🚫 Tentativa de execução sem sucesso. Próxima OS!",
    "🚫 Ocorrência de improdutividade computada na planilha!",
    "🚫 Mais uma tentativa registrada. Foco na rota! 📉"
]

# --- AVISO INSTITUCIONAL INDEPENDENTE ---
AVISO_INDEPENDENTE = (
    "⚠️ *AVISO IMPORTANTE DE USO*\n\n"
    "Este bot *NÃO é um sistema oficial da empresa* e não possui qualquer vínculo com a concessionária.\n"
    "Trata-se de uma ferramenta independente desenvolvida por um funcionário para auxílio e controle pessoal de suas metas e bonificações.\n\n"
    "📌 *Nota:* Todas as informações e números registrados são inseridos manualmente pelo próprio usuário e são totalmente manipuláveis, "
    "servindo exclusivamente como um painel pessoal de acompanhamento."
)

# --- SERVIDOR WEB DE MANUTENÇÃO DE STATUS ---
app = Flask('')

@app.route('/')
def home():
    return "Sistema Operacional Online!"

def run():
    app.run(host='0.0.0.0', port=8080)

t = Thread(target=run)
t.start()

# --- CONFIGURAÇÃO DO BOT E BANCO POSTGRESQL ---
TOKEN = os.environ.get('BOT_TOKEN', '8804109455:AAFQBAd3Lz2U4sd5nmNS6ZaxlX7jnE1MIZA')
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
            nome VARCHAR(100),
            autorizado BOOLEAN DEFAULT FALSE
        );
    ''')
    cur.execute('''
        ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS autorizado BOOLEAN DEFAULT FALSE;
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

def esta_autorizado(user_id):
    str_id = str(user_id)
    if str_id == str(ADMIN_ID):
        return True
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT autorizado FROM usuarios WHERE user_id = %s;", (str_id,))
    res = cur.fetchone()
    cur.close()
    conn.close()
    return res[0] if res and res[0] is not None else False

def definir_autorizacao(user_id, status: bool):
    str_id = str(user_id)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET autorizado = %s WHERE user_id = %s;", (status, str_id))
    conn.commit()
    cur.close()
    conn.close()

def inicializar_agente(user_id, nome):
    str_id = str(user_id)
    is_admin = (str_id == str(ADMIN_ID))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO usuarios (user_id, nome, autorizado)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET nome = EXCLUDED.nome;
    ''', (str_id, nome, is_admin))
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
            SUM(CASE WHEN tipo = 'corte' THEN quantidade ELSE 0 END) AS cortes,
            SUM(CASE WHEN tipo = 'religacao' THEN quantidade ELSE 0 END) AS religacoes,
            SUM(CASE WHEN tipo = 'reaviso_maos' THEN quantidade ELSE 0 END) AS rv_maos,
            SUM(CASE WHEN tipo = 'reaviso_outros' THEN quantidade ELSE 0 END) AS rv_outros,
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

# --- GERADOR DE IMAGEM DA TABELA SEMANAL (PARA O ENCARREGADO) ---
def criar_imagem_relatorio_semanal(nome, data_inicio, data_fim, totais, dias, faixa_str, bonif_str, pontos, mes_pagamento):
    width, height = 720, 820
    image = Image.new('RGB', (width, height), color=(20, 24, 33))
    draw = ImageDraw.Draw(image)
    
    font_main = ImageFont.load_default()

    # Cabeçalho
    draw.rectangle([(20, 20), (700, 100)], fill=(30, 41, 59), outline=(59, 130, 246), width=2)
    draw.text((40, 32), "COMPROVANTE DE PRODUCAO SEMANAL - CAMPO", fill=(255, 255, 255), font=font_main)
    draw.text((40, 58), f"Agente: {nome.upper()} | Periodo: {data_inicio} a {data_fim}", fill=(148, 163, 184), font=font_main)

    # Painel do Resumo
    draw.rectangle([(20, 115), (700, 360)], fill=(30, 41, 59), outline=(100, 116, 139), width=1)
    
    cr = totais.get('corte', 0) + totais.get('religacao', 0)
    rv_m = totais.get('reaviso_maos', 0)
    rv_o = totais.get('reaviso_outros', 0)
    rv_tot = rv_m + rv_o
    imp = totais.get('improdutivo', 0)
    ng = totais.get('negociacao', 0)

    lines_summary = [
        "---------------- RESUMO DE EXECUCAO ----------------",
        f"• Cortes / Religacoes (CR): {cr}",
        f"• Reavisos em Maos (RV-M):  {rv_m}",
        f"• Reavisos Outros (RV-O):   {rv_o}",
        f"• Total Reavisos (RV):      {rv_tot}",
        f"• Improdutivos (IMP):       {imp}",
        f"• Negociacoes (NG):          {ng}",
        "---------------- METAS E VALORES ----------------",
        f"⭐ Pontuacao Total:       {pontos:.2f} pts",
        f"🏆 Faixa Atingida:        {faixa_str}",
        f"💰 Bonificacao Estimada:  R$ {bonif_str}",
        f"🗓️ Mes de Pagamento:      {mes_pagamento.upper()}"
    ]

    y = 130
    for line in lines_summary:
        draw.text((40, y), line, fill=(226, 232, 240), font=font_main)
        y += 18

    # Tabela Diária
    draw.rectangle([(20, 380), (700, 750)], fill=(30, 41, 59), outline=(100, 116, 139), width=1)
    draw.text((40, 395), "---------------- TABELA DIARIA DE SERVICOS ----------------", fill=(255, 255, 255), font=font_main)
    draw.text((40, 425), "Data       | CR  | RV  | IMP | NG ", fill=(59, 130, 246), font=font_main)
    draw.text((40, 440), "--------------------------------------------------", fill=(100, 116, 139), font=font_main)

    hoje = agora_sp()
    segunda = hoje - timedelta(days=hoje.weekday())
    dias_ordem = ['SEG', 'TERCA', 'QUARTA', 'QUINTA', 'SEXTA', 'SAB']

    y = 460
    for idx, dia_chave in enumerate(dias_ordem):
        dt = (segunda + timedelta(days=idx)).strftime("%d/%m/%Y")
        d_dados = dias.get(dia_chave, {})

        d_cr = d_dados.get('corte', 0) + d_dados.get('religacao', 0)
        d_rv = d_dados.get('reaviso_maos', 0) + d_dados.get('reaviso_outros', 0)
        d_imp = d_dados.get('improdutivo', 0)
        d_ng = d_dados.get('negociacao', 0)

        row_str = f"{dt} | {d_cr:3d} | {d_rv:3d} | {d_imp:3d} | {d_ng:3d}"
        draw.text((40, y), row_str, fill=(226, 232, 240), font=font_main)
        y += 22

    draw.text((40, 765), "* Comprovante gerado para conferencia e acompanhamento com o encarregado.", fill=(148, 163, 184), font=font_main)

    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

# --- TECLADOS INTERATIVOS ---
def menu_principal_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=False, is_persistent=True, row_width=2)
    
    btn_religue = types.KeyboardButton('🔌 Religue +1')
    btn_maos = types.KeyboardButton('✋ Reaviso em Mãos')
    
    btn_improdutivo = types.KeyboardButton('🚫 Improdutivo +1')
    btn_comandos = types.KeyboardButton('📜 Comandos & Termos')
    
    btn_relatorio = types.KeyboardButton('📊 Relatório Semanal')
    btn_mensal = types.KeyboardButton('📅 Histórico Mensal')
    
    btn_registrar = types.KeyboardButton('⚡ Registrar Produção')
    btn_reset_semana = types.KeyboardButton('🔄 Resetar Semana')
    
    markup.add(btn_religue, btn_maos)
    markup.add(btn_improdutivo, btn_comandos)
    markup.add(btn_relatorio, btn_mensal)
    markup.add(btn_registrar, btn_reset_semana)
    return markup

def teclado_registro_rapido():
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("🔌 Religue +1", callback_data="add_religacao_1"),
        types.InlineKeyboardButton("✋ Reaviso Mãos +1", callback_data="convert_maos_1"),
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
        types.InlineKeyboardButton("⚠️ SIM, ZERAR E GERAR FOTO", callback_data="confirm_reset_semana"),
        types.InlineKeyboardButton("❌ CANCELAR", callback_data="cancel_reset_semana")
    )
    return markup

# --- CAPTURA CONTINUA (NEXT STEP) ---
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

# --- HANDLERS DAS AÇÕES RÁPIDAS ---
@bot.message_handler(func=lambda m: m.text == '🔌 Religue +1')
def acao_religue_rapido(message):
    if not esta_autorizado(message.from_user.id):
        return bot.reply_to(message, "⛔ *Acesso não autorizado.* Digite /start para solicitar liberação.", parse_mode="Markdown")

    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    processar_lancamento(str_id, 'religacao', 1)
    frase = random.choice(FRASES_MOTIVACIONAIS)
    bot.reply_to(message, f"🔌 *+1 RELIGAÇÃO REGISTRADA!*\n\n💬 _{frase}_", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == '✋ Reaviso em Mãos')
def acao_maos_rapido(message):
    if not esta_autorizado(message.from_user.id):
        return bot.reply_to(message, "⛔ *Acesso não autorizado.* Digite /start para solicitar liberação.", parse_mode="Markdown")

    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    converter_reaviso_para_maos(str_id, 1)
    frase = random.choice(FRASES_MOTIVACIONAIS)
    bot.reply_to(message, f"✋ *+1 REAVISO EM MÃOS REGISTRADO!*\n\n💬 _{frase}_", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == '🚫 Improdutivo +1')
def acao_improdutivo_rapido(message):
    if not esta_autorizado(message.from_user.id):
        return bot.reply_to(message, "⛔ *Acesso não autorizado.* Digite /start para solicitar liberação.", parse_mode="Markdown")

    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    processar_lancamento(str_id, 'improdutivo', 1)
    frase_imp = random.choice(FRASES_IMPRODUTIVO)
    bot.reply_to(message, f"🚫 *+1 IMPRODUTIVO COMPUTADO!*\n\n💬 _{frase_imp}_", parse_mode="Markdown")

# --- START & REGULAMENTO ---
@bot.message_handler(commands=['start'])
def start(message):
    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)

    if not esta_autorizado(str_id):
        bot.reply_to(
            message, 
            "⏳ *SOLICITAÇÃO DE ACESSO ENVIADA*\n\n"
            "Seu acesso está pendente de aprovação pelo administrador. "
            "Você receberá uma notificação assim que for liberado!", 
            parse_mode="Markdown"
        )
        
        if str(ADMIN_ID) != 'SEU_TELEGRAM_ID_AQUI':
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("✅ APROVAR", callback_data=f"adm_aprovar_{str_id}"),
                types.InlineKeyboardButton("❌ RECUSAR", callback_data=f"adm_recusar_{str_id}")
            )
            
            texto_admin = (
                f"🔔 *NOVA SOLICITAÇÃO DE ACESSO*\n\n"
                f"👤 *Nome:* {nome}\n"
                f"🆔 *ID:* `{str_id}`\n\n"
                f"Deseja liberar este usuário para usar o bot?"
            )
            try:
                bot.send_message(ADMIN_ID, texto_admin, parse_mode="Markdown", reply_markup=markup)
            except Exception as e:
                print(f"Erro ao notificar admin: {e}")
        return

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
    if not esta_autorizado(message.from_user.id):
        return bot.reply_to(message, "⛔ *Acesso não autorizado.* Digite /start para solicitar liberação.", parse_mode="Markdown")

    texto = (
        "📜 *REGULAMENTO INTERNO DE USO (USO RESTRITO & PESSOAL)*\n\n"
        "📌 *Propósito do Aplicativo:*\n"
        "• Sistema independente idealizado e programado por um **funcionário da operação**.\n"
        "• **Uso exclusivo e privado** restrito apenas a 4 funcionários autorizados para acompanhamento de metas.\n"
        "• Não possui integração com o sistema da concessionária. Todo dado é registrado pelo próprio operador para fins de auditoria pessoal.\n\n"
        "----------------------------------------\n"
        "📊 *RELATÓRIOS E CONSULTAS:*\n"
        "• `/relatorio` ou `/prod` - Resumo semanal com pontuação e tabela `IMP`\n"
        "• `/mensal` ou `/historico` - Histórico em tabelas mês a mês\n"
        "• `/resetar` - Zera a semana e **gera imagem em foto para o encarregado**\n"
        "• `/zerar_mensal` - Apaga todo o histórico permanentemente\n\n"
        "⚡ *LANÇAMENTOS RÁPIDOS POR TEXTO:*\n"
        "• `/corte [qnt]` - Lança cortes (Ex: `/corte 10`)\n"
        "• `/rel [qnt]` - Lança religações (Ex: `/rel 5`)\n"
        "• `/rea [qnt]` - Lança reavisos (Ex: `/rea 30`)\n"
        "• `/imp [qnt]` - Lança improdutivos (Ex: `/imp 2`)\n"
        "• `/maos [qnt]` - Converte reavisos para em mãos (Ex: `/maos 2`)\n\n"
        "⚙️ *AJUSTE DE DIA ESPECÍFICO:*\n"
        "• `/addcorte [dia] [qnt]` - Ex: `/addcorte seg 10`\n\n"
        f"----------------------------------------\n"
        f"{AVISO_INDEPENDENTE}"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == '⚡ Registrar Produção')
def menu_registro(message):
    if not esta_autorizado(message.from_user.id):
        return bot.reply_to(message, "⛔ *Acesso não autorizado.* Digite /start para solicitar liberação.", parse_mode="Markdown")

    bot.reply_to(message, "⚡ *PAINEL DE REGISTRO RÁPIDO*\nToque abaixo para registrar:", 
                 parse_mode="Markdown", reply_markup=teclado_registro_rapido())

@bot.message_handler(commands=['maos'])
def converter_maos_manual(message):
    if not esta_autorizado(message.from_user.id):
        return bot.reply_to(message, "⛔ *Acesso não autorizado.* Digite /start para solicitar liberação.", parse_mode="Markdown")

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
    if not esta_autorizado(message.from_user.id):
        return bot.reply_to(message, "⛔ *Acesso não autorizado.* Digite /start para solicitar liberação.", parse_mode="Markdown")

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
    if not esta_autorizado(message.from_user.id):
        return bot.reply_to(message, "⛔ *Acesso não autorizado.* Digite /start para solicitar liberação.", parse_mode="Markdown")

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
        
        if tipo_id in ['corte', 'religacao']:
            frase_extra = f"\n\n💬 _{random.choice(FRASES_MOTIVACIONAIS)}_"
        elif tipo_id == 'improdutivo':
            frase_extra = f"\n\n💬 _{random.choice(FRASES_IMPRODUTIVO)}_"
        else:
            frase_extra = ""

        bot.reply_to(message, f"✅ *+{quantidade} {tipo_nome}(s)* registrado(s)!{frase_extra}", parse_mode="Markdown")
    except:
        bot.reply_to(message, f"⚠️ Sintaxe: `{comando} 10`", parse_mode="Markdown")

# --- RELATÓRIOS E CONSULTAS ---
@bot.message_handler(func=lambda m: m.text == '📅 Histórico Mensal' or m.text in ['/mensal', '/meses', '/historico'])
def relatorio_mensal(message):
    if not esta_autorizado(message.from_user.id):
        return bot.reply_to(message, "⛔ *Acesso não autorizado.* Digite /start para solicitar liberação.", parse_mode="Markdown")

    str_id = str(message.from_user.id)
    nome = message.from_user.first_name
    inicializar_agente(str_id, nome)
    
    dados_meses = obter_historico_mensal(str_id)
    
    if not dados_meses:
        return bot.reply_to(message, "📂 *Nenhum histórico mensal registrado no momento.*", parse_mode="Markdown")
    
    texto = f"📅 *HISTÓRICO MENSAL DE PRODUÇÃO - CONSOLIDAÇÃO EM TABELAS*\n👤 Agente: *{nome.upper()}*\n\n"
    
    for row in dados_meses:
        mes_ano_str, cortes, religacoes, rv_maos, rv_outros, imp, neg = row
        ano, mes = mes_ano_str.split('-')
        nome_mes = MESES_NOME.get(int(mes), mes)
        
        mes_pag_num = int(mes) + 2
        ano_pag = int(ano)
        if mes_pag_num > 12:
            mes_pag_num -= 12
            ano_pag += 1
        nome_mes_pag = MESES_NOME.get(mes_pag_num, str(mes_pag_num))
        
        cr_total = cortes + religacoes
        rv_total = rv_maos + rv_outros
        pontos = (cr_total * PESO_SERVICO) + (rv_total * PESO_REAVISO)
        
        m_f1_pts, m_f2_pts, m_f3_pts = 250 * PESO_SERVICO, 300 * PESO_SERVICO, 350 * PESO_SERVICO
        
        if pontos >= m_f3_pts:
            valor_bonif = 300.00
            faixa_nome = "Faixa 3"
        elif pontos >= m_f2_pts:
            valor_bonif = 200.00
            faixa_nome = "Faixa 2"
        elif pontos >= m_f1_pts:
            valor_bonif = 150.00
            faixa_nome = "Faixa 1"
        else:
            valor_bonif = 0.00
            faixa_nome = "Sem Faixa"
            
        bonif_str = f"{valor_bonif:,.2f}".replace('.', ',')
        
        texto += (
            f"🗓️ *MÊS/ANO: {nome_mes} / {ano}*\n"
            f"```\n"
            f"+------------------------------------+-------+\n"
            f"| ITEM OPERACIONAL                   | QTD   |\n"
            f"+------------------------------------+-------+\n"
            f"| ✂️  Cortes Executados              | {cortes:5d} |\n"
            f"| 🔌 Religações Executadas           | {religacoes:5d} |\n"
            f"| ✋ Reavisos em Mãos                | {rv_maos:5d} |\n"
            f"| 📬 Reavisos Outros                 | {rv_outros:5d} |\n"
            f"| 🚫 Improdutivos (IMP)              | {imp:5d} |\n"
            f"| 🤝 Negociações                     | {neg:5d} |\n"
            f"+------------------------------------+-------+\n"
            f"| ⭐ PONTUAÇÃO TOTAL                 |{pontos:7.2f}|\n"
            f"| 🏆 FAIXA ATINGIDA                  | {faixa_nome:5s} |\n"
            f"| 💰 VALOR ESTIMADO                  |R${bonif_str:>6s}|\n"
            f"| 🗓️ MÊS DE PAGAMENTO                | {nome_mes_pag:5s} |\n"
            f"+------------------------------------+-------+\n"
            f"```\n"
        )
    
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == '📊 Relatório Semanal' or m.text in ['/relatorio', '/status', '/prod', '/dds'])
def relatorio(message):
    if not esta_autorizado(message.from_user.id):
        return bot.reply_to(message, "⛔ *Acesso não autorizado.* Digite /start para solicitar liberação.", parse_mode="Markdown")

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
    
    imp = totais.get('improdutivo', 0)
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
        falta_str = "Meta máxima atingida! 🎉"
        bonificacao = 300.00
    elif pontos >= m_f2_pts:
        faixa_str = "Faixa 2"
        falta_str = "Atingiu a Faixa 2 💪"
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
        f"👋 Olá *{nome.upper()}*, segue o resumo da sua produção na semana:\n\n"
        f"📅 *Período:* `{data_inicio}` a `{data_fim}`\n"
        f"• Cortes/Religações (CR): *{cr}*\n"
        f"• Reavisos Atendidos (RV): *{detalhe_reaviso}*\n"
        f"• Improdutivos (IMP): *{imp}*\n"
        f"• Negociações (NG): *{ng}*\n\n"
        f"⭐ *PONTUAÇÃO TOTAL:* *{pontos:.2f} pts*\n"
        f"🏆 *Faixa Atingida:* *{faixa_str}*\n"
        f"📊 *Situação:* _{falta_str}_\n"
        f"💰 *Bonificação Estimada:* *R$ {bonif_str}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚨 💳 *MÊS DE PAGAMENTO DESTA PRODUÇÃO* 💳 🚨\n"
        f"🔥 ➔ ➔ ➔  【 *{nome_mes_pagamento.upper()}* 】  ⬅️ ⬅️ ⬅️ 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    bot.send_message(message.chat.id, msg_bonif, parse_mode="Markdown")

    dias_ordem = ['SEG', 'TERCA', 'QUARTA', 'QUINTA', 'SEXTA', 'SAB']
    linhas_tabela = []
    
    for idx, dia_chave in enumerate(dias_ordem):
        dt = (segunda + timedelta(days=idx)).strftime("%d/%m/%Y")
        d_dados = dias.get(dia_chave, {})
        
        d_cr = d_dados.get('corte', 0) + d_dados.get('religacao', 0)
        d_rv = d_dados.get('reaviso_maos', 0) + d_dados.get('reaviso_outros', 0)
        d_imp = d_dados.get('improdutivo', 0)
        d_ng = d_dados.get('negociacao', 0)
        
        linhas_tabela.append(f"{dt} | {d_cr:2d} | {d_rv:2d} | {d_imp:3d} | {d_ng:2d}")

    tabela_formatada = "\n".join(linhas_tabela)

    msg_diario = (
        "📅 *Serviços executados por dia:*\n\n"
        "```\n"
        "Data       | CR | RV | IMP | NG\n"
        "---------------------------------\n"
        f"{tabela_formatada}\n"
        "```"
    )

    bot.send_message(message.chat.id, msg_diario, parse_mode="Markdown")

# --- COMANDOS DE RESET E ZERAR ---
@bot.message_handler(func=lambda m: m.text == '🔄 Resetar Semana' or m.text == '/resetar')
def solicitar_reset_semana(message):
    if not esta_autorizado(message.from_user.id):
        return bot.reply_to(message, "⛔ *Acesso não autorizado.* Digite /start para solicitar liberação.", parse_mode="Markdown")

    str_id = str(message.from_user.id)
    inicializar_agente(str_id, message.from_user.first_name)
    bot.reply_to(
        message, 
        "⚠️ *CONFIRMAÇÃO DE RESET SEMANAL*\n\n"
        "Deseja zerar a contagem ativa da semana atual?\n"
        "📸 *Uma foto comprovante será gerada automaticamente para enviar ao encarregado.*", 
        parse_mode="Markdown", 
        reply_markup=teclado_confirmacao_reset_semana()
    )

@bot.message_handler(commands=['zerar_mensal', 'resetarmensal'])
def solicitar_zerar_mensal(message):
    if not esta_autorizado(message.from_user.id):
        return bot.reply_to(message, "⛔ *Acesso não autorizado.* Digite /start para solicitar liberação.", parse_mode="Markdown")

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

# --- CALLBACKS DOS BOTÕES INLINE ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)

    if call.data.startswith('adm_aprovar_'):
        user_alvo = call.data.replace('adm_aprovar_', '')
        definir_autorizacao(user_alvo, True)
        
        bot.edit_message_text(f"✅ *USUÁRIO APROVADO!* (ID: `{user_alvo}`)", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Usuário liberado com sucesso!", show_alert=True)
        
        try:
            bot.send_message(user_alvo, "🎉 *SEU ACESSO FOI LIBERADO SEU BOT JÁ PODE SER USADO!*\n\nDigite /start para abrir o menu.", parse_mode="Markdown", reply_markup=menu_principal_keyboard())
        except Exception as e:
            print(f"Erro ao notificar usuário aprovado: {e}")
        return

    elif call.data.startswith('adm_recusar_'):
        user_alvo = call.data.replace('adm_recusar_', '')
        definir_autorizacao(user_alvo, False)
        
        bot.edit_message_text(f"❌ *SOLICITAÇÃO RECUSADA.* (ID: `{user_alvo}`)", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Solicitação recusada!", show_alert=True)
        
        try:
            bot.send_message(user_alvo, "⛔ *Sua solicitação de acesso foi recusada pelo administrador.*", parse_mode="Markdown")
        except Exception as e:
            print(f"Erro ao notificar usuário recusado: {e}")
        return

    if not esta_autorizado(user_id):
        bot.answer_callback_query(call.id, "⛔ Acesso não autorizado. Digite /start para solicitar.", show_alert=True)
        return

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

    elif call.data == 'add_religacao_1':
        processar_lancamento(user_id, 'religacao', 1)
        frase = random.choice(FRASES_MOTIVACIONAIS)
        bot.answer_callback_query(call.id, f"🔌 +1 RELIGUE REGISTRADO!\n\n{frase}", show_alert=True)

    elif call.data == 'convert_maos_1':
        converter_reaviso_para_maos(user_id, 1)
        frase = random.choice(FRASES_MOTIVACIONAIS)
        bot.answer_callback_query(call.id, f"✋ +1 REAVISO EM MÃOS REGISTRADO!\n\n{frase}", show_alert=True)

    elif call.data == 'add_improdutivo_1':
        processar_lancamento(user_id, 'improdutivo', 1)
        frase_imp = random.choice(FRASES_IMPRODUTIVO)
        bot.answer_callback_query(call.id, f"🚫 +1 IMPRODUTIVO COMPUTADO!\n\n{frase_imp}", show_alert=True)

    elif call.data == 'confirm_reset_semana':
        totais, dias = obter_resumo_semana(user_id)
        
        hoje = agora_sp()
        segunda = hoje - timedelta(days=hoje.weekday())
        sabado = segunda + timedelta(days=5)
        data_inicio = segunda.strftime("%d/%m")
        data_fim = sabado.strftime("%d/%m")
        
        mes_pagamento_num = hoje.month + 2
        if mes_pagamento_num > 12: mes_pagamento_num -= 12
        nome_mes_pagamento = MESES_NOME[mes_pagamento_num]

        cr = totais.get('corte', 0) + totais.get('religacao', 0)
        rv_total = totais.get('reaviso_maos', 0) + totais.get('reaviso_outros', 0)
        pontos = (cr * PESO_SERVICO) + (rv_total * PESO_REAVISO)

        if pontos >= (350 * PESO_SERVICO): faixa_str, bonificacao = "Faixa 3", 300.00
        elif pontos >= (300 * PESO_SERVICO): faixa_str, bonificacao = "Faixa 2", 200.00
        elif pontos >= (250 * PESO_SERVICO): faixa_str, bonificacao = "Faixa 1", 150.00
        else: faixa_str, bonificacao = "Sem Faixa", 0.00
        
        bonif_str = f"{bonificacao:,.2f}".replace('.', ',')

        # Gera foto para o encarregado
        foto_stream = criar_imagem_relatorio_semanal(
            call.from_user.first_name, data_inicio, data_fim,
            totais, dias, faixa_str, bonif_str, pontos, nome_mes_pagamento
        )

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE lancamentos SET semana_ativa = FALSE WHERE user_id = %s AND semana_ativa = TRUE;", (user_id,))
        conn.commit()
        cur.close()
        conn.close()

        bot.edit_message_text("🔄 *CICLO SEMANAL ZERADO COM SUCESSO!*", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.send_photo(
            call.message.chat.id, 
            photo=foto_stream, 
            caption="📸 *COMPROVANTE DE PRODUÇÃO SEMANAL GERADO!*\n\n_Envie esta imagem para seu encarregado para conferência de valores e metas._",
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id, "Semana zerada e comprovante em imagem gerado!", show_alert=True)

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
