# app/config.py
import os

LLM_MANAGER_URL = os.getenv("LLM_MANAGER_URL", "http://192.168.149.194:8000")
LLM_API_KEY = os.getenv("LLM_API_KEY", "rs-5kjsdfh25knnl2j345lnkjsdfs692lksdfl3ff")

# Доступные модели
AVAILABLE_MODELS = {
    "a-vibe": {
        "name": "A-VIBE",
        "description": "Универсальная модель для анализа резюме",
        "model_id": "a-vibe"
    },
    "qwen3-14b": {
        "name": "Qwen3-14B",
        "description": "Быстрая модель с хорошей точностью",
        "model_id": "qwen3-14b"
    },
    "qwen2.5-coder-14b": {
        "name": "Qwen2.5-Coder-14B",
        "description": "Специализирована на технических навыках и коде",
        "model_id": "qwen2.5-coder-14b"
    }
}

DEFAULT_MODEL = "a-vibe"

def load_system_prompt():
    try:
        with open('/app/prompts/system_prompt.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "You are an HR analysis assistant."

def load_hr_guidelines():
    try:
        with open('/app/prompts/hr_guidelines.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""

def get_selected_model():
    """Получает выбранную модель из session_state или дефолтную"""
    import streamlit as st
    return st.session_state.get('selected_model', DEFAULT_MODEL)

def set_selected_model(model_key: str):
    """Сохраняет выбранную модель в session_state"""
    import streamlit as st
    if model_key in AVAILABLE_MODELS:
        st.session_state['selected_model'] = model_key
        return True
    return False
