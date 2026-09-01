# Перенос проекта на робота (Raspberry Pi 4, Ubuntu 24.04 + ROS 2 Jazzy)

Пошаговая инструкция: развернуть готовый стек (визуальная одометрия Astra +
GPS-навигация Nav2) на Raspberry Pi 4. Сценарий: **Ubuntu 24.04 arm64 и ROS 2
Jazzy уже установлены**, код переносим через **git**, собираем **на самом Pi**.

Все патчи лежат в этом же каталоге `integration_ros2_ws/`. Их raw-ссылки на GitHub:

```
https://raw.githubusercontent.com/Kos220v/Ros2_ws_orbbec/arena/01a0537c-ros2-ws-orbbec/integration_ros2_ws/astra_vo_integration.patch
https://raw.githubusercontent.com/Kos220v/Ros2_ws_orbbec/arena/01a0537c-ros2-ws-orbbec/integration_ros2_ws/nav2_rotation_fix.patch
https://raw.githubusercontent.com/Kos220v/Ros2_ws_orbbec/arena/01a0537c-ros2-ws-orbbec/integration_ros2_ws/astra_camera_jazzy_fix.patch
https://raw.githubusercontent.com/Kos220v/Ros2_ws_orbbec/arena/01a0537c-ros2-ws-orbbec/integration_ros2_ws/astra_gazebo_sim.patch
```

> ⚠️ `astra_gazebo_sim.patch` — только симуляция. **На робота его не ставим**
> (Gazebo на Pi не нужен и тянет лишние тяжёлые зависимости).

---

## 0. Подготовка Pi (один раз)

```bash
# swap: первая сборка astra_camera (C++) может упереться в 4 ГБ ОЗУ.
# Добавляем 2 ГБ swap на время сборки.
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
free -h                          # проверить, что swap появился

# базовые инструменты
sudo apt update
sudo apt install -y git python3-colcon-common-extensions python3-rosdep build-essential cmake
```

> Быстрый USB-накопитель/SSD под `~/ros2_ws` крайне желателен — сборка и RTAB-Map
> активно пишут на диск, microSD изнашивается и тормозит.

---

## 1. Перенос кода через git

На Pi:

```bash
cd ~
git clone https://github.com/Kos220v/ros2_ws.git
cd ros2_ws
git checkout -b astra-visual-odometry

# скачать патчи
cd ~
for p in astra_vo_integration nav2_rotation_fix astra_camera_jazzy_fix; do
  wget -O ~/$p.patch \
  https://raw.githubusercontent.com/Kos220v/Ros2_ws_orbbec/arena/01a0537c-ros2-ws-orbbec/integration_ros2_ws/$p.patch
done
```

Наложить патчи **строго по порядку**:

```bash
cd ~/ros2_ws
git apply --check ~/astra_vo_integration.patch && git apply ~/astra_vo_integration.patch
git apply --check ~/nav2_rotation_fix.patch   && git apply ~/nav2_rotation_fix.patch
git add -A && git commit -m "Astra VO вместо колёс+IMU+компаса + фикс контроллера Nav2"
```

> `--check` сначала проверяет применимость без записи. Если ругнётся «already
> exists» или «patch does not apply» — значит база не чистый `ros2_ws` main;
> напиши мне вывод, разберёмся.

---

## 2. Драйвер камеры Astra (OpenNI) — собирается из исходников

Оригинальная Astra 2019 г. работает только через OpenNI. Ставим
пропатченный `ros2_astra_camera`:

```bash
# 2.1 libuvc из исходников
cd ~
git clone https://github.com/libuvc/libuvc.git
cd libuvc && mkdir -p build && cd build
cmake .. && make -j$(nproc) && sudo make install && sudo ldconfig

# 2.2 драйвер в рабочее пространство
cd ~/ros2_ws/src
rm -rf OrbbecSDK_ROS2 astra_camera        # убрать несовместимый новый SDK, если есть
git clone https://github.com/orbbec/ros2_astra_camera.git
cd ros2_astra_camera
git apply ~/astra_camera_jazzy_fix.patch  # фикс сборки под Jazzy (19 файлов)

# 2.3 системные зависимости драйвера
sudo apt install -y libgflags-dev ros-jazzy-image-geometry ros-jazzy-camera-info-manager \
  ros-jazzy-image-transport ros-jazzy-image-publisher libgoogle-glog-dev libusb-1.0-0-dev \
  libeigen3-dev ros-jazzy-backward-ros libdw-dev

# 2.4 udev-правила для legacy Astra (иначе камера видна только под sudo)
cd ~/ros2_ws/src/ros2_astra_camera/astra_camera/scripts
sudo bash install.sh
sudo udevadm control --reload && sudo udevadm trigger
# после этого ПЕРЕТКНУТЬ USB камеры
```

