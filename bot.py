import telebot
from datetime import datetime
import math
from flask import Flask
from threading import Thread

# --- CONFIGURAÇÃO DO SERVIDOR (Evita o erro CRASHED no Railway) ---
app = Flask('')

@app.route('/')
def home():
    return "Servidor do App do Técnico está online!"

def run():
    app.run(host='0.0.0.0', port=8080)

# Inicia o servidor em segundo plano
t = Thread(target=run)
t.start()
# ------------------------------------------------------------------

# Substitua pelo Token do seu bot
TOKEN = '8820258308:AAHxPYzXUr81ohEZx8cfN7qmADhzL8OYnW8'
bot = telebot.TeleBot(TOKEN)

# Pesos dos serviços (usados apenas internamente para calcular a equivalência das metas)
PESO_SERVICO = 13.64 # Corte ou Religação
PESO_REAVISO = 7.80

# Banco de dados temporário na memória
usuarios = {}

DIAS_SEMANA = {
    0: 'Segunda-feira', 1: 'Terça-feira', 2: 'Quarta-feira',
    3: 'Quinta-feira', 4: 'Sexta-feira', 5: 'Sábado', 6: 'Domingo'
}

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
        f"🏢 *CONTROLE DE CAMPO*\n"
        f"Fala, {nome}! Bem-vindo ao seu registro operacional.\n\n"
        "Este sistema registra sua produção, separando Cortes, Religações e Reavisos, e calcula as metas de forma rápida.\n\n"
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
        
        usuarios[user_id]['producao_diaria'][dia_nome][tipo_id] += quantidade
        usuarios[user_id]['totais'][tipo_id] += quantidade
        
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
    
    # Cálculo de pontos base para saber o avanço das metas sem usar R$
    pontos_total = (t['corte'] + t['religacao']) * PESO_SERVICO + (t['reaviso'] * PESO_REAVISO)
    total_servicos_brutos = t['corte'] + t['religacao'] + t['reaviso']
    
    m_f1, m_f2, m_f3 = 250, 300, 350
    
    def calcular_meta(meta_qnt):
        meta_pontos = meta_qnt * PESO_SERVICO
        falta_pontos = meta_pontos - pontos_total
        
        if falta_pontos <= 0:
            return "✅ *CONCLUÍDA*"
            
        faltam_servicos = math.ceil(falta_pontos / PESO_SERVICO)
        faltam_reavisos = math.ceil(falta_pontos / PESO_REAVISO)
        
        return f"Faltam {faltam_servicos} serv. OU {faltam_reavisos} reavisos"

    if pontos_total >= (m_f3 * PESO_SERVICO): status_msg = "🟢 FAIXA 3 CONCLUÍDA"
    elif pontos_total >= (m_f2 * PESO_SERVICO): status_msg = "🟡 FAIXA 2 CONCLUÍDA"
    elif pontos_total >= (m_f1 * PESO_SERVICO): status_msg = "🟠 FAIXA 1 CONCLUÍDA"
    else: status_msg = "🔴 NA BATALHA"
    
    tabela_linhas = []
    for dia in DIAS_SEMANA.values():
        d = dias[dia]
        tabela_linhas.append(f"{dia[:3]} ➔ C: {d['corte']} | R: {d['religacao']} | Rv: {d['reaviso']}")
    tabela_semanal = "\n".join(tabela_linhas)
    
    historico_texto = "\n".join(dados['historico']) if dados['historico'] else "Nenhum registro recente."
    
    relatorio_final = (
        f"📊 *DIÁRIO DE PRODUÇÃO*\n"
        f"👤 *Técnico:* {nome} | *Status:* {status_msg}\n"
        f"═════════════════════════\n\n"
        f"📋 *Total na Rua:* {total_servicos_brutos} (C: {t['corte']} | R: {t['religacao']} | Rv: {t['reaviso']})\n\n"
        f"📅 *PRODUÇÃO DA SEMANA:*\n"
        f"`{tabela_semanal}`\n\n"
        f"🎯 *PROJEÇÃO DE METAS:*\n"
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
        
        bot.reply_to(message, f"🔄 *CICLO REINICIADO*\n{nome}, tudo zerado para começar a nova contagem.", parse_mode="Markdown")

print("Sistema Online. Aguardando comandos no Telegram...")
bot.infinity_polling()
