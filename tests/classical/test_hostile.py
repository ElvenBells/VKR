import pytest
from playwright.sync_api import Page, expect

def test_hostile_canvas_and_animations(page: Page, base_url: str):
    """
    Сценарий: Клик по кнопке с текстом 'CONFIRM' (рандомный ID), 
    взаимодействие с Canvas (через координаты) и анимацией.
    """
    page.goto(f"{base_url}/hostile.html")
    
    # 1. Поиск кнопки по тексту, так как ID рандомны
    # Это работает, но медленно и зависит от структуры DOM
    confirm_btn = page.get_by_text("CONFIRM")
    expect(confirm_btn).to_be_visible()
    confirm_btn.click()
    
    # 2. Canvas: Классический PW не видит элементы внутри canvas.
    # Приходится использовать координаты (хрупко при ресайзе)
    # Кликаем примерно в центр первого столбца графика (Q1)
    # Координаты жестко заданы в HTML, но в реальности это риск
    canvas = page.locator("#chartCanvas")
    box = canvas.bounding_box()
    if box:
        # Клик в точку (x=35, y=150) относительно канваса
        page.mouse.click(box['x'] + 35, box['y'] + 150)
    
    # 3. Анимация: Клик по красному кругу
    # Селектор по title или классу, если они стабильны
    animated_icon = page.locator(".animated-icon")
    # Playwright автоматически ожидает stabilization перед кликом (actionability check)
    animated_icon.click()
    
    # Валидация лога
    log_entry = page.locator("#log")
    expect(log_entry).to_contain_text("Icon Clicked", timeout=5000)