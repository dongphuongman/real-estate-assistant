"""Groq model provider — ultra-fast LPU inference via OpenAI-compatible API."""

import os
from typing import Any, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from .base import (
    ModelCapability,
    ModelInfo,
    PricingInfo,
    RemoteModelProvider,
)


class GroqProvider(RemoteModelProvider):
    """Groq model provider using OpenAI-compatible API."""

    @property
    def name(self) -> str:
        return "groq"

    @property
    def display_name(self) -> str:
        return "Groq"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("GROQ_API_KEY")
        if "base_url" not in self.config:
            self.config["base_url"] = "https://api.groq.com/openai/v1"

    def list_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                id="llama-3.3-70b-versatile",
                display_name="Llama 3.3 70B (Versatile)",
                provider_name=self.display_name,
                context_window=128000,
                pricing=PricingInfo(input_price_per_1m=0.59, output_price_per_1m=0.79),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Meta Llama 3.3 70B — fast general-purpose model",
                recommended_for=["general chat", "reasoning", "tool use"],
            ),
            ModelInfo(
                id="llama-3.1-8b-instant",
                display_name="Llama 3.1 8B (Instant)",
                provider_name=self.display_name,
                context_window=128000,
                pricing=PricingInfo(input_price_per_1m=0.05, output_price_per_1m=0.08),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Ultra-fast lightweight model for simple tasks",
                recommended_for=["quick responses", "classification", "extraction"],
            ),
            ModelInfo(
                id="gemma2-9b-it",
                display_name="Gemma 2 9B IT",
                provider_name=self.display_name,
                context_window=8192,
                pricing=PricingInfo(input_price_per_1m=0.20, output_price_per_1m=0.20),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Google Gemma 2 9B instruction-tuned",
                recommended_for=["instruction following", "summarization"],
            ),
        ]

    def create_model(
        self,
        model_id: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        streaming: bool = True,
        request_timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> BaseChatModel:
        model_info = self.get_model_info(model_id)
        if not model_info:
            available = [m.id for m in self.list_models()]
            raise ValueError(f"Model '{model_id}' not available. Available: {', '.join(available)}")

        api_key = self.get_api_key()
        if not api_key:
            raise RuntimeError("Groq API key required. Set GROQ_API_KEY environment variable.")

        timeout = request_timeout
        if timeout is None:
            timeout = self.config.get("request_timeout")
        if timeout is None:
            from config.settings import get_settings

            timeout = get_settings().llm_request_timeout_seconds

        llm = ChatOpenAI(
            model=model_id,
            temperature=temperature,
            streaming=streaming,
            api_key=SecretStr(api_key),
            base_url=self.config.get("base_url", "https://api.groq.com/openai/v1"),
            request_timeout=timeout,  # type: ignore[call-arg]
            **kwargs,
        )
        if max_tokens is not None:
            llm.max_tokens = max_tokens
        return llm

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        api_key = self.get_api_key()
        if not api_key:
            return False, "API key not provided"
        try:
            self.create_model("llama-3.1-8b-instant")
            return True, None
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
