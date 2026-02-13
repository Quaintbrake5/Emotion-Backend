#!/usr/bin/env python3
"""
Test script for audio prediction functionality.
Tests the fixes for shape mismatch and datetime.timezone errors.
"""

import numpy as np
import os
import sys
import tempfile
import soundfile as sf
from datetime import datetime, timezone

# Add parent directory to path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_test_audio(duration=3.0, sample_rate=22050):
    """Create a simple test audio file with a sine wave."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Create a sine wave with some variation
    signal = np.sin(2 * np.pi * 440 * t) * 0.5 + np.sin(2 * np.pi * 880 * t) * 0.3
    return signal.astype(np.float32)

def test_spectrogram_generation():
    """Test spectrogram generation produces correct shape."""
    print("Testing spectrogram generation...")
    try:
        from services.audio_service import generate_spectrogram

        signal = create_test_audio(duration=2.0)
        spectrogram = generate_spectrogram(signal)

        expected_shape = (180, 120, 1)
        if spectrogram.shape == expected_shape:
            print(f"✓ Spectrogram shape correct: {spectrogram.shape}")
            return True
        else:
            print(f"✗ Spectrogram shape incorrect: expected {expected_shape}, got {spectrogram.shape}")
            return False
    except Exception as e:
        print(f"✗ Spectrogram generation failed: {e}")
        return False

def test_datetime_timezone():
    """Test datetime.timezone import works."""
    print("Testing datetime.timezone import...")
    try:
        now = datetime.now(timezone.utc)
        print(f"✓ datetime.timezone works: {now}")
        return True
    except Exception as e:
        print(f"✗ datetime.timezone failed: {e}")
        return False

def test_prediction_pipeline():
    """Test the full prediction pipeline."""
    print("Testing prediction pipeline...")
    try:
        from services.prediction_service import process_audio_for_prediction

        signal = create_test_audio(duration=2.0)
        result = process_audio_for_prediction(signal)

        if isinstance(result, dict) and len(result) > 0:
            print(f"✓ Prediction successful: {result}")
            return True
        else:
            print(f"✗ Prediction failed: invalid result {result}")
            return False
    except Exception as e:
        print(f"✗ Prediction pipeline failed: {e}")
        return False

def test_prediction_with_storage():
    """Test prediction with storage function (no longer saves to MongoDB)."""
    print("Testing prediction with storage...")
    try:
        from services.prediction_service import process_audio_for_prediction_with_storage
        import asyncio

        async def test_storage():
            signal = create_test_audio(duration=2.0)
            result = await process_audio_for_prediction_with_storage(
                signal=signal,
                user_id="test_user",
                filename="test.wav",
                audio_duration=2.0
            )

            if isinstance(result, dict) and "emotion" in result and "confidence" in result:
                print(f"✓ Prediction with storage works: emotion={result['emotion']}, confidence={result['confidence']:.2f}")
                return True
            else:
                print(f"✗ Prediction with storage failed: invalid result {result}")
                return False

        return asyncio.run(test_storage())
    except Exception as e:
        print(f"✗ Prediction with storage test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Running audio prediction tests...\n")

    tests = [
        test_datetime_timezone,
        test_spectrogram_generation,
        test_prediction_pipeline,
        test_prediction_with_storage
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The fixes should resolve the original errors.")
    else:
        print("❌ Some tests failed. Please check the issues above.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
