from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models import Student, Attendance, Setting
from backend.schemas import AnalyticsCounts, SettingsResponse, SettingsUpdate
import datetime

router = APIRouter()

@router.get("/counts", response_model=AnalyticsCounts)
def get_analytics_counts(db: Session = Depends(get_db)):
    total_students = db.query(Student).count()
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    today_attendance = db.query(Attendance).filter(Attendance.date == today_str).count()
    
    today_percentage = (today_attendance / total_students * 100) if total_students > 0 else 0.0
    
    # 7-day average
    seven_days_ago = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    past_week_attendance = db.query(Attendance).filter(
        Attendance.date >= seven_days_ago
    ).count()
    seven_day_average = (past_week_attendance / 7.0 / total_students * 100) if total_students > 0 else 0.0
    
    return AnalyticsCounts(
        total_students=total_students,
        today_attendance=today_attendance,
        today_percentage=round(today_percentage, 2),
        seven_day_average=round(seven_day_average, 2)
    )

@router.get("/daily-counts")
def get_daily_counts(db: Session = Depends(get_db)):
    thirty_days_ago = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    
    results = db.query(
        Attendance.date, func.count(Attendance.id)
    ).filter(
        Attendance.date >= thirty_days_ago
    ).group_by(Attendance.date).all()
    
    return [{"date": r[0], "count": r[1]} for r in results]
