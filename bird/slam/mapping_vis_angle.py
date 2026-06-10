#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import cv2
import numpy as np
import json

from sensor_msgs.msg import Image, CompressedImage
from geometry_msgs.msg import PoseStamped
from cv_bridge import CvBridge
from std_msgs.msg import String
from sensor_msgs.msg import Image

import tf.transformations as tft


class PoseVisualizerNode:

    def __init__(self):

        rospy.init_node('visualizer')

        self.bridge = CvBridge()

        # =========================================
        # MAP
        # =========================================
        self.node_map = {}

        # kare harita
        self.map_width = 350
        self.map_height = 350

        # 2m x 2m dünya
        self.world_width = 2.0
        self.world_height = 2.0

        self.margin = 1

        # ayrı scale
        self.scale_x = (
            self.map_width - 2*self.margin
        ) / self.world_width

        self.scale_y = (
            self.map_height - 2*self.margin
        ) / self.world_height

        # =========================================
        # ROBOT
        # =========================================
        self.robot_pose = None
        self.camera_image = None

        # =========================================
        # YOLO
        # =========================================
        self.bboxes = []

        # =========================================
        # HUMAN TRACKING
        # =========================================
        self.tracked_humans = {}

        self.next_human_id = 0

        # aynı insan kabul edilme mesafesi (metre)
        self.same_human_threshold = 0.3

        # timeout süresi
        self.human_timeout = 10.0

        # smoothing
        self.alpha = 0.7

        # =========================================
        # ROS
        # =========================================

        self.viz_pub = rospy.Publisher(
            "/bird/live_visualization/compressed",
            CompressedImage,
            queue_size=1
        )

        self.new_human_pub = rospy.Publisher(
            "/bird/new_human_detected",
            PoseStamped,
            queue_size=10
        )

        rospy.Subscriber(
            "/duckiebot/aruco_debug/image",
            Image,
            self.image_callback
        )

        rospy.Subscriber(
            "/bird/fused_pose",
            PoseStamped,
            self.pose_callback
        )

        rospy.Subscriber(
            "/duckie/detections",
            String,
            self.yolo_callback
        )

        rospy.Subscriber(
            "/bird/new_marker_detected",
            PoseStamped,
            self.marker_callback
        )

    # =========================================================
    # MARKER CALLBACK
    # =========================================================
    def marker_callback(self, msg):

        try:

            marker_id = int(msg.header.frame_id.strip())

            x = msg.pose.position.x
            y = msg.pose.position.y

            q = msg.pose.orientation

            _, _, yaw = tft.euler_from_quaternion(
                [q.x, q.y, q.z, q.w]
            )

            self.node_map[marker_id] = (x, y, yaw)

        except Exception as e:

            rospy.logwarn(f"Marker parse hatası: {e}")

    # =========================================================
    # YOLO CALLBACK
    # =========================================================
    def yolo_callback(self, msg):

        try:

            data = msg.data.strip()

            if data == "" or data == "[]":

                self.bboxes = []
                return

            self.bboxes = json.loads(data)

        except Exception as e:

            rospy.logwarn(f"YOLO parse hatası: {e}")
            self.bboxes = []

    # =========================================================
    # POSE CALLBACK
    # =========================================================
    def pose_callback(self, msg):

        self.robot_pose = msg

    # =========================================================
    # IMAGE CALLBACK
    # =========================================================
    def image_callback(self, msg):

        try:

            self.camera_image = self.bridge.imgmsg_to_cv2(
                msg,
                "bgr8"
            )

            self.create_visualization()

        except Exception as e:

            rospy.logerr(f"Görsel işleme hatası: {e}")

    # =========================================================
    # WORLD TO PIXEL
    # =========================================================
    def world_to_pixel(self, x, y):

        px = int(x * self.scale_x) + self.margin

        py = int(
            self.map_height
            - (y * self.scale_y)
            - self.margin
        )

        return (px, py)

    # =========================================================
    # HUMAN LOCALIZATION
    # =========================================================
    def human_localization(self, x, y):

        best_dist = 999999

        # mevcut insanlarla karşılaştır
        for hid, human in self.tracked_humans.items():

            hx = human["x"]
            hy = human["y"]

            dist = np.sqrt((x - hx) ** 2 + (y - hy) ** 2)

            if dist < best_dist:
                best_dist = dist

        # =========================================
        # AYNI İNSAN -> UPDATE ETME
        # =========================================
        if best_dist < self.same_human_threshold:
            #rospy.loginfo(f"aynı insan")
            return

        # =========================================
        # YENİ İNSAN
        # =========================================
        else:

            human_id = self.next_human_id

            self.tracked_humans[human_id] = {

                "x": x,
                "y": y
            }

            # =========================================
            # PUBLISH NEW HUMAN
            # =========================================
            msg = PoseStamped()

            # timestamp
            msg.header.stamp = rospy.Time.now()

            # id bilgisini frame_id içine koyuyoruz
            msg.header.frame_id = str(human_id)

            # position
            msg.pose.position.x = x
            msg.pose.position.y = y
            msg.pose.position.z = 0.0

            # orientation kullanılmıyor
            msg.pose.orientation.w = 1.0

            self.new_human_pub.publish(msg)

            rospy.loginfo(f"Yeni insan bulundu -> H{human_id}")

            self.next_human_id += 1

    # =========================================================
    # DRAW CONE
    # =========================================================
    def draw_cone(self, img, rx, ry, yaw):

        angle_offset = np.deg2rad(15)

        color = (0, 255, 0)

        length = 250

        left_angle = yaw + angle_offset
        right_angle = yaw - angle_offset

        lx = int(rx + length * np.cos(left_angle))
        ly = int(ry - length * np.sin(left_angle))

        rx2 = int(rx + length * np.cos(right_angle))
        ry2 = int(ry - length * np.sin(right_angle))

        h, w = img.shape[:2]

        lx = np.clip(lx, 0, w - 1)
        ly = np.clip(ly, 0, h - 1)

        rx2 = np.clip(rx2, 0, w - 1)
        ry2 = np.clip(ry2, 0, h - 1)

        pts = np.array([
            [rx, ry],
            [lx, ly],
            [rx2, ry2]
        ], np.int32)

        pts = pts.reshape((-1, 1, 2))

        overlay = img.copy()

        cv2.fillPoly(overlay, [pts], color)

        alpha = 0.3

        cv2.addWeighted(
            overlay,
            alpha,
            img,
            1 - alpha,
            0,
            img
        )

    # =========================================================
    # DRAW MARKER ICON
    # =========================================================
    def draw_marker_icon(self, img, center, yaw, marker_id):

        cx, cy = center

        size = 24
        half = size // 2

        # dış siyah kare
        cv2.rectangle(
            img,
            (cx - half, cy - half),
            (cx + half, cy + half),
            (0, 0, 0),
            -1
        )

        # iç beyaz kare
        inner = int(size * 0.7) // 2

        cv2.rectangle(
            img,
            (cx - inner, cy - inner),
            (cx + inner, cy + inner),
            (255, 255, 255),
            -1
        )

        # ortadaki siyah kare
        inner2 = int(size * 0.35) // 2

        cv2.rectangle(
            img,
            (cx - inner2, cy - inner2),
            (cx + inner2, cy + inner2),
            (0, 0, 0),
            -1
        )

        # yön oku
        arrow_len = 25

        ax = int(cx + arrow_len * np.cos(yaw))
        ay = int(cy - arrow_len * np.sin(yaw))

        cv2.arrowedLine(
            img,
            (cx, cy),
            (ax, ay),
            (0, 255, 0),
            2,
            tipLength=0.3
        )

        # marker id
        cv2.putText(
            img,
            f"A{marker_id}",
            (cx - 12, cy + half + 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )

    # =========================================================
    # VISUALIZATION
    # =========================================================
    def create_visualization(self):

        if self.camera_image is None:
            return

        # =========================================
        # MAP BG
        # =========================================
        map_img = np.full(
            (self.map_height, self.map_width, 3),
            (40, 40, 45),
            dtype=np.uint8
        )

        # =========================================
        # WALLS
        # =========================================
        wall_thickness = 20
        wall_color = (80, 80, 80)

        m = self.margin

        cv2.rectangle(
            map_img,
            (m, m),
            (self.map_width - m, self.map_height - m),
            wall_color,
            wall_thickness
        )

        # =========================================
        # MARKERS
        # =========================================
        for node_id, (x, y, yaw) in self.node_map.items():

            center = self.world_to_pixel(x, y)

            self.draw_marker_icon(
            map_img,
            center,
            yaw,
            node_id
            )

            yaw_deg = np.degrees(yaw)

            cv2.putText(
                map_img,
                f"A{node_id}",
                (center[0] + 10, center[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1
            )

            cv2.putText(
                map_img,
                f"{yaw_deg:.1f}",
                (center[0] + 10, center[1] + 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (200, 255, 200),
                1
            )

            arrow_len = 25

            ax = int(center[0] + arrow_len * np.cos(yaw))
            ay = int(center[1] - arrow_len * np.sin(yaw))

            cv2.line(
                map_img,
                center,
                (ax, ay),
                (0, 255, 0),
                2
            )

        # =========================================
        # ROBOT
        # =========================================
        if self.robot_pose is not None:

            rx_world = self.robot_pose.pose.position.x * 0.9
            ry_world = self.robot_pose.pose.position.y * 0.9

            rx, ry = self.world_to_pixel(
                rx_world,
                ry_world
            )

            q = self.robot_pose.pose.orientation

            _, _, yaw = tft.euler_from_quaternion(
                [q.x, q.y, q.z, q.w]
            )

            cv2.circle(
                map_img,
                (rx, ry),
                10,
                (0, 200, 255),
                -1
            )

            arrow_len = 30

            ax = int(rx + arrow_len * np.cos(yaw))
            ay = int(ry - arrow_len * np.sin(yaw))

            cv2.line(
                map_img,
                (rx, ry),
                (ax, ay),
                (0, 255, 255),
                3
            )

            self.draw_cone(map_img, rx, ry, yaw)

        # =========================================
        # YOLO HUMAN LOCALIZATION
        # =========================================
        if self.robot_pose is not None and len(self.bboxes) > 0:

            rx_world = self.robot_pose.pose.position.x * 0.9
            ry_world = self.robot_pose.pose.position.y * 0.9

            q = self.robot_pose.pose.orientation

            _, _, yaw = tft.euler_from_quaternion(
                [q.x, q.y, q.z, q.w]
            )

            for box in self.bboxes:

                d = box.get("distance", None)
                    
                # 30 cm'den uzaktaki insanları yok say
                if d > 0.30:
                    continue

                if d is None:
                    continue

                angle_deg = box.get("angle", None)

                if angle_deg is None:
                    continue

                angle_rad = np.deg2rad(angle_deg)

                global_angle = yaw + (np.pi / 2 - angle_rad)

                bx_world = rx_world + d * np.cos(global_angle)
                by_world = ry_world + d * np.sin(global_angle)

                # =========================================
                # MAP BOUNDARY CHECK
                # =========================================
                if (
                    bx_world < 0 or
                    bx_world > self.world_width or
                    by_world < 0 or
                    by_world > self.world_height
                ):
                    continue

                self.human_localization(
                    bx_world,
                    by_world
                )
                

        # =========================================
        # DRAW TRACKED HUMANS
        # =========================================
        for hid, human in self.tracked_humans.items():

            hx = human["x"]
            hy = human["y"]

            px, py = self.world_to_pixel(hx, hy)

            cv2.circle(
                map_img,
                (px, py),
                10,
                (0, 0, 255),
                -1
            )

            cv2.putText(
                map_img,
                f"H{hid}",
                (px + 10, py - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

        # =========================================
        # CAMERA + MAP
        # =========================================
        h, w = self.camera_image.shape[:2]

        scale_ratio = self.map_height / h

        cam_resized = cv2.resize(
            self.camera_image,
            (int(w * scale_ratio), self.map_height)
        )

        combined = np.hstack((cam_resized, map_img))

        msg = self.bridge.cv2_to_compressed_imgmsg(
            combined,
            dst_format='jpg'
        )

        self.viz_pub.publish(msg)


# =========================================================
# MAIN
# =========================================================
if __name__ == '__main__':

    try:

        node = PoseVisualizerNode()

        rospy.spin()

    except rospy.ROSInterruptException:
        pass