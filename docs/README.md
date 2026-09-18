# 📚 Полная документация системы обнаружения дронов

## 🗂️ Структура документации

Этот каталог содержит исчерпывающую документацию по всем компонентам системы обнаружения дронов на базе Orange Pi 5.

```
docs/
├── README.md                    # Этот файл - навигатор по документации
├── api/                         # Документация API
│   ├── rest_api.md             # REST API для управления системой
│   ├── websocket_api.md        # WebSocket API для стриминга и телеметрии
│   └── events_api.md           # API событий детекции
├── hardware/                    # Аппаратная часть
│   ├── orange_pi_setup.md      # Настройка Orange Pi 5
│   ├── camera_configuration.md # Конфигурация камер
│   ├── usb_requirements.md     # Требования к USB камерам
│   └── network_setup.md        # Настройка сети
├── deployment/                  # Развертывание
│   ├── installation.md         # Пошаговая установка
│   ├── configuration.md        # Конфигурационные файлы
│   ├── rknn_model_setup.md     # Настройка RKNN модели
│   └── troubleshooting.md      # Решение проблем
└── data_flow/                   # Потоки данных
    ├── gstreamer_pipelines.md  # GStreamer пайплайны
    ├── detection_pipeline.md   # Пайплайн детекции
    ├── streaming_protocol.md   # Протокол стриминга
    └── notification_system.md  # Система уведомлений
```

## 📖 Краткое описание разделов

### 🔌 API (Application Programming Interface)

- **REST API**: Управление системой, настройка параметров, получение статуса
- **WebSocket API**: Реальное время - стриминг видео, телеметрия, события детекции
- **Events API**: Обработка событий обнаружения, логирование, интеграция с внешними системами

### 🖥️ Hardware (Аппаратное обеспечение)

- **Orange Pi Setup**: Установка ОС, драйверов, настройка NPU
- **Camera Configuration**: Выбор камер, углы обзора, разрешение, FPS
- **USB Requirements**: Пропускная способность, требования к контроллерам
- **Network Setup**: Wi-Fi, Ethernet, настройка маршрутизации

### 🚀 Deployment (Развертывание)

- **Installation**: Пошаговая инструкция установки всех компонентов
- **Configuration**: Конфигурационные файлы, переменные окружения
- **RKNN Model Setup**: Конвертация YOLOv8 в формат RKNN для NPU
- **Troubleshooting**: Частые проблемы и их решения

### 📊 Data Flow (Потоки данных)

- **GStreamer Pipelines**: Построение пайплайнов захвата видео
- **Detection Pipeline**: Обработка кадров нейросетью
- **Streaming Protocol**: Протокол передачи видео на планшет
- **Notification System**: Генерация голосовых уведомлений

## 🎯 Быстрый старт

1. Изучите [Аппаратные требования](hardware/orange_pi_setup.md)
2. Настройте [ОС и драйверы](hardware/orange_pi_setup.md)
3. Установите [Программное обеспечение](deployment/installation.md)
4. Сконфигурируйте [Камеры](hardware/camera_configuration.md)
5. Запустите [Систему](deployment/installation.md#запуск-системы)

## 📞 Контакты и поддержка

Для вопросов по документации создавайте Issues в репозитории.
