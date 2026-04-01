from importlib.machinery import ModuleSpec
from unittest.mock import patch

import pytest

from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.tools.holehe.client import HoleheProvider
from backend.app.providers.tools.maigret.client import MaigretProvider


def test_holehe_prefers_binary_when_present() -> None:
    with (
        patch(
            "backend.app.providers.tools.holehe.client.shutil.which",
            return_value="/usr/local/bin/holehe",
        ),
        patch(
            "backend.app.providers.tools.holehe.client.importlib.util.find_spec",
            return_value=None,
        ),
    ):
        invocation = HoleheProvider._resolve_invocation()

    assert invocation == ["/usr/local/bin/holehe"]


def test_holehe_falls_back_to_python_module() -> None:
    with (
        patch(
            "backend.app.providers.tools.holehe.client.importlib.util.find_spec",
            return_value=ModuleSpec("holehe", loader=None),
        ),
        patch(
            "backend.app.providers.tools.holehe.client.sys.executable",
            "/usr/bin/python3",
        ),
    ):
        invocation = HoleheProvider._resolve_invocation()

    assert invocation == [
        "/usr/bin/python3",
        "-c",
        "import holehe.core as c; c.check_update = lambda: None; c.main()",
    ]


def test_holehe_raises_when_unavailable() -> None:
    with (
        patch(
            "backend.app.providers.tools.holehe.client.shutil.which", return_value=None
        ),
        patch(
            "backend.app.providers.tools.holehe.client.importlib.util.find_spec",
            return_value=None,
        ),
    ):
        with pytest.raises(ProviderError, match="holehe is not installed"):
            HoleheProvider._resolve_invocation()


def test_holehe_raises_on_nonzero_exit() -> None:
    with patch("backend.app.providers.tools.holehe.client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "Traceback: update check failed"

        with pytest.raises(ProviderError, match="update check failed"):
            HoleheProvider._run_holehe(
                "person@example.com",
                ["/usr/local/bin/holehe"],
            )


def test_holehe_parses_domain_without_recovery_metadata() -> None:
    with patch("backend.app.providers.tools.holehe.client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = (
            "[+] github.com / FullName Test User\n[+] spotify.com\n"
        )
        mock_run.return_value.stderr = ""

        found = HoleheProvider._run_holehe(
            "person@example.com",
            ["/usr/local/bin/holehe"],
        )

    assert found == ["github.com", "spotify.com"]


def test_maigret_prefers_binary_when_present() -> None:
    with patch(
        "backend.app.providers.tools.maigret.client.shutil.which",
        return_value="/usr/local/bin/maigret",
    ):
        invocation = MaigretProvider._resolve_invocation()

    assert invocation == ["/usr/local/bin/maigret"]


def test_maigret_falls_back_to_python_module() -> None:
    with (
        patch(
            "backend.app.providers.tools.maigret.client.shutil.which", return_value=None
        ),
        patch(
            "backend.app.providers.tools.maigret.client.importlib.util.find_spec",
            return_value=ModuleSpec("maigret", loader=None),
        ),
        patch(
            "backend.app.providers.tools.maigret.client.sys.executable",
            "/usr/bin/python3",
        ),
    ):
        invocation = MaigretProvider._resolve_invocation()

    assert invocation == ["/usr/bin/python3", "-m", "maigret"]


def test_maigret_raises_when_unavailable() -> None:
    with (
        patch(
            "backend.app.providers.tools.maigret.client.shutil.which", return_value=None
        ),
        patch(
            "backend.app.providers.tools.maigret.client.importlib.util.find_spec",
            return_value=None,
        ),
    ):
        with pytest.raises(ProviderError, match="maigret is not installed"):
            MaigretProvider._resolve_invocation()
