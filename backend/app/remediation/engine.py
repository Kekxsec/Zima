# backend/app/remediation/engine.py
from backend.app.correlation.models import Finding
from backend.app.signals.models import Signal

SIGNAL_TO_PLAYBOOK: dict[str, str] = {
    "email_breached": "rotate_credentials",
    "mfa_missing": "enable_mfa",
    "password_reuse_detected": "rotate_credentials",
    "sms_mfa_only": "upgrade_mfa",
    "password_exposed": "rotate_exposed_password",
    "stealer_log_hit": "device_compromise_response",
    "username_exposure": "review_account_footprint",
    "alias_exposure_detected": "review_alias_accounts",
    "account_discovered": "review_account_footprint",
    "account_enumeration_risk": "review_email_exposure",
}

FINDING_TO_PLAYBOOKS: dict[str, list[str]] = {
    "high_identity_compromise_risk": ["rotate_credentials", "enable_mfa"],
    "username_reuse_detected": ["review_account_footprint"],
}


class RemediationEngine:
    def get_tasks_for_signals(self, signals: list[Signal]) -> list[dict[str, str]]:
        tasks: list[dict[str, str]] = []
        seen: set[str] = set()
        for signal in signals:
            if signal.status != "open":
                continue
            playbook = SIGNAL_TO_PLAYBOOK.get(signal.signal_type)
            if playbook and playbook not in seen:
                seen.add(playbook)
                tasks.append(
                    {
                        "playbook": playbook,
                        "trigger": signal.signal_type,
                        "priority": signal.severity,
                        "entity_value": signal.entity_value,
                    }
                )
        return tasks

    def get_tasks_for_findings(self, findings: list[Finding]) -> list[dict[str, str]]:
        tasks: list[dict[str, str]] = []
        seen: set[str] = set()
        for finding in findings:
            if finding.status != "open":
                continue
            for playbook in FINDING_TO_PLAYBOOKS.get(finding.finding_type, []):
                if playbook not in seen:
                    seen.add(playbook)
                    tasks.append(
                        {
                            "playbook": playbook,
                            "trigger": finding.finding_type,
                            "priority": finding.severity,
                        }
                    )
        return tasks
