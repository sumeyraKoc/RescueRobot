#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import cv2
import cv2.aruco as aruco
import numpy as np
from sensor_msgs.msg import Image, CompressedImage
from geometry_msgs.msg import PoseStamped
from cv_bridge import CvBridge
from tf.transformations import quaternion_from_euler


class ArUcoLocalizer:
    def __init__(self):
        rospy.init_node('aruco_detector_node')
        self.bridge = CvBridge()

        # Kamera kalibrasyonu
        self.K = np.array([[370.4782766860996,0.0,319.1440639481878],
                            [0.0,369.31290489671466, 235.39077922138782],
                            [0.0,0.0,1.0]])
        
        self.d = np.array([-0.3480740501405288, 0.1071839195319511, 0.007871493822851558, -0.0005925913204724595, 0.0])

        self.marker_length = 0.085

        # NODE MAP (Markerların Dünya Koordinatları)
        self.node_map = {
            0: (0,0), 1: (1,0), 2: (2,0), 3: (3,0),
            4: (0,1), 5: (1,1), 6: (2,1), 7: (3,1),
            8: (0,2), 9: (1,2), 10: (2,2), 11: (3,2),
            12: (0,3), 13: (1,3), 14: (2,3), 15: (3,3)
        }
        self.marker_yaw = {i: -90.0 for i in range(16)} 
        
        self.aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_5X5_100)
        self.parameters = aruco.DetectorParameters_create()
        self.parameters.adaptiveThreshWinSizeMin = 3
        self.parameters.adaptiveThreshWinSizeMax = 35
        self.parameters.adaptiveThreshConstant =  0.03

        self.img_w = 640
        self.img_h = 480
        self.frame_center = self.img_w / 2.0
        self.fov_min = self.img_w * 0.25
        self.fov_max = self.img_w * 0.75

        self.process_freq = 0.015 
        self.last_process_time = rospy.Time.now()

        # --- PUBLISHERS ---
        self.image_pub = rospy.Publisher("/duckiebot/aruco_debug/image", Image, queue_size=1)
        # Robotun Pozisyonu
        self.pose_pub = rospy.Publisher("/bird/aruco_detector_node/pose", PoseStamped, queue_size=1)
        # Tespit Edilen Marker'ın Pozisyonu (YENİ)
        self.marker_pub = rospy.Publisher("/bird/aruco_detector_node/detected_marker_pose", PoseStamped, queue_size=1)

        # --- SUBSCRIBER ---    
        rospy.Subscriber("/yolo/image/compressed", CompressedImage, self.callback, queue_size=1)
        

        rospy.loginfo("ArUco node başlatıldı")
        
    def rotationMatrixToEulerAngles(self, R):
        sy = np.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
        singular = sy < 1e-6
        if not singular:
            x = np.arctan2(R[2, 1], R[2, 2]); y = np.arctan2(-R[2, 0], sy); z = np.arctan2(R[1, 0], R[0, 0])
        else:
            x = np.arctan2(-R[1, 2], R[1, 1]); y = np.arctan2(-R[2, 0], sy); z = 0
        return np.array([x, y, z])

    def process_pose(self, frame, corners, rvecs, tvecs, ids, idx):
        aruco.drawDetectedMarkers(frame, corners)
        aruco.drawAxis(frame, self.K, self.d, rvecs[idx], tvecs[idx], 0.05)

        current_time = rospy.Time.now()
        marker_id = ids[idx][0]

        # 1. MARKER POSE (Haritadaki Sabit Konumu)
        mx, my = self.node_map.get(marker_id, (0,0))
        m_yaw_deg = self.marker_yaw.get(marker_id, 0.0)
        m_yaw_rad = np.radians(m_yaw_deg)

        marker_msg = PoseStamped()
        marker_msg.header.stamp = current_time
        marker_msg.header.frame_id = str(marker_id) # Markerlar haritaya göre sabittir
        marker_msg.pose.position.x = mx
        marker_msg.pose.position.y = my
        marker_msg.pose.position.z = 0.0
        
        mq = quaternion_from_euler(0, 0, m_yaw_rad)
        marker_msg.pose.orientation.x = mq[0]
        marker_msg.pose.orientation.y = mq[1]
        marker_msg.pose.orientation.z = mq[2]
        marker_msg.pose.orientation.w = mq[3]
        
        self.marker_pub.publish(marker_msg)

        # 2. ROBOT POSE (Hesaplanan Konum)
        tvec = tvecs[idx][0]
        rvec = rvecs[idx][0]
        R_cm, _ = cv2.Rodrigues(rvec)
        R_mc = R_cm.T
        t_mc = -R_mc @ tvec.reshape(3,1)

        R_wm = np.array([
            [np.cos(m_yaw_rad), -np.sin(m_yaw_rad), 0],
            [np.sin(m_yaw_rad),  np.cos(m_yaw_rad), 0],
            [0, 0, 1]
        ])

        t_wc = R_wm @ t_mc + np.array([[mx],[my],[0]])

        pose_msg = PoseStamped()
        pose_msg.header.stamp = current_time
        pose_msg.header.frame_id = str(marker_id)
        pose_msg.pose.position.x = t_wc[0][0]
        pose_msg.pose.position.y = t_wc[1][0]
        pose_msg.pose.position.z = t_wc[2][0]

        R_wc = R_wm @ R_mc

        # Sadece yaw çek (ilk koddaki mantığa paralel)
        yaw = np.arctan2(R_wc[1,0], R_wc[0,0])
        yaw = yaw + np.pi / 2
        
        q = quaternion_from_euler(0, 0, yaw)
        pose_msg.pose.orientation.x = q[0]; pose_msg.pose.orientation.y = q[1]
        pose_msg.pose.orientation.z = q[2]; pose_msg.pose.orientation.w = q[3]

        self.pose_pub.publish(pose_msg)

    def callback(self, msg):
        current_time = rospy.Time.now()

        try:
            np_arr = np.frombuffer(msg.data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # --- HER FRAME DEBUG YAYIN ---
            debug_frame = frame.copy()

            # --- SADECE POSE İÇİN THROTTLE ---
            if (current_time - self.last_process_time).to_sec() >= self.process_freq:
                self.last_process_time = current_time

                corners, ids, _ = aruco.detectMarkers(gray, self.aruco_dict, parameters=self.parameters)

                if ids is not None:
                    rvecs, tvecs, _ = aruco.estimatePoseSingleMarkers(
                        corners, self.marker_length, self.K, self.d
                    )

                    selected_idx = None
                    min_dist = float('inf')

                    for i in range(len(ids)):
                        m_center_x = np.mean(corners[i][0][:, 0])
                        if self.fov_min <= m_center_x <= self.fov_max:
                            dist = abs(m_center_x - self.frame_center)
                            if dist < min_dist:
                                min_dist = dist
                                selected_idx = i

                    if selected_idx is not None:
                        self.process_pose(debug_frame, corners, rvecs, tvecs, ids, selected_idx)

            # --- DEBUG IMAGE HER ZAMAN ---
            img_msg = self.bridge.cv2_to_imgmsg(debug_frame, "bgr8")
            self.image_pub.publish(img_msg)

        except Exception as e:
            rospy.logerr(f"Hata: {e}")

if __name__ == '__main__':
    node = ArUcoLocalizer()
    rospy.spin()