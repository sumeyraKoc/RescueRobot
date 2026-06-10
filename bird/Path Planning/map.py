#!/usr/bin/env python3

import numpy as np


class OccupancyGridMap:

    def __init__(
        self,
        world_size=1.5,
        resolution=0.05
    ):

        self.world_size = world_size
        self.resolution = resolution

        # Grid boyutu
        self.width = int(world_size / resolution)
        self.height = int(world_size / resolution)

        # Occupancy grid
        # 0 -> free
        # 1 -> occupied
        self.grid = np.zeros(
            (self.height, self.width),
            dtype=np.uint8
        )

    # =========================
    # WORLD -> GRID
    # =========================
    def world_to_grid(self, x, y):

        gx = int(x / self.resolution)
        gy = int(y / self.resolution)

        return gx, gy

    # =========================
    # GRID -> WORLD
    # =========================
    def grid_to_world(self, gx, gy):

        x = gx * self.resolution
        y = gy * self.resolution

        return x, y

    # =========================
    # MAP SINIRI
    # =========================
    def is_inside(self, gx, gy):

        return (
            0 <= gx < self.width and
            0 <= gy < self.height
        )

    # =========================
    # OBSTACLE EKLE
    # =========================
    def add_obstacle(self, x, y, radius=0.1):

        center_gx, center_gy = self.world_to_grid(x, y)

        radius_cells = int(radius / self.resolution)

        for dx in range(-radius_cells, radius_cells + 1):
            for dy in range(-radius_cells, radius_cells + 1):

                gx = center_gx + dx
                gy = center_gy + dy

                if not self.is_inside(gx, gy):
                    continue

                dist = np.sqrt(dx**2 + dy**2)

                if dist <= radius_cells:
                    self.grid[gy, gx] = 1

    # =========================
    # OCCUPIED MI?
    # =========================
    def is_occupied(self, gx, gy):

        if not self.is_inside(gx, gy):
            return True

        return self.grid[gy, gx] == 1