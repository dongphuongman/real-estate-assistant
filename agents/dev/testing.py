"""
Testing Agent implementation.
"""
from typing import Any, Dict, Optional

from .base import DevAgent


class TestingAgent(DevAgent):
    def __init__(self, provider: str = "openai", model_config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("Testing", provider, model_config)

    def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        code = context.get("code", "")
        
        system_prompt = (
            "You are a QA Engineer. "
            "Write comprehensive unit tests for the provided code using 'pytest'. "
            "Cover edge cases and happy paths."
        )
        
        user_input = f"Code to test:\n{code}\n\nTask: {task}"
        
        tests = self._call_llm(system_prompt, user_input)
        
        return {
            "status": "success",
            "tests": tests,
            "agent": "TestingAgent"
        }
