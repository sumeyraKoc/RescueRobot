#!/usr/bin/env python3

import rospy
import numpy as np
from duckietown_msgs.msg import WheelEncoderStamped
from geometry_msgs.msg import PoseStamped
import tf.transformations as tft


class WheelOdometryNode:
    def __init__(self):
        rospy.init_node('odometry_node')

        # Robotun fiziksel parametreleri
        self.WHEEL_RADIUS = 0.0318
        self.WHEEL_BASELINE = 0.1
        self.TICKS_PER_REV = 135

        # Başlangıç konumu ve açısı
        self.x = 0.05
        self.y = 0.05
        self.theta = 0.0

        # Anlık tık verileri
        self.left_ticks = None
        self.right_ticks = None
        
        # Bir önceki adımın tık verileri
        self.prev_left = None
        self.prev_right = None

        # Yayıncı (Publisher)
        self.pose_pub = rospy.Publisher(
            "/bird/fused_pose", PoseStamped, queue_size=1)

        # Abonelikler (Subscribers)
        # Sol tekerlek verisi geldiğinde hem veri güncellenir hem de odometri hesabı tetiklenir
        rospy.Subscriber("/bird/left_wheel_encoder_node/tick",
                         WheelEncoderStamped, self.left_cb)

        # Sağ tekerlek verisi geldiğinde sadece değer kaydedilir
        rospy.Subscriber("/bird/right_wheel_encoder_node/tick",
                         WheelEncoderStamped, self.right_cb)

        rospy.loginfo("Sadece Odometri (Sol Tekerlek Tetiklemeli) node başlatıldı")

    def left_cb(self, msg):
        self.left_ticks = msg.data
        # Güncelleme fonksiyonu artık sol tekerlek verisi geldiğinde çalışıyor
        self.update_odometry()

    def right_cb(self, msg):
        # Sağ tekerlek sadece veriyi günceller, hesaplamayı tetiklemez
        self.right_ticks = msg.data
    
    def delta_ticks(self, current, prev):
        delta = current - prev
        if delta > 1000:
            delta -= 65535
        elif delta < -1000:
            delta += 65535
        return delta

    def update_odometry(self):
        # İki tekerlekten de en az bir kere veri gelmiş olması gerekir
        if self.left_ticks is None or self.right_ticks is None:
            return

        # İlk adımda bir önceki değerleri eşitleyip döner (başlangıç referansı)
        if self.prev_left is None or self.prev_right is None:
            self.prev_left = self.left_ticks
            self.prev_right = self.right_ticks
            return

        # Tık farklarının hesaplanması
        d_left_ticks = self.delta_ticks(self.left_ticks, self.prev_left)
        d_right_ticks = self.delta_ticks(self.right_ticks, self.prev_right)

        # Mevcut tıkları, bir sonraki adım için "eski tık" olarak kaydet
        self.prev_left = self.left_ticks
        self.prev_right = self.right_ticks

        # Tık değerlerini metre cinsinden mesafeye dönüştürme
        d_left = 2 * np.pi * self.WHEEL_RADIUS * d_left_ticks / self.TICKS_PER_REV
        d_right = 2 * np.pi * self.WHEEL_RADIUS * d_right_ticks / self.TICKS_PER_REV

        # Robotun merkezinin aldığı yol ve dönme açısı
        d_center = (d_left + d_right) / 2.0
        d_theta = (d_right - d_left) / self.WHEEL_BASELINE

        # Ortalama yönelim açısı (Trigonometrik hesaplama için)
        theta_mid = self.theta + d_theta / 2.0

        # Koordinatların ve açının güncellenmesi
        self.x += d_center * np.cos(theta_mid)
        self.y += d_center * np.sin(theta_mid)
        self.theta += d_theta

        # Yeni konumu yayınla
        self.publish_pose()        

    def publish_pose(self):
        pose = PoseStamped()
        pose.header.stamp = rospy.Time.now()
        pose.header.frame_id = "map"

        pose.pose.position.x = self.x
        pose.pose.position.y = self.y
        pose.pose.position.z = 0.0

        # Açıyı ROS'un kabul ettiği Quaternion formatına çevirme
        q = tft.quaternion_from_euler(0, 0, self.theta)
        pose.pose.orientation.x = q[0]
        pose.pose.orientation.y = q[1]
        pose.pose.orientation.z = q[2]
        pose.pose.orientation.w = q[3]

        self.pose_pub.publish(pose)


if __name__ == '__main__':
    node = WheelOdometryNode()
    rospy.spin()