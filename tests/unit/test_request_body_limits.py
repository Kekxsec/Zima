from backend.app.main import (
    _DEFAULT_MAX_REQUEST_BODY_BYTES,
    _MAILBOX_UPLOAD_MAX_REQUEST_BODY_BYTES,
    _max_request_body_bytes_for_path,
)


def test_mailbox_upload_routes_use_larger_request_body_limit() -> None:
    assert (
        _max_request_body_bytes_for_path("/api/v1/email-accounts/uploads")
        == _MAILBOX_UPLOAD_MAX_REQUEST_BODY_BYTES
    )
    assert (
        _max_request_body_bytes_for_path("/api/v1/email-accounts/uploads/folder")
        == _MAILBOX_UPLOAD_MAX_REQUEST_BODY_BYTES
    )


def test_non_mailbox_routes_keep_default_request_body_limit() -> None:
    assert (
        _max_request_body_bytes_for_path("/api/v1/imports/vault")
        == _DEFAULT_MAX_REQUEST_BODY_BYTES
    )
    assert _max_request_body_bytes_for_path("/") == _DEFAULT_MAX_REQUEST_BODY_BYTES
