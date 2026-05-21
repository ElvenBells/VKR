import cv2
import numpy as np
import easyocr
from PIL import Image
import io
from typing import List, Dict, Any
from ultralytics import YOLO

# Инициализация моделей (Singleton pattern recommended for production)
# EasyOCR загружает модели при первом запуске
ocr_reader = easyocr.Reader(['en'], gpu=False) # gpu=True для продакшена
# YOLOv8 для детекции UI элементов (требуется дообученная модель, здесь используем предтренированную как пример)
# В реальном проекте нужна модель, обученная на датасете UI (напр., RICO или собственном)
try:
    ui_detector = YOLO('yolov8n.pt') # Заглушка, в реальности нужна модель на кнопки/инпуты
except Exception:
    ui_detector = None

class CVEngine:
    def __init__(self):
        self.reader = ocr_reader
        self.detector = ui_detector

    def preprocess_image(self, image_np: np.ndarray) -> np.ndarray:
        """
        Улучшение изображения для лучшего распознавания:
        - Конвертация в оттенки серого (для OCR)
        - Повышение контраста (CLAHE)
        - Шумоподавление
        """
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        
        # Применяем CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Легкое размытие для удаления шума
        denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
        
        return denoised

    def analyze_screen(self, screenshot_bytes: bytes) -> Dict[str, Any]:
        """
        Полный анализ экрана: OCR + Детекция объектов.
        Возвращает структурированное описание UI.
        """
        # Конвертация байтов в numpy array (RGB)
        image = Image.open(io.BytesIO(screenshot_bytes)).convert('RGB')
        image_np = np.array(image)
        
        # 1. OCR (Распознавание текста и координат)
        # easyocr возвращает: [(bbox), text, confidence]
        ocr_results = self.reader.readtext(image_np, detail=1, paragraph=False)
        
        text_elements = []
        for bbox, text, conf in ocr_results:
            if conf > 0.5: # Фильтр низких уверенностей
                # bbox: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                points = np.array(bbox, dtype=np.int32)
                x_min, y_min = np.min(points[:, 0]), np.min(points[:, 1])
                x_max, y_max = np.max(points[:, 0]), np.max(points[:, 1])
                
                text_elements.append({
                    "type": "text",
                    "content": text,
                    "bbox": [x_min, y_min, x_max, y_max],
                    "center": ((x_min + x_max) // 2, (y_min + y_max) // 2),
                    "confidence": conf
                })

        # 2. Object Detection (Поиск кнопок, инпутов, иконок)
        # Примечание: YOLOv8 coco dataset не идеален для UI, но покажет принцип
        ui_elements = []
        if self.detector:
            results = self.detector(image_np, verbose=False)
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    # Фильтруем только релевантные классы (если бы модель была специализирована)
                    # Для примера берем все с высокой уверенностью
                    if box.conf[0] > 0.6:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cls_id = int(box.cls[0])
                        cls_name = r.names[cls_id]
                        
                        # Маппинг классов COCO на UI (примерный):
                        # cell phone -> mobile UI? remote -> button? 
                        # В реальности тут будет класс 'button', 'input_field'
                        ui_elements.append({
                            "type": "ui_component",
                            "label": cls_name, # Например 'remote', 'cell phone'
                            "bbox": [x1, y1, x2, y2],
                            "center": ((x1 + x2) // 2, (y1 + y2) // 2),
                            "confidence": float(box.conf[0])
                        })

        return {
            "width": image.width,
            "height": image.height,
            "elements": text_elements + ui_elements,
            "raw_image": image_np
        }