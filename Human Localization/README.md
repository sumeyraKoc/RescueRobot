# Overview

This project implements a real-time human detection and localization system using multiple camera sources. It combines image acquisition, preprocessing, deep learning-based person detection, and geometric localization to estimate the position of detected people relative to the robot.

The system is organized into independent modules, each responsible for a specific stage of the processing pipeline. Camera modules acquire synchronized images from different sources, processing modules prepare the images for inference, the detection module identifies people using a custom neural network, and the localization module estimates each person's distance and viewing angle using camera calibration and homography.

The modular structure allows each component to be developed, tested, and maintained independently while providing a complete end-to-end detection pipeline.

## Processing Pipeline

The overall workflow of the system is:

1. Acquire images from the Duckiebot and Raspberry Pi cameras.
2. Store the latest frames in thread-safe shared buffers.
3. Apply camera calibration and image preprocessing.
4. Extract the Region of Interest (ROI).
5. Perform person detection using the trained neural network.
6. Convert image detections into real-world positions using homography.
7. Publish detection results and annotated images through ROS.
8. Display the processed results for real-time visualization.

Each module documented below describes one part of this pipeline and its role within the overall system.

---
# Model Weights

## Download

| v0.1 | Base model | [Download Link](https://drive.google.com/drive/folders/1nb_do_qkIaDVHX7IGVNEsfy37MNNWAY6?usp=sharing) |

