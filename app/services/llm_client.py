# app/services/llm_client.py
import requests
import json
import time
import re
from typing import Dict, Any
from config import (
    LLM_MANAGER_URL,
    LLM_API_KEY,
    load_system_prompt,
    load_hr_guidelines,
    AVAILABLE_MODELS,
    get_selected_model
)

class LLMClient:
    def __init__(self):
        self.base_url = LLM_MANAGER_URL
        self.api_key = LLM_API_KEY
        self.system_prompt = load_system_prompt()
        self.hr_guidelines = load_hr_guidelines()

    def _get_model_config(self):
        """Получает конфигурацию текущей выбранной модели"""
        model_key = get_selected_model()
        return AVAILABLE_MODELS.get(model_key, AVAILABLE_MODELS['a-vibe'])

    def _switch_model(self, model_id: str):
        """Переключает активную модель в оркестраторе"""
        try:
            url = f"{self.base_url}/switch/{model_id}"
            headers = {"Authorization": f"Bearer {self.api_key}"}

            print(f"🔄 Переключаюсь на модель {model_id}...")
            response = requests.post(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            switch_data = response.json()
            print(f"✓ Ответ switch: {switch_data}")

            return True

        except Exception as e:
            print(f"❌ Ошибка переключения модели: {str(e)}")
            return False

    def _call_llm(self, user_prompt: str, temperature: float = 0.3, max_retries: int = 3) -> str:
        model_config = self._get_model_config()
        model_id = model_config['model_id']

        # Переключаемся на модель
        self._switch_model(model_id)
        
        # Ждём загрузки - для 14B моделей значительно дольше
        wait_time = 15 if '14b' in model_id.lower() else 4
        print(f"⏳ Ждём загрузки модели ({wait_time} сек)...")
        time.sleep(wait_time)

        url = f"{self.base_url}/v1/chat/completions"

        # Увеличиваем max_tokens чтобы JSON не обрезался
        payload = {
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": 8000
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # Ретраи при 503 (модель грузится)
        for attempt in range(max_retries):
            try:
                print(f"🚀 Отправляю запрос к LLM (попытка {attempt + 1}/{max_retries})...")
                response = requests.post(url, json=payload, headers=headers, timeout=240)
                
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                
                result = response.json()
                
                # Проверяем структуру
                if 'choices' not in result or not result['choices']:
                    # Если 503 - модель ещё грузится
                    if 'error' in result and result['error'].get('code') == 503:
                        if attempt < max_retries - 1:
                            wait = (attempt + 1) * 10  # 10, 20, 30 сек
                            print(f"⚠️ Модель ещё грузится, жду {wait} сек...")
                            time.sleep(wait)
                            continue
                    raise ValueError(f"Invalid response structure. Response: {result}")
                
                print(f"✅ Получен ответ от LLM")
                return result['choices'][0]['message']['content']
                
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"⏱️ Таймаут, повтор...")
                    time.sleep(5)
                    continue
                raise
            except Exception as e:
                if attempt < max_retries - 1 and "503" in str(e):
                    print(f"⚠️ Ошибка 503, повтор через 10 сек...")
                    time.sleep(10)
                    continue
                raise

        raise Exception("Все попытки вызова LLM исчерпаны")

    def call_llm(self, user_prompt: str, temperature: float = 0.3) -> str:
        """Публичный метод для вызова LLM"""
        return self._call_llm(user_prompt, temperature)

    def _clean_json_text(self, text: str) -> str:
        """Очищает текст от мусора перед парсингом JSON"""
        # Убираем однострочные комментарии // (для coder-моделей)
        text = re.sub(r'//[^\n]*\n', '\n', text)
        
        # Убираем многострочные комментарии /* */
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        
        return text

    def _extract_json(self, text: str) -> dict:
        """Извлекает и парсит JSON из ответа LLM"""
        
        # DEBUG: Сохраняем сырой ответ
        print("=" * 60)
        print("DEBUG: Сырой ответ LLM (первые 500 символов):")
        print(text[:500])
        print("=" * 60)
        
        clean = text.strip()
        
        # Убираем markdown блоки
        if '```json' in clean:
            clean = clean.split('```json', 1)[1]
        if clean.startswith('```'):
            clean = clean[3:]
        if clean.endswith('```'):
            clean = clean[:-3]
        
        clean = clean.strip()
        
        # Очищаем от комментариев (для coder-моделей)
        clean = self._clean_json_text(clean)
        
        # Ищем начало JSON - может быть { или [
        json_start = -1
        json_start_char = None
        
        for char in ['{', '[']:
            # Ищем первое вхождение в первых 500 символах
            pos = clean.find(char)
            if pos != -1 and pos < 500:
                if json_start == -1 or pos < json_start:
                    json_start = pos
                    json_start_char = char
        
        # Если не нашли в первых 500 - ищем последнее (reasoning-модели)
        if json_start == -1:
            for char in ['{', '[']:
                pos = clean.rfind(char)
                if pos != -1:
                    if json_start == -1 or pos > json_start:
                        json_start = pos
                        json_start_char = char
        
        if json_start == -1:
            print(f"❌ DEBUG: Не найдено начало JSON. Весь текст:\n{clean}")
            raise ValueError(f"Не найдены границы JSON в ответе")
        
        # Определяем конечный символ в зависимости от начального
        if json_start_char == '{':
            json_end = clean.rfind('}') + 1
        else:  # '['
            json_end = clean.rfind(']') + 1
        
        if json_end == 0 or json_end <= json_start:
            print(f"❌ DEBUG: Не найден конец JSON. json_start={json_start}, json_end={json_end}")
            raise ValueError(f"Не найден конец JSON")
        
        json_str = clean[json_start:json_end]
        
        print(f"DEBUG: Извлечённый JSON (длина {len(json_str)}, первые 300 символов):")
        print(json_str[:300])
        print("=" * 60)
        
        try:
            result = json.loads(json_str)
            
            # Если LLM вернул массив - берём первый элемент
            if isinstance(result, list):
                if not result:
                    raise ValueError("Пустой массив в ответе LLM")
                result = result[0]
            
            return result
        except json.JSONDecodeError as e:
            # Попытка автофикса распространённых ошибок
            print(f"⚠️ JSON поврежден, пытаюсь починить: {str(e)}")
            
            # 1. Убираем trailing commas
            fixed = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            # 2. Экранируем неэкранированные переносы строк в значениях
            # Ищем строки вида: "key": "value с переносом
            # и заменяем переносы на \n
            def fix_multiline_strings(match):
                key = match.group(1)
                value = match.group(2)
                # Заменяем реальные переносы на \n
                value = value.replace('\n', '\\n').replace('\r', '')
                return f'"{key}": "{value}"'
            
            # Паттерн для строковых значений
            fixed = re.sub(r'"([^"]+)":\s*"([^"]*(?:\n[^"]*)*)"', fix_multiline_strings, fixed)
            
            # 3. Добавляем кавычки к ключам без них
            fixed = re.sub(r'(\w+)(\s*):', r'"\1"\2:', fixed)
            
            # 4. Убираем одинарные кавычки
            fixed = fixed.replace("'", '"')
            
            print(f"DEBUG: Попытка починить JSON...")
            
            try:
                result = json.loads(fixed)
                print(f"✓ JSON починен автоматически")
                
                if isinstance(result, list):
                    result = result[0] if result else {}
                
                return result
            except Exception as repair_error:
                print(f"❌ Автофикс не помог: {repair_error}")
                print(f"DEBUG: Фрагмент JSON (последние 500 символов):")
                print(json_str[-500:])
                raise ValueError(f"Не удалось распарсить JSON: {str(e)}")

    def analyze_resume(self, resume_data: Dict[str, Any], vacancy_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
Проанализируй резюме кандидата относительно требований вакансии.

HR Guidelines:
{self.hr_guidelines}

Вакансия:
{json.dumps(vacancy_data, ensure_ascii=False, indent=2)}

Резюме:
{json.dumps(resume_data, ensure_ascii=False, indent=2)}

Верни результат СТРОГО в формате JSON (без markdown блоков, без комментариев):
{{
    "matching_score": {{
        "overall": <число 0-100>,
        "hard_skills": <число 0-100>,
        "hard_skills_reasoning": "<объяснение оценки БЕЗ переносов строк>",
        "experience": <число 0-100>,
        "experience_reasoning": "<объяснение оценки БЕЗ переносов строк>",
        "cultural_fit": <число 0-100>,
        "cultural_fit_reasoning": "<объяснение БЕЗ переносов строк>",
        "communication": <число 0-100>,
        "communication_reasoning": "<объяснение БЕЗ переносов строк>",
        "growth_potential": <число 0-100>,
        "growth_potential_reasoning": "<объяснение БЕЗ переносов строк>",
        "stability": <число 0-100>,
        "stability_reasoning": "<объяснение БЕЗ переносов строк>"
    }},
    "summary": "<краткий вывод БЕЗ переносов строк>",
    "strengths": ["сильная сторона 1", "сильная сторона 2"],
    "weaknesses": ["слабая сторона 1", "слабая сторона 2"],
    "missing_skills": ["недостающий навык 1", "недостающий навык 2"],
    "red_flags": ["риск 1", "риск 2"],
    "recommendation": "YES|NO|MAYBE",
    "confidence_level": "HIGH|MEDIUM|LOW",
    "interview_questions": ["вопрос 1", "вопрос 2", "вопрос 3"],
    "next_steps": ["шаг 1", "шаг 2"],
    "salary_expectation_fit": "MATCH|BELOW|ABOVE|UNCLEAR",
    "availability": "IMMEDIATE|NOTICE_PERIOD|UNCLEAR"
}}

КРИТИЧЕСКИ ВАЖНО:
1. Верни ТОЛЬКО валидный JSON
2. НЕ добавляй текст ДО или ПОСЛЕ JSON
3. НЕ используй комментарии // или /* */
4. Все строки в двойных кавычках
5. Все ключи в двойных кавычках
6. НЕ используй переносы строк внутри строковых значений - пиши весь текст в одну строку
7. Если текст длинный - сокращай, но НЕ переноси на новую строку
"""

        response = self._call_llm(prompt)
        return self._extract_json(response)

    def extract_structure(self, text: str, extraction_type: str) -> Dict[str, Any]:
        if extraction_type == "vacancy":
            prompt = f"""
Извлеки структурированную информацию о вакансии из текста.

Текст:
{text[:3000]}

Верни ТОЛЬКО валидный JSON (без markdown, без текста до/после, без комментариев):
{{
    "title": "должность",
    "company": "компания",
    "requirements": {{
        "hard_skills": ["навык1", "навык2"],
        "soft_skills": ["навык1", "навык2"],
        "experience_years": число
    }}
}}

ВАЖНО: 
1. ТОЛЬКО JSON, без дополнительного текста
2. НЕ используй переносы строк внутри строковых значений
"""
        else:  # resume
            prompt = f"""
Извлеки структурированную информацию о кандидате из резюме.

Текст:
{text[:3000]}

Верни ТОЛЬКО валидный JSON (без markdown, без текста до/после, без комментариев):
{{
    "name": "ФИО",
    "age": число,
    "experience_years": число,
    "skills": ["навык1", "навык2"],
    "education": "образование",
    "previous_positions": ["должность1", "должность2"]
}}

ВАЖНО: 
1. ТОЛЬКО JSON, без дополнительного текста
2. НЕ используй переносы строк внутри строковых значений
"""

        response = self._call_llm(prompt)
        return self._extract_json(response)
