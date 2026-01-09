# app/components/kanban.py
"""Kanban доска для управления кандидатами"""
import streamlit as st
from typing import List
from db.models import SessionLocal, Match
from components.status_manager import STATUS_CONFIG, change_status
import json

def render_kanban_board(matches: List[Match]):
    """
    Рендерит Kanban доску с кандидатами
    
    Args:
        matches: Список всех кандидатов
    """
    st.markdown("### 📋 Kanban доска")
    
    # Группируем кандидатов по статусам
    grouped = {key: [] for key in STATUS_CONFIG.keys()}
    
    for m in matches:
        status = getattr(m, 'status', 'new')
        if status in grouped:
            grouped[status].append(m)
        else:
            grouped['new'].append(m)
    
    # Создаём колонки для каждого статуса
    cols = st.columns(len(STATUS_CONFIG))
    
    for i, (status_key, config) in enumerate(STATUS_CONFIG.items()):
        with cols[i]:
            # Заголовок колонки
            count = len(grouped[status_key])
            st.markdown(
                f"""<div style="background: {config['color']}; color: white; padding: 10px; 
                border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 10px;">
                {config['label']}<br><span style="font-size: 24px;">{count}</span>
                </div>""",
                unsafe_allow_html=True
            )
            
            # Карточки кандидатов
            for m in grouped[status_key]:
                render_candidate_card(m, status_key)

def render_candidate_card(match: Match, current_status: str):
    """Рендерит карточку кандидата в Kanban"""
    
    analysis = json.loads(match.analysis_json)
    score = match.score
    rec = analysis.get('recommendation', 'MAYBE')
    
    # Цвет карточки по рекомендации
    card_colors = {
        'YES': '#d4edda',
        'NO': '#f8d7da',
        'MAYBE': '#fff3cd'
    }
    card_color = card_colors.get(rec, '#f8f9fa')
    
    with st.container():
        st.markdown(
            f"""<div style="background: {card_color}; padding: 12px; border-radius: 8px; 
            margin-bottom: 8px; border-left: 4px solid #0066cc;">
            <strong>{match.resume_name}</strong><br>
            <small>{match.vacancy_title}</small><br>
            <span style="font-size: 18px; font-weight: bold; color: #0066cc;">{score}%</span>
            </div>""",
            unsafe_allow_html=True
        )
        
        # Кнопки действий
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("👁️", key=f"kanban_view_{match.id}", help="Открыть"):
                st.session_state['selected_match_id'] = match.id
                st.session_state['switch_to_results'] = True
                st.rerun()
        
        with col2:
            # Меню быстрой смены статуса
            status_labels = {key: STATUS_CONFIG[key]['label'] for key in STATUS_CONFIG.keys()}
            
            new_status = st.selectbox(
                "Статус",
                list(STATUS_CONFIG.keys()),
                format_func=lambda x: status_labels[x],
                index=list(STATUS_CONFIG.keys()).index(current_status),
                key=f"kanban_status_{match.id}",
                label_visibility="collapsed"
            )
            
            if new_status != current_status:
                change_status(match.id, current_status, new_status)
                st.rerun()
        
        with col3:
            if st.button("📊", key=f"kanban_compare_{match.id}", help="Добавить к сравнению"):
                if 'comparison_candidates' not in st.session_state:
                    st.session_state['comparison_candidates'] = []
                
                if match.id not in st.session_state['comparison_candidates']:
                    if len(st.session_state['comparison_candidates']) >= 3:
                        st.warning("Максимум 3 кандидата для сравнения")
                    else:
                        st.session_state['comparison_candidates'].append(match.id)
                        st.success("Добавлен к сравнению")
                        st.rerun()
                else:
                    st.session_state['comparison_candidates'].remove(match.id)
                    st.rerun()
        
        # Индикатор выбора для сравнения
        if 'comparison_candidates' in st.session_state:
            if match.id in st.session_state['comparison_candidates']:
                st.markdown("✅ **Выбран для сравнения**")
