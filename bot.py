import telebot
from datetime import datetime
import math
from flask import Flask
from threading import Thread

# --- CONFIGURAÇÃO DO SERVIDOR ---
app = Flask('')

@app.route('/')
def home():
    return "Servidor do App do Técnico está online!"

def run():
    app.run(host='0.0.0.0', port=8080)

t = Thread(target=run)
t.start()
# --------------------------------

# Substitua pelo Token do seu bot
TOKEN = '8820258308:AAHxPYzXUr81ohEZx8cfN7qmADhzL8OYnW8'
bot = telebot.TeleBot(TOKEN)

# Pesos dos serviços
PESO_SERVICO = 13.64 # Corte ou Religação
PESO_REAVISO = 7.80

# Banco de dados temporário na memória
usuarios = {}

DIAS_SEMANA = {
    0: 'SEG', 1: 'TERCA', 2: 'QUARTA',
    3: 'QUINTA', 4: 'SEXTA', 5: 'SAB', 6: 'FOLGA'
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
        f"🏢 *MEU CONTROLE DE PRODUÇÃO*\n"
        f"Fala, {nome}! .\n\n"
        "📌 *COMANDOS DE REGISTRO:*\n"
        "• `/corte [qnt]` - Ex: `/corte 10`\n"
        "• `/rel [qnt]` - Ex: `/rel 5` (Religação)\n"
        "• `/rea [qnt]` - Ex: `/rea 15` (Reaviso)\n\n"
        "📊 *CONSULTAS E SIMULAÇÕES:*\n"
        "• `/relatorio` - Painel de metas e tabela semanal\n"
        "• `/total [servicos] [reavisos]` - Simula sua meta (Ex: `/total 200 50`)\n"
        "• `/resetar` - Inicia um novo ciclo"
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

# NOVO COMANDO: SIMULAÇÃO
@bot.message_handler(commands=['total', 'simular'])
def simular_meta(message):
    try:
        partes = message.text.split()
        if len(partes) != 3:
            bot.reply_to(message, "⚠️ *FORMATO DA SIMULAÇÃO*\nUse: `/total [Cortes+Religações] [Reavisos]`\nExemplo: `/total 200 50`\n_(Isso simula 200 serviços e 50 reavisos)_", parse_mode="Markdown")
            return
        
        sim_servicos = int(partes[1])
        sim_reavisos = int(partes[2])
        
        pontos_simulados = (sim_servicos * PESO_SERVICO) + (sim_reavisos * PESO_REAVISO)
        m_f1, m_f2, m_f3 = 250, 300, 350
        
        def calcular_meta_simulada(meta_qnt):
            meta_pontos = meta_qnt * PESO_SERVICO
            falta_pontos = meta_pontos - pontos_simulados
            
            if falta_pontos <= 0:
                return "✅ *META BATIDA 📈*"
                
            faltam_servicos = math.ceil(falta_pontos / PESO_SERVICO)
            faltam_reavisos = math.ceil(falta_pontos / PESO_REAVISO)
            return f"Faltam {faltam_servicos} serv. OU {faltam_reavisos} reavisos"

        if pontos_simulados >= (m_f3 * PESO_SERVICO): status_msg = "🟢 FAIXA 3"
        elif pontos_simulados >= (m_f2 * PESO_SERVICO): status_msg = "🟡 FAIXA 2"
        elif pontos_simulados >= (m_f1 * PESO_SERVICO): status_msg = "🟠 FAIXA 1"
        else: status_msg = "🔴 NÃO BATI A META AINDA 😢"
        
        resposta = (
            f"🔮 *MEU RESULTADO*\n"
            f"Serviços (C/R): {sim_servicos} | Reavisos: {sim_reavisos}\n"
            f"Status Simulado: {status_msg}\n"
            f"═════════════════════════\n\n"
            f"🎯 *MINHA VISÃO DA META:*\n"
            f"• *FAIXA 1 💲(250):* {calcular_meta_simulada(m_f1)}\n"
            f"• *FAIXA 2 💲(300):* {calcular_meta_simulada(m_f2)}\n"
            f"• *FAIXA 3 💲(350):* {calcular_meta_simulada(m_f3)}\n\n"
            f"_(Simulação total da meta, não altera a planilha/relatorio)_")
        bot.reply_to(message, resposta, parse_mode="Markdown")
        
    except ValueError:
        bot.reply_to(message, "⚠️ Digite apenas números. Exemplo: `/total 200 50`", parse_mode="Markdown")

@bot.message_handler(commands=['relatorio', 'status'])
def relatorio(message):
    user_id = message.from_user.id
    nome = message.from_user.first_name
    inicializar_agente(user_id, nome)
    
    dados = usuarios[user_id]
    t = dados['totais']
    dias = dados['producao_diaria']
    
    pontos_total = (t['corte'] + t['religacao']) * PESO_SERVICO + (t['reaviso'] * PESO_REAVISO)
    total_servicos_brutos = t['corte'] + t['religacao'] + t['reaviso']
    
    m_f1, m_f2, m_f3 = 250, 300, 350
    
    def calcular_meta(meta_qnt):
        meta_pontos = meta_qnt * PESO_SERVICO
        falta_pontos = meta_pontos - pontos_total
        
        if falta_pontos <= 0:
            return "✅ *BATI A META*"
            
        faltam_servicos = math.ceil(falta_pontos / PESO_SERVICO)
        faltam_reavisos = math.ceil(falta_pontos / PESO_REAVISO)
        
        return f"Faltam {faltam_servicos} serv. OU {faltam_reavisos} reavisos"

    if pontos_total >= (m_f3 * PESO_SERVICO): status_msg = "🥉 FAIXA 3 CONCLUÍDA"
    elif pontos_total >= (m_f2 * PESO_SERVICO): status_msg = "🥈 FAIXA 2 CONCLUÍDA"
    elif pontos_total >= (m_f1 * PESO_SERVICO): status_msg = "🥇 FAIXA 1 CONCLUÍDA"
    else: status_msg = "🔴 NA BATALHA"
    
    tabela_linhas = []
    for dia in DIAS_SEMANA.values():
        d = dias[dia]
        tabela_linhas.append(f"{dia[:3]} ➔ C: {d['corte']} | R: {d['religacao']} | Rv: {d['reaviso']}")
    tabela_semanal = "\n".join(tabela_linhas)
    
    historico_texto = "\n".join(dados['historico']) if dados['historico'] else "Nenhum registro recente."
    
    relatorio_final = (
        f"📊 *DIÁRIO  DA MINHA PRODUÇÃO*\n"
        f"👤 *Técnico:* {nome} | *Status:* {status_msg}\n"
        f"═════════════════════════\n\n"
        f"📋 *Total :* {total_servicos_brutos} (C: {t['corte']} | R: {t['religacao']} | Rv: {t['reaviso']})\n\n"
        f"📅 *PRODUÇÃO DA SEMANA:*\n"
        f"`{tabela_semanal}`\n\n"
        f"🎯 *MINHA PROJEÇÃO PARA CHEHAR NO OBJETIVO:*\n"
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
