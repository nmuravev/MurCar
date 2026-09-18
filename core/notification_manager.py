"""
Менеджер голосовых уведомлений на основе детекции
Использование TTS (Text-to-Speech) для озвучивания направления и типа угрозы
"""

import logging
import time
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class Direction(Enum):
    """Направления для голосовых сообщений"""
    FRONT = "впереди"
    BACK = "сзади"
    LEFT = "слева"
    RIGHT = "справа"
    TOP = "над головой"
    FRONT_LEFT = "спереди слева"
    FRONT_RIGHT = "спереди справа"
    BACK_LEFT = "сзади слева"
    BACK_RIGHT = "сзади справа"


@dataclass
class VoiceAlert:
    """Структура голосового уведомления"""
    message: str
    priority: int  # 1-5, где 5 - критическое
    direction: Direction
    object_type: str
    timestamp: float
    audio_file: Optional[str] = None


class NotificationManager:
    """
    Менеджер уведомлений с интеллектуальным cooldown и приоритетами
    
    Функции:
    - Генерация текстовых сообщений на основе позиции и типа объекта
    - Text-to-Speech синтез (RuTTS или Silero)
    - Cooldown для предотвращения спама
    - Приоритизация угроз
    """
    
    # Приоритеты типов объектов (чем выше, тем важнее)
    OBJECT_PRIORITIES = {
        'drone': 5,          # Критическая угроза
        'vtol': 4,           # Высокий приоритет
        'helicopter': 4,     # Высокий приоритет
        'plane': 3           # Средний приоритет
    }
    
    # Шаблоны сообщений
    MESSAGE_TEMPLATES = {
        'single': "Внимание! {object_type} {direction}",
        'multiple': "Внимание! Несколько целей: {objects}",
        'critical': "Тревога! {object_type} {direction}, высота {altitude} метров",
        'lost': "Цель потеряна"
    }
    
    def __init__(
        self,
        language: str = 'ru',
        cooldown_seconds: float = 5.0,
        use_tts: bool = True,
        tts_engine: str = 'silero'  # 'silero', 'rhvoice', 'yandex'
    ):
        self.language = language
        self.cooldown_seconds = cooldown_seconds
        self.use_tts = use_tts
        self.tts_engine = tts_engine
        
        # Отслеживание последних уведомлений
        self.last_notification: Dict[str, float] = {}
        
        # Буфер активных алертов
        self.active_alerts: list = []
        
        # TTS движок
        self.tts_model = None
        
        # Директория для аудио файлов
        self.audio_dir = Path("audio_alerts")
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
    def initialize_tts(self):
        """Инициализация TTS движка"""
        if not self.use_tts:
            logger.info("TTS disabled")
            return True
        
        logger.info(f"Initializing TTS engine: {self.tts_engine}")
        
        try:
            if self.tts_engine == 'silero':
                # Silero TTS - оффлайн, качественный русский голос
                self._init_silero()
            elif self.tts_engine == 'rhvoice':
                # RHVoice - легкий оффлайн движок
                self._init_rhvoice()
            elif self.tts_engine == 'yandex':
                # Yandex SpeechKit - онлайн, лучшее качество
                self._init_yandex()
            else:
                logger.warning(f"Unknown TTS engine: {self.tts_engine}")
                return False
            
            logger.info("TTS engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS: {e}")
            self.use_tts = False
            return False
    
    def _init_silero(self):
        """Инициализация Silero TTS"""
        try:
            import torch
            
            # Загрузка модели Silero
            model, example_text = torch.hub.load(
                repo_or_dir='snakers4/silero-models',
                model='silero_tts',
                language=self.language,
                speaker='xenia'  # Русский женский голос
            )
            
            self.tts_model = model
            logger.info("Silero TTS loaded")
            
        except Exception as e:
            logger.error(f"Silero initialization failed: {e}")
            raise
    
    def _init_rhvoice(self):
        """Инициализация RHVoice"""
        try:
            # Проверка наличия RHVoice в системе
            import subprocess
            
            result = subprocess.run(
                ['RHVoice-test', '--list-voices'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("RHVoice available")
            else:
                raise Exception("RHVoice not installed")
                
        except Exception as e:
            logger.error(f"RHVoice not available: {e}")
            raise
    
    def _init_yandex(self):
        """Инициализация Yandex SpeechKit"""
        logger.warning("Yandex SpeechKit requires API key and internet connection")
        # TODO: Реализация через Yandex Cloud API
    
    def generate_alert(
        self,
        camera_position: str,
        object_type: str,
        confidence: float,
        altitude: Optional[float] = None,
        multiple_objects: bool = False
    ) -> Optional[VoiceAlert]:
        """
        Генерация голосового уведомления
        
        Args:
            camera_position: Позиция камеры (front, back, left, right, top)
            object_type: Тип объекта (drone, vtol, helicopter, plane)
            confidence: Уверенность детекции (0-1)
            altitude: Высота объекта (если известна)
            multiple_objects: Множественные цели
            
        Returns:
            VoiceAlert или None если сработал cooldown
        """
        # Проверка cooldown
        alert_key = f"{camera_position}_{object_type}"
        current_time = time.time()
        
        if not self._should_notify(alert_key, current_time):
            logger.debug(f"Cooldown active for {alert_key}")
            return None
        
        # Определение направления
        direction = self._map_position_to_direction(camera_position)
        
        # Получение названия объекта
        object_name = self._get_object_name(object_type)
        
        # Выбор шаблона сообщения
        if altitude and confidence > 0.8:
            message = self.MESSAGE_TEMPLATES['critical'].format(
                object_type=object_name,
                direction=direction.value,
                altitude=int(altitude)
            )
            priority = 5
        elif multiple_objects:
            message = self.MESSAGE_TEMPLATES['multiple'].format(
                objects=f"{object_name} ({direction.value})"
            )
            priority = 4
        else:
            message = self.MESSAGE_TEMPLATES['single'].format(
                object_type=object_name,
                direction=direction.value
            )
            priority = self.OBJECT_PRIORITIES.get(object_type, 3)
        
        # Создание алерта
        alert = VoiceAlert(
            message=message,
            priority=priority,
            direction=direction,
            object_type=object_type,
            timestamp=current_time
        )
        
        # Обновление последнего уведомления
        self.last_notification[alert_key] = current_time
        
        # Синтез речи
        if self.use_tts:
            audio_file = self._synthesize_speech(message, object_type, camera_position)
            alert.audio_file = audio_file
        
        logger.info(f"Alert generated: {message} (priority: {priority})")
        
        return alert
    
    def _should_notify(self, key: str, current_time: float) -> bool:
        """Проверка необходимости уведомления (cooldown)"""
        if key not in self.last_notification:
            return True
        
        elapsed = current_time - self.last_notification[key]
        return elapsed >= self.cooldown_seconds
    
    def _map_position_to_direction(self, position: str) -> Direction:
        """Маппинг позиции камеры на направление"""
        mapping = {
            'front': Direction.FRONT,
            'back': Direction.BACK,
            'left': Direction.LEFT,
            'right': Direction.RIGHT,
            'top': Direction.TOP
        }
        return mapping.get(position, Direction.FRONT)
    
    def _get_object_name(self, object_type: str) -> str:
        """Получение человеко-читаемого названия объекта"""
        names = {
            'drone': 'дрон',
            'vtol': 'вертолет вертикального взлета',
            'helicopter': 'вертолет',
            'plane': 'самолет'
        }
        return names.get(object_type, 'неопознанный объект')
    
    def _synthesize_speech(
        self,
        text: str,
        object_type: str,
        camera_position: str
    ) -> Optional[str]:
        """Синтез речи из текста"""
        try:
            filename = f"alert_{object_type}_{camera_position}_{int(time.time())}.wav"
            filepath = self.audio_dir / filename
            
            if self.tts_engine == 'silero' and self.tts_model:
                # Silero синтез
                audio = self.tts_model.apply_tts(
                    text=text,
                    speaker='xenia',
                    sample_rate=48000
                )
                
                # Сохранение в файл
                import scipy.io.wavfile as wav
                wav.write(str(filepath), 48000, audio)
                
            elif self.tts_engine == 'rhvoice':
                # RHVoice синтез через командную строку
                import subprocess
                
                subprocess.run([
                    'RHVoice-test',
                    '--voice=Anna',  # Русский голос
                    '--text', text,
                    '--out', str(filepath)
                ], check=True)
            
            else:
                logger.warning("No TTS engine available")
                return None
            
            logger.info(f"Speech synthesized: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}")
            return None
    
    def play_alert(self, alert: VoiceAlert):
        """Воспроизведение голосового уведомления"""
        if not alert.audio_file:
            logger.warning("No audio file for alert")
            return
        
        try:
            import subprocess
            
            # Воспроизведение через aplay (Linux)
            subprocess.run(['aplay', alert.audio_file], check=True)
            
            # Или через pygame (кроссплатформенно)
            # self._play_with_pygame(alert.audio_file)
            
            logger.info(f"Alert played: {alert.message}")
            
        except Exception as e:
            logger.error(f"Failed to play alert: {e}")
    
    def _play_with_pygame(self, audio_file: str):
        """Воспроизведение через pygame (альтернативный метод)"""
        try:
            import pygame
            
            pygame.mixer.init()
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Pygame playback failed: {e}")


# Пример использования
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Инициализация менеджера уведомлений
    notifier = NotificationManager(
        language='ru',
        cooldown_seconds=5.0,
        use_tts=True,
        tts_engine='silero'
    )
    
    # Инициализация TTS
    if notifier.initialize_tts():
        print("TTS ready")
    
    # Генерация тестового алерта
    alert = notifier.generate_alert(
        camera_position='front',
        object_type='drone',
        confidence=0.85,
        altitude=50.0
    )
    
    if alert:
        print(f"Alert: {alert.message}")
        print(f"Priority: {alert.priority}")
        print(f"Direction: {alert.direction.value}")
        
        # Воспроизведение
        if alert.audio_file:
            notifier.play_alert(alert)
