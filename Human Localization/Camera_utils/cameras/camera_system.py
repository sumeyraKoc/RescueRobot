import cv2
import sys

from pathlib import Path

from Camera_utils.shared.frame_buffer import FrameBuffer

from Camera_utils.cameras.duckie_camera import DuckieCamera
from Camera_utils.cameras.noir_camera import TCPCamera

from Camera_utils.processing.duckie_image_processor import (
    DuckieImageProcessor
)

from Camera_utils.config.camera_config import (
    WIDTH,
    HEIGHT,
    DIM
)

from Camera_utils.config.duckie_config import (
    DUCKIE_WS,
    DUCKIE_TOPIC
)

from Camera_utils.config.pi_camera_config import (
    PI_TCP
)


sys.path.append(
    str(
        Path(__file__).resolve().parent.parent
    )
)


# =====================================================
# CAMERA SYSTEM
# =====================================================

class CameraSystem:

    def __init__(self):

        # =================================================
        # Shared Buffers
        # =================================================

        self.duckie_buffer = FrameBuffer()

        self.pi_buffer = FrameBuffer()

        # =================================================
        # Cameras
        # =================================================

        self.duckie = DuckieCamera(
            DUCKIE_WS,
            DUCKIE_TOPIC,
            self.duckie_buffer
        )

        self.pi = TCPCamera(
            PI_TCP,
            WIDTH,
            HEIGHT,
            self.pi_buffer
        )

        # =================================================
        # Image Processor
        # =================================================

        self.processor = DuckieImageProcessor()

        # =================================================
        # Dimensions
        # =================================================

        self.DIM = DIM


    # =====================================================
    # START
    # =====================================================

    def start(self):

        self.duckie.start()

        self.pi.start()

        print("[INFO] Camera system started")


    # =====================================================
    # STOP
    # =====================================================

    def stop(self):

        self.duckie.stop()

        self.pi.stop()

        cv2.destroyAllWindows()

        print("[INFO] Camera system stopped")


    # =====================================================
    # MAIN LOOP
    # =====================================================
    def get_frames(self):

        duckie_frame = self.duckie_buffer.get()
   
        pi_frame = self.pi_buffer.get()

        if duckie_frame is None:
            return None,None

        if pi_frame is None:
            return None, None

        duckie_processed = self.processor.process(
            duckie_frame
        )

        pi_final = cv2.resize(
            pi_frame,
            self.DIM,
            interpolation=cv2.INTER_LINEAR
        )

        return duckie_processed ,pi_final
    
    def run(self):

        while True:

            duckie_frame, pi_frame =  (self.get_frames())
                
    


            if duckie_frame is None:
                continue

            if pi_frame is None:
                continue

            cv2.imshow(
                "duckie_processed",
                duckie_frame
            )

            cv2.imshow(
                "pi_camera",
                pi_frame
            )

            key = cv2.waitKey(1)

            if key == 27:
                break

        self.stop()

    
    