"""FreshserviceProvider creates incidents/tickets in Freshservice."""
import base64
import dataclasses
from typing import Optional

import pydantic
import requests

from keep.contextmanager.contextmanager import ContextManager
from keep.exceptions.provider_exception import ProviderException
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig


@pydantic.dataclasses.dataclass
class FreshserviceProviderAuthConfig:
    domain: str = dataclasses.field(
        metadata={
            "required": True,
            "description": "Freshservice domain (e.g. yourcompany.freshservice.com)",
        }
    )
    api_key: str = dataclasses.field(
        metadata={
            "required": True,
            "description": "Freshservice API key",
            "sensitive": True,
        }
    )
    requester_email: str = dataclasses.field(
        metadata={
            "required": True,
            "description": "Email of the incident requester",
        }
    )


class FreshserviceProvider(BaseProvider):
    """Creates tickets/incidents in Freshservice ITSM."""

    PROVIDER_DISPLAY_NAME = "Freshservice"
    PROVIDER_CATEGORY = ["Ticketing"]
    PROVIDER_TAGS = ["ticketing"]

    def __init__(
        self,
        context_manager: ContextManager,
        provider_id: str,
        config: ProviderConfig,
    ):
        super().__init__(context_manager, provider_id, config)

    def validate_config(self):
        self.authentication_config = FreshserviceProviderAuthConfig(
            **self.config.authentication
        )

    def dispose(self):
        pass

    def _notify(
        self,
        message: str = "",
        title: str = "Keep Alert",
        priority: int = 2,
        **kwargs,
    ):
        if not message:
            raise ProviderException(
                f"{self.__class__.__name__} requires a message"
            )
        domain = self.authentication_config.domain.rstrip("/")
        url = f"https://{domain}/api/v2/tickets"
        credentials = base64.b64encode(
            f"{self.authentication_config.api_key}:X".encode()
        ).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }
        payload = {
            "subject": title,
            "description": message,
            "email": self.authentication_config.requester_email,
            "priority": priority,
            "status": 2,
            "type": "Incident",
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code not in (200, 201):
            raise ProviderException(
                f"{self.__class__.__name__} failed: HTTP {response.status_code}"
                f" - {response.text[:200]}"
            )
        self.logger.debug("Freshservice ticket created")
        return response.json()