---

## 3. Зависимости остального стека

RTAB-Map ставится **готовым пакетом** (НЕ компилируется — это важно для Pi):

```bash
sudo apt install -y ros-jazzy-rtabmap-odom

# Nav2 + robot_localization + мелочи, если ещё не стоят
sudo apt install -y ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
  ros-jazzy-robot-localization ros-jazzy-rmw-cyclonedds-cpp

# добить остальные объявленные зависимости автоматически
cd ~/ros2_ws
sudo rosdep init 2>/dev/null; rosdep update
rosdep install --from-paths src --ignore-src -r -y \
  --skip-keys "astra_camera ydlidar_ros2_driver"
```

---

## 4. Сборка на Pi

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash

# сначала msgs+драйвер камеры (C++, самая долгая часть — 10-20 мин на Pi 4)
colcon build --packages-up-to astra_camera --parallel-workers 2

# затем весь проект (лидар и view_robot пропускаем, если не нужны на роботе)
colcon build --symlink-install --parallel-workers 2 \
  --packages-skip ydlidar_ros2_driver view_robot

source install/setup.bash
```

> `--parallel-workers 2` бережёт ОЗУ на Pi (по умолчанию colcon жрёт по числу
> ядер и может словить OOM). Если всё равно падает по памяти — поставь `1`.

---

## 5. DDS (тот же, что в симуляции)

Чтобы узлы стабильно видели друг друга (как мы выяснили при тесте маршрута):

```bash
cd ~/ros2_ws
source ./setup_dds.sh        # CYCLONEDDS_URI + RMW=rmw_cyclonedds_cpp
```

Скрипт добавляет `CYCLONEDDS_URI` в `~/.bashrc`, так что в новых терминалах DDS
подхватится сам. **Во всех терминалах на роботе должен быть один и тот же RMW.**

---

## 6. Подгонка под реальное железо

1. **Крепление камеры.** В `src/tracked_robot_description/urdf/tracked_robot.urdf.xacro`
   свойство `cam_xyz` — задай реальное положение Astra на корпусе (метры, от
   `base_link`). Камера жёстко спереди, НЕ на поворотной платформе.
2. **Имена топиков камеры.** Если legacy-драйвер отдаёт глубину/цвет под другими
   именами, переопредели в запуске VO:
   `depth_topic:=... rgb_topic:=... camera_info_topic:=...`
3. **Реальный маршрут.** `src/robot_navigation/config/gps_waypoints.yaml` пуст —
   заполни настоящими координатами обхода. Файл `gps_waypoints_sim.yaml` — только
   для симуляции, на робота не влияет. Записать маршрут прямо на объекте:
   `ros2 run robot_navigation gps_waypoint_logger`.

---

## 7. Проверка на роботе (по возрастанию)

```bash
# 7.1 Камера отдаёт картинку
ros2 launch astra_camera astra.launch.xml
ros2 topic hz /camera/color/image_raw          # ~10-30 Гц
ros2 topic hz /camera/depth/image_raw

# 7.2 Визуальная одометрия (в другом терминале)
ros2 launch astra_odometry rgbd_odometry.launch.py publish_tf:=true frame_id:=camera_link
ros2 topic echo /odom --field pose.pose.position   # двигай робота — координаты меняются

# 7.3 Диагностика всего стека перед выездом
ros2 run robot_navigation nav_preflight_check      # на роботе камера ДОЛЖНА быть зелёной

# 7.4 Полный запуск как раньше
ros2 launch robot_navigation bringup.launch.py
```

---

## 8. Про курс (важно!)

Компаса больше нет → визуальная одометрия даёт **относительный** курс.
Абсолютную привязку по сторонам света даёт GPS при движении: **после старта
проедь несколько метров вперёд**, чтобы курс выровнялся. Только после этого
запускай проезд маршрута.

---

## 9. Автозапуск при включении робота (опционально)

Когда всё проверено, оформи `bringup.launch.py` как systemd-сервис, чтобы стек
поднимался сам. Заготовку сервис-юнита могу сгенерировать — скажи.

---

## Частые проблемы

| Симптом | Причина / решение |
|---|---|
| `colcon build` падает без сообщения | OOM. Увеличь swap, `--parallel-workers 1` |
| Камера видна только под sudo | udev-правила не применены — повтори шаг 2.4 + переткни USB |
| `nav_preflight_check`: камера FAIL | драйвер не запущен / USB / udev |
| Сервис/топик «не виден» между терминалами | разный RMW — `source ./setup_dds.sh` во ВСЕХ |
| Nav2 отклоняет маршрут | нет GPS-фикса → navsat_transform без `/fromLL`; жди фикс |
| `RTPS_READER_HISTORY Error` | работает FastRTPS вместо Cyclone — примени setup_dds.sh |
