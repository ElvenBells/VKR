import os
import json
import base64
from typing import Optional, List, Dict
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from langchain_core.messages import HumanMessageContentPart

class LLMPlanner:
    def __init__(self, model_name: str = "gpt-4o", api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found")
            
        self.llm = ChatOpenAI(model=model_name, temperature=0.0, api_key=self.api_key)

    def _encode_image(self, image_np) -> str:
        from PIL import Image
        import io
        img = Image.fromarray(image_np)
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def plan_action(self, task: str, screen_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Отправляет скриншот и задачу в LLM, получает план действия.
        screen_data: результат из CVEngine.analyze_screen
        """
        base64_img = self._encode_image(screen_data["raw_image"])
        
        # Формируем промпт с контекстом
        # Мы передаем не только картинку, но и JSON с найденными элементами для точности
        elements_json = json.dumps(screen_data["elements"], indent=2)
        
        prompt_text = f"""
        You are an AI QA Agent. Your task is to interact with a website based on a screenshot and detected elements.
        
        CURRENT TASK: "{task}"
        
        DETECTED ELEMENTS (Text & UI Components):
        {elements_json}
        
        IMAGE DIMENSIONS: {screen_data['width']}x{screen_data['height']}
        
        INSTRUCTIONS:
        1. Analyze the visual layout and the list of elements.
        2. Decide the NEXT SINGLE ACTION required to progress towards the task.
        3. If the task requires clicking a button, identify its coordinates (center of the element).
        4. If the task requires typing, identify the input field coordinates.
        5. Return a JSON object with the following structure ONLY:
        {{
            "action": "click" | "type" | "scroll" | "wait" | "complete",
            "target_element_description": "Brief description of what you are targeting",
            "coordinates": [x, y], // Center coordinates for click/type
            "text_value": "string", // Only for 'type' action
            "reasoning": "Why you chose this action"
        }}
        
        If the task is already completed based on the screen, set action to "complete".
        """

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}", "detail": "low"}}
            ]
        )
        
        response = self.llm.invoke([message])
        content = response.content
        
        # Парсинг JSON из ответа (LLM иногда добавляет маркдаун)
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            return json.loads(content.strip())
        except json.JSONDecodeError:
            # Fallback или выброс ошибки
            return {"action": "error", "reasoning": f"Failed to parse LLM response: {content}"}