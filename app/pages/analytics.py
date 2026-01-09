"""Страница аналитики и статистики"""
import streamlit as st
from datetime import datetime, timedelta
from db.models import SessionLocal, Match, Vacancy
from utils.metrics import (
    calculate_funnel_metrics,
    calculate_conversion_rate,
    get_average_scores_by_vacancy,
    get_top_missing_skills,
    get_recommendation_distribution,
    get_candidates_by_date,
    get_time_to_decision_stats
)
from components.charts import (
    render_funnel_chart,
    render_score_distribution,
    render_vacancy_comparison,
    render_missing_skills_chart,
    render_recommendation_pie,
    render_timeline_chart
)

def render_analytics_page():
    """Рендерит страницу аналитики"""
    
    st.title("📊 Аналитика и статистика")
    
    # Загружаем данные
    db = SessionLocal()
    all_matches = db.query(Match).all()
    vacancies = db.query(Vacancy).all()
    db.close()
    
    if not all_matches:
        st.info("Нет данных для аналитики. Добавьте кандидатов.")
        return
    
    # Фильтр по периоду
    col1, col2 = st.columns(2)
    with col1:
        days_filter = st.selectbox(
            "Период",
            [7, 14, 30, 90, 365, 0],
            format_func=lambda x: f"Последние {x} дней" if x > 0 else "Всё время",
            index=2,
            key="analytics_period_filter"  # ИСПРАВЛЕНО: добавлен key
        )
    
    # Фильтруем по периоду
    if days_filter > 0:
        cutoff_date = datetime.now() - timedelta(days=days_filter)
        matches = [m for m in all_matches if hasattr(m, 'created_at') and m.created_at >= cutoff_date]
    else:
        matches = all_matches
    
    with col2:
        st.metric("Всего кандидатов", len(matches))
    
    st.divider()
    
    # Основные метрики
    st.markdown("### 📈 Ключевые показатели")
    
    col1, col2, col3, col4 = st.columns(4)
    
    avg_score = sum(m.score for m in matches) / len(matches) if matches else 0
    
    conversion = calculate_conversion_rate(matches)
    time_stats = get_time_to_decision_stats(matches)
    
    with col1:
        st.metric("Средняя оценка", f"{avg_score:.1f}%")
    
    with col2:
        st.metric("Конверсия в оффер", f"{conversion.get('overall_success', 0):.1f}%")
    
    with col3:
        st.metric("Отказов", f"{conversion.get('rejection_rate', 0):.1f}%")
    
    with col4:
        avg_hours = time_stats.get('avg_hours', 0)
        st.metric("Среднее время решения", f"{avg_hours:.1f}ч")
    
    st.divider()
    
    # Графики в 2 колонки
    col1, col2 = st.columns(2)
    
    with col1:
        # Воронка
        funnel_metrics = calculate_funnel_metrics(matches)
        render_funnel_chart(funnel_metrics)
        
        # Распределение оценок
        render_score_distribution(matches)
    
    with col2:
        # Распределение решений
        recommendations = get_recommendation_distribution(matches)
        render_recommendation_pie(recommendations)
        
        # Динамика по дням
        date_counts = get_candidates_by_date(matches, days=30)
        render_timeline_chart(date_counts)
    
    st.divider()
    
    # Сравнение вакансий
    st.markdown("### 🎯 Анализ по вакансиям")
    vacancy_scores = get_average_scores_by_vacancy(matches)
    
    if vacancy_scores:
        render_vacancy_comparison(vacancy_scores)
        
        # Таблица с детализацией
        with st.expander("Детальная статистика по вакансиям"):
            table_data = []
            for vacancy, scores in vacancy_scores.items():
                table_data.append({
                    "Вакансия": vacancy,
                    "Кандидатов": scores['count'],
                    "Средняя оценка": f"{scores['overall']:.1f}%",
                    "Hard Skills": f"{scores['hard_skills']:.1f}%",
                    "Experience": f"{scores['experience']:.1f}%"
                })
            st.dataframe(table_data, use_container_width=True)
    
    st.divider()
    
    # ТОП недостающих навыков
    st.markdown("### 🎓 Анализ недостающих навыков")
    top_skills = get_top_missing_skills(matches, top_n=10)
    render_missing_skills_chart(top_skills)
    
    if top_skills:
        st.info(f"💡 **Рекомендация:** Самый часто недостающий навык — **{top_skills[0][0]}** ({top_skills[0][1]} кандидатов)")
