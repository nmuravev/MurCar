# 🔌 WebSocket API Документация

## Обзор

WebSocket API обеспечивает двустороннюю связь в реальном времени для стриминга видео, передачи телеметрии и событий детекции.

**URL подключения**: `ws://<orange_pi_ip>:8080/ws`

## Аутентификация

При подключении необходимо передать токен в параметре URL:
```
ws://192.168.1.100:8080/ws?token=<your_jwt_token>
```

## Типы сообщений

### Клиент → Сервер

#### 1. Подписка на поток камеры
```json
{
  "action": "subscribe",
  "stream_type": "video",
  "camera_id": "cam_0",
  "format": "h264"
}
```

#### 2. Отписка от потока
```json
{
  "action": "unsubscribe",
  "stream_type": "video",
  "camera_id": "cam_0"
}
```

#### 3. Запрос телеметрии
```json
{
  "action": "subscribe",
  "stream_type": "telemetry",
  "interval_ms": 100
}
```

#### 4. Запрос событий детекции
```json
{
  "action": "subscribe",
  "stream_type": "detections"
}
```

#### 5. Управление камерой (PTZ если поддерживается)
```json
{
  "action": "camera_control",
  "camera_id": "cam_0",
  "command": "move",
  "params": {
    "pan": 45,
    "tilt": 30
  }
}
```

### Сервер → Клиент

#### 1. Видеопоток (бинарные данные)
Формат: Бинарные данные H.264/H.265 с наложенными bounding boxes

**Заголовок кадра** (первые 16 байт):
```
Bytes 0-3:   Magic number (0xDDET)
Bytes 4-7:   Frame size (uint32)
Bytes 8-11:  Timestamp (uint32, milliseconds)
Bytes 12-15: Camera ID (uint32)
Bytes 16+:   H.264/H.265 данные
```

#### 2. Событие детекции
```json
{
  "type": "detection",
  "timestamp": "2024-01-15T10:30:15.123Z",
  "camera_id": "cam_0",
  "camera_name": "Front",
  "direction": "front",
  "objects": [
    {
      "class": "drone",
      "confidence": 0.87,
      "bbox": {
        "x": 120,
        "y": 45,
        "width": 60,
        "height": 50
      },
      "center": {
        "x": 150,
        "y": 70
      },
      "track_id": 42
    }
  ],
  "notification": {
    "voice_message": "Внимание! Дрон обнаружен спереди!",
    "priority": "high"
  }
}
```

#### 3. Телеметрия системы
```json
{
  "type": "telemetry",
  "timestamp": "2024-01-15T10:30:15.123Z",
  "system": {
    "cpu_usage": 45.2,
    "memory_usage": 62.8,
    "npu_usage": 78.5,
    "temperature": 52.3,
    "uptime": 3600
  },
  "cameras": [
    {
      "id": "cam_0",
      "fps_current": 58,
      "fps_target": 60,
      "dropped_frames": 12,
      "status": "active"
    }
  ],
  "detections": {
    "last_minute": 3,
    "last_hour": 45,
    "total": 1234
  }
}
```

#### 4. Статус подключения камеры
```json
{
  "type": "camera_status",
  "camera_id": "cam_0",
  "status": "connected",
  "message": "Camera initialized successfully",
  "resolution": "1920x1080",
  "fps": 60
}
```

#### 5. Ошибка
```json
{
  "type": "error",
  "code": "CAMERA_DISCONNECTED",
  "message": "Camera cam_0 lost connection",
  "timestamp": "2024-01-15T10:30:15.123Z",
  "recoverable": true
}
```

#### 6. Голосовое уведомление (текст)
```json
{
  "type": "voice_notification",
  "timestamp": "2024-01-15T10:30:15.123Z",
  "message": "Внимание! Дрон обнаружен слева сзади!",
  "direction": "back_left",
  "object_class": "drone",
  "confidence": 0.87,
  "audio_file": "/notifications/audio_20240115_103015.mp3"
}
```

## Протокол стриминга видео

### Формат кадра с BBOX

Каждый видеопоток содержит наложенные bounding boxes:

```
+------------------+
|  H.264 Frame     |
|  + BBOX Overlay  |
+------------------+
       |
       v
+------------------+
|  Header (16B)    |
|  Payload (N bytes)|
+------------------+
```

**BBOX формат** (накладывается поверх H.264):
- Красная рамка: drone
- Желтая рамка: vtol
- Синяя рамка: airplane
- Зеленая рамка: helicopter

### Мультиплексирование потоков

Для поддержки 5 камер одновременно используется мультиплексирование:

```json
{
  "type": "multi_stream",
  "streams": [
    {
      "camera_id": "cam_0",
      "frame_data": "<base64_h264>",
      "timestamp": 1705315815123
    },
    {
      "camera_id": "cam_1",
      "frame_data": "<base64_h264>",
      "timestamp": 1705315815125
    }
  ]
}
```

## Примеры использования

### JavaScript (браузер)

