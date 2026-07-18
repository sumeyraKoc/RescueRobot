# Homography Distance Estimator

The `HomographyDistanceEstimator` converts image coordinates into real-world ground coordinates using a homography matrix. It is used to estimate the distance and viewing angle of detected people relative to the camera.

## Features

- Corrects camera lens distortion using the camera calibration parameters.
- Projects image points onto the ground plane using a homography matrix.
- Estimates the distance between the camera and the detected object.
- Computes the horizontal viewing angle of the detected object.

---

# Estimation Pipeline

The distance estimation process consists of the following steps:

1. **Undistort the Image Point**
   - Correct the detected image coordinates using the camera intrinsic matrix and distortion coefficients.

2. **Project to the Ground Plane**
   - Apply the homography matrix to transform the corrected image point into real-world ground coordinates.

3. **Compute the Viewing Angle**
   - Calculate the angle between the camera's forward direction and the detected object using the projected ground coordinates.

4. **Estimate the Distance**
   - Compute the straight-line distance from the camera to the detected object using the projected position and viewing angle.

---

# Main Functions

### `undistort_point(u, v)`

Corrects the input image coordinates using the camera calibration parameters to compensate for lens distortion.

### `image_to_ground(u, v)`

Projects the corrected image point onto the ground plane using the homography matrix and returns its real-world coordinates.

### `distance_and_angle(u, v)`

Calculates the object's distance and viewing angle from the camera based on the projected ground coordinates.

---

# Output

For each detected object, the estimator returns:

- **Distance** – Estimated distance from the camera (meters).
- **Angle** – Horizontal angle relative to the camera's forward direction (degrees).

These values are used by the detection system to provide localization information together with each detected person.
