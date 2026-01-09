"""Модуль сравнения кандидатов"""
import streamlit as st
import json
from typing import List
from db.models import Match
import plotly.graph_objects as go

def render_comparison_view(matches: List[Match]):
    """
    Рендерит сравнение выбранных кандидатов
    
    Args:
        matches: Список кандидатов для сравнения (макс 3)
    """
    if not matches:
        st.info("Выберите кандидатов для сравнения на Kanban доске")
        return
    
    if len(matches) > 3:
        st.warning("Максимум 3 кандидата одновременно")
        matches = matches[:3]
    
    st.markdown(f"### 🔍 Сравнение кандидатов ({len(matches)})")
    
    # Кнопка очистки
    if st.button("🗑️ Очистить выбор"):
        st.session_state['comparison_candidates'] = []
        st.rerun()
    
    st.divider()
    
    # Базовая информация
    cols = st.columns(len(matches))
    
    for i, m in enumerate(matches):
        with cols[i]:
            st.markdown(f"#### {m.resume_name}")
            st.write(f"**Вакансия:** {m.vacancy_title}")
            st.metric("Overall Score", f"{m.score}%")
    
    st.divider()
    
    # Радарная диаграмма метрик
    render_radar_chart(matches)
    
    st.divider()
    
    # Таблица детального сравнения
    render_comparison_table(matches)
    
    st.divider()
    
    # Сравнение текстовых полей
    render_text_comparison(matches)

def render_radar_chart(matches: List[Match]):
    """Радарная диаграмма сравнения метрик"""
    
    st.markdown("#### Сравнение по критериям")
    
    categories = ['Hard Skills', 'Experience', 'Cultural Fit', 'Communication', 'Growth Potential', 'Stability']
    
    fig = go.Figure()
    
    colors = ['#0066cc', '#28a745', '#ffc107']
    
    for idx, m in enumerate(matches):
        analysis = json.loads(m.analysis_json)
        scores = analysis['matching_score']
        
        values = [
            scores.get('hard_skills', 0),
            scores.get('experience', 0),
            scores.get('cultural_fit', 0),
            scores.get('communication', 0),
            scores.get('growth_potential', 0),
            scores.get('stability', 0)
        ]
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=m.resume_name,
            line=dict(color=colors[idx % len(colors)])
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        ),
        showlegend=True,
        height=500,
        template="plotly_dark"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_comparison_table(matches: List[Match]):
    """Таблица сравнения"""
    
    st.markdown("#### Детальное сравнение")
    
    # Формируем данные для таблицы
    table_data = []
    
    criteria = [
        ('Overall', 'overall'),
        ('Hard Skills', 'hard_skills'),
        ('Experience', 'experience'),
        ('Cultural Fit', 'cultural_fit'),
        ('Communication', 'communication'),
        ('Growth Potential', 'growth_potential'),
        ('Stability', 'stability')
    ]
    
    for crit_name, crit_key in criteria:
        row = {'Критерий': crit_name}
        
        for m in matches:
            analysis = json.loads(m.analysis_json)
            score = analysis['matching_score'].get(crit_key, 0)
            row[m.resume_name] = f"{score}%"
        
        table_data.append(row)
    
    # Добавляем рекомендацию
    rec_row = {'Критерий': 'Рекомендация'}
    rec_map = {"YES": "✅ Принять", "NO": "❌ Отклонить", "MAYBE": "🔍 Уточнить"}
    
    for m in matches:
        analysis = json.loads(m.analysis_json)
        rec = analysis.get('recommendation', 'MAYBE')
        rec_row[m.resume_name] = rec_map.get(rec, rec)
    
    table_data.append(rec_row)
    
    # ИСПРАВЛЕНО: use_container_width вместо width='stretch'
    st.dataframe(table_data, use_container_width=True)

def render_text_comparison(matches: List[Match]):
    """Сравнение текстовых полей"""
    
    st.markdown("#### Качественное сравнение")
    
    fields = [
        ('💪 Сильные стороны', 'strengths', '#d4edda'),
        ('⚠️ Слабые стороны', 'weaknesses', '#fff3cd'),
        ('❌ Недостающие навыки', 'missing_skills', '#f8d7da'),
        ('🚩 Риски', 'red_flags', '#f8d7da')
    ]
    
    for field_name, field_key, bg_color in fields:
        st.markdown(f"**{field_name}:**")
        
        cols = st.columns(len(matches))
        
        for i, m in enumerate(matches):
            with cols[i]:
                st.markdown(f"<div style='background: {bg_color}; padding: 10px; border-radius: 5px; min-height: 100px;'>", unsafe_allow_html=True)
                
                analysis = json.loads(m.analysis_json)
                items = analysis.get(field_key, [])
                
                if items:
                    for item in items:
                        st.write(f"• {item}")
                else:
                    st.write("—")
                
                st.markdown("</div>", unsafe_allow_html=True)
        
        st.divider()
