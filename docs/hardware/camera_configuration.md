# 📷 Конфигурация камер

## Обзор системы

Система использует **5 USB камер** для обеспечения кругового обзора:
- **4 камеры по горизонтали** (90° каждая) - перед, зад, лево, право
- **1 камера вверх** - обзор неба

## Требования к камерам

### Технические характеристики

| Параметр | Минимум | Рекомендуется | Идеал |
|----------|---------|---------------|-------|
| **Разрешение** | 720p | 1080p | 4K |
| **FPS** | 30 | 60 | 60+ |
| **Угол обзора** | 80° | 90° | 100-110° |
| **Интерфейс** | USB 2.0 | USB 3.0 | USB 3.0/3.1 |
| **Кодирование** | MJPEG | H.264 | H.264/H.265 |
| **Фокус** | Фиксированный | Регулируемый | Motorized |

### Рекомендуемые модели камер

#### Вариант 1: Бюджетный (~$25-35 за камеру)
- **Logitech C920/C922** - 1080p@30fps, 78° FOV
- **Microsoft LifeCam HD-3000** - 720p@30fps, 68° FOV
- **AUSDOM USB Camera** - 1080p@30fps, 90° FOV

#### Вариант 2: Оптимальный (~$40-60 за камеру)
- **Logitech Brio 4K** - 4K@30fps, 90° FOV (дорого но отлично)
- **Razer Kiyo Pro** - 1080p@60fps, 90° FOV
- **Dell UltraSharp Webcam** - 1080p@60fps, 90° FOV

#### Вариант 3: Профессиональный (~$70-100 за камеру)
- **ELP USB Camera Module** - 1080p@60fps, 100-140° FOV (wide angle)
- **Arducam USB Camera** - Разные модули с разными углами
- **See3CAM_130** - 1080p@60fps, глобальный затвор

### Спецификации для нашей задачи

Для детекции дронов критичны:
1. **Высокий FPS** (60+) - для отслеживания быстрых объектов
2. **Широкий угол** (90-110°) - для максимального покрытия
3. **Низкая задержка** - UVC совместимость обязательна
4. **Хорошая светочувствительность** - работа в сумерках

## Расположение камер

### Схема монтажа на автомобиле

```
                    [Камера 2: Вперед]
                         ↑
                         |
        [Камера 0: ←] ---+--- [Камера 1: →]
            Лево         |        Право
                         |
                    [Камера 3: Назад]
                         ↓
                    
                    [Камера 4: ↑ Вверх]
```

### Углы установки

| Камера | ID | Направление | Угол горизонтальный | Угол вертикальный |
|--------|-----|-------------|---------------------|-------------------|
| Передняя | cam_0 | Forward | 0° | +10° (вверх) |
| Правая | cam_1 | Right | +90° | 0° |
| Левая | cam_2 | Left | -90° | 0° |
| Задняя | cam_3 | Backward | 180° | +10° (вверх) |
| Верхняя | cam_4 | Up | N/A | +90° (вертикально) |

### Рекомендации по монтажу

1. **Высота установки**: Минимум 1.5-2м от земли
2. **Защита от вибраций**: Используйте демпферы
3. **Влагозащита**: IP65+ для уличных условий
4. **Обзор без препятствий**: Избегайте закрытия камер частями авто

## Подключение к Orange Pi

### Схема подключения USB

```
Orange Pi 5
    ├── USB 3.0 Port 1 ──┬── Камера 0 (Перед)
    │                     └── Камера 1 (Право)
    │
    ├── USB 3.0 Port 2 ──┬── Камера 2 (Лево)
    │                     └── Камера 3 (Зад)
    │
    └── USB 3.0 Port 3 ──── Камера 4 (Верх)
```

**Важно**: Используйте USB Hub с внешним питанием!

### Требования к питанию

Каждая камера потребляет ~500mA @ 5V:
- 5 камер × 500mA = 2.5A минимум
- Рекомендуется USB Hub на 3-4A с внешним блоком питания

### Проверка подключенных камер

```bash
# Список всех USB устройств
lsusb

# Ожидаемый вывод:
# Bus 002 Device 002: ID 046d:082d Logitech, Inc. HD Pro Webcam C920
# Bus 002 Device 003: ID 046d:082d Logitech, Inc. HD Pro Webcam C920
# Bus 002 Device 004: ID 046d:082d Logitech, Inc. HD Pro Webcam C920
# Bus 002 Device 005: ID 046d:082d Logitech, Inc. HD Pro Webcam C920
# Bus 002 Device 006: ID 046d:082d Logitech, Inc. HD Pro Webcam C920

# Проверка видеоустройств
ls -la /dev/video*

# Ожидаемый вывод:
# crw-rw----+ 1 root video 81, 0 ... /dev/video0
# crw-rw----+ 1 root video 81, 1 ... /dev/video1
# crw-rw----+ 1 root video 81, 2 ... /dev/video2
# crw-rw----+ 1 root video 81, 3 ... /dev/video3
# crw-rw----+ 1 root video 81, 4 ... /dev/video4
```

### Определение соответствия camera_id → /dev/videoX

```bash
#!/bin/bash
# save as: identify_cameras.sh

for dev in /dev/video[0-9]; do
    echo "=== $dev ==="
    v4l2-ctl --device=$dev --info
    echo ""
done
```

Или используйте udev правила для постоянных имен:

```bash
sudo nano /etc/udev/rules.d/70-camera-persistent-names.rules
```

