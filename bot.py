import telebot
from datetime import datetime
import calendar
import math

# Substitua pelo Token do seu bot
TOKEN = '8820258308:AAHxPYzXUr81ohEZx8cfN7qmADhzL8OYnW8'
bot = telebot.TeleBot(TOKEN)

# Valores financeiros da sua planilha
VALOR_SERVICO = 13.64 # Corte ou Religação
VALOR_REAVISO = 7.80

# Banco de dados temporário na memória
usuarios = {}

DIAS_SEMANA = {
    0: 'Segunda-feira', 1: 'Terça-feira', 2: 'Quarta-feira',
    3: 'Quinta-feira', 4: 'Sexta-feira', 5: 'Sábado', 6: 'Domingo'
}

def obter_dias_restantes():
    hoje = datetime.now()
    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
    dias_restantes = ultimo_dia - hoje.day
    return max(1, dias_restantes)

def inicializar_agente(user_id, nome):
    if user_id not in usuarios:
        usuarios[user_id] = {
            'nome': nome,
            'totais': {'corte': 0, 'religacao': 0, 'reaviso': 0},
            'producao_diaria': {
                dia: {'corte': 0, 'religacao': 0, 'reaviso': 0} for dia in DIAS_SEMANA.values()
            },
            'historico': []
        }

@bot.message_handler(commands=['start', 'help'])
def start(message):
    user_id = message.from_user.id
    nome = message.from_user.first_name
    inicializar_agente(user_id, nome)
    
    texto = (
        f"🏢 *MEU SISTEMA DE GESTÃO DE PRODUTIVIDADE*\n"
        f"Bem-vindo, Agente Comercial {nome}.\n\n"
        "Este sistema registra sua produção, separando Cortes, Religações e Reavisos, e calcula as metas com base no valor de cada serviço.\n\n"
        "📌 *COMANDOS RÁPIDOS:*\n"
        "• `/corte [qnt]` - Ex: `/corte 10`\n"
        "• `/rel [qnt]` - Ex: `/rel 5` (Religação)\n"
        "• `/rea [qnt]` - Ex: `/rea 15` (Reaviso)\n\n"
        "• `/relatorio` - Painel de metas e tabela semanal\n"
        "• `/resetar` - Inicia um novo ciclo de faturamento"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['corte', 'rel', 'rea', 'religacao', 'reaviso'])
def registrar_servico(message):
    user_id = message.from_user.id
    nome = message.from_user.first_name
    inicializar_agente(user_id, nome)
    
    comando = message.text.split()[0].lower()
    
    # Identifica o tipo de serviço pelo comando digitado
    if comando == '/corte':
        tipo_id = 'corte'
        tipo_nome = 'Corte'
    elif comando in ['/rel', '/religacao']:
        tipo_id = 'religacao'
        tipo_nome = 'Religação'
    elif comando in ['/rea', '/reaviso']:
        tipo_id = 'reaviso'
        tipo_nome = 'Reaviso'
    else:
        return

    try:
        quantidade = int(message.text.split()[1])
        
        agora = datetime.now()
        dia_nome = DIAS_SEMANA[agora.weekday()]
        data_hora = agora.strftime("%d/%m %H:%M")
        
        # Atualiza o banco de dados
        usuarios[user_id]['producao_diaria'][dia_nome][tipo_id] += quantidade
        usuarios[user_id]['totais'][tipo_id] += quantidade
        
        # Salva histórico
        log_entry = f"[{data_hora}] {dia_nome[:3]}: +{quantidade} {tipo_nome}"
        usuarios[user_id]['historico'].append(log_entry)
        if len(usuarios[user_id]['historico']) > 5:
            usuarios[user_id]['historico'].pop(0)
            
        resposta = (
            f"✅ *REGISTRO CONFIRMADO*\n"
            f"Adicionado: {quantidade} {tipo_nome}(s)\n"
            f"Veja seu avanço com `/relatorio`"
        )
        bot.reply_to(message, resposta, parse_mode="Markdown")
        
    except:
        bot.reply_to(message, f"⚠️ *FALHA NO REGISTRO*\nUse o formato correto. Exemplo: `{comando} 5`", parse_mode="Markdown")

