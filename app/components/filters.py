"""UI компонент для фильтрации кандидатов"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

def render_filters(vacancies: list) -> Dict[str, Any]:
    """
    Рендерит панель фильтров и возвращает выбранные значения
    
    Args:
        vacancies: Список объектов Vacancy из БД
    
    Returns:
        Словарь с параметрами фильтрации
    """
    st.markdown("### 🔍 Фильтры")
    
    # Создаём expander для компактности
    with st.expander("Настроить фильтры", expanded=True):
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Фильтр по вакансии
            vacancy_options = {"Все вакансии": None}
            for v in vacancies:
                vacancy_options[f"{v.title} @ {v.company}"] = v.id
            
            selected_vacancy = st.selectbox(
                "Вакансия",
                list(vacancy_options.keys()),
                key="filter_vacancy"
            )
            vacancy_id = vacancy_options[selected_vacancy]
            
            # Фильтр по решению
            recommendation_map = {
                "Все": None,
                "✅ Принять": "YES",
                "❌ Отклонить": "NO",
                "🔍 Уточнить": "MAYBE"
            }
            
            selected_rec = st.selectbox(
                "Решение",
                list(recommendation_map.keys()),
                key="filter_recommendation"
            )
            recommendation = recommendation_map[selected_rec]
        
        with col2:
            # Фильтр по рейтингу (слайдер)
            score_range = st.slider(
                "Рейтинг Overall (%)",
                min_value=0,
                max_value=100,
                value=(0, 100),
                step=5,
                key="filter_score"
            )
            min_score, max_score = score_range
            
            # Поиск по имени
            search_query = st.text_input(
                "🔎 Поиск по имени",
                placeholder="Введите имя кандидата...",
                key="filter_search"
            )
        
        # Фильтр по дате
        col3, col4 = st.columns(2)
        
        with col3:
            use_date_filter = st.checkbox("Фильтр по дате", value=False)
        
        date_from = None
        date_to = None
        
        if use_date_filter:
            with col3:
                date_from = st.date_input(
                    "С даты",
                    value=datetime.now() - timedelta(days=30),
                    key="filter_date_from"
                )
                if date_from:
                    date_from = datetime.combine(date_from, datetime.min.time())
            
            with col4:
                date_to = st.date_input(
                    "По дату",
                    value=datetime.now(),
                    key="filter_date_to"
                )
                if date_to:
                    date_to = datetime.combine(date_to, datetime.max.time())
        
        # Кнопка сброса фильтров
        if st.button("🔄 Сбросить фильтры"):
            # Очищаем session state
            for key in list(st.session_state.keys()):
                if key.startswith('filter_'):
                    del st.session_state[key]
            st.rerun()
    
    return {
        'vacancy_id': vacancy_id,
        'min_score': min_score,
        'max_score': max_score,
        'recommendation': recommendation,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to
    }


def show_filter_summary(filters: Dict[str, Any], total_count: int, filtered_count: int):
    """
    Показывает краткую сводку активных фильтров
    
    Args:
        filters: Словарь с параметрами фильтрации
        total_count: Общее количество кандидатов
        filtered_count: Количество после фильтрации
    """
    active_filters = []
    
    if filters['vacancy_id']:
        active_filters.append(f"Вакансия: ID {filters['vacancy_id']}")
    
    if filters['min_score'] > 0 or filters['max_score'] < 100:
        active_filters.append(f"Рейтинг: {filters['min_score']}-{filters['max_score']}%")
    
    if filters['recommendation']:
        rec_names = {"YES": "Принять", "NO": "Отклонить", "MAYBE": "Уточнить"}
        active_filters.append(f"Решение: {rec_names[filters['recommendation']]}")
    
    if filters['search_query']:
        active_filters.append(f"Поиск: '{filters['search_query']}'")
    
    if filters['date_from'] or filters['date_to']:
        active_filters.append("Фильтр по дате активен")
    
    if active_filters:
        st.info(f"🔍 **Активные фильтры:** {' | '.join(active_filters)}")
    
    st.caption(f"Показано {filtered_count} из {total_count} кандидатов")
