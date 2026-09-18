"""
GStreamer пайплайны для захвата видео с USB камер на Orange Pi 5
Поддержка H.264 аппаратного кодирования/декодирования
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GStreamerPipeline:
    """Генератор GStreamer пайплайнов для различных сценариев"""
    
    @staticmethod
    def usb_camera_pipeline(
        camera_id: int,
        width: int = 1920,
        height: int = 1080,
        fps: int = 60,
        use_hardware_encoding: bool = True
    ) -> str:
        """
        Пайплайн для захвата с USB камеры с аппаратным декодированием
        
        Args:
            camera_id: ID устройства (/dev/video{camera_id})
            width: Ширина кадра
            height: Высота кадра
            fps: Частота кадров
            use_hardware_encoding: Использовать ли аппаратное кодирование H.264
            
        Returns:
            Строка пайплайна GStreamer
        """
        # Для камер с аппаратным кодированием H.264
        if use_hardware_encoding:
            pipeline = (
                f"v4l2src device=/dev/video{camera_id} ! "
                f"image/jpeg,width={width},height={height},framerate={fps}/1 ! "
                f"jpegdec ! "
                f"videoconvert ! "
                f"video/x-raw,format=NV12 ! "
                f"mpph264enc ! "
                f"h264parse ! "
                f"queue max-size-buffers=3 leaky=downstream ! "
                f"appsink name=sink emit-signals=true sync=false"
            )
        else:
            # Для камер без аппаратного кодирования (MJPEG или raw)
            pipeline = (
                f"v4l2src device=/dev/video{camera_id} ! "
                f"video/x-raw,width={width},height={height},framerate={fps}/1 ! "
                f"videoconvert ! "
                f"video/x-raw,format=NV12 ! "
                f"mpph264enc ! "
                f"h264parse ! "
                f"queue max-size-buffers=3 leaky=downstream ! "
                f"appsink name=sink emit-signals=true sync=false"
            )
        
        logger.info(f"Generated USB camera pipeline for /dev/video{camera_id}: {pipeline}")
        return pipeline
    
    @staticmethod
    def rtsp_server_pipeline(
        source_pipeline: str,
        host: str = "0.0.0.0",
        port: int = 8554,
        path: str = "/stream"
    ) -> str:
        """
        Пайплайн RTSP сервера для стриминга на планшет
        
        Args:
            source_pipeline: Пайплайн источника видео
            host: Хост для bind
            port: Порт RTSP
            path: Путь к стриму
            
        Returns:
            Строка пайплайна GStreamer RTSP сервера
        """
        pipeline = (
            f"{source_pipeline} ! "
            f"rtph264pay config-interval=1 pt=96 ! "
            f"gdppay ! "
            f"tcpserversink host={host} port={port}"
        )
        
        logger.info(f"Generated RTSP server pipeline on {host}:{port}{path}")
        return pipeline
    
    @staticmethod
    def detection_overlay_pipeline(
        source_pipeline: str,
        bbox_data: dict
    ) -> str:
        """
        Пайплайн для наложения BBOX на видео
        
        Примечание: Наложение BBOX лучше делать программно через OpenCV,
        так как GStreamer textoverlay требует сложной настройки координат
        
        Args:
            source_pipeline: Пайплайн источника
            bbox_data: Данные о bounding boxes
            
        Returns:
            Строка пайплайна с наложением
        """
        # Базовый пайплайн - наложение делается в коде через OpenCV
        pipeline = (
            f"{source_pipeline} ! "
            f"videoconvert ! "
            f"appsink name=sink emit-signals=true sync=false"
        )
        
        return pipeline
    
    @staticmethod
    def multi_camera_mux_pipeline(
        camera_pipelines: list,
        layout: str = "2x2"
    ) -> str:
        """
        Пайплайн для объединения нескольких камер в один поток (picture-in-picture)
        
        Args:
            camera_pipelines: Список пайплайнов камер
            layout: Раскладка ("2x2", "1+4", "horizontal", "vertical")
            
        Returns:
            Строка пайплайна с мультиплексированием
        """
        if layout == "2x2":
            # 4 камеры в квадрате 2x2
            sink_str = "compositor name=sink sink_0::xpos=0 sink_0::ypos=0 sink_0::width=960 sink_0::height=540 sink_1::xpos=960 sink_1::ypos=0 sink_1::width=960 sink_1::height=540 sink_2::xpos=0 sink_2::ypos=540 sink_2::width=960 sink_2::height=540 sink_3::xpos=960 sink_3::ypos=540 sink_3::width=960 sink_3::height=540"
        elif layout == "horizontal":
            # Горизонтальная раскладка
            sink_str = "compositor name=sink sink_0::xpos=0 sink_0::ypos=0 sink_0::width=384 sink_0::height=1080 sink_1::xpos=384 sink_1::ypos=0 sink_1::width=384 sink_1::height=1080"
        else:
            sink_str = "compositor name=sink"
        
        inputs = " ".join([f"{pipe} ! queue ! videorate ! video/x-raw,framerate=30/1 ! videoscale ! video/x-raw,width=960,height=540 ! sink_{i}::" 
                          for i, pipe in enumerate(camera_pipelines[:4])])
        
        pipeline = f"{inputs} ! {sink_str} ! x264enc ! rtph264pay ! udpsink host=127.0.0.1 port=5000"
        
        logger.info(f"Generated multi-camera mux pipeline with layout {layout}")
        return pipeline


# Примеры использования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Пайплайн для камеры 0 (фронтальная)
    front_camera = GStreamerPipeline.usb_camera_pipeline(
        camera_id=0,
        width=1920,
        height=1080,
        fps=60
    )
    print(f"Front camera pipeline:\n{front_camera}\n")
    
    # RTSP сервер для стриминга
    rtsp_pipeline = GStreamerPipeline.rtsp_server_pipeline(
        source_pipeline=front_camera,
        host="0.0.0.0",
        port=8554
    )
    print(f"RTSP server pipeline:\n{rtsp_pipeline}\n")
    
    # Мультиплексирование 4 камер
    camera_pipelines = [
        GStreamerPipeline.usb_camera_pipeline(i, 1920, 1080, 60)
        for i in range(4)
    ]
    mux_pipeline = GStreamerPipeline.multi_camera_mux_pipeline(
        camera_pipelines,
        layout="2x2"
    )
    print(f"Multi-camera mux pipeline:\n{mux_pipeline}\n")