@bot.message_handler(commands=['relatorio', 'status'])
def relatorio(message):
    user_id = message.from_user.id
    nome = message.from_user.first_name
    inicializar_agente(user_id, nome)
    
    dados = usuarios[user_id]
    t = dados['totais']
    dias = dados['producao_diaria']
    
    # Cálculo Financeiro
    valor_total = (t['corte'] + t['religacao']) * VALOR_SERVICO + (t['reaviso'] * VALOR_REAVISO)
    total_servicos_brutos = t['corte'] + t['religacao'] + t['reaviso']
    
    # Metas Oficiais de Volume Equivalente
    m_f1, m_f2, m_f3 = 250, 300, 350
    dias_rest = obter_dias_restantes()
    
    def calcular_meta(meta_qnt):
        meta_rs = meta_qnt * VALOR_SERVICO # Transforma a meta em valor Financeiro (Ex: 250 * 13.64)
        falta_rs = meta_rs - valor_total
        
        if falta_rs <= 0:
            return "✅ *BATI A META*"
            
        faltam_servicos = math.ceil(falta_rs / VALOR_SERVICO)
        faltam_reavisos = math.ceil(falta_rs / VALOR_REAVISO)
        media_dia = faltam_servicos / dias_rest
        
        return f"Faltam {faltam_servicos} serv. OU {faltam_reavisos} reavisos (Média: {media_dia:.1f}/dia)"

    # Definição de Status baseado no Financeiro
    if valor_total >= (m_f3 * VALOR_SERVICO): status_msg = "🟢 FAIXA 3 CONCLUÍDA"
    elif valor_total >= (m_f2 * VALOR_SERVICO): status_msg = "🟡 FAIXA 2 CONCLUÍDA"
    elif valor_total >= (m_f1 * VALOR_SERVICO): status_msg = "🟠 FAIXA 1 CONCLUÍDA"
    else: status_msg = "🔴 BUSCANDO A META"
    
    # Montagem da Tabela Semanal (C = Corte, R = Religação, Rv = Reaviso)
    tabela_linhas = []
    for dia in DIAS_SEMANA.values():
        d = dias[dia]
        tabela_linhas.append(f"{dia[:3]} ➔ C: {d['corte']} | R: {d['religacao']} | Rv: {d['reaviso']}")
    tabela_semanal = "\n".join(tabela_linhas)
    
    historico_texto = "\n".join(dados['historico']) if dados['historico'] else "Nenhum registro recente."
    
    relatorio_final = (
        f"📊 *MEU SISTEMA DE CONTROLE*\n"
        f"👤 *Agente:* {nome} | *Status:* {status_msg}\n"
        f"═════════════════════════\n\n"
        f"💰 *VALOR ACUMULADO:* R$ {valor_total:.2f}\n"
        f"📋 *Total de Ordens:* {total_servicos_brutos} (C: {t['corte']} | R: {t['religacao']} | Rv: {t['reaviso']})\n\n"
        f"📅 *PRODUÇÃO DA SEMANA:*\n"
        f"`{tabela_semanal}`\n\n"
        f"🎯 *PROJEÇÃO DE METAS 
        f"• *Faixa 1 ({m_f1}):* {calcular_meta(m_f1)}\n"
        f"• *Faixa 2 ({m_f2}):* {calcular_meta(m_f2)}\n"
        f"• *Faixa 3 ({m_f3}):* {calcular_meta(m_f3)}\n\n"
        f"🔎 *ÚLTIMOS REGISTROS:*\n"
        f"`{historico_texto}`"
    )
    
    bot.reply_to(message, relatorio_final, parse_mode="Markdown")

@bot.message_handler(commands=['resetar'])
def resetar(message):
    user_id = message.from_user.id
    nome = message.from_user.first_name
    
    if user_id in usuarios:
        usuarios[user_id]['totais'] = {'corte': 0, 'religacao': 0, 'reaviso': 0}
        for dia in DIAS_SEMANA.values():
            usuarios[user_id]['producao_diaria'][dia] = {'corte': 0, 'religacao': 0, 'reaviso': 0}
        usuarios[user_id]['historico'] = []
        
        bot.reply_to(message, f"🔄 *SEMANA REINICIADA*\nAgente {nome}, seus dados de faturamento foram zerados para o novo período.", parse_mode="Markdown")

print("Sistema Corporativo Online. Aguardando comandos no Telegram...")
bot.infinity_polling()
