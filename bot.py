import os
import socket
import uuid
import urllib.request
from datetime import datetime, timezone
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, Update
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

# Estados da conversa
MATRICULA, MEDIDOR, LOCALIZACAO, PERGUNTAS, FOTO = range(5)

# Lista de perguntas do checklist APR
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
    
    await update.message.reply_text("Iniciando emissão da Análise Prévia de Risco (APR).\n\nPor favor, informe a sua MATRÍCULA:")
    return MATRICULA

async def get_matricula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['matricula'] = update.message.text
    await update.message.reply_text("Informe o NÚMERO DO MEDIDOR:")
    return MEDIDOR

async def get_medidor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['medidor'] = update.message.text
    
    button = KeyboardButton(text="📍 Enviar minha localização atual", request_location=True)
    keyboard = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "Por favor, clique no botão abaixo para enviar sua localização atual:",
        reply_markup=keyboard
    )
    return LOCALIZACAO

async def get_localizacao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    loc = update.message.location
    context.user_data['lat'] = loc.latitude
    context.user_data['lon'] = loc.longitude
    
    reply_keyboard = [['SIM', 'NÃO']]
    
    # Pergunta geral para confirmar todos de uma vez
    msg = (
        "<b>CHECKLIST DE SEGURANÇA APR:</b>\n\n"
        "1. Possuo equipamentos e ferramentas em condições de segurança?\n"
        "2. Veículo estacionado em local seguro?\n"
        "3. Local desobstruído e sem risco de queda?\n"
        "4. Local livre de insetos ou animais agressivos?\n"
        "5. Caixa do medidor verificada sem fuga de tensão elétrica?\n"
        "6. É possível executar a atividade com segurança?\n\n"
        "<b>Confirma SIM para todos os itens acima?</b>"
    )
    
    await update.message.reply_html(
        msg,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return PERGUNTAS

async def get_perguntas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ans = update.message.text.upper()
    
    # Preenche todas as respostas com a opção escolhida (SIM ou NÃO)
    context.user_data['answers'] = [ans] * len(QUESTIONS)
    
    await update.message.reply_text(
        "Checklist registrado com sucesso!\n\nAgora, envie uma FOTO/SELFIE do local do serviço para finalizar.",
        reply_markup=ReplyKeyboardRemove()
    )
    return FOTO

async def get_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"foto_{update.effective_user.id}.jpg"
    await photo_file.download_to_drive(photo_path)
    
    context.user_data['photo_path'] = photo_path
    context.user_data['termino'] = datetime.now()
    
    await update.message.reply_text("Gerando o comprovante em PDF com o mapa e foto...")
    
    # Baixar mapa via Geoapify / CartoDB estático com marcador
    map_path = f"mapa_{update.effective_user.id}.png"
    lat, lon = context.user_data['lat'], context.user_data['lon']
    
    # URL do gerador de mapa estável e limpo
    map_url = f"https://maps.geoapify.com/v1/staticmap?style=osm-bright&width=400&height=300&center=lonlat:{lon},{lat}&zoom=16&marker=lonlat:{lon},{lat};color:%23ff0000;size:medium&apiKey=c518b0e8c07e4c70a1a0f9b0c201d4a0"
    
    try:
        req = urllib.request.Request(map_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp, open(map_path, 'wb') as out:
            out.write(resp.read())
        context.user_data['map_path'] = map_path
    except Exception:
        # Fallback de mapa secundário caso a API principal oscile
        try:
            map_url_alt = f"https://static-maps.yandex.ru/1.x/?lang=pt_BR&ll={lon},{lat}&z=16&l=map&pt={lon},{lat},pm2rdm&size=400,300"
            req = urllib.request.Request(map_url_alt, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp, open(map_path, 'wb') as out:
                out.write(resp.read())
            context.user_data['map_path'] = map_path
        except Exception:
            context.user_data['map_path'] = None

    pdf_path = generate_pdf(update, context)
    
    medidor_num = context.user_data.get('medidor', 'APR')
    with open(pdf_path, 'rb') as pdf:
        await update.message.reply_document(
            document=pdf,
            filename=f"APR_Medidor_{medidor_num}.pdf",
            caption=f"📋 *Relatório APR Concluído*\nMedidor: {medidor_num}\nID: {context.user_data['id_apr']}",
            parse_mode="Markdown"
        )
        
    for path in [photo_path, map_path, pdf_path]:
        if path and os.path.exists(path):
            os.remove(path)
        
    return ConversationHandler.END

def generate_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    medidor_num = context.user_data.get('medidor', '')
    pdf_filename = f"APR_Medidor_{medidor_num}.pdf"
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=15, leading=18, textColor=colors.HexColor('#1A365D'))
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=12, leading=14, textColor=colors.HexColor('#2B6CB0'))
    normal_style = styles['Normal']
    
    # Título do PDF
    story.append(Paragraph(f"<b>RELATÓRIO DE APR - MEDIDOR: {medidor_num}</b>", title_style))
    story.append(Spacer(1, 10))
    
    # Tabela de Dados Gerais
    info_data = [
        ["ID APR:", context.user_data['id_apr'], "LATITUDE:", str(context.user_data['lat'])],
        ["MATRÍCULA:", context.user_data['matricula'], "LONGITUDE:", str(context.user_data['lon'])],
        ["MEDIDOR:", context.user_data['medidor'], "TELEGRAM ID:", str(update.effective_user.id)],
        ["INÍCIO:", context.user_data['inicio'].strftime('%d/%m/%Y %H:%M'), "COMPUTADOR:", socket.gethostname()],
        ["TÉRMINO:", context.user_data['termino'].strftime('%d/%m/%Y %H:%M'), "HORÁRIO UTC:", datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')]
    ]
    
    t_info = Table(info_data, colWidths=[90, 160, 90, 190])
    t_info.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#2D3748')),
        ('TEXTCOLOR', (2,0), (2,-1), colors.HexColor('#2D3748')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 12))
    
    # Checklist APR
    story.append(Paragraph("<b>CHECKLIST DE SEGURANÇA (APR)</b>", subtitle_style))
    story.append(Spacer(1, 5))
    
    for q, a in zip(QUESTIONS, context.user_data['answers']):
        story.append(Paragraph(f"<b>{q}</b>", normal_style))
        story.append(Paragraph(f"Resposta: <b>{a}</b>", normal_style))
        story.append(Spacer(1, 3))
        
    story.append(Spacer(1, 15))
    
    # Fotos e Mapa Lado a Lado
    story.append(Paragraph("<b>COMPROVANTE (FOTO E LOCALIZAÇÃO)</b>", subtitle_style))
    story.append(Spacer(1, 8))
    
    img_foto = Image(context.user_data['photo_path'], width=230, height=170)
    
    if context.user_data.get('map_path') and os.path.exists(context.user_data['map_path']):
        img_mapa = Image(context.user_data['map_path'], width=230, height=170)
    else:
        img_mapa = Paragraph("<i>Mapa indisponível</i>", normal_style)
    
    media_table = Table([[img_foto, img_mapa]], colWidths=[260, 260])
    media_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(media_table)
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
