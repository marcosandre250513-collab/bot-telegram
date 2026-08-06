import os
import socket
import uuid
import ssl
import math
import urllib.request
from datetime import datetime, timezone
from PIL import Image as PILImage, ImageOps, ImageDraw
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
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
    context.user_data['answers'] = [ans] * len(QUESTIONS)
    
    await update.message.reply_text(
        "Checklist registrado com sucesso!\n\nAgora, envie uma FOTO/SELFIE do local do serviço para finalizar.",
        reply_markup=ReplyKeyboardRemove()
    )
    return FOTO

def generate_osm_map(lat, lon, output_path, zoom=16, width=400, height=300):
    """Gera um mapa nativo baixando tiles do OpenStreetMap e desenhando marcador no centro."""
    try:
        lat_rad = math.radians(lat)
        n = 2 ** zoom
        xtile_float = (lon + 180.0) / 360.0 * n
        ytile_float = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n

        xtile = int(xtile_float)
        ytile = int(ytile_float)

        x_offset = int((xtile_float - xtile) * 256)
        y_offset = int((ytile_float - ytile) * 256)

        canvas = PILImage.new('RGB', (256 * 3, 256 * 3), color=(240, 240, 240))
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) APRBot/1.0'}
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        for dx in range(-1, 2):
            for dy in range(-1, 2):
                tile_x, tile_y = xtile + dx, ytile + dy
                url = f"https://tile.openstreetmap.org/{zoom}/{tile_x}/{tile_y}.png"
                req = urllib.request.Request(url, headers=headers)
                try:
                    with urllib.request.urlopen(req, context=ssl_ctx, timeout=4) as resp:
                        tile_img = PILImage.open(resp)
                        canvas.paste(tile_img, ((dx + 1) * 256, (dy + 1) * 256))
                except Exception:
                    pass

        center_x = 256 + x_offset
        center_y = 256 + y_offset

        left = max(0, center_x - (width // 2))
        top = max(0, center_y - (height // 2))
        cropped = canvas.crop((left, top, left + width, top + height))

        # Desenhar Marcador (Pin Vermelho) no centro exato
        draw = ImageDraw.Draw(cropped)
        cx, cy = width // 2, height // 2
        draw.ellipse([cx - 10, cy - 25, cx + 10, cy - 5], fill=(220, 38, 38), outline=(255, 255, 255), width=2)
        draw.polygon([(cx - 8, cy - 10), (cx + 8, cy - 10), (cx, cy)], fill=(220, 38, 38))
        draw.ellipse([cx - 4, cy - 18, cx + 4, cy - 12], fill=(255, 255, 255))

        cropped.save(output_path)
        return output_path
    except Exception:
        return None

def get_proportional_image(path, max_w, max_h):
    """Ajusta orientacao EXIF da foto e redimensiona sem distorcer."""
    try:
        with PILImage.open(path) as img:
            # Corrige a rotacao automatica de fotos do celular
            img = ImageOps.exif_transpose(img)
            img.save(path)
            w, h = img.size

        ratio = min(max_w / w, max_h / h)
        return RLImage(path, width=w * ratio, height=h * ratio)
    except Exception:
        return RLImage(path, width=max_w, height=max_h)

async def get_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"foto_{update.effective_user.id}.jpg"
    await photo_file.download_to_drive(photo_path)
    
    context.user_data['photo_path'] = photo_path
    context.user_data['termino'] = datetime.now()
    
    await update.message.reply_text("Gerando o comprovante em PDF com o mapa e foto...")
    
    map_path = f"mapa_{update.effective_user.id}.png"
    lat, lon = context.user_data['lat'], context.user_data['lon']
    
    saved_map = generate_osm_map(lat, lon, map_path)
    context.user_data['map_path'] = saved_map

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
    
    # Título
    story.append(Paragraph(f"<b>RELATÓRIO DE APR - MEDIDOR: {medidor_num}</b>", title_style))
    story.append(Spacer(1, 10))
    
    # Dados Gerais
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
    
    # Checklist
    story.append(Paragraph("<b>CHECKLIST DE SEGURANÇA (APR)</b>", subtitle_style))
    story.append(Spacer(1, 5))
    
    for q, a in zip(QUESTIONS, context.user_data['answers']):
        story.append(Paragraph(f"<b>{q}</b>", normal_style))
        story.append(Paragraph(f"Resposta: <b>{a}</b>", normal_style))
        story.append(Spacer(1, 3))
        
    story.append(Spacer(1, 15))
    
    # Fotos e Mapa Proporcionais
    story.append(Paragraph("<b>COMPROVANTE (FOTO E LOCALIZAÇÃO)</b>", subtitle_style))
    story.append(Spacer(1, 8))
    
    img_foto = get_proportional_image(context.user_data['photo_path'], max_w=240, max_h=220)
    
    if context.user_data.get('map_path') and os.path.exists(context.user_data['map_path']):
        img_mapa = get_proportional_image(context.user_data['map_path'], max_w=240, max_h=220)
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
