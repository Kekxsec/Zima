# backend/app/modules/base/service.py
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from backend.app.signals.schemas import SignalCreate

if TYPE_CHECKING:
    from backend.app.jobs.context import ScanExecutionContext


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
        ctx: ScanExecutionContext | None = None,
    ) -> list[SignalCreate]:
        """
        Execute against one asset. Returns signals.
        Must never raise on provider failure — degrade gracefully.
        ctx, if provided, is used by local-subprocess modules to check
        execution policy before spawning child processes.
        """
        ...
