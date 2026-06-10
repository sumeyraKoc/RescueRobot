#!/usr/bin/env python3

import numpy as np
import math



class DWAPlanner:

    def __init__(self, config):

        planner_cfg = config["planner"]
        robot_cfg = config["robot"]

        # Velocity limits
        self.max_v = planner_cfg["max_v"]
        self.max_w = planner_cfg["max_w"]
        self.min_v = planner_cfg["min_v"]

        # Sampling
        self.v_samples = planner_cfg["v_samples"]
        self.w_samples = planner_cfg["w_samples"]

        # Simulation
        self.dt = planner_cfg["dt"]
        self.predict_time = planner_cfg["predict_time"]

        # Robot
        self.robot_radius = robot_cfg["radius"]
        self.safety_margin = robot_cfg["safety_margin"]

        # Cost weights
        self.goal_weight = planner_cfg["goal_weight"]
        self.path_weight = planner_cfg["path_weight"]
        self.obstacle_weight = planner_cfg["obstacle_weight"]
        self.heading_weight = planner_cfg["heading_weight"]
        self.progress_weight = planner_cfg["progress_weight"]


    # =====================================
    # MAIN PLAN
    # =====================================
    def plan(
        self,
        robot_pose,
        global_path,
        obstacle
    ):

        best_cost = float("inf")
        best_traj = None
        all_trajs = []
        best_control = (0.0, 0.0)

        v_list = np.linspace(
	    self.min_v,
	    self.max_v,
	    self.v_samples
	)

        w_list = np.linspace(
            -self.max_w,
            self.max_w,
            self.w_samples
        )

        for v in v_list:
            for w in w_list:

                traj = self.simulate_trajectory(
                    robot_pose,
                    v,
                    w
                )

                all_trajs.append(traj)

                if self.check_collision(
                    traj,
                    obstacle
                ):
                    continue

                cost = self.compute_cost(
                    traj,
                    global_path,
                    obstacle
                )

                if cost < best_cost:
                    best_cost = cost
                    best_traj = traj
                    best_control = (v, w)

        return best_control, best_traj, all_trajs

    # =====================================
    # TRAJECTORY SIMULATION
    # =====================================
    def simulate_trajectory(
        self,
        pose,
        v,
        w
    ):

        x, y, yaw = pose
        traj = []

        time = 0.0

        while time < self.predict_time:

            x += v * math.cos(yaw) * self.dt
            y += v * math.sin(yaw) * self.dt
            yaw += w * self.dt

            traj.append((x, y, yaw))

            time += self.dt

        return traj

    # =====================================
    # COLLISION CHECK
    # =====================================
    def check_collision(
        self,
        traj,
        obstacle
    ):

        ox = obstacle["x"]
        oy = obstacle["y"]
        radius = obstacle["radius"]

        safe_radius = (
            radius
            + self.robot_radius
            + self.safety_margin
        )

        for x, y, _ in traj:

            dist = math.hypot(
                x - ox,
                y - oy
            )

            if dist <= safe_radius:
                return True

        return False

    # =====================================
    # COST FUNCTION
    # =====================================
    def compute_cost(
        self,
        traj,
        global_path,
        obstacle
    ):

        start_x, start_y, _ = traj[0]
        end_x, end_y, _ = traj[-1]

        forward_progress = math.hypot(
            end_x - start_x,
            end_y - start_y
        )

        final_x, final_y, final_yaw = traj[-1]

        # ---------------------
        # GOAL COST
        # ---------------------
        gx, gy = global_path[-1]

        goal_cost = math.hypot(
            gx - final_x,
            gy - final_y
        )

        # ---------------------
        # PATH COST
        # Average distance of whole trajectory to global path
        # ---------------------
        path_cost = 0.0

        for x, y, _ in traj:

            min_path_dist = float("inf")

            for px, py in global_path:

                d = math.hypot(
                    px - x,
                    py - y
                )

                if d < min_path_dist:
                    min_path_dist = d

            path_cost += min_path_dist

        path_cost /= len(traj)

        # ---------------------
        # OBSTACLE COST
        # ---------------------
        ox = obstacle["x"]
        oy = obstacle["y"]

        min_obs_dist = float("inf")

        for x, y, _ in traj:

            d = math.hypot(
                x - ox,
                y - oy
            )

            if d < min_obs_dist:
                min_obs_dist = d

        obstacle_cost = 1.0 / (
            min_obs_dist + 1e-6
        )

        # ---------------------
        # HEADING COST
        # Robot heading should point toward goal
        # ---------------------
        heading_to_goal = math.atan2(
            gy - final_y,
            gx - final_x
        )

        heading_error = abs(
            math.atan2(
                math.sin(heading_to_goal - final_yaw),
                math.cos(heading_to_goal - final_yaw)
            )
        )

        # ---------------------
        # TOTAL COST
        # Lower cost is better
        # ---------------------
        total_cost = (
            self.goal_weight * goal_cost
            + self.path_weight * path_cost
            + self.obstacle_weight * obstacle_cost
            + self.heading_weight * heading_error
            - self.progress_weight * forward_progress
        )

        return total_cost