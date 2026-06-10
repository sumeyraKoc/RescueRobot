import cv2
import json
import time
import base64
import websocket
import threading
import numpy as np
import supervision as sv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent

sys.path.append(str(ROOT))

from Camera_utils.cameras.camera_system import (
    CameraSystem
)

from Inference import PersonDetector

from Human_localization.DistanceEstimator import (
    HomographyDistanceEstimator
)

from Camera_utils.calibration.duckie_calibration import (
    K,
    D
)

from Camera_utils.config.ros_config import (
    ROS_WS
)

# =====================================================
# TENT WRAPPER
# =====================================================

class TentAdapter:

    def __init__(self, model):

        self.model = model


    def adapt(self, frame):

        # insert TENT adaptation here

        return frame
    
# =====================================================
# VISUALIZATION THREAD
# =====================================================

class VisualizationThread:

    def __init__(self):

        self.lock = threading.Lock()

        self.frame = None

        self.running = False


    def update(self, frame):

        with self.lock:

            self.frame = frame


    def start(self):

        self.running = True

        thread = threading.Thread(
            target=self.loop,
            daemon=True
        )

        thread.start()


    def loop(self):

        while self.running:

            with self.lock:

                frame = self.frame

            if frame is None:

                time.sleep(0.01)

                continue

            cv2.imshow(
                "Detection",
                frame
            )

            if cv2.waitKey(1) == 27:
                break

# =====================================================
# DETECTION SYSTEM
# =====================================================

class DetectionSystem:

    def __init__(self):

        # =============================================
        # Camera System
        # =============================================

        self.camera_system = CameraSystem()

        # =============================================
        # Detector
        # =============================================

        self.detector = PersonDetector(
            "/home/mert/Desktop/RoboticsProject/Human Localization/best_test.pth",
            device="cuda"
        )

        # =============================================
        # TENT
        # =============================================

        self.tent = TentAdapter(
            self.detector
        )

        # =============================================
        # Tracker
        # =============================================

        self.tracker = sv.ByteTrack()

        # =============================================
        # Visualization
        # =============================================

        self.visualization = VisualizationThread()

        # =============================================
        # Homography
        # =============================================

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

        # =============================================
        # ROS
        # =============================================

        self.ws = websocket.create_connection(
            ROS_WS
        )

        self.DUCKIE_IMAGE_TOPIC = (
            "/duckie/detection/image/compressed"
        )

        self.DUCKIE_BBOX_TOPIC = (
            "/duckie/detections"
        )

        self.advertise_topics()


    # =================================================
    # ADVERTISE
    # =================================================

    def advertise_topics(self):

        self.ws.send(json.dumps({

            "op": "advertise",

            "topic": self.DUCKIE_IMAGE_TOPIC,

            "type": "sensor_msgs/CompressedImage"
        }))

        self.ws.send(json.dumps({

            "op": "advertise",

            "topic": self.DUCKIE_BBOX_TOPIC,

            "type": "std_msgs/String"
        }))


    # =================================================
    # DETECT
    # =================================================

    def detect(self, processed):

        full_frame = processed["full_frame"]

        roi_frame = processed["roi_frame"]

        roi_x = processed["roi_x"]

        roi_y = processed["roi_y"]

        # =============================================
        # TENT
        # =============================================

        roi_frame = self.tent.adapt(
            roi_frame
        )

        # =============================================
        # Detection
        # =============================================

        boxes = self.detector.predict(
            roi_frame,
            draw=False
        )

        h_roi, w_roi = roi_frame.shape[:2]

        detections = []

        for (xc, yc, bw, bh, score) in boxes:

            x1_roi = int((xc - bw / 2) * w_roi)
            y1_roi = int((yc - bh / 2) * h_roi)
            x2_roi = int((xc + bw / 2) * w_roi)
            y2_roi = int((yc + bh / 2) * h_roi)

            x1 = x1_roi + roi_x
            y1 = y1_roi + roi_y
            x2 = x2_roi + roi_x
            y2 = y2_roi + roi_y

            detections.append([
                x1,
                y1,
                x2,
                y2,
                score
            ])

        if len(detections) == 0:

            return full_frame, []

        detections = np.array(detections)

        tracker_input = sv.Detections(
            xyxy=detections[:, :4],
            confidence=detections[:, 4]
        )

        tracks = self.tracker.update_with_detections(
            tracker_input
        )

        annotated = full_frame.copy()

        result = []

        for i in range(len(tracks)):

            x1, y1, x2, y2 = tracks.xyxy[i]

            track_id = int(
                tracks.tracker_id[i]
            )

            confidence = float(
                tracks.confidence[i]
            )

            x_center = (x1 + x2) / 2

            y_bottom = y2

            distance_result = (
                self.depth_estimator
                .distance_and_angle(
                    x_center,
                    y_bottom
                )
            )

            if distance_result is None:
                continue

            distance, angle = distance_result

            result.append({

                "track_id": track_id,

                "x1": float(x1),
                "y1": float(y1),
                "x2": float(x2),
                "y2": float(y2),

                "confidence": confidence,

                "distance": float(distance),

                "angle": float(angle)
            })

            cv2.rectangle(
                annotated,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                (0, 255, 0),
                2
            )

            label = (
                f"ID {track_id} | "
                f"{distance:.2f}m | "
                f"{angle:.1f}deg"
            )

            cv2.putText(
                annotated,
                label,
                (int(x1), int(y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )

        return annotated, result
    
    # =================================================
    # PUBLISH
    # =================================================

    def publish(self, frame, detections):

        self.ws.send(json.dumps({

            "op": "publish",

            "topic": self.DUCKIE_BBOX_TOPIC,

            "msg": {
                "data": json.dumps(detections)
            }
        }))

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

        self.ws.send(json.dumps({

            "op": "publish",

            "topic": self.DUCKIE_IMAGE_TOPIC,

            "msg": {

                "format": "jpeg",

                "data": img_b64
            }
        }))


    # =================================================
    # RUN
    # =================================================

    def run(self):

        self.camera_system.start()

        self.visualization.start()

        prev_time = time.time()

        while True:

            processed = (
                self.camera_system
                .get_frames()
            )

            if processed is None:

                time.sleep(0.01)

                continue

            annotated, detections = (
                self.detect(processed)
            )

            self.publish(
                annotated,
                detections
            )

            curr_time = time.time()

            fps = 1.0 / (
                curr_time - prev_time
            )

            prev_time = curr_time

            cv2.putText(
                annotated,
                f"FPS: {fps:.1f}",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

            self.visualization.update(
                annotated
            )

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    system = DetectionSystem()

    system.run()