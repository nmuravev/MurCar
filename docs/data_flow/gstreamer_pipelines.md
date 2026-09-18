# 📊 Потоки данных системы

## Общая архитектура

Система обрабатывает видеопотоки от 5 камер параллельно, используя конвейерную обработку:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   Камеры    │────▶│  GStreamer   │────▶│   YOLOv8    │────▶│  Стриминг/   │
│ (5 потоков) │     │  Pipeline    │     │   RKNN      │     │  Уведомления │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐     ┌──────────────┐
                    │  Декодиров-  │     │  Трекинг +   │
                    │  ание H.264  │     │  Телеметрия  │
                    └──────────────┘     └──────────────┘
```

## GStreamer пайплайны

### Архитектура пайплайна для одной камеры

```
v4l2src → h264parse → v4l2h264dec → videoconvert → appsink → NPU
                                                    ↓
                                              RTSP Server
```

### Полный пайплайн для всех 5 камер

Каждая камера имеет свой независимый пайплайн:

#### Пайплайн камеры 0 (Передняя)
```python
pipeline_front = """
v4l2src device=/dev/video0 !
    video/x-h264,width=1920,height=1080,framerate=60/1 !
    h264parse !
    v4l2h264dec !
    video/x-raw,format=NV12 !
    videoconvert !
    video/x-raw,format=RGB !
    appsink name=sink_front emit-signals=true max-buffers=1 drop=true
"""
```

#### Пайплайн камеры 1 (Правая)
```python
pipeline_right = """
v4l2src device=/dev/video1 !
    video/x-h264,width=1920,height=1080,framerate=60/1 !
    h264parse !
    v4l2h264dec !
    video/x-raw,format=NV12 !
    videoconvert !
    video/x-raw,format=RGB !
    appsink name=sink_right emit-signals=true max-buffers=1 drop=true
"""
```

#### Пайплайн камеры 2 (Левая)
```python
pipeline_left = """
v4l2src device=/dev/video2 !
    video/x-h264,width=1920,height=1080,framerate=60/1 !
    h264parse !
    v4l2h264dec !
    video/x-raw,format=NV12 !
    videoconvert !
    video/x-raw,format=RGB !
    appsink name=sink_left emit-signals=true max-buffers=1 drop=true
"""
```

#### Пайплайн камеры 3 (Задняя)
```python
pipeline_back = """
v4l2src device=/dev/video3 !
    video/x-h264,width=1920,height=1080,framerate=60/1 !
    h264parse !
    v4l2h264dec !
    video/x-raw,format=NV12 !
    videoconvert !
    video/x-raw,format=RGB !
    appsink name=sink_back emit-signals=true max-buffers=1 drop=true
"""
```

#### Пайплайн камеры 4 (Верхняя)
```python
pipeline_up = """
v4l2src device=/dev/video4 !
    video/x-h264,width=1920,height=1080,framerate=60/1 !
    h264parse !
    v4l2h264dec !
    video/x-raw,format=NV12 !
    videoconvert !
    video/x-raw,format=RGB !
    appsink name=sink_up emit-signals=true max-buffers=1 drop=true
"""
```

### Оптимизация пайплайнов

#### С аппаратным кодированием для стриминга
```python
pipeline_with_rtsp = """
v4l2src device=/dev/video0 !
    video/x-h264,width=1920,height=1080,framerate=60/1 !
    h264parse !
    queue max-size-buffers=3 leaky=downstream !
    v4l2h264dec !
    video/x-raw,format=NV12 !
    queue max-size-buffers=3 leaky=downstream !
    v4l2h264enc !
    h264parse !
    rtph264pay config-interval=1 pt=96 !
    rtspclientsink location=rtsp://localhost:8554/stream0
"""
```

#### Для детекции с пропуском кадров
```python
pipeline_detection = """
v4l2src device=/dev/video0 !
    video/x-h264,width=1920,height=1080,framerate=60/1 !
    h264parse !
    v4l2h264dec !
    video/x-raw,format=NV12 !
    videorate !
    video/x-raw,framerate=20/1 !
    videoconvert !
    video/x-raw,format=RGB,width=640,height=640 !
    appsink name=sink_front emit-signals=true max-buffers=1 drop=true
"""
```

## Пайплайн детекции

### Обработка кадра в NPU

```python
# 1. Получение кадра из GStreamer
frame = appsink.pull()  # numpy array shape=(640, 640, 3)

# 2. Предобработка
frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
frame_normalized = frame_rgb / 255.0
frame_expanded = np.expand_dims(frame_normalized, axis=0)

# 3. Инференс на NPU
outputs = rknn.inference(inputs=[frame_expanded])

# 4. Постобработка
boxes = decode_outputs(outputs, confidence_threshold=0.5)

