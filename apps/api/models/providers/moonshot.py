"""
Moonshot AI (Kimi) model provider implementation.

Supports Moonshot V1 models via OpenAI-compatible API.
Known for strong multimodal and long-context capabilities.
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

MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"


class MoonshotProvider(RemoteModelProvider):
    """Moonshot AI (Kimi) model provider using OpenAI-compatible API."""

    @property
    def name(self) -> str:
        return "moonshot"

    @property
    def display_name(self) -> str:
        return "Moonshot AI (Kimi)"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        # Get API key from config, environment, or None
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("MOONSHOT_API_KEY")

        # Set base URL for Moonshot API
        if "base_url" not in self.config:
            self.config["base_url"] = MOONSHOT_BASE_URL

    def list_models(self) -> List[ModelInfo]:
        """List available Moonshot models."""
        return [
            ModelInfo(
                id="moonshot-v1-8k",
                display_name="Moonshot V1 8K",
                provider_name=self.display_name,
                context_window=8_000,
                pricing=PricingInfo(input_price_per_1m=0.25, output_price_per_1m=0.50),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Fast model with 8K context - great for quick tasks",
                recommended_for=[
                    "quick tasks",
                    "short conversations",
                    "simple queries",
                    "low-latency responses",
                ],
            ),
            ModelInfo(
                id="moonshot-v1-32k",
                display_name="Moonshot V1 32K",
                provider_name=self.display_name,
                context_window=32_000,
                pricing=PricingInfo(input_price_per_1m=0.50, output_price_per_1m=1.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Extended context for longer documents and conversations",
                recommended_for=[
                    "document analysis",
                    "long conversations",
                    "article summarization",
                    "medium-length content",
                ],
            ),
            ModelInfo(
                id="moonshot-v1-128k",
                display_name="Moonshot V1 128K",
                provider_name=self.display_name,
                context_window=128_000,
                pricing=PricingInfo(input_price_per_1m=1.00, output_price_per_1m=2.00),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Full context model for large documents and code analysis",
                recommended_for=[
                    "large document processing",
                    "code analysis",
                    "book summarization",
                    "complex reasoning",
                ],
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
        """Create Moonshot model instance using OpenAI-compatible client."""
        # Validate model exists
        model_info = self.get_model_info(model_id)
        if not model_info:
            available = [m.id for m in self.list_models()]
            raise ValueError(
                f"Model '{model_id}' not available. Available models: {', '.join(available)}"
            )

        # Validate API key
        api_key = self.get_api_key()
        if not api_key:
            raise RuntimeError(
                "Moonshot API key required. "
                "Set MOONSHOT_API_KEY environment variable or provide in config."
            )

        # Get timeout from config or use default from settings
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
            base_url=self.config.get("base_url", MOONSHOT_BASE_URL),
            request_timeout=timeout,  # type: ignore[call-arg]
            **kwargs,
        )
        if max_tokens is not None:
            llm.max_tokens = max_tokens
        return llm

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate Moonshot connection."""
        api_key = self.get_api_key()
        if not api_key:
            return False, "API key not provided"

        try:
            # Try to create a minimal model instance
            self.create_model("moonshot-v1-8k")
            # If no error, connection is valid
            return True, None
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
