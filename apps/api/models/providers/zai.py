"""
ZAI (Zhipu AI) model provider implementation.

Supports GLM-4.7 and GLM-5 models via OpenAI-compatible API.
Includes a FREE tier model (glm-4.7-flash) for testing.
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

ZAI_BASE_URL = "https://api.z.ai/api/paas/v4"


class ZaiProvider(RemoteModelProvider):
    """ZAI (Zhipu AI) model provider using OpenAI-compatible API."""

    @property
    def name(self) -> str:
        return "zai"

    @property
    def display_name(self) -> str:
        return "ZAI (Zhipu AI)"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        super().__init__(config)
        # Get API key from config, environment, or None
        if "api_key" not in self.config:
            self.config["api_key"] = os.getenv("ZAI_API_KEY")

        # Set base URL for ZAI API
        if "base_url" not in self.config:
            self.config["base_url"] = ZAI_BASE_URL

    def list_models(self) -> List[ModelInfo]:
        """List available ZAI models."""
        return [
            # FREE model - great for testing
            ModelInfo(
                id="glm-4.7-flash",
                display_name="GLM-4.7 Flash (FREE)",
                provider_name=self.display_name,
                context_window=200_000,
                pricing=PricingInfo(input_price_per_1m=0.0, output_price_per_1m=0.0),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="FREE tier model - perfect for testing and development",
                recommended_for=[
                    "testing",
                    "development",
                    "low-cost production",
                    "prototyping",
                ],
            ),
            # Best value for production
            ModelInfo(
                id="glm-4.7-flashx",
                display_name="GLM-4.7 FlashX (Best Value)",
                provider_name=self.display_name,
                context_window=200_000,
                pricing=PricingInfo(input_price_per_1m=0.07, output_price_per_1m=0.40),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Ultra-fast and cheap - best value for production (95%+ cheaper than GPT-5)",
                recommended_for=[
                    "production",
                    "high-volume",
                    "real-time chat",
                    "cost optimization",
                ],
            ),
            # Balanced model
            ModelInfo(
                id="glm-4.7",
                display_name="GLM-4.7 (Balanced)",
                provider_name=self.display_name,
                context_window=128_000,
                pricing=PricingInfo(input_price_per_1m=0.60, output_price_per_1m=2.20),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Balanced performance and cost - good for complex reasoning",
                recommended_for=[
                    "complex reasoning",
                    "balanced workloads",
                    "moderate volume",
                ],
            ),
            # Flagship model
            ModelInfo(
                id="glm-5",
                display_name="GLM-5 (Flagship)",
                provider_name=self.display_name,
                context_window=200_000,
                pricing=PricingInfo(input_price_per_1m=1.00, output_price_per_1m=3.20),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                ],
                description="Flagship model with best performance - still 75% cheaper than GPT-5.2",
                recommended_for=[
                    "complex tasks",
                    "high-quality output",
                    "advanced reasoning",
                ],
            ),
            # Vision models
            ModelInfo(
                id="glm-4.6v-flash",
                display_name="GLM-4.6V Flash Vision (FREE)",
                provider_name=self.display_name,
                context_window=8_000,
                pricing=PricingInfo(input_price_per_1m=0.0, output_price_per_1m=0.0),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                    ModelCapability.VISION,
                ],
                description="FREE vision model for image understanding",
                recommended_for=[
                    "image analysis",
                    "document OCR",
                    "visual Q&A",
                ],
            ),
            ModelInfo(
                id="glm-4.6v",
                display_name="GLM-4.6V Vision",
                provider_name=self.display_name,
                context_window=8_000,
                pricing=PricingInfo(input_price_per_1m=0.30, output_price_per_1m=0.90),
                capabilities=[
                    ModelCapability.STREAMING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.JSON_MODE,
                    ModelCapability.SYSTEM_MESSAGES,
                    ModelCapability.VISION,
                ],
                description="Advanced vision model for complex image tasks",
                recommended_for=[
                    "complex image analysis",
                    "multi-image reasoning",
                    "detailed visual tasks",
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
        """Create ZAI model instance using OpenAI-compatible client."""
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
                "ZAI API key required. Set ZAI_API_KEY environment variable or provide in config."
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
            base_url=self.config.get("base_url", ZAI_BASE_URL),
            request_timeout=timeout,  # type: ignore[call-arg]
            **kwargs,
        )
        if max_tokens is not None:
            llm.max_tokens = max_tokens
        return llm

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        """Validate ZAI connection."""
        api_key = self.get_api_key()
        if not api_key:
            return False, "API key not provided"

        try:
            # Try to create a minimal model instance (using free model)
            self.create_model("glm-4.7-flash")
            # If no error, connection is valid
            return True, None
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
