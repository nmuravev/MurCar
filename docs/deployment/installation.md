# 🚀 Пошаговая установка системы

## Предварительные требования

Перед началом установки убедитесь, что:
- ✅ Orange Pi 5 настроен (см. [orange_pi_setup.md](../hardware/orange_pi_setup.md))
- ✅ Камеры подключены и определены системой
- ✅ Есть подключение к интернету
- ✅ Создан пользователь `droneops` с правами sudo

## Шаг 1: Подготовка окружения

### 1.1 Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### 1.2 Установка системных зависимостей
```bash
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    cmake \
    build-essential \
    libusb-1.0-0-dev \
    libgtk-3-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    gfortran \
    openexr \
    libatlas-base-dev \
    wget \
    curl \
    htop \
    net-tools \
    iputils-ping
```

### 1.3 Установка GStreamer
```bash
sudo apt install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-alsa \
    gstreamer1.0-gl \
    gstreamer1.0-gtk3 \
    gstreamer1.0-jack \
    gstreamer1.0-rtsp \
    gstreamer1.0-vaapi
```

Проверка установки:
```bash
gst-launch-1.0 --version
```

## Шаг 2: Установка RKNN Toolkit

### 2.1 Клонирование репозитория
```bash
cd ~
git clone https://github.com/airockchip/rknn-toolkit2.git
cd rknn-toolkit2
```

### 2.2 Установка Python зависимостей
```bash
cd runtime/python3

# Создание виртуального окружения (рекомендуется)
python3 -m venv venv
source venv/bin/activate

# Установка wheel пакета
pip install rknn_toolkit2-*.whl

# Проверка установки
python3 -c "from rknn.api import RKNN; print('RKNN OK')"
```

### 2.3 Установка ONNX (для конвертации моделей)
```bash
pip install onnx==1.13.0
pip install onnxruntime==1.14.0
```

## Шаг 3: Установка приложения детекции

### 3.1 Клонирование репозитория проекта
```bash
cd /home/droneops
git clone <your-repo-url> drone_detection_system
cd drone_detection_system
```

### 3.2 Создание виртуального окружения
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3.3 Установка зависимостей Python
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.4 Проверка установленных пакетов
```bash
pip list | grep -E "ultralytics|rknn|opencv|gstreamer"
```

## Шаг 4: Конвертация модели YOLOv8 в RKNN

### 4.1 Скачивание предобученной модели
```bash
cd models

# Скачивание YOLOv8s
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt

# Или используйте свою модель
# wget <your-model-url>
```

### 4.2 Конвертация в ONNX
```bash
pip install ultralytics

python3 -c "
from ultralytics import YOLO
model = YOLO('yolov8s.pt')
model.export(format='onnx', imgsz=640)
"
```

### 4.3 Конвертация в RKNN
```bash
cd /home/droneops/drone_detection_system/models
python3 convert_to_rknn.py
```

Содержимое `convert_to_rknn.py`:
```python
#!/usr/bin/env python3
"""
Конвертация YOLOv8 ONNX модели в формат RKNN для NPU Orange Pi 5
"""

from rknn.api import RKNN
import os

# Пути
ONNX_MODEL = 'yolov8s.onnx'
RKNN_MODEL = 'yolov8s.rknn'

# Проверка наличия файла
if not os.path.exists(ONNX_MODEL):
    print(f"Ошибка: Файл {ONNX_MODEL} не найден")
    exit(1)

print("Инициализация RKNN...")
rknn = RKNN(verbose=True)

# Конфигурация
print("Настройка конфигурации...")
rknn.config(
    target_platform='rk3588',
    optimization_level=3,
    do_quantization=True,
    dataset='./dataset.txt'  # файл со списком изображений для калибровки
)

# Загрузка модели
print(f"Загрузка модели из {ONNX_MODEL}...")
ret = rknn.load_onnx(model=ONNX_MODEL)
if ret != 0:
    print("Ошибка загрузки модели!")
    exit(1)

# Билд модели
print("Билд модели...")
ret = rknn.build(do_convert=True, do_quantization=True, target_platform='rk3588')
if ret != 0:
    print("Ошибка билда модели!")
    exit(1)

# Экспорт
print(f"Экспорт модели в {RKNN_MODEL}...")
ret = rknn.export_rknn(RKNN_MODEL)
if ret != 0:
    print("Ошибка экспорта модели!")
    exit(1)

print(f"✅ Модель успешно сконвертирована: {RKNN_MODEL}")
print(f"Размер: {os.path.getsize(RKNN_MODEL) / 1024 / 1024:.2f} MB")
```

### 4.4 Файл калибровки dataset.txt
Создайте файл `dataset.txt` со списком изображений для квантования:
```bash
cat > dataset.txt << EOF
calib_images/img1.jpg
calib_images/img2.jpg
calib_images/img3.jpg
calib_images/img4.jpg
calib_images/img5.jpg
EOF
```

Скачайте 10-20 изображений с дронами в папку `calib_images/`.

## Шаг 5: Настройка конфигурации

### 5.1 Создание конфигурационного файла
```bash
cd /home/droneops/drone_detection_system
cp config.example.yaml config.yaml
```

