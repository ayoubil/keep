"""
BetterstackProvider is a class that allows creating incidents in Better Stack (formerly Better Uptime).
"""

import dataclasses
import datetime

import pydantic
import requests

from keep.contextmanager.contextmanager import ContextManager
from keep.providers.base.base_provider import BaseProvider
from keep.providers.models.provider_config import ProviderConfig, ProviderScope


@pydantic.dataclasses.dataclass
class BetterstackProviderAuthConfig:
    """
    Better Stack authentication configuration.
    """

    api_token: str = dataclasses.field(
        metadata={
            "required": True,
            "description": "Better Stack API token",
            "sensitive": True,
        },
    )

    status_page_subdomain: str = dataclasses.field(
        default=None,
        metadata={
            "required": False,
            "description": "Better Stack status page subdomain (optional)",
            "sensitive": False,
        },
    )


class BetterstackProvider(BaseProvider):
    """Create incidents in Better Stack via the Uptime API."""

    PROVIDER_DISPLAY_NAME = "Better Stack"
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

    BASE_API_URL = "https://uptime.betterstack.com/api/v2"

    def __init__(
        self, context_manager: ContextManager, provider_id: str, config: ProviderConfig
    ):
        super().__init__(context_manager, provider_id, config)

    def dispose(self):
        pass

    def validate_config(self):
        self.authentication_config = BetterstackProviderAuthConfig(
            **self.config.authentication
        )

    def __get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.authentication_config.api_token}",
            "Content-Type": "application/json",
        }

    def validate_scopes(self) -> dict[str, bool | str]:
        try:
            response = requests.get(
                f"{self.BASE_API_URL}/monitors",
                headers=self.__get_headers(),
                timeout=10,
            )
            if response.ok:
                return {"authenticated": True}
            return {"authenticated": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"authenticated": str(e)}

    def _notify(
        self,
        name: str = "",
        status: str = "investigating",
        started_at: str = "",
        requester_email: str = "",
        **kwargs,
    ) -> dict:
        """
        Create an incident in Better Stack.

        Args:
            name: Incident title / name.
            status: Incident status (investigating, identified, monitoring, resolved).
            started_at: ISO 8601 timestamp when the incident started. Defaults to now.
            requester_email: Email of the requester.
        """
        if not started_at:
            started_at = datetime.datetime.now(tz=datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

        payload: dict = {
            "name": name,
            "status": status,
            "started_at": started_at,
        }

        if requester_email:
            payload["requester_email"] = requester_email

        self.logger.info(
            "Creating incident in Better Stack",
            extra={"name": name, "status": status},
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
                "Failed to create incident in Better Stack",
                extra={"response_text": response.text, "status_code": response.status_code},
            )
            raise Exception(response.text) from e

        result = response.json()
        self.logger.info(
            "Incident created in Better Stack",
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
        description="Better Stack Provider",
        authentication={"api_token": os.environ["BETTERSTACK_API_TOKEN"]},
    )

    provider = BetterstackProvider(
        context_manager=context_manager,
        provider_id="betterstack-test",
        config=config,
    )
    print(provider.validate_scopes())
