# Configuration Files

This folder contains the configuration files used by the camera system. Keeping these settings separate makes it easier to modify camera parameters without changing the main code.

---

# Camera Configuration

This file defines the common image resolution used throughout the project.

## Parameters

- `WIDTH = 640`
- `HEIGHT = 480`
- `DIM = (640, 480)`

These values are used when resizing images, creating calibration maps, and ensuring both camera streams use the same resolution.

---

# Camera Controls

This file manages adjustable camera settings and stores them in a JSON file (`camera_controls.json`) this used to restrict the active camera ROI(Region over interest) by manipulating wide camera with these settings but now it do not use this config earlier version was using this it is a redundant part.

## Default Controls

- **zoom** – Digital zoom level.
- **x_offset** – Horizontal image shift.
- **y_offset** – Vertical image shift.
- **bottom_crop** – Pixels removed from the bottom of the image.
- **sharpness** – Image sharpness level.
- **detail** – Additional image enhancement parameter.

## Functions

### `load_camera_controls()`

- Loads camera settings from `camera_controls.json`.
- If the file does not exist, the default values are used.
- Allows camera settings to persist between program runs.

### `save_camera_controls(settings)`

- Saves the current camera settings to `camera_controls.json`.
- Makes any changes permanent for future executions.

---

# Duckiebot Configuration

This file stores the communication settings for the Duckiebot camera.

## Parameters

- `DUCKIE_WS` – WebSocket address of the Duckiebot (user-defined).
- `DUCKIE_TOPIC` – ROS topic that publishes the compressed camera images.

The camera system connects to this WebSocket and subscribes to the specified topic to receive image frames.

---

# Raspberry Pi Camera Configuration

This file contains the network address of the Raspberry Pi NoIR camera stream.

## Parameter

- `PI_TCP` – TCP address of the H.264 video stream.

The `StreamReader` uses this address to receive and decode the live camera feed that still running, but starting camera feed from Raspberry PI is complicated it is started from PI by **hand**.

---

# ROS Configuration

This file stores the WebSocket address used to communicate with the ROS system.

## Parameter

- `ROS_WS` – WebSocket address of the ROS bridge.

It is used by components that need to publish or subscribe to ROS topics through a WebSocket connection.
