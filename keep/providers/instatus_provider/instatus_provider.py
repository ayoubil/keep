"""InstatusProvider creates incidents on Instatus status pages."""

import dataclasses
from datetime import datetime, timezone

import pydantic
import requests

from keep.contextmanager.contextmanager import ContextManager
from keep.exceptions.provider_exception import ProviderException
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig


@pydantic.dataclasses.dataclass
class InstatusProviderAuthConfig:
    api_key: str = dataclasses.field(
        metadata={
            "required": True,
            "description": "Instatus API key",
            "sensitive": True,
        }
    )
    page_id: str = dataclasses.field(
        metadata={
            "required": True,
            "description": "Instatus page ID",
        }
    )


class InstatusProvider(BaseProvider):
    PROVIDER_DISPLAY_NAME = "Instatus"
    PROVIDER_CATEGORY = ["Monitoring"]

    def __init__(
        self, context_manager: ContextManager, provider_id: str, config: ProviderConfig
    ):
        super().__init__(context_manager, provider_id, config)

    def validate_config(self):
        self.authentication_config = InstatusProviderAuthConfig(
            **self.config.authentication
        )

    def dispose(self):
        pass

    def _notify(
        self,
        message: str = "",
        title: str = "Keep Alert",
        status: str = "INVESTIGATING",
        **kwargs,
    ):
        if not message:
            raise ProviderException(
                f"{self.__class__.__name__} requires a message"
            )
        url = f"https://api.instatus.com/v2/{self.authentication_config.page_id}/incidents"
        payload = {
            "name": title,
            "message": message,
            "status": status,
            "notify": True,
            "started": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        response = requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.authentication_config.api_key}"
            },
        )
        if response.status_code not in (200, 201):
            raise ProviderException(
                f"{self.__class__.__name__} failed: HTTP {response.status_code} - {response.text[:200]}"
            )
        self.logger.debug("Instatus incident created")


if __name__ == "__main__":
    import logging
    import os

    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])
    context_manager = ContextManager(
        tenant_id="singletenant",
        workflow_id="test",
    )
    config = ProviderConfig(
        description="Instatus Provider",
        authentication={
            "api_key": os.environ.get("INSTATUS_API_KEY"),
            "page_id": os.environ.get("INSTATUS_PAGE_ID"),
        },
    )
    provider = InstatusProvider(
        context_manager, provider_id="instatus-test", config=config
    )
    provider.notify(message="Test incident from Keep", title="Keep Test")
