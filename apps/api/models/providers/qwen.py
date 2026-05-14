"""Qwen/DashScope model provider — bilingual CN/EN models via OpenAI-compatible API."""

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


class QwenProvider(RemoteModelProvider):
    """Qwen model provider via DashScope OpenAI-compatible API."""

    @property
    def name(self) -> str:
        return "qwen"

    @property
    def display_name(self) -> str:
        return "Qwen (Alibaba Cloud)"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("DASHSCOPE_API_KEY")
        if "base_url" not in self.config:
            self.config["base_url"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def list_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                id="qwen-plus-latest",
                display_name="Qwen Plus (Latest)",
                provider_name=self.display_name,
                context_window=131072,
                pricing=PricingInfo(input_price_per_1m=0.14, output_price_per_1m=0.40),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Qwen 3 Plus — balanced performance, excellent CN/EN bilingual",
                recommended_for=["bilingual chat", "general purpose", "Chinese market"],
            ),
            ModelInfo(
                id="qwen-turbo-latest",
                display_name="Qwen Turbo (Latest)",
                provider_name=self.display_name,
                context_window=131072,
                pricing=PricingInfo(input_price_per_1m=0.03, output_price_per_1m=0.06),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Qwen Turbo — ultra-fast, cost-effective",
                recommended_for=["quick responses", "high volume", "classification"],
            ),
            ModelInfo(
                id="qwen-max-latest",
                display_name="Qwen Max (Latest)",
                provider_name=self.display_name,
                context_window=32768,
                pricing=PricingInfo(input_price_per_1m=1.60, output_price_per_1m=6.40),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Qwen Max — flagship for complex reasoning",
                recommended_for=["complex reasoning", "advanced analysis", "long context"],
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
            raise RuntimeError(
                "DashScope API key required. Set DASHSCOPE_API_KEY environment variable."
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
            base_url=self.config.get(
                "base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ),
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
            self.create_model("qwen-turbo-latest")
            return True, None
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
