from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/db/hr_analysis.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Vacancy(Base):
    __tablename__ = "vacancies"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    requirements_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    matches = relationship("Match", back_populates="vacancy")

class Match(Base):
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True, index=True)
    resume_name = Column(String, nullable=False)
    vacancy_id = Column(Integer, ForeignKey("vacancies.id"))
    vacancy_title = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    analysis_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # НОВОЕ: статус кандидата
    status = Column(String, default="new")  # new, review, interview, offer, rejected, reserve
    status_updated_at = Column(DateTime, default=datetime.utcnow)
    
    vacancy = relationship("Vacancy", back_populates="matches")
    comments = relationship("Comment", back_populates="match", cascade="all, delete-orphan")
    status_history = relationship("StatusHistory", back_populates="match", cascade="all, delete-orphan")

# НОВОЕ: таблица комментариев
class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    text = Column(Text, nullable=False)
    tags = Column(String)  # JSON array строк
    created_at = Column(DateTime, default=datetime.utcnow)
    
    match = relationship("Match", back_populates="comments")

# НОВОЕ: история смены статусов
class StatusHistory(Base):
    __tablename__ = "status_history"
    
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    old_status = Column(String)
    new_status = Column(String, nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    
    match = relationship("Match", back_populates="status_history")

def init_db():
    Base.metadata.create_all(bind=engine)
