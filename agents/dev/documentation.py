"""
Documentation Agent implementation.
"""
from typing import Any, Dict, Optional
from .base import DevAgent

class DocumentationAgent(DevAgent):
    def __init__(self, provider: str = "openai", model_config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("Documentation", provider, model_config)

    def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        code = context.get("code", "")
        
        system_prompt = (
            "You are a Technical Writer. "
            "Generate clear and concise documentation for the provided code. "
            "Include an overview, function descriptions, and usage examples."
            "Format as Markdown."
        )
        
        user_input = f"Code:\n{code}\n\nTask: {task}"
        
        docs = self._call_llm(system_prompt, user_input)
        
        return {
            "status": "success",
            "documentation": docs,
            "agent": "DocumentationAgent"
        }