# 5. Фильтрация по классам
detections = filter_classes(boxes, classes=['drone', 'vtol', 'airplane', 'helicopter'])
```

### Параллельная обработка 5 потоков

```python
import threading
from concurrent.futures import ThreadPoolExecutor

class ParallelDetector:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.detectors = [RKNNDetector(i) for i in range(5)]
    
    def process_all_cameras(self, frames):
        """
        frames: dict {camera_id: frame}
        """
        futures = {
            self.executor.submit(self.detectors[i].detect, frame): i
            for i, (cam_id, frame) in enumerate(frames.items())
        }
        
        results = {}
        for future in as_completed(futures):
            cam_idx = futures[future]
            results[f"cam_{cam_idx}"] = future.result()
        
        return results
```

## Протокол стриминга

### RTSP сервер

Камера транслирует поток по адресу:
```
rtsp://<orange_pi_ip>:8554/stream{0-4}
```

Где:
- `stream0` - Передняя камера
- `stream1` - Правая камера
- `stream2` - Левая камера
- `stream3` - Задняя камера
- `stream4` - Верхняя камера

### Формат потока

- **Кодек**: H.264 (Baseline Profile)
- **Разрешение**: 1920×1080 @ 30fps (или 1280×720 @ 60fps)
- **Битрейт**: 4000 kbps (переменный VBR)
- **Keyframe интервал**: 60 кадров (2 секунды при 30fps)
- **Аудио**: Отсутствует

### Наложение BBOX на видео

Bounding boxes накладываются поверх видеопотока перед отправкой:

```python
def draw_detections(frame, detections):
    """
    Рисует bounding boxes на кадре
    """
    for det in detections:
        x1, y1, x2, y2 = map(int, det['bbox'])
        class_name = det['class']
        confidence = det['confidence']
        
        # Выбор цвета по классу
        colors = {
            'drone': (0, 0, 255),      # Красный (BGR)
            'vtol': (0, 255, 255),     # Желтый
            'airplane': (255, 0, 0),   # Синий
            'helicopter': (0, 255, 0)  # Зеленый
        }
        color = colors.get(class_name, (255, 255, 255))
        
        # Рисуем рамку
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # Рисуем подпись
        label = f"{class_name} {confidence:.2f}"
        cv2.putText(frame, label, (x1, y1 - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    return frame
```

## Система уведомлений

### Генерация голосовых сообщений

```python
class NotificationManager:
    def __init__(self):
        self.cooldowns = {}
        self.cooldown_seconds = 10
        
    def generate_voice_message(self, detection):
        """
        Генерирует текстовое сообщение для озвучивания
        """
        direction_map = {
            'front': 'спереди',
            'back': 'сзади',
            'left': 'слева',
            'right': 'справа',
            'up': 'над головой'
        }
        
        class_map = {
            'drone': 'дрон',
            'vtol': 'БПЛА вертикального взлета',
            'airplane': 'самолет',
            'helicopter': 'вертолет'
        }
        
        direction = direction_map.get(detection['direction'], '')
        obj_class = class_map.get(detection['class'], 'объект')
        
        message = f"Внимание! {obj_class} обнаружен {direction}!"
        
        return message
    
    def should_notify(self, camera_id, detection):
        """
        Проверяет, прошло ли время cooldown
        """
        now = time.time()
        key = f"{camera_id}_{detection['class']}"
        
        if key not in self.cooldowns or \
           now - self.cooldowns[key] > self.cooldown_seconds:
            self.cooldowns[key] = now
            return True
        
        return False
    
    def speak(self, text):
        """
        Воспроизводит текст через TTS
        """
        # Используем eSpeak или другой TTS движок
        subprocess.run(['espeak', '-v', 'ru', text])
        
        # Или генерируем MP3 файл
        # gtts-cli -l ru -o /tmp/notification.mp3 text
        # subprocess.run(['aplay', '/tmp/notification.mp3'])
```

### Комбинации направлений

Для более точных уведомлений используются комбинации:

| Камера | Позиция объекта | Сообщение |
|--------|----------------|-----------|
| cam_0 (перед) | Центр | "спереди" |
| cam_0 (перед) | Слева | "спереди слева" |
| cam_0 (перед) | Справа | "спереди справа" |
| cam_1 (право) | Центр | "справа" |
| cam_2 (лево) | Центр | "слева" |
| cam_3 (зад) | Центр | "сзади" |
| cam_3 (зад) | Слева | "сзади слева" |
| cam_3 (зад) | Справа | "сзади справа" |
| cam_4 (верх) | Любой | "над головой" |

### Логика определения направления

```python
def get_direction_description(camera_id, bbox_center_x, frame_width):
    """
    Определяет направление на основе позиции объекта в кадре
    """
    center_ratio = bbox_center_x / frame_width
    
    directions = {
        'cam_0': {  # Передняя камера
            (0.0, 0.33): 'спереди слева',
            (0.33, 0.66): 'спереди',
            (0.66, 1.0): 'спереди справа'
        },
        'cam_1': {  # Правая камера
            (0.0, 1.0): 'справа'
        },
        'cam_2': {  # Левая камера
            (0.0, 1.0): 'слева'
        },
        'cam_3': {  # Задняя камера
            (0.0, 0.33): 'сзади слева',
            (0.33, 0.66): 'сзади',
            (0.66, 1.0): 'сзади справа'
        },
        'cam_4': {  # Верхняя камера
            (0.0, 1.0): 'над головой'
        }
    }
    
    cam_directions = directions.get(camera_id, {})
    
    for (low, high), description in cam_directions.items():
        if low <= center_ratio < high:
            return description
    
    return 'неизвестно'
```

## Поток данных от детекции до планшета

### Полная цепочка

```
1. Камера захватывает кадр
         ↓
2. GStreamer декодирует H.264 → RGB
         ↓
3. Кадр уменьшается до 640×640 для NPU
         ↓
4. YOLOv8 на NPU выполняет инференс
         ↓
5. Постобработка: фильтрация по confidence
         ↓
6. Если обнаружен объект:
   ├─→ Наложение BBOX на полный кадр
   ├─→ Генерация голосового уведомления
   └─→ Отправка события через WebSocket
         ↓
7. Кадр с BBOX кодируется в H.264
         ↓
8. RTSP сервер транслирует поток
         ↓
9. Планшет подключается и отображает видео
```

### Формат WebSocket сообщения о детекции

```json
{
  "type": "detection_event",
  "timestamp": "2024-01-15T10:30:15.123Z",
  "camera_id": "cam_0",
  "camera_name": "Front",
  "direction": "front",
  "objects": [
    {
      "id": 1,
      "class": "drone",
      "confidence": 0.87,
      "bbox": {
        "x_min": 120,
        "y_min": 45,
        "x_max": 180,
        "y_max": 95
      },
      "center": {
        "x": 150,
        "y": 70
      },
      "size": {
        "width": 60,
        "height": 50
      },
      "area": 3000,
      "track_id": 42
    }
  ],
  "notification": {
    "voice_message": "Внимание! Дрон обнаружен спереди!",
    "priority": "high",
    "audio_file": "/notifications/audio_20240115_103015.mp3"
  },
  "telemetry": {
    "system_load": {
      "cpu": 45.2,
      "memory": 62.8,
      "npu": 78.5
    },
    "fps": {
      "capture": 58,
      "detection": 20
    }
  }
}
```

## Оптимизация производительности

### Методы оптимизации

1. **Пропуск кадров**: Обработка каждого 2-3 кадра вместо каждого
2. **Уменьшение разрешения**: 640×640 для детекции, 1080p для стриминга
3. **Параллелизация**: 5 потоков NPU одновременно
4. **Кэширование**: Кэширование результатов для статичных сцен
5. **Batch inference**: Группировка кадров от разных камер

### Балансировка нагрузки

```python
# Конфигурация для оптимальной производительности
config = {
    'detection': {
        'resolution': 640,  # Для NPU
        'fps_target': 20,   # Целевой FPS детекции
        'frame_skip': 2,    # Пропускать 2 кадра из 3
        'batch_size': 1     # По одному кадру на камеру
    },
    'streaming': {
        'resolution': 1920, # Full HD для вывода
        'fps_target': 30,   # 30 FPS для видео
        'bitrate': 4000     # 4 Mbps
    },
    'npu': {
        'threads': 5,       # По потоку на камеру
        'core_mask': 0xF0   # Использование больших ядер
    }
}
```

## Мониторинг потоков данных

### Метрики для отслеживания

- **FPS захвата**: Должен быть ≥ 50 для каждой камеры
- **FPS детекции**: Целевой 15-20 FPS
- **Задержка**: От захвата до уведомления < 200ms
- **Использование NPU**: 70-90% (оптимальная загрузка)
- **Потеря кадров**: < 1% от общего числа

### Dashboard мониторинга

```python
# Пример метрик Prometheus
metrics = {
    'camera_fps_total': Counter('camera_frames_captured', 'Total captured frames', ['camera_id']),
    'camera_fps_current': Gauge('camera_fps_current', 'Current FPS', ['camera_id']),
    'detection_count': Counter('detections_total', 'Total detections', ['camera_id', 'class']),
    'npu_utilization': Gauge('npu_utilization_percent', 'NPU utilization %'),
    'processing_latency': Histogram('processing_latency_seconds', 'Processing latency'),
    'websocket_clients': Gauge('websocket_clients_connected', 'Connected WS clients')
}
```

## Следующие шаги

Изучите также:
- [REST API](../api/rest_api.md) - Управление системой
- [WebSocket API](../api/websocket_api.md) - Стриминг и события
- [Конфигурация](../../deployment/configuration.md) - Настройка параметров
