"""Mistral model provider — EU-hosted, open-weight models via OpenAI-compatible API."""

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


class MistralProvider(RemoteModelProvider):
    """Mistral model provider using OpenAI-compatible API."""

    @property
    def name(self) -> str:
        return "mistral"

    @property
    def display_name(self) -> str:
        return "Mistral"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("MISTRAL_API_KEY")
        if "base_url" not in self.config:
            self.config["base_url"] = "https://api.mistral.ai/v1"

    def list_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                id="mistral-small-latest",
                display_name="Mistral Small (Latest)",
                provider_name=self.display_name,
                context_window=128000,
                pricing=PricingInfo(input_price_per_1m=0.10, output_price_per_1m=0.30),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Mistral Small 3.1 — fast, cost-effective, good tool use",
                recommended_for=["general chat", "tool use", "EU-hosted workloads"],
            ),
            ModelInfo(
                id="mistral-medium-latest",
                display_name="Mistral Medium (Latest)",
                provider_name=self.display_name,
                context_window=128000,
                pricing=PricingInfo(input_price_per_1m=0.40, output_price_per_1m=2.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Mistral Medium — balanced performance and quality",
                recommended_for=["complex reasoning", "code generation", "analysis"],
            ),
            ModelInfo(
                id="mistral-large-latest",
                display_name="Mistral Large (Latest)",
                provider_name=self.display_name,
                context_window=128000,
                pricing=PricingInfo(input_price_per_1m=2.00, output_price_per_1m=6.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Mistral Large — flagship model for demanding tasks",
                recommended_for=["complex reasoning", "advanced analysis", "multilingual"],
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
                "Mistral API key required. Set MISTRAL_API_KEY environment variable."
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
            base_url=self.config.get("base_url", "https://api.mistral.ai/v1"),
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
            self.create_model("mistral-small-latest")
            return True, None
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
