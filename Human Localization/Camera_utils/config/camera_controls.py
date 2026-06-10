import json
import os


# =====================================================
# SETTINGS FILE
# =====================================================

SETTINGS_FILE = "camera_controls.json"


# =====================================================
# DEFAULTS
# =====================================================

DEFAULT_CAMERA_CONTROLS = {

    "zoom": 184,

    "x_offset": 50,

    "y_offset": 57,

    "bottom_crop": 26,

    "sharpness": 136,

    "detail": 0
}


# =====================================================
# LOAD
# =====================================================

def load_camera_controls():

    settings = DEFAULT_CAMERA_CONTROLS.copy()

    if os.path.exists(SETTINGS_FILE):

        with open(SETTINGS_FILE, "r") as f:

            data = json.load(f)

        settings.update(data)

        print("[INFO] Camera controls loaded")

    return settings


# =====================================================
# SAVE
# =====================================================

def save_camera_controls(settings):

    with open(SETTINGS_FILE, "w") as f:

        json.dump(
            settings,
            f,
            indent=4
        )

    print("[INFO] Camera controls saved")