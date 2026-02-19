from fastapi import FastAPI, WebSocket
import asyncio
import base64
import cv2
import numpy as np
import math
import time

app = FastAPI()

# open simulation video
video = cv2.VideoCapture("video.mp4")

robot_x = 300
robot_y = 300
theta = 0


def get_video_frame():

    global video

    ret, frame = video.read()

    # video bittiyse başa sar
    if not ret:

        video.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = video.read()

    # optional overlay text
    cv2.putText(frame, "Simulation Camera Feed",
                (20,40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0,255,0),
                2)

    _, buffer = cv2.imencode('.jpg', frame)

    return base64.b64encode(buffer).decode('utf-8')


def generate_fake_humans():

    t = time.time()

    return [
        {
            "x": 200 + 100 * math.sin(t),
            "y": 200 + 100 * math.cos(t)
        },
        {
            "x": 400 + 50 * math.sin(t * 0.5),
            "y": 300 + 50 * math.cos(t * 0.5)
        }
    ]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    global robot_x, robot_y, theta

    await websocket.accept()

    while True:

        theta += 0.05

        robot_x = 300 + 150 * math.cos(theta)
        robot_y = 300 + 150 * math.sin(theta)

        data = {
            "pose": {
                "x": robot_x,
                "y": robot_y,
                "theta": theta
            },
            "humans": generate_fake_humans(),
            "frame": get_video_frame()
        }

        await websocket.send_json(data)

        await asyncio.sleep(0.033)  # 30 FPS
