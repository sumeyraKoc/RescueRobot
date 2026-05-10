#!/usr/bin/env python3

import rospy
import numpy as np
from duckietown_msgs.msg import WheelEncoderStamped
from geometry_msgs.msg import PoseStamped
import tf.transformations as tft


class WheelOdometryNode:
    def __init__(self):
        rospy.init_node('odometry_node')

        self.WHEEL_RADIUS = 0.0318
        self.WHEEL_BASELINE = 0.1
        self.TICKS_PER_REV = 135

        self.x = 0.5
        self.y = 0.5
        self.theta = 0.0

        self.left_ticks = None
        self.right_ticks = None
        self.prev_left = None
        self.prev_right = None

        self.last_aruco_time = None
        self.ARUCO_TIMEOUT = 1.0


        self.pose_pub = rospy.Publisher(
            "/bird/fused_pose", PoseStamped, queue_size=1)

        rospy.Subscriber("/bird/left_wheel_encoder_node/tick",
                         WheelEncoderStamped, self.left_cb)

        rospy.Subscriber("/bird/right_wheel_encoder_node/tick",
                         WheelEncoderStamped, self.right_cb)

        rospy.Subscriber(
            "/bird/aruco_detector_node/pose",
            PoseStamped,
            self.aruco_cb,
            queue_size=1
        )

        rospy.loginfo("Odometry + Fallback node başlatıldı")

    def left_cb(self, msg):
        self.left_ticks = msg.data

    def right_cb(self, msg):
        self.right_ticks = msg.data
        self.update_odometry()

    def aruco_cb(self, msg):

        # 3. ArUco detector'dan gelen relatif (robota göre) pozisyonu al
        # Senin belirttiğin eşleme: x = tvec[2], y = -tvec[0]
        self.x  = msg.pose.position.x
        self.y = msg.pose.position.y

        # 4. Robotun yönelimini (theta) mesajdaki quaternion'dan hesapla
        orientation_list = [msg.pose.orientation.x, msg.pose.orientation.y, 
                            msg.pose.orientation.z, msg.pose.orientation.w]
        (_, _, yaw_from_aruco) = tft.euler_from_quaternion(orientation_list)

        # Robotun açısını güncelle (Marker'ın dünya açısı + ölçülen relatif açı)
        self.theta = yaw_from_aruco

        # 6. Zaman damgasını güncelle ki update_odometry ArUco'ya öncelik versin
        self.last_aruco_time = rospy.Time.now()

        # Görselleştirme için hemen yayınla
        self.publish_pose("ARUCO")
        
    
    def delta_ticks(self, current, prev):
        delta = current - prev
        if delta > 1000:
            delta -= 65535
        elif delta < -1000:
            delta += 65535
        return delta

    def update_odometry(self):
        if self.left_ticks is None or self.right_ticks is None:
            return

        if self.prev_left is None:
            self.prev_left = self.left_ticks
            self.prev_right = self.right_ticks
            return

        # ArUco aktifse odometry kullanma
        if self.last_aruco_time is not None:
            dt = (rospy.Time.now() - self.last_aruco_time).to_sec()
            if dt < self.ARUCO_TIMEOUT:
                self.publish_pose("ARUCO")
                return

        d_left_ticks = self.delta_ticks(self.left_ticks, self.prev_left)
        d_right_ticks = self.delta_ticks(self.right_ticks, self.prev_right)

        self.prev_left = self.left_ticks
        self.prev_right = self.right_ticks

        d_left = 2 * np.pi * self.WHEEL_RADIUS * d_left_ticks / self.TICKS_PER_REV
        d_right = 2 * np.pi * self.WHEEL_RADIUS * d_right_ticks / self.TICKS_PER_REV

        d_center = (d_left + d_right) / 2.0
        d_theta = (d_right - d_left) / self.WHEEL_BASELINE

        theta_mid = self.theta + d_theta / 2.0

        self.x += d_center * np.cos(theta_mid)
        self.y += d_center * np.sin(theta_mid)
        self.theta += d_theta

        # rospy.loginfo_throttle(
        #     1, f"ODOMETRY → x:{self.x:.2f}, y:{self.y:.2f}")
        self.publish_pose("ODOMETRY")        

    def publish_pose(self, mode):
        pose = PoseStamped()
        pose.header.stamp = rospy.Time.now()
        pose.header.frame_id = "map"

        pose.pose.position.x = self.x
        pose.pose.position.y = self.y
        pose.pose.position.z = 0.0

        q = tft.quaternion_from_euler(0, 0, self.theta)
        pose.pose.orientation.x = q[0]
        pose.pose.orientation.y = q[1]
        pose.pose.orientation.z = q[2]
        pose.pose.orientation.w = q[3]

        self.pose_pub.publish(pose)

        


if __name__ == '__main__':
    node = WheelOdometryNode()
    rospy.spin()
