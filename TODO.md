# TODO: Deploy CNN and SVM Models to Hugging Face Spaces and Integrate with Backend

## Steps to Complete

- [x] Create Gradio app script (`Emotion-Dataset/gradio_app.py`) that loads CNN and SVM models, processes audio input, and returns emotion predictions for deployment to Hugging Face Spaces.
- [x] Modify `Emotion-Backend/services/prediction_service.py` to use `gradio_client` for calling the deployed Hugging Face Space instead of local predictions.
- [x] Update `process_audio_for_prediction` and `process_audio_for_prediction_with_storage` functions to send audio data to the space and receive results asynchronously.
- [x] Add necessary imports and error handling for `gradio_client` calls in the prediction service.
- [ ] Test the backend integration to ensure predictions work without local model loading.
- [ ] Deploy the Gradio app to Hugging Face Spaces and update the Space URL in the backend code.
- [ ] Monitor for performance and implement error handling (e.g., timeouts, retries) for the API calls.