```javascript
const ws = new WebSocket('ws://192.168.1.100:8080/ws?token=eyJhbGc...');

ws.onopen = () => {
  console.log('Connected to drone detection system');
  
  // Подписаться на видео с передней камеры
  ws.send(JSON.stringify({
    action: 'subscribe',
    stream_type: 'video',
    camera_id: 'cam_0',
    format: 'h264'
  }));
  
  // Подписаться на события детекции
  ws.send(JSON.stringify({
    action: 'subscribe',
    stream_type: 'detections'
  }));
};

ws.onmessage = (event) => {
  if (event.data instanceof Blob) {
    // Бинарные данные видео
    handleVideoFrame(event.data);
  } else {
    // JSON сообщение
    const message = JSON.parse(event.data);
    
    switch(message.type) {
      case 'detection':
        handleDetection(message);
        break;
      case 'telemetry':
        updateTelemetryDisplay(message);
        break;
      case 'voice_notification':
        playVoiceNotification(message);
        break;
    }
  }
};

function handleDetection(message) {
  console.log(`Detected ${message.objects.length} objects`);
  message.objects.forEach(obj => {
    console.log(`- ${obj.class} (${obj.confidence}) at [${obj.bbox.x}, ${obj.bbox.y}]`);
  });
  
  if (message.notification) {
    console.log(`Voice: ${message.notification.voice_message}`);
  }
}
```

### Python

```python
import asyncio
import websockets
import json

async def connect():
    uri = "ws://192.168.1.100:8080/ws?token=eyJhbGc..."
    
    async with websockets.connect(uri) as websocket:
        # Подписка на события
        await websocket.send(json.dumps({
            "action": "subscribe",
            "stream_type": "detections"
        }))
        
        # Подписка на телеметрию
        await websocket.send(json.dumps({
            "action": "subscribe",
            "stream_type": "telemetry",
            "interval_ms": 500
        }))
        
        async for message in websocket:
            try:
                data = json.loads(message)
                
                if data.get('type') == 'detection':
                    print(f"DETECTION: {data['objects']}")
                    
                    if 'notification' in data:
                        print(f"VOICE: {data['notification']['voice_message']}")
                        
                elif data.get('type') == 'telemetry':
                    print(f"CPU: {data['system']['cpu_usage']}%")
                    
            except json.JSONDecodeError:
                # Бинарные данные видео
                process_video_frame(message)

asyncio.run(connect())
```

### Flutter (Dart)

```dart
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';

class DroneDetectionClient {
  late WebSocketChannel channel;
  
  void connect(String ip, String token) {
    channel = WebSocketChannel.connect(
      Uri.parse('ws://$ip:8080/ws?token=$token'),
    );
    
    channel.stream.listen((message) {
      if (message is String) {
        final data = jsonDecode(message);
        _handleMessage(data);
      } else if (message is List<int>) {
        _handleVideoFrame(message);
      }
    });
    
    // Подписка на детекции
    channel.sink.add(jsonEncode({
      'action': 'subscribe',
      'stream_type': 'detections',
    }));
  }
  
  void _handleMessage(Map<String, dynamic> data) {
    switch (data['type']) {
      case 'detection':
        _onDetection(data);
        break;
      case 'voice_notification':
        _onVoiceNotification(data);
        break;
      case 'telemetry':
        _onTelemetry(data);
        break;
    }
  }
  
  void _onDetection(Map<String, dynamic> data) {
    print('Обнаружено объектов: ${data['objects'].length}');
    
    for (var obj in data['objects']) {
      print('- ${obj['class']} (${obj['confidence']})');
    }
    
    if (data['notification'] != null) {
      print('Голос: ${data['notification']['voice_message']}');
    }
  }
  
  void _onVoiceNotification(Map<String, dynamic> data) {
    // Воспроизведение аудио
    print('Голосовое уведомление: ${data['message']}');
  }
  
  void disconnect() {
    channel.sink.close();
  }
}
```

## Коды ошибок WebSocket

| Код | Название | Описание |
|-----|----------|----------|
| 1000 | NORMAL_CLOSURE | Нормальное закрытие |
| 1001 | GOING_AWAY | Клиент уходит |
| 1002 | PROTOCOL_ERROR | Ошибка протокола |
| 1003 | UNSUPPORTED_DATA | Неподдерживаемые данные |
| 1008 | POLICY_VIOLATION | Нарушение политики |
| 1009 | MESSAGE_TOO_BIG | Сообщение слишком большое |
| 4000 | AUTH_FAILED | Ошибка аутентификации |
| 4001 | CAMERA_NOT_FOUND | Камера не найдена |
| 4002 | STREAM_BUSY | Поток занят |
| 4003 | NPU_OVERLOAD | Перегрузка NPU |

## Производительность

### Рекомендуемые параметры

- **Видео**: 1080p @ 30fps на камеру (для 5 камер)
- **Телеметрия**: интервал 500ms
- **Детекции**: реального времени (по факту обнаружения)

### Оптимизация

1. Используйте бинарный формат для видео вместо base64
2. Настройте QoS на сети для приоритизации трафика
3. Используйте отдельную сеть для видеопотоков
4. Включите сжатие WebSocket (permessage-deflate)

## Безопасность

1. Всегда используйте токены аутентификации
2. Ограничьте доступ по IP адресам
3. Используйте WSS (WebSocket Secure) в production
4. Регулярно обновляйте токены
5. Логируйте все подключения

## Версионирование

Протокол версионируется через параметр при подключении:
```
ws://192.168.1.100:8080/ws?token=...&version=1.0
```

Текущая версия: **1.0**
