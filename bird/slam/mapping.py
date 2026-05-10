#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import cv2
import cv2.aruco as aruco
import numpy as np

from sensor_msgs.msg import CompressedImage, Image
from geometry_msgs.msg import PoseStamped
from cv_bridge import CvBridge
from tf.transformations import quaternion_from_euler, euler_from_quaternion

class ArucoSLAM:
    def __init__(self):
        rospy.init_node('aruco_slam_node')
        self.bridge = CvBridge()

        # --- CAMERA PARAMS ---
        self.K = np.array([[370.4782766860996, 0.0, 319.1440639481878],
                            [0.0, 369.31290489671466, 235.39077922138782],
                            [0.0, 0.0, 1.0]])
        self.d = np.array([-0.3480740501405288, 0.1071839195319511,
                           0.007871493822851558, -0.0005925913204724595, 0.0])
        self.marker_length = 0.065

        self.map = {}
        self.robot_pose = None
        self.aruco_dict = aruco.Dictionary_get(aruco.DICT_5X5_100)
        self.parameters = aruco.DetectorParameters_create()

        # --- PUBLISHERS ---
        self.pose_pub = rospy.Publisher("/bird/aruco_detector_node/pose", PoseStamped, queue_size=1)
        self.debug_pub = rospy.Publisher("/duckiebot/aruco_debug/image", Image, queue_size=1)
        self.marker_pub = rospy.Publisher("/bird/new_marker_detected", PoseStamped, queue_size=10)
        
        # --- SUBSCRIBERS ---
        #rospy.Subscriber("/bird/camera_node/image/compressed", CompressedImage, self.image_cb, queue_size=1)
        rospy.Subscriber("/yolo/image/compressed", CompressedImage, self.image_cb, queue_size=1)
        rospy.Subscriber("/bird/fused_pose", PoseStamped, self.pose_cb, queue_size=1)
        
        rospy.loginfo("Aruco SLAM node revize edilmiş haliyle başladı")

    def pose_cb(self, msg):
        self.robot_pose = msg

    def process_aruco_pose(self, marker_id, rvec, tvec):
        """Yeni bir marker tespit edildiğinde haritaya ekleme işlemini yapar."""
        # --- CV -> ROBOT ---
        R_cv2robot = np.array([
            [ 0,  0,  1],   
            [-1,  0,  0],
            [ 0, -1,  0]
        ])
        
        t_cm = tvec.reshape(3,1)
        t_mc_robot = R_cv2robot @ t_cm

        # --- ROBOT WORLD POSE ---
        rx = self.robot_pose.pose.position.x
        ry = self.robot_pose.pose.position.y

        q = self.robot_pose.pose.orientation
        _, _, robot_yaw = euler_from_quaternion([q.x, q.y, q.z, q.w])

        # --- ROBOT ROTATION ---
        R_wr = np.array([
            [ np.cos(robot_yaw), -np.sin(robot_yaw), 0],
            [ np.sin(robot_yaw),  np.cos(robot_yaw), 0],
            [0,                   0,                 1]
        ])

        # --- MARKER WORLD POSITION ---
        t_wm = R_wr @ t_mc_robot + np.array([[rx],[ry],[0]])

        mx = float(t_wm[0][0])
        my = float(t_wm[1][0])

        R_cm, _ = cv2.Rodrigues(rvec)
        R_wm = R_wr @ R_cv2robot @ R_cm
        m_yaw = np.arctan2(R_wm[1,0], R_wm[0,0])
        
        # --- MAP'E EKLE ---
        self.map[marker_id] = (mx, my, m_yaw)

        # --- PUBLISH ---
        self.publish_new_marker(marker_id, mx, my, m_yaw)
        rospy.loginfo(f"NEW MARKER {marker_id} added: ({mx:.2f}, {my:.2f}, {m_yaw:.2f})")

    def process_robot_pose(self, marker_id, rvec, tvec):
        """Bilinen bir marker üzerinden robotun dünya üzerindeki konumunu hesaplar."""
        current_time = rospy.Time.now()
        mx, my, m_yaw = self.map[marker_id]

        tvec_m = tvec.reshape(3,1)
        R_cm, _ = cv2.Rodrigues(rvec)
        R_mc = R_cm.T
        t_mc = -R_mc @ tvec_m

        R_wm = np.array([
            [np.cos(m_yaw), -np.sin(m_yaw), 0],
            [np.sin(m_yaw),  np.cos(m_yaw), 0],
            [0, 0, 1]
        ])

        t_wc = R_wm @ t_mc + np.array([[mx],[my],[0]])
        R_wc = R_wm @ R_mc

        # Robot Poz Mesajı
        pose_msg = PoseStamped()
        pose_msg.header.stamp = current_time
        pose_msg.header.frame_id = str(marker_id)
        pose_msg.pose.position.x = t_wc[0][0]
        pose_msg.pose.position.y = t_wc[1][0]
        pose_msg.pose.position.z = t_wc[2][0]

        yaw = np.arctan2(R_wc[1,0], R_wc[0,0]) + np.pi / 2
        q = quaternion_from_euler(0, 0, yaw)
        pose_msg.pose.orientation.x, pose_msg.pose.orientation.y = q[0], q[1]
        pose_msg.pose.orientation.z, pose_msg.pose.orientation.w = q[2], q[3]

        self.pose_pub.publish(pose_msg)
        
    def image_cb(self, msg):
        if self.robot_pose is None:
            return

        np_arr = np.frombuffer(msg.data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        h, w = gray.shape

        # Görüntünün kenarlarından bırakılacak oran
        margin_ratio = 0.25

        x_margin = int(w * margin_ratio)
        y_margin = int(h * margin_ratio)

        corners, ids, _ = aruco.detectMarkers(
            gray,
            self.aruco_dict,
            parameters=self.parameters
        )

        if ids is not None:

            filtered_corners = []
            filtered_ids = []

            # --- KENAR FİLTRESİ ---
            for i in range(len(ids)):

                c = corners[i][0]

                # Marker merkezi
                cx = np.mean(c[:, 0])
                cy = np.mean(c[:, 1])

                # Eğer marker görüntünün kenarına yakınsa ignore et
                if (
                    cx < x_margin or
                    cx > (w - x_margin) or
                    cy < y_margin or
                    cy > (h - y_margin)
                ):
                    continue

                filtered_corners.append(corners[i])
                filtered_ids.append(ids[i])

            # Hiç marker kalmadıysa çık
            if len(filtered_ids) == 0:
                debug_img = self.bridge.cv2_to_imgmsg(frame, "bgr8")
                self.debug_pub.publish(debug_img)
                return

            filtered_ids = np.array(filtered_ids)

            rvecs, tvecs, _ = aruco.estimatePoseSingleMarkers(
                filtered_corners,
                self.marker_length,
                self.K,
                self.d
            )

            # Görselleştirme
            aruco.drawDetectedMarkers(frame, filtered_corners, filtered_ids)

            for i in range(len(filtered_ids)):

                marker_id = int(filtered_ids[i][0])
                rvec = rvecs[i][0]
                tvec = tvecs[i][0]

                aruco.drawAxis(frame, self.K, self.d, rvec, tvec, 0.05)

                if marker_id not in self.map:
                    self.process_aruco_pose(marker_id, rvec, tvec)
                else:
                    self.process_robot_pose(marker_id, rvec, tvec)

        # Debug Image
        debug_img = self.bridge.cv2_to_imgmsg(frame, "bgr8")
        self.debug_pub.publish(debug_img)

    def publish_new_marker(self, m_id, x, y, yaw):
        msg = PoseStamped()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = str(m_id) 
        msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = x, y, 0
        q = quaternion_from_euler(0, 0, yaw)
        msg.pose.orientation.x, msg.pose.orientation.y, msg.pose.orientation.z, msg.pose.orientation.w = q
        self.marker_pub.publish(msg)

if __name__ == '__main__':
    node = ArucoSLAM()
    rospy.spin()