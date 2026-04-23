#!/bin/bash
source /environment.sh
dt-launchfile-init
dt-exec rosrun design_project localizer_aruco_node.py &
dt-exec rosrun design_project odometry_node.py &
dt-exec rosrun design_project visualizer_node.py

dt-launchfile-join
