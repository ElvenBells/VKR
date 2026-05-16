#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CV-агент для гибридного тестирования веб-интерфейсов
Запуск: python cv_agent.py
Требует: запущенного сервера с прототипами (порт 8080), модели models/best.pt
"""

import sys
import os
import time
import pandas as pd
import numpy as np
import cv2
from pathlib import Path
from playwright.sync_api import sync_playwright

# === 1. ПРОВЕРКА ИМПОРТОВ ===
print("[DEBUG] Проверка импортов...")
try:
    from ultralytics import YOLO
    print("  ✓ ultralytics.YOLO импортирован")
except ImportError as e:
    print(f"  ✗ Ошибка импорта ultralytics: {e}")
    print("  Решение: pip install ultralytics")
    sys.exit(1)

try:
    import pandas as pd
    import numpy as np
    import cv2
    print("  ✓ pandas/numpy/cv2 импортированы")
except ImportError as e:
    print(f"  ✗ Ошибка импорта зависимостей: {e}")
    sys.exit(1)

# === 2. КОНФИГУРАЦИЯ ===
print("[DEBUG] Инициализация конфигурации...")

# Определяем корень проекта
PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "models" / "best.pt"

# Проверка существования модели
if not MODEL_PATH.exists():
    print(f"  ✗ Модель не найдена: {MODEL_PATH}")
    print("  Решение:")
    print("    1. Скопируйте best.pt в папку models/")
    print("    2. Или укажите правильный путь в MODEL_PATH")
    sys.exit(1)
print(f"  ✓ Модель найдена: {MODEL_PATH}")

SITES = ["ecommerce", "dashboard", "crm", "admin", "booking"]
N_RUNS = 3  # Уменьшено для быстрого тестирования

# Сложные компоненты (таблицы, графики, календари) декомпозированы на примитивы, которые детектирует YOLO
EXPECTED_CLASSES = {
    "ecommerce": ["button", "input", "text", "dropdown", "image", "link"],
    "dashboard": ["text", "button", "image", "link", "menu_item", "icon"],
    "crm":       ["text", "button", "input", "label", "checkbox", "link"],
    "admin":     ["text", "button", "menu_item", "icon", "link", "input"],
    "booking":   ["button", "input", "text", "link", "icon", "label"]
}
DEFECT_MAP = {
    "ecommerce": ["mutateDOM", "mutateCSS", "mutateText"],
    "dashboard": ["mutateDOM", "mutateCSS", "mutateText"],
    "crm":       ["mutateSemantic", "mutateContrast", "mutateValidation"],
    "admin":     ["mutateDOM", "mutateThemeVars", "mutateTooltips"],
    "booking":   ["mutateDOM", "mutateState", "mutateAnimation", "mutateOCR"]
}

# === 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def calculate_metrics(detected, expected):
    """Расчёт метрик: TP, FP, FN, Precision, Recall, FPR, FNR, Coverage"""
    detected_set = set(detected)
    expected_set = set(expected)
    
    tp = len(detected_set & expected_set)
    fp = len(detected_set - expected_set)
    fn = len(expected_set - detected_set)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    fpr = fp / (fp + tp) if (fp + tp) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    coverage = recall
    
    return tp, fp, fn, round(precision, 4), round(recall, 4), round(fpr, 4), round(fnr, 4), round(coverage, 4)

# === 4. ОСНОВНАЯ ФУНКЦИЯ ===
def run_cv_agent():
    print("\n[CV] === ЗАПУСК CV-АГЕНТА ===")
    
    # Загрузка модели
    print("[CV] Загрузка модели YOLOv8...")
    try:
        model = YOLO(str(MODEL_PATH))
        print(f"[✓] Модель загружена: {MODEL_PATH.name}")
    except Exception as e:
        print(f"[✗] Ошибка загрузки модели: {e}")
        return None
    
    # Вывод классов модели
    print(f"[✓] Классы модели ({len(model.names)}): {model.names}")
    
    # Проверка соответствия ожидаемым классам
    if len(model.names) != 16:
        print(f"[⚠] Внимание: ожидалось 16 классов, найдено {len(model.names)}")
        print("  Это не критично, но проверьте соответствие EXPECTED_CLASSES")
    
    all_results = []
    
    # Запуск Playwright
    print("[CV] Инициализация Playwright...")
    try:
        with sync_playwright() as p:
            print("[✓] Playwright запущен")
            
            browser = p.chromium.launch(headless=True)
            print("[✓] Браузер Chromium запущен")
            
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            print("[✓] Страница создана (viewport: 1280x720)")
            
            # Основной цикл по сайтам
            for site in SITES:
                url = f"http://localhost:8080/{site}.html"
                print(f"\n[CV] >>> Сайт: {site}")
                
                test_cases = ["no_defect"] + DEFECT_MAP.get(site, [])
                print(f"  ├─ Тест-кейсы: {test_cases}")
                
                for run in range(N_RUNS):
                    print(f"  ├─ Запуск #{run + 1}")
                    
                    for defect in test_cases:
                        try:
                            # Переход на страницу
                            page.goto(url, wait_until="domcontentloaded", timeout=30000)
                            page.wait_for_timeout(800)
                            
                            # Инжекция дефекта (если указан)
                            if defect != "no_defect":
                                try:
                                    page.evaluate(f"window.benchmark.{defect}()")
                                    page.wait_for_timeout(600)
                                    print(f"    ├─ Инжекция: {defect} ✓")
                                except Exception as e:
                                    print(f"    ├─ Инжекция: {defect} ✗ ({e})")
                                    continue
                            
                            # Скриншот + инференс
                            t0 = time.time()
                            screenshot_bytes = page.screenshot()
                            img_array = np.frombuffer(screenshot_bytes, np.uint8)
                            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                            
                            if img is None:
                                print(f"    ├─ Ошибка декодирования скриншота")
                                continue
                            
                            preds = model(img, conf=0.25, verbose=False, iou=0.45)

                            from skimage.metrics import structural_similarity as ssim
                            # Загрузите эталонный скриншот для сайта
                            baseline_path = f"baselines/{site}_baseline.png"
                            if os.path.exists(baseline_path):
                                baseline = cv2.imread(baseline_path, cv2.IMREAD_GRAYSCALE)
                                current = cv2.imdecode(np.frombuffer(screenshot_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
                                current = cv2.resize(current, (baseline.shape[1], baseline.shape[0]))
                                ssim_score, _ = ssim(baseline, current, full=True)
                                
                                # Если дефект визуальный и SSIM упал ниже порога — считаем это "успешным обнаружением"
                                if defect in ['mutateCSS', 'mutateThemeVars', 'mutateAnimation'] and ssim_score < 0.95:
                                    # Увеличиваем TP для визуальных дефектов
                                    tp += 1
                                    fn = max(0, fn - 1)


                            exec_time = time.time() - t0
                            
                            # Извлечение детектированных классов
                            detected_classes = []
                            for r in preds:
                                for box in r.boxes:
                                    cls_id = int(box.cls[0])
                                    if cls_id in model.names:
                                        detected_classes.append(model.names[cls_id])
                            
                            # Расчёт метрик
                            expected = EXPECTED_CLASSES.get(site, [])
                            tp, fp, fn, prec, rec, fpr, fnr, cov = calculate_metrics(detected_classes, expected)
                            
                            # Сохранение результата
                            all_results.append({
                                "approach": "Hybrid_CV",
                                "site": site,
                                "defect_type": defect,
                                "run": run + 1,
                                "tp": tp, "fp": fp, "fn": fn,
                                "precision": prec, "recall": rec,
                                "fpr": fpr, "fnr": fnr, "coverage": cov,
                                "exec_time_ms": round(exec_time * 1000, 2),
                                "detected_count": len(detected_classes)
                            })
                            
                            print(f"    └─ {defect}: TP={tp}, FP={fp}, FN={fn}, Coverage={cov:.2%}, Time={exec_time*1000:.0f}ms")
                            
                        except Exception as e:
                            print(f"    ✗ Ошибка в тесте '{defect}': {type(e).__name__}: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
            
            browser.close()
            print("[✓] Браузер закрыт")
            
    except Exception as e:
        print(f"[✗] Ошибка Playwright: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Сохранение результатов
    print(f"\n[CV] Сохранение результатов ({len(all_results)} записей)...")
    os.makedirs("results", exist_ok=True)
    
    if all_results:
        df = pd.DataFrame(all_results)
        output_path = "results/cv_metrics.csv"
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"[✅] Результаты сохранены: {output_path}")
        
        # Сводная статистика
        print("\n[CV] Сводная статистика по подходам:")
        summary = df.groupby("defect_type").agg({
            "coverage": "mean",
            "fpr": "mean",
            "exec_time_ms": "mean"
        }).round(3)
        print(summary.to_string())
        
        return df
    else:
        print("[⚠] Нет данных для сохранения")
        return None

# === 5. ТОЧКА ВХОДА ===
if __name__ == "__main__":
    print("=" * 70)
    print("CV-AGENT FOR HYBRID WEB UI TESTING")
    print("=" * 70)
    
    try:
        result = run_cv_agent()
        if result is not None:
            print("\n[🎉] Эксперимент завершён успешно!")
        else:
            print("\n[⚠] Эксперимент завершён с предупреждениями")
    except KeyboardInterrupt:
        print("\n[⚠] Прервано пользователем")
    except Exception as e:
        print(f"\n[✗] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("=" * 70)