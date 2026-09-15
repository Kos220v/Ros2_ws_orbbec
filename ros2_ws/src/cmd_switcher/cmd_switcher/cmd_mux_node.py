import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from rclpy.time import Time

class CmdMuxNode(Node):
    def __init__(self):
        super().__init__('cmd_mux_node')

        # --- НАСТРОЙКИ ПРИОРИТЕТОВ (СЕКУНДЫ) ---
        # Тайм-аут — это «сколько канал считается живым после последнего
        # сообщения». Если сообщение опоздало сильнее, мультиплексор на этом
        # же тике публикует НОЛЬ, привод сбрасывает скважность, а через
        # 20–50 мс приходит следующее сообщение и скважность снова
        # выставляется — робот ДЁРГАЕТСЯ.
        #
        # Пульт (elrs_receiver) публикует 20 Гц (каждые 50 мс). Старый порог
        # 0.2 с оставлял запас всего в ~3 пропущенных периода: на Pi 4 под
        # полным стеком (камера + rtabmap + Nav2) планировщик Linux легко
        # задерживает Python-узел на 100–200 мс, и запас исчерпывался.
        # 0.5 с — по-прежнему безопасно (при потере пульта робот
        # останавливается за полсекунды; сам elrs_receiver перестаёт
        # публиковать через timeout_sec), но пропуски отдельных тиков уже
        # не превращаются в удары по трансмиссии.
        self.declare_parameter('timeout_manual', 0.5)
        self.declare_parameter('timeout_app_manual', 0.5)
        self.declare_parameter('timeout_home', 0.5)
        self.declare_parameter('timeout_auto', 2.0)
        # Частота выходного /cmd_vel. 20 Гц достаточно: пульт публикует 20 Гц,
        # Nav2 (velocity_smoother) — 20 Гц; привод kolesa_control сам
        # перевыставляет последнюю команду на своей частоте.
        self.declare_parameter('publish_rate', 20.0)

        self.timeout_manual = float(self.get_parameter('timeout_manual').value)
        self.timeout_app_manual = float(self.get_parameter('timeout_app_manual').value)
        self.timeout_home = float(self.get_parameter('timeout_home').value)
        self.timeout_auto = float(self.get_parameter('timeout_auto').value)
        publish_rate = float(self.get_parameter('publish_rate').value)
        if publish_rate <= 0.0:
            publish_rate = 20.0
        # ---------------------------------------

        # Хранилище последних сообщений: (msg, timestamp)
        self.last_manual = None
        self.last_app_manual = None
        self.last_home = None
        self.last_auto = None

        # Подписчики на разные источники
        self.sub_manual = self.create_subscription(Twist, '/cmd_vel/manual', self.cb_manual, 10)
        # ДОБАВЛЕНО: канал ручного управления из desktop-приложения (клавиатура/джойстик в UI),
        # публикуется через rosbridge. Приоритет НИЖЕ физического пульта — если оператор
        # одновременно держит в руках RC-пульт, он всегда может перехватить управление.
        self.sub_app_manual = self.create_subscription(Twist, '/cmd_vel/app_manual', self.cb_app_manual, 10)
        self.sub_home = self.create_subscription(Twist, '/cmd_vel/home', self.cb_home, 10)
        self.sub_auto = self.create_subscription(Twist, '/cmd_vel/auto', self.cb_auto, 10)

        # Паблишер в драйвер робота
        self.pub_final = self.create_publisher(Twist, '/cmd_vel', 10)

        # Таймер проверки/публикации (по умолчанию 20 Гц)
        self.timer = self.create_timer(1.0 / publish_rate, self.publish_logic)

        self.get_logger().info(
            "Cmd Mux Node started. Listening for manual, app_manual, home, auto... "
            f"(publish {publish_rate:.0f} Hz; timeouts manual={self.timeout_manual:.2f}s "
            f"app={self.timeout_app_manual:.2f}s home={self.timeout_home:.2f}s "
            f"auto={self.timeout_auto:.2f}s)"
        )

    def cb_manual(self, msg):
        self.last_manual = (msg, self.get_clock().now())

    def cb_app_manual(self, msg):
        self.last_app_manual = (msg, self.get_clock().now())

    def cb_home(self, msg):
        self.last_home = (msg, self.get_clock().now())

    def cb_auto(self, msg):
        self.last_auto = (msg, self.get_clock().now())

    def publish_logic(self):
        now = self.get_clock().now()
        final_cmd = Twist() # По умолчанию стоп (все нули)

        # 1. ПРОВЕРКА ФИЗИЧЕСКОГО ПУЛЬТА (Высший приоритет)
        if self.last_manual:
            msg, time_received = self.last_manual
            age_sec = (now - time_received).nanoseconds / 1e9
            if age_sec < self.timeout_manual:
                self.pub_final.publish(msg)
                return

        # 2. ПРОВЕРКА РУЧНОГО УПРАВЛЕНИЯ ИЗ ПРИЛОЖЕНИЯ (ДОБАВЛЕНО)
        if self.last_app_manual:
            msg, time_received = self.last_app_manual
            age_sec = (now - time_received).nanoseconds / 1e9
            if age_sec < self.timeout_app_manual:
                self.pub_final.publish(msg)
                return

        # 3. ПРОВЕРКА РЕЖИМА "ДОМОЙ" (Средний приоритет)
        if self.last_home:
            msg, time_received = self.last_home
            age_sec = (now - time_received).nanoseconds / 1e9
            if age_sec < self.timeout_home:
                self.pub_final.publish(msg)
                return

        # 4. ПРОВЕРКА АВТОПИЛОТА (Низший приоритет)
        if self.last_auto:
            msg, time_received = self.last_auto
            age_sec = (now - time_received).nanoseconds / 1e9
            if age_sec < self.timeout_auto:
                self.pub_final.publish(msg)
                return

        # Если никто не прислал свежих данных -> Стоп
        self.pub_final.publish(final_cmd)

def main(args=None):
    rclpy.init(args=args)
    node = CmdMuxNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
