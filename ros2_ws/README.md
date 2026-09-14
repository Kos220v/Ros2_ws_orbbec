# ros2_ws

Разработка робота на ROS 2 Jazzy.

## Подключение STM32 IMU к Raspberry Pi

IMU подключается через внешний USB-UART преобразователь. Перед запуском
проекта необходимо настроить UART, права пользователя и постоянный адрес
`/dev/imu_stm32` по инструкции:

[`src/imu_stm32_bridge/docs/USB_UART_RASPBERRY_PI.md`](src/imu_stm32_bridge/docs/USB_UART_RASPBERRY_PI.md)

Инструкция по запуску робота по заранее записанному GPS-маршруту:

[`src/robot_navigation/docs/RUN_PREPLANNED_ROUTE_RASPBERRY_PI.md`](src/robot_navigation/docs/RUN_PREPLANNED_ROUTE_RASPBERRY_PI.md)
