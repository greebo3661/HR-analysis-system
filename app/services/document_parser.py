import io
import json
import re
from pypdf import PdfReader
from docx import Document
from typing import Dict, Any

class DocumentParser:
    """Парсер PDF и DOCX документов"""

    @staticmethod
    def parse_pdf(file_bytes: bytes) -> str:
        """Извлекает текст из PDF"""
        try:
            pdf = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise ValueError(f"Ошибка парсинга PDF: {str(e)}")

    @staticmethod
    def parse_docx(file_bytes: bytes) -> str:
        """Извлекает текст из DOCX"""
        try:
            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            return text.strip()
        except Exception as e:
            raise ValueError(f"Ошибка парсинга DOCX: {str(e)}")

    @classmethod
    def parse_file(cls, file_bytes: bytes, filename: str) -> str:
        """Определяет тип файла и парсит"""
        if filename.lower().endswith('.pdf'):
            return cls.parse_pdf(file_bytes)
        elif filename.lower().endswith('.docx'):
            return cls.parse_docx(file_bytes)
        elif filename.lower().endswith('.txt'):
            return file_bytes.decode('utf-8')
        else:
            raise ValueError(f"Неподдерживаемый формат: {filename}")

class VacancyExtractor:
    """Извлекает структурированные данные вакансии через LLM"""

    @staticmethod
    def extract_vacancy_structure(text: str, llm_client) -> Dict[str, Any]:
        """Структурирует текст вакансии через LLM"""

        prompt = f"""Извлеки из текста вакансии структурированные данные.

Текст вакансии:
{text[:2000]}

Верни ТОЛЬКО JSON в таком формате:
{{
  "title": "Название должности",
  "company": "Название компании",
  "requirements": {{
    "hard_skills": ["навык1", "навык2", "навык3"],
    "soft_skills": ["навык1", "навык2"],
    "experience_years": 3
  }},
  "responsibilities": "Краткое описание обязанностей"
}}

Если какое-то поле не найдено, используй значения по умолчанию."""

        # Используем call_llm
        response = llm_client.call_llm(prompt, temperature=0.1)

        # Очищаем от markdown
        clean = response.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]

        return json.loads(clean.strip())

class ResumeExtractor:
    """Извлекает структурированные данные резюме через LLM"""

    @staticmethod
    def extract_resume_structure(text: str, llm_client) -> Dict[str, Any]:
        """Структурирует текст резюме через LLM"""

        prompt = f"""Извлеки из текста резюме структурированные данные.

Текст резюме:
{text[:2500]}

Верни ТОЛЬКО JSON в таком формате:
{{
  "name": "Фамилия Имя Отчество",
  "age": 30,
  "gender": "М|Ж|Не указано",
  "email": "email@example.com",
  "phone": "+7 999 123-45-67",
  "skills": ["навык1", "навык2", "навык3"],
  "experience": [
    {{
      "company": "Название компании",
      "position": "Должность",
      "start_date": "2020-01",
      "end_date": "2023-12",
      "description": "Краткое описание"
    }}
  ],
  "education": [
    {{
      "institution": "ВУЗ",
      "degree": "Степень",
      "year": "2019"
    }}
  ]
}}

ВАЖНО:
- Определи пол по имени (например: Анна=Ж, Иван=М)
- Если возраст прямо указан - используй его
- Если указана дата рождения - вычисли возраст (сейчас 2026 год)
- Если ФИО не найдено, используй "Кандидат (возраст, пол)" например "Кандидат (31 год, М)"
"""

        # Используем call_llm
        response = llm_client.call_llm(prompt, temperature=0.1)

        # Очищаем от markdown
        clean = response.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]

        result = json.loads(clean.strip())

        # Фоллбэк для имени
        if not result.get('name') or result['name'] in ['N/A', 'Не указано', 'Unknown']:
            age = result.get('age', 'Н/У')
            gender = result.get('gender', 'Н/У')
            from datetime import datetime
            timestamp = datetime.now().strftime("%d.%m %H:%M")
            result['name'] = f"Кандидат ({age} лет, {gender}) [{timestamp}]"

        return result
