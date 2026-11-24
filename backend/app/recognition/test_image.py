"""
CLI Test Utility for FaceNexa AI Engine (Phase 3).

Usage:
    python -m backend.app.recognition.test_image path/to/image.jpg

Outputs:
    • Number of faces detected
    • Bounding boxes & confidence
    • Face quality breakdown
    • Face alignment status
    • ArcFace embedding status & dimensions
    • Per-stage execution latency (ms) & effective FPS
"""

import sys
import os
import cv2
import json

from backend.app.recognition.model_manager import ModelManager
from backend.app.recognition.frame_processor import FaceProcessingService


def run_test(image_path: str):
    if not os.path.exists(image_path):
        print(f"Error: File not found at '{image_path}'")
        sys.exit(1)

    print(f"\n=======================================================")
    print(f"  FACENEXA PHASE 3 — RECOGNITION ENGINE TEST UTILITY  ")
    print(f"=======================================================")
    print(f"Loading image: {image_path}")

    frame = cv2.imread(image_path)
    if frame is None or frame.size == 0:
        print("Error: Failed to decode image file.")
        sys.exit(1)

    h, w, c = frame.shape
    print(f"Image resolution: {w}x{h} ({c} channels)")

    print("\nInitializing AI ModelManager...")
    manager = ModelManager.get_instance()
    manager.initialize()

    status = manager.get_status()
    print(f"Status: {status.status.upper()}")
    print(f"Inference Device: {status.inference_device.upper()}")
    print(f"Detector: {status.detection_model.name} ({'Loaded' if status.detection_model.loaded else 'Failed'})")
    print(f"Recognizer: {status.recognition_model.name} ({'Loaded' if status.recognition_model.loaded else 'Failed'})")

    if not manager.is_ready:
        print("\n[!] Model loading failed or incomplete. Cannot proceed with inference.")
        sys.exit(1)

    print("\nRunning face processing pipeline...")
    processor = FaceProcessingService()
    results, metrics = processor.process_frame(frame)

    print(f"\n-------------------------------------------------------")
    print(f"RESULTS SUMMARY")
    print(f"-------------------------------------------------------")
    print(f"Faces Detected: {len(results)}")

    for idx, face in enumerate(results):
        print(f"\n--- FACE #{idx + 1} ---")
        print(f"Face ID:               {face.face_id}")
        print(f"Bounding Box (x1,y1,x2,y2): [{face.bbox.x1}, {face.bbox.y1}, {face.bbox.x2}, {face.bbox.y2}] (Width: {face.bbox.width}px, Height: {face.bbox.height}px)")
        print(f"Detection Confidence:  {(face.detection_confidence * 100):.2f}%")

        if face.landmarks:
            print(f"Landmarks Found:       Left Eye, Right Eye, Nose, Mouth Left, Mouth Right")

        if face.quality:
            q = face.quality
            print(f"Quality Overall Score: {(q.overall_score * 100):.1f}%")
            print(f"  - Size Check:        {q.face_size.upper()}")
            print(f"  - Blur Status:       {q.blur.upper()} (Score: {q.blur_score})")
            print(f"  - Brightness:        {q.brightness.upper()} (Value: {q.brightness_value})")
            print(f"  - Pose Check:        {q.pose.upper()}")
            print(f"  - Suitable for Rec:  {'YES' if q.usable else 'NO'}")
            if q.feedback:
                print(f"  - Quality Feedback:  '{q.feedback}'")

        print(f"Embedding Available:   {'YES' if face.embedding_available else 'NO'}")
        if face.face_id in processor.latest_embeddings:
            emb = processor.latest_embeddings[face.face_id]
            print(f"Embedding Vector Dim:  {emb.shape[0]} floats (L2 norm: {cv2.norm(emb):.4f})")

    print(f"\n-------------------------------------------------------")
    print(f"TIMING BREAKDOWN")
    print(f"-------------------------------------------------------")
    print(f"Detection Time:  {metrics.detection_ms:6.2f} ms")
    print(f"Quality Time:    {metrics.quality_ms:6.2f} ms")
    print(f"Alignment Time:  {metrics.alignment_ms:6.2f} ms")
    print(f"Embedding Time:  {metrics.embedding_ms:6.2f} ms")
    print(f"-------------------------------------------------------")
    print(f"Total AI Time:   {metrics.total_ms:6.2f} ms")
    print(f"Effective AI FPS: {metrics.ai_fps:6.2f} FPS")
    print(f"=======================================================\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m backend.app.recognition.test_image path/to/image.jpg")
        sys.exit(1)
    run_test(sys.argv[1])
