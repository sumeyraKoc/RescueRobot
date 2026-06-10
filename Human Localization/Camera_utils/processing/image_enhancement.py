import cv2


# =====================================================
# DETAIL ENHANCEMENT
# =====================================================

def enhance_detail(frame, detail):

    if detail <= 0:
        return frame

    return cv2.detailEnhance(
        frame,
        sigma_s=detail,
        sigma_r=0.15
    )


# =====================================================
# SHARPEN
# =====================================================

def sharpen(frame, sharpness):

    blurred = cv2.GaussianBlur(
        frame,
        (0, 0),
        1.0
    )

    sharpened = cv2.addWeighted(
        frame,
        1.0 + sharpness,
        blurred,
        -sharpness,
        0
    )

    return sharpened