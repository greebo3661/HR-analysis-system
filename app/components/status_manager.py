"""Компонент для управления статусами кандидатов"""
import streamlit as st
from datetime import datetime
from db.models import SessionLocal, Match, StatusHistory

# Доступные статусы
STATUS_CONFIG = {
    "new": {
        "label": "🆕 Новый",
        "color": "#17a2b8",
        "description": "Резюме получено, не просмотрено"
    },
    "review": {
        "label": "👀 На рассмотрении",
        "color": "#ffc107",
        "description": "Резюме в процессе оценки"
    },
    "interview": {
        "label": "📞 Интервью",
        "color": "#007bff",
        "description": "Назначено или проведено интервью"
    },
    "offer": {
        "label": "✅ Оффер",
        "color": "#28a745",
        "description": "Предложение о работе отправлено"
    },
    "rejected": {
        "label": "❌ Отказ",
        "color": "#dc3545",
        "description": "Кандидат отклонён"
    },
    "reserve": {
        "label": "📦 Резерв",
        "color": "#6c757d",
        "description": "Сохранён в резерв на будущее"
    }
}

def get_status_label(status_key: str) -> str:
    """Возвращает красивый label для статуса"""
    return STATUS_CONFIG.get(status_key, {}).get("label", status_key)

def get_status_color(status_key: str) -> str:
    """Возвращает цвет для статуса"""
    return STATUS_CONFIG.get(status_key, {}).get("color", "#6c757d")

def render_status_badge(status_key: str):
    """Отображает красивый бейдж статуса"""
    config = STATUS_CONFIG.get(status_key, {})
    label = config.get("label", status_key)
    color = config.get("color", "#6c757d")
    
    st.markdown(
        f"""<span style="background-color: {color}; color: white; padding: 4px 12px; 
        border-radius: 12px; font-size: 14px; font-weight: 500;">{label}</span>""",
        unsafe_allow_html=True
    )

def render_status_selector(match_id: int, current_status: str):
    """
    Рендерит селектор для изменения статуса
    
    Args:
        match_id: ID кандидата
        current_status: Текущий статус
    """
    st.markdown("### Изменить статус")
    
    # Создаём список опций
    status_options = {config["label"]: key for key, config in STATUS_CONFIG.items()}
    
    current_label = STATUS_CONFIG[current_status]["label"]
    
    selected_label = st.selectbox(
        "Новый статус",
        list(status_options.keys()),
        index=list(status_options.keys()).index(current_label),
        key=f"status_selector_{match_id}"
    )
    
    new_status = status_options[selected_label]
    
    if new_status != current_status:
        if st.button("💾 Сохранить статус", key=f"save_status_{match_id}"):
            change_status(match_id, current_status, new_status)
            st.success(f"Статус изменён: {STATUS_CONFIG[new_status]['label']}")
            st.rerun()

def change_status(match_id: int, old_status: str, new_status: str):
    """
    Изменяет статус кандидата и сохраняет в историю
    
    Args:
        match_id: ID кандидата
        old_status: Старый статус
        new_status: Новый статус
    """
    db = SessionLocal()
    
    # Обновляем статус
    match = db.query(Match).filter(Match.id == match_id).first()
    if match:
        match.status = new_status
        match.status_updated_at = datetime.utcnow()
        
        # Сохраняем историю
        history = StatusHistory(
            match_id=match_id,
            old_status=old_status,
            new_status=new_status,
            changed_at=datetime.utcnow()
        )
        db.add(history)
        db.commit()
    
    db.close()

def render_status_history(match_id: int):
    """
    Отображает историю смены статусов
    
    Args:
        match_id: ID кандидата
    """
    db = SessionLocal()
    history = db.query(StatusHistory).filter(
        StatusHistory.match_id == match_id
    ).order_by(StatusHistory.changed_at.desc()).all()
    db.close()
    
    if not history:
        st.info("История статусов пуста")
        return
    
    st.markdown("### 📜 История статусов")
    
    for h in history:
        old_label = STATUS_CONFIG.get(h.old_status, {}).get("label", h.old_status) if h.old_status else "—"
        new_label = STATUS_CONFIG.get(h.new_status, {}).get("label", h.new_status)
        date_str = h.changed_at.strftime("%d.%m.%Y %H:%M")
        
        st.markdown(f"**{date_str}:** {old_label} → {new_label}")

def get_status_counts(matches: list) -> dict:
    """
    Подсчитывает количество кандидатов в каждом статусе
    
    Args:
        matches: Список объектов Match
    
    Returns:
        Словарь {status_key: count}
    """
    counts = {key: 0 for key in STATUS_CONFIG.keys()}
    
    for m in matches:
        status = getattr(m, 'status', 'new')
        if status in counts:
            counts[status] += 1
        else:
            counts['new'] += 1  # fallback для старых записей
    
    return counts

def render_status_overview(matches: list):
    """
    Отображает сводку по статусам (воронка)
    
    Args:
        matches: Список объектов Match
    """
    counts = get_status_counts(matches)
    
    st.markdown("### 📊 Воронка найма")
    
    cols = st.columns(len(STATUS_CONFIG))
    
    for i, (key, config) in enumerate(STATUS_CONFIG.items()):
        with cols[i]:
            count = counts[key]
            st.metric(
                label=config["label"],
                value=count,
                help=config["description"]
            )
