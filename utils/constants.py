import os
from pathlib import Path

# Audio processing constants
SAMPLE_RATE = 22050
EMOTION_LABELS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad']

# Model paths
BASE_DIR = Path(__file__).resolve().parent.parent  # Emotion-Backend directory
MODEL_DIR = BASE_DIR / "models"

# Models are now hosted on Hugging Face Space - no local loading needed
extractor = None
svm_model = None
