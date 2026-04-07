# backend/app/modules/browser/extension_risk/service.py
import uuid

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.modules.browser.extension_risk.rules import crxcavator_severity
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.cloud.chrome_web_store_api.client import (
    ChromeWebStoreApiProvider,
)
from backend.app.providers.cloud.firefox_addons_site_api.client import (
    FirefoxAddonsSiteApiProvider,
)
from backend.app.providers.threat_intel.crxcavator.client import CrxcavatorProvider
from backend.app.providers.tools.browser_extension_detector.client import (
    BrowserExtensionDetectorProvider,
)
from backend.app.providers.tools.malicious_extension_sentry.client import (
    MaliciousExtensionSentryProvider,
)
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


class ExtensionRiskService(BaseModuleService):
    module_name = "extension_risk"
    module_domain = "browser"
    required_entity_types = [EntityType.URL, EntityType.DEVICE]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        ctx: object = None,
    ) -> list[SignalCreate]:
        """Assess browser extension risk.

        Dispatches based on asset_value:
          - URL assets (extension ID assets): CRXcavator risk report path.
            asset_value format: "{extension_id}:{version}:{platform}"
            e.g. "cfhdojbkjhnklbpkdaibdccddilifddb:1.2.3:Chrome"
            Defaults: version="latest", platform="Chrome".

          - DEVICE assets: local extension scan path.
            Enumerates installed extensions via filesystem scan and checks
            each against the Malicious Extension Sentry database.
        """
        # Dispatch: if asset_value looks like a Chromium extension ID (32 lowercase
        # letters) or contains ":version:platform" parts, use the URL/CRXcavator path.
        # Otherwise treat this as a DEVICE asset and run the local scan path.
        parts = asset_value.strip().split(":")
        candidate_id = parts[0].strip()
        is_extension_asset = (
            # Chromium extension ID: 32 lowercase alphabetic characters
            (
                len(candidate_id) == 32
                and candidate_id.isalpha()
                and candidate_id.islower()
            )
            # Firefox GUID: {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx} or {name@domain}
            or (candidate_id.startswith("{") and candidate_id.endswith("}"))
            # Firefox email-style ID: e.g. uBlock0@raymondhill.net
            or "@" in candidate_id
        )

        if is_extension_asset:
            return await self._run_crxcavator_path(
                user_id=user_id,
                asset_id=asset_id,
                asset_value=asset_value,
                parts=parts,
            )
        else:
            return await self._run_device_scan_path(
                user_id=user_id,
                asset_id=asset_id,
                asset_value=asset_value,
            )

    async def _run_crxcavator_path(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        parts: list[str],
    ) -> list[SignalCreate]:
        """CRXcavator risk report for a single known extension asset."""
        signals: list[SignalCreate] = []

        extension_id = parts[0].strip()
        version = parts[1].strip() if len(parts) > 1 else "latest"
        platform = parts[2].strip() if len(parts) > 2 else "Chrome"

        if not extension_id:
            return signals

        # --- CRXcavator risk report ---
        crxcavator = CrxcavatorProvider()
        crx_data: dict = {}
        try:
            if version == "latest":
                versions = await crxcavator.get_versions(extension_id)
                if versions and isinstance(versions, list):
                    version = (
                        versions[-1].get("version", "latest") if versions else "latest"
                    )

            if version != "latest":
                crx_data = await crxcavator.check_extension(
                    extension_id, version, platform
                )
        except ProviderError as e:
            logger.error(
                "extension_risk.crxcavator_failure",
                error=str(e),
                extension_id=extension_id,
            )
            crx_data = {}

        risk = {}
        if isinstance(crx_data, dict):
            data = crx_data.get("data") or crx_data
            risk = data.get("risk") if isinstance(data, dict) else {}

        total_risk = risk.get("total") if isinstance(risk, dict) else None

        if total_risk is None:
            logger.info(
                "extension_risk.no_crxcavator_report",
                extension_id=extension_id,
                version=version,
            )
            return signals

        severity = crxcavator_severity(int(total_risk))

        # --- Optional enrichment from CWS / AMO ---
        store_enrichment: dict = {}
        if platform.lower() in {"chrome", "chromium", "edge", "brave"}:
            cws = ChromeWebStoreApiProvider()
            try:
                meta = await cws.get_extension(extension_id)
                if meta:
                    store_enrichment = meta
            except ProviderError:
                pass
        elif platform.lower() == "firefox":
            amo = FirefoxAddonsSiteApiProvider()
            try:
                meta = await amo.get_addon(extension_id)
                if meta:
                    store_enrichment = meta
            except ProviderError:
                pass

        ext_name = store_enrichment.get("name") or extension_id

        signals.append(
            SignalCreate(
                signal_type="browser_extension_risk",
                category="browser_security",
                entity_type=EntityType.URL,
                entity_id=asset_id,
                entity_value=asset_value,
                user_id=user_id,
                severity=severity,
                confidence=Confidence.HIGH,
                source=self.module_name,
                provider="crxcavator",
                summary=(
                    f"Extension '{ext_name}' has CRXcavator total risk "
                    f"score {total_risk} on {platform}"
                ),
                details=(
                    f"CRXcavator risk breakdown — "
                    f"CSP: {risk.get('csp', {}).get('total', 'n/a')}, "
                    f"Permissions: {risk.get('permissions', {}).get('total', 'n/a')}, "
                    f"RetireJS: {risk.get('retire', {}).get('total', 'n/a')}, "
                    f"Webstore: {risk.get('webstore', {}).get('total', 'n/a')}."
                ),
                evidence={
                    "extension_id": extension_id,
                    "version": version,
                    "platform": platform,
                    "total_risk": total_risk,
                    "risk_breakdown": risk,
                    "store_metadata": store_enrichment,
                },
                tags=["extension_risk", "crxcavator", "browser_security"],
                recommended_action=(
                    "Review extension permissions and provenance. "
                    "Consider removing or replacing high-risk extensions."
                ),
                source_ref=f"crxcavator:{extension_id}:{version}:{platform}",
            )
        )

        logger.info(
            "extension_risk.crxcavator_completed",
            user_id=str(user_id),
            extension_id=extension_id,
            total_risk=total_risk,
            severity=severity.value,
            signals_emitted=len(signals),
        )
        return signals

    async def _run_device_scan_path(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
    ) -> list[SignalCreate]:
        """Local extension scan path for DEVICE assets.

        1. Enumerates installed browser extensions via filesystem scan.
        2. Checks each extension ID against the Malicious Extension Sentry database.
        3. Emits a CRITICAL malicious_extension_found signal for each hit.
        """
        signals: list[SignalCreate] = []

        # --- Step 1: enumerate installed extensions ---
        detector = BrowserExtensionDetectorProvider()
        installed: list[dict] = []
        try:
            installed = await detector.scan()
        except ProviderError as e:
            logger.warning(
                "extension_risk.browser_extension_detector_failure",
                error=str(e),
                asset_id=str(asset_id),
            )

        if not installed:
            logger.info(
                "extension_risk.device_scan_no_extensions",
                asset_id=str(asset_id),
            )
            return signals

        # Only check Chromium-based extension IDs — MaliciousExtensionSentry only
        # covers Chrome/Edge; Firefox uses different ID schemes.
        chromium_ids = [
            ext["extension_id"]
            for ext in installed
            if ext.get("browser") in {"chrome", "edge", "brave", "chromium"}
            and len(ext.get("extension_id", "")) == 32
        ]

        if not chromium_ids:
            logger.info(
                "extension_risk.device_scan_no_chromium_extensions",
                asset_id=str(asset_id),
                total_installed=len(installed),
            )
            return signals

        # Build a lookup map for enriching hits with name/version from inventory
        inventory_map: dict[str, dict] = {}
        for ext in installed:
            eid = ext.get("extension_id", "")
            if eid and eid not in inventory_map:
                inventory_map[eid] = ext

        # --- Step 2: check against malicious extension database ---
        sentry = MaliciousExtensionSentryProvider()
        hits: list[dict] = []
        try:
            hits = await sentry.check_extensions(chromium_ids)
        except ProviderError as e:
            logger.warning(
                "extension_risk.malicious_extension_sentry_failure",
                error=str(e),
                asset_id=str(asset_id),
            )

        # --- Step 3: emit signals for each malicious extension found ---
        for hit in hits:
            ext_id = hit.get("extension_id", "")
            db_name = hit.get("name", "")
            date_added = hit.get("date_added", "")
            source_url = hit.get("source_url", "")

            # Enrich with local inventory data if available
            local_ext = inventory_map.get(ext_id, {})
            local_name = local_ext.get("name", "")
            ext_name = db_name or local_name or ext_id
            browser = local_ext.get("browser", "chrome")
            version = local_ext.get("version", "")
            profile = local_ext.get("profile", "")

            details_parts = [
                f"Extension ID: {ext_id}.",
                f"Database entry: added {date_added}." if date_added else "",
                f"Discovery report: {source_url}" if source_url else "",
            ]

            signals.append(
                SignalCreate(
                    signal_type="malicious_extension_found",
                    category="account_security",
                    entity_type=EntityType.DEVICE,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.CRITICAL,
                    confidence=Confidence.MEDIUM,
                    source=self.module_name,
                    provider="malicious_extension_sentry",
                    summary=(
                        f"Malicious browser extension '{ext_name}' (ID: {ext_id}) "
                        f"is installed in {browser}"
                    ),
                    details=" ".join(p for p in details_parts if p),
                    evidence={
                        "extension_id": ext_id,
                        "extension_name": ext_name,
                        "date_added": date_added,
                        "source_url": source_url,
                        "browser": browser,
                        "version": version,
                        "profile": profile,
                        "source_provider": "malicious_extension_sentry",
                    },
                    tags=[
                        "malicious_extension",
                        "browser_security",
                        browser,
                        "extension_risk",
                    ],
                    recommended_action=(
                        f"Remove '{ext_name}' (ID: {ext_id}) from {browser} "
                        "immediately. "
                        "This extension is known to be malicious. Check for signs of "
                        "credential theft, session hijacking, or data exfiltration."
                    ),
                    source_ref=f"malicious_extension_sentry:{ext_id}",
                )
            )

        logger.info(
            "extension_risk.device_scan_completed",
            user_id=str(user_id),
            asset_id=str(asset_id),
            extensions_scanned=len(chromium_ids),
            malicious_found=len(hits),
            signals_emitted=len(signals),
        )
        return signals
