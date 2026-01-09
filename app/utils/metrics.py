"""Утилиты для расчёта аналитических метрик"""
from typing import List, Dict, Any
from collections import Counter
from datetime import datetime, timedelta
import json
from db.models import Match

def calculate_funnel_metrics(matches: List[Match]) -> Dict[str, int]:
    """
    Рассчитывает метрики воронки найма
    
    Returns:
        Dict с количеством кандидатов на каждом этапе
    """
    from components.status_manager import STATUS_CONFIG
    
    counts = {key: 0 for key in STATUS_CONFIG.keys()}
    
    for m in matches:
        status = getattr(m, 'status', 'new')
        if status in counts:
            counts[status] += 1
        else:
            counts['new'] += 1
    
    return counts

def calculate_conversion_rate(matches: List[Match]) -> Dict[str, float]:
    """
    Рассчитывает конверсию между этапами воронки
    
    Returns:
        Dict с процентом конверсии
    """
    total = len(matches)
    if total == 0:
        return {}
    
    metrics = calculate_funnel_metrics(matches)
    
    conversion = {
        'new_to_review': (metrics['review'] / total * 100) if total > 0 else 0,
        'review_to_interview': (metrics['interview'] / total * 100) if total > 0 else 0,
        'interview_to_offer': (metrics['offer'] / total * 100) if total > 0 else 0,
        'overall_success': (metrics['offer'] / total * 100) if total > 0 else 0,
        'rejection_rate': (metrics['rejected'] / total * 100) if total > 0 else 0
    }
    
    return conversion

def get_average_scores_by_vacancy(matches: List[Match]) -> Dict[str, Dict[str, float]]:
    """
    Средние оценки по вакансиям
    
    Returns:
        Dict {vacancy_title: {metric: score}}
    """
    vacancy_scores = {}
    
    for m in matches:
        vacancy = m.vacancy_title
        
        if vacancy not in vacancy_scores:
            vacancy_scores[vacancy] = {
                'overall': [],
                'hard_skills': [],
                'experience': [],
                'count': 0
            }
        
        vacancy_scores[vacancy]['overall'].append(m.score)
        vacancy_scores[vacancy]['count'] += 1
        
        # Извлекаем доп. метрики из JSON
        try:
            analysis = json.loads(m.analysis_json)
            hs = analysis['matching_score'].get('hard_skills', 0)
            exp = analysis['matching_score'].get('experience', 0)
            
            vacancy_scores[vacancy]['hard_skills'].append(hs)
            vacancy_scores[vacancy]['experience'].append(exp)
        except:
            pass
    
    # Считаем средние
    result = {}
    for vacancy, scores in vacancy_scores.items():
        result[vacancy] = {
            'overall': sum(scores['overall']) / len(scores['overall']) if scores['overall'] else 0,
            'hard_skills': sum(scores['hard_skills']) / len(scores['hard_skills']) if scores['hard_skills'] else 0,
            'experience': sum(scores['experience']) / len(scores['experience']) if scores['experience'] else 0,
            'count': scores['count']
        }
    
    return result

def get_top_missing_skills(matches: List[Match], top_n: int = 10) -> List[tuple]:
    """
    ТОП недостающих навыков
    
    Returns:
        List[(skill, count)]
    """
    all_missing = []
    
    for m in matches:
        try:
            analysis = json.loads(m.analysis_json)
            missing = analysis.get('missing_skills', [])
            all_missing.extend(missing)
        except:
            pass
    
    counter = Counter(all_missing)
    return counter.most_common(top_n)

def get_recommendation_distribution(matches: List[Match]) -> Dict[str, int]:
    """
    Распределение решений (Принять/Отклонить/Уточнить)
    
    Returns:
        Dict {recommendation: count}
    """
    recommendations = {'YES': 0, 'NO': 0, 'MAYBE': 0}
    
    for m in matches:
        try:
            analysis = json.loads(m.analysis_json)
            rec = analysis.get('recommendation', 'MAYBE')
            if rec in recommendations:
                recommendations[rec] += 1
        except:
            pass
    
    return recommendations

def get_candidates_by_date(matches: List[Match], days: int = 30) -> Dict[str, int]:
    """
    Количество кандидатов по дням
    
    Args:
        days: За сколько последних дней считать
    
    Returns:
        Dict {date_str: count}
    """
    from datetime import date
    
    today = datetime.now().date()
    date_counts = {}
    
    for m in matches:
        if hasattr(m, 'created_at'):
            m_date = m.created_at.date()
            
            # Только за последние N дней
            if (today - m_date).days <= days:
                date_str = m_date.strftime('%d.%m')
                date_counts[date_str] = date_counts.get(date_str, 0) + 1
    
    return date_counts

def get_time_to_decision_stats(matches: List[Match]) -> Dict[str, Any]:
    """
    Статистика времени от подачи резюме до решения
    
    Returns:
        Dict с метриками времени
    """
    times = []
    
    for m in matches:
        status = getattr(m, 'status', 'new')
        
        # Считаем только для завершённых (offer, rejected)
        if status in ['offer', 'rejected']:
            created = getattr(m, 'created_at', None)
            updated = getattr(m, 'status_updated_at', None)
            
            if created and updated:
                delta = (updated - created).total_seconds() / 3600  # в часах
                times.append(delta)
    
    if not times:
        return {'avg_hours': 0, 'min_hours': 0, 'max_hours': 0, 'count': 0}
    
    return {
        'avg_hours': sum(times) / len(times),
        'min_hours': min(times),
        'max_hours': max(times),
        'count': len(times)
    }
