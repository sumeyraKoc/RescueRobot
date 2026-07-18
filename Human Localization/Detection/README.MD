# Person Detector

The `PersonDetector` class performs real-time person detection using a custom PyTorch model. It handles model loading, image preprocessing, inference, prediction decoding, and post-processing in a single interface.

## Features

- Loads a trained custom detection model.
- Supports GPU (CUDA) inference with FP16 precision.
- Uses `torch.compile()` for improved inference performance.
- Processes RGB images with optional support for IR inputs.
- Decodes Distribution Focal Loss (DFL) bounding box predictions.
- Applies confidence thresholding and Non-Maximum Suppression (NMS).
- Can return detections or visualize them on the input image.

---

# Inference Pipeline

The detector follows the pipeline below:

1. **Image Preprocessing**
   - Resize the input image to the model input size.
   - Normalize pixel values to the range `[0,1]`.
   - Convert the image into a PyTorch tensor.
   - Transfer the tensor to the selected device (GPU or CPU).

2. **Model Inference**
   - Pass the preprocessed image through the trained neural network.
   - The model predicts object confidence scores and bounding box distributions at multiple feature scales.

3. **Prediction Decoding**
   - Convert the raw DFL predictions into bounding box coordinates.
   - Apply the confidence threshold to remove low-confidence detections.
   - Merge detections from all prediction scales.

4. **Post-processing**
   - Apply GPU-based Non-Maximum Suppression (NMS) to remove overlapping detections.
   - Convert the remaining detections to NumPy arrays.

5. **Visualization (Optional)**
   - Draw bounding boxes and confidence scores on the original image.
   - Return either the annotated image or only the detection results.

---

# Main Functions

### `preprocess(image)`

Prepares an RGB image for inference by resizing, normalizing, and converting it to a tensor.

### `preprocess_ir(image)`

Prepares a grayscale or infrared image for the network when IR input is used.

### `decode(preds)`

Converts the raw network outputs into bounding boxes and confidence scores. The method performs Distribution Focal Loss (DFL) decoding and combines predictions from all feature levels.

### `nms(boxes)`

Removes duplicate or overlapping detections using GPU-based Non-Maximum Suppression while keeping the highest-confidence predictions.

### `draw(image, boxes)`

Draws the detected bounding boxes and confidence values on the image for visualization.

### `predict(image, draw=True)`

Executes the complete detection pipeline:

- Preprocesses the image.
- Runs model inference.
- Decodes the predictions.
- Applies NMS.
- Returns either the detected bounding boxes or an annotated image containing the detections.

---

# Performance Optimizations

The detector includes several optimizations for real-time inference:

- Half-precision (FP16) computation.
- CUDA automatic mixed precision (`autocast`).
- `torch.compile()` for optimized execution.
- Cached feature grids to avoid repeated computations.
- GPU-based Non-Maximum Suppression.
- Early confidence filtering before decoding all predictions.
