import websocket
import json
import base64
import cv2
import numpy as np

def on_message(ws, message):
    data = json.loads(message)

    if "msg" in data:
        img_b64 = data["msg"]["data"]
        img_bytes = base64.b64decode(img_b64)

        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        cv2.imshow("ROS Camera", frame)
        cv2.waitKey(1)

ws = websocket.WebSocketApp(
    "ws://172.17.8.100:9001",
    on_message=on_message
)

# subscribe to topic
def on_open(ws):
    sub_msg = {
        "op": "subscribe",
        "topic": "/bird/camera_node/image/compressed"
    }
    ws.send(json.dumps(sub_msg))

ws.on_open = on_open
ws.run_forever()