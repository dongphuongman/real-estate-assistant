"""
OpenRouter model provider implementation.

OpenRouter provides a unified OpenAI-compatible API to 400+ models
from multiple providers, including free models for budget-conscious usage.
"""

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

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(RemoteModelProvider):
    """OpenRouter model provider — unified API to 400+ models."""

    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def display_name(self) -> str:
        return "OpenRouter"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("OPENROUTER_API_KEY")

    def list_models(self) -> List[ModelInfo]:
        """List curated OpenRouter models (free + cheap)."""
        return [
            # --- Free models ---
            ModelInfo(
                id="meta-llama/llama-3.1-8b-instruct:free",
                display_name="Llama 3.1 8B (Free)",
                provider_name=self.display_name,
                context_window=131072,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Free tier Llama 3.1 8B — good for general queries",
                recommended_for=["free tier", "general purpose", "chat"],
            ),
            ModelInfo(
                id="google/gemma-2-9b-it:free",
                display_name="Gemma 2 9B (Free)",
                provider_name=self.display_name,
                context_window=8192,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Free tier Gemma 2 9B — strong instruction following",
                recommended_for=["free tier", "instruction following"],
            ),
            ModelInfo(
                id="qwen/qwen-2-7b-instruct:free",
                display_name="Qwen 2 7B (Free)",
                provider_name=self.display_name,
                context_window=32768,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Free tier Qwen 2 7B — good multilingual support",
                recommended_for=["free tier", "multilingual"],
            ),
            # --- Cheap paid models ---
            ModelInfo(
                id="deepseek/deepseek-chat",
                display_name="DeepSeek V3",
                provider_name=self.display_name,
                context_window=65536,
                pricing=PricingInfo(input_price_per_1m=0.14, output_price_per_1m=0.28),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="DeepSeek V3 — very cheap, strong reasoning",
                recommended_for=["cost-effective", "reasoning", "general purpose"],
            ),
            ModelInfo(
                id="google/gemini-2.0-flash-exp:free",
                display_name="Gemini 2.0 Flash (Free)",
                provider_name=self.display_name,
                context_window=1048576,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Free Gemini 2.0 Flash — fast, 1M context",
                recommended_for=["free tier", "fast responses", "long context"],
            ),
            ModelInfo(
                id="openai/gpt-4o-mini",
                display_name="GPT-4o Mini (via OpenRouter)",
                provider_name=self.display_name,
                context_window=128000,
                pricing=PricingInfo(input_price_per_1m=0.15, output_price_per_1m=0.60),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="GPT-4o Mini through OpenRouter — affordable quality",
                recommended_for=["balanced quality/cost", "function calling"],
            ),
            ModelInfo(
                id="anthropic/claude-3.5-haiku",
                display_name="Claude 3.5 Haiku (via OpenRouter)",
                provider_name=self.display_name,
                context_window=200000,
                pricing=PricingInfo(input_price_per_1m=0.80, output_price_per_1m=4.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Claude 3.5 Haiku — fast and capable",
                recommended_for=["fast quality", "analysis"],
            ),
        ]

    def get_free_model_ids(self) -> List[str]:
        """Return IDs of models with no pricing (free tier)."""
        return [m.id for m in self.list_models() if m.pricing is None]

    def create_model(
        self,
        model_id: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        streaming: bool = True,
        request_timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> BaseChatModel:
        """Create OpenRouter model instance via OpenAI-compatible API."""
        api_key = self.get_api_key()
        if not api_key:
            raise RuntimeError(
                "OpenRouter API key required. "
                "Set OPENROUTER_API_KEY environment variable or provide in config."
            )

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
            base_url=OPENROUTER_BASE_URL,
            request_timeout=timeout,
            default_headers={
                "HTTP-Referer": self.config.get("app_url", "https://realestate.assistant"),
                "X-Title": "AI Real Estate Assistant",
            },
            **kwargs,
        )
        if max_tokens is not None:
            llm.max_tokens = max_tokens
        return llm

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate OpenRouter connection."""
        api_key = self.get_api_key()
        if not api_key:
            return False, "API key not provided"
        try:
            free_models = self.get_free_model_ids()
            if free_models:
                return True, None
            return False, "No free models available"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
