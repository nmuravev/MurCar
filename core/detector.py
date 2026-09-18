"""
YOLOv8s детектор для Orange Pi 5 NPU (RKNN формат)
Обучение на датасетах: drones, VTOL, helicopters, planes
"""

import logging
import time
from typing import List, Optional
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class YOLOv8Detector:
    """
    Детектор объектов на базе YOLOv8s, оптимизированный под NPU Orange Pi 5
    
    Поддерживаемые классы:
    - drone (БПЛА квадрокоптерного типа)
    - vtol (Вертолеты вертикального взлета)
    - helicopter (Классические вертолеты)
    - plane (Самолеты)
    """
    
    # Классы объектов для детекции
    CLASSES = ['drone', 'vtol', 'helicopter', 'plane']
    
    def __init__(
        self,
        model_path: str = "models/yolov8s_drone.rknn",
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        input_size: tuple = (640, 640),
        use_npu: bool = True
    ):
        """
        Инициализация детектора
        
        Args:
            model_path: Путь к модели в формате RKNN
            confidence_threshold: Порог уверенности детекции
            iou_threshold: Порог IoU для NMS
            input_size: Размер входного изображения для модели
            use_npu: Использовать ли NPU для ускорения
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self.use_npu = use_npu
        
        self.model = None
        self.is_loaded = False
        
        # Статистика производительности
        self.fps_history = []
        self.last_inference_time = 0.0
        
    def load_model(self):
        """
        Загрузка RKNN модели для NPU Orange Pi 5
        
        Требует установленный rknn-toolkit2 и драйверы NPU
        """
        logger.info(f"Loading YOLOv8s model from {self.model_path}")
        
        if not Path(self.model_path).exists():
            logger.warning(f"Model file not found: {self.model_path}")
            logger.info("Please convert YOLOv8s to RKNN format using rknn-toolkit2")
            logger.info("Example conversion code provided in models/convert_to_rknn.py")
            return False
        
        try:
            if self.use_npu:
                from rknn.api import RKNN
                
                self.model = RKNN()
                self.model.load_rknn(self.model_path)
                
                # Инициализация NPU
                ret = self.model.init_runtime(
                    target='rk3588',
                    device_id='auto'
                )
                
                if ret != 0:
                    logger.error(f"Failed to initialize NPU runtime: {ret}")
                    return False
                    
                logger.info("NPU initialized successfully")
            else:
                logger.warning("NPU disabled, falling back to CPU (slow)")
                # TODO: Загрузка ONNX модели для CPU
            
            self.is_loaded = True
            logger.info(f"Model loaded successfully. Classes: {self.CLASSES}")
            return True
            
        except ImportError as e:
            logger.error(f"rknn-toolkit2 not installed: {e}")
            logger.info("Install with: pip install rknn-toolkit2")
            return False
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """
        Предобработка кадра для модели
        
        Args:
            frame: Входное изображение (BGR, OpenCV формат)
            
        Returns:
            Предобработанный тензор
        """
        import cv2
        
        # Resize до input_size
        resized = cv2.resize(frame, self.input_size, interpolation=cv2.INTER_LINEAR)
        
        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Normalize to [0, 1]
        normalized = rgb.astype(np.float32) / 255.0
        
        # Transpose to CHW format
        transposed = np.transpose(normalized, (2, 0, 1))
        
        # Add batch dimension
        batched = np.expand_dims(transposed, axis=0)
        
        return batched
    
    def detect(self, frame: np.ndarray) -> List[dict]:
        """
        Детекция объектов на кадре
        
        Args:
            frame: Кадр изображения (BGR, OpenCV формат)
            
        Returns:
            Список обнаруженных объектов с bbox, confidence и class
        """
        if not self.is_loaded:
            logger.warning("Model not loaded, skipping detection")
            return []
        
        start_time = time.time()
        
        try:
            # Предобработка
            input_data = self.preprocess(frame)
            
            # Инференс
            if self.use_npu and self.model:
                outputs = self.model.inferences([input_data])
            else:
                logger.error("No model available for inference")
                return []
            
            # Постобработка
            detections = self.postprocess(outputs, frame.shape)
            
            # Расчет FPS
            inference_time = time.time() - start_time
            self.last_inference_time = inference_time
            self.fps_history.append(1.0 / inference_time)
            if len(self.fps_history) > 30:
                self.fps_history.pop(0)
            
            avg_fps = np.mean(self.fps_history)
            logger.debug(f"Detection: {len(detections)} objects, {inference_time*1000:.1f}ms, FPS: {avg_fps:.1f}")
            
            return detections
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []
    
    def postprocess(self, outputs: List[np.ndarray], image_shape: tuple) -> List[dict]:
        """
        Постобработка выходов модели (декодирование, NMS)
        
        Args:
            outputs: Выходные данные модели
            image_shape: Оригинальный размер изображения (height, width, channels)
            
        Returns:
            Отфильтрованные детекции
        """
        # YOLOv8 output format: [batch, 84, 8400] -> [x, y, w, h, class_probs]
        output = outputs[0] if isinstance(outputs, list) else outputs
        
        if len(output.shape) == 3:
            output = output[0]  # Remove batch dimension
        
        # Транспонирование для удобства обработки
        # output shape: (84, 8400) -> (8400, 84)
        output = output.T
        
        boxes = []
        scores = []
        class_ids = []
        
        img_height, img_width = image_shape[:2]
        scale_x = img_width / self.input_size[0]
        scale_y = img_height / self.input_size[1]
        
        for i in range(output.shape[0]):
            # Get class probabilities
            class_probs = output[i, 4:]
            class_id = np.argmax(class_probs)
            confidence = class_probs[class_id]
            
            if confidence >= self.confidence_threshold:
                # Get box coordinates (center_x, center_y, width, height)
                cx, cy, w, h = output[i, :4]
                
                # Convert to corner coordinates (x1, y1, x2, y2)
                x1 = (cx - w / 2) * scale_x
                y1 = (cy - h / 2) * scale_y
                x2 = (cx + w / 2) * scale_x
                y2 = (cy + h / 2) * scale_y
                
                boxes.append([x1, y1, x2, y2])
                scores.append(confidence)
                class_ids.append(class_id)
        
        # Non-Maximum Suppression
        if len(boxes) > 0:
            indices = self._nms(boxes, scores, self.iou_threshold)
            
            detections = []
            for idx in indices:
                detections.append({
                    'bbox': [float(boxes[idx][j]) for j in range(4)],
                    'confidence': float(scores[idx]),
                    'class_id': int(class_ids[idx]),
                    'class_name': self.CLASSES[class_ids[idx]]
                })
            
            return detections
        
        return []
    
    def _nms(self, boxes: List[List[float]], scores: List[float], iou_threshold: float) -> List[int]:
        """
        Non-Maximum Suppression для фильтрации перекрывающихся bbox
        
        Args:
            boxes: Список bounding boxes [x1, y1, x2, y2]
            scores: Уверенности детекции
            iou_threshold: Порог IoU
            
        Returns:
            Индексы выбранных bbox
        """
        if len(boxes) == 0:
            return []
        
        boxes = np.array(boxes)
        scores = np.array(scores)
        
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h
            
            ovr = inter / (areas[i] + areas[order[1:]] - inter)
            
            order = order[1:][ovr <= iou_threshold]
        
        return keep
    
    def get_stats(self) -> dict:
        """Получить статистику производительности"""
        return {
            'avg_fps': np.mean(self.fps_history) if self.fps_history else 0,
            'last_inference_time_ms': self.last_inference_time * 1000,
            'is_loaded': self.is_loaded,
            'model_path': self.model_path
        }


# Пример использования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    detector = YOLOv8Detector(
        model_path="models/yolov8s_drone.rknn",
        confidence_threshold=0.5
    )
    
    if detector.load_model():
        print("Model loaded successfully!")
        print(f"Classes: {detector.CLASSES}")
    else:
        print("Failed to load model. Please convert YOLOv8s to RKNN format first.")
