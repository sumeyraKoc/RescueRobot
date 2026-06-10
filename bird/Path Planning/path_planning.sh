#!/bin/bash
source /environment.sh
dt-launchfile-init
dt-exec rosrun design_project odometry_v2.py &
dt-exec rosrun design_project map.py &
dt-exec rosrun design_project astar_v2.py &
dt-exec rosrun design_project dwa.py &
dt-exec rosrun design_project  dwa_navigation_node.py 
dt-launchfile-join
