import websocket
import base64
import cv2
import numpy as np
import threading
import json
import socket


# =====================================================
# DUCKIE CAMERA
# =====================================================

class DuckieCamera:

    def __init__(
        self,
        ws_url,
        topic,
        buffer
    ):

        self.ws_url = ws_url
        self.topic = topic
        self.buffer = buffer

        self.ws = None
        self.thread = None

        self.running = False


    # =====================================================
    # START
    # =====================================================

    def start(self):

        websocket.enableTrace(False)

        self.running = True

        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

        self.thread = threading.Thread(
            target=self.websocket_loop,
            daemon=True
        )

        self.thread.start()


    # =====================================================
    # STOP
    # =====================================================

    def stop(self):

        self.running = False

        if self.ws is not None:
            self.ws.close()

        print("[INFO] Duckie camera stopped")


    # =====================================================
    # WEBSOCKET LOOP
    # =====================================================

    def websocket_loop(self):

        while self.running:

            try:

                self.ws.run_forever(
                    ping_interval=0,
                    skip_utf8_validation=True
                )

            except Exception as e:

                print("[DuckieCamera WS ERROR]", e)


    # =====================================================
    # ON OPEN
    # =====================================================

    def on_open(self, ws):

        try:

            sock = ws.sock.sock

            sock.setsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_NODELAY,
                1
            )

        except Exception as e:

            print("[DuckieCamera Socket ERROR]", e)

        subscribe_message = {
            "op": "subscribe",
            "topic": self.topic,
            "queue_length": 1,
            "throttle_rate": 0
        }

        ws.send(
            json.dumps(subscribe_message)
        )

        print("[INFO] Duckie camera connected")


    # =====================================================
    # ON MESSAGE
    # =====================================================

    def on_message(self, ws, message):

        try:

            data = json.loads(message)

            if "msg" not in data:
                return

            if "data" not in data["msg"]:
                return

            image_base64 = data["msg"]["data"]

            image_bytes = base64.b64decode(
                image_base64
            )

            np_array = np.frombuffer(
                image_bytes,
                dtype=np.uint8
            )

            frame = cv2.imdecode(
                np_array,
                cv2.IMREAD_COLOR
            )

            if frame is None:
                return

            # =============================================
            # Update Shared Buffer
            # =============================================

            self.buffer.update(frame)

        except Exception as e:

            print("[DuckieCamera Decode ERROR]", e)


    # =====================================================
    # ON ERROR
    # =====================================================

    def on_error(self, ws, error):

        print("[DuckieCamera ERROR]", error)


    # =====================================================
    # ON CLOSE
    # =====================================================

    def on_close(self, ws, close_status_code, close_msg):

        print("[INFO] Duckie camera disconnected")