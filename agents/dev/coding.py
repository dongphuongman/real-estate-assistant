"""
Coding Agent implementation.
"""
from typing import Any, Dict, Optional
from .base import DevAgent

class CodingAgent(DevAgent):
    def __init__(self, provider: str = "openai", model_config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("Coding", provider, model_config)

    def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        existing_code = context.get("existing_code", "")
        
        system_prompt = (
            "You are an expert Software Engineer. "
            "Your task is to write clean, efficient, and well-documented Python code. "
            "Follow these rules:\n"
            "1. Use type hints.\n"
            "2. Include docstrings.\n"
            "3. Handle errors gracefully.\n"
            "4. Do not include markdown formatting like ```python in the output unless asked."
        )
        
        user_input = f"Task: {task}\n\nContext/Existing Code:\n{existing_code}"
        
        code = self._call_llm(system_prompt, user_input)
        
        return {
            "status": "success",
            "code": code,
            "agent": "CodingAgent"
        }
