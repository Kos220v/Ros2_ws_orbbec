# astra_odometry — визуальная одометрия с камеры Orbbec Astra

Пакет заменяет **колёсную одометрию + IMU (MPU6050) + компас** визуальной
одометрией RTAB-Map (`rgbd_odometry`) по RGB-D камере Orbbec Astra. Публикует
`/odom` (поза X/Y + курс yaw + линейная/угловая скорости) — тот же топик, что
раньше давала колёсная одометрия, поэтому оба EKF (`robot_localization`)
переучивать на другое имя не нужно.

## Что было и что стало

| Было | Стало |
|------|-------|
| `robot_odom` (энкодеры → `/odom`) | `astra_odometry` (камера → `/odom`) |
| `mpu6050_control` → `/imu/data_raw` | удалён |
| `compass_control` → `/imu/mag_raw` | удалён |
| `imu_filter_madgwick` → `/imu/data` | удалён |
| `mag_declination_node` → `/imu/mag` | удалён |
| EKF: скорости из `/odom` + курс из `/imu/data` | EKF: поза + курс + скорости из `/odom` |

GPS-навигация (Nav2 + dual-EKF + `navsat_transform`) **сохранена**. Абсолютную
привязку к сторонам света теперь даёт GPS-трек (при движении), а не компас.

## Топики

Публикация:
* `/odom` — `nav_msgs/Odometry`, визуальная одометрия.

Подписки (ремап на драйвер `astra_camera`):
* `/camera/color/image_raw`, `/camera/color/camera_info`
* `/camera/depth/image_raw` (registered to color)

`rgbd_odometry` запускается с `publish_tf:=false` — TF `odom → base_link`
по-прежнему принадлежит `ekf_filter_node_odom`.

## Зависимости

```bash
sudo apt install -y ros-jazzy-rtabmap-odom

# Драйвер Astra (OpenNI) собирается из исходников в этот же workspace:
cd ~/ros2_ws/src
git clone https://github.com/orbbec/ros2_astra_camera.git
sudo apt install -y libgflags-dev nlohmann-json3-dev \
  ros-jazzy-image-transport ros-jazzy-camera-info-manager \
  libgoogle-glog-dev libusb-1.0-0-dev libeigen3-dev
cd ros2_astra_camera/astra_camera/scripts && sudo bash install.sh
sudo udevadm control --reload && sudo udevadm trigger
```

## Запуск

Весь стек одной командой (как и раньше):

```bash
ros2 launch robot_navigation bringup.launch.py
```

Только визуальная одометрия (для проверки камеры):

```bash
ros2 launch astra_odometry visual_odometry.launch.py
ros2 run astra_odometry odom_monitor          # человекочитаемая сводка /odom
```

## Важное про курс

Визуальная одометрия даёт **относительный** курс (от точки старта), а не
абсолютный азимут — компаса больше нет. Абсолютный курс появляется, когда робот
проедет несколько метров и GPS-трек свяжется с движением. Поэтому **после старта
сначала проедьте прямо несколько метров**, прежде чем полагаться на курс.

## Куда крутить

* Крепление камеры на роботе: `tracked_robot_description/urdf/tracked_robot.urdf.xacro`,
  свойство `cam_xyz` (камера жёстко спереди на корпусе).
* Параметры визуальной одометрии: `astra_odometry/launch/rgbd_odometry.launch.py`.
* Фьюзинг в EKF: `robot_navigation/config/dual_ekf_navsat.yaml`.
