"""
Debugging Agent implementation.
"""
from typing import Any, Dict, Optional
from .base import DevAgent

class DebuggingAgent(DevAgent):
    def __init__(self, provider: str = "openai", model_config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("Debugging", provider, model_config)

    def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        code = context.get("code", "")
        error = context.get("error", "")
        
        system_prompt = (
            "You are an expert Debugger. "
            "Analyze the code and the error message provided. "
            "Identify the root cause and provide a fixed version of the code. "
            "Explain the fix briefly."
        )
        
        user_input = f"Code:\n{code}\n\nError:\n{error}\n\nTask: {task}"
        
        response = self._call_llm(system_prompt, user_input)
        
        return {
            "status": "success",
            "analysis": response,
            "agent": "DebuggingAgent"
        }
