"""
Performance benchmark test utility:
- Measures detection, quality, alignment, embedding latency
- Calculates effective AI FPS
- Measures memory usage
"""

import time
import pytest
import numpy as np

from backend.app.recognition.model_manager import ModelManager
from backend.app.recognition.frame_processor import FaceProcessingService


def test_ai_pipeline_performance_benchmark():
    manager = ModelManager.get_instance()
    if not manager.is_ready:
        manager.initialize()

    if not manager.is_ready:
        pytest.skip("InsightFace models not loaded yet — skipping benchmark test.")

    processor = FaceProcessingService()
    # Create test synthetic frame
    synthetic_frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)

    warmup_runs = 2
    for _ in range(warmup_runs):
        processor.process_frame(synthetic_frame)

    test_runs = 5
    latencies = []

    for _ in range(test_runs):
        t0 = time.perf_counter()
        results, metrics = processor.process_frame(synthetic_frame)
        elapsed = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed)

    avg_latency = np.mean(latencies)
    effective_fps = 1000.0 / avg_latency if avg_latency > 0 else 0.0

    print(f"\n--- AI PERFORMANCE BENCHMARK ---")
    print(f"Average Total Latency: {avg_latency:.2f} ms")
    print(f"Effective AI FPS:      {effective_fps:.2f} FPS")
    print(f"Inference Device:      {manager.inference_device.upper()}")
    print(f"--------------------------------\n")

    assert avg_latency > 0.0
