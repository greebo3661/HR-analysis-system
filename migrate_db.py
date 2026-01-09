"""Миграция БД: добавление новых таблиц и полей"""
import sqlite3
import os

DB_PATH = "/data/db/hr_analysis.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print("БД не существует, миграция не требуется")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Начало миграции...")
    
    # Проверяем существующие колонки
    cursor.execute("PRAGMA table_info(matches)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    # Добавляем status и status_updated_at если их нет
    if 'status' not in existing_columns:
        print("Добавляем колонку 'status'...")
        cursor.execute("ALTER TABLE matches ADD COLUMN status TEXT DEFAULT 'new'")
        cursor.execute("UPDATE matches SET status = 'new' WHERE status IS NULL")
    
    if 'status_updated_at' not in existing_columns:
        print("Добавляем колонку 'status_updated_at'...")
        cursor.execute("ALTER TABLE matches ADD COLUMN status_updated_at TIMESTAMP")
        cursor.execute("UPDATE matches SET status_updated_at = created_at WHERE status_updated_at IS NULL")
    
    # Создаём таблицу comments если её нет
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches (id) ON DELETE CASCADE
        )
    """)
    print("Таблица 'comments' создана")
    
    # Создаём таблицу status_history если её нет
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            old_status TEXT,
            new_status TEXT NOT NULL,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches (id) ON DELETE CASCADE
        )
    """)
    print("Таблица 'status_history' создана")
    
    conn.commit()
    conn.close()
    
    print("✅ Миграция завершена успешно!")

if __name__ == "__main__":
    migrate()
