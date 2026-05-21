import pytest
from playwright.sync_api import Page, expect, TimeoutError

def test_login_flow(page: Page, base_url: str):
    """
    Сценарий: Ввод данных в форму логина и проверка успеха.
    """
    page.goto(f"{base_url}/basic.html")
    
    # Явные ожидания видимости элементов
    username_input = page.locator("#username")
    password_input = page.locator("#password")
    login_btn = page.locator("#login-btn")
    
    expect(username_input).to_be_visible()
    
    # Действия
    username_input.fill("test_user")
    password_input.fill("secret_password")
    login_btn.click()
    
    # Валидация результата
    result_div = page.locator("#result")
    expect(result_div).to_be_visible(timeout=5000)
    
    user_display = page.locator("#user-display")
    expect(user_display).to_have_text("test_user")