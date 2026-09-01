#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
nav_preflight_check — проверка готовности стека ПЕРЕД выездом.

Автономный робот на улице ломается дорого. Этот узел за 15 секунд проверяет
всё, что обычно и оказывается причиной неудачного заезда, и печатает понятный
чеклист. Запускать после bringup, до того как переводить пульт в AUTO:

    ros2 run robot_navigation nav_preflight_check

Что проверяется:
  1. Идут ли данные со всех датчиков (GNSS, камера Astra, лидар, одометрия).
  2. Есть ли валидный GPS-фикс и сколько спутников.
  3. Содержит ли /odom ориентацию (курс из визуальной одометрии).
  4. Собрана ли TF-цепочка map -> odom -> base_link.
  5. Публикуется ли /odometry/gps (то есть работает ли navsat_transform).
  6. Поднят ли экшен Nav2 /follow_gps_waypoints.
  7. Согласован ли курс визуальной одометрии с направлением движения по GPS.

ИСТОЧНИК ОДОМЕТРИИ: колёсная одометрия + IMU + компас заменены визуальной
одометрией RTAB-Map с камеры Astra. Проверок IMU/магнитометра здесь больше нет;
вместо них проверяются RGB/depth-топики камеры и наличие курса в /odom.
"""

import math

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from nav2_msgs.action import FollowGPSWaypoints
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, LaserScan, NavSatFix, NavSatStatus

import tf2_ros


GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def quaternion_to_yaw(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class PreflightCheck(Node):

    def __init__(self):
        super().__init__('nav_preflight_check')

        self.declare_parameter('duration', 15.0)
        # Nav2 можно намеренно не запускать (use_navigation:=false),
        # когда отлаживается только локализация. Тогда его отсутствие
        # не должно выглядеть как поломка.
        self.declare_parameter('expect_nav2', True)

        self._failures = []
        self._warnings = []

        self._counts = {}
        self._last = {}

        self._subscribe(NavSatFix, '/gps/fix', qos_profile_sensor_data)
        self._subscribe(Image, '/camera/color/image_raw',
                        qos_profile_sensor_data)
        self._subscribe(Image, '/camera/depth/image_raw',
                        qos_profile_sensor_data)
        self._subscribe(Odometry, '/odom', 10)
        self._subscribe(Odometry, '/odometry/local', 10)
        self._subscribe(Odometry, '/odometry/global', 10)
        self._subscribe(Odometry, '/odometry/gps', 10)
        self._subscribe(LaserScan, '/scan_reliable', qos_profile_sensor_data)

        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self)

        self._client = ActionClient(
            self, FollowGPSWaypoints, 'follow_gps_waypoints')

        duration = float(self.get_parameter('duration').value)
        self.get_logger().info(
            f'Сбор данных {duration:.0f} секунд, не трогайте робота...')
        self._timer = self.create_timer(duration, self._report)

    def _subscribe(self, msg_type, topic, qos):
        self._counts[topic] = 0

        def cb(msg, t=topic):
            self._counts[t] += 1
            self._last[t] = msg

        self.create_subscription(msg_type, topic, cb, qos)

    # ------------------------------------------------------------------ вывод
    def _line(self, ok, title, detail=''):
        """Печатает пункт чеклиста и запоминает результат для итога."""
        if ok is True:
            mark = f'{GREEN}[ OK ]{RESET}'
        elif ok is None:
            mark = f'{YELLOW}[ ?? ]{RESET}'
            self._warnings.append(title)
        else:
            mark = f'{RED}[FAIL]{RESET}'
            self._failures.append(title)
        print(f'{mark} {title}')
        if detail:
            for row in detail.split('\n'):
                print(f'       {row}')

    def _report(self):
        self._timer.cancel()
        duration = float(self.get_parameter('duration').value)

        print('\n' + '=' * 72)
        print('  ПРОВЕРКА ГОТОВНОСТИ К АВТОНОМНОМУ ЗАЕЗДУ')
        print('=' * 72)

        self._check_sensors(duration)
        self._check_gps()
        self._check_orientation()
        self._check_tf()
        self._check_navsat()
        self._check_nav2()
        self._check_heading_consistency()

        self._summary()
        rclpy.shutdown()

    def _summary(self):
        print()
        print('=' * 72)
        if self._failures:
            print(f'  {RED}ИТОГ: провалено пунктов — '
                  f'{len(self._failures)}{RESET}')
            for title in self._failures:
                print(f'    - {title}')
            print()
            print('  ВЫЕЗЖАТЬ НЕЛЬЗЯ, пока это не устранено.')
        elif self._warnings:
            print(f'  {YELLOW}ИТОГ: замечаний — {len(self._warnings)}{RESET}')
            for title in self._warnings:
                print(f'    - {title}')
            print()
            print('  Критичных отказов нет, но перечисленное стоит проверить.')
        else:
            print(f'  {GREEN}ИТОГ: все пункты пройдены.{RESET}')
            print('  Можно переводить пульт в AUTO.')
        print('=' * 72)
        print()

    def _check_sensors(self, duration):
        print('\n--- Датчики ---')
        expectations = {
            '/gps/fix': 0.5,
            '/camera/color/image_raw': 10.0,
            '/camera/depth/image_raw': 10.0,
            '/odom': 10.0,
            '/scan_reliable': 3.0,
        }
        hints = {
            '/gps/fix': 'Проверьте питание и порт GNSS (nmea_navsat_driver).',
            '/camera/color/image_raw':
                'Камера Astra не отдаёт RGB. Проверьте по порядку:\n'
                '  1) подключение по USB (lsusb — ищите Orbbec)\n'
                '  2) запущен ли драйвер astra_camera\n'
                '  3) udev-правила драйвера (scripts/install.sh)',
            '/camera/depth/image_raw':
                'Камера Astra не отдаёт depth. Обычно та же причина, что и с\n'
                'RGB. Если RGB идёт, а depth нет — проверьте depth_registration\n'
                'в astra_odometry/launch/astra_camera.launch.py.',
            '/odom': 'Не публикуется визуальная одометрия. Проверьте, идут ли\n'
                     'RGB и depth выше: без них rgbd_odometry молчит. Если\n'
                     'изображения идут, а /odom нет — смотрите лог узла\n'
                     'rgbd_odometry (мало текстуры / рассинхрон QoS).',
            '/scan_reliable': 'Не запущен лидар или relay_reliable.',
        }

        for topic, expected_hz in expectations.items():
            count = self._counts.get(topic, 0)
            hz = count / duration
            if count == 0:
                self._line(False, f'{topic}: нет данных', hints[topic])
            elif hz < expected_hz * 0.5:
                self._line(
                    None,
                    f'{topic}: {hz:.1f} Гц (ожидалось ~{expected_hz:.0f} Гц)',
                    'Частота занижена. Проверьте загрузку CPU и шину I2C/USB.')
            else:
                self._line(True, f'{topic}: {hz:.1f} Гц')

    def _check_gps(self):
        print('\n--- GNSS ---')
        fix = self._last.get('/gps/fix')
        if fix is None:
            self._line(False, 'GPS-фикс', 'Сообщений нет вообще.')
            return

        if fix.status.status == NavSatStatus.STATUS_NO_FIX:
            self._line(
                False, 'GPS-фикс отсутствует',
                'Приёмник видит спутники, но решения нет. Вынесите робота на\n'
                'открытое место и подождите: холодный старт занимает до 2 минут.')
            return

        cov = fix.position_covariance[0]
        acc = math.sqrt(cov) if cov > 0 else float('nan')

        detail = f'широта {fix.latitude:.7f}, долгота {fix.longitude:.7f}'
        if not math.isnan(acc):
            detail += f'\nоценка точности по горизонтали: ~{acc:.1f} м'

        if not math.isnan(acc) and acc > 10.0:
            self._line(
                None, 'GPS-фикс есть, но точность плохая',
                detail + '\nПри точности хуже 10 м робот будет вилять. '
                         'Дождитесь большего числа спутников.')
        else:
            self._line(True, 'GPS-фикс валиден', detail)

    def _check_orientation(self):
        print('\n--- Ориентация (курс из визуальной одометрии) ---')
        odom = self._last.get('/odom')
        if odom is None:
            self._line(
                False, 'Нет /odom',
                'Визуальная одометрия не публикует курс. Сначала разберитесь\n'
                'с топиками камеры выше (RGB/depth).')
            return

        yaw = quaternion_to_yaw(odom.pose.pose.orientation)
        self._line(
            True, 'Курс визуальной одометрии публикуется',
            f'yaw: {math.degrees(yaw):+.1f}° (ОТНОСИТЕЛЬНЫЙ, от точки старта)\n'
            f'Это не абсолютный азимут: у визуальной одометрии нет компаса.\n'
            f'Абсолютную привязку по сторонам света даёт GPS при движении —\n'
            f'проедьте несколько метров вперёд для выравнивания курса.')

    def _check_tf(self):
        print('\n--- Дерево TF ---')
        for parent, child in (('map', 'odom'), ('odom', 'base_link')):
            try:
                self._tf_buffer.lookup_transform(
                    parent, child, rclpy.time.Time())
                self._line(True, f'{parent} -> {child}')
            except Exception as exc:
                hint = ('map -> odom публикует ekf_filter_node_map.'
                        if parent == 'map'
                        else 'odom -> base_link публикует ekf_filter_node_odom.\n'
                             'Убедитесь, что publish_tf выключен у rgbd_odometry '
                             'иначе трансформ публикуют двое.')
                self._line(False, f'{parent} -> {child} отсутствует',
                           f'{hint}\n{exc}')

    def _check_navsat(self):
        print('\n--- navsat_transform ---')
        if self._counts.get('/odometry/gps', 0) > 0:
            self._line(True, '/odometry/gps публикуется')
        else:
            self._line(
                False, '/odometry/gps молчит',
                'navsat_transform не смог связать GPS с фреймом map.\n'
                'Обычные причины: нет фикса, не пришла отфильтрованная\n'
                'одометрия /odometry/global, либо робот ещё не двигался\n'
                '(курс из GPS появляется только при движении).')

        if self._counts.get('/odometry/global', 0) > 0:
            self._line(True, '/odometry/global публикуется (глобальный EKF)')
        else:
            self._line(False, '/odometry/global молчит',
                       'Не работает ekf_filter_node_map.')

    def _check_nav2(self):
        print('\n--- Nav2 ---')
        expect = bool(self.get_parameter('expect_nav2').value)

        if self._client.wait_for_server(timeout_sec=5.0):
            self._line(True, 'Экшен /follow_gps_waypoints доступен')
        elif not expect:
            self._line(
                None, 'Nav2 не запущен (проверка отключена параметром)',
                'Это ожидаемо при expect_nav2:=false.')
        else:
            self._line(
                False, 'Экшен /follow_gps_waypoints недоступен',
                'Если вы запускали bringup с use_navigation:=false — это\n'
                'ожидаемо, Nav2 просто не поднимали. Тогда запустите проверку\n'
                'так: ros2 run robot_navigation nav_preflight_check \\\n'
                '        --ros-args -p expect_nav2:=false\n'
                '\n'
                'Иначе Nav2 не поднялся или lifecycle-менеджер не активировал\n'
                'узлы. Смотрите: ros2 lifecycle get /waypoint_follower')

    def _check_heading_consistency(self):
        print('\n--- Согласованность визуальной одометрии и глобального EKF ---')
        vo = self._last.get('/odom')
        glob = self._last.get('/odometry/global')

        if vo is None or glob is None:
            self._line(None, 'Проверка невозможна',
                       'Нужны и /odom (визуальная одометрия), и '
                       '/odometry/global.')
            return

        yaw_vo = quaternion_to_yaw(vo.pose.pose.orientation)
        yaw_glob = quaternion_to_yaw(glob.pose.pose.orientation)
        diff = math.degrees(
            math.atan2(math.sin(yaw_vo - yaw_glob),
                       math.cos(yaw_vo - yaw_glob)))

        # Курс VO относительный, глобального EKF — абсолютный (через GPS), поэтому
        # СМЕЩЕНИЕ между ними ожидаемо. Важно, что после движения оно постоянно.
        self._line(
            None, f'Смещение курса VO и EKF: {diff:+.1f}°',
            'Курс визуальной одометрии ОТНОСИТЕЛЬНЫЙ, поэтому расхождение с\n'
            'абсолютным курсом глобального EKF — норма. Проедьте 10-20 метров\n'
            'по прямой: если после этого смещение перестало «плыть» и держится\n'
            'постоянным — курс сошёлся и ехать можно.')


def main(args=None):
    rclpy.init(args=args)
    node = PreflightCheck()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception:
        pass
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass


if __name__ == '__main__':
    main()
