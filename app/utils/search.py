"""Утилиты для фильтрации и поиска кандидатов"""
from datetime import datetime
from typing import List, Optional
from db.models import Match
import json

def filter_matches(
    matches: List[Match],
    vacancy_id: Optional[int] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    recommendation: Optional[str] = None,
    search_query: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> List[Match]:
    """
    Фильтрует список кандидатов по заданным параметрам
    
    Args:
        matches: Список объектов Match из БД
        vacancy_id: ID вакансии (None = все вакансии)
        min_score: Минимальный рейтинг (0-100)
        max_score: Максимальный рейтинг (0-100)
        recommendation: Фильтр по решению ("YES", "NO", "MAYBE")
        search_query: Поиск по имени кандидата
        date_from: Начало периода
        date_to: Конец периода
    
    Returns:
        Отфильтрованный список Match
    """
    filtered = matches
    
    # Фильтр по вакансии
    if vacancy_id is not None:
        filtered = [m for m in filtered if m.vacancy_id == vacancy_id]
    
    # Фильтр по рейтингу
    if min_score is not None:
        filtered = [m for m in filtered if m.score >= min_score]
    
    if max_score is not None:
        filtered = [m for m in filtered if m.score <= max_score]
    
    # Фильтр по решению
    if recommendation:
        filtered = [
            m for m in filtered 
            if json.loads(m.analysis_json).get('recommendation') == recommendation
        ]
    
    # Поиск по имени
    if search_query and search_query.strip():
        query_lower = search_query.lower().strip()
        filtered = [
            m for m in filtered 
            if query_lower in m.resume_name.lower()
        ]
    
    # Фильтр по дате
    if date_from:
        filtered = [m for m in filtered if m.created_at >= date_from]
    
    if date_to:
        filtered = [m for m in filtered if m.created_at <= date_to]
    
    return filtered
