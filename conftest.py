import pytest
from playwright.sync_api import sync_playwright
import allure

@pytest.fixture(scope="session")
def browser_context_args():
    return {"viewport": {"width": 1280, "height": 720}}

@pytest.fixture(scope="function")
def page(browser_context_args):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) # Headless для CI, False для отладки
        context = browser.new_context(**browser_context_args)
        page = context.new_page()
        
        # Включаем сбор видео для отчетов Allure
        page.context.tracing.start(screenshots=True, snapshots=True, sources=True)
        
        yield page
        
        # Сохранение трейса при падении теста (упрощенно)
        page.context.tracing.stop(path="trace.zip")
        browser.close()