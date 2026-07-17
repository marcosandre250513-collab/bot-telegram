import telebot
from datetime import datetime
import calendar

# Substitua pelo Token do seu bot
TOKEN = '8820258308:AAHxPYzXUr81ohEZx8cfN7qmADhzL8OYnW8'
bot = telebot.TeleBot(TOKEN)

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
            'total_mes': 0,
            'producao_diaria': {
                'Segunda-feira': 0, 'Terça-feira': 0, 'Quarta-feira': 0,
                'Quinta-feira': 0, 'Sexta-feira': 0, 'Sábado': 0, 'Domingo': 0
            },
            'historico': []
        }

@bot.message_handler(commands=['start', 'help'])
def start(message):
    user_id = message.from_user.id
    nome = message.from_user.first_name
    inicializar_agente(user_id, nome)
    
    texto = (
        f"🏢 *SISTEMA DE GESTÃO DE PRODUTIVIDADE - EQUATORIAL*\n"
        f"Bem-vindo, Agente Comercial {nome}.\n\n"
        "Este sistema registra sua produção diária e monitora o atingimento de metas com transparência corporativa.\n\n"
        "📌 *COMANDOS OPERACIONAIS:*\n"
        "• `/lancar [quantidade]` - Ex: `/lancar 50`\n"
        "• `/relatorio` - Exibe o painel de metas e tabela semanal\n"
        "• `/resetar` - Inicia um novo ciclo de faturamento"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['lancar'])
def lancar(message):
    user_id = message.from_user.id
    nome = message.from_user.first_name
    inicializar_agente(user_id, nome)
    
    try:
        # Extrai a quantidade lançada
        quantidade = int(message.text.split()[1])
        
        # Obtém dados do momento exato do lançamento
        agora = datetime.now()
        dia_nome = DIAS_SEMANA[agora.weekday()]
        data_hora = agora.strftime("%d/%m/%Y às %H:%M")
        
        # Registra os dados no perfil do Agente
        usuarios[user_id]['producao_diaria'][dia_nome] += quantidade
        usuarios[user_id]['total_mes'] += quantidade
        
        # Salva log de auditoria mantendo os últimos 5 lançamentos
        log_entry = f"[{data_hora}] {dia_nome}: +{quantidade} serv."
        usuarios[user_id]['historico'].append(log_entry)
        if len(usuarios[user_id]['historico']) > 5:
            usuarios[user_id]['historico'].pop(0)
            
        resposta = (
            f"✅ *REGISTRO CONFIRMADO*\n"
            f"Agente: {nome}\n"
            f"Lançado em: {dia_nome}\n"
            f"Volume: {quantidade} serviços.\n\n"
            f"Para visualizar o impacto nas suas metas, digite `/relatorio`."
        )
        bot.reply_to(message, resposta, parse_mode="Markdown")
        
    except:
        bot.reply_to(message, "⚠️ *FALHA NO REGISTRO*\nPadrão exigido: `/lancar [quantidade]`. Exemplo: `/lancar 55`", parse_mode="Markdown")

@bot.message_handler(commands=['relatorio', 'status'])
def relatorio(message):
    user_id = message.from_user.id
    nome = message.from_user.first_name
    inicializar_agente(user_id, nome)
    
    dados = usuarios[user_id]
    total = dados['total_mes']
    dias = dados['producao_diaria']
    
    # Metas Oficiais [Opção A]
    m_f1, m_f2, m_f3 = 250, 300, 350
    
    # Cálculo de Dificuldade Diária
    dias_rest = obter_dias_restantes()
    media_f1 = max(0, m_f1 - total) / dias_rest if total < m_f1 else 0
    media_f2 = max(0, m_f2 - total) / dias_rest if total < m_f2 else 0
    media_f3 = max(0, m_f3 - total) / dias_rest if total < m_f3 else 0
    
    # Definição de Status
    if total >= m_f3: status_msg = "🟢 FAIXA 3 CONCLUÍDA"
    elif total >= m_f2: status_msg = "🟡 FAIXA 2 CONCLUÍDA"
    elif total >= m_f1: status_msg = "🟠 FAIXA 1 CONCLUÍDA"
    else: status_msg = "🔴 EM EXECUÇÃO (Abaixo da F1)"
    
    # Montagem do Relatório Visual
    tabela_semanal = (
        f"Segunda-feira : {dias['Segunda-feira']}\n"
        f"Terça-feira   : {dias['Terça-feira']}\n"
        f"Quarta-feira  : {dias['Quarta-feira']}\n"
        f"Quinta-feira  : {dias['Quinta-feira']}\n"
        f"Sexta-feira   : {dias['Sexta-feira']}\n"
        f"Sábado        : {dias['Sábado']}"
    )
    
    historico_texto = "\n".join(dados['historico']) if dados['historico'] else "Nenhum registro no ciclo atual."
    
    relatorio_final = (
        f"📊 *PAINEL DE PERFORMANCE CORPORATIVO*\n"
        f"👤 *Agente:* {nome} | *Status:* {status_msg}\n"
        f"═════════════════════════\n\n"
        f"📈 *VOLUME ACUMULADO:* {total} serviços\n\n"
        f"📅 *DISTRIBUIÇÃO DA SEMANA:*\n"
        f"`{tabela_semanal}`\n\n"
        f"🎯 *PROJEÇÃO DE METAS (Restam {dias_rest} dias):*\n"
        f"• *Faixa 1 ({m_f1}):* Faltam {max(0, m_f1 - total)} ➔ Média: {media_f1:.1f}/dia\n"
        f"• *Faixa 2 ({m_f2}):* Faltam {max(0, m_f2 - total)} ➔ Média: {media_f2:.1f}/dia\n"
        f"• *Faixa 3 ({m_f3}):* Faltam {max(0, m_f3 - total)} ➔ Média: {media_f3:.1f}/dia\n\n"
        f"🔎 *ÚLTIMOS REGISTROS (Auditoria):*\n"
        f"`{historico_texto}`"
    )
    
    bot.reply_to(message, relatorio_final, parse_mode="Markdown")

@bot.message_handler(commands=['resetar'])
def resetar(message):
    user_id = message.from_user.id
    nome = message.from_user.first_name
    
    if user_id in usuarios:
        usuarios[user_id]['total_mes'] = 0
        for dia in DIAS_SEMANA.values():
            usuarios[user_id]['producao_diaria'][dia] = 0
        usuarios[user_id]['historico'] = []
        
        bot.reply_to(message, f"🔄 *CICLO REINICIADO*\nAgente {nome}, seus dados de faturamento foram zerados para o novo período.", parse_mode="Markdown")

print("Sistema Corporativo Online. Aguardando comandos no Telegram...")
bot.infinity_polling()

