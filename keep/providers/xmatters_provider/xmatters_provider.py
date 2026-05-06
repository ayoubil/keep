"""xMattersProvider sends alert notifications via xMatters Flow Designer webhook."""
import dataclasses
from typing import Optional

import pydantic
import requests

from keep.contextmanager.contextmanager import ContextManager
from keep.exceptions.provider_exception import ProviderException
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig
from keep.validation.fields import HttpsUrl


@pydantic.dataclasses.dataclass
class XMattersProviderAuthConfig:
    webhook_url: HttpsUrl = dataclasses.field(
        metadata={
            "required": True,
            "description": "xMatters Flow Designer incoming webhook URL",
            "sensitive": True,
            "validation": "https_url",
        }
    )


class XMattersProvider(BaseProvider):
    """Sends alert notifications via xMatters Flow Designer webhook."""

    PROVIDER_DISPLAY_NAME = "xMatters"
    PROVIDER_CATEGORY = ["Incident Management"]
    PROVIDER_TAGS = ["incident"]

    def __init__(
        self,
        context_manager: ContextManager,
        provider_id: str,
        config: ProviderConfig,
    ):
        super().__init__(context_manager, provider_id, config)

    def validate_config(self):
        self.authentication_config = XMattersProviderAuthConfig(
            **self.config.authentication
        )

    def dispose(self):
        pass

    def _notify(
        self,
        message: str = "",
        title: str = "Keep Alert",
        severity: str = "high",
        **kwargs,
    ):
        if not message:
            raise ProviderException(
                f"{self.__class__.__name__} requires a message"
            )
        payload = {
            "properties": {
                "subject": title,
                "body": message,
                "severity": severity,
            }
        }
        response = requests.post(
            str(self.authentication_config.webhook_url), json=payload
        )
        if response.status_code not in (200, 202):
            raise ProviderException(
                f"{self.__class__.__name__} failed: HTTP {response.status_code}"
                f" - {response.text[:200]}"
            )
        self.logger.debug("xMatters notification sent")
