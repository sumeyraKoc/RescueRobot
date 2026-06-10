import threading
import cv2

from Camera_utils.cameras.stream_reader import StreamReader


# =====================================================
# TCP CAMERA
# =====================================================

class TCPCamera:

    def __init__(
        self,
        url,
        width,
        height,
        buffer
    ):

        # =================================================
        # Stream Reader
        # =================================================

        self.reader = StreamReader(
            url,
            width,
            height
        )

        # =================================================
        # Shared Buffer
        # =================================================

        self.buffer = buffer

        # =================================================
        # Thread Control
        # =================================================

        self.running = False
        self.thread = None


    # =====================================================
    # START
    # =====================================================

    def start(self):

        if self.running:
            return

        self.running = True

        self.thread = threading.Thread(
            target=self.capture_loop,
            daemon=True
        )

        self.thread.start()

        print("[INFO] TCP camera started")


    # =====================================================
    # STOP
    # =====================================================

    def stop(self):

        self.running = False

        print("[INFO] TCP camera stopped")


    # =====================================================
    # CAPTURE LOOP
    # =====================================================

    def capture_loop(self):

        while self.running:

            try:

                # =========================================
                # Read Frame
                # =========================================

                frame = self.reader.read_frame()

                if frame is None:
                    continue

                # =========================================
                # Rotate
                # =========================================

                frame = cv2.rotate(
                    frame,
                    cv2.ROTATE_180
                )

                # =========================================
                # Resize to Duckie Resolution
                # =========================================

                frame = cv2.resize(
                    frame,
                    (640, 480)
                )

                # =========================================
                # Convert to IR-like image
                # =========================================

                gray = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2GRAY
                )

                # Soft CLAHE
                clahe = cv2.createCLAHE(
                    clipLimit=1.2,
                    tileGridSize=(12, 12)
                )

                gray = clahe.apply(gray)

                # Very soft blur
                gray = cv2.GaussianBlur(
                    gray,
                    (3, 3),
                    0.5
                )
                # =========================================
                # Update Shared Buffer
                # =========================================

                self.buffer.update(gray)

            except Exception as e:

                print("[TCPCamera ERROR]", e)