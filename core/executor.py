import time
from playwright.sync_api import Page
from .cv_engine import CVEngine
from .llm_planner import LLMPlanner

class VisionExecutor:
    def __init__(self, page: Page, max_retries: int = 3):
        self.page = page
        self.cv_engine = CVEngine()
        self.planner = LLMPlanner()
        self.max_retries = max_retries

    def execute_task(self, task_description: str, max_steps: int = 10):
        """
        Главный цикл: Скриншот -> Анализ -> План -> Действие -> Валидация
        """
        print(f"🚀 Starting Vision Task: '{task_description}'")
        
        for step in range(max_steps):
            print(f"\n--- Step {step + 1} ---")
            
            # 1. Захват экрана
            screenshot = self.page.screenshot(full_page=True)
            
            # 2. Анализ CV
            screen_data = self.cv_engine.analyze_screen(screenshot)
            print(f"Detected {len(screen_data['elements'])} elements.")
            
            # 3. Планирование LLM
            plan = self.planner.plan_action(task_description, screen_data)
            print(f"LLM Plan: {plan.get('action')} -> {plan.get('target_element_description')}")
            
            action = plan.get("action")
            
            if action == "complete":
                print("✅ Task completed successfully.")
                return True
            
            if action == "error":
                print(f"⚠️ LLM Error: {plan.get('reasoning')}")
                return False

            # 4. Выполнение действия
            try:
                coords = plan.get("coordinates")
                if not coords:
                    raise ValueError("No coordinates provided by LLM")
                
                x, y = coords
                
                if action == "click":
                    # Эмуляция клика мышью по координатам
                    self.page.mouse.click(x, y)
                    print(f"🖱️ Clicked at ({x}, {y})")
                    
                elif action == "type":
                    text = plan.get("text_value", "")
                    # Сначала клик в поле, потом ввод
                    self.page.mouse.click(x, y)
                    self.page.keyboard.type(text)
                    print(f"⌨️ Typed '{text}' at ({x}, {y})")
                    
                elif action == "scroll":
                    self.page.evaluate(f"window.scrollBy(0, {coords[1]})")
                    
                # Небольшая пауза для рендеринга изменений
                time.sleep(1.0) 
                
            except Exception as e:
                print(f"❌ Execution error: {e}")
                # Здесь можно реализовать логику ретраев
                continue

        print("⏰ Max steps reached without completion.")
        return False