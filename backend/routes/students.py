from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db, APP_DIR
from backend.models import Student
from backend.schemas import StudentCreate, StudentResponse
from backend.services.face_service import generate_and_save_embeddings
import os
import shutil
import uuid
from typing import List

router = APIRouter()

@router.post("/", response_model=StudentResponse)
def create_student(student_in: StudentCreate, db: Session = Depends(get_db)):
    # Check if student exists
    if db.query(Student).filter(Student.roll_no == student_in.roll_no).first():
        raise HTTPException(status_code=400, detail="Student with this roll number already exists")

    # Generate unique student ID
    student_id = str(uuid.uuid4())
    
    # Process images and generate embeddings
    success = generate_and_save_embeddings(student_id, student_in.images)
    if not success:
        raise HTTPException(status_code=400, detail="Could not detect faces in the provided images")

    # Create student record
    db_student = Student(
        student_id=student_id,
        name=student_in.name,
        roll_no=student_in.roll_no,
        class_section=student_in.class_section,
        email=student_in.email,
        face_folder_path=os.path.join(APP_DIR, "students", student_id)
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

@router.get("/", response_model=List[StudentResponse])
def get_students(db: Session = Depends(get_db)):
    return db.query(Student).all()

@router.delete("/{student_id}")
def delete_student(student_id: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    # Delete from DB
    db.delete(student)
    db.commit()
    
    # Delete files
    student_dir = os.path.join(APP_DIR, "students", student_id)
    if os.path.exists(student_dir):
        shutil.rmtree(student_dir)
        
    return {"success": True}
