# TODO: Fix Audio Prediction Error

## Completed Tasks
- [x] Modified constants.py to create extractor as embedding model (128 features)
- [x] Updated EMOTION_LABELS to match 6 classes (removed 'surprise')
- [x] Updated predict_emotion to use svm_model.predict_proba on embedding
- [x] Updated function signature and logic in predict_emotion

## Next Steps
- [x] Test prediction functionality
- [x] Verify the fix resolves the "X has 6 features, but SVC is expecting 128 features" error
- [x] Fix Pydantic validation error for emotion field in API response
