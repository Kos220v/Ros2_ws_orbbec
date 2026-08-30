#!/usr/bin/env bash
# check_odometry.sh
# Quick manual sanity checks for the Astra visual-odometry pipeline.
# Run AFTER `ros2 launch astra_odometry robot_odometry.launch.py`.
#
# Usage: ./check_odometry.sh
set -uo pipefail

green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
red()   { printf '\033[0;31m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[0;33m%s\033[0m\n' "$*"; }

section() { echo; yellow "== $* =="; }

require_topic() {
  local topic="$1"
  if ros2 topic list 2>/dev/null | grep -qx "$topic"; then
    green "  [OK]  $topic present"
    return 0
  else
    red   "  [MISSING]  $topic"
    return 1
  fi
}

hz_check() {
  local topic="$1"
  echo "  measuring rate of $topic for 5s ..."
  timeout 6 ros2 topic hz "$topic" 2>/dev/null | head -n 3 || \
    red "  could not measure $topic (no publisher?)"
}

section "1. Camera topics (astra_camera)"
require_topic /camera/color/image_raw
require_topic /camera/color/camera_info
require_topic /camera/depth/image_raw
require_topic /camera/depth/camera_info

section "2. Odometry topic (rtabmap rgbd_odometry)"
require_topic /odom

section "3. Publish rates"
hz_check /camera/color/image_raw
hz_check /camera/depth/image_raw
hz_check /odom

section "4. One odometry sample"
timeout 5 ros2 topic echo --once /odom 2>/dev/null || \
  red "  no /odom message received in 5s"

section "5. TF: odom -> base_footprint"
timeout 5 ros2 run tf2_ros tf2_echo odom base_footprint 2>/dev/null | head -n 12 || \
  yellow "  tf2_echo returned nothing (is publish_tf:=true?)"

echo
green "Done. Move the camera slowly (with texture in view) and re-run to see the pose change."
