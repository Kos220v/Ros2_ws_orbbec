# Запуск робота по заранее запланированному маршруту

Инструкция для Raspberry Pi и ROS 2 Jazzy. Маршрут состоит из GPS-точек,
которые передаются Nav2 через `gps_waypoint_commander`.

> **Важно:** это инструкция для движения на реальном роботе. Первый запуск
> выполняйте на открытой площадке, на малой скорости, с оператором рядом и
> готовым к немедленной остановке пультом.

## 1. Как работает автономный маршрут

```text
GPS -> /gps/fix ------------------------------┐
STM32 IMU -> /imu/data -----------------------┤
VESC энкодеры -> /wheel/odometry -------------┤
                                              v
                                  robot_localization
                                  map -> odom -> base_link
                                              |
LiDAR -> /scan -> costmap -> Nav2 -> /cmd_vel/auto
                                              |
                               cmd_switcher -> /cmd_vel
                                              |
                                      kolesa_control -> моторы
```

`gps_waypoint_commander` не управляет моторами напрямую. Он загружает YAML с
точками и отправляет его Nav2 через action `/follow_gps_waypoints`.

Безопасность организована следующим образом:

- после запуска робот **не начинает движение автоматически**;
- маршрут запускается сервисом или переводом пульта в режим `AUTO`;
- ручное управление имеет приоритет над `/cmd_vel/auto`;
- перевод пульта из `AUTO` в другой режим отменяет маршрут;
- аварийная отмена доступна через сервис `cancel_route`.

## 2. Что подготовить до запуска

### 2.1. Аппаратная проверка

Перед включением моторов убедиться, что:

1. аккумулятор заряжен;
2. обе гусеницы свободно вращаются и ничего не задевают;
3. LiDAR установлен и не закрыт корпусом;
4. GPS имеет хороший обзор неба;
5. STM32 IMU подключён через USB-UART, а `/dev/imu_stm32` настроен;
6. переключатель ручного управления находится не в `AUTO`;
7. рядом с роботом есть оператор с пультом.

Настройка USB-UART описана отдельно:

```text
src/imu_stm32_bridge/docs/USB_UART_RASPBERRY_PI.md
```

Проверить устройства до запуска ROS:

```bash
ls -l /dev/imu_stm32
ls -l /dev/lidar /dev/gps 2>/dev/null || true
```

Если постоянный симлинк IMU ещё не создан, временно используйте настоящий
порт, например `/dev/ttyUSB0` или `/dev/ttyACM0`.

### 2.2. Подготовить окружение ROS 2

В первом терминале Raspberry Pi:

```bash
cd ~/Ros2_ws_orbbec/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

Если рабочее пространство ещё не собрано:

```bash
cd ~/Ros2_ws_orbbec/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
./rebuild.sh
source install/setup.bash
```

Команды `source` нужно выполнить в каждом новом терминале. Для запуска по
сети и на Raspberry Pi также должна быть настроена DDS-конфигурация:

```bash
cd ~/Ros2_ws_orbbec/ros2_ws
./setup_dds.sh
source ~/.bashrc
```

## 3. Подготовить файл маршрута

Маршрут хранится в YAML. Рекомендуемый формат:

```yaml
waypoints:
  - latitude: 50.77535
    longitude: 6.08389
    yaw: 0.0
  - latitude: 50.77560
    longitude: 6.08450
    yaw: 1.5708
  - latitude: 50.77510
    longitude: 6.08500
```

Поля:

- `latitude` — широта в градусах от `-90` до `90`;
- `longitude` — долгота в градусах от `-180` до `180`;
- `yaw` — необязательный желаемый курс в радианах, ENU:
  - `0` — восток;
  - `1.5708` — север;
  - `3.1416` — запад;
  - `-1.5708` — юг.

Старый формат `lat`/`lon` также поддерживается.

### Рекомендуемый способ записи точек

Координаты лучше записывать GPS-приёмником самого робота, а не брать из
онлайн-карты. Это уменьшает систематическую ошибку GPS-антенны.

1. Запустить основной стек с отключёнными Nav2 и командиром:

   ```bash
   ros2 launch robot_navigation bringup.launch.py \
       use_navigation:=false \
       use_commander:=false
   ```

2. Дождаться сообщений `/gps/fix` и хорошего GPS-фикса.
3. Во втором терминале запустить логгер:

   ```bash
   source /opt/ros/jazzy/setup.bash
   source ~/Ros2_ws_orbbec/ros2_ws/install/setup.bash
   ros2 run robot_navigation gps_waypoint_logger \
       --ros-args -p output_file:=/home/pi/route.yaml
   ```

4. Медленно проехать роботом по будущему маршруту вручную.
5. В каждой нужной точке остановиться и выполнить:

   ```bash
   ros2 service call /gps_waypoint_logger/log_waypoint std_srvs/srv/Trigger
   ```

6. Если последняя точка записана ошибочно:

   ```bash
   ros2 service call /gps_waypoint_logger/undo_waypoint std_srvs/srv/Trigger
   ```

Логгер сохраняет файл после каждой точки. Рекомендуемое расстояние между
точками — примерно 5–20 метров и обязательно отдельная точка на каждом
повороте. Для обычного GPS не следует ставить соседние точки ближе 3 метров.

После завершения проверить файл:

```bash
cat /home/pi/route.yaml
```

Проверить количество точек без запуска робота можно так:

```bash
python3 - <<'PY'
import sys
try:
    import yaml
