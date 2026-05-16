#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOM-базлайн для сравнительного анализа гибридного CV-подхода
Запуск: python dom_baseline.py
Требует: запущенного сервера с прототипами (порт 8080)
"""

import sys
import os
import time
import pandas as pd
from pathlib import Path
from playwright.sync_api import sync_playwright

# === 1. ПРОВЕРКА ИМПОРТОВ ===
print("[DEBUG] Проверка импортов...")
try:
    import pandas as pd
    print("  ✓ pandas импортирован")
except ImportError as e:
    print(f"  ✗ Ошибка импорта pandas: {e}")
    print("  Решение: pip install pandas")
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright
    print("  ✓ playwright.sync_api импортирован")
except ImportError as e:
    print(f"  ✗ Ошибка импорта playwright: {e}")
    print("  Решение: pip install playwright && playwright install chromium")
    sys.exit(1)

# === 2. КОНФИГУРАЦИЯ ===
print("[DEBUG] Инициализация конфигурации...")

SITES = ["ecommerce", "dashboard", "crm", "admin", "booking"]
N_RUNS = 3  # Уменьшено для быстрого тестирования



DOM_LOCATORS = {
    "ecommerce": [
        "div.container > section:nth-child(2) > div:nth-child(1) > div.card-body > h4:first-child",  # 5 уровней вложенности + позиция
        "div.card-body > button.add-btn:nth-of-type(1):not([disabled])",                             # Класс + тип + псевдо-селектор
        "aside.filters > div:nth-child(2) > select:nth-of-type(1) > option:checked",                 # Зависит от выбранного option
        "div.product-grid > article:nth-child(1) > div.card-body > h4.card-title:first-child",       # Позиция карточки + теги
        "header > div:last-child > span:last-child > span:nth-child(1)"                              # Глубокая навигация по последним элементам
    ],
    "dashboard": [
        "div.kpi-grid > article:first-child > div:nth-child(2) > div.kpi-value",                     # Позиция KPI + вложенность
        "div.table-container > table > thead > tr > th:nth-child(3)",                                # Зависит от порядка колонок
        "svg.chart > g:last-child > path:nth-of-type(1)[stroke]",                                    # Зависит от структуры SVG
        "tbody > tr:first-child > td:nth-child(4) > span.status-badge:first-child",                  # Позиция строки + ячейки + бейджа
        "header > div.header-controls > select#period-filter:nth-of-type(1) > option[selected]"      # Атрибут + позиция + выбранное значение
    ],
    "crm": [
        "table#contact-table > tbody > tr:nth-child(1) > td:nth-child(1) > div.contact-info",        # ID таблицы + позиция строки/ячейки
        "td:nth-child(3) > span[class^='badge-']:first-of-type",                                     # Префикс класса + псевдо-селектор
        "form#contact-form > div:nth-child(1) > input.form-input:first-of-type:not([readonly])",     # ID формы + позиция + атрибут
        "div[role='dialog'] > div.modal-card > div.modal-header > h2:first-child",                   # ARIA-роль + структура модалки
        "header > div.controls > input#search-input[placeholder='Поиск...']:first-of-type"          # Точное значение placeholder
    ],
    "admin": [
        "aside#sidebar > ul.nav-list > li:nth-child(1) > span.nav-icon:first-child",                # ID сайдбара + позиция + иконка
        "table#user-table > tbody > tr:nth-child(1) > td:nth-child(2)",                             # ID таблицы + позиция ячейки
        "td:last-child > div.action-cell > button:nth-child(1)[data-tooltip]:not([disabled])",      # Атрибут + псевдо-селектор + позиция
        "tr:nth-child(2) > td:nth-child(4) > span.status-badge:nth-of-type(1)[class*='active']",    # Позиция + частичное совпадение класса
        "header > div.header-actions > button#theme-toggle:first-of-type > span:first-child"        # ID кнопки + вложенность
    ],
    "booking": [
        "div.calendar-grid > div:nth-child(10):not(.empty):not(.disabled)",                         # Позиция дня + исключения
        "form#booking-form > div:nth-child(2) > input.form-input:first-of-type[required]",          # ID формы + атрибут required
        "nav#stepper-nav > div:nth-child(2) > div.step-circle:first-child",                         # ID навигации + позиция шага
        "div.actions > button.btn-primary:last-of-type:not([disabled]):not([hidden])",              # Множественные псевдо-селекторы
        "div.card > div:last-child > span:last-child > span:nth-child(1)"                           # Глубокая вложенность по последним элементам
    ]
}


# DOM_LOCATORS = {
#     "ecommerce": [
#         "div.container > section:nth-child(2) > div",           # Ломается при добавлении обёртки (mutateDOM)
#         "div.card-body > button[class='add-btn']",             # Ломается при удалении класса (mutateDOM)
#         "aside.filters > div:nth-child(2) > select",           # Позиционный, ломается при изменении структуры фильтров
#         "div.card-body > h4",                                  # Ломается, если тег h4 заменён на p/div (mutateDOM)
#         "header > div:last-child > span:last-child"            # Хрупкая навигация по DOM-дереву
#     ],
#     "dashboard": [
#         "div.kpi-grid > article:first-child > div:nth-child(2)", # Позиционный, ломается при рефакторинге KPI
#         "div.table-container thead th:nth-child(3)",            # Ломается при изменении заголовков таблицы
#         "svg.chart > g:last-child > path",                      # Зависит от структуры SVG, ломается при перерисовке
#         "tbody tr:first-child td:nth-child(4) span",            # Хрупкий, ломается при сортировке/изменении строк
#         "header select:nth-of-type(1)"                         # Ломается при изменении порядка элементов в шапке
#     ],
#     "crm": [
#         "table tbody tr:nth-child(1)",                         # Ломается при фильтрации/добавлении строк
#         "td:nth-child(3) span[class^='badge-']",               # Ломается при изменении префикса класса (mutateSemantic)
#         "form > div:nth-child(1) input",                       # Позиционный, ломается при изменении порядка полей
#         "div[role='dialog'] > div > form",                     # Зависит от структуры модалки, ломается при mutateDOM
#         "header input[placeholder]"                            # Ломается, если атрибут placeholder удалён/изменён
#     ],
#     "admin": [
#         "aside > ul > li:nth-child(1)",                        # Ломается при изменении структуры сайдбара
#         "table tbody > tr:nth-child(1)",                       # Позиционный, ломается при CRUD-операциях
#         "td:last-child > button:nth-child(1)",                 # Хрупкий, ломается при изменении ячеек действий
#         "tr:nth-child(2) td:nth-child(4) span",                # Ломается при изменении таблицы/сортировке
#         "header button:first-child"                            # Ломается при добавлении/удалении кнопок в шапке
#     ],
#     "booking": [
#         "div.calendar-grid > div:nth-child(10)",               # Позиционный день, ломается при смене месяца/структуры
#         "form > div:nth-child(2) input",                       # Ломается при изменении порядка полей формы
#         "nav > div:nth-child(2)",                              # Зависит от порядка шагов, ломается при mutateDOM
#         "div.actions > button:last-child",                     # Ломается при добавлении/удалении кнопок
#         "div.card > div:last-child span"                       # Хрупкий, ломается при изменении структуры карточки
#     ]
# }


# # Селекторы, точно соответствующие вашим синтетическим прототипам
# DOM_LOCATORS = {
#     "ecommerce": [
#         "[data-testid='product-card']",
#         "[data-testid='add-btn']",
#         ".dropdown",
#         "[data-testid='card-title']",
#         "[data-testid='cart-counter']"
#     ],
#     "dashboard": [
#         "[data-testid='kpi-card-revenue']",
#         ".data-table th",
#         ".chart-line",
#         ".status-badge",
#         "#period-filter"
#     ],
#     "crm": [
#         "[data-testid='contact-row']",
#         ".badge",
#         ".form-input",
#         "[data-testid='contact-modal']",
#         "#search-input"
#     ],
#     "admin": [
#         "[data-testid='sidebar-nav']",
#         "[data-testid='user-row']",
#         ".action-btn",
#         ".status-badge",
#         "#theme-toggle"
#     ],
#     "booking": [
#         ".cal-day",
#         ".form-input",
#         "[data-testid='stepper-navigation']",
#         ".btn-primary",
#         "[data-testid='status-message']"
#     ]
# }

DEFECT_MAP = {
    "ecommerce": ["mutateDOM", "mutateCSS", "mutateText"],
    "dashboard": ["mutateDOM", "mutateCSS", "mutateText"],
    "crm":       ["mutateSemantic", "mutateContrast", "mutateValidation"],
    "admin":     ["mutateDOM", "mutateThemeVars", "mutateTooltips"],
    "booking":   ["mutateDOM", "mutateState", "mutateAnimation", "mutateOCR"]
}

# === 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def calculate_metrics(detected_count, expected_count):
    """Расчёт метрик для DOM-подхода"""
    tp = min(detected_count, expected_count)
    fp = max(0, detected_count - expected_count)
    fn = max(0, expected_count - detected_count)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    fpr = fp / (fp + tp) if (fp + tp) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    coverage = recall
    
    return tp, fp, fn, round(precision, 4), round(recall, 4), round(fpr, 4), round(fnr, 4), round(coverage, 4)

# === 4. ОСНОВНАЯ ФУНКЦИЯ ===
def run_dom_baseline():
    print("\n[DOM] === ЗАПУСК DOM-БАЗЛАЙНА ===")
    all_results = []
    
    # Запуск Playwright
    print("[DOM] Инициализация Playwright...")
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
                print(f"\n[DOM] >>> Сайт: {site}")
                
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
                            
                            # Подсчёт найденных элементов через DOM-локаторы
                            t0 = time.time()
                            detected = 0
                            for loc in DOM_LOCATORS[site]:
                                try:
                                    count = page.locator(loc).count()
                                    detected += count
                                    if count > 0:
                                        print(f"    ├─ Найдено '{loc}': {count} шт.")
                                except Exception as e:
                                    print(f"    ├─ Ошибка при поиске '{loc}': {e}")
                                    pass
                            exec_time = time.time() - t0
                            
                            # Расчёт метрик
                            expected = len(DOM_LOCATORS[site])
                            tp, fp, fn, prec, rec, fpr, fnr, cov = calculate_metrics(detected, expected)
                            
                            # Сохранение результата
                            all_results.append({
                                "approach": "DOM_Baseline",
                                "site": site,
                                "defect_type": defect,
                                "run": run + 1,
                                "tp": tp, "fp": fp, "fn": fn,
                                "precision": prec, "recall": rec,
                                "fpr": fpr, "fnr": fnr, "coverage": cov,
                                "exec_time_ms": round(exec_time * 1000, 2),
                                "detected_count": detected,
                                "expected_count": expected
                            })
                            
                            print(f"    └─ {defect}: Detected={detected}/{expected}, Coverage={cov:.2%}, Time={exec_time*1000:.0f}ms")
                            
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
    print(f"\n[DOM] Сохранение результатов ({len(all_results)} записей)...")
    os.makedirs("results", exist_ok=True)
    
    if all_results:
        df = pd.DataFrame(all_results)
        output_path = "results/dom_metrics.csv"
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"[✅] Результаты сохранены: {output_path}")
        
        # Сводная статистика
        print("\n[DOM] Сводная статистика по подходам:")
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
    print("DOM-BASELINE FOR COMPARATIVE ANALYSIS")
    print("=" * 70)
    
    try:
        result = run_dom_baseline()
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