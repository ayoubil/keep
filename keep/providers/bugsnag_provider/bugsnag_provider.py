"""BugsnagProvider sends error notifications to Bugsnag."""
import dataclasses

import pydantic
import requests

from keep.contextmanager.contextmanager import ContextManager
from keep.exceptions.provider_exception import ProviderException
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig, ProviderScope
from keep.providers.providers_factory import ProvidersFactory


@pydantic.dataclasses.dataclass
class BugsnagProviderAuthConfig:
    api_key: str = dataclasses.field(
        metadata={
            "required": True,
            "description": "Bugsnag API key",
            "sensitive": True,
        }
    )


class BugsnagProvider(BaseProvider):
    """Send error events to Bugsnag."""

    PROVIDER_DISPLAY_NAME = "Bugsnag"
    PROVIDER_CATEGORY = ["Monitoring"]

    PROVIDER_SCOPES = [
        ProviderScope(
            name="bugsnag:notify",
            description="Send error events to Bugsnag",
            mandatory=True,
            alias="Send events",
        ),
    ]

    def __init__(
        self, context_manager: ContextManager, provider_id: str, config: ProviderConfig
    ):
        super().__init__(context_manager, provider_id, config)

    def validate_config(self):
        self.authentication_config = BugsnagProviderAuthConfig(
            **self.config.authentication
        )

    def dispose(self):
        pass

    def _notify(
        self,
        message: str = "",
        severity: str = "error",
        error_class: str = "Alert",
        **kwargs,
    ):
        """
        Send an error event to Bugsnag.

        Args:
            message (str): The error message to report.
            severity (str): Event severity — "error", "warning", or "info". Defaults to "error".
            error_class (str): The error class name. Defaults to "Alert".
        """
        if not message:
            raise ProviderException(
                f"{self.__class__.__name__} requires a message"
            )

        payload = {
            "apiKey": self.authentication_config.api_key,
            "notifier": {
                "name": "Keep",
                "version": "1.0.0",
                "url": "https://keephq.dev",
            },
            "events": [
                {
                    "exceptions": [
                        {
                            "errorClass": error_class,
                            "message": message,
                            "stacktrace": [],
                        }
                    ],
                    "severity": severity,
                }
            ],
        }

        response = requests.post(
            "https://notify.bugsnag.com/",
            json=payload,
            headers={
                "Bugsnag-Api-Key": self.authentication_config.api_key,
                "Content-Type": "application/json",
                "Bugsnag-Payload-Version": "5",
            },
        )

        if response.status_code not in (200, 202):
            raise ProviderException(
                f"{self.__class__.__name__} failed: HTTP {response.status_code} - {response.text}"
            )

        self.logger.debug("Bugsnag notification sent successfully")
        return response.text


if __name__ == "__main__":
    import logging
    import os

    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])
    context_manager = ContextManager(
        tenant_id="singletenant",
        workflow_id="test",
    )

    api_key = os.environ.get("BUGSNAG_API_KEY")
    assert api_key

    provider_config = ProviderConfig(
        description="Bugsnag Provider",
        authentication={"api_key": api_key},
    )
    provider = ProvidersFactory.get_provider(
        context_manager=context_manager,
        provider_id="keep-bugsnag",
        provider_type="bugsnag",
        provider_config=provider_config,
    )
    provider.notify(message="Test alert from Keep", severity="warning")
