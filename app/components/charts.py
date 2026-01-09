"""Компонент для визуализации данных"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List
from components.status_manager import STATUS_CONFIG

def render_funnel_chart(metrics: Dict[str, int]):
    """Воронка найма"""
    
    labels = [STATUS_CONFIG[key]['label'] for key in metrics.keys()]
    values = list(metrics.values())
    
    fig = go.Figure(go.Funnel(
        y=labels,
        x=values,
        textinfo="value+percent initial",
        marker=dict(color=[STATUS_CONFIG[key]['color'] for key in metrics.keys()])
    ))
    
    fig.update_layout(
        title="Воронка найма",
        height=400,
        template="plotly_dark"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_score_distribution(matches: list):
    """Распределение оценок"""
    
    scores = [m.score for m in matches]
    
    fig = go.Figure(data=[go.Histogram(
        x=scores,
        nbinsx=20,
        marker_color='#0066cc'
    )])
    
    fig.update_layout(
        title="Распределение оценок Overall",
        xaxis_title="Оценка (%)",
        yaxis_title="Количество кандидатов",
        height=350,
        template="plotly_dark"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_vacancy_comparison(vacancy_scores: Dict[str, Dict[str, float]]):
    """Сравнение вакансий по средним оценкам"""
    
    vacancies = list(vacancy_scores.keys())
    overall = [v['overall'] for v in vacancy_scores.values()]
    hard_skills = [v['hard_skills'] for v in vacancy_scores.values()]
    experience = [v['experience'] for v in vacancy_scores.values()]
    
    fig = go.Figure(data=[
        go.Bar(name='Overall', x=vacancies, y=overall, marker_color='#0066cc'),
        go.Bar(name='Hard Skills', x=vacancies, y=hard_skills, marker_color='#28a745'),
        go.Bar(name='Experience', x=vacancies, y=experience, marker_color='#ffc107')
    ])
    
    fig.update_layout(
        title="Средние оценки по вакансиям",
        xaxis_title="Вакансия",
        yaxis_title="Средняя оценка (%)",
        barmode='group',
        height=400,
        template="plotly_dark"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_missing_skills_chart(top_skills: List[tuple]):
    """ТОП недостающих навыков"""
    
    if not top_skills:
        st.info("Нет данных о недостающих навыках")
        return
    
    skills = [s[0] for s in top_skills]
    counts = [s[1] for s in top_skills]
    
    fig = go.Figure(go.Bar(
        x=counts,
        y=skills,
        orientation='h',
        marker_color='#dc3545'
    ))
    
    fig.update_layout(
        title="ТОП-10 недостающих навыков",
        xaxis_title="Количество кандидатов",
        yaxis_title="Навык",
        height=400,
        template="plotly_dark"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_recommendation_pie(recommendations: Dict[str, int]):
    """Распределение решений"""
    
    labels = {
        'YES': '✅ Принять',
        'NO': '❌ Отклонить',
        'MAYBE': '🔍 Уточнить'
    }
    
    fig = go.Figure(data=[go.Pie(
        labels=[labels[k] for k in recommendations.keys()],
        values=list(recommendations.values()),
        marker=dict(colors=['#28a745', '#dc3545', '#ffc107']),
        hole=0.4
    )])
    
    fig.update_layout(
        title="Распределение решений",
        height=350,
        template="plotly_dark"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_timeline_chart(date_counts: Dict[str, int]):
    """Динамика поступления резюме"""
    
    if not date_counts:
        st.info("Нет данных за выбранный период")
        return
    
    dates = list(date_counts.keys())
    counts = list(date_counts.values())
    
    fig = go.Figure(data=go.Scatter(
        x=dates,
        y=counts,
        mode='lines+markers',
        line=dict(color='#0066cc', width=2),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title="Поступление резюме по дням",
        xaxis_title="Дата",
        yaxis_title="Количество",
        height=300,
        template="plotly_dark"
    )
    
    st.plotly_chart(fig, use_container_width=True)
