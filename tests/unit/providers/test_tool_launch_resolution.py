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


@pytest.mark.asyncio
async def test_holehe_raises_on_nonzero_exit() -> None:
    mock_proc = type(
        "Proc",
        (),
        {
            "communicate": lambda self, timeout=None: (
                b"",
                b"Traceback: update check failed",
            ),
            "returncode": 1,
            "pid": 99999,
            "__enter__": lambda self: self,
            "__exit__": lambda self, *a: None,
        },
    )()
    with patch(
        "backend.app.providers.tools.holehe.client.subprocess.Popen",
        return_value=mock_proc,
    ):
        with pytest.raises(ProviderError, match="update check failed"):
            await HoleheProvider._run_holehe_async(
                "person@example.com",
                ["/usr/local/bin/holehe"],
            )


@pytest.mark.asyncio
async def test_holehe_parses_domain_without_recovery_metadata() -> None:
    stdout = b"[+] github.com / FullName Test User\n[+] spotify.com\n"
    mock_proc = type(
        "Proc",
        (),
        {
            "communicate": lambda self, timeout=None: (stdout, b""),
            "returncode": 0,
            "pid": 99999,
            "__enter__": lambda self: self,
            "__exit__": lambda self, *a: None,
        },
    )()
    with patch(
        "backend.app.providers.tools.holehe.client.subprocess.Popen",
        return_value=mock_proc,
    ):
        found = await HoleheProvider._run_holehe_async(
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
