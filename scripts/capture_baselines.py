#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт генерации эталонных скриншотов для 5 прототипов.
Запуск: python scripts/capture_baselines.py
Требует: запущенного локального сервера с прототипами (порт 8080)
"""

from playwright.sync_api import sync_playwright
import os
from pathlib import Path

def main():
    # === 1. Определяем корень проекта (независимо от точки запуска) ===
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    BASELINES_DIR = PROJECT_ROOT / "baselines"
    BASELINES_DIR.mkdir(exist_ok=True)
    
    # === 2. Параметры ===
    SITES = ["ecommerce", "dashboard", "crm", "admin", "booking"]
    BASE_URL = "http://localhost:8080"
    VIEWPORT = {"width": 1280, "height": 720}
    
    # === 3. Запуск Playwright ===
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT)
        
        for site in SITES:
            url = f"{BASE_URL}/{site}.html"
            print(f"[→] Загрузка: {url}")
            
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(1000)  # стабилизация рендеринга
            
            output_path = BASELINES_DIR / f"{site}_baseline.png"
            page.screenshot(path=str(output_path), full_page=True)
            print(f"[+] Сохранено: {output_path}")
        
        browser.close()
    
    print("\n✅ Все базлайны сгенерированы.")

if __name__ == "__main__":
    main()