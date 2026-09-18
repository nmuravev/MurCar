# 🔌 REST API Документация

## Обзор

REST API предоставляет возможности управления системой обнаружения дронов, настройки параметров и получения статуса системы.

**Базовый URL**: `http://<orange_pi_ip>:8080/api/v1`

## Аутентификация

Все запросы требуют API ключ в заголовке:
```
Authorization: Bearer <your_api_key>
```

## Эндпоинты

### 1. Управление системой

#### GET `/system/status`
Получение текущего статуса системы.

**Ответ**:
```json
{
  "status": "running",
  "uptime": 3600,
  "cameras_active": 5,
  "detections_last_hour": 12,
  "cpu_usage": 45.2,
  "memory_usage": 62.8,
  "npu_usage": 78.5
}
```

#### POST `/system/start`
Запуск системы обнаружения.

**Ответ**:
```json
{
  "message": "System started successfully",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### POST `/system/stop`
Остановка системы обнаружения.

**Ответ**:
```json
{
  "message": "System stopped successfully",
  "timestamp": "2024-01-15T10:35:00Z"
}
```

#### POST `/system/restart`
Перезапуск системы.

### 2. Управление камерами

#### GET `/cameras`
Получение списка всех камер и их статуса.

**Ответ**:
```json
{
  "cameras": [
    {
      "id": "cam_0",
      "name": "Front",
      "status": "active",
      "resolution": "1920x1080",
      "fps": 60,
      "angle": 90,
      "direction": "front"
    },
    {
      "id": "cam_1",
      "name": "Right",
      "status": "active",
      "resolution": "1920x1080",
      "fps": 60,
      "angle": 90,
      "direction": "right"
    }
  ]
}
```

#### GET `/cameras/{camera_id}`
Получение информации о конкретной камере.

#### PUT `/cameras/{camera_id}/settings`
Настройка параметров камеры.

**Тело запроса**:
```json
{
  "resolution": "1920x1080",
  "fps": 60,
  "brightness": 50,
  "contrast": 50
}
```

#### POST `/cameras/{camera_id}/calibrate`
Калибровка камеры.

### 3. Управление детекцией

#### GET `/detection/settings`
Получение текущих настроек детекции.

**Ответ**:
```json
{
  "model": "yolov8s.rknn",
  "confidence_threshold": 0.5,
  "iou_threshold": 0.45,
  "classes": ["drone", "vtol", "airplane", "helicopter"],
  "frame_skip": 2
}
```

#### PUT `/detection/settings`
Обновление настроек детекции.

**Тело запроса**:
```json
{
  "confidence_threshold": 0.6,
  "iou_threshold": 0.5,
  "frame_skip": 3
}
```

#### GET `/detection/history`
Получение истории обнаружений.

**Параметры**:
- `limit` (int): Количество записей (default: 100)
- `start_time` (string): Начало периода (ISO 8601)
- `end_time` (string): Конец периода (ISO 8601)
- `camera_id` (string): Фильтр по камере

**Ответ**:
```json
{
  "detections": [
    {
      "id": "det_001",
      "timestamp": "2024-01-15T10:30:15Z",
      "camera_id": "cam_0",
      "class": "drone",
      "confidence": 0.87,
      "bbox": [120, 45, 180, 95],
      "direction": "front",
      "telemetry": {
        "distance_estimate": "unknown",
        "speed_estimate": "unknown"
      }
    }
  ],
  "total": 1,
  "limit": 100
}
```

### 4. Управление стримингом

#### GET `/streaming/status`
Получение статуса стриминга.

**Ответ**:
```json
{
  "rtsp_enabled": true,
  "rtsp_port": 8554,
  "active_streams": 5,
  "clients_connected": 2
}
```

#### POST `/streaming/start`
Запуск RTSP стриминга.

#### POST `/streaming/stop`
Остановка RTSP стриминга.

#### GET `/streaming/clients`
Получение списка подключенных клиентов.

### 5. Управление уведомлениями

#### GET `/notifications/settings`
Получение настроек уведомлений.

**Ответ**:
```json
{
  "voice_enabled": true,
  "voice_language": "ru",
  "min_confidence": 0.5,
  "cooldown_seconds": 10,
  "directions_enabled": true
}
```

#### PUT `/notifications/settings`
Обновление настроек уведомлений.

**Тело запроса**:
```json
{
  "voice_enabled": true,
  "voice_language": "ru",
  "min_confidence": 0.6,
  "cooldown_seconds": 15
}
```

#### GET `/notifications/history`
История отправленных уведомлений.

### 6. Логи и диагностика

#### GET `/logs/system`
Получение системных логов.

**Параметры**:
- `lines` (int): Количество строк (default: 100)
- `level` (string): Уровень логирования (INFO, WARNING, ERROR)

#### GET `/logs/detection`
Логи детекции.

#### POST `/diagnostics/run`
Запуск диагностики системы.

**Ответ**:
```json
{
  "status": "completed",
  "checks": {
    "cameras": "passed",
    "npu": "passed",
    "network": "passed",
    "storage": "warning",
    "memory": "passed"
  },
  "recommendations": [
    "Free up storage space (85% used)"
  ]
}
```

## Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успех |
| 400 | Неверный запрос |
| 401 | Неавторизован |
| 403 | Доступ запрещен |
| 404 | Ресурс не найден |
| 500 | Внутренняя ошибка сервера |
| 503 | Сервис недоступен |

## Примеры использования

### Python пример

```python
import requests

API_KEY = "your_api_key"
BASE_URL = "http://192.168.1.100:8080/api/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Получить статус системы
response = requests.get(f"{BASE_URL}/system/status", headers=headers)
print(response.json())

# Обновить настройки детекции
new_settings = {
    "confidence_threshold": 0.6,
    "iou_threshold": 0.5
}
response = requests.put(
    f"{BASE_URL}/detection/settings",
    headers=headers,
    json=new_settings
)
print(response.json())

# Получить историю обнаружений
response = requests.get(
    f"{BASE_URL}/detection/history?limit=50",
    headers=headers
)
print(response.json())
```

### cURL примеры

```bash
# Получить статус системы
curl -X GET http://192.168.1.100:8080/api/v1/system/status \
  -H "Authorization: Bearer your_api_key"

# Запустить систему
curl -X POST http://192.168.1.100:8080/api/v1/system/start \
  -H "Authorization: Bearer your_api_key"

# Обновить настройки детекции
curl -X PUT http://192.168.1.100:8080/api/v1/detection/settings \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"confidence_threshold": 0.6}'
```

## Лимиты

- Максимум 100 запросов в минуту на один API ключ
- Максимум 1000 записей в истории обнаружений
- Максимальный размер payload: 1MB

## Версионирование

API версионируется через URL: `/api/v1/`. При внесении breaking changes будет выпущена версия v2.
