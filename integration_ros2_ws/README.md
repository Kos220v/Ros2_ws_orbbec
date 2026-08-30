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
