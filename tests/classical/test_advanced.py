import pytest
from playwright.sync_api import Page, expect

def test_shadow_dom_and_modal(page: Page, base_url: str):
    """
    Сценарий: Работа с Shadow DOM, подгрузка списка, модальное окно.
    """
    page.goto(f"{base_url}/advanced.html")
    
    # 1. Shadow DOM: доступ через evaluate или locator с pierce
    # Playwright автоматически проникает в Shadow DOM при использовании locator
    shadow_btn = page.locator("custom-widget").locator("#shadow-btn")
    expect(shadow_btn).to_have_text("Click Inside Shadow")
    
    # 2. Dynamic List: Ожидание появления элементов после клика
    load_btn = page.locator("#load-more")
    initial_count = page.locator("#dynamic-list li").count()
    
    load_btn.click()
    
    # Ожидание увеличения количества элементов
    expect(page.locator("#dynamic-list li")).to_have_count(initial_count + 5, timeout=5000)
    
    # 3. Modal Window
    modal_trigger = page.locator("#open-modal")
    modal_overlay = page.locator(".modal-overlay")
    close_btn = page.locator(".close-btn")
    
    modal_trigger.click()
    expect(modal_overlay).to_be_visible()
    
    # Взаимодействие внутри модалки
    checkbox = page.locator('input[type="checkbox"]')
    checkbox.uncheck()
    
    save_btn = page.locator(".modal button", has_text="Save")
    save_btn.click()
    
    expect(modal_overlay).to_be_hidden()