import cv2
import json
import time
import base64
import websocket
import numpy as np

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent

sys.path.append(str(ROOT))

# =====================================================
# CAMERA SYSTEM
# =====================================================

from Camera_utils.cameras.camera_system import (
    CameraSystem
)

# =====================================================
# DETECTOR
# =====================================================

from Inference import PersonDetector

# =====================================================
# DISTANCE ESTIMATOR
# =====================================================

from Human_localization.DistanceEstimator import (
    HomographyDistanceEstimator
)

# =====================================================
# CALIBRATION
# =====================================================

from Camera_utils.calibration.duckie_calibration import (
    K,
    D
)

from Camera_utils.processing.duckie_image_processor import (DuckieImageProcessor)

# =====================================================
# CONFIG
# =====================================================

from Camera_utils.config.ros_config import (
    ROS_WS
)

# =====================================================
# DETECTION SYSTEM
# =====================================================

class DetectionSystem:

    def __init__(self):

        # =================================================
        # Camera System
        # =================================================

        self.camera_system = CameraSystem()

        # =================================================
        # Detector
        # =================================================

        self.detector = PersonDetector(
            "/home/mert/Desktop/RoboticsProject/Human Localization/best_test.pth",
            device="cuda"
        )

        # =================================================
        # Homography
        # =================================================

        H = [

            -3.944251854896834e-05,
             0.000244465300969488,
             0.3525628062426299,

            -0.0015625521124053067,
             8.221648302865118e-05,
             0.4953884314142318,

            -1.0725377094867827e-05,
             0.010420490862005964,
            -1.5438629450394505
        ]


        self.depth_estimator = (
            HomographyDistanceEstimator(
                H,
                K=K,
                D=D,
                kx=1.0,
                ky=1.0
            )
        )

        # =================================================
        # ROS
        # =================================================

        self.ws = websocket.create_connection(
            ROS_WS
        )

        # =================================================
        # Topics
        # =================================================

        self.DUCKIE_IMAGE_TOPIC = (
            "/duckie/detection/image/compressed"
        )

        self.DUCKIE_BBOX_TOPIC = (
            "/duckie/detections"
        )

        self.PI_IMAGE_TOPIC = (
            "/pi/detection/image/compressed"
        )

        self.PI_BBOX_TOPIC = (
            "/pi/detections"
        )

        self.advertise_topics()


    # =====================================================
    # ADVERTISE TOPICS
    # =====================================================

    def advertise_topics(self):

        image_topics = [

            self.DUCKIE_IMAGE_TOPIC,
            self.PI_IMAGE_TOPIC
        ]

        bbox_topics = [

            self.DUCKIE_BBOX_TOPIC,

            self.PI_BBOX_TOPIC
        ]

        # =============================================
        # Image Topics
        # =============================================

        for topic in image_topics:

            self.ws.send(json.dumps({

                "op": "advertise",

                "topic": topic,

                "type": "sensor_msgs/CompressedImage"
            }))

        # =============================================
        # Detection Topics
        # =============================================

        for topic in bbox_topics:

            self.ws.send(json.dumps({

                "op": "advertise",

                "topic": topic,

                "type": "std_msgs/String"
            }))


    # =====================================================
    # DETECT
    # =====================================================

    def detect(self, processed, ir):

        # =============================================
        # Extract data
        # =============================================


        full_frame = processed["full_frame"]

        roi_frame = processed["roi_frame"]

        roi_x = processed["roi_x"]

        roi_y = processed["roi_y"]

        # =============================================
        # Detector on ROI ONLY
        # =============================================

        boxes = self.detector.predict(
            roi_frame,
            draw=False
        )

        annotated = full_frame.copy()

        if ir:

            annotated = cv2.cvtColor(
                annotated,
                cv2.COLOR_RGB2GRAY
            )

            annotated = cv2.cvtColor(
                annotated,
                cv2.COLOR_GRAY2BGR
            )

        bbox_data = []

        h_roi, w_roi = roi_frame.shape[:2]

        # =============================================
        # Loop detections
        # =============================================

        for (xc, yc, bw, bh, score) in boxes:

            # =========================================
            # ROI coords
            # =========================================

            x1_roi = int(
                (xc - bw / 2) * w_roi
            )

            y1_roi = int(
                (yc - bh / 2) * h_roi
            )

            x2_roi = int(
                (xc + bw / 2) * w_roi
            )

            y2_roi = int(
                (yc + bh / 2) * h_roi
            )

            # =========================================
            # FULL FRAME coords
            # =========================================

            x1 = x1_roi + roi_x

            y1 = y1_roi + roi_y

            x2 = x2_roi + roi_x

            y2 = y2_roi + roi_y

            # =========================================
            # Distance
            # =========================================

            x_center = (x1 + x2) / 2

            y_bottom = y2

            result = (
                self.depth_estimator
                .distance_and_angle(
                    x_center,
                    y_bottom
                )
            )

            if result is None:
                continue

            distance, angle = result

            # =========================================
            # Save
            # =========================================

            bbox_data.append({

                "x1": float(x1),

                "y1": float(y1),

                "x2": float(x2),

                "y2": float(y2),

                "confidence": float(score),

                "distance": float(distance),

                "angle": float(angle),

                "class_id": 0
            })

            # =========================================
            # Draw
            # =========================================

            color = (180, 70, 20)

            cv2.rectangle(

                annotated,

                (x1, y1),

                (x2, y2),

                color,

                2
            )

            label = (

                f"{score:.2f} | "

                f"{distance:.2f}m | "

                f"{angle:.1f}deg"
            )

            cv2.putText(

                annotated,

                label,

                (x1, y1 - 10),

                cv2.FONT_HERSHEY_SIMPLEX,

                0.55,

                color,

                2
            )

        return annotated,roi_frame, bbox_data,


    # =====================================================
    # PUBLISH
    # =====================================================

    def publish(
        self,
        frame,
        detections,
        image_topic,
        detection_topic
    ):

        # =============================================
        # Publish Detections
        # =============================================

        if detection_topic is not None:

            self.ws.send(json.dumps({

                "op": "publish",

                "topic": detection_topic,

                "msg": {
                    "data": json.dumps(detections)
                }
            }))

        # =============================================
        # Encode Image
        # =============================================

        _, buffer = cv2.imencode(

            ".jpg",

            frame,

            [
                int(cv2.IMWRITE_JPEG_QUALITY),
                60
            ]
        )

        img_b64 = base64.b64encode(
            buffer
        ).decode("utf-8")

        # =============================================
        # Publish Image
        # =============================================

        self.ws.send(json.dumps({

            "op": "publish",

            "topic": image_topic,

            "msg": {

                "format": "jpeg",

                "data": img_b64
            }
        }))


    # =====================================================
    # RUN
    # =====================================================

    def run(self):

        self.camera_system.start()

        prev_time = time.time()

        while True:

            # =============================================
            # Get Frames
            # =============================================

            duckie_frame, pi_frame = self.camera_system.get_frames()
     
       
            if duckie_frame is None:
                continue

            if pi_frame is None:
                continue

            # =============================================
            # Detect
            # =============================================

            duckie_detected,roi ,duckie_boxes = (
                self.detect(
                    duckie_frame,False
                )
            )

            

            # =============================================
            # Publish
            # =============================================

            self.publish(

                duckie_detected,

                duckie_boxes,

                self.DUCKIE_IMAGE_TOPIC,

                self.DUCKIE_BBOX_TOPIC
            )

            self.publish(
                pi_frame,
                self.PI_IMAGE_TOPIC,
                self.PI_IMAGE_TOPIC,
                None
            )

            # =============================================
            # FPS
            # =============================================

            curr_time = time.time()

            fps = 1.0 / (
                curr_time - prev_time
            )

            prev_time = curr_time

            cv2.putText(
                duckie_detected,
                f"FPS: {fps:.1f}",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

            # =============================================
            # Display
            # =============================================

            cv2.imshow(
                "Duckie Detection",
                duckie_detected
            )

            cv2.imshow(
                "PI Detection",
                pi_frame
            )

            cv2.imshow(
                "Duckie ROI",
                roi
            )

            key = cv2.waitKey(1)

            if key == 27:
                break

        self.camera_system.stop()

        cv2.destroyAllWindows()


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    system = DetectionSystem()

    system.run()