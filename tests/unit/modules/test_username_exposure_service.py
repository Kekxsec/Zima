import uuid
from unittest.mock import patch

import pytest

from backend.app.modules.identity.username_exposure.service import (
    UsernameExposureService,
)


@pytest.mark.asyncio
async def test_username_exposure_service_does_not_run_maigret_for_email_local_part() -> (
    None
):
    service = UsernameExposureService()

    with patch(
        "backend.app.modules.identity.username_exposure.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = None

        signals = await service.run(
            user_id=uuid.uuid4(),
            asset_id=uuid.uuid4(),
            asset_value="alice@example.com",
        )

    assert signals == []
