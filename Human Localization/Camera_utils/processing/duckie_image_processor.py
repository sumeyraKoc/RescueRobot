import cv2
import numpy as np 

from Camera_utils.calibration.duckie_calibration import (
    WIDTH,
    HEIGHT,
    DIM,
    roi,
    map1,
    map2
)

from Camera_utils.config.camera_controls import (
    load_camera_controls,
    save_camera_controls
)



# =====================================================
# DUCKIE IMAGE PROCESSOR
# =====================================================

class DuckieImageProcessor:

    def __init__(self):

        self.WIDTH = WIDTH
        self.HEIGHT = HEIGHT

        self.DIM = DIM

        self.roi = roi

        self.crop_w = 320
        self.crop_h = 200  # 240

        self.map1 = map1
        self.map2 = map2

        self.settings = load_camera_controls()


    # =====================================================
    # SAVE SETTINGS
    # =====================================================

    def save_settings(self):

        save_camera_controls(
            self.settings
        )

    

    # =====================================================
    # PROCESS
    # =====================================================

    def process(self, frame):
        # =============================================
        # Center ROI
        # =============================================

        center_x = self.WIDTH // 2
        center_y = self.HEIGHT // 2

        x1 = center_x - self.crop_w // 2
        y1 = center_y - self.crop_h // 2

        x2 = x1 + self.crop_w
        y2 = y1 + self.crop_h

        # =============================================
        # ROI crop ONLY
        # =============================================

        roi_frame = frame[
            y1:y2,
            x1:x2
        ]

        return {

            "full_frame": frame,

            "roi_frame": roi_frame,

            "roi_x": x1,

            "roi_y": y1
        }