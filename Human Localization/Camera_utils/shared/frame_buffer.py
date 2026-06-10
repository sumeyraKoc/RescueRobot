import threading


# =====================================================
# FRAME BUFFER
# =====================================================

class FrameBuffer:

    def __init__(self):

        self.lock = threading.Lock()

        self.frame = None


    # =====================================================
    # UPDATE FRAME
    # =====================================================

    def update(self, frame):

        with self.lock:

            self.frame = frame.copy()


    # =====================================================
    # GET FRAME
    # =====================================================

    def get(self):

        with self.lock:
         
            if self.frame is None:
                return None

            return self.frame.copy()


    # =====================================================
    # CLEAR
    # =====================================================

    def clear(self):

        with self.lock:

            self.frame = None