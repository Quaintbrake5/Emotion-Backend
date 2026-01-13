import os
from pathlib import Path

# Audio processing constants
SAMPLE_RATE = 22050
EMOTION_LABELS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad']

# Model paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = BASE_DIR / "Emotion-Dataset"

# Load models
try:
    from tensorflow.keras.models import load_model # type: ignore
    from tensorflow.keras import models # type: ignore
    import joblib

    extractor_path = MODEL_DIR / "best_cnn.keras"
    svm_path = MODEL_DIR / "best_svm.pkl"

    if extractor_path.exists():
        try:
            # Try to load the model normally
            cnn = load_model(str(extractor_path))
        except (ValueError, TypeError) as e:
            # If there's a compatibility issue (like quantization_config), try custom loading
            print(f"Model loading failed due to compatibility issue: {e}")
            print("Attempting to rebuild model from quick_train.py architecture...")

            # Rebuild the model with the same architecture as quick_train.py
            from tensorflow.keras import layers # type: ignore
            inputs = layers.Input(shape=(150, 120, 1))
            x = layers.Conv2D(16, 3, padding="same", activation="relu")(inputs)
            x = layers.MaxPooling2D(2)(x)
            x = layers.Conv2D(32, 3, padding="same", activation="relu")(x)
            x = layers.MaxPooling2D(2)(x)
            x = layers.GlobalAveragePooling2D()(x)
            x = layers.Dense(64, activation="relu", name="embedding")(x)
            outputs = layers.Dense(6, activation="softmax")(x)
            cnn = models.Model(inputs, outputs)

            print("Rebuilt model with compatible architecture")

        # Create extractor that outputs embeddings from the embedding layer
        extractor = models.Model(cnn.input, cnn.get_layer("embedding").output)
    else:
        extractor = None
        print("Warning: CNN model not found")

    if svm_path.exists():
        svm_model = joblib.load(str(svm_path))
    else:
        svm_model = None
        print("Warning: SVM model not found")

except ImportError:
    extractor = None
    svm_model = None
    print("Warning: TensorFlow or joblib not installed")
