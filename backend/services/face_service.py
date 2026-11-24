import os
import base64
import cv2
import numpy as np
import face_recognition
from backend.database import APP_DIR

STUDENTS_DIR = os.path.join(APP_DIR, "students")

def decode_base64_image(base64_string: str) -> np.ndarray:
    """Decodes a base64 string to an OpenCV image."""
    if ',' in base64_string:
        base64_string = base64_string.split(',')[1]
    img_data = base64.b64decode(base64_string)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def generate_and_save_embeddings(student_id: str, images_base64: list) -> bool:
    """Generates embeddings for a new student and saves to .npy file."""
    student_dir = os.path.join(STUDENTS_DIR, student_id)
    os.makedirs(student_dir, exist_ok=True)
    
    known_encodings = []
    for idx, b64 in enumerate(images_base64):
        img = decode_base64_image(b64)
        if img is None:
            continue
        
        # Save raw image for record
        img_path = os.path.join(student_dir, f"{idx}.jpg")
        cv2.imwrite(img_path, img)
        
        # Convert BGR to RGB for face_recognition
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Find face locations and encodings
        face_locations = face_recognition.face_locations(rgb_img)
        if len(face_locations) > 0:
            face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
            if len(face_encodings) > 0:
                known_encodings.append(face_encodings[0])
    
    if not known_encodings:
        return False
    
    # Save embeddings
    embeddings_file = os.path.join(student_dir, "embeddings.npy")
    np.save(embeddings_file, np.array(known_encodings))
    return True

def load_all_embeddings() -> dict:
    """Loads all saved embeddings into memory."""
    student_embeddings = {}
    if not os.path.exists(STUDENTS_DIR):
        return student_embeddings
        
    for student_id in os.listdir(STUDENTS_DIR):
        embeddings_file = os.path.join(STUDENTS_DIR, student_id, "embeddings.npy")
        if os.path.exists(embeddings_file):
            student_embeddings[student_id] = np.load(embeddings_file)
    
    return student_embeddings

def recognize_face(base64_image: str, threshold: float = 0.6) -> dict:
    """Recognizes a face in the image and returns the best match."""
    img = decode_base64_image(base64_image)
    if img is None:
        return {"success": False, "message": "Invalid image"}
        
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_img)
    
    if len(face_locations) == 0:
        return {"success": False, "message": "No face detected"}
        
    face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
    if len(face_encodings) == 0:
        return {"success": False, "message": "Could not extract face encoding"}
        
    unknown_encoding = face_encodings[0]
    
    all_embeddings = load_all_embeddings()
    if not all_embeddings:
        return {"success": False, "message": "No students registered"}
        
    best_match_id = None
    best_distance = float('inf')
    
    for student_id, encodings in all_embeddings.items():
        # Compare with all encodings for this student
        distances = face_recognition.face_distance(encodings, unknown_encoding)
        if len(distances) > 0:
            min_dist = min(distances)
            if min_dist < best_distance:
                best_distance = min_dist
                best_match_id = student_id
                
    if best_match_id and best_distance <= threshold:
        # Confidence is roughly 1 - distance
        confidence = max(0.0, 1.0 - best_distance)
        return {
            "success": True,
            "student_id": best_match_id,
            "confidence": confidence,
            "message": "Face recognized"
        }
    
    return {"success": False, "message": "Face not recognized or below confidence threshold"}
