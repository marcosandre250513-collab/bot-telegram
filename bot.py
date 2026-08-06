import hashlib
import os
import socket
import uuid
from datetime import datetime, timezone
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Definindo os estados da conversa
MATRICULA, MEDIDOR, LOCALIZACAO, PERGUNTAS, FOTO = range(5)

# Lista de perguntas do checklist APR do seu modelo
QUESTIONS = [
    "1. Eu possuo todos os equipamentos de segurança necessários e ferramentas em condições para realização da atividade com segurança?",
    "2. Meu veículo está estacionado em condições seguras?",
    "3. O local de trabalho está desobstruído e seguro sem risco de queda de mesmo nível ou objetos?",
    "4. O local está livre de insetos ou animais agressivos?",
    "5. Foi verificado com a chave teste que a caixa do medidor não possui fuga de tensão elétrica?",
    "6. É possível executar a atividade com segurança?"
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    context.user_data['inicio'] = datetime.now()
    context.user_data['id_apr'] = uuid.uuid4().hex[:8].upper()
    context.user_data['answers'] = []
    
    await update.message.reply_text("Iniciando emissão da APR.\nPor favor, informe a sua MATRÍCULA:")
    return MATRICULA

async def get_matricula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['matricula'] = update.message.text
    await update.message.reply_text("Informe o NÚMERO DO MEDIDOR:")
    return MEDIDOR

async def get_medidor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['medidor'] = update.message.text
    await update.message.reply_text(
        "Por favor, envie sua LOCALIZAÇÃO atual no Telegram (use o ícone de clipe > Localização):"
    )
    return LOCALIZACAO

async def get_localizacao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    loc = update.message.location
    context.user_data['lat'] = loc.latitude
    context.user_data['lon'] = loc.longitude
    
    context.user_data['current_question'] = 0
    reply_keyboard = [['SIM', 'NÃO']]
    
    await update.message.reply_text(
        QUESTIONS[0],
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return PERGUNTAS

async def get_perguntas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ans = update.message.text
    context.user_data['answers'].append(ans)
    
    q_index = context.user_data['current_question'] + 1
    context.user_data['current_question'] = q_index
    
    if q_index < len(QUESTIONS):
        reply_keyboard = [['SIM', 'NÃO']]
        await update.message.reply_text(
            QUESTIONS[q_index],
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return PERGUNTAS
    else:
        await update.message.reply_text(
            "Checklist concluído! Por favor, tire uma SELFIE/FOTO do local para finalizar.",
            reply_markup=ReplyKeyboardRemove()
        )
        return FOTO

async def get_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"foto_{update.effective_user.id}.jpg"
    await photo_file.download_to_drive(photo_path)
    
    context.user_data['photo_path'] = photo_path
    context.user_data['termino'] = datetime.now()
    
    await update.message.reply_text("Gerando relatório PDF...")
    
    pdf_path = generate_pdf(update, context)
    
    with open(pdf_path, 'rb') as pdf:
        await update.message.reply_document(
            document=pdf,
            filename=f"APR_{context.user_data['id_apr']}.pdf",
            caption="Relatório APR gerado com sucesso!"
        )
        
    if os.path.exists(photo_path):
        os.remove(photo_path)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
        
    return ConversationHandler.END

def generate_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    pdf_filename = f"APR_Report_{context.user_data['id_apr']}.pdf"
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, leading=18, textColor=colors.HexColor('#1A365D'))
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=12, leading=14, textColor=colors.HexColor('#2B6CB0'))
    normal_style = styles['Normal']
    
    # Cabeçalho
    story.append(Paragraph("<b>SMART APR FORENSIC REPORT</b>", title_style))
    story.append(Spacer(1, 10))
    
    # Cálculo de hashes para integridade
    with open(context.user_data['photo_path'], 'rb') as f:
        hash_foto = hashlib.sha256(f.read()).hexdigest()
        
    raw_data = f"{context.user_data['id_apr']}{context.user_data['matricula']}{context.user_data['lat']}{context.user_data['lon']}"
    hash_apr = hashlib.sha256(raw_data.encode()).hexdigest()
    
    # Tabela de Identificação
    info_data = [
        ["ID APR:", context.user_data['id_apr'], "LATITUDE:", str(context.user_data['lat'])],
        ["MATRÍCULA:", context.user_data['matricula'], "LONGITUDE:", str(context.user_data['lon'])],
        ["MEDIDOR:", context.user_data['medidor'], "TELEGRAM ID:", str(update.effective_user.id)],
        ["INÍCIO:", context.user_data['inicio'].strftime('%d/%m/%Y %H:%M'), "HOSTNAME:", socket.gethostname()],
        ["TÉRMINO:", context.user_data['termino'].strftime('%d/%m/%Y %H:%M'), "UTC:", datetime.now(timezone.utc).isoformat()]
    ]
    
    t_info = Table(info_data, colWidths=[100, 150, 100, 180])
    t_info.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#2D3748')),
        ('TEXTCOLOR', (2,0), (2,-1), colors.HexColor('#2D3748')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 15))
    
    # Checklist
    story.append(Paragraph("<b>CHECKLIST APR</b>", subtitle_style))
    story.append(Spacer(1, 5))
    
    for q, a in zip(QUESTIONS, context.user_data['answers']):
        story.append(Paragraph(f"<b>{q}</b>", normal_style))
        story.append(Paragraph(f"Resposta: <b>{a}</b>", normal_style))
        story.append(Spacer(1, 4))
        
    story.append(Spacer(1, 10))
    
    # Integridade Forense
    story.append(Paragraph("<b>INTEGRIDADE FORENSE</b>", subtitle_style))
    story.append(Paragraph(f"<b>HASH SHA256 APR:</b><br/>{hash_apr}", normal_style))
    story.append(Paragraph(f"<b>HASH FOTO FINAL:</b><br/>{hash_foto}", normal_style))
    story.append(Spacer(1, 15))
    
    # Anexo Foto
    if os.path.exists(context.user_data['photo_path']):
        story.append(Paragraph("<b>COMPROVANTE / FOTO REGISTRADA</b>", subtitle_style))
        story.append(Spacer(1, 5))
        img = Image(context.user_data['photo_path'], width=200, height=150)
        story.append(img)
        
    doc.build(story)
    return pdf_filename

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Emissão de APR cancelada.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    TOKEN = "8899554735:AAE_eCvqX4zmcOP2EM5VaPo8cD1Ast_scWA"
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MATRICULA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_matricula)],
            MEDIDOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_medidor)],
            LOCALIZACAO: [MessageHandler(filters.LOCATION, get_localizacao)],
            PERGUNTAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_perguntas)],
            FOTO: [MessageHandler(filters.PHOTO, get_foto)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
