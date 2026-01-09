"""Компонент для работы с комментариями"""
import streamlit as st
import json
from datetime import datetime
from db.models import SessionLocal, Comment

def render_comments(match_id: int):
    """
    Отображает комментарии и форму добавления
    
    Args:
        match_id: ID кандидата
    """
    st.markdown("### 💬 Комментарии и заметки")
    
    # Форма добавления комментария
    with st.form(f"comment_form_{match_id}", clear_on_submit=True):
        comment_text = st.text_area(
            "Добавить комментарий",
            placeholder="Результаты звонка, впечатления, заметки...",
            height=100
        )
        
        tags_input = st.text_input(
            "Теги (через запятую)",
            placeholder="#срочно, #перспективный, #запасной"
        )
        
        if st.form_submit_button("💾 Сохранить комментарий"):
            if comment_text.strip():
                add_comment(match_id, comment_text, tags_input)
                st.success("Комментарий добавлен")
                st.rerun()
            else:
                st.error("Введите текст комментария")
    
    # Список комментариев
    db = SessionLocal()
    comments = db.query(Comment).filter(
        Comment.match_id == match_id
    ).order_by(Comment.created_at.desc()).all()
    db.close()
    
    if not comments:
        st.info("Комментариев пока нет")
        return
    
    st.divider()
    
    for c in comments:
        with st.container():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                date_str = c.created_at.strftime("%d.%m.%Y %H:%M")
                st.markdown(f"**{date_str}**")
                st.write(c.text)
                
                # Теги
                if c.tags:
                    try:
                        tags = json.loads(c.tags)
                        if tags:
                            tags_html = " ".join([
                                f'<span style="background: #e3f2fd; color: #1976d2; padding: 2px 8px; '
                                f'border-radius: 8px; font-size: 12px; margin-right: 4px;">{tag}</span>'
                                for tag in tags
                            ])
                            st.markdown(tags_html, unsafe_allow_html=True)
                    except:
                        pass
            
            with col2:
                if st.button("🗑️", key=f"del_comment_{c.id}", help="Удалить комментарий"):
                    delete_comment(c.id)
                    st.rerun()
            
            st.divider()

def add_comment(match_id: int, text: str, tags_input: str = ""):
    """
    Добавляет комментарий к кандидату
    
    Args:
        match_id: ID кандидата
        text: Текст комментария
        tags_input: Строка с тегами через запятую
    """
    db = SessionLocal()
    
    # Парсим теги
    tags = []
    if tags_input.strip():
        tags = [
            tag.strip() 
            for tag in tags_input.split(",") 
            if tag.strip()
        ]
    
    comment = Comment(
        match_id=match_id,
        text=text,
        tags=json.dumps(tags, ensure_ascii=False) if tags else None,
        created_at=datetime.utcnow()
    )
    
    db.add(comment)
    db.commit()
    db.close()

def delete_comment(comment_id: int):
    """Удаляет комментарий"""
    db = SessionLocal()
    db.query(Comment).filter(Comment.id == comment_id).delete()
    db.commit()
    db.close()
