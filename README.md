# Ros2_ws_orbbec — визуальная одометрия с камеры Orbbec Astra (робот АРКОС-1)

Рабочее пространство ROS 2 для получения **одометрии** (и только одометрии — без
построения карты/SLAM) с 3D-камеры **Orbbec Astra**, подключённой по USB.

* **ОС / ROS:** Ubuntu 24.04 + ROS 2 **Jazzy**
* **Драйвер камеры:** `astra_camera` (OpenNI / Orbbec)
* **Одометрия:** RTAB-Map `rgbd_odometry` (визуальная одометрия по RGB-D)
* **Робот:** **АРКОS-1 СБ «Робот-обходчик»** — гусеничная (skid-steer) самоходная
  тележка (~124 кг). Камера Astra **жёстко закреплена спереди на корпусе**, чтобы
  кадр одометрии не смещался относительно базы (в отличие от поворотной платформы
  с видеокамерой обзора).

> Гусеницы в модели смоделированы как **skid-steer**: визуальные гусеничные
> кожухи закрывают четыре скрытых ведущих колеса (по два на сторону), которыми
> управляет плагин DiffDrive. Повороты — за счёт разницы скоростей бортов, как у
> реального гусеничного шасси. Габариты/масса в
> `src/astra_description/urdf/astra_robot.urdf.xacro` заданы приблизительно по
> сборочному чертежу — **уточните под реальные размеры вашего робота**.

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
| `astra_description` | URDF/xacro робота (diff-drive + камера Astra), TF-дерево, RViz. Одна модель для реального робота и симуляции (`use_gazebo:=true`) |
| `astra_odometry`    | запуск драйвера камеры, RTAB-Map `rgbd_odometry`, узел-монитор одометрии, тесты, скрипты |
| `astra_gazebo`      | симуляция в Gazebo Harmonic: виртуальный робот + depth-камера + мир, мост ros_gz. Проверка одометрии **без реального робота** |

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

## 4A. Проверка БЕЗ реального робота — симуляция в Gazebo

Пакет `astra_gazebo` поднимает **полностью виртуальный** стенд: робот с depth-камерой
в мире Gazebo Harmonic. Одометрия при этом остаётся **визуальной** (RTAB-Map по
синтетическому RGB-D), а не берётся из симулятора — то есть проверяется тот же
самый пайплайн, что и на реальном роботе. Реальная камера и робот не нужны.

### Зависимости симуляции (Gazebo Harmonic — штатный для Jazzy)

```bash
sudo apt install -y \
  ros-jazzy-ros-gz-sim \
  ros-jazzy-ros-gz-bridge \
  ros-jazzy-ros-gz-image \
  ros-jazzy-teleop-twist-keyboard \
  xterm
```

Пересоберите workspace, чтобы появился новый пакет:

```bash
cd ~/Ros2_ws_orbbec
colcon build --symlink-install
source install/setup.bash
```

### Запуск симуляции

```bash
ros2 launch astra_gazebo simulation.launch.py
```

Откроются Gazebo и RViz2. Что запускается автоматически:
Gazebo с миром `astra_world` → робот (URDF с `use_gazebo:=true`) → мост ros_gz →
RTAB-Map `rgbd_odometry`.

### Управление роботом (в отдельном терминале)

```bash
source ~/Ros2_ws_orbbec/install/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
# клавиши: i вперёд, k стоп, j/l поворот, , назад
```

Катайте робота между цветными объектами — в RViz красная стрелка `/odom`
(визуальная одометрия) должна двигаться вслед за роботом.

### Три источника одометрии для сравнения

| Топик | Что это |
|-------|---------|
| `/odom` | **визуальная** одометрия RTAB-Map — то, что мы тестируем |
| `/wheel/odometry` | одометрия по колёсам (diff-drive Gazebo) — референс |
| `/ground_truth/odometry` | точная поза из симулятора — эталон |

Сравнить визуальную одометрию с эталоном:

```bash
ros2 run astra_odometry odom_monitor                                   # /odom
ros2 run astra_odometry odom_monitor --ros-args -p odom_topic:=/ground_truth/odometry
ros2 topic echo /odom
```

В RViz одновременно видны красная стрелка (VO) и зелёная (ground truth) — чем
ближе траектории, тем точнее одометрия.

### Полезные аргументы `simulation.launch.py`

| Аргумент | По умолчанию | Описание |
|----------|--------------|----------|
| `use_rviz` | `true` | открыть RViz2 |
| `x` / `y` / `z` / `yaw` | `0/0/0.08/0` | начальная поза робота |
| `world` | `astra_world.sdf` | путь к SDF-миру |

> Советы: одометрия по синтетическому RGB-D чувствительна к текстуре — в мире
> специально расставлены цветные объекты и стена. Двигайтесь плавно; при слишком
> быстром вращении VO может «потеряться» (как и на реальной камере).

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
         ├─ left_track / right_track       (визуальные гусеницы)
         ├─ front_left_wheel  / rear_left_wheel   (скрытые ведущие)
         ├─ front_right_wheel / rear_right_wheel  (скрытые ведущие)
         └─ camera_link                    (жёстко на корпусе, спереди)
             ├─ camera_depth_frame ─ camera_depth_optical_frame
             └─ camera_rgb_frame   ─ camera_rgb_optical_frame
```

Смещение камеры относительно базы задаётся в
`src/astra_description/urdf/astra_robot.urdf.xacro` (свойства `cam_x/cam_y/cam_z`).
**Обязательно подгоните их под реальное крепление камеры на вашем роботе.**
Там же — габариты корпуса (`base_*`), колея (`wheel_separation`), база
(`wheel_base`), радиус ведущего колеса (`wheel_radius`) и размеры гусениц
(`track_*`); приведите их к реальным значениям АРКОС-1.
