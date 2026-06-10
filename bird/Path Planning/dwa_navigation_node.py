#!/usr/bin/env python3

import rospy
import math
import cv2
import numpy as np
import os
import yaml

from geometry_msgs.msg import PoseStamped
from duckietown_msgs.msg import WheelsCmdStamped

from map import OccupancyGridMap
from astar_v2 import AStarPlanner
from dwa import DWAPlanner

from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class DWANavigationNode:

    def __init__(self):

        rospy.init_node("dwa_navigation_node")

        self.bridge = CvBridge()

        # =====================================
        # LOAD YAML CONFIG
        # =====================================

        package_path = os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )

        yaml_path = os.path.join(
            package_path,
            "config",
            "params.yaml"
        )

        with open(yaml_path, "r") as file:
            self.config = yaml.safe_load(file)

        # =====================================
        # ROBOT PARAMS
        # =====================================

        self.BASELINE = self.config["robot"]["baseline"]

        # =====================================
        # ROBOT STATE
        # =====================================

        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0

        self.pose_received = False

        # =====================================
        # MAP
        # =====================================

        self.grid_map = OccupancyGridMap(
            world_size=self.config["map"]["world_size"],
            resolution=self.config["map"]["resolution"]
        )

        # =====================================
        # GLOBAL PATH
        # =====================================

        self.start = tuple(
            self.config["mission"]["start"]
        )

        self.goal = tuple(
            self.config["mission"]["goal"]
        )

        self.astar = AStarPlanner(
            self.grid_map
        )

        self.global_path = self.astar.plan(
            self.start,
            self.goal
        )

        # =====================================
        # OBSTACLE
        # =====================================

        self.obstacle = self.config["obstacle"]

        # =====================================
        # DWA
        # =====================================

        self.dwa = DWAPlanner(
            self.config
        )

        # =====================================
        # TRAJECTORY HISTORY
        # =====================================

        self.history = []

        # =====================================
        # SUBSCRIBERS
        # =====================================

        rospy.Subscriber(
            "/bird/fused_pose",
            PoseStamped,
            self.pose_callback
        )

        # =====================================
        # PUBLISHERS
        # =====================================

        self.cmd_pub = rospy.Publisher(
            "/bird/wheels_driver_node/wheels_cmd",
            WheelsCmdStamped,
            queue_size=1
        )

        self.image_pub = rospy.Publisher(
            "/bird/dwa_visualization",
            Image,
            queue_size=1
        )

        rospy.loginfo(
            "DWA Navigation Node Started"
        )

        self.loop()

    # =====================================
    # POSE CALLBACK
    # =====================================

    def pose_callback(self, msg):

        self.x = msg.pose.position.x
        self.y = msg.pose.position.y

        q = msg.pose.orientation

        siny_cosp = 2 * (
            q.w * q.z +
            q.x * q.y
        )

        cosy_cosp = 1 - 2 * (
            q.y * q.y +
            q.z * q.z
        )

        self.yaw = math.atan2(
            siny_cosp,
            cosy_cosp
        )

        self.pose_received = True

    # =====================================
    # MAIN LOOP
    # =====================================

    def loop(self):

        rate = rospy.Rate(10)

        while not rospy.is_shutdown():

            if not self.pose_received:
                rate.sleep()
                continue

            robot_pose = (
                self.x,
                self.y,
                self.yaw
            )

            # ---------------------------------
            # DWA PLAN
            # ---------------------------------

            best_control, best_traj, all_trajs = self.dwa.plan(
                robot_pose,
                self.global_path,
                self.obstacle
            )

            v, w = best_control

            # ---------------------------------
            # DIFF DRIVE CONVERSION
            # ---------------------------------

            left = v - (
                w * self.BASELINE / 2.0
            )

            right = v + (
                w * self.BASELINE / 2.0
            )

            # ---------------------------------
            # PUBLISH CMD
            # ---------------------------------

            cmd = WheelsCmdStamped()

            cmd.header.stamp = rospy.Time.now()

            cmd.vel_left = left
            cmd.vel_right = right

            self.cmd_pub.publish(cmd)

            # ---------------------------------
            # HISTORY
            # ---------------------------------

            self.history.append(
                (self.x, self.y)
            )

            # ---------------------------------
            # VISUALIZATION
            # ---------------------------------

            self.visualize(
                best_traj,
                all_trajs
            )

            # ---------------------------------
            # GOAL CHECK
            # ---------------------------------

            dist_to_goal = math.hypot(
                self.goal[0] - self.x,
                self.goal[1] - self.y
            )

            if dist_to_goal < 0.1:

                rospy.loginfo(
                    "GOAL REACHED"
                )

                stop = WheelsCmdStamped()

                stop.vel_left = 0.0
                stop.vel_right = 0.0

                self.cmd_pub.publish(stop)

                break

            rate.sleep()

    # =====================================
    # WORLD -> PIXEL
    # =====================================

    def world_to_pixel(self, x, y):

        scale = 400

        px = int(
            x / self.grid_map.world_size * scale
        )

        py = int(
            scale -
            y / self.grid_map.world_size * scale
        )

        return px, py

    # =====================================
    # VISUALIZATION
    # =====================================

    def visualize(
        self,
        best_traj,
        all_trajs
    ):

        canvas = np.ones(
            (400, 400, 3),
            dtype=np.uint8
        ) * 255

        # ---------------------------------
        # GLOBAL PATH
        # ---------------------------------

        for i in range(
            len(self.global_path) - 1
        ):

            p1 = self.world_to_pixel(
                *self.global_path[i]
            )

            p2 = self.world_to_pixel(
                *self.global_path[i + 1]
            )

            cv2.line(
                canvas,
                p1,
                p2,
                (255, 0, 0),
                2
            )

        # ---------------------------------
        # ALL TRAJECTORIES
        # ---------------------------------

        for traj in all_trajs:

            for i in range(
                len(traj) - 1
            ):

                p1 = self.world_to_pixel(
                    traj[i][0],
                    traj[i][1]
                )

                p2 = self.world_to_pixel(
                    traj[i + 1][0],
                    traj[i + 1][1]
                )

                cv2.line(
                    canvas,
                    p1,
                    p2,
                    (180, 180, 180),
                    1
                )

        # ---------------------------------
        # BEST TRAJECTORY
        # ---------------------------------

        if best_traj is not None:

            for i in range(
                len(best_traj) - 1
            ):

                p1 = self.world_to_pixel(
                    best_traj[i][0],
                    best_traj[i][1]
                )

                p2 = self.world_to_pixel(
                    best_traj[i + 1][0],
                    best_traj[i + 1][1]
                )

                cv2.line(
                    canvas,
                    p1,
                    p2,
                    (0, 255, 0),
                    3
                )

        # ---------------------------------
        # ROBOT HISTORY
        # ---------------------------------

        for i in range(
            len(self.history) - 1
        ):

            p1 = self.world_to_pixel(
                *self.history[i]
            )

            p2 = self.world_to_pixel(
                *self.history[i + 1]
            )

            cv2.line(
                canvas,
                p1,
                p2,
                (0, 0, 0),
                2
            )

        # ---------------------------------
        # ROBOT
        # ---------------------------------

        robot_px = self.world_to_pixel(
            self.x,
            self.y
        )

        cv2.circle(
            canvas,
            robot_px,
            6,
            (255, 0, 255),
            -1
        )

        # ---------------------------------
        # SENSOR AREA
        # ---------------------------------

        sensor_range = self.config["robot"]["sensor_range"]

        sensor_px = int(
            sensor_range
            / self.grid_map.world_size
            * 400
        )

        cv2.circle(
            canvas,
            robot_px,
            sensor_px,
            (255, 255, 0),
            1
        )

        # ---------------------------------
        # GOAL
        # ---------------------------------

        goal_px = self.world_to_pixel(
            *self.goal
        )

        cv2.circle(
            canvas,
            goal_px,
            7,
            (0, 255, 255),
            -1
        )

        # ---------------------------------
        # OBSTACLE
        # ---------------------------------

        obs_px = self.world_to_pixel(
            self.obstacle["x"],
            self.obstacle["y"]
        )

        obs_radius = int(
            self.obstacle["radius"]
            / self.grid_map.world_size
            * 400
        )

        cv2.circle(
            canvas,
            obs_px,
            obs_radius,
            (0, 0, 255),
            -1
        )

        # ---------------------------------
        # SAFETY ZONE
        # ---------------------------------

        safe_radius = (
            self.obstacle["radius"]
            + self.dwa.robot_radius
            + self.dwa.safety_margin
        )

        safe_px = int(
            safe_radius
            / self.grid_map.world_size
            * 400
        )

        cv2.circle(
            canvas,
            obs_px,
            safe_px,
            (0, 165, 255),
            2
        )

        msg = self.bridge.cv2_to_imgmsg(
            canvas,
            encoding="bgr8"
        )

        self.image_pub.publish(msg)


if __name__ == '__main__':

    try:
        DWANavigationNode()

    except rospy.ROSInterruptException:
        pass
