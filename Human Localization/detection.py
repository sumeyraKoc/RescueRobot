#!/usr/bin/env python3

import websocket
import json
import base64
import cv2
import numpy as np
from ultralytics import YOLO
import threading
import time
from HomographyDistanceEstimator import HomographyDistanceEstimator
from Inference import PersonDetector
# -----------------------------
# CONFIG
# -----------------------------
WS_URL = "ws://10.85.249.100:9001"

SUB_TOPIC = "/bird/camera_node/image/compressed"
PUB_IMAGE_TOPIC = "/yolo/image/compressed"
PUB_BBOX_TOPIC = "/yolo/bboxes"

# -----------------------------
# MODEL
# -----------------------------
model = YOLO("yolov8n.pt")

# -----------------------------
# SHARED FRAME BUFFER
# -----------------------------
latest_frame = None
lock = threading.Lock()

# -----------------------------
# CAMERA CALIBRATION
# -----------------------------
K = np.array([
    [358.4449764374496, 0.0, 330.49169468278836],
    [0.0, 346.4352060043585, 312.76086485966465],
    [0.0, 0.0, 1.0]
])

D = np.array([
    -0.28357366125833844,
     0.04198648852969383,
    -0.024006486344252245,
    -6.450971385675886e-05,
     0.0
])

h, w = 480, 640

# -----------------------------
# HOMOGRAPHY
# -----------------------------
H = [
    -3.944251854896834e-05, 0.000244465300969488, 0.3525628062426299,
    -0.0015625521124053067, 8.221648302865118e-05, 0.4953884314142318,
    -1.0725377094867827e-05, 0.010420490862005964, -1.5438629450394505
]

depth_estimator = HomographyDistanceEstimator(
    H,
    K=K,
    D=D,
    kx=1.0,
    ky=1.0
)

# -----------------------------
# RECEIVE FROM ROS
# -----------------------------
def on_message(ws, message):
    global latest_frame 

    try:
        data = json.loads(message)

        if "msg" not in data:
            return

        img_b64 = data["msg"]["data"]
        img_bytes = base64.b64decode(img_b64)

        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return

        with lock:
            latest_frame = frame

    except Exception as e:
        print("Decode error:", e)

# -----------------------------
# YOLO + PROCESS LOOP
# -----------------------------
def process_loop(ws):
    global latest_frame

    while True:
        frame = None

        with lock:
            if latest_frame is not None:
                frame = latest_frame.copy()
                latest_frame = None

        if frame is None:
            time.sleep(0.001)
            continue

        # Resize
        frame = cv2.resize(frame, (w, h))

        # YOLO
     

        detector = PersonDetector("/home/mert/Desktop/RHL/best_test.pth", device="cuda")

        boxes = detector.predict(frame, draw=False)

        annotated = frame.copy()
        bboxes = []

        h_img, w_img = frame.shape[:2]

        for (xc, yc, bw, bh, score) in boxes:

            # convert normalized xywh → pixel xyxy
            x1 = (xc - bw / 2) * w_img
            y1 = (yc - bh / 2) * h_img
            x2 = (xc + bw / 2) * w_img
            y2 = (yc + bh / 2) * h_img

            x_center = (x1 + x2) / 2

            # 🔥 same foot-point logic
            y_bottom = y2 - (y2 - y1) * 0.07

            result = depth_estimator.distance_and_angle(x_center, y_bottom)

            if result is None:
                continue

            distance, angle = result

            bboxes.append({
                "x1": float(x1),
                "y1": float(y1),
                "x2": float(x2),
                "y2": float(y2),
                "confidence": float(score),
                "class_id": 0,  # only person
                "distance": distance,
                "angle": angle
            })

            # Draw box
            cv2.rectangle(
                annotated,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                (0, 255, 0),
                2
            )

            # Draw distance + angle
            cv2.putText(
                annotated,
                f"{distance:.2f}m | {angle:.1f}°",
                (int(x1), int(y1) - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )

        # -----------------------------
        # PUBLISH BBOX
        # -----------------------------
        ws.send(json.dumps({
            "op": "publish",
            "topic": PUB_BBOX_TOPIC,
            "msg": {
                "data": json.dumps(bboxes)
            }
        }))

        # -----------------------------
        # PUBLISH IMAGE
        # -----------------------------
        _, buffer = cv2.imencode(
            ".jpg",
            annotated,
            [int(cv2.IMWRITE_JPEG_QUALITY), 60]
        )

        img_b64 = base64.b64encode(buffer).decode("utf-8")

        ws.send(json.dumps({
            "op": "publish",
            "topic": PUB_IMAGE_TOPIC,
            "msg": {
                "format": "jpeg",
                "data": img_b64
            }
        }))

        cv2.imshow("YOLO OUTPUT", annotated)
        cv2.waitKey(1)

# -----------------------------
# WS EVENTS
# -----------------------------
def on_open(ws):
    print("Connected to ROSBridge")

    ws.send(json.dumps({
        "op": "advertise",
        "topic": PUB_IMAGE_TOPIC,
        "type": "sensor_msgs/CompressedImage"
    }))

    ws.send(json.dumps({
        "op": "advertise",
        "topic": PUB_BBOX_TOPIC,
        "type": "std_msgs/String"
    }))

    ws.send(json.dumps({
        "op": "subscribe",
        "topic": SUB_TOPIC,
        "queue_length": 1,
        "throttle_rate": 0
    }))

    threading.Thread(target=process_loop, args=(ws,), daemon=True).start()

def on_error(ws, error):
    print("Error:", error)

def on_close(ws, code, msg):
    print("Closed:", msg)

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        WS_URL,
        on_message=on_message,
        on_open=on_open,
        on_error=on_error,
        on_close=on_close
    )

    ws.run_forever()