from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db, APP_DIR
from backend.models import Student, Attendance, Setting
from backend.schemas import RecognizeRequest, RecognizeResponse, AttendanceResponse
from backend.services.face_service import recognize_face
import datetime
import os
import base64
import uuid

router = APIRouter()

@router.post("/recognize", response_model=RecognizeResponse)
def handle_recognition(request: RecognizeRequest, db: Session = Depends(get_db)):
    # Get threshold from settings or default
    setting = db.query(Setting).filter(Setting.key == "confidence_threshold").first()
    threshold = float(setting.value) if setting else 0.6
    
    # Perform recognition
    result = recognize_face(request.image, threshold)
    
    if not result["success"]:
        return RecognizeResponse(success=False, message=result["message"])
        
    student_id = result["student_id"]
    confidence = result["confidence"]
    
    # Check if student exists
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        return RecognizeResponse(success=False, message="Student found in embeddings but not in database")
        
    # Check duplicate for today
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    existing_attendance = db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.date == today_str
    ).first()
    
    if existing_attendance:
        return RecognizeResponse(
            success=True, 
            student_id=student_id, 
            name=student.name, 
            confidence=confidence,
            message="Already marked present today"
        )
        
    # Save snapshot
    snapshot_filename = f"{student_id}_{uuid.uuid4().hex[:8]}.jpg"
    snapshot_path = os.path.join(APP_DIR, "attendance", snapshot_filename)
    
    img_data = request.image.split(',')[1] if ',' in request.image else request.image
    with open(snapshot_path, "wb") as f:
        f.write(base64.b64decode(img_data))
        
    # Create attendance record
    new_attendance = Attendance(
        student_id=student_id,
        date=today_str,
        status="Present",
        snapshot_path=snapshot_path,
        confidence=confidence,
        emotion="Unknown" # Emotion not supported by face_recognition
    )
    db.add(new_attendance)
    db.commit()
    db.refresh(new_attendance)
    
    return RecognizeResponse(
        success=True,
        student_id=student_id,
        name=student.name,
        confidence=confidence,
        message="Attendance marked successfully"
    )

@router.get("/today", response_model=list[AttendanceResponse])
def get_today_attendance(db: Session = Depends(get_db)):
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    return db.query(Attendance).filter(Attendance.date == today_str).all()
