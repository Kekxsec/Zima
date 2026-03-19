# backend/app/modules/base/service.py
import uuid
from abc import ABC, abstractmethod

from backend.app.signals.schemas import SignalCreate


class BaseModuleService(ABC):
    module_name: str
    module_domain: str
    required_entity_types: list[str]  # Modules declare what they need

    @abstractmethod
    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
    ) -> list[SignalCreate]:
        """
        Execute against one asset. Returns signals.
        Must never raise on provider failure — degrade gracefully.
        """
        ...
