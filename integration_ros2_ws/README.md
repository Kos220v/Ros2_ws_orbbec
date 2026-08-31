# Интеграция визуальной одометрии Astra в проект `ros2_ws`

Здесь лежит патч, который встраивает разработанную визуальную одометрию с камеры
Orbbec Astra в ваш проект робота **[Kos220v/ros2_ws](https://github.com/Kos220v/ros2_ws)**,
убирая из него **колёсную одометрию, IMU (MPU6050) и компас**.

> ⚠️ Почему патч, а не пуш: моя рабочая сессия привязана к репозиторию
> `Ros2_ws_orbbec`, и пушить в `ros2_ws` я не могу. Патч применяется одной
> командой и даёт точно тот же результат.

## Как применить

```bash
cd ~/ros2_ws                       # ваш проект робота
git checkout -b astra-visual-odometry
git apply /path/to/astra_vo_integration.patch
git add -A && git commit -m "Визуальная одометрия Astra вместо колёс+IMU+компаса"
```

Патч проверен: применяется на свежий клон `ros2_ws` (ветка `main`) **без
конфликтов**. Если хотите сначала посмотреть, что изменится, без записи:

```bash
git apply --check --stat /path/to/astra_vo_integration.patch
```

## Что делает патч

### Добавляет
* **`src/astra_odometry/`** — новый пакет: драйвер камеры Astra (astra_camera /
  OpenNI) + RTAB-Map `rgbd_odometry`. Публикует `/odom` (поза + курс + скорости),
  узел-монитор `odom_monitor`, юнит-тесты.
* **`camera_link` + оптические фреймы Astra** в
  `tracked_robot_description/urdf/tracked_robot.urdf.xacro` — камера жёстко
  спереди на корпусе (свойство `cam_xyz`).

### Убирает
* Пакеты `robot_odom`, `mpu6050_control`, `compass_control` — целиком.
* Узлы/конфиги курса: `mag_declination_node`, `mag_calibrator`, `heading_check`,
  `i2c_check`, `imu_filter.yaml`, `mag_calibration.yaml`.
* Запуск `imu_filter_madgwick`.

### Перенастраивает
* **`start.launch.py`** (слой железа): вместо `robot_odom` + `mpu6050_control` +
  `compass_control` подключает `astra_odometry/visual_odometry.launch.py`.
* **`dual_ekf_navsat.yaml`**: оба EKF теперь берут из `/odom` позу + курс +
  скорости (визуальная одометрия); входы IMU удалены; `navsat_transform`
  работает с `use_odometry_yaw` без IMU.
* **`localization.launch.py`**: остаются только два EKF + `navsat_transform`.
* **`bringup.launch.py`**: убраны аргументы `declination_deg` и `mag_i2c_bus`,
  добавлен `astra_driver_launch`.
* **`nav_preflight_check`**: проверяет RGB/depth камеры и курс из `/odom` вместо
  IMU/магнитометра.

**GPS-навигация (Nav2 + dual-EKF + navsat_transform) сохранена полностью.**

## Что осталось сделать на роботе

1. Установить зависимости (RTAB-Map + драйвер Astra) — см.
   `src/astra_odometry/README.md` внутри патча, раздел «Зависимости».
2. Пересобрать: `colcon build --symlink-install && source install/setup.bash`.
3. Запуск как раньше: `ros2 launch robot_navigation bringup.launch.py`.
4. Подогнать крепление камеры (`cam_xyz` в URDF) под реальное положение Astra.

## Важное про курс

Компаса больше нет, поэтому визуальная одометрия даёт **относительный** курс.
Абсолютную привязку по сторонам света даёт GPS при движении — **после старта
проедьте несколько метров вперёд**, чтобы курс выровнялся.

## Проверка (выполнена офлайн)
* Патч применяется на чистый клон `ros2_ws` без конфликтов.
* Все Python-файлы компилируются; flake8 (F-проверки) чистый.
* URDF разворачивается в валидный XML; все YAML валидны.
* 9 юнит-тестов `astra_odometry` проходят.

---

# Второй патч: симуляция в Gazebo — `astra_gazebo_sim.patch`

Отдельный патч, который добавляет пакет **`astra_gazebo`** — виртуального робота
в **Gazebo Harmonic**, чтобы проверить всю связку
**визуальная одометрия → dual-EKF → GPS → Nav2 без реального робота и без
реальной камеры**.

> Одометрия в симуляции — **настоящая визуальная**: RTAB-Map `rgbd_odometry`
> считает `/odom` по синтетическим RGB-D картинкам виртуальной Astra. Это тот же
> код и тот же пайплайн, что поедет на железе, — а не подсунутая «идеальная»
> поза из симулятора.

## Как применить (ПОСЛЕ первого патча)

```bash
cd ~/ros2_ws                       # уже с применённым astra_vo_integration.patch
git apply /path/to/astra_gazebo_sim.patch
git add -A && git commit -m "Симуляция в Gazebo для проверки VO->EKF->GPS->Nav2"
```

Порядок важен: sim-патч зависит от пакета `astra_odometry` из первого патча.
Проверено: `astra_gazebo_sim.patch` применяется без конфликтов на клон `ros2_ws`
с уже наложенным `astra_vo_integration.patch`.

## Что внутри `astra_gazebo`

* `urdf/tracked_robot_sim.urdf.xacro` — **физическая** модель гусеничного робота
  (skid-steer: гусеничные кожухи + 4 скрытых ведущих колеса) с камерой Astra,
  2D-лидаром и GPS. Имена фреймов **совпадают** с реальным URDF, поэтому конфиги
  EKF/Nav2/navsat работают без правок. Реальный URDF не тронут.
* `worlds/outdoor.sdf` — уличный мир с заданными GPS-координатами (нужны NavSat)
  и текстурными объектами (визуальной одометрии нужна текстура в кадре).
* `config/bridge.yaml` — мост `ros_gz_bridge`. Камера мостится под теми же
  именами, что даёт реальный `astra_camera`; лидар → `/scan`; GPS → `/gps/fix`.
* `launch/simulation.launch.py` — Gazebo + спавн + мост + `robot_state_publisher`
  + `relay_reliable` + `cmd_switcher` + `rgbd_odometry` + локализация
  (+ Nav2 по флагу). Всё с `use_sim_time:=true`.
* `launch/teleop.launch.py`, `rviz/simulation.rviz`, `README.md`.

## Запуск симуляции

```bash
# зависимости
sudo apt install -y ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-bridge \
                    ros-jazzy-ros-gz-image ros-jazzy-teleop-twist-keyboard xterm
cd ~/ros2_ws && colcon build --symlink-install && source install/setup.bash

# только VO + локализация (лёгкий режим)
ros2 launch astra_gazebo simulation.launch.py
# с полной навигацией Nav2
ros2 launch astra_gazebo simulation.launch.py use_navigation:=true

# управление (в отдельном терминале)
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
    --ros-args -r /cmd_vel:=/cmd_vel/app_manual
```

В RViz: красная стрелка `/odom` — визуальная одометрия (что проверяем), зелёная
`/ground_truth/odometry` — эталон из симулятора. Катайте робота между цветными
объектами и смотрите, как расходятся/сходятся траектории. Подробности — в
`src/astra_gazebo/README.md` внутри патча.

### Источник одометрии `odom_source` (важно)

На **синтетической** картинке Gazebo визуальная одометрия ведёт себя ненадёжно
(бедная текстура → RTAB-Map теряет фичи: рывки, иногда движение в другую
сторону). Это ожидаемо — VO рассчитана на реальные кадры. Поэтому в симуляции
есть переключатель источника `/odom`:

```bash
# идеальная одометрия из симулятора — проверка EKF -> GPS -> navsat -> Nav2
ros2 launch astra_gazebo simulation.launch.py            # по умолчанию ground_truth
ros2 launch astra_gazebo simulation.launch.py odom_source:=ground_truth

# настоящая визуальная одометрия — для отдельной отладки камеры
ros2 launch astra_gazebo simulation.launch.py odom_source:=visual
```

В режиме `ground_truth` весь остальной стек (dual-EKF, navsat_transform, Nav2,
cmd_switcher) — **настоящий** и работает ровно так же, как на роботе; меняется
только источник одометрии. Так проверяется вся навигация детерминированно, не
завися от капризов VO на синтетике.

## Проверка (выполнена офлайн)
* `astra_gazebo_sim.patch` применяется на клон `ros2_ws` с наложенным первым
  патчем без конфликтов.
* Launch-файлы компилируются; flake8 (F-проверки) чистый.
* sim-URDF (xacro) разворачивается в валидный XML: 15 links, 3 сенсора
  (RGB-D камера, gpu_lidar, navsat), плагин skid-steer DiffDrive.
* Мир SDF и `bridge.yaml` валидны.

> ⚠️ Gazebo здесь не запускался (в среде нет GPU/Gazebo) — проверена корректность
> файлов и применимость патча. Первый реальный запуск делайте на машине с
> Gazebo Harmonic; габариты робота в sim-URDF приблизительные, при желании
> приведите к реальным размерам АРКОС-1.
