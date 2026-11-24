from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from datetime import datetime
from backend.database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    roll_no = Column(String)
    class_section = Column(String)
    email = Column(String)
    face_folder_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    date = Column(String, index=True) # YYYY-MM-DD
    status = Column(String, default="Present")
    snapshot_path = Column(String)
    confidence = Column(Float)
    emotion = Column(String, nullable=True) # Kept for schema compatibility, may be null with face_recognition

class EmotionLog(Base):
    __tablename__ = "emotion_logs"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    emotion = Column(String)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String)
