import os
from pathlib import Path

# Audio processing constants
SAMPLE_RATE = 22050
EMOTION_LABELS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad']

# Model paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Go up to project root
MODEL_DIR = BASE_DIR / "Emotion-Dataset"
MODEL_PUBLIC_DIR = BASE_DIR / "Emotion-Backend/models/"

# Load models
try:
    from tensorflow.keras.models import load_model # type: ignore
    from tensorflow.keras import models # type: ignore
    import joblib
    import logging

    logger = logging.getLogger(__name__)

    extractor_path = MODEL_PUBLIC_DIR / "best_cnn.keras"
    svm_path = MODEL_PUBLIC_DIR / "best_svm.pkl"
    
    local_extractor_path = MODEL_DIR / "best_cnn.keras"
    local_svm_path = MODEL_DIR / "best_svm.pkl"

    extractor = None
    svm_model = None

    if extractor_path.exists():
        try:
            # Try to load the model normally
            cnn = load_model(str(extractor_path))
            # Create extractor that outputs embeddings from the embedding layer
            extractor = models.Model(cnn.input, cnn.get_layer("embedding").output)
            logger.info("CNN model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load CNN model: {e}")
            print(f"Error: CNN model loading failed: {e}")
    else:
        logger.warning(f"CNN model not found at {extractor_path}")
        print(f"Warning: CNN model not found at {extractor_path}")

    if svm_path.exists():
        try:
            svm_model = joblib.load(str(svm_path))
            logger.info("SVM model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load SVM model: {e}")
            print(f"Error: SVM model loading failed: {e}")
    else:
        logger.warning(f"SVM model not found at {svm_path}")
        print(f"Warning: SVM model not found at {svm_path}")

    
    if local_extractor_path.exists():
        try:
            cnn = load_model(str(local_extractor_path))
            extractor = models.Model(cnn.input, cnn.get_layer("embedding").output)
            logger.info("CNN model loaded successfully from local path")
        except Exception as e:
            logger.error(f"Failed to load CNN model from local path: {e}")
            print(f"Error: CNN model loading from local path failed: {e}")
    else:
        logger.warning(f"CNN model not found at local path {local_extractor_path}")
        print(f"Warning: CNN model not found at local path {local_extractor_path}")
        
    if local_svm_path.exists():
        try:
            svm_model = joblib.load(str(local_svm_path))
            logger.info("SVM model loaded successfully from local path")
        except Exception as e:
            logger.error(f"Failed to load SVM model from local path: {e}")
            print(f"Error: SVM model loading from local path failed: {e}")
            
except ImportError as e:
    extractor = None
    svm_model = None
    logger = logging.getLogger(__name__)
    logger.error(f"Required ML libraries not available: {e}")
    print(f"Warning: TensorFlow or joblib not installed: {e}")