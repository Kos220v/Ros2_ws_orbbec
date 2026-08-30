# Ros2_ws_orbbec — визуальная одометрия с камеры Orbbec Astra

Рабочее пространство ROS 2 для получения **одометрии** (и только одометрии — без
построения карты/SLAM) с 3D-камеры **Orbbec Astra**, подключённой по USB.

* **ОС / ROS:** Ubuntu 24.04 + ROS 2 **Jazzy**
* **Драйвер камеры:** `astra_camera` (OpenNI / Orbbec)
* **Одометрия:** RTAB-Map `rgbd_odometry` (визуальная одометрия по RGB-D)
* **Робот:** diff-drive база с URDF и камерой Astra сверху

```
Astra (USB)
   │  /camera/color/image_raw  +  /camera/depth/image_raw (registered)
   ▼
rtabmap rgbd_odometry ──►  /odom  (nav_msgs/Odometry)
                       └─►  TF: odom → base_footprint
```

---

## Содержимое

| Пакет | Назначение |
|-------|-----------|
| `astra_description` | URDF/xacro робота (diff-drive + камера Astra), TF-дерево, RViz |
| `astra_odometry`    | запуск драйвера камеры, RTAB-Map `rgbd_odometry`, узел-монитор одометрии, тесты, скрипты |

---

## 1. Зависимости

Установите ROS 2 Jazzy, затем зависимости пакетов:

```bash
sudo apt update
sudo apt install -y \
  ros-jazzy-rtabmap-odom \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-joint-state-publisher \
  ros-jazzy-joint-state-publisher-gui \
  ros-jazzy-xacro \
  ros-jazzy-tf2-ros \
  ros-jazzy-rviz2
```

### Драйвер камеры Astra (OpenNI)

Драйвер `astra_camera` не ставится через apt для Jazzy — соберите из исходников
в этом же workspace:

```bash
cd ~/Ros2_ws_orbbec/src
git clone https://github.com/orbbec/ros2_astra_camera.git
# зависимости драйвера
sudo apt install -y libgflags-dev nlohmann-json3-dev \
  ros-jazzy-image-transport ros-jazzy-image-publisher ros-jazzy-camera-info-manager \
  libgoogle-glog-dev libusb-1.0-0-dev libeigen3-dev

# правила udev для доступа к камере по USB (один раз)
cd ros2_astra_camera/astra_camera/scripts
sudo bash install.sh
sudo udevadm control --reload && sudo udevadm trigger
```

> Отключите и заново подключите камеру после установки udev-правил.

---

## 2. Сборка

```bash
cd ~/Ros2_ws_orbbec
rosdep install --from-paths src --ignore-src -r -y   # необязательно, подтянет остальное
colcon build --symlink-install
source install/setup.bash
```

Добавьте `source ~/Ros2_ws_orbbec/install/setup.bash` в `~/.bashrc` для удобства.

---

## 3. Запуск на роботе (полный стек)

Одна команда поднимает описание робота + драйвер камеры + одометрию:

```bash
source ~/Ros2_ws_orbbec/install/setup.bash
ros2 launch astra_odometry robot_odometry.launch.py
```

С визуализацией в RViz2 (одометрия, TF, модель робота):

```bash
ros2 launch astra_odometry robot_odometry.launch.py use_rviz:=true
```

Полезные аргументы:

| Аргумент | По умолчанию | Описание |
|----------|--------------|----------|
| `use_rviz` | `false` | открыть RViz2 с готовой конфигурацией |
| `publish_tf` | `true` | публиковать TF `odom → base_footprint` |
| `driver_launch` | `astra.launch.xml` | launch-файл драйвера внутри `astra_camera` (например `astra_mini.launch.xml`) |
| `use_sim_time` | `false` | использовать `/clock` |

Результат:

* Топик **`/odom`** (`nav_msgs/Odometry`)
* Трансформа **`odom → base_footprint`**

---

## 4. Ручные тесты

### 4.1 Только камера (проверка драйвера)

```bash
ros2 launch astra_odometry astra_camera.launch.py
ros2 topic list | grep camera
ros2 topic hz /camera/color/image_raw
ros2 topic hz /camera/depth/image_raw
```

### 4.2 Только одометрия (камера уже запущена в другом терминале)

```bash
ros2 launch astra_odometry rgbd_odometry.launch.py
```

### 4.3 Монитор одометрии (человекочитаемый вывод)

Печатает позу (x, y, z, yaw), скорости, пройденный путь, частоту и
предупреждение, если VO «потерялась»:

```bash
ros2 run astra_odometry odom_monitor
# пример вывода:
# pose x=+0.123 y=-0.045 z=+0.002 yaw=  +5.3deg | vel lin=0.031 m/s ang=+0.012 rad/s | dist=0.412 m | rate=28.0 Hz
```

Перемещайте камеру (в кадре должна быть текстура/предметы) — поза должна меняться.

### 4.4 Скрипт быстрой проверки

Проверяет наличие топиков, их частоты, один сэмпл `/odom` и TF:

```bash
ros2 run astra_odometry check_odometry.sh
# или напрямую:
src/astra_odometry/scripts/check_odometry.sh
```

### 4.5 Ручная проверка «на глаз»

```bash
# посмотреть сообщения одометрии
ros2 topic echo /odom

# проверить трансформу
ros2 run tf2_ros tf2_echo odom base_footprint

# дерево TF в PDF
ros2 run tf2_tools view_frames
```

### 4.6 Просмотр только URDF/TF робота (без камеры)

```bash
ros2 launch astra_description description.launch.py use_rviz:=true use_gui:=true
```

---

## 5. Автоматические тесты (`colcon test`)

Быстрые тесты без железа (юнит-тесты математики + линтеры flake8/pep257):

```bash
cd ~/Ros2_ws_orbbec
colcon test --packages-select astra_odometry
colcon test-result --verbose
```

---

## 6. Советы по качеству одометрии

Визуальная одометрия по RGB-D работает лучше всего, когда:

* в кадре есть **текстура** (не пустая белая стена);
* достаточное **освещение**;
* движение **плавное**, без рывков;
* дистанция до сцены в рабочем диапазоне Astra (~0.6–8 м).

Если одометрия «прыгает» или теряется — `odom_monitor` выдаст предупреждение
«visual odometry may be LOST». Параметры RTAB-Map можно донастроить в
`src/astra_odometry/launch/rgbd_odometry.launch.py` (или через
`src/astra_odometry/config/rgbd_odometry.yaml`).

---

## 7. Дерево кадров (TF)

```
odom
 └─ base_footprint          (публикует rgbd_odometry)
     └─ base_link
         ├─ left_wheel
         ├─ right_wheel
         ├─ caster_wheel
         └─ camera_link
             ├─ camera_depth_frame ─ camera_depth_optical_frame
             └─ camera_rgb_frame   ─ camera_rgb_optical_frame
```

Смещение камеры относительно базы задаётся в
`src/astra_description/urdf/astra_robot.urdf.xacro` (свойства `cam_x/cam_y/cam_z`).
**Обязательно подгоните их под реальное крепление камеры на вашем роботе.**
