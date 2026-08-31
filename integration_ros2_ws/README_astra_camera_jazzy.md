# Драйвер оригинальной Astra (OpenNI) под ROS 2 Jazzy

## Зачем
Оригинальная Orbbec **Astra** (`2bc5:0401`, 2019 г.) — legacy-устройство на
протоколе **OpenNI**, НЕ UVC. Новый `OrbbecSDK_ROS2` её не поддерживает
(в списке только Astra 2 / Astra+ / Astra Mini Pro / Astra Pro Plus).
Нужен старый OpenNI2-драйвер `orbbec/ros2_astra_camera`, но он не собирается
под Jazzy. Патч `astra_camera_jazzy_fix.patch` чинит сборку.

## Что чинит патч (9 файлов)
1. `image_geometry/pinhole_camera_model.h` -> `.hpp` (в Jazzy заголовок переименован)
2. `cv_bridge/cv_bridge.h` -> `.hpp` (то же)
3. `OnParametersSetCallbackType` -> `OnSetParametersCallbackType` (переименован тип rclcpp)

## Установка
```bash
# 1. libuvc (если ещё не стоит)
cd ~
git clone https://github.com/libuvc/libuvc.git
cd libuvc && mkdir -p build && cd build && cmake .. && make -j$(nproc) && sudo make install && sudo ldconfig

# 2. драйвер в рабочее пространство
cd ~/ros2_ws/src
rm -rf OrbbecSDK_ROS2 astra_camera      # убрать несовместимый новый SDK и прошлый клон
git clone https://github.com/orbbec/ros2_astra_camera.git

# 3. применить патч Jazzy
cd ros2_astra_camera
git apply ~/astra_camera_jazzy_fix.patch     # см. raw-ссылку ниже

# 4. зависимости
cd ~/ros2_ws
sudo apt install -y libgflags-dev ros-jazzy-image-geometry ros-jazzy-camera-info-manager \
  ros-jazzy-image-transport ros-jazzy-image-publisher libgoogle-glog-dev libusb-1.0-0-dev \
  libeigen3-dev ros-jazzy-backward-ros libdw-dev

# 5. udev-правила (у legacy Astra свой набор — 56-orbbec-usb.rules)
cd ~/ros2_ws/src/ros2_astra_camera/astra_camera/scripts
sudo bash install.sh
sudo udevadm control --reload && sudo udevadm trigger
# переткнуть USB камеры

# 6. сборка (сначала msgs, потом драйвер)
cd ~/ros2_ws
colcon build --packages-up-to astra_camera
source install/setup.bash
```

## Запуск (два терминала)
```bash
# T1 — драйвер камеры
ros2 launch astra_camera astra.launch.xml

# T2 — наша визуальная одометрия
ros2 launch astra_odometry rgbd_odometry.launch.py publish_tf:=true
```

## Проверка
```bash
ros2 topic hz /camera/color/image_raw
ros2 topic hz /camera/depth/image_raw
ros2 topic echo /odom --field pose.pose.position   # двигай камеру рукой
```
Если у legacy-драйвера имена топиков глубины отличаются от ожидаемых нашим VO
(`/camera/depth/image_raw`, `/camera/color/image_raw`, `/camera/color/camera_info`),
переопредели их аргументами rgbd_odometry.launch.py: depth_topic:=..., rgb_topic:=...,
camera_info_topic:=...
