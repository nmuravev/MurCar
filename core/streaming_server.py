"""
RTSP сервер для стриминга видео с детекцией на планшет
Использование GStreamer и aiortc для WebRTC/RTSP
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StreamClient:
    """Информация о подключенном клиенте (планшете)"""
    client_id: str
    host: str
    port: int
    protocol: str  # 'rtsp', 'webrtc', 'websocket'
    connected_at: float
    last_heartbeat: float


class VideoStreamingServer:
    """
    Сервер для трансляции видео с наложенной детекцией на планшет
    
    Поддерживаемые протоколы:
    - RTSP (низкая задержка, хорошая совместимость)
    - WebRTC (минимальная задержка, сложнее в настройке)
    - WebSocket (для передачи телеметрии)
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        rtsp_port: int = 8554,
        webrtc_port: int = 8080,
        websocket_port: int = 8765
    ):
        self.host = host
        self.rtsp_port = rtsp_port
        self.webrtc_port = webrtc_port
        self.websocket_port = websocket_port
        
        self.clients: Dict[str, StreamClient] = {}
        self.is_running = False
        
        # Буфер последних кадров для каждого потока
        self.frame_buffers: Dict[int, bytes] = {}
        
    async def start(self):
        """Запуск серверов всех протоколов"""
        logger.info(f"Starting streaming server on {self.host}")
        
        self.is_running = True
        
        # Запуск RTSP сервера
        rtsp_task = asyncio.create_task(self._run_rtsp_server())
        
        # Запуск WebSocket сервера для телеметрии
        ws_task = asyncio.create_task(self._run_websocket_server())
        
        # WebRTC опционально (требует дополнительной настройки)
        # webrtc_task = asyncio.create_task(self._run_webrtc_server())
        
        logger.info(f"RTSP server: rtsp://{self.host}:{self.rtsp_port}/stream")
        logger.info(f"WebSocket server: ws://{self.host}:{self.websocket_port}")
        
        await asyncio.gather(rtsp_task, ws_task, return_exceptions=True)
    
    async def stop(self):
        """Остановка сервера"""
        logger.info("Stopping streaming server...")
        self.is_running = False
        
        for client_id in list(self.clients.keys()):
            await self._disconnect_client(client_id)
    
    async def _run_rtsp_server(self):
        """
        RTSP сервер через GStreamer
        
        Планшет подключается через VLC или любой RTSP плеер
        URL: rtsp://orange_pi_ip:8554/stream
        """
        try:
            import gi
            gi.require_version('Gst', '1.0')
            gi.require_version('GstRtspServer', '1.0')
            from gi.repository import Gst, GstRtspServer, GLib
            
            # Инициализация GStreamer
            Gst.init(None)
            
            # Создание RTSP сервера
            server = GstRtspServer.RTSPServer()
            server.set_service(str(self.rtsp_port))
            
            # Создание фабрики медиа
            factory = GstRtspServer.RTSPMediaFactory()
            factory.set_launch(
                "( "
                "appsrc name=src emit-signals=true is-live=true caps=video/x-raw,format=BGR,width=1920,height=1080,framerate=30/1 ! "
                "videoconvert ! "
                "x264enc speed-preset=ultrafast tune=zerolatency ! "
                "rtph264pay config-interval=1 name=pay0 pt=96 "
                ")"
            )
            factory.set_shared(True)
            factory.set_buffer_size(3)
            factory.set_latency(0)  # Минимальная задержка
            
            # Добавление маунта
            mount_point = "/stream"
            server.get_mount_points().add_factory(mount_point, factory)
            
            # Привязка к адресу
            server.attach(None)
            
            logger.info(f"RTSP server running on rtsp://{self.host}:{self.rtsp_port}{mount_point}")
            
            # Запуск main loop
            loop = GLib.MainLoop()
            loop.run()
            
        except ImportError as e:
            logger.error(f"GStreamer RTSP not available: {e}")
            logger.info("Install: sudo apt install python3-gi gir1.2-gst-rtsp-server-1.0")
        except Exception as e:
            logger.error(f"RTSP server error: {e}")
    
    async def _run_websocket_server(self):
        """
        WebSocket сервер для передачи телеметрии и команд
        
        Планшет подключается для получения:
        - Координат обнаруженных объектов
        - Голосовых уведомлений (текст)
        - Команд управления
        """
        try:
            import websockets
            
            async def handler(websocket, path):
                client_id = str(id(websocket))
                logger.info(f"WebSocket client connected: {client_id}")
                
                client = StreamClient(
                    client_id=client_id,
                    host=websocket.remote_address[0],
                    port=websocket.remote_address[1],
                    protocol='websocket',
                    connected_at=asyncio.get_event_loop().time(),
                    last_heartbeat=asyncio.get_event_loop().time()
                )
                
                self.clients[client_id] = client
                
                try:
                    async for message in websocket:
                        # Обработка команд от планшета
                        await self._handle_websocket_message(websocket, message)
                        client.last_heartbeat = asyncio.get_event_loop().time()
                        
                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"WebSocket client disconnected: {client_id}")
                finally:
                    del self.clients[client_id]
            
            server = await websockets.start(
                handler,
                self.host,
                self.websocket_port
            )
            
            logger.info(f"WebSocket server running on ws://{self.host}:{self.websocket_port}")
            
            await server.wait_closed()
            
        except ImportError:
            logger.warning("websockets not installed, skipping WebSocket server")
            logger.info("Install: pip install websockets")
        except Exception as e:
            logger.error(f"WebSocket server error: {e}")
    
    async def _handle_websocket_message(self, websocket, message: str):
        """Обработка сообщений от планшета"""
        import json
        
        try:
            data = json.loads(message)
            cmd = data.get('command')
            
            if cmd == 'ping':
                await websocket.send(json.dumps({'status': 'pong'}))
            elif cmd == 'get_stats':
                stats = self.get_server_stats()
                await websocket.send(json.dumps(stats))
            elif cmd == 'switch_camera':
                camera_id = data.get('camera_id')
                logger.info(f"Switching to camera {camera_id}")
                # TODO: Переключение активного потока
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON message: {message}")
    
    async def send_frame(self, camera_id: int, frame_bytes: bytes, detections: list):
        """
        Отправка кадра с детекцией клиентам
        
        Args:
            camera_id: ID камеры
            frame_bytes: JPEG encoded frame с наложенными BBOX
            detections: Список обнаруженных объектов
        """
        # Сохранение в буфер
        self.frame_buffers[camera_id] = frame_bytes
        
        # Отправка телеметрии через WebSocket
        if detections:
            telemetry = {
                'type': 'detection',
                'camera_id': camera_id,
                'timestamp': asyncio.get_event_loop().time(),
                'objects': detections
            }
            
            await self.broadcast_telemetry(telemetry)
    
    async def broadcast_telemetry(self, telemetry: dict):
        """Рассылка телеметрии всем подключенным клиентам"""
        import json
        
        message = json.dumps(telemetry)
        
        disconnected = []
        
        for client_id, client in self.clients.items():
            if client.protocol == 'websocket':
                try:
                    # Найти соответствующий websocket
                    # TODO: Реализовать хранение websocket объектов
                    pass
                except Exception as e:
                    logger.error(f"Failed to send to {client_id}: {e}")
                    disconnected.append(client_id)
        
        # Удаление отключенных клиентов
        for client_id in disconnected:
            del self.clients[client_id]
    
    async def _disconnect_client(self, client_id: str):
        """Отключение клиента"""
        if client_id in self.clients:
            logger.info(f"Disconnecting client {client_id}")
            del self.clients[client_id]
    
    def get_server_stats(self) -> dict:
        """Получение статистики сервера"""
        return {
            'connected_clients': len(self.clients),
            'active_streams': len(self.frame_buffers),
            'uptime': 'N/A',  # TODO: Добавить tracking uptime
            'protocol': {
                'rtsp_port': self.rtsp_port,
                'websocket_port': self.websocket_port
            }
        }


