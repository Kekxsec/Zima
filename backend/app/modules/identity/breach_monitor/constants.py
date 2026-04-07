# backend/app/modules/identity/breach_monitor/constants.py

SIGNAL_TYPE_EMAIL_BREACHED = "email_breached"
SIGNAL_CATEGORY = "identity_security"

RECOMMENDED_ACTION_BREACH = (
    "Rotate the password used at this service immediately. "
    "Enable MFA if not already active."
)
RECOMMENDED_ACTION_CREDENTIAL = (
    "Rotate the exposed password immediately on all services where it was used. "
    "Use a unique password for each service. Enable MFA."
)
