"""
RootlyProvider is a class that allows creating incidents in Rootly.
"""

import dataclasses
import typing

import pydantic
import requests

from keep.contextmanager.contextmanager import ContextManager
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig, ProviderScope


@pydantic.dataclasses.dataclass
class RootlyProviderAuthConfig:
    """
    Rootly authentication configuration.
    """

    api_key: str = dataclasses.field(
        metadata={
            "required": True,
            "description": "Rootly API key",
            "sensitive": True,
        },
    )


class RootlyProvider(BaseProvider):
    """Create incidents in Rootly via the REST API."""

    PROVIDER_DISPLAY_NAME = "Rootly"
    PROVIDER_CATEGORY = ["Incident Management"]
    PROVIDER_TAGS = ["alert"]

    PROVIDER_SCOPES = [
        ProviderScope(
            name="authenticated",
            description="User is authenticated",
            mandatory=True,
            alias="Authenticated",
        ),
    ]

    BASE_API_URL = "https://api.rootly.com/v1"

    SEVERITY_VALUES = typing.Literal["critical", "high", "medium", "low"]

    def __init__(
        self, context_manager: ContextManager, provider_id: str, config: ProviderConfig
    ):
        super().__init__(context_manager, provider_id, config)

    def dispose(self):
        pass

    def validate_config(self):
        self.authentication_config = RootlyProviderAuthConfig(
            **self.config.authentication
        )

    def __get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.authentication_config.api_key}",
            "Content-Type": "application/vnd.api+json",
        }

    def validate_scopes(self) -> dict[str, bool | str]:
        try:
            response = requests.get(
                f"{self.BASE_API_URL}/incidents",
                headers=self.__get_headers(),
                params={"page[size]": 1},
                timeout=10,
            )
            if response.ok:
                return {"authenticated": True}
            return {"authenticated": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"authenticated": str(e)}

    def _notify(
        self,
        title: str = "",
        description: str = "",
        severity: str = "high",
        **kwargs,
    ) -> dict:
        """
        Create an incident in Rootly.

        Args:
            title: Incident title.
            description: Incident description.
            severity: Severity level (critical, high, medium, low).
        """
        attributes: dict = {"title": title}

        if description:
            attributes["description"] = description

        if severity:
            attributes["severity"] = severity

        payload = {"data": {"attributes": attributes}}

        self.logger.info(
            "Creating incident in Rootly",
            extra={"title": title, "severity": severity},
        )

        response = requests.post(
            f"{self.BASE_API_URL}/incidents",
            headers=self.__get_headers(),
            json=payload,
            timeout=30,
        )

        try:
            response.raise_for_status()
        except Exception as e:
            self.logger.error(
                "Failed to create incident in Rootly",
                extra={"response_text": response.text, "status_code": response.status_code},
            )
            raise Exception(response.text) from e

        result = response.json()
        self.logger.info(
            "Incident created in Rootly",
            extra={"incident_id": result.get("data", {}).get("id")},
        )
        return result


if __name__ == "__main__":
    import logging
    import os

    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])
    context_manager = ContextManager(
        tenant_id="singletenant",
        workflow_id="test",
    )

    config = ProviderConfig(
        description="Rootly Provider",
        authentication={"api_key": os.environ["ROOTLY_API_KEY"]},
    )

    provider = RootlyProvider(
        context_manager=context_manager,
        provider_id="rootly-test",
        config=config,
    )
    print(provider.validate_scopes())
