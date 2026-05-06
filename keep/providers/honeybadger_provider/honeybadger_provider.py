"""HoneybadgerProvider sends error notifications to Honeybadger."""
import dataclasses

import pydantic
import requests

from keep.contextmanager.contextmanager import ContextManager
from keep.exceptions.provider_exception import ProviderException
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig, ProviderScope
from keep.providers.providers_factory import ProvidersFactory


@pydantic.dataclasses.dataclass
class HoneybadgerProviderAuthConfig:
    api_key: str = dataclasses.field(
        metadata={
            "required": True,
            "description": "Honeybadger API key",
            "sensitive": True,
        }
    )
    project_id: str = dataclasses.field(
        metadata={
            "required": True,
            "description": "Honeybadger project ID",
        }
    )


class HoneybadgerProvider(BaseProvider):
    """Send error notices to Honeybadger."""

    PROVIDER_DISPLAY_NAME = "Honeybadger"
    PROVIDER_CATEGORY = ["Monitoring"]

    PROVIDER_SCOPES = [
        ProviderScope(
            name="honeybadger:notify",
            description="Send error notices to Honeybadger",
            mandatory=True,
            alias="Send notices",
        ),
    ]

    def __init__(
        self, context_manager: ContextManager, provider_id: str, config: ProviderConfig
    ):
        super().__init__(context_manager, provider_id, config)

    def validate_config(self):
        self.authentication_config = HoneybadgerProviderAuthConfig(
            **self.config.authentication
        )

    def dispose(self):
        pass

    def _notify(
        self,
        message: str = "",
        error_class: str = "Alert",
        **kwargs,
    ):
        """
        Send an error notice to Honeybadger.

        Args:
            message (str): The error message to report.
            error_class (str): The error class name. Defaults to "Alert".
        """
        if not message:
            raise ProviderException(
                f"{self.__class__.__name__} requires a message"
            )

        payload = {
            "notifier": {
                "name": "Keep",
                "version": "1.0.0",
                "url": "https://keephq.dev",
            },
            "error": {
                "class": error_class,
                "message": message,
            },
            "request": {
                "url": "https://keephq.dev",
            },
        }

        response = requests.post(
            "https://api.honeybadger.io/v1/notices",
            json=payload,
            headers={
                "X-API-Key": self.authentication_config.api_key,
                "Content-Type": "application/json",
            },
        )

        if response.status_code not in (200, 201):
            raise ProviderException(
                f"{self.__class__.__name__} failed: HTTP {response.status_code} - {response.text}"
            )

        self.logger.debug("Honeybadger notice sent successfully")
        return response.json()


if __name__ == "__main__":
    import logging
    import os

    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])
    context_manager = ContextManager(
        tenant_id="singletenant",
        workflow_id="test",
    )

    api_key = os.environ.get("HONEYBADGER_API_KEY")
    project_id = os.environ.get("HONEYBADGER_PROJECT_ID")
    assert api_key and project_id

    provider_config = ProviderConfig(
        description="Honeybadger Provider",
        authentication={"api_key": api_key, "project_id": project_id},
    )
    provider = ProvidersFactory.get_provider(
        context_manager=context_manager,
        provider_id="keep-honeybadger",
        provider_type="honeybadger",
        provider_config=provider_config,
    )
    provider.notify(message="Test alert from Keep", error_class="TestAlert")
