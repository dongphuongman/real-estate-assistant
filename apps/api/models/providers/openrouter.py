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
            # --- Top free models (production quality) ---
            ModelInfo(
                id="nvidia/nemotron-3-super-120b-a12b:free",
                display_name="Nemotron 3 Super 120B (Free)",
                provider_name=self.display_name,
                context_window=262144,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="120B MoE hybrid Mamba-Transformer, 12B active. Top free model.",
                recommended_for=["free tier", "production", "chat", "tools", "analysis"],
            ),
            ModelInfo(
                id="meta-llama/llama-3.3-70b-instruct:free",
                display_name="Llama 3.3 70B (Free)",
                provider_name=self.display_name,
                context_window=65536,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="70B multilingual (8 languages), strong dialogue",
                recommended_for=["free tier", "multilingual", "chat"],
            ),
            ModelInfo(
                id="openai/gpt-oss-120b:free",
                display_name="GPT-oss 120B (Free)",
                provider_name=self.display_name,
                context_window=131072,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="OpenAI open-source 120B MoE, function calling",
                recommended_for=["free tier", "general purpose"],
            ),
            ModelInfo(
                id="google/gemma-4-31b-it:free",
                display_name="Gemma 4 31B (Free)",
                provider_name=self.display_name,
                context_window=262144,
                pricing=None,
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="31B dense, 256K context, 140+ languages",
                recommended_for=["free tier", "multilingual", "long context"],
            ),
            # --- Cheap paid models (fallback) ---
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
