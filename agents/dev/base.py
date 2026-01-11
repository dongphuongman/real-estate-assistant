"""
Base class for Development Agents.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from models.provider_factory import ModelProviderFactory

logger = logging.getLogger(__name__)

class DevAgent(ABC):
    """Abstract base class for development agents."""

    def __init__(
        self, 
        role: str, 
        provider: str = "openai",
        model_config: Optional[Dict[str, Any]] = None
    ):
        self.role = role
        self.provider_name = provider
        self.config = model_config or {}
        
        # Initialize LLM
        self.llm = self._init_llm()
        
    def _init_llm(self) -> BaseChatModel:
        """Initialize the Language Model."""
        try:
            provider = ModelProviderFactory.get_provider(self.provider_name, self.config)
            
            # Determine model_id
            model_id = self.config.get("model_id")
            if not model_id:
                # Try to find a default or pick the first one
                models = provider.list_models()
                if not models:
                    raise ValueError(f"No models available for provider {self.provider_name}")
                model_id = models[0].id
                
            return provider.create_model(model_id=model_id, temperature=0)
        except Exception as e:
            logger.error(f"Failed to init LLM: {e}")
            raise

    @abstractmethod
    def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the agent's task."""
        pass

    def _call_llm(self, system_prompt: str, user_input: str) -> str:
        """Helper to call LLM."""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input)
        ]
        response = self.llm.invoke(messages)
        content = response.content
        if isinstance(content, str):
            return content
        return str(content)
