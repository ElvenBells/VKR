import os
import csv
from playwright.sync_api import sync_playwright
from skimage.metrics import structural_similarity as ssim
import cv2

# === КОНФИГУРАЦИЯ ===
# Каждый сайт имеет свой набор методов window.benchmark
SITE_DEFECTS = {
    "ecommerce": ["mutateDOM", "mutateCSS", "mutateText"],
    "dashboard": ["mutateDOM", "mutateCSS", "mutateText"],
    "crm":       ["mutateSemantic", "mutateContrast", "mutateValidation"],
    "admin":     ["mutateDOM", "mutateThemeVars", "mutateTooltips"],
    "booking":   ["mutateDOM", "mutateState", "mutateAnimation", "mutateOCR"]
}

BASE_URL = "http://localhost:8080"
VIEWPORT = {"width": 1280, "height": 720}
BASELINES_DIR = "baselines"
SCREENSHOTS_DIR = "screenshots"
RESULTS_FILE = "results/defect_metrics.csv"

# Создаём директории
os.makedirs(BASELINES_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs("results", exist_ok=True)

def calculate_ssim(baseline_path, defect_path):
    """Расчёт SSIM между эталоном и скриншотом с дефектом"""
    img1 = cv2.imread(baseline_path, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(defect_path, cv2.IMREAD_GRAYSCALE)
    if img1 is None or img2 is None:
        return 0.0
    # Приводим к одинаковому размеру
    img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
    score, _ = ssim(img1, img2, full=True)
    return round(score, 4)

def main():
    print("[INFO] Запуск экспериментального прогона дефектов...")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT)

        for site, defects in SITE_DEFECTS.items():
            baseline_path = os.path.join(BASELINES_DIR, f"{site}_baseline.png")
            if not os.path.exists(baseline_path):
                print(f"[️] Базлайн для '{site}' не найден. Пропускаю.")
                continue

            print(f"\n[→] Обработка сайта: {site}")
            url = f"{BASE_URL}/{site}.html"
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(800)  # Стабилизация рендеринга

            for defect in defects:
                try:
                    print(f"  ├─ Инжекция: {defect}")
                    
                    # Применяем дефект через JS-хук
                    page.evaluate(f"window.benchmark.{defect}()")
                    page.wait_for_timeout(600)  # Ждём отрисовку изменений

                    defect_path = os.path.join(SCREENSHOTS_DIR, f"{site}_{defect}.png")
                    page.screenshot(path=defect_path, full_page=True)

                    # Считаем метрику
                    ssim_val = calculate_ssim(baseline_path, defect_path)
                    print(f"  └─ SSIM: {ssim_val}")

                    results.append({
                        "site": site,
                        "defect_type": defect,
                        "ssim_score": ssim_val,
                        "baseline": baseline_path,
                        "defect_screenshot": defect_path
                    })
                except Exception as e:
                    print(f"  └─ ❌ Ошибка: {e}")
                    results.append({
                        "site": site,
                        "defect_type": defect,
                        "ssim_score": "ERROR",
                        "baseline": baseline_path,
                        "defect_screenshot": None
                    })

            # Сбрасываем страницу к чистому состоянию перед следующим сайтом
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(500)

        browser.close()

    # Сохраняем результаты в CSV
    with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["site", "defect_type", "ssim_score", "baseline", "defect_screenshot"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[✅] Эксперимент завершён. Таблица метрик: {RESULTS_FILE}")

if __name__ == "__main__":
    main()