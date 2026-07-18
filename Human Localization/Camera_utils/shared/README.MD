# Frame Buffer

The `FrameBuffer` class provides a thread-safe way to share image frames between different parts of the camera system.

## Purpose

Since each camera runs in its own thread, the frame buffer stores the most recent image and allows other threads to safely access it without data conflicts.

## Functions

### `update(frame)`

- Stores the latest frame in the buffer.
- A copy of the frame is saved to prevent unintended modifications.

### `get()`

- Returns a copy of the most recent frame.
- Returns `None` if no frame is available.

### `clear()`

- Removes the current frame from the buffer.

## Thread Safety

A `threading.Lock` is used to ensure that only one thread can read or update the buffer at a time. This prevents race conditions while frames are being shared between the camera threads and the main application.
