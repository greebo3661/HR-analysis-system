import streamlit as st
import json
from datetime import datetime
from db.models import init_db, SessionLocal, Vacancy, Match
from services.llm_client import LLMClient
from services.document_parser import DocumentParser, VacancyExtractor, ResumeExtractor
from config import load_system_prompt
from pdf_export import generate_pdf_report
from components.filters import render_filters, show_filter_summary
from components.status_manager import (
    render_status_badge, render_status_selector, 
    render_status_history, render_status_overview, get_status_label
)
from components.comments import render_comments
from utils.search import filter_matches
from pages.analytics import render_analytics_page

init_db()

st.set_page_config(page_title="HR Analysis System", layout="wide", page_icon="📊")

st.markdown("""
<style>
    .section-header {
        border-bottom: 2px solid #0066cc;
        padding-bottom: 8px;
        margin: 25px 0 15px 0;
        font-weight: 600;
        font-size: 18px;
        color: #0066cc;
    }
    .reasoning-box {
        background: #f8f9fa;
        border-left: 4px solid #6c757d;
        padding: 10px;
        border-radius: 5px;
        margin: 8px 0;
        font-size: 14px;
        color: #495057;
        font-style: italic;
    }
    .strengths-box {
        background: #d4edda;
        border-left: 4px solid #28a745;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        color: #155724;
    }
    .strengths-box strong {
        color: #155724;
    }
    .weaknesses-box {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        color: #856404;
    }
    .weaknesses-box strong {
        color: #856404;
    }
    .missing-box {
        background: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        color: #721c24;
    }
    .missing-box strong {
        color: #721c24;
    }
    .info-box {
        background: #d1ecf1;
        border-left: 4px solid #17a2b8;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        color: #0c5460;
    }
    .info-box strong {
        color: #0c5460;
    }
    .metric-help {
        font-size: 12px;
        color: #6c757d;
        font-style: italic;
        margin-top: 5px;
    }
    .table-header {
        font-weight: 600;
        color: #6c757d;
        border-bottom: 1px solid #444;
        padding-bottom: 5px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("HR Analysis System")

with st.sidebar.expander("⚙️ Настройки промптов"):
    st.markdown("### System Prompt")
    st.info("""
**Что это:** Основной промпт для анализа резюме.

**Содержит:**
- Критерии оценки (Hard Skills, Experience, и т.д.)
- Шкалу оценок (0-100)
- Формат ответа LLM (JSON структура)

**Когда редактировать:**
- Изменить веса критериев
- Добавить новые метрики
- Ужесточить/смягчить оценки
    """)
    
    uploaded_system_prompt = st.file_uploader(
        "Загрузить новый System Prompt (.txt)",
        type=["txt"],
        key="upload_system_prompt"
    )
    
    if uploaded_system_prompt:
        new_content = uploaded_system_prompt.read().decode('utf-8')
        if st.button("Применить System Prompt"):
            with open('/app/prompts/system_prompt.txt', 'w', encoding='utf-8') as f:
                f.write(new_content)
            st.success("System Prompt обновлён!")
    
    if st.button("📥 Скачать текущий System Prompt"):
        with open('/app/prompts/system_prompt.txt', 'r', encoding='utf-8') as f:
            st.download_button(
                "Сохранить файл",
                f.read(),
                file_name="system_prompt.txt",
                mime="text/plain"
            )
    
    st.divider()
    
    st.markdown("### HR Guidelines")
    st.info("""
**Что это:** Корпоративные правила найма.

**Содержит:**
- Приоритеты при найме
- Red Flags (автоматический отказ)
- Отраслевые особенности
    """)
    
    uploaded_hr_guidelines = st.file_uploader(
        "Загрузить новые HR Guidelines (.txt)",
        type=["txt"],
        key="upload_hr_guidelines"
    )
    
    if uploaded_hr_guidelines:
        new_content = uploaded_hr_guidelines.read().decode('utf-8')
        if st.button("Применить HR Guidelines"):
            with open('/app/prompts/hr_guidelines.txt', 'w', encoding='utf-8') as f:
                f.write(new_content)
            st.success("HR Guidelines обновлены!")
    
    if st.button("📥 Скачать текущие HR Guidelines"):
        with open('/app/prompts/hr_guidelines.txt', 'r', encoding='utf-8') as f:
            st.download_button(
                "Сохранить файл",
                f.read(),
                file_name="hr_guidelines.txt",
                mime="text/plain"
            )
    
    st.divider()
    
    
with st.sidebar.expander("🤖 Выбор модели анализа"):
    from config import AVAILABLE_MODELS, get_selected_model, set_selected_model
    
    current_model = get_selected_model()
    
    model_options = {
        config['name']: key 
        for key, config in AVAILABLE_MODELS.items()
    }
    
    selected_model_name = st.selectbox(
        "Модель для анализа",
        list(model_options.keys()),
        index=list(model_options.values()).index(current_model),
        help="Выберите LLM для анализа резюме",
        key="model_selector_sidebar"
    )
    
    new_model_key = model_options[selected_model_name]
    
    if new_model_key != current_model:
        set_selected_model(new_model_key)
        st.success(f"Модель изменена на {selected_model_name}")
        st.rerun()
    
    # Показываем описание текущей модели
    model_config = AVAILABLE_MODELS[current_model]
    st.info(f"**Текущая модель:** {model_config['name']}\n\n{model_config['description']}")

st.sidebar.divider()

if st.button("🔄 Перезагрузить промпты"):
        st.session_state['prompt_reloaded'] = True
        st.rerun()

page = st.sidebar.radio("Навигация", ["Вакансии", "Анализ", "Результаты", "Аналитика", "Kanban", "Сравнение"])

if page == "Аналитика":
    render_analytics_page()

elif page == "Вакансии":
    st.title("Управление вакансиями")
    
    add_method = st.radio("Способ добавления", ["Форма", "Загрузить файл"])
    
    if add_method == "Форма":
        with st.form("new_vacancy", clear_on_submit=True):
            st.subheader("Добавить вакансию")
            title = st.text_input("Должность *")
            company = st.text_input("Компания *")
            
            col1, col2 = st.columns(2)
            with col1:
                hard_skills = st.text_area("Hard Skills (через запятую)")
            with col2:
                soft_skills = st.text_area("Soft Skills (через запятую)")
            
            experience_years = st.number_input("Требуемый опыт (лет)", min_value=0, max_value=30, value=3)
            
            if st.form_submit_button("Сохранить"):
                if not title or not company:
                    st.error("Заполните обязательные поля!")
                else:
                    requirements = {
                        "hard_skills": [s.strip() for s in hard_skills.split(",") if s.strip()],
                        "soft_skills": [s.strip() for s in soft_skills.split(",") if s.strip()],
                        "experience_years": experience_years
                    }
                    
                    db = SessionLocal()
                    vacancy = Vacancy(
                        title=title,
                        company=company,
                        requirements_json=json.dumps(requirements, ensure_ascii=False)
                    )
                    db.add(vacancy)
                    db.commit()
                    db.close()
                    
                    st.success(f"Вакансия '{title}' добавлена")
                    st.rerun()
    
    else:
        st.subheader("Загрузить вакансию из файла")
        uploaded_file = st.file_uploader("Файл (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
        
        if uploaded_file and st.button("Обработать"):
            with st.spinner("Обработка..."):
                try:
                    file_bytes = uploaded_file.read()
                    text = DocumentParser.parse_file(file_bytes, uploaded_file.name)
                    
                    st.text_area("Извлечённый текст (500 символов)", text[:500], height=150)
                    
                    llm = LLMClient()
                    vacancy_data = VacancyExtractor.extract_vacancy_structure(text, llm)
                    
                    st.json(vacancy_data)
                    
                    db = SessionLocal()
                    vacancy = Vacancy(
                        title=vacancy_data['title'],
                        company=vacancy_data['company'],
                        requirements_json=json.dumps(vacancy_data['requirements'], ensure_ascii=False)
                    )
                    db.add(vacancy)
                    db.commit()
                    db.close()
                    
                    st.success(f"Вакансия '{vacancy_data['title']}' добавлена")
                    
                except Exception as e:
                    st.error(f"Ошибка: {str(e)}")
    
    st.divider()
    st.subheader("Текущие вакансии")
    
    db = SessionLocal()
    vacancies = db.query(Vacancy).order_by(Vacancy.created_at.desc()).all()
    db.close()
    
    if not vacancies:
        st.info("Вакансии отсутствуют")
    else:
        for v in vacancies:
            with st.expander(f"{v.title} @ {v.company} (ID: {v.id})"):
                req = json.loads(v.requirements_json)
                st.write(f"**Hard Skills:** {', '.join(req.get('hard_skills', []))}")
                st.write(f"**Опыт:** {req.get('experience_years', 'N/A')} лет")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Удалить вакансию", key=f"del_{v.id}"):
                        db = SessionLocal()
                        db.query(Match).filter(Match.vacancy_id == v.id).delete()
                        db.query(Vacancy).filter(Vacancy.id == v.id).delete()
                        db.commit()
                        db.close()
                        st.success(f"Вакансия и связанные резюме удалены")
                        st.rerun()
                
                with col2:
                    db = SessionLocal()
                    matches_count = db.query(Match).filter(Match.vacancy_id == v.id).count()
                    db.close()
                    if matches_count > 0:
                        if st.button(f"🧹 Очистить резюме ({matches_count})", key=f"clear_{v.id}"):
                            db = SessionLocal()
                            db.query(Match).filter(Match.vacancy_id == v.id).delete()
                            db.commit()
                            db.close()
                            st.success(f"Резюме очищены")
                            st.rerun()

elif page == "Анализ":
    st.title("Анализ резюме")
    
    db = SessionLocal()
    vacancies = db.query(Vacancy).all()
    db.close()
    
    if not vacancies:
        st.warning("Добавьте вакансии")
    else:
        vacancy_options = {f"{v.id}: {v.title} @ {v.company}": v for v in vacancies}
        selected_key = st.selectbox("Вакансия", list(vacancy_options.keys()))
        vacancy = vacancy_options[selected_key]
        
        st.info(f"Вакансия: **{vacancy.title}** | **{vacancy.company}**")
        
        input_method = st.radio("Загрузка резюме", ["Файлы (PDF/DOCX)", "JSON"])
        
        if input_method == "Файлы (PDF/DOCX)":
            uploaded_files = st.file_uploader("Резюме", type=["pdf", "docx", "txt"], accept_multiple_files=True)
            
            if uploaded_files and st.button("Анализировать"):
                progress_bar = st.progress(0)
                results = []
                
                for i, file in enumerate(uploaded_files):
                    st.info(f"Обработка: {file.name}")
                    
                    try:
                        file_bytes = file.read()
                        text = DocumentParser.parse_file(file_bytes, file.name)
                        
                        llm = LLMClient()
                        resume = ResumeExtractor.extract_resume_structure(text, llm)
                        
                        vacancy_data = {
                            "title": vacancy.title,
                            "company": vacancy.company,
                            "requirements": json.loads(vacancy.requirements_json)
                        }
                        
                        analysis = llm.analyze_resume(resume, vacancy_data)
                        
                        db = SessionLocal()
                        match = Match(
                            resume_name=resume.get('name', file.name),
                            vacancy_id=vacancy.id,
                            vacancy_title=vacancy.title,
                            score=analysis['matching_score']['overall'],
                            analysis_json=json.dumps(analysis, ensure_ascii=False),
                            status='new'
                        )
                        db.add(match)
                        db.commit()
                        db.close()
                        
                        results.append({
                            "file": file.name,
                            "name": resume.get('name', 'Unknown'),
                            "score": analysis['matching_score']['overall']
                        })
                        
                    except Exception as e:
                        st.error(f"Ошибка в {file.name}: {str(e)}")
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                st.success(f"Обработано: {len(results)} резюме")
                if results:
                    st.dataframe(results)
        
        else:
            st.subheader("JSON резюме")
            example = {"name": "Иванов Иван", "age": 28, "skills": ["Python"]}
            
            resume_json = st.text_area("JSON", value=json.dumps(example, ensure_ascii=False, indent=2), height=300)
            
            if st.button("Анализировать"):
                try:
                    resume = json.loads(resume_json)
                    
                    with st.spinner("Анализ..."):
                        llm = LLMClient()
                        vacancy_data = {
                            "title": vacancy.title,
                            "company": vacancy.company,
                            "requirements": json.loads(vacancy.requirements_json)
                        }
                        
                        analysis = llm.analyze_resume(resume, vacancy_data)
                        
                        db = SessionLocal()
                        match = Match(
                            resume_name=resume.get('name', 'Unknown'),
                            vacancy_id=vacancy.id,
                            vacancy_title=vacancy.title,
                            score=analysis['matching_score']['overall'],
                            analysis_json=json.dumps(analysis, ensure_ascii=False),
                            status='new'
                        )
                        db.add(match)
                        db.commit()
                        db.close()
                        
                        st.success("Анализ завершён")
                        
                except Exception as e:
                    st.error(f"Ошибка: {str(e)}")

elif page == "Результаты":
    st.title("Результаты анализа")
    
    db = SessionLocal()
    all_matches = db.query(Match).order_by(Match.score.desc()).all()
    vacancies = db.query(Vacancy).all()
    db.close()
    
    if not all_matches:
        st.info("Результаты отсутствуют")
    else:
        render_status_overview(all_matches)
        
        st.divider()
        
        filters = render_filters(vacancies)
        
        matches = filter_matches(
            all_matches,
            vacancy_id=filters['vacancy_id'],
            min_score=filters['min_score'],
            max_score=filters['max_score'],
            recommendation=filters['recommendation'],
            search_query=filters['search_query'],
            date_from=filters['date_from'],
            date_to=filters['date_to']
        )
        
        show_filter_summary(filters, len(all_matches), len(matches))
        
        st.divider()
        st.subheader("Список кандидатов")
        
        if not matches:
            st.warning("Нет кандидатов, соответствующих фильтрам")
        else:
            header_cols = st.columns([0.5, 3, 2, 1, 1, 1.5, 1.5])
            with header_cols[0]:
                st.markdown("<div class='table-header'></div>", unsafe_allow_html=True)
            with header_cols[1]:
                st.markdown("<div class='table-header'>Кандидат</div>", unsafe_allow_html=True)
            with header_cols[2]:
                st.markdown("<div class='table-header'>Вакансия</div>", unsafe_allow_html=True)
            with header_cols[3]:
                st.markdown("<div class='table-header'>Overall</div>", unsafe_allow_html=True)
            with header_cols[4]:
                st.markdown("<div class='table-header'>Решение</div>", unsafe_allow_html=True)
            with header_cols[5]:
                st.markdown("<div class='table-header'>Статус</div>", unsafe_allow_html=True)
            with header_cols[6]:
                st.markdown("<div class='table-header'>Дата</div>", unsafe_allow_html=True)
            
            for m in matches:
                analysis = json.loads(m.analysis_json)
                rec_map = {"YES": "✅", "NO": "❌", "MAYBE": "🔍"}
                rec_icon = rec_map.get(analysis.get('recommendation', 'MAYBE'), '🔍')
                
                cols = st.columns([0.5, 3, 2, 1, 1, 1.5, 1.5])
                
                with cols[0]:
                    if st.button("👁️", key=f"view_{m.id}", help="Открыть детальный анализ"):
                        st.session_state['selected_match_id'] = m.id
                        st.rerun()
                
                with cols[1]:
                    st.write(f"**{m.resume_name}**")
                
                with cols[2]:
                    st.write(f"{m.vacancy_title}")
                
                with cols[3]:
                    st.write(f"**{m.score}%**")
                
                with cols[4]:
                    st.write(f"{rec_icon}")
                
                with cols[5]:
                    status = getattr(m, 'status', 'new')
                    render_status_badge(status)
                
                with cols[6]:
                    date_str = m.created_at.strftime("%d.%m %H:%M") if hasattr(m, 'created_at') else "N/A"
                    st.write(date_str)
        
        if matches:
            st.divider()
            st.markdown("<div class='section-header'>Детальный анализ кандидата</div>", unsafe_allow_html=True)
            
            if 'selected_match_id' in st.session_state and st.session_state['selected_match_id']:
                default_id = st.session_state['selected_match_id']
            else:
                default_id = matches[0].id
            
            match_id = st.selectbox(
                "Выберите кандидата", 
                [m.id for m in matches], 
                format_func=lambda x: f"ID {x}: {next(m.resume_name for m in matches if m.id == x)}",
                index=[m.id for m in matches].index(default_id) if default_id in [m.id for m in matches] else 0,
                key="results_match_selector"
            )
            
            st.session_state['selected_match_id'] = match_id
            
            selected = next((m for m in matches if m.id == match_id), None)
            if selected:
                analysis = json.loads(selected.analysis_json)
                
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"### {selected.resume_name}")
                with col2:
                    pdf_buffer = generate_pdf_report(selected, analysis)
                    st.download_button(
                        label="📄 Экспорт PDF",
                        data=pdf_buffer,
                        file_name=f"analysis_{selected.resume_name.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )
                with col3:
                    if st.button("🗑️ Удалить", key="delete_match_button"):
                        db = SessionLocal()
                        db.query(Match).filter(Match.id == selected.id).delete()
                        db.commit()
                        db.close()
                        if 'selected_match_id' in st.session_state:
                            del st.session_state['selected_match_id']
                        st.rerun()
                
                st.write(f"**Вакансия:** {selected.vacancy_title}")
                
                st.divider()
                col1, col2 = st.columns(2)
                
                with col1:
                    current_status = getattr(selected, 'status', 'new')
                    render_status_selector(selected.id, current_status)
                    render_status_history(selected.id)
                
                with col2:
                    render_comments(selected.id)
                
                st.divider()
                
                st.markdown("<div class='section-header'>Основные показатели</div>", unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Overall Score", f"{analysis['matching_score']['overall']}%")
                    st.markdown("<div class='metric-help'>Итоговая оценка</div>", unsafe_allow_html=True)
                with col2:
                    st.metric("Hard Skills", f"{analysis['matching_score'].get('hard_skills', 0)}%")
                    st.markdown("<div class='metric-help'>Технические навыки (65%)</div>", unsafe_allow_html=True)
                with col3:
                    st.metric("Experience", f"{analysis['matching_score'].get('experience', 0)}%")
                    st.markdown("<div class='metric-help'>Опыт (35%)</div>", unsafe_allow_html=True)
                with col4:
                    rec_map = {"YES": "Принять", "NO": "Отклонить", "MAYBE": "Уточнить"}
                    rec = rec_map.get(analysis.get('recommendation', 'N/A'), 'N/A')
                    st.metric("Решение", rec)
                    st.markdown("<div class='metric-help'>Рекомендация</div>", unsafe_allow_html=True)

elif page == "Kanban":
    from components.kanban import render_kanban_board
    
    st.title("📋 Kanban доска")
    
    db = SessionLocal()
    all_matches = db.query(Match).all()
    db.close()
    
    if not all_matches:
        st.info("Нет кандидатов для отображения")
    else:
        render_kanban_board(all_matches)
        
        # Показываем счётчик выбранных для сравнения
        if 'comparison_candidates' in st.session_state and st.session_state['comparison_candidates']:
            count = len(st.session_state['comparison_candidates'])
            st.sidebar.success(f"✅ Выбрано для сравнения: {count}/3")
            
            if st.sidebar.button("🔍 Перейти к сравнению"):
                st.session_state['active_page'] = 'Сравнение'
                st.rerun()

elif page == "Сравнение":
    from components.comparison import render_comparison_view
    
    st.title("🔍 Сравнение кандидатов")
    
    if 'comparison_candidates' not in st.session_state or not st.session_state['comparison_candidates']:
        st.info("Выберите кандидатов для сравнения на Kanban доске (кнопка 📊)")
        st.info("Можно выбрать до 3 кандидатов одновременно")
    else:
        db = SessionLocal()
        candidate_ids = st.session_state['comparison_candidates']
        matches = db.query(Match).filter(Match.id.in_(candidate_ids)).all()
        db.close()
        
        render_comparison_view(matches)

elif page == "Kanban":
    from components.kanban import render_kanban_board
    
    st.title("📋 Kanban доска")
    
    db = SessionLocal()
    all_matches = db.query(Match).all()
    db.close()
    
    if not all_matches:
        st.info("Нет кандидатов для отображения")
    else:
        render_kanban_board(all_matches)
        
        # Показываем счётчик выбранных для сравнения
        if 'comparison_candidates' in st.session_state and st.session_state['comparison_candidates']:
            count = len(st.session_state['comparison_candidates'])
            st.sidebar.success(f"✅ Выбрано для сравнения: {count}/3")
            
            if st.sidebar.button("🔍 Перейти к сравнению"):
                st.session_state['active_page'] = 'Сравнение'
                st.rerun()

elif page == "Сравнение":
    from components.comparison import render_comparison_view
    
    st.title("🔍 Сравнение кандидатов")
    
    if 'comparison_candidates' not in st.session_state or not st.session_state['comparison_candidates']:
        st.info("Выберите кандидатов для сравнения на Kanban доске (кнопка 📊)")
        st.info("Можно выбрать до 3 кандидатов одновременно")
    else:
        db = SessionLocal()
        candidate_ids = st.session_state['comparison_candidates']
        matches = db.query(Match).filter(Match.id.in_(candidate_ids)).all()
        db.close()
        
        render_comparison_view(matches)