### 5.2 Редактирование config.yaml
```yaml
# config.yaml

# Настройки камер
cameras:
  - id: cam_0
    device: /dev/video0
    name: Front
    direction: front
    resolution: [1920, 1080]
    fps: 60
    enabled: true
    
  - id: cam_1
    device: /dev/video1
    name: Right
    direction: right
    resolution: [1920, 1080]
    fps: 60
    enabled: true
    
  - id: cam_2
    device: /dev/video2
    name: Left
    direction: left
    resolution: [1920, 1080]
    fps: 60
    enabled: true
    
  - id: cam_3
    device: /dev/video3
    name: Back
    direction: back
    resolution: [1920, 1080]
    fps: 60
    enabled: true
    
  - id: cam_4
    device: /dev/video4
    name: Up
    direction: up
    resolution: [1920, 1080]
    fps: 60
    enabled: true

# Настройки детекции
detection:
  model_path: models/yolov8s.rknn
  confidence_threshold: 0.5
  iou_threshold: 0.45
  classes:
    - drone
    - vtol
    - airplane
    - helicopter
  frame_skip: 2  # Пропускать каждый 2-й кадр для производительности
  npu_threads: 5  # Количество потоков NPU (по одному на камеру)

# Настройки стриминга
streaming:
  enabled: true
  rtsp_port: 8554
  codec: h264
  bitrate: 4000  # kbps
  keyframe_interval: 60

# Настройки уведомлений
notifications:
  voice_enabled: true
  voice_language: ru
  min_confidence: 0.5
  cooldown_seconds: 10
  audio_output: default

# Настройки API
api:
  host: 0.0.0.0
  port: 8080
  auth_token: your_secure_token_here

# Логирование
logging:
  level: INFO
  file: logs/detection.log
  max_size_mb: 100
  backup_count: 5
```

## Шаг 6: Тестовый запуск

### 6.1 Проверка камер
```bash
source venv/bin/activate

# Тест одной камеры
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
if ret:
    print('✅ Камера работает')
    cv2.imwrite('test_frame.jpg', frame)
else:
    print('❌ Ошибка камеры')
cap.release()
"
```

### 6.2 Тест GStreamer пайплайна
```bash
gst-launch-1.0 v4l2src device=/dev/video0 ! \
    video/x-raw,width=1920,height=1080,framerate=60/1 ! \
    videoconvert ! \
    ximagesink
```

### 6.3 Тест модели RKNN
```bash
python3 -c "
from rknn.api import RKNN
rknn = RKNN()
rknn.load_rknn('models/yolov8s.rknn')
print('✅ Модель загружена успешно')
"
```

### 6.4 Запуск основной системы
```bash
cd /home/droneops/drone_detection_system
python3 main.py --config config.yaml
```

## Шаг 7: Настройка автозапуска

### 7.1 Создание systemd сервиса
```bash
sudo nano /etc/systemd/system/drone-detection.service
```

Содержимое:
```ini
[Unit]
Description=Drone Detection System
After=network.target multi-user.target
Wants=network.target

[Service]
Type=simple
User=droneops
Group=droneops
WorkingDirectory=/home/droneops/drone_detection_system
Environment="PATH=/home/droneops/drone_detection_system/venv/bin"
ExecStart=/home/droneops/drone_detection_system/venv/bin/python3 main.py --config config.yaml
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=drone-detection

# Limits
LimitNOFILE=65535
Nice=-5

[Install]
WantedBy=multi-user.target
```

### 7.2 Включение сервиса
```bash
sudo systemctl daemon-reload
sudo systemctl enable drone-detection.service
sudo systemctl start drone-detection.service
```

### 7.3 Проверка статуса
```bash
sudo systemctl status drone-detection.service
```

### 7.4 Просмотр логов
```bash
sudo journalctl -u drone-detection.service -f
```

## Шаг 8: Проверка работы

### 8.1 Проверка REST API
```bash
curl http://localhost:8080/api/v1/system/status
```

### 8.2 Проверка WebSocket
Подключитесь через браузер или инструмент:
```
ws://localhost:8080/ws?token=your_token
```

### 8.3 Проверка RTSP потока
```bash
ffplay rtsp://localhost:8554/stream0
```

## Шаг 9: Мониторинг и отладка

### 9.1 Скрипт проверки здоровья системы
```bash
#!/bin/bash
# health_check.sh

echo "=== Drone Detection System Health Check ==="
echo ""

# Статус сервиса
echo "Сервис:"
sudo systemctl is-active drone-detection.service

# Использование ресурсов
echo ""
echo "Ресурсы:"
top -bn1 | grep "Cpu(s)" | awk '{print "CPU: " $2 "%"}'
free -h | grep Mem | awk '{print "RAM: " $3 "/" $2}'

# Камеры
echo ""
echo "Камеры:"
ls /dev/video* | wc -l | xargs echo "Доступно камер:"

# NPU
echo ""
echo "NPU:"
cat /sys/class/devfreq/fdabf000.npu/load 2>/dev/null || echo "N/A"

# Логи
echo ""
echo "Последние ошибки:"
sudo journalctl -u drone-detection.service -n 5 --no-pager | grep -i error || echo "Ошибок нет"
```

### 9.2 Настройка логирования
Логи находятся в `/home/droneops/drone_detection_system/logs/`

## Решение проблем

### Ошибка: "No module named 'rknn'"
```bash
source venv/bin/activate
pip install -e ~/rknn-toolkit2/runtime/python3
```

### Ошибка: "Cannot open camera"
```bash
# Проверка прав
ls -la /dev/video*

# Добавление пользователя в группу video
sudo usermod -aG video droneops
sudo reboot
```

### Ошибка: "NPU not found"
```bash
# Проверка драйверов
dmesg | grep -i rockchip

# Перезагрузка службы NPU
sudo systemctl restart rockchip-npu
```

### Высокая задержка видео
- Уменьшите разрешение до 720p
- Включите аппаратное кодирование H.264
- Увеличьте `frame_skip` в конфиге

## Следующие шаги

После успешной установки:
1. Настройте [калибровку камер](../hardware/camera_configuration.md#калибровка-камер)
2. Изучите [API документацию](../api/rest_api.md)
3. Настройте интеграцию с планшетом
4. Проведите полевые тесты
