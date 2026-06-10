#!/usr/bin/env python3

import heapq
import math


class AStarPlanner:

    def __init__(self, occupancy_map):

        self.map = occupancy_map

        # 8-connected movement
        self.motion = [
            (1, 0, 1.0),
            (-1, 0, 1.0),
            (0, 1, 1.0),
            (0, -1, 1.0),

            (1, 1, math.sqrt(2)),
            (1, -1, math.sqrt(2)),
            (-1, 1, math.sqrt(2)),
            (-1, -1, math.sqrt(2))
        ]

    # =========================
    # HEURISTIC
    # =========================
    def heuristic(self, a, b):

        return math.hypot(
            b[0] - a[0],
            b[1] - a[1]
        )

    # =========================
    # PLAN
    # =========================
    def plan(self, start, goal):

        start_g = self.map.world_to_grid(*start)
        goal_g = self.map.world_to_grid(*goal)

        open_set = []

        heapq.heappush(
            open_set,
            (0, start_g)
        )

        came_from = {}

        g_score = {}
        g_score[start_g] = 0

        while open_set:

            _, current = heapq.heappop(open_set)

            if current == goal_g:
                return self.reconstruct_path(
                    came_from,
                    current
                )

            for dx, dy, move_cost in self.motion:

                nx = current[0] + dx
                ny = current[1] + dy

                neighbor = (nx, ny)

                if not self.map.is_inside(nx, ny):
                    continue

                if self.map.is_occupied(nx, ny):
                    continue

                tentative_g = (
                    g_score[current]
                    + move_cost
                )

                if (
                    neighbor not in g_score
                    or tentative_g < g_score[neighbor]
                ):

                    came_from[neighbor] = current

                    g_score[neighbor] = tentative_g

                    f_score = (
                        tentative_g
                        + self.heuristic(
                            neighbor,
                            goal_g
                        )
                    )

                    heapq.heappush(
                        open_set,
                        (f_score, neighbor)
                    )

        return None

    # =========================
    # PATH RECONSTRUCTION
    # =========================
    def reconstruct_path(
        self,
        came_from,
        current
    ):

        path = [current]

        while current in came_from:
            current = came_from[current]
            path.append(current)

        path.reverse()

        world_path = []

        for gx, gy in path:
            wx, wy = self.map.grid_to_world(gx, gy)
            world_path.append((wx, wy))
            
        print(world_path)

        return world_path
