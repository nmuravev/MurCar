# Drone Detection System для Orange Pi 5

Система обнаружения дронов, вертолетов и самолетов в реальном времени с использованием 5 USB-камер и нейросети YOLOv8s на Orange Pi 5.

## 📋 Описание

Система обеспечивает круговой обзор неба (360°) с помощью:
- 4 камер по горизонтали (90° каждая) - фронт, тыл, лево, право
- 1 камеры направленной вверх

**Основные возможности:**
- ✅ Параллельная обработка 5 видеопотоков (60 FPS, 1080p)
- ✅ Детекция в реальном времени через YOLOv8s на NPU Orange Pi 5
- ✅ Стриминг видео с BBOX на планшет по RTSP
- ✅ Голосовые уведомления на русском языке
- ✅ Передача телеметрии через WebSocket

## 🏗️ Архитектура

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Камера 1   │     │  GStreamer       │     │  YOLOv8s        │
│  (Front)    │────▶│  Pipeline        │────▶│  Detector (NPU) │
└─────────────┘     └──────────────────┘     └─────────────────┘
                                                 │
┌─────────────┐     ┌──────────────────┐         │
│  Камера 2   │     │  GStreamer       │         │
│  (Back)     │────▶│  Pipeline        │─────────┤
└─────────────┘     └──────────────────┘         │
                                                  ▼
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Камера 3   │     │  GStreamer       │     │  Notification   │
│  (Left)     │────▶│  Pipeline        │────▶│  Manager (TTS)  │
└─────────────┘     └──────────────────┘     └─────────────────┘
                                                 │
┌─────────────┐     ┌──────────────────┐         │
│  Камера 4   │     │  GStreamer       │         │
│  (Right)    │────▶│  Pipeline        │─────────┤
└─────────────┘     └──────────────────┘         │
                                                  ▼
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Камера 5   │     │  GStreamer       │     │  Streaming      │
│  (Top)      │────▶│  Pipeline        │────▶│  Server (RTSP)  │──▶ Планшет
└─────────────┘     └──────────────────┘     └─────────────────┘
```

## 📁 Структура проекта

```
drone_detection_system/
├── main.py                 # Точка входа, оркестрация компонентов
├── core/
│   ├── detector.py         # YOLOv8s детектор (RKNN формат)
│   ├── gstreamer_pipeline.py # Генерация GStreamer пайплайнов
│   ├── streaming_server.py   # RTSP/WebSocket сервер
│   └── notification_manager.py # Голосовые уведомления (TTS)
├── models/
│   └── convert_to_rknn.py  # Скрипт конвертации YOLOv8 → RKNN
├── utils/                  # Вспомогательные утилиты
├── streams/                # Менеджеры потоков
├── datasets/               # Датасеты для обучения
│   └── drone_dataset.yaml
├── models/                 # Модели (после конвертации)
│   └── yolov8s_drone.rknn
└── audio_alerts/           # Сгенерированные аудио уведомления
```

## 🚀 Быстрый старт

### 1. Установка зависимостей на Orange Pi 5

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка системных пакетов
sudo apt install -y \
    python3-pip \
    python3-opencv \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-rtsp \
    python3-gi \
    gir1.2-gst-rtsp-server-1.0 \
    portaudio19-dev \
    rhvoice \
    alsa-utils

# Установка Python зависимостей
pip3 install \
    numpy \
    opencv-python \
    ultralytics \
    rknn-toolkit2 \
    websockets \
    torch \
    scipy
```

### 2. Конвертация модели YOLOv8s в RKNN

```bash
cd /workspace/drone_detection_system

# Подготовка датасета и конвертация модели
python3 models/convert_to_rknn.py
```

**Примечание:** Конвертация требует:
- Предварительно обученную модель YOLOv8s (.pt файл)
- Датасет для калибровки (дроны, вертолеты, самолеты)

### 3. Запуск системы

```bash
python3 main.py
```

## 📺 Подключение планшета

### RTSP поток (видео с детекцией)

1. Установите VLC или любой RTSP плеер на планшет
2. Подключитесь к: `rtsp://<IP_OrangePi>:8554/stream`
3. Видео будет отображаться с наложенными BBOX

### WebSocket (телеметрия)

Для получения данных об обнаруженных объектах:

```javascript
// Пример на JavaScript для планшета
const ws = new WebSocket('ws://<IP_OrangePi>:8765');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'detection') {
        console.log(`Detected: ${data.objects}`);
    }
};
```

## 🔧 Настройка

### Конфигурация камер

Отредактируйте `main.py`:

```python
cameras_config = [
    CameraConfig(0, CameraPosition.FRONT, (1920, 1080), 60, ""),
    CameraConfig(1, CameraPosition.BACK, (1920, 1080), 60, ""),
    CameraConfig(2, CameraPosition.LEFT, (1920, 1080), 60, ""),
    CameraConfig(3, CameraPosition.RIGHT, (1920, 1080), 60, ""),
    CameraConfig(4, CameraPosition.TOP, (1920, 1080), 60, ""),
]
```

### Параметры детекции

В `core/detector.py`:

```python
detector = YOLOv8Detector(
    model_path="models/yolov8s_drone.rknn",
    confidence_threshold=0.5,  # Порог уверенности
    iou_threshold=0.45,        # IoU для NMS
    use_npu=True               # Использовать NPU
)
```

### Голосовые уведомления

В `core/notification_manager.py`:

```python
notifier = NotificationManager(
    language='ru',
    cooldown_seconds=5.0,  # Задержка между повторами
    use_tts=True,
    tts_engine='silero'    # 'silero', 'rhvoice', 'yandex'
)
```

## 🎯 Рекомендуемые датасеты

Для обучения/дообучения модели:

1. **[DroneDetection Dataset](https://www.kaggle.com/datasets/viccombat20/drone-detection)** - Kaggle
2. **[UAV-Video Object Detection](https://github.com/UAV-Video-Detection)** - GitHub
3. **[VTOL Aircraft Dataset](https://universe.roboflow.com/)** - Roboflow
4. **[Small Plane Detection](https://github.com/VisDrone/VisDrone)** - VisDrone

## ⚡ Производительность

| Компонент | Ожидаемая производительность |
|-----------|------------------------------|
| YOLOv8s (NPU) | ~30-40 FPS на поток |
| GStreamer захват | 60 FPS (аппаратное декодирование) |
| RTSP стриминг | <100ms задержка |
| TTS генерация | ~500ms на фразу |

**Оптимизация:**
- Обработка каждого 2-3 кадра для снижения нагрузки
- Использование трекинга между кадрами
- Динамическое изменение разрешения при высокой нагрузке

## 🔍 Troubleshooting

### Камеры не определяются

```bash
# Проверка подключенных устройств
ls /dev/video*

# Тест захвата
gst-launch-1.0 v4l2src device=/dev/video0 ! videoconvert ! autovideosink
```

### Ошибки NPU

```bash
# Проверка драйверов NPU
dmesg | grep rockchip

# Перезагрузка службы NPU
sudo systemctl restart rknn-service
```

### Проблемы с RTSP

```bash
# Тест RTSP сервера
ffplay rtsp://localhost:8554/stream

# Проверка портов
netstat -tlnp | grep 8554
```

## 📝 Лицензия

MIT License

## 👥 Авторы

Система разработана для Orange Pi 5 LTS с использованием:
- YOLOv8s (Ultralytics)
- GStreamer 1.0
- RKNN Toolkit 2 (Rockchip NPU)
- Silero TTS (русский язык)
