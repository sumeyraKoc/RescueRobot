import numpy as np
import cv2

class HomographyDistanceEstimator:
    def __init__(self, H, K, D, kx=1.0, ky=1.0, y_offset=0.0):
        self.H = np.array(H).reshape(3, 3)

        if abs(self.H[2, 2]) > 1e-8:
            self.H = self.H / self.H[2, 2]
        else:
            self.H = self.H / np.linalg.norm(self.H)

        self.K = np.array(K).reshape(3, 3)
        self.D = np.array(D).flatten()

        self.kx = kx
        self.ky = ky
        self.y_offset = y_offset

    

    def undistort_point(self, u, v):
        pts = np.array([[[u, v]]], dtype=np.float32)
        und = cv2.undistortPoints(pts, self.K, self.D)
        x, y = und[0, 0]

        u_corr = x * self.K[0, 0] + self.K[0, 2]
        v_corr = y * self.K[1, 1] + self.K[1, 2]

        return float(u_corr), float(v_corr)

    def image_to_ground(self, u, v):
        u, v = self.undistort_point(u, v)

        pt = np.array([u, v, 1.0])
        g = self.H @ pt

        if abs(g[2]) < 1e-6:
            return None

        X = (g[0] / g[2]) * self.kx
        Y = (g[1] / g[2]) * self.ky

        return X, Y

    def distance_and_angle(self, u, v):
        coords = self.image_to_ground(u, v)
        if coords is None:
            return None

        X_raw, Y = coords

        # 🔥 compute angle from raw X,Y
        angle = float(np.degrees(np.arctan2(X_raw, Y)))

        # 🔥 recompute X using Y + angle (trusted)
        rad = np.radians(angle)
        distance = Y / np.cos(rad)


        return distance, angle