except ImportError:
    print('Установите python3-yaml: sudo apt install python3-yaml')
    sys.exit(1)

path = '/home/pi/route.yaml'
with open(path, encoding='utf-8') as f:
    data = yaml.safe_load(f) or {}
points = data.get('waypoints', [])
print('Точек:', len(points))
for i, p in enumerate(points, 1):
    print(i, p.get('latitude', p.get('lat')), p.get('longitude', p.get('lon')))
PY
```

### Ручное редактирование

Можно создать файл вручную:

```bash
cp ~/Ros2_ws_orbbec/ros2_ws/src/robot_navigation/config/gps_waypoints.yaml \
   /home/pi/route.yaml
nano /home/pi/route.yaml
```

Не используйте примерные координаты из чужого файла. Ошибка в широте и
долготе может отправить робота в совершенно другое место.

## 4. Проверить систему перед движением

Сначала запустить только железо:

```bash
cd ~/Ros2_ws_orbbec/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch project_start start.launch.py
```

Если IMU подключён не через `/dev/imu_stm32`:

```bash
ros2 launch project_start start.launch.py imu_port:=/dev/ttyUSB0
```

В другом терминале проверить основные топики:

```bash
source /opt/ros/jazzy/setup.bash
source ~/Ros2_ws_orbbec/ros2_ws/install/setup.bash

ros2 topic echo /imu/data --once
ros2 topic echo /gps/fix --once
ros2 topic echo /wheel/odometry --once
ros2 topic echo /scan --once
```

Проверить наличие устройств и частоты:

```bash
ros2 topic list | grep -E 'imu|gps|wheel|scan|cmd_vel'
ros2 topic hz /imu/data
ros2 topic hz /wheel/odometry
ros2 topic hz /scan
```

Перед движением нужно убедиться, что:

- `/imu/data` содержит меняющийся курс и корректный `frame_id`;
- `/gps/fix` имеет статус не `STATUS_NO_FIX`;
- `/wheel/odometry` публикуется и изменяет расстояние при движении гусениц;
- `/scan` содержит дальности LiDAR;
- IMU откалиброван на неподвижном роботе.

## 5. Запустить полный стек с маршрутом

Команда запуска:

```bash
cd ~/Ros2_ws_orbbec/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch robot_navigation bringup.launch.py \
    waypoints_file:=/home/pi/route.yaml \
    imu_port:=/dev/imu_stm32
```

Если используется временный порт:

```bash
ros2 launch robot_navigation bringup.launch.py \
    waypoints_file:=/home/pi/route.yaml \
    imu_port:=/dev/ttyUSB0
```

Дополнительные параметры:

```bash
# Запустить маршрут два раза подряд после старта
ros2 launch robot_navigation bringup.launch.py \
    waypoints_file:=/home/pi/route.yaml \
    number_of_loops:=2

# Запустить только железо и локализацию, без Nav2
ros2 launch robot_navigation bringup.launch.py \
    waypoints_file:=/home/pi/route.yaml \
    use_navigation:=false
```

После запуска подождать завершения инициализации:

- IMU и GPS должны начать публиковать данные сразу;
- локализация стартует с задержкой;
- Nav2 стартует примерно через 15 секунд;
- командир маршрута стартует примерно через 20 секунд.

Проверить состояние Nav2:

```bash
ros2 lifecycle get /controller_server
ros2 lifecycle get /planner_server
ros2 lifecycle get /bt_navigator
ros2 lifecycle get /waypoint_follower
```

Ожидаемое состояние для Nav2 — `active`.

Проверить, что командир прочитал файл маршрута:

```bash
ros2 node list | grep gps_waypoint_commander
ros2 service list | grep gps_waypoint_commander
```

В логах должно быть сообщение с количеством загруженных точек:

```text
Загружено точек маршрута: N
```

## 6. Запустить маршрут

### Вариант A: сервисом

Это рекомендуемый способ для первого автономного заезда.

1. Робот должен стоять на стартовой точке.
2. Пульт должен быть в ручном/безопасном режиме, не в `AUTO`.
3. Оператор должен иметь возможность немедленно перевести пульт обратно.
4. Убедиться, что первая точка находится не дальше примерно 50–60 метров.
5. Выполнить:

```bash
ros2 service call /gps_waypoint_commander/start_route std_srvs/srv/Trigger
```

При успешном запуске ответ будет похож на:

```text
success: true
message: Маршрут отправлен в Nav2: N точек
```

В логах командира появятся текущая точка, прогресс и сообщения о завершении
отдельных waypoint'ов.

### Вариант B: переключателем пульта

Перевести переключатель режима пульта в `AUTO`. Узел `elrs_receiver` публикует
`/control_mode`, а значение `0` означает `AUTO`.

Проверить режим можно так:

```bash
ros2 topic echo /control_mode --once
```

При значении `0` командир запускает маршрут, если GPS-фикс уже получен и
Nav2 action-сервер доступен.

### Автоматический старт

Автоматический старт после запуска штатного `bringup.launch.py` отключён
намеренно. Не включайте его на реальном роботе без стендовой проверки:

```bash
ros2 run robot_navigation gps_waypoint_commander \
    --ros-args \
    -p waypoints_file:=/home/pi/route.yaml \
    -p autostart:=true
```

Такой запуск используется только для тестового стенда и требует, чтобы
остальные узлы Nav2 уже были запущены отдельно.

## 7. Остановить или отменить маршрут

Штатная отмена:

```bash
ros2 service call /gps_waypoint_commander/cancel_route std_srvs/srv/Trigger
```

Альтернативно перевести пульт из `AUTO` в ручной режим. Любая команда от
пульта имеет приоритет над автоматикой.

Для немедленной остановки моторов дополнительно остановить публикацию
команд/выключить привод согласно инструкции по безопасности конкретного
контроллера. Не полагайтесь только на SSH-соединение: при потере сети
оператор должен использовать локальный пульт.

После остановки проверить, что команда остановки действительно дошла:

```bash
ros2 topic echo /cmd_vel --once
```

## 8. Контроль во время маршрута

В отдельном терминале удобно наблюдать:

```bash
# GPS
ros2 topic echo /gps/fix

# Отфильтрованная глобальная поза
ros2 topic echo /odometry/global

# Курс IMU
ros2 topic echo /imu/azimuth

# Пройденное расстояние/скорость от колёс
ros2 topic echo /wheel/odometry

# Команда Nav2 и итоговая команда моторам
ros2 topic echo /cmd_vel/auto
ros2 topic echo /cmd_vel
```

Для визуального контроля запустить RViz с конфигурацией проекта:

```bash
ros2 launch robot_navigation navigation.launch.py
```

Если Nav2 уже запущен через `bringup.launch.py`, второй раз этот launch-файл
запускать не нужно. В RViz следует проверить:

- `Fixed Frame: map`;
- TF-цепочку `map -> odom -> base_link`;
- положение робота;
- `/scan`;
- глобальный и локальный costmap;
- направление стрелки `base_link`.

## 9. Типичные проблемы

### `Маршрут пуст` или `Файл маршрута не найден`

Проверить путь и права:

```bash
ls -l /home/pi/route.yaml
head -30 /home/pi/route.yaml
```

Путь передаётся параметром именно так:

```bash
waypoints_file:=/home/pi/route.yaml
```

### `Старт отменён: нет сообщений в /gps/fix`

Проверить GPS-драйвер и порт. Дождаться открытого неба и статуса фикса:

```bash
ros2 topic echo /gps/fix --once
```

### `Nav2 не отвечает: action /follow_gps_waypoints недоступен`

Проверить, что Nav2 запущен и lifecycle-узлы имеют состояние `active`:

```bash
ros2 action list | grep follow_gps_waypoints
ros2 lifecycle get /waypoint_follower
```

### `GOAL_OUTSIDE_MAP`

Соседние точки слишком далеко друг от друга или первая точка слишком далеко
от робота. Добавить промежуточные точки с шагом до 50 м и подъехать ближе к
первой точке. Скользящий global costmap не покрывает весь маршрут целиком.

### Робот едет в сторону или крутится

Остановить маршрут и проверить:

```bash
ros2 topic echo /imu/azimuth --once
ros2 topic echo /imu/data --once
ros2 topic echo /wheel/odometry --once
```

Чаще всего причина — магнитная калибровка, неверная ориентация IMU или
инверсия направления моторов в параметрах `kolesa_control`.

### Робот не останавливается у точки

Для обычного GPS ошибка может составлять несколько метров. Не ставить точки
слишком близко и не уменьшать `xy_goal_tolerance` ниже реальной точности
приёмника. При необходимости изменить параметр в
`robot_navigation/config/nav2_params.yaml`.

### Робот останавливается при препятствии

Проверить, что `/scan` публикуется, costmap видит препятствие, а LiDAR не
перекрыт. Не отключать защиту costmap на реальном роботе.

## 10. Завершение работы

После окончания маршрута:

1. дождаться сообщения об успешном завершении или отменить маршрут;
2. перевести пульт в ручной безопасный режим;
3. убедиться, что `/cmd_vel` равен нулю;
4. остановить ROS 2 сочетанием `Ctrl+C` в терминале запуска;
5. выключить питание приводов и только затем отключить Raspberry Pi.
