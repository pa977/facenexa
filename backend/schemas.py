from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class StudentBase(BaseModel):
    name: str
    roll_no: str
    class_section: str
    email: str

class StudentCreate(StudentBase):
    images: List[str] # List of base64 encoded images

class StudentResponse(StudentBase):
    id: int
    student_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class RecognizeRequest(BaseModel):
    image: str # base64 encoded image frame

class RecognizeResponse(BaseModel):
    success: bool
    student_id: Optional[str] = None
    name: Optional[str] = None
    confidence: Optional[float] = None
    message: str

class AttendanceBase(BaseModel):
    student_id: str
    status: str
    confidence: float

class AttendanceResponse(AttendanceBase):
    id: int
    timestamp: datetime
    date: str
    
    class Config:
        from_attributes = True

class AnalyticsCounts(BaseModel):
    total_students: int
    today_attendance: int
    today_percentage: float
    seven_day_average: float

class SettingsResponse(BaseModel):
    camera_device: str
    confidence_threshold: float
    session_timeout: int

class SettingsUpdate(BaseModel):
    camera_device: Optional[str] = None
    confidence_threshold: Optional[float] = None
    session_timeout: Optional[int] = None
