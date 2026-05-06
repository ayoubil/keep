"""StatuspageProvider creates incidents on Atlassian Statuspage."""

import dataclasses

import pydantic
import requests

from keep.contextmanager.contextmanager import ContextManager
from keep.exceptions.provider_exception import ProviderException
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig


@pydantic.dataclasses.dataclass
class StatuspageProviderAuthConfig:
    api_key: str = dataclasses.field(
        metadata={
            "required": True,
            "description": "Statuspage API key (OAuth token)",
            "sensitive": True,
        }
    )
    page_id: str = dataclasses.field(
        metadata={
            "required": True,
            "description": "Statuspage page ID",
        }
    )


class StatuspageProvider(BaseProvider):
    PROVIDER_DISPLAY_NAME = "Statuspage"
    PROVIDER_CATEGORY = ["Monitoring"]

    def __init__(
        self, context_manager: ContextManager, provider_id: str, config: ProviderConfig
    ):
        super().__init__(context_manager, provider_id, config)

    def validate_config(self):
        self.authentication_config = StatuspageProviderAuthConfig(
            **self.config.authentication
        )

    def dispose(self):
        pass

    def _notify(
        self,
        message: str = "",
        title: str = "Keep Alert",
        status: str = "investigating",
        **kwargs,
    ):
        if not message:
            raise ProviderException(
                f"{self.__class__.__name__} requires a message"
            )
        url = f"https://api.statuspage.io/v1/pages/{self.authentication_config.page_id}/incidents"
        payload = {
            "incident": {
                "name": title,
                "status": status,
                "body": message,
            }
        }
        response = requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"OAuth {self.authentication_config.api_key}"
            },
        )
        if response.status_code not in (200, 201):
            raise ProviderException(
                f"{self.__class__.__name__} failed: HTTP {response.status_code} - {response.text[:200]}"
            )
        self.logger.debug("Statuspage incident created")


if __name__ == "__main__":
    import logging
    import os

    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])
    context_manager = ContextManager(
        tenant_id="singletenant",
        workflow_id="test",
    )
    config = ProviderConfig(
        description="Statuspage Provider",
        authentication={
            "api_key": os.environ.get("STATUSPAGE_API_KEY"),
            "page_id": os.environ.get("STATUSPAGE_PAGE_ID"),
        },
    )
    provider = StatuspageProvider(
        context_manager, provider_id="statuspage-test", config=config
    )
    provider.notify(message="Test incident from Keep", title="Keep Test")
