import subprocess
import numpy as np


# =====================================================
# STREAM READER
# =====================================================

class StreamReader:

    def __init__(
        self,
        url,
        width,
        height
    ):

        # =================================================
        # Dimensions
        # =================================================

        self.width = width
        self.height = height

        self.frame_size = (
            width *
            height *
            3
        )

        # =================================================
        # FFMPEG COMMAND
        # =================================================

        self.command = [

            "ffmpeg",

            "-fflags", "nobuffer",

            "-flags", "low_delay",

            "-f", "h264",

            "-i", url,

            "-vf",
            f"fps=30,scale={width}:{height}",

            "-pix_fmt", "bgr24",

            "-vcodec", "rawvideo",

            "-an",

            "-sn",

            "-dn",

            "-f", "rawvideo",

            "-"
        ]

        # =================================================
        # START PIPE
        # =================================================

        self.pipe = subprocess.Popen(

            self.command,

            stdout=subprocess.PIPE,

            stderr=subprocess.DEVNULL,

            bufsize=10**6
        )

        print("[INFO] StreamReader started")


    # =====================================================
    # READ EXACT
    # =====================================================

    def read_exact(self, size):

        buffer = b''

        while len(buffer) < size:

            chunk = self.pipe.stdout.read(
                size - len(buffer)
            )

            if not chunk:
                return None

            buffer += chunk

        return buffer


    # =====================================================
    # READ FRAME
    # =====================================================

    def read_frame(self):

        raw_frame = self.read_exact(
            self.frame_size
        )

        if raw_frame is None:
            return None

        frame = np.frombuffer(
            raw_frame,
            dtype=np.uint8
        )

        frame = frame.reshape(
            (
                self.height,
                self.width,
                3
            )
        )

        return frame.copy()


    # =====================================================
    # CLOSE
    # =====================================================

    def close(self):

        if self.pipe is not None:

            self.pipe.kill()

            self.pipe.wait()

        print("[INFO] StreamReader closed")