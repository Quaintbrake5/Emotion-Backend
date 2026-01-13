from enum import Enum

class Emotion(str, Enum):
    ANGRY = "angry"
    DISGUST = "disgust"
    FEAR = "fear"
    HAPPY = "happy"
    NEUTRAL = "neutral"
    SAD = "sad"

class ModelType(str, Enum):
    CNN = "cnn"
    SVM = "svm"
    HYBRID = "hybrid"
