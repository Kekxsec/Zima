# tests/factories.py
import hashlib
import uuid
from datetime import UTC, datetime

from factory import Factory, LazyAttribute, Sequence

from backend.app.assets.models import Asset
from backend.app.auth.models import AuthToken, User
from backend.app.correlation.models import Finding
from backend.app.db.models.audit import AuditEvent
from backend.app.scoring.models import Score
from backend.app.signals.models import Signal


class UserFactory(Factory):
    class Meta:
        model = User

    id = LazyAttribute(lambda _: uuid.uuid4())
    tier = "core"
    is_active = True
    deleted_at = None
    last_sign_in_at = None


class AuthTokenFactory(Factory):
    class Meta:
        model = AuthToken

    id = LazyAttribute(lambda _: uuid.uuid4())
    email = Sequence(lambda n: f"user{n}@example.com")
    code_hash = LazyAttribute(lambda _: hashlib.sha256(b"123456").hexdigest())
    expires_at = LazyAttribute(
        lambda _: datetime.now(UTC).replace(year=datetime.now(UTC).year + 1)
    )
    used_at = None
    requested_from_ip = "127.0.0.1"


class AssetFactory(Factory):
    class Meta:
        model = Asset

    id = LazyAttribute(lambda _: uuid.uuid4())
    user_id = LazyAttribute(lambda _: uuid.uuid4())
    entity_type = "email"
    value = Sequence(lambda n: f"asset{n}@example.com")
    is_primary = False
    is_verified = True
    verified_at = LazyAttribute(lambda _: datetime.now(UTC))


class SignalFactory(Factory):
    class Meta:
        model = Signal

    id = LazyAttribute(lambda _: uuid.uuid4())
    signal_id = Sequence(lambda n: f"sig_{n:024x}")
    signal_type = "email_breached"
    category = "identity_security"
    entity_type = "email"
    entity_id = LazyAttribute(lambda _: uuid.uuid4())
    entity_value = Sequence(lambda n: f"user{n}@example.com")
    user_id = LazyAttribute(lambda _: uuid.uuid4())
    severity = "high"
    confidence = "high"
    source = "breach_monitor"
    provider = "hibp"
    summary = "Email found in test breach"
    details = None
    evidence: dict = {}
    tags: list = ["identity", "breach"]
    recommended_action = "Rotate credentials"
    status = "open"


class FindingFactory(Factory):
    class Meta:
        model = Finding

    id = LazyAttribute(lambda _: uuid.uuid4())
    finding_id = Sequence(lambda n: f"fnd_{n:024x}")
    finding_type = "high_identity_compromise_risk"
    user_id = LazyAttribute(lambda _: uuid.uuid4())
    severity = "high"
    confidence = "high"
    title = "Test finding"
    explanation = "Test explanation"
    contributing_signal_ids: list = []
    affected_entity_ids: list = []
    rule_name = "high_identity_compromise_risk"
    status = "open"


class ScoreFactory(Factory):
    class Meta:
        model = Score

    id = LazyAttribute(lambda _: uuid.uuid4())
    user_id = LazyAttribute(lambda _: uuid.uuid4())
    domain = "identity"
    score = 100
    scorer_version = "1.0"
    signal_count = 0
    scan_id = None


class AuditEventFactory(Factory):
    class Meta:
        model = AuditEvent

    id = LazyAttribute(lambda _: uuid.uuid4())
    user_id = LazyAttribute(lambda _: uuid.uuid4())
    event_type = "auth.sign_in_success"
    ip_address = "127.0.0.1"
    event_metadata: dict = {}