Добавьте (замените серийные номера на ваши):
```
SUBSYSTEM=="video4linux", ATTRS{serial}=="12345678", SYMLINK+="camera_front"
SUBSYSTEM=="video4linux", ATTRS{serial}=="23456789", SYMLINK+="camera_right"
SUBSYSTEM=="video4linux", ATTRS{serial}=="34567890", SYMLINK+="camera_left"
SUBSYSTEM=="video4linux", ATTRS{serial}=="45678901", SYMLINK+="camera_back"
SUBSYSTEM=="video4linux", ATTRS{serial}=="56789012", SYMLINK+="camera_up"
```

Применение:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Настройка параметров камер

### Проверка поддерживаемых форматов

```bash
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

### Установка разрешения и FPS

```bash
# Для каждой камеры установите 1080p@60fps
v4l2-ctl --device=/dev/video0 \
    --set-fmt-video=width=1920,height=1080,pixelformat=MJPG \
    --set-parm=60
```

### GStreamer тестирование

```bash
# Тест одной камеры
gst-launch-1.0 v4l2src device=/dev/video0 ! \
    video/x-raw,width=1920,height=1080,framerate=60/1 ! \
    ximagesink

# Тест с аппаратным кодированием
gst-launch-1.0 v4l2src device=/dev/video0 ! \
    video/x-raw,width=1920,height=1080,framerate=60/1 ! \
    v4l2h264enc ! \
    h264parse ! \
    rtph264pay config-interval=1 pt=96 ! \
    udpsink host=127.0.0.1 port=5000
```

## Калибровка камер

### Внутренняя калибровка (intrinsics)

Для точной детекции необходима калибровка каждой камеры:

```python
# calibration.py
import cv2
import numpy as np

# Параметры для шахматной доски 9x6
CHESSBOARD = (9, 6)
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

objp = np.zeros((CHESSBOARD[0] * CHESSBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHESSBOARD[0], 0:CHESSBOARD[1]].T.reshape(-1, 2)

objpoints = []  # 3d points in real world space
imgpoints = []  # 2d points in image plane

cap = cv2.VideoCapture(0)

print("Покажите шахматную доску камере...")

while True:
    ret, img = cap.read()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    ret, corners = cv2.findChessboardCorners(gray, CHESSBOARD, None)
    
    if ret:
        objpoints.append(objp)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)
        
        cv2.drawChessboardCorners(img, CHESSBOARD, corners2, ret)
        cv2.imshow('img', img)
        cv2.waitKey(500)
        print(f"Найдено углов: {len(imgpoints)}")
        
        if len(imgpoints) >= 20:
            break

cap.release()
cv2.destroyAllWindows()

# Калибровка
ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
    objpoints, imgpoints, gray.shape[::-1], None, None
)

print(f"RMSE: {ret}")
print(f"Camera matrix:\n{mtx}")
print(f"Distortion coeffs: {dist}")

# Сохранение параметров
np.savez('camera_0_calib.npz', mtx=mtx, dist=dist)
```

### Внешняя калибровка (extrinsics)

Для определения взаимного положения камер используйте метод с известными точками в пространстве.

## Оптимизация пропускной способности

### Проблема bandwidth USB 3.0

Теоретическая пропускная способность USB 3.0:
- 5 Gbps = 625 MB/s
- Реальная: ~400-450 MB/s

Расчет для 5 камер 1080p@60fps:
- Несжатое видео: 1920×1080×3 bytes × 60 fps = 373 MB/s на камеру
- 5 камер: 1865 MB/s ❌ (превышает лимит)

**Решение**: Использовать камеры с аппаратным кодированием H.264

С H.264 @ 1080p60:
- Сжатый поток: ~8-12 Mbps = 1-1.5 MB/s на камеру
- 5 камер: 5-7.5 MB/s ✅ (в пределах лимита)

### Настройка MJPEG vs H.264

Если камеры поддерживают H.264:
```bash
v4l2-ctl --device=/dev/video0 --set-fmt-video=width=1920,height=1080,pixelformat=H264
```

Проверка доступных кодеков:
```bash
v4l2-ctl --device=/dev/video0 --list-formats-ext | grep -A 20 "H264\|MJPG"
```

## Мониторинг состояния камер

### Скрипт проверки

```bash
#!/bin/bash
# check_cameras.sh

echo "=== Camera Status Check ==="

for i in {0..4}; do
    dev="/dev/video$i"
    if [ -e "$dev" ]; then
        echo -n "Camera $i ($dev): "
        fps=$(v4l2-ctl --device=$dev --get-parm | grep "Frames per second" | awk '{print $NF}')
        fmt=$(v4l2-ctl --device=$dev --get-fmt-video | grep "Width" | awk '{print $2, $4, $6}')
        echo "FPS: $fps, Format: $fmt"
    else
        echo "Camera $i: NOT FOUND"
    fi
done

echo ""
echo "USB Bandwidth Usage:"
cat /sys/kernel/debug/usb/devices | grep -A 5 "Bus.*Dev" | grep -E "MxPS|Avail"
```

### Автоматическое восстановление

Создайте systemd сервис для мониторинга:

```ini
# /etc/systemd/system/camera-monitor.service
[Unit]
Description=Camera Health Monitor
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/camera-monitor.py
Restart=always
User=droneops

[Install]
WantedBy=multi-user.target
```

## Следующие шаги

После настройки камер:
1. Протестируйте каждую камеру отдельно
2. Проведите калибровку
3. Настройте GStreamer пайплайны
4. Перейдите к [установке ПО](../../deployment/installation.md)
