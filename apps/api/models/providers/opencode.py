"""
OpenCode Go model provider implementation.

OpenCode Go provides an OpenAI-compatible API to curated open coding models
(GLM, Kimi, DeepSeek, MiMo, MiniMax, Qwen) via https://opencode.ai/zen/go/v1
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

OPENCODE_BASE_URL = "https://opencode.ai/zen/go/v1"


class OpenCodeProvider(RemoteModelProvider):
    """OpenCode Go provider — curated open coding models via OpenAI-compatible API."""

    @property
    def name(self) -> str:
        return "opencode"

    @property
    def display_name(self) -> str:
        return "OpenCode Go"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("OPENCODE_API_KEY")

    def list_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                id="glm-5.1",
                display_name="GLM-5.1",
                provider_name=self.display_name,
                context_window=262144,
                pricing=PricingInfo(input_price_per_1m=2.0, output_price_per_1m=8.0),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="ZhipuAI GLM-5.1 — flagship open coding model",
                recommended_for=["coding", "complex reasoning", "agents"],
            ),
            ModelInfo(
                id="glm-5",
                display_name="GLM-5",
                provider_name=self.display_name,
                context_window=262144,
                pricing=PricingInfo(input_price_per_1m=1.5, output_price_per_1m=6.0),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="ZhipuAI GLM-5 — strong open coding model",
                recommended_for=["coding", "general purpose"],
            ),
            ModelInfo(
                id="kimi-k2.6",
                display_name="Kimi K2.6",
                provider_name=self.display_name,
                context_window=131072,
                pricing=PricingInfo(input_price_per_1m=1.5, output_price_per_1m=6.0),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Moonshot Kimi K2.6 — strong coding and reasoning",
                recommended_for=["coding", "reasoning", "agents"],
            ),
            ModelInfo(
                id="kimi-k2.5",
                display_name="Kimi K2.5",
                provider_name=self.display_name,
                context_window=131072,
                pricing=PricingInfo(input_price_per_1m=0.6, output_price_per_1m=2.4),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Moonshot Kimi K2.5 — cost-effective coding model",
                recommended_for=["cost-effective", "coding"],
            ),
            ModelInfo(
                id="deepseek-v4-pro",
                display_name="DeepSeek V4 Pro",
                provider_name=self.display_name,
                context_window=131072,
                pricing=PricingInfo(input_price_per_1m=1.0, output_price_per_1m=4.0),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="DeepSeek V4 Pro — advanced reasoning",
                recommended_for=["reasoning", "analysis", "tools"],
            ),
            ModelInfo(
                id="deepseek-v4-flash",
                display_name="DeepSeek V4 Flash",
                provider_name=self.display_name,
                context_window=131072,
                pricing=PricingInfo(input_price_per_1m=0.1, output_price_per_1m=0.4),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="DeepSeek V4 Flash — ultra-cheap fast model",
                recommended_for=["cost-effective", "fast responses", "high volume"],
            ),
            ModelInfo(
                id="mimo-v2.5-pro",
                display_name="MiMo-V2.5-Pro",
                provider_name=self.display_name,
                context_window=262144,
                pricing=PricingInfo(input_price_per_1m=1.5, output_price_per_1m=6.0),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Xiaomi MiMo-V2.5-Pro — coding specialist",
                recommended_for=["coding", "long context"],
            ),
            ModelInfo(
                id="mimo-v2.5",
                display_name="MiMo-V2.5",
                provider_name=self.display_name,
                context_window=262144,
                pricing=PricingInfo(input_price_per_1m=0.8, output_price_per_1m=3.2),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Xiaomi MiMo-V2.5 — balanced coding model",
                recommended_for=["coding", "balanced cost"],
            ),
            ModelInfo(
                id="qwen3.6-plus",
                display_name="Qwen3.6 Plus",
                provider_name=self.display_name,
                context_window=131072,
                pricing=PricingInfo(input_price_per_1m=0.8, output_price_per_1m=3.2),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Alibaba Qwen3.6 Plus — strong general-purpose model",
                recommended_for=["general purpose", "multilingual"],
            ),
            ModelInfo(
                id="qwen3.5-plus",
                display_name="Qwen3.5 Plus",
                provider_name=self.display_name,
                context_window=131072,
                pricing=PricingInfo(input_price_per_1m=0.2, output_price_per_1m=0.8),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Alibaba Qwen3.5 Plus — budget-friendly, high volume",
                recommended_for=["cost-effective", "high volume", "multilingual"],
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
        api_key = self.get_api_key()
        if not api_key:
            raise RuntimeError(
                "OpenCode API key required. "
                "Set OPENCODE_API_KEY environment variable or provide in config."
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
            base_url=OPENCODE_BASE_URL,
            request_timeout=timeout,
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
            models = self.list_models()
            if models:
                return True, None
            return False, "No models available"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
