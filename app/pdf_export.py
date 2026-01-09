import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# Регистрируем русские шрифты
pdfmetrics.registerFont(TTFont('DejaVu', '/app/fonts/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVu-Bold', '/app/fonts/DejaVuSans-Bold.ttf'))

def generate_pdf_report(match, analysis):
    """Генерирует читаемый PDF отчёт по кандидату на русском"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        leftMargin=2*cm, 
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    story = []
    
    # Стили с русским шрифтом
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName='DejaVu-Bold',
        fontSize=20,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=10,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName='DejaVu-Bold',
        fontSize=14,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=12,
        spaceBefore=18,
        borderWidth=0,
        borderColor=colors.HexColor('#0066cc'),
        borderPadding=5,
        backColor=colors.HexColor('#f0f0f0')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName='DejaVu',
        fontSize=11,
        spaceAfter=8,
        leading=14
    )
    
    bold_style = ParagraphStyle(
        'CustomBold',
        parent=styles['Normal'],
        fontName='DejaVu-Bold',
        fontSize=11,
        spaceAfter=8,
        leading=14
    )
    
    small_style = ParagraphStyle(
        'CustomSmall',
        parent=styles['Normal'],
        fontName='DejaVu',
        fontSize=9,
        textColor=colors.HexColor('#666666'),
        spaceAfter=6,
        leading=12
    )
    
    # Заголовок
    story.append(Paragraph(f"Анализ кандидата: {match.resume_name}", title_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"Вакансия: <b>{match.vacancy_title}</b>", normal_style))
    story.append(Paragraph(f"Дата анализа: {datetime.now().strftime('%d.%m.%Y %H:%M')}", small_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Основные показатели
    story.append(Paragraph("Основные показатели", heading_style))
    
    metrics = [
        ("Общая оценка соответствия", analysis['matching_score']['overall'], "Итоговая оценка кандидата"),
        ("Технические навыки", analysis['matching_score'].get('hard_skills', 0), "Вес 65% в итоговой оценке"),
        ("Релевантный опыт работы", analysis['matching_score'].get('experience', 0), "Вес 35% в итоговой оценке"),
        ("Соответствие культуре компании", analysis['matching_score'].get('cultural_fit', 0), "Дополнительный критерий"),
        ("Потенциал развития", analysis['matching_score'].get('growth_potential', 0), "Дополнительный критерий"),
        ("Качество резюме", analysis['matching_score'].get('communication', 0), "Дополнительный критерий"),
        ("Стабильность работы", analysis['matching_score'].get('stability', 0), "Дополнительный критерий"),
    ]
    
    for name, score, desc in metrics:
        story.append(Paragraph(f"<b>{name}:</b> {score}%", normal_style))
        story.append(Paragraph(f"<i>{desc}</i>", small_style))
    
    story.append(Spacer(1, 0.3*cm))
    
    # Рекомендация
    rec_map = {"YES": "Рекомендован к найму", "NO": "Не рекомендован", "MAYBE": "Требуется уточнение"}
    conf_map = {"HIGH": "Высокая", "MEDIUM": "Средняя", "LOW": "Низкая"}
    
    story.append(Paragraph(f"<b>Рекомендация:</b> {rec_map.get(analysis.get('recommendation', 'N/A'), 'N/A')}", bold_style))
    story.append(Paragraph(f"<b>Уверенность в оценке:</b> {conf_map.get(analysis.get('confidence_level', 'MEDIUM'), 'Средняя')}", normal_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Обоснование оценок
    story.append(Paragraph("Обоснование оценок", heading_style))
    
    reasoning_items = [
        ("Технические навыки", analysis['matching_score'].get('hard_skills_reasoning', 'Не указано')),
        ("Релевантный опыт", analysis['matching_score'].get('experience_reasoning', 'Не указано')),
        ("Соответствие культуре", analysis['matching_score'].get('cultural_fit_reasoning', 'Не указано')),
        ("Потенциал развития", analysis['matching_score'].get('growth_potential_reasoning', 'Не указано')),
        ("Качество резюме", analysis['matching_score'].get('communication_reasoning', 'Не указано')),
        ("Стабильность", analysis['matching_score'].get('stability_reasoning', 'Не указано')),
    ]
    
    for title, text in reasoning_items:
        story.append(Paragraph(f"<b>{title}:</b>", bold_style))
        story.append(Paragraph(text, normal_style))
        story.append(Spacer(1, 0.2*cm))
    
    # Общая оценка
    story.append(Paragraph("Общая оценка", heading_style))
    story.append(Paragraph(analysis.get('summary', 'Не указана'), normal_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Сильные стороны
    story.append(Paragraph("Сильные стороны", heading_style))
    for s in analysis.get('strengths', []):
        story.append(Paragraph(f"• {s}", normal_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Слабые стороны
    story.append(Paragraph("Слабые стороны", heading_style))
    for w in analysis.get('weaknesses', []):
        story.append(Paragraph(f"• {w}", normal_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Недостающие навыки
    if analysis.get('missing_skills'):
        story.append(Paragraph("Недостающие навыки", heading_style))
        for skill in analysis['missing_skills']:
            story.append(Paragraph(f"• {skill}", normal_style))
        story.append(Spacer(1, 0.3*cm))
    
    # Риски
    if analysis.get('red_flags'):
        story.append(Paragraph("Возможные риски", heading_style))
        for flag in analysis['red_flags']:
            story.append(Paragraph(f"• {flag}", normal_style))
        story.append(Spacer(1, 0.3*cm))
    
    # Вопросы для интервью
    story.append(Paragraph("Рекомендуемые вопросы для интервью", heading_style))
    for i, q in enumerate(analysis.get('interview_questions', []), 1):
        story.append(Paragraph(f"{i}. {q}", normal_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Следующие шаги
    story.append(Paragraph("Рекомендованные следующие шаги", heading_style))
    for step in analysis.get('next_steps', []):
        story.append(Paragraph(f"• {step}", normal_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Дополнительная информация
    story.append(Paragraph("Дополнительная информация", heading_style))
    
    salary_map = {
        "MATCH": "Соответствует бюджету компании", 
        "BELOW": "Ниже ожиданий кандидата", 
        "ABOVE": "Выше бюджета компании", 
        "UNCLEAR": "Не указано в резюме"
    }
    story.append(Paragraph(f"<b>Зарплатные ожидания:</b> {salary_map.get(analysis.get('salary_expectation_fit', 'UNCLEAR'), 'Не указано')}", normal_style))
    
    avail_map = {
        "IMMEDIATE": "Готов приступить немедленно",
        "NOTICE_PERIOD": "Требуется отработка (обычно 2 недели)",
        "UNCLEAR": "Не указано в резюме"
    }
    story.append(Paragraph(f"<b>Доступность:</b> {avail_map.get(analysis.get('availability', 'UNCLEAR'), 'Не указано')}", normal_style))
    
    # Генерируем PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
