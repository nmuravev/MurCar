"""
Скрипт для конвертации YOLOv8s модели в формат RKNN для Orange Pi 5 NPU

Требования:
- ultralytics (для загрузки YOLOv8)
- rknn-toolkit2 (для конвертации в RKNN)

Использование общественных датасетов:
- DroneDetection (UAV детекция)
- VTOL Aircraft Dataset
- Helicopter Detection Dataset
- Small Plane Detection
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def convert_yolov8_to_rknn(
    model_name: str = "yolov8s.pt",
    output_path: str = "models/yolov8s_drone.rknn",
    dataset_path: str = "datasets/drone_dataset.yaml",
    target_platform: str = "rk3588"
):
    """
    Конвертация YOLOv8 модели в RKNN формат для NPU Orange Pi 5
    
    Args:
        model_name: Имя предобученной модели YOLOv8 или путь к weights
        output_path: Путь для сохранения RKNN модели
        dataset_path: Путь к YAML файлу датасета для калибровки
        target_platform: Целевая платформа (rk3588 для Orange Pi 5)
    """
    try:
        from rknn.api import RKNN
        import yaml
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.info("Install with: pip install rknn-toolkit2 pyyaml")
        return False
    
    # Создание директории для моделей
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting conversion: {model_name} -> {output_path}")
    
    # Загрузка конфигурации датасета
    try:
        with open(dataset_path, 'r') as f:
            dataset_config = yaml.safe_load(f)
        
        classes = dataset_config.get('names', [])
        nc = len(classes)  # Number of classes
        
        logger.info(f"Dataset loaded: {nc} classes - {classes}")
        
    except FileNotFoundError:
        logger.warning(f"Dataset config not found: {dataset_path}")
        logger.info("Using default COCO classes for conversion")
        classes = ['drone', 'vtol', 'helicopter', 'plane']
        nc = len(classes)
    
    # Инициализация RKNN
    rknn = RKNN(verbose=True)
    
    # Конфигурация
    logger.info("Configuring RKNN...")
    rknn.config(
        mean_values=[[0, 0, 0]],
        std_values=[[255, 255, 255]],
        target_platform=target_platform,
        optimization_level=3,  # Максимальная оптимизация для NPU
        quantization=True,    # INT8 квантование для ускорения
        do_quantization=True
    )
    
    # Загрузка ONNX модели (YOLOv8 экспортируется в ONNX)
    logger.info("Loading ONNX model...")
    
    # Сначала нужно экспортировать YOLOv8 в ONNX
    onnx_path = export_yolov8_to_onnx(model_name, nc, classes)
    
    if not onnx_path:
        logger.error("Failed to export YOLOv8 to ONNX")
        return False
    
    # Загрузка ONNX в RKNN
    ret = rknn.load_onnx(
        model=onnx_path,
        inputs=[{'name': 'images', 'shape': [1, 3, 640, 640]}]
    )
    
    if ret != 0:
        logger.error(f"Failed to load ONNX model: {ret}")
        return False
    
    # Калибровка на датасете (для INT8 квантования)
    logger.info("Running calibration...")
    ret = rknn.build(
        do_quantization=True,
        dataset=dataset_path if Path(dataset_path).exists() else None
    )
    
    if ret != 0:
        logger.error(f"Build failed: {ret}")
        return False
    
    # Экспорт RKNN модели
    logger.info(f"Exporting RKNN model to {output_path}...")
    ret = rknn.export_rknn(output_path)
    
    if ret != 0:
        logger.error(f"Export failed: {ret}")
        return False
    
    logger.info(f"Successfully converted model to {output_path}")
    
    # Тестирование модели
    logger.info("Testing RKNN model...")
    ret = rknn.init_runtime(target=target_platform, device_id='auto')
    if ret == 0:
        logger.info("RKNN model test successful!")
    else:
        logger.warning(f"Runtime test failed: {ret}")
    
    rknn.release()
    
    return True


def export_yolov8_to_onnx(
    model_name: str,
    num_classes: int = 4,
    class_names: list = None
) -> str:
    """
    Экспорт YOLOv8 модели в ONNX формат
    
    Args:
        model_name: Предобученная модель или weights
        num_classes: Количество классов для fine-tuning
        class_names: Список имен классов
        
    Returns:
        Путь к ONNX файлу или None при ошибке
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("ultralytics not installed")
        logger.info("Install with: pip install ultralytics")
        return None
    
    output_dir = Path("models")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    onnx_path = output_dir / "yolov8s_drone.onnx"
    
    # Если модель уже существует, используем её
    if Path(model_name).exists() and model_name.endswith('.pt'):
        logger.info(f"Loading custom trained model: {model_name}")
        model = YOLO(model_name)
    else:
        # Загрузка предобученной YOLOv8s
        logger.info(f"Loading pretrained YOLOv8s: {model_name}")
        model = YOLO(model_name)
    
    # Fine-tuning на нашем датасете (опционально)
    # model.train(data=dataset_path, epochs=100, imgsz=640)
    
    # Экспорт в ONNX
    logger.info("Exporting to ONNX...")
    try:
        model.export(
            format='onnx',
            imgsz=640,
            simplify=True,
            opset=12,
            dynamic=False
        )
        
        # Перемещение файла
        exported_path = Path(model_name.replace('.pt', '.onnx'))
        if exported_path.exists():
            exported_path.rename(onnx_path)
            logger.info(f"ONNX model saved to {onnx_path}")
            return str(onnx_path)
            
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return None
    
    return None


def prepare_dataset():
    """
    Подготовка датасета для обучения/калибровки
    
    Рекомендуемые общественные датасеты:
    1. DroneDetection Dataset (Kaggle)
    2. UAV-Video Object Detection
    3. VTOL Aircraft Dataset
    4. Small Aircraft Detection
    
    Формат YAML:
    path: datasets/drone_dataset
    train: images/train
    val: images/val
    test: images/test
    
    names:
      0: drone
      1: vtol
      2: helicopter
      3: plane
    """
    dataset_yaml = """
path: datasets/drone_dataset
train: images/train
val: images/val
test: images/test

nc: 4
names:
  0: drone
  1: vtol
  2: helicopter
  3: plane
"""
    
    dataset_dir = Path("datasets")
    dataset_dir.mkdir(parents=True, exist_ok=True)
    
    yaml_path = dataset_dir / "drone_dataset.yaml"
    
    with open(yaml_path, 'w') as f:
        f.write(dataset_yaml)
    
    logger.info(f"Dataset config created: {yaml_path}")
    logger.info("Download and prepare images in datasets/drone_dataset/images/")
    
    return str(yaml_path)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Шаг 1: Подготовка датасета
    logger.info("=" * 50)
    logger.info("Step 1: Preparing dataset configuration")
    dataset_path = prepare_dataset()
    
    # Шаг 2: Конвертация модели
    logger.info("=" * 50)
    logger.info("Step 2: Converting YOLOv8s to RKNN")
    
    success = convert_yolov8_to_rknn(
        model_name="yolov8s.pt",  # Или путь к своей обученной модели .pt
        output_path="models/yolov8s_drone.rknn",
        dataset_path=dataset_path,
        target_platform="rk3588"
    )
    
    if success:
        logger.info("=" * 50)
        logger.info("Conversion completed successfully!")
        logger.info("Model ready for Orange Pi 5 NPU")
    else:
        logger.error("Conversion failed. Check logs above.")
