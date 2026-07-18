# Camera System

This module manages both camera sources and provides synchronized frames for the application.

## Overview

The system uses two different cameras:

- **Duckiebot Camera** – Receives RGB images through a WebSocket connection.
- **Raspberry Pi NoIR Camera** – Receives an H.264 video stream over TCP.

Each camera runs in its own thread and continuously updates a shared frame buffer. The main application reads the latest frame from each buffer, processes the images, and returns them together.

## Camera System Workflow

1. Create shared frame buffers.
2. Start both camera threads.
3. Continuously receive frames from each camera.
4. Process the Duckiebot camera image.
5. Resize the Raspberry Pi image to match the calibration resolution.
6. Return both frames for visualization or further processing.

---

# Duckie Camera

The Duckie camera connects to the Duckiebot using a **WebSocket** connection.

### Process

1. Connect to the WebSocket server.
2. Subscribe to the configured camera topic.
3. Receive images encoded as Base64 strings.
4. Decode the Base64 data into JPEG bytes.
5. Convert the JPEG into an OpenCV image.
6. Store the latest frame in the shared buffer.

This camera provides the normal RGB image used by the system.

---

# TCP Camera

The Raspberry Pi NoIR camera is received through a TCP video stream.

### Process

1. Read the H.264 stream using the `StreamReader`.
2. Rotate the image by 180°.
3. Resize the frame to **640 × 480**.
4. Convert the image to grayscale.
5. Apply CLAHE to improve local contrast.
6. Apply a small Gaussian blur to reduce noise.
7. Store the processed image in the shared buffer.

The output is an infrared-like grayscale image that is easier to compare with the Duckiebot camera.

---

# Stream Reader

The `StreamReader` is responsible for reading raw frames from the Raspberry Pi video stream.

### Process

1. Start an FFmpeg process.
2. Decode the incoming H.264 stream.
3. Scale frames to the desired resolution.
4. Convert each frame to raw BGR format.
5. Read the exact number of bytes required for one frame.
6. Convert the byte data into a NumPy array.
7. Reshape the array into an OpenCV image and return it.

Using FFmpeg allows reliable decoding of the network video stream while keeping latency low.
