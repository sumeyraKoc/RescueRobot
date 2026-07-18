# Image Processing

This module prepares the Duckiebot camera image for further processing.

---

# Duckie Image Processor

The `DuckieImageProcessor` extracts a fixed **Region of Interest (ROI)** from the camera image.

## Initialization

When created, the processor:

- Loads the camera calibration parameters.
- Loads the saved camera control settings.
- Defines the ROI size (`320 × 200` pixels).
- Stores the undistortion maps and image dimensions.

## Processing Workflow

For every input frame:

1. Compute the center of the image.
2. Define a fixed ROI around the image center.
3. Crop the ROI from the original frame.
4. Return both the original image and the cropped ROI.

The returned data includes:

- `full_frame` – Original camera image.
- `roi_frame` – Cropped region of interest.
- `roi_x` – X-coordinate of the ROI.
- `roi_y` – Y-coordinate of the ROI.

Using a fixed ROI reduces the amount of image data that needs to be processed while keeping the area of interest centered.

---

# Image Enhancement

This module provides optional functions to improve image quality before further processing.

## Detail Enhancement

The `enhance_detail()` function increases local image details using OpenCV's detail enhancement filter.

- If the detail value is `0` or less, the original image is returned.
- Higher values produce stronger detail enhancement.

## Sharpening

The `sharpen()` function increases image sharpness using an unsharp masking technique.

### Process

1. Apply a Gaussian blur to the image.
2. Combine the original and blurred images using weighted addition.
3. Return the sharpened result.

The sharpening strength is controlled by the `sharpness` parameter.# Image Processing

This module prepares the Duckiebot camera image for further processing.

---

# Duckie Image Processor

The `DuckieImageProcessor` extracts a fixed **Region of Interest (ROI)** from the camera image.

## Initialization

When created, the processor:

- Loads the camera calibration parameters.
- Loads the saved camera control settings.
- Defines the ROI size (`320 × 200` pixels).
- Stores the undistortion maps and image dimensions.

## Processing Workflow

For every input frame:

1. Compute the center of the image.
2. Define a fixed ROI around the image center.
3. Crop the ROI from the original frame.
4. Return both the original image and the cropped ROI.

The returned data includes:

- `full_frame` – Original camera image.
- `roi_frame` – Cropped region of interest.
- `roi_x` – X-coordinate of the ROI.
- `roi_y` – Y-coordinate of the ROI.

Using a fixed ROI reduces the amount of image data that needs to be processed while keeping the area of interest centered.

---

# Image Enhancement

This module provides optional functions to improve image quality before further processing.

## Detail Enhancement

The `enhance_detail()` function increases local image details using OpenCV's detail enhancement filter.

- If the detail value is `0` or less, the original image is returned.
- Higher values produce stronger detail enhancement.

## Sharpening

The `sharpen()` function increases image sharpness using an unsharp masking technique.

### Process

1. Apply a Gaussian blur to the image.
2. Combine the original and blurred images using weighted addition.
3. Return the sharpened result.

The sharpening strength is controlled by the `sharpness` parameter.