class OverlayRenderer:
    """
    Рендеринг BBOX и телеметрии на кадр
    
    Использует OpenCV для наложения графики
    """
    
    def __init__(self):
        self.colors = {
            'drone': (0, 255, 0),      # Зеленый
            'vtol': (0, 0, 255),       # Красный
            'helicopter': (255, 0, 0), # Синий
            'plane': (255, 255, 0)     # Циан
        }
    
    def draw_detections(self, frame, detections: list) -> bytes:
        """
        Наложение bounding boxes и информации на кадр
        
        Args:
            frame: Кадр изображения (numpy array)
            detections: Список детекций от YOLO
            
        Returns:
            JPEG encoded bytes готового кадра
        """
        import cv2
        import numpy as np
        
        output_frame = frame.copy()
        
        for det in detections:
            bbox = det['bbox']
            class_name = det['class_name']
            confidence = det['confidence']
            
            x1, y1, x2, y2 = map(int, bbox)
            
            # Цвет по классу
            color = self.colors.get(class_name, (255, 255, 255))
            
            # Рисуем bbox
            cv2.rectangle(output_frame, (x1, y1), (x2, y2), color, 2)
            
            # Подпись с классом и уверенностью
            label = f"{class_name}: {confidence:.2f}"
            cv2.putText(
                output_frame,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )
        
        # Кодирование в JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        _, encoded = cv2.imencode('.jpg', output_frame, encode_param)
        
        return encoded.tobytes()


# Пример использования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    server = VideoStreamingServer(
        host="0.0.0.0",
        rtsp_port=8554,
        websocket_port=8765
    )
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        asyncio.run(server.stop())
