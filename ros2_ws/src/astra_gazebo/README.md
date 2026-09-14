# astra_gazebo — симуляция робота для проверки одометрии без выезда

Пакет поднимает **виртуального** гусеничного робота в Gazebo Harmonic с камерой
Astra, лидаром и GPS. Позволяет проверить всю связку
**визуальная одометрия → dual-EKF → GPS → Nav2** без реального робота и без
реальной камеры.

Одометрия при этом **настоящая визуальная**: RTAB-Map `rgbd_odometry` считает
`/odom` по синтетическим RGB-D картинкам виртуальной Astra — тот же пайплайн,
что и на железе. GPS и колёсная одометрия смоделированы отдельно для сравнения.

## Зависимости

```bash
sudo apt install -y \
  ros-jazzy-ros-gz-sim \
  ros-jazzy-ros-gz-bridge \
  ros-jazzy-ros-gz-image \
  ros-jazzy-teleop-twist-keyboard \
  xterm
```

(Плюс уже нужные для стека `ros-jazzy-rtabmap-odom`, `ros-jazzy-robot-localization`,
`ros-jazzy-navigation2`, `ros-jazzy-nav2-bringup`.)

Сборка:

```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

## Источник одометрии (`odom_source`)

Аргумент `odom_source` выбирает, откуда берётся `/odom` для EKF:

| Значение | Что даёт | Когда использовать |
|----------|----------|--------------------|
| `ground_truth` (по умолчанию) | идеальную позу из симулятора | проверить связку EKF → GPS → navsat → Nav2 |
| `visual` | настоящую визуальную одометрию RTAB-Map по камере | отладка самой VO |

> ⚠️ На **синтетической** картинке Gazebo визуальная одометрия ведёт себя
> ненадёжно (бедная текстура → потеря фич, рывки, иногда инверсия направления).
> Это нормально: RTAB-Map рассчитан на реальные кадры. Поэтому для проверки
> навигации по умолчанию стоит `ground_truth` — весь остальной стек (EKF, GPS,
> Nav2, cmd_switcher) при этом настоящий и работает точно так же, как на роботе.
> Режим `visual` оставлен для отдельной отладки камеры.

## Запуск

Проверка навигации на идеальной одометрии (рекомендуется):

```bash
ros2 launch astra_gazebo simulation.launch.py
# то же явно:
ros2 launch astra_gazebo simulation.launch.py odom_source:=ground_truth
```

Отладка настоящей визуальной одометрии:

```bash
ros2 launch astra_gazebo simulation.launch.py odom_source:=visual
```

С полной навигацией Nav2:

```bash
ros2 launch astra_gazebo simulation.launch.py use_navigation:=true
```

Управление роботом (в отдельном терминале):

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
    --ros-args -r /cmd_vel:=/cmd_vel/app_manual
```

Команды идут через `cmd_switcher` (как на роботе). Катайте робота между цветными
объектами — в RViz красная стрелка `/odom` (визуальная одометрия) поедет за
роботом, зелёная — эталон из симулятора.

## Что сравнивать

| Топик | Что это |
|-------|---------|
| `/odom` | визуальная одометрия RTAB-Map — **что проверяем** |
| `/wheel/odometry` | колёсная одометрия (Gazebo) — референс |
| `/ground_truth/odometry` | точная поза симулятора — эталон |
| `/odometry/local` | локальный EKF (VO) |
| `/odometry/global` | глобальный EKF (VO + GPS) |

Удобно сравнить визуальную одометрию с эталоном:

```bash
ros2 run astra_odometry odom_monitor
ros2 run astra_odometry odom_monitor --ros-args -p odom_topic:=/ground_truth/odometry
```

Проверка полного стека (как на роботе):

```bash
ros2 run robot_navigation nav_preflight_check --ros-args -p expect_nav2:=false
# (или без -p, если запускали с use_navigation:=true)
```

## Аргументы `simulation.launch.py`

| Аргумент | По умолчанию | Описание |
|----------|--------------|----------|
| `odom_source` | `ground_truth` | источник `/odom`: `ground_truth` или `visual` |
| `use_rviz` | `true` | открыть RViz2 |
| `use_navigation` | `false` | поднимать ли Nav2 (тяжёлый) |
| `world` | `outdoor.sdf` | путь к SDF-миру |
| `x`/`y`/`z`/`yaw` | `0/0/0.2/0` | стартовая поза робота |

## Важное про курс и GPS

* Визуальная одометрия даёт **относительный** курс. Абсолютную привязку даёт
  GPS при движении — **проедьте несколько метров вперёд** после старта.
* GPS-координаты берутся из `spherical_coordinates` в `worlds/outdoor.sdf`
  (по умолчанию Нижний Новгород). Поменяйте на свои, если тестируете конкретный
  GPS-маршрут; координаты маршрута кладите в `robot_navigation/config/gps_waypoints.yaml`.
* Гусеницы смоделированы как skid-steer (визуальные кожухи + 4 скрытых колеса).
  Габариты в `urdf/tracked_robot_sim.urdf.xacro` — приблизительные; при желании
  приведите к реальным размерам АРКОС-1.

## Почему отдельный sim-URDF

Реальный `tracked_robot_description/urdf/tracked_robot.urdf.xacro` содержит только
фреймы датчиков (без тел и колёс) — этого хватает для TF на роботе, но симулятору
нужна физическая модель. Поэтому здесь свой `tracked_robot_sim.urdf.xacro` с теми
же именами фреймов, поэтому конфиги EKF/Nav2/navsat работают без изменений.
Реальный URDF не тронут.
