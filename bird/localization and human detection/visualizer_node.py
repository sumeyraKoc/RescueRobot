#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image, CompressedImage # CompressedImage eklendi
from geometry_msgs.msg import PoseStamped
from cv_bridge import CvBridge
import tf.transformations as tft
from std_msgs.msg import String
import json

class PoseVisualizerNode:
    def __init__(self):
        rospy.init_node('as3_visualize')
        self.bridge = CvBridge()

        # Harita Verileri
        # SADECE BUNLAR KALACAK
        self.node_map = {
            0: (0,0),
            7: (3,1),
            13: (1,3),
            15: (3,3)  # 16 yoktu, en yakın bu
        }
        # Görsel Parametreleri
        self.map_size = 600  
        self.offset = 100    
        self.scale = 100     
        
        self.robot_pose = None
        self.camera_image = None


        # Subscriberlar
        rospy.Subscriber("/duckiebot/aruco_debug/image", Image, self.image_callback)
        rospy.Subscriber("/bird/fused_pose", PoseStamped, self.pose_callback)
        rospy.Subscriber("/yolo/bboxes", String, self.yolo_callback)

        # Publisher - CompressedImage olarak değiştirildi
        self.viz_pub = rospy.Publisher("/bird/live_visualization/compressed", CompressedImage, queue_size=1)

        self.human=False
    def yolo_callback(self, msg):
        try:
            data = msg.data.strip()

            # Boş string kontrolü (bazen direkt "" gelebilir)
            if data == "" or data == "[]":
                self.human = False
                return

            # JSON parse
            boxes = json.loads(data)

            # Liste boş mu dolu mu?
            if isinstance(boxes, list) and len(boxes) > 0:
                self.human = True
            else:
                self.human = False

        except Exception as e:
            rospy.logwarn(f"YOLO parse hatası: {e}")
            self.human = False
            
    def pose_callback(self, msg):
        self.robot_pose = msg
        
    def image_callback(self, msg):
        try:
            self.camera_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            self.create_visualization()
        except Exception as e:
            rospy.logerr(f"Görsel işleme hatası: {e}")

    def world_to_pixel(self, x, y):
        max_y = 3
        px = int(self.offset + x * self.scale)
        py = int(self.offset + (max_y-y) * self.scale)
        return (px, py)
    
    def draw_cone(self, img, rx, ry, yaw):
        angle_offset = np.deg2rad(15)

        if self.human:
            color = (0, 255, 0)
        else:
            color = (0, 0, 255)

        length = 250

        left_angle = yaw + angle_offset
        right_angle = yaw - angle_offset

        lx = int(rx + length * np.cos(left_angle))
        ly = int(ry - length * np.sin(left_angle))

        rx2 = int(rx + length * np.cos(right_angle))
        ry2 = int(ry - length * np.sin(right_angle))

        h, w = img.shape[:2]
        lx = np.clip(lx, 0, w-1)
        ly = np.clip(ly, 0, h-1)
        rx2 = np.clip(rx2, 0, w-1)
        ry2 = np.clip(ry2, 0, h-1)

        pts = np.array([[rx, ry], [lx, ly], [rx2, ry2]], np.int32)
        pts = pts.reshape((-1, 1, 2))

        # 🔹 Overlay oluştur
        overlay = img.copy()

        # 🔹 Koniyi overlay'e çiz
        cv2.fillPoly(overlay, [pts], color)

        # 🔹 Alpha blending (şeffaflık burada ayarlanır)
        alpha = 0.3  # 0.0 = tamamen şeffaf, 1.0 = tamamen opak
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img) 

    def create_visualization(self):
        if self.camera_image is None:
            return

        # ===== 1. Arkaplan (kirli beton rengi) =====
        map_img = np.full((self.map_size, self.map_size, 3), (40, 40, 45), dtype=np.uint8)

        # ===== 2. ODA DUVARLARI =====
        wall_thickness = 20
        wall_color = (80, 80, 80)

        # dış çerçeve
        cv2.rectangle(map_img, (50,50), (550,550), wall_color, wall_thickness)

        # kırık duvar efekti (random boşluklar)
        cv2.line(map_img, (300,50), (350,100), (30,30,30), 25)  # kırık üst duvar
        cv2.line(map_img, (50,300), (100,350), (30,30,30), 25)  # kırık sol duvar

        # ===== 3. ENKAZ =====


        # ===== 4. ARUCO MARKERLAR (YEŞİL) =====
        for node_id, pos in self.node_map.items():
            center = self.world_to_pixel(*pos)

            cv2.circle(map_img, center, 10, (0,255,0), -1)
            cv2.putText(map_img, f"A{node_id}",
                        (center[0]+10, center[1]-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (0,255,0), 1)

        # ===== 5. ROBOT =====
        if self.robot_pose is not None:
            rx_world = self.robot_pose.pose.position.x
            ry_world = self.robot_pose.pose.position.y
            rx, ry = self.world_to_pixel(rx_world, ry_world)

            q = self.robot_pose.pose.orientation
            _, _, yaw = tft.euler_from_quaternion([q.x, q.y, q.z, q.w])

            cv2.circle(map_img, (rx, ry), 12, (0, 200, 255), -1)

            arrow_len = 30
            ax = int(rx + arrow_len * np.cos(yaw))
            ay = int(ry - arrow_len * np.sin(yaw))

            cv2.line(map_img, (rx, ry), (ax, ay), (0, 255, 255), 3)
        # ===== 5.5 HUMAN CONE =====
            self.draw_cone(map_img, rx, ry, yaw)

        # ===== 6. KAMERA + HARİTA =====
        h, w = self.camera_image.shape[:2]
        scale_ratio = self.map_size / h
        cam_resized = cv2.resize(self.camera_image, (int(w * scale_ratio), self.map_size))

        combined = np.hstack((cam_resized, map_img))

        msg = self.bridge.cv2_to_compressed_imgmsg(combined, dst_format='jpg')
        self.viz_pub.publish(msg)

if __name__ == '__main__':
    try:
        node = PoseVisualizerNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